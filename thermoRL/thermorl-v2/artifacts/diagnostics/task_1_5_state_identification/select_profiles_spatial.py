"""Augment preconditioning-only candidate set with spatial pulse profiles."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from raps.system_config import get_system_config

from select_profiles import CDU_VARS, select_design
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def powers(spec: dict, interval_start_s: int, switched_at_s: int | None) -> np.ndarray:
    vector = np.full(44, 10.86)
    active = interval_start_s >= spec["start_s"] and switched_at_s is None
    if "fixed_end_s" in spec:
        active = active and interval_start_s < spec["fixed_end_s"]
    if active:
        if spec["scope"] == "rack_01":
            vector[0] = spec["power_kw"]
        else:
            vector[1:] = spec["power_kw"]
    return vector


def main() -> None:
    prereg_path = ROOT / "preregistration.json"
    addendum_path = ROOT / "preregistration_spatial_addendum.json"
    original_path = ROOT / "selection.json"
    config = json.loads(prereg_path.read_text())
    addendum = json.loads(addendum_path.read_text())
    original = json.loads(original_path.read_text())
    assert addendum["original_preregistration_sha256"] == sha256(prereg_path)
    assert addendum["uniform_candidate_selection_sha256"] == sha256(original_path)
    ambient = Ambient()
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    dt = config["communication_interval_s"]
    target = config["target_rack_01_coolant_c"]
    tolerance = config["match_tolerance_c"]
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    initial_handle = backend.save_state()
    all_rows = []
    spatial = {}
    try:
        def capture(name: str, elapsed: float, applied: np.ndarray, old_target: float | None) -> dict:
            th = backend.observe()
            gl = backend.global_observe()
            current = float(th.t_c[0])
            return {
                "profile": name,
                "elapsed_s": elapsed,
                "fmu_time_s": backend.time_s,
                "rack_01_power_kw": float(applied[0]),
                "other_racks_power_kw_each": float(applied[1]),
                "rack_01_coolant_c": current,
                "rack_01_slope_k_per_min": None if old_target is None else (current - old_target) / dt * 60.0,
                "mean_other_rack_coolant_c": float(np.mean(th.t_c[1:])),
                "cdu_01_primary_supply_c": float(th.extras["T_prim_s_C"][0]),
                "cdu_01_primary_return_c": float(th.extras["T_prim_r_C"][0]),
                "mean_other_cdu_primary_return_c": float(np.mean(th.extras["T_prim_r_C"][1:])),
                "datacenter_primary_flow_gpm": float(gl["fmu.V_flow_prim_GPM"]),
            }

        for name, spec in addendum["new_preconditioning_candidates"].items():
            backend.restore_state(initial_handle)
            switched_at = None
            first_match = None
            rows = [capture(name, 0.0, np.full(44, 10.86), None)]
            for tick in range(1, config["max_preconditioning_s"] // dt + 1):
                start = (tick - 1) * dt
                applied = powers(spec, start, switched_at)
                backend.step(applied, dt, ambient)
                now = tick * dt
                row = capture(name, float(now), applied, rows[-1]["rack_01_coolant_c"])
                rows.append(row)
                if "fixed_end_s" in spec and now == spec["fixed_end_s"]:
                    switched_at = now
                if "end_rule" in spec and switched_at is None and spec["scope"] == "rack_01" and applied[0] != 10.86:
                    if (spec["power_kw"] > 10.86 and row["rack_01_coolant_c"] >= 32.1) or (spec["power_kw"] < 10.86 and row["rack_01_coolant_c"] <= 32.1):
                        switched_at = now
                eligible = (
                    switched_at is not None
                    and now >= switched_at + dt
                    and row["rack_01_power_kw"] == 10.86
                    and row["other_racks_power_kw_each"] == 10.86
                    and abs(row["rack_01_coolant_c"] - target) <= tolerance
                )
                if eligible and first_match is None:
                    first_match = now
                if first_match is not None and now >= first_match + 200:
                    break
            all_rows.extend(rows)
            candidates = [row for row in rows if first_match is not None
                and first_match <= row["elapsed_s"] <= first_match + 200
                and row["rack_01_power_kw"] == 10.86
                and row["other_racks_power_kw_each"] == 10.86
                and abs(row["rack_01_coolant_c"] - target) <= tolerance]
            best = min(candidates, key=lambda row: (abs(row["rack_01_coolant_c"] - target), row["elapsed_s"])) if candidates else None
            spatial[name] = {
                "spec": spec,
                "switch_back_time_s": switched_at,
                "first_match_time_s": first_match,
                "selected": best,
                "rows_recorded": len(rows),
            }
    finally:
        backend.free_state(initial_handle)
        backend.close()

    trace_path = ROOT / "candidate_preconditioning_spatial.csv"
    with trace_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    combined = {**original["all_candidates"], **spatial}
    feasible = {name: value for name, value in combined.items() if value["selected"] is not None}
    count = 6 if len(feasible) >= 6 else 5 if len(feasible) == 5 else 0
    selected, design_info = select_design(feasible, count) if count else ([], {})
    result = {
        "status": "selected" if selected else "fewer_than_five_matches_no_step_branches",
        "selected_profiles": selected,
        "selected_count": count,
        "design_info": design_info,
        "all_candidates": combined,
        "spatial_candidates": spatial,
        "original_selection_sha256": sha256(original_path),
        "spatial_preregistration_sha256": sha256(addendum_path),
        "selection_script_sha256": sha256(Path(__file__)),
        "spatial_trace_sha256": sha256(trace_path),
        "fmu_sha256": sha256(FMU),
        "spatial_trace_rows": len(all_rows),
    }
    (ROOT / "selection_spatial.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "selected_profiles": selected,
        "design_info": design_info,
        "spatial_states": {name: {"switch": v["switch_back_time_s"], "selected": v["selected"]} for name, v in spatial.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
