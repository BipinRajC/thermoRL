"""Six-state paired sweep with frozen coolant-only predictions and full ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from subprocess import check_output
from time import perf_counter

import numpy as np
from raps.system_config import get_system_config

from select_profiles import CDU_VARS, interval_power
from select_profiles_spatial import powers as spatial_powers
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
FROZEN_PATH = ROOT.parent / "task_1_5_off_trajectory/frozen_coolant_only_model.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def predict(fit: dict, x: float) -> float:
    return fit["intercept"] + fit["standardized_slope"] * (x - fit["predictor_mean_c"]) / fit["predictor_std_c"]


def metric(rows: list[dict], column: str) -> dict:
    peak = max(rows, key=lambda row: row[column])
    minimum = min(rows, key=lambda row: row[column])
    return {
        "final_increment": rows[-1][column],
        "peak_increment": peak[column],
        "time_of_window_max_s": peak["elapsed_s"],
        "max_at_horizon": peak["elapsed_s"] == rows[-1]["elapsed_s"],
        "minimum_increment": minimum[column],
        "time_of_window_min_s": minimum["elapsed_s"],
        "peak_minus_final": peak[column] - rows[-1][column],
    }


def profile_power(name: str, spec: dict, start_s: int, switched_at: int | None, original: dict) -> np.ndarray:
    if name in original:
        return np.full(44, interval_power(spec, start_s, switched_at))
    return spatial_powers(spec, start_s, switched_at)


def update_switch(name: str, spec: dict, now: int, applied: np.ndarray, target_c: float, current: int | None, original: dict) -> int | None:
    if current is not None:
        return current
    if name in original:
        if spec["kind"] == "high" and applied[0] != 10.86 and target_c >= 32.1:
            return now
        if spec["kind"] == "low" and applied[0] != 10.86 and target_c <= 32.1:
            return now
    else:
        if "fixed_end_s" in spec and now == spec["fixed_end_s"]:
            return now
        if "end_rule" in spec and applied[0] != 10.86:
            if (spec["power_kw"] > 10.86 and target_c >= 32.1) or (spec["power_kw"] < 10.86 and target_c <= 32.1):
                return now
    return current


def run(run_name: str) -> None:
    prereg_path = ROOT / "preregistration.json"
    spatial_path = ROOT / "preregistration_spatial_addendum.json"
    selection_path = ROOT / "selection_spatial.json"
    prereg = json.loads(prereg_path.read_text())
    selection = json.loads(selection_path.read_text())
    frozen = json.loads(FROZEN_PATH.read_text())
    assert selection["status"] == "selected" and len(selection["selected_profiles"]) == 6
    assert selection["spatial_preregistration_sha256"] == sha256(spatial_path)
    assert selection["original_selection_sha256"] == sha256(ROOT / "selection.json")
    dt = prereg["communication_interval_s"]
    horizon = prereg["branch_protocol"]["duration_s"]
    ambient = Ambient(t_air_k=prereg["branch_protocol"]["ambient_air_k"], t_ext_k=prereg["branch_protocol"]["ambient_external_k"])
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    heat_keys = power_input_names(coupling)
    background = np.full(44, 10.86)
    stepped = background.copy()
    stepped[0] = 40.0
    coolant = [f"rack_{i:02d}_coolant_c" for i in range(1, 45)]
    supply = [f"cdu_{i:02d}_primary_supply_c" for i in range(1, 45)]
    ret = [f"cdu_{i:02d}_primary_return_c" for i in range(1, 45)]
    power_cols = [f"rack_{i:02d}_power_kw" for i in range(1, 45)]
    heat_cols = [f"rack_{i:02d}_fmu_heat_input_w" for i in range(1, 45)]
    thermal = coolant + supply + ret + ["datacenter_primary_flow_gpm"]
    preconditioning = []
    branches = []
    responses = []
    predictions = []
    summaries = {}
    start_wall = perf_counter()
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    initial_handle = backend.save_state()
    try:
        def capture(elapsed: float, applied: np.ndarray) -> dict:
            th = backend.observe()
            gl = backend.global_observe()
            inputs = rack_kw_to_fmu_inputs(applied, coupling, ambient)
            row = {"elapsed_s": elapsed, "fmu_time_s": backend.time_s}
            row.update(zip(coolant, map(float, th.t_c)))
            row.update(zip(supply, map(float, th.extras["T_prim_s_C"])))
            row.update(zip(ret, map(float, th.extras["T_prim_r_C"])))
            row.update(zip(power_cols, map(float, applied)))
            row.update(zip(heat_cols, (float(inputs[key]) for key in heat_keys)))
            row["datacenter_primary_flow_gpm"] = float(gl["fmu.V_flow_prim_GPM"])
            return row

        for name in selection["selected_profiles"]:
            candidate = selection["all_candidates"][name]
            spec = candidate["spec"]
            chosen = candidate["selected"]
            target_time = int(chosen["elapsed_s"])
            backend.restore_state(initial_handle)
            switched_at = None
            state_rows = [capture(0.0, background)]
            for tick in range(1, target_time // dt + 1):
                start = (tick - 1) * dt
                applied = profile_power(name, spec, start, switched_at, prereg["candidate_profiles"])
                backend.step(applied, dt, ambient)
                now = tick * dt
                row = capture(float(now), applied)
                state_rows.append(row)
                switched_at = update_switch(name, spec, now, applied, row[coolant[0]], switched_at, prereg["candidate_profiles"])
            initial = state_rows[-1]
            if switched_at != candidate["switch_back_time_s"]:
                raise ValueError(f"{name}: preconditioning switch changed")
            for column, pilot_key in (
                (coolant[0], "rack_01_coolant_c"),
                (supply[0], "cdu_01_primary_supply_c"),
                (ret[0], "cdu_01_primary_return_c"),
                ("datacenter_primary_flow_gpm", "datacenter_primary_flow_gpm"),
            ):
                if abs(initial[column] - chosen[pilot_key]) > 1e-8:
                    raise ValueError(f"{name}: selected state changed at {column}")
            if abs(initial[coolant[0]] - 32.0) > 0.1 or any(initial[column] != 10.86 for column in power_cols):
                raise ValueError(f"{name}: branch current state does not satisfy match")
            preconditioning.extend({"profile": name, **row} for row in state_rows)
            state_handle = backend.save_state()
            try:
                paired_branches = {}
                for branch, applied in (("control", background), ("step", stepped)):
                    backend.restore_state(state_handle)
                    rows = [capture(0.0, background)]
                    for tick in range(1, horizon // dt + 1):
                        backend.step(applied, dt, ambient)
                        rows.append(capture(float(tick * dt), applied))
                    paired_branches[branch] = rows
                    branches.extend({"profile": name, "branch": branch, **row} for row in rows)
                if paired_branches["control"][0] != paired_branches["step"][0]:
                    raise ValueError(f"{name}: branch-time observation mismatch")
                if paired_branches["control"][0] != {**initial, "elapsed_s": 0.0}:
                    raise ValueError(f"{name}: saved state differs from preconditioning")
                effect_rows = []
                prediction_rows = []
                initial_t = initial[coolant[0]]
                for held, step, curve_model in zip(paired_branches["control"], paired_branches["step"], frozen["curve_models"]):
                    if held["elapsed_s"] != step["elapsed_s"] or step["elapsed_s"] != curve_model["elapsed_s"]:
                        raise ValueError("Time axes differ")
                    effect = {"elapsed_s": step["elapsed_s"]}
                    effect.update({column: step[column] - held[column] for column in thermal})
                    effect_rows.append(effect)
                    estimated = predict(curve_model, initial_t)
                    prediction_rows.append({
                        "elapsed_s": step["elapsed_s"],
                        "initial_target_c": initial_t,
                        "observed_paired_rack_01_c": effect[coolant[0]],
                        "frozen_curve_prediction_c": estimated,
                        "curve_signed_residual_c": effect[coolant[0]] - estimated,
                    })
                responses.extend({"profile": name, **row} for row in effect_rows)
                predictions.extend({"profile": name, **row} for row in prediction_rows)
                target_metric = metric(effect_rows, coolant[0])
                peak_time = target_metric["time_of_window_max_s"]
                peak_at_time_prediction = next(row["frozen_curve_prediction_c"] for row in prediction_rows if row["elapsed_s"] == peak_time)
                scalar_peak_prediction = predict(frozen["scalar_models"]["paired_peak_increment_c"], initial_t)
                scalar_final_prediction = predict(frozen["scalar_models"]["paired_final_increment_c"], initial_t)
                curve_abs = [abs(row["curve_signed_residual_c"]) for row in prediction_rows]
                absolute_step_peak = max(paired_branches["step"], key=lambda row: row[coolant[0]])
                summaries[name] = {
                    "saved_fmu_time_s": target_time,
                    "switch_back_time_s": switched_at,
                    "branch_initial_observations_match_exactly": True,
                    "initial_rack_coolant_c": [initial[column] for column in coolant],
                    "initial_cdu_primary_supply_c": [initial[column] for column in supply],
                    "initial_cdu_primary_return_c": [initial[column] for column in ret],
                    "initial_primary_flow_gpm": initial["datacenter_primary_flow_gpm"],
                    "initial_power_kw": [initial[column] for column in power_cols],
                    "initial_fmu_heat_input_w": [initial[column] for column in heat_cols],
                    "one_tick_target_slope_k_per_min": (initial[coolant[0]] - state_rows[-2][coolant[0]]) / dt * 60.0,
                    "target_paired_response": target_metric,
                    "absolute_step_peak_c": absolute_step_peak[coolant[0]],
                    "absolute_step_peak_time_s": absolute_step_peak["elapsed_s"],
                    "cdu_01_primary_supply_response": metric(effect_rows, supply[0]),
                    "cdu_01_primary_return_response": metric(effect_rows, ret[0]),
                    "neighbor_final_increment_range_c": [min(effect_rows[-1][column] for column in coolant[1:]), max(effect_rows[-1][column] for column in coolant[1:])],
                    "neighbor_max_abs_increment_c": max(abs(row[column]) for row in effect_rows for column in coolant[1:]),
                    "frozen_coolant_model": {
                        "predicted_final_increment_c": scalar_final_prediction,
                        "signed_final_residual_c": target_metric["final_increment"] - scalar_final_prediction,
                        "predicted_peak_increment_c": scalar_peak_prediction,
                        "peak_to_peak_scalar_residual_c": target_metric["peak_increment"] - scalar_peak_prediction,
                        "curve_residual_at_observed_peak_time_c": target_metric["peak_increment"] - peak_at_time_prediction,
                        "curve_time_integrated_mean_abs_error_c": float(np.trapezoid(curve_abs, [row["elapsed_s"] for row in prediction_rows]) / horizon),
                        "curve_max_abs_error_c": max(curve_abs),
                        "curve_max_abs_error_time_s": prediction_rows[int(np.argmax(curve_abs))]["elapsed_s"],
                    },
                }
            finally:
                backend.free_state(state_handle)
        runtime = {"wall_until_last_sample_s": perf_counter() - start_wall, "fmu_calls_s": backend.runtime_s()}
    finally:
        backend.free_state(initial_handle)
        backend.close()

    output_dir = ROOT / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "preconditioning": output_dir / "preconditioning.csv",
        "branch_ledger": output_dir / "branch_ledger.csv",
        "response_ledger": output_dir / "response_ledger.csv",
        "frozen_prediction_ledger": output_dir / "frozen_prediction_ledger.csv",
    }
    write_csv(paths["preconditioning"], preconditioning)
    write_csv(paths["branch_ledger"], branches)
    write_csv(paths["response_ledger"], responses)
    write_csv(paths["frozen_prediction_ledger"], predictions)
    metadata = {
        "experiment": "preregistered six-state identification sweep; no acceptance threshold",
        "run_name": run_name,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "source_sha256": {
            "run_script": sha256(Path(__file__)),
            "original_preregistration": sha256(prereg_path),
            "spatial_addendum": sha256(spatial_path),
            "profile_selection": sha256(selection_path),
            "frozen_coolant_model": sha256(FROZEN_PATH),
            "uniform_profile_source": sha256(ROOT / "select_profiles.py"),
            "spatial_profile_source": sha256(ROOT / "select_profiles_spatial.py"),
            "backend": sha256(PROJECT / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT / "tests/fmu/test_fmu_backend.py"),
        },
        "fmu_sha256": sha256(FMU),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "fmpy_version": version("fmpy"),
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "selected_profiles": selection["selected_profiles"],
        "design_info": selection["design_info"],
        "profiles": summaries,
        "runtime": runtime,
        "row_counts": {"preconditioning": len(preconditioning), "branches": len(branches), "responses": len(responses), "predictions": len(predictions)},
        "file_sha256": {name: sha256(path) for name, path in paths.items()},
    }
    (output_dir / "metrics_and_provenance.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "run": run_name,
        "rows": metadata["row_counts"],
        "selected_profiles": selection["selected_profiles"],
        "results": {name: {
            "initial_t_c": state["initial_rack_coolant_c"][0],
            "initial_return_c": state["initial_cdu_primary_return_c"][0],
            "slope_k_per_min": state["one_tick_target_slope_k_per_min"],
            "flow_gpm": state["initial_primary_flow_gpm"],
            "paired_final_c": state["target_paired_response"]["final_increment"],
            "paired_peak_c": state["target_paired_response"]["peak_increment"],
            "frozen_final_residual_c": state["frozen_coolant_model"]["signed_final_residual_c"],
        } for name, state in summaries.items()},
        "file_sha256": metadata["file_sha256"],
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", choices=("run_01", "run_02"))
    args = parser.parse_args()
    run(args.run_name)
