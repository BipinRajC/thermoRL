"""Find preregistered temperature matches using preconditioning only."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from raps.system_config import get_system_config

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
CDU_VARS = {
    "T_prim_s_C": CDU_SUMMARY + "T_prim_s_C",
    "T_prim_r_C": CDU_SUMMARY + "T_prim_r_C",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_power(schedule: list[list[float]], interval_start_s: int) -> float:
    return next(power for start, power in reversed(schedule) if interval_start_s >= start)


def main() -> None:
    prereg_path = ROOT / "preregistration.json"
    model_path = ROOT / "frozen_coolant_only_model.json"
    config = json.loads(prereg_path.read_text())
    dt = config["branch_protocol"]["communication_interval_s"]
    max_s = config["max_preconditioning_s"]
    ambient = Ambient(t_air_k=config["branch_protocol"]["ambient_air_k"], t_ext_k=config["branch_protocol"]["ambient_external_k"])
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    heat_keys = power_input_names(coupling)
    rows = []
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    initial_handle = backend.save_state()
    try:
        def capture(profile: str, elapsed: float, power_kw: float) -> dict:
            thermal = backend.observe()
            globals_ = backend.global_observe()
            powers = np.full(coupling.num_cdus, power_kw)
            inputs = rack_kw_to_fmu_inputs(powers, coupling, ambient)
            row = {"profile": profile, "elapsed_s": elapsed, "fmu_time_s": backend.time_s}
            row.update({f"rack_{i:02d}_coolant_c": float(thermal.t_c[i - 1]) for i in range(1, 45)})
            row.update({f"cdu_{i:02d}_primary_supply_c": float(thermal.extras["T_prim_s_C"][i - 1]) for i in range(1, 45)})
            row.update({f"cdu_{i:02d}_primary_return_c": float(thermal.extras["T_prim_r_C"][i - 1]) for i in range(1, 45)})
            row.update({f"rack_{i:02d}_power_kw": power_kw for i in range(1, 45)})
            row.update({f"rack_{i:02d}_fmu_heat_input_w": float(inputs[heat_keys[i - 1]]) for i in range(1, 45)})
            row["datacenter_primary_flow_gpm"] = float(globals_["fmu.V_flow_prim_GPM"])
            return row

        for name, schedule in config["preconditioning_profiles"].items():
            backend.restore_state(initial_handle)
            rows.append(capture(name, 0.0, profile_power(schedule, 0)))
            for tick in range(1, max_s // dt + 1):
                start = (tick - 1) * dt
                power = profile_power(schedule, start)
                backend.step(np.full(coupling.num_cdus, power), dt, ambient)
                rows.append(capture(name, float(tick * dt), power))
    finally:
        backend.free_state(initial_handle)
        backend.close()

    trace_path = ROOT / "feasibility_preconditioning.csv"
    with trace_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    by_profile = {name: [row for row in rows if row["profile"] == name] for name in config["preconditioning_profiles"]}
    candidates = {}
    selected = None
    tolerance = config["rack_01_match_tolerance_c"]
    for target in config["temperature_target_candidates_c_in_priority_order"]:
        matches = {}
        all_match = True
        for name, schedule in config["preconditioning_profiles"].items():
            last_switch = schedule[-1][0]
            eligible = [
                row for row in by_profile[name]
                if row["elapsed_s"] >= config["minimum_eligible_time_s"]
                and row["elapsed_s"] >= last_switch + config["minimum_time_after_last_power_switch_s"]
                and row["rack_01_power_kw"] == config["branch_protocol"]["background_rack_kw_each"]
            ]
            if not eligible:
                all_match = False
                matches[name] = {"eligible": False}
                continue
            best = min(eligible, key=lambda row: (abs(row["rack_01_coolant_c"] - target), row["elapsed_s"]))
            error = best["rack_01_coolant_c"] - target
            matches[name] = {
                "eligible": True,
                "time_s": best["elapsed_s"],
                "target_rack_01_coolant_c": best["rack_01_coolant_c"],
                "error_from_target_c": error,
                "within_tolerance": abs(error) <= tolerance,
                "cdu_01_primary_supply_c": best["cdu_01_primary_supply_c"],
                "cdu_01_primary_return_c": best["cdu_01_primary_return_c"],
                "primary_flow_gpm": best["datacenter_primary_flow_gpm"],
            }
            all_match = all_match and abs(error) <= tolerance
        candidates[str(target)] = matches
        if all_match and selected is None:
            selected = {"target_c": target, "matches": matches}

    selection = {
        "status": "matched" if selected else "no_common_match; no branch experiment authorized under preregistration",
        "selected": selected,
        "all_candidate_results": candidates,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "preregistration_sha256": sha256(prereg_path),
        "frozen_model_sha256": sha256(model_path),
        "feasibility_script_sha256": sha256(Path(__file__)),
        "fmu_sha256": sha256(FMU),
        "feasibility_preconditioning_sha256": sha256(trace_path),
        "sample_count": len(rows),
    }
    (ROOT / "match_selection.json").write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": selection["status"], "selected": selected, "candidate_results": candidates}, indent=2))


if __name__ == "__main__":
    main()
