"""Paired off-trajectory transfer test with frozen coolant-only predictions."""

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

from find_matches_v3 import CDU_VARS, profile_power
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
PROFILES = ("constant_hold", "late_high_then_base", "low_then_raised_base")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def predict(model: dict, coolant_c: float) -> float:
    return model["intercept"] + model["standardized_slope"] * (
        coolant_c - model["predictor_mean_c"]
    ) / model["predictor_std_c"]


def response_metric(rows: list[dict], column: str) -> dict:
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


def run(run_name: str) -> None:
    prereg_path = ROOT / "preregistration.json"
    v2_path = ROOT / "preregistration_v2.json"
    v3_path = ROOT / "preregistration_v3.json"
    selection_path = ROOT / "match_selection_v3.json"
    model_path = ROOT / "frozen_coolant_only_model.json"
    base = json.loads(prereg_path.read_text())
    v2 = json.loads(v2_path.read_text())
    v3 = json.loads(v3_path.read_text())
    selected = json.loads(selection_path.read_text())
    model = json.loads(model_path.read_text())
    assert selected["status"] == "matched"
    assert selected["preregistration_v3_sha256"] == sha256(v3_path)
    assert selected["frozen_model_sha256"] == sha256(model_path)
    assert model["preregistration_sha256"] == sha256(prereg_path)
    assert v3["inherits_preregistration_v2_sha256"] == sha256(v2_path)
    protocol = base["branch_protocol"]
    dt = protocol["communication_interval_s"]
    horizon = protocol["horizon_s"]
    ambient = Ambient(t_air_k=protocol["ambient_air_k"], t_ext_k=protocol["ambient_external_k"])
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    heat_keys = power_input_names(coupling)
    background = np.full(coupling.num_cdus, protocol["background_rack_kw_each"], dtype=np.float64)
    stepped = background.copy()
    stepped[0] = protocol["rack_01_step_kw"]
    rack_names = [f"rack_{i:02d}_coolant_c" for i in range(1, 45)]
    supply_names = [f"cdu_{i:02d}_primary_supply_c" for i in range(1, 45)]
    return_names = [f"cdu_{i:02d}_primary_return_c" for i in range(1, 45)]
    power_names = [f"rack_{i:02d}_power_kw" for i in range(1, 45)]
    heat_names = [f"rack_{i:02d}_fmu_heat_input_w" for i in range(1, 45)]
    thermal_names = rack_names + supply_names + return_names + ["datacenter_primary_flow_gpm"]
    all_preconditioning = []
    all_branches = []
    all_responses = []
    all_predictions = []
    summaries = {}
    start_wall = perf_counter()
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    initial_handle = backend.save_state()
    try:
        def capture(elapsed: float, power_kw: np.ndarray) -> dict:
            thermal = backend.observe()
            globals_ = backend.global_observe()
            inputs = rack_kw_to_fmu_inputs(power_kw, coupling, ambient)
            row = {"elapsed_s": elapsed, "fmu_time_s": backend.time_s}
            row.update(zip(rack_names, map(float, thermal.t_c)))
            row.update(zip(supply_names, map(float, thermal.extras["T_prim_s_C"])))
            row.update(zip(return_names, map(float, thermal.extras["T_prim_r_C"])))
            row.update(zip(power_names, map(float, power_kw)))
            row.update(zip(heat_names, (float(inputs[key]) for key in heat_keys)))
            row["datacenter_primary_flow_gpm"] = float(globals_["fmu.V_flow_prim_GPM"])
            return row

        for name in PROFILES:
            backend.restore_state(initial_handle)
            target_time = int(selected["selected"][name]["selected"]["elapsed_s"])
            switched_at = None
            precondition = [capture(0.0, background)]
            for tick in range(1, target_time // dt + 1):
                interval_start = (tick - 1) * dt
                power = profile_power(name, interval_start, switched_at)
                powers = np.full(coupling.num_cdus, power)
                backend.step(powers, dt, ambient)
                now = tick * dt
                row = capture(float(now), powers)
                precondition.append(row)
                if name == "late_high_then_base" and switched_at is None and power == 20.0 and row[rack_names[0]] >= v3["late_high_switch_threshold_c"]:
                    switched_at = now
                if name == "low_then_raised_base" and switched_at is None and power == 5.0 and row[rack_names[0]] <= 32.1:
                    switched_at = now
            pilot = selected["selected"][name]
            initial = precondition[-1]
            if switched_at != pilot["profile_switch_back_time_s"]:
                raise ValueError(f"{name}: power switch changed from feasibility run")
            for column, pilot_key in (
                (rack_names[0], "rack_01_coolant_c"),
                (supply_names[0], "cdu_01_primary_supply_c"),
                (return_names[0], "cdu_01_primary_return_c"),
                ("datacenter_primary_flow_gpm", "datacenter_primary_flow_gpm"),
            ):
                expected = pilot["selected"].get(pilot_key, pilot["selected"].get("primary_flow_gpm"))
                if abs(initial[column] - expected) > 1e-8:
                    raise ValueError(f"{name}: selected state differs from feasibility run at {column}")
            if abs(initial[rack_names[0]] - v2["target_rack_01_coolant_c"]) > v2["target_match_tolerance_c"]:
                raise ValueError(f"{name}: rack temperature match failed")
            if not all(initial[key] == 10.86 for key in power_names):
                raise ValueError(f"{name}: current rack power is not the common background")
            all_preconditioning.extend({"profile": name, **row} for row in precondition)
            state_handle = backend.save_state()
            try:
                branch_rows = {}
                for branch, power_kw in (("control", background), ("step", stepped)):
                    backend.restore_state(state_handle)
                    rows = [capture(0.0, background)]
                    for tick in range(1, horizon // dt + 1):
                        backend.step(power_kw, dt, ambient)
                        rows.append(capture(float(tick * dt), power_kw))
                    branch_rows[branch] = rows
                    all_branches.extend({"profile": name, "branch": branch, **row} for row in rows)
                if branch_rows["control"][0] != branch_rows["step"][0]:
                    raise ValueError(f"{name}: branch-time observation mismatch")
                if branch_rows["control"][0] != {**initial, "elapsed_s": 0.0}:
                    raise ValueError(f"{name}: saved state differs from preconditioning")
                responses = []
                predictions = []
                target_t = initial[rack_names[0]]
                for control, step, curve_model in zip(branch_rows["control"], branch_rows["step"], model["curve_models"]):
                    if control["elapsed_s"] != step["elapsed_s"] or step["elapsed_s"] != curve_model["elapsed_s"]:
                        raise ValueError("Time axes differ")
                    response = {"elapsed_s": step["elapsed_s"]}
                    response.update({column: step[column] - control[column] for column in thermal_names})
                    responses.append(response)
                    prediction = predict(curve_model, target_t)
                    predictions.append({
                        "elapsed_s": step["elapsed_s"],
                        "initial_target_c": target_t,
                        "observed_paired_rack_01_c": response[rack_names[0]],
                        "frozen_model_predicted_c": prediction,
                        "signed_residual_c": response[rack_names[0]] - prediction,
                    })
                all_responses.extend({"profile": name, **row} for row in responses)
                all_predictions.extend({"profile": name, **row} for row in predictions)
                target_metric = response_metric(responses, rack_names[0])
                raw_peak = max(branch_rows["step"], key=lambda row: row[rack_names[0]])
                final_prediction = predict(model["scalar_models"]["paired_final_increment_c"], target_t)
                peak_prediction = predict(model["scalar_models"]["paired_peak_increment_c"], target_t)
                error_values = [abs(row["signed_residual_c"]) for row in predictions]
                neighbors = rack_names[1:]
                summaries[name] = {
                    "profile_switch_back_time_s": switched_at,
                    "saved_fmu_time_s": target_time,
                    "branch_initial_observations_match_exactly": True,
                    "initial_rack_coolant_c": [initial[column] for column in rack_names],
                    "initial_cdu_primary_supply_c": [initial[column] for column in supply_names],
                    "initial_cdu_primary_return_c": [initial[column] for column in return_names],
                    "initial_primary_flow_gpm": initial["datacenter_primary_flow_gpm"],
                    "initial_power_kw": [initial[column] for column in power_names],
                    "initial_fmu_heat_input_w": [initial[column] for column in heat_names],
                    "target_one_tick_slope_k_per_min": (initial[rack_names[0]] - precondition[-2][rack_names[0]]) / dt * 60.0,
                    "target_paired_response": target_metric,
                    "target_raw_step_peak_c": raw_peak[rack_names[0]],
                    "target_raw_step_peak_time_s": raw_peak["elapsed_s"],
                    "cdu_01_primary_supply_response": response_metric(responses, supply_names[0]),
                    "cdu_01_primary_return_response": response_metric(responses, return_names[0]),
                    "neighbor_final_increment_range_c": [min(responses[-1][column] for column in neighbors), max(responses[-1][column] for column in neighbors)],
                    "neighbor_max_abs_increment_c": max(abs(row[column]) for row in responses for column in neighbors),
                    "frozen_model_scalar_predictions": {
                        "paired_final_increment_c": final_prediction,
                        "paired_final_signed_residual_c": target_metric["final_increment"] - final_prediction,
                        "paired_peak_increment_c": peak_prediction,
                        "paired_peak_signed_residual_c": target_metric["peak_increment"] - peak_prediction,
                    },
                    "frozen_model_curve_errors": {
                        "time_average_absolute_c": float(np.trapezoid(error_values, [row["elapsed_s"] for row in predictions]) / horizon),
                        "maximum_absolute_c": max(error_values),
                        "maximum_absolute_time_s": predictions[int(np.argmax(error_values))]["elapsed_s"],
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
        "prediction_ledger": output_dir / "prediction_ledger.csv",
    }
    write_csv(paths["preconditioning"], all_preconditioning)
    write_csv(paths["branch_ledger"], all_branches)
    write_csv(paths["response_ledger"], all_responses)
    write_csv(paths["prediction_ledger"], all_predictions)
    metadata = {
        "experiment": "off-trajectory frozen coolant-only transfer test; no acceptance threshold",
        "run_name": run_name,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "source_sha256": {
            "run_script": sha256(Path(__file__)),
            "original_preregistration": sha256(prereg_path),
            "profile_revision_v2": sha256(v2_path),
            "profile_revision_v3": sha256(v3_path),
            "match_selection_v3": sha256(selection_path),
            "frozen_model": sha256(model_path),
            "profile_power_source": sha256(ROOT / "find_matches_v3.py"),
            "backend": sha256(PROJECT / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT / "tests/fmu/test_fmu_backend.py"),
            "lassen_config": sha256(REPO / "sim-raps/config/lassen.yaml"),
        },
        "fmu_sha256": sha256(FMU),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "fmpy_version": version("fmpy"),
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "protocol": protocol,
        "profiles": summaries,
        "runtime": runtime,
        "row_counts": {"preconditioning": len(all_preconditioning), "branches": len(all_branches), "responses": len(all_responses), "predictions": len(all_predictions)},
        "file_sha256": {name: sha256(path) for name, path in paths.items()},
    }
    (output_dir / "metrics_and_provenance.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "run": run_name,
        "rows": metadata["row_counts"],
        "profiles": {name: {
            "time_s": values["saved_fmu_time_s"],
            "initial_target_c": values["initial_rack_coolant_c"][0],
            "initial_slope_k_per_min": values["target_one_tick_slope_k_per_min"],
            "paired_final_c": values["target_paired_response"]["final_increment"],
            "final_signed_residual_c": values["frozen_model_scalar_predictions"]["paired_final_signed_residual_c"],
            "peak_signed_residual_c": values["frozen_model_scalar_predictions"]["paired_peak_signed_residual_c"],
            "curve_time_avg_abs_error_c": values["frozen_model_curve_errors"]["time_average_absolute_c"],
        } for name, values in summaries.items()},
        "file_sha256": metadata["file_sha256"],
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", choices=("run_01", "run_02"))
    args = parser.parse_args()
    run(args.run_name)
