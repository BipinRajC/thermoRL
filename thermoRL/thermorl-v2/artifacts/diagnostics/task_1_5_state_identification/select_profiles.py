"""Preconditioning-only candidate search and fixed six-state design selection."""

from __future__ import annotations

import csv
import hashlib
import itertools
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interval_power(spec: dict, interval_start_s: int, switched_at_s: int | None) -> float:
    if spec["kind"] == "constant" or interval_start_s < spec["start_s"] or switched_at_s is not None:
        return 10.86
    return float(spec["pulse_kw_each_rack"])


def select_design(feasible: dict[str, dict], count: int) -> tuple[list[str], dict]:
    names = sorted(feasible)
    min_return = min(names, key=lambda name: (feasible[name]["selected"]["cdu_01_primary_return_c"], name))
    max_return = max(names, key=lambda name: (feasible[name]["selected"]["cdu_01_primary_return_c"], name))
    features = np.asarray([[feasible[name]["selected"][key] for key in (
        "cdu_01_primary_return_c", "rack_01_slope_k_per_min", "datacenter_primary_flow_gpm",
    )] for name in names])
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std[std == 0] = 1.0
    scaled = (features - mean) / std
    design = {name: np.concatenate(([1.0], scaled[index])) for index, name in enumerate(names)}
    choices = []
    for subset in itertools.combinations(names, count):
        if min_return not in subset or max_return not in subset:
            continue
        matrix = np.asarray([design[name] for name in subset])
        sign, logdet = np.linalg.slogdet(matrix.T @ matrix)
        score = float(logdet) if sign > 0 else float("-inf")
        choices.append((score, subset))
    best_score = max(score for score, _ in choices)
    best = min(subset for score, subset in choices if score == best_score)
    raw = np.asarray([[feasible[name]["selected"][key] for key in (
        "cdu_01_primary_return_c", "rack_01_slope_k_per_min", "datacenter_primary_flow_gpm",
    )] for name in best])
    correlation = np.corrcoef(raw, rowvar=False)
    matrix = np.asarray([design[name] for name in best])
    info = {
        "minimum_return_profile": min_return,
        "maximum_return_profile": max_return,
        "selected_log_determinant": best_score,
        "selected_design_rank": int(np.linalg.matrix_rank(matrix)),
        "selected_design_condition_number": float(np.linalg.cond(matrix)),
        "selected_predictor_correlation_matrix": correlation.tolist(),
        "candidate_count": len(names),
        "feasible_subset_count": len(choices),
    }
    return list(best), info


def main() -> None:
    config_path = ROOT / "preregistration.json"
    config = json.loads(config_path.read_text())
    ambient = Ambient()
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    initial_handle = backend.save_state()
    traces = []
    candidates = {}
    dt = config["communication_interval_s"]
    target = config["target_rack_01_coolant_c"]
    tol = config["match_tolerance_c"]
    try:
        def capture(name: str, elapsed: float, power: float, previous_t: float | None) -> dict:
            th = backend.observe()
            gl = backend.global_observe()
            temperature = float(th.t_c[0])
            return {
                "profile": name,
                "elapsed_s": elapsed,
                "fmu_time_s": backend.time_s,
                "power_applied_during_preceding_interval_kw_each_rack": power,
                "rack_01_coolant_c": temperature,
                "rack_01_slope_k_per_min": None if previous_t is None else (temperature - previous_t) / dt * 60.0,
                "cdu_01_primary_supply_c": float(th.extras["T_prim_s_C"][0]),
                "cdu_01_primary_return_c": float(th.extras["T_prim_r_C"][0]),
                "datacenter_primary_flow_gpm": float(gl["fmu.V_flow_prim_GPM"]),
            }

        for name, spec in config["candidate_profiles"].items():
            backend.restore_state(initial_handle)
            switched_at = None
            first_match = None
            rows = [capture(name, 0.0, 10.86, None)]
            for tick in range(1, config["max_preconditioning_s"] // dt + 1):
                interval_start = (tick - 1) * dt
                power = interval_power(spec, interval_start, switched_at)
                backend.step(np.full(coupling.num_cdus, power), dt, ambient)
                now = tick * dt
                row = capture(name, float(now), power, rows[-1]["rack_01_coolant_c"])
                rows.append(row)
                if switched_at is None and spec["kind"] == "high" and power != 10.86 and row["rack_01_coolant_c"] >= 32.1:
                    switched_at = now
                if switched_at is None and spec["kind"] == "low" and power != 10.86 and row["rack_01_coolant_c"] <= 32.1:
                    switched_at = now
                eligible = (
                    now >= 600
                    and (spec["kind"] == "constant" or switched_at is not None)
                    and now >= (switched_at or 0) + dt
                    and power == 10.86
                )
                if eligible and abs(row["rack_01_coolant_c"] - target) <= tol and first_match is None:
                    first_match = now
                if first_match is not None and now >= first_match + 200:
                    break
            traces.extend(rows)
            eligible_rows = [row for row in rows if first_match is not None
                and first_match <= row["elapsed_s"] <= first_match + 200
                and row["power_applied_during_preceding_interval_kw_each_rack"] == 10.86
                and abs(row["rack_01_coolant_c"] - target) <= tol]
            selected = min(eligible_rows, key=lambda row: (abs(row["rack_01_coolant_c"] - target), row["elapsed_s"])) if eligible_rows else None
            candidates[name] = {
                "spec": spec,
                "switch_back_time_s": switched_at,
                "first_match_time_s": first_match,
                "selected": selected,
                "rows_recorded": len(rows),
            }
    finally:
        backend.free_state(initial_handle)
        backend.close()

    trace_path = ROOT / "candidate_preconditioning.csv"
    with trace_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(traces[0]))
        writer.writeheader()
        writer.writerows(traces)
    feasible = {name: candidate for name, candidate in candidates.items() if candidate["selected"] is not None}
    if len(feasible) >= 6:
        count = 6
    elif len(feasible) == 5:
        count = 5
    else:
        count = 0
    selected_names, design_info = select_design(feasible, count) if count else ([], {})
    result = {
        "status": "selected" if selected_names else "fewer_than_five_matches_no_step_branches",
        "selected_profiles": selected_names,
        "selected_count": count,
        "design_info": design_info,
        "all_candidates": candidates,
        "preregistration_sha256": sha256(config_path),
        "selection_script_sha256": sha256(Path(__file__)),
        "fmu_sha256": sha256(FMU),
        "candidate_trace_sha256": sha256(trace_path),
        "candidate_trace_rows": len(traces),
    }
    (ROOT / "selection.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "selected_profiles": selected_names,
        "design_info": design_info,
        "candidate_states": {name: {"switch": v["switch_back_time_s"], "selected": v["selected"]} for name, v in candidates.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
