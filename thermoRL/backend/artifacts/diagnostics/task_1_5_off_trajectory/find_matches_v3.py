"""Preconditioning-only feasibility check for documented v3 switch point."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from raps.system_config import get_system_config

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
CDU_VARS = {
    "T_prim_s_C": CDU_SUMMARY + "T_prim_s_C",
    "T_prim_r_C": CDU_SUMMARY + "T_prim_r_C",
}
PROFILES = ("constant_hold", "late_high_then_base", "low_then_raised_base")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_power(name: str, interval_start_s: int, switched_at_s: int | None) -> float:
    if name == "constant_hold":
        return 10.86
    if name == "late_high_then_base":
        return 10.86 if interval_start_s < 7200 or switched_at_s is not None else 20.0
    if name == "low_then_raised_base":
        return 10.86 if interval_start_s < 600 or switched_at_s is not None else 5.0
    raise ValueError(name)


def main() -> None:
    config_path = ROOT / "preregistration_v2.json"
    addendum_path = ROOT / "preregistration_v3.json"
    model_path = ROOT / "frozen_coolant_only_model.json"
    config = json.loads(config_path.read_text())
    addendum = json.loads(addendum_path.read_text())
    assert addendum["inherits_preregistration_v2_sha256"] == sha256(config_path)
    assert addendum["prior_v2_feasibility_sha256"] == sha256(ROOT / "match_selection_v2.json")
    assert config["frozen_coolant_only_model_sha256"] == sha256(model_path)
    assert config["prior_feasibility_selection_sha256"] == sha256(ROOT / "match_selection.json")
    dt = config["sample_interval_s"]
    target = config["target_rack_01_coolant_c"]
    tol = config["target_match_tolerance_c"]
    ambient = Ambient()
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    initial_handle = backend.save_state()
    all_rows = []
    selection = {}
    try:
        def capture(name: str, elapsed: float, power: float, previous_t: float | None) -> dict:
            th = backend.observe()
            gl = backend.global_observe()
            current = float(th.t_c[0])
            return {
                "profile": name,
                "elapsed_s": elapsed,
                "fmu_time_s": backend.time_s,
                "power_applied_during_preceding_interval_kw_each_rack": power,
                "rack_01_coolant_c": current,
                "rack_01_slope_k_per_min": None if previous_t is None else (current - previous_t) / dt * 60.0,
                "cdu_01_primary_supply_c": float(th.extras["T_prim_s_C"][0]),
                "cdu_01_primary_return_c": float(th.extras["T_prim_r_C"][0]),
                "datacenter_primary_flow_gpm": float(gl["fmu.V_flow_prim_GPM"]),
            }

        for name in PROFILES:
            backend.restore_state(initial_handle)
            switched_at = None
            rows = [capture(name, 0.0, 10.86, None)]
            first_hit_time = None
            for tick in range(1, config["maximum_preconditioning_s"] // dt + 1):
                start = (tick - 1) * dt
                power = profile_power(name, start, switched_at)
                backend.step(np.full(coupling.num_cdus, power), dt, ambient)
                now = tick * dt
                row = capture(name, float(now), power, rows[-1]["rack_01_coolant_c"])
                rows.append(row)
                if name == "late_high_then_base" and switched_at is None and power == 20.0 and row["rack_01_coolant_c"] >= addendum["late_high_switch_threshold_c"]:
                    switched_at = now
                if name == "low_then_raised_base" and switched_at is None and power == 5.0 and row["rack_01_coolant_c"] <= 32.1:
                    switched_at = now
                eligible = (
                    now >= 600
                    and (switched_at is not None or name == "constant_hold")
                    and now >= (switched_at or 0) + dt
                    and power == 10.86
                )
                if eligible and abs(row["rack_01_coolant_c"] - target) <= tol and first_hit_time is None:
                    first_hit_time = now
                if first_hit_time is not None and now >= first_hit_time + 200:
                    break
            all_rows.extend(rows)
            candidates = [
                row for row in rows
                if first_hit_time is not None
                and first_hit_time <= row["elapsed_s"] <= first_hit_time + 200
                and row["power_applied_during_preceding_interval_kw_each_rack"] == 10.86
                and abs(row["rack_01_coolant_c"] - target) <= tol
            ]
            best = min(candidates, key=lambda row: (abs(row["rack_01_coolant_c"] - target), row["elapsed_s"])) if candidates else None
            selection[name] = {
                "profile_switch_back_time_s": switched_at,
                "first_match_time_s": first_hit_time,
                "selected": None if best is None else best,
                "rows_recorded": len(rows),
            }
    finally:
        backend.free_state(initial_handle)
        backend.close()

    trace_path = ROOT / "feasibility_preconditioning_v3.csv"
    with trace_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    result = {
        "status": "matched" if all(selection[name]["selected"] is not None for name in PROFILES) else "feasibility_failed_no_step_branches",
        "selected": selection,
        "preregistration_v2_sha256": sha256(config_path),
        "preregistration_v3_sha256": sha256(addendum_path),
        "frozen_model_sha256": sha256(model_path),
        "source_script_sha256": sha256(Path(__file__)),
        "fmu_sha256": sha256(FMU),
        "feasibility_trace_sha256": sha256(trace_path),
        "total_rows": len(all_rows),
    }
    (ROOT / "match_selection_v3.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
