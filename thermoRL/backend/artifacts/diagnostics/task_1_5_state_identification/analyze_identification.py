"""Run only preregistered leave-one-profile-out response regressions."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "preregistration.json"
SELECTION_PATH = ROOT / "selection_spatial.json"
RUN_PATH = ROOT / "run_01/metrics_and_provenance.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def loo_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    predictions = np.empty(len(y))
    for holdout in range(len(y)):
        keep = np.arange(len(y)) != holdout
        train = x[keep]
        center = train.mean(axis=0)
        spread = train.std(axis=0)
        spread[spread == 0] = 1.0
        scaled = (train - center) / spread
        test = (x[holdout] - center) / spread
        response_center = y[keep].mean()
        coefficients = np.linalg.solve(
            scaled.T @ scaled + alpha * np.eye(x.shape[1]),
            scaled.T @ (y[keep] - response_center),
        )
        predictions[holdout] = response_center + test @ coefficients
    return predictions


def main() -> None:
    config = json.loads(PREREG_PATH.read_text())
    selection = json.loads(SELECTION_PATH.read_text())
    metadata = json.loads(RUN_PATH.read_text())
    repeat = json.loads((ROOT / "repeat_verification.json").read_text())
    assert repeat["all_csv_byte_identical"] is True
    assert metadata["source_sha256"]["original_preregistration"] == sha256(PREREG_PATH)
    assert metadata["source_sha256"]["profile_selection"] == sha256(SELECTION_PATH)
    rows = []
    for name in selection["selected_profiles"]:
        state = metadata["profiles"][name]
        response = state["target_paired_response"]
        frozen = state["frozen_coolant_model"]
        rows.append({
            "profile": name,
            "state_time_s": state["saved_fmu_time_s"],
            "rack_01_coolant_c": state["initial_rack_coolant_c"][0],
            "rack_01_coolant_slope_k_per_min": state["one_tick_target_slope_k_per_min"],
            "cdu_01_primary_supply_c": state["initial_cdu_primary_supply_c"][0],
            "cdu_01_primary_return_c": state["initial_cdu_primary_return_c"][0],
            "datacenter_primary_flow_gpm": state["initial_primary_flow_gpm"],
            "mean_other_rack_coolant_c": float(np.mean(state["initial_rack_coolant_c"][1:])),
            "final_paired_increment_c": response["final_increment"],
            "peak_paired_increment_c": response["peak_increment"],
            "peak_time_s": response["time_of_window_max_s"],
            "peak_at_horizon": response["max_at_horizon"],
            "absolute_step_peak_c": state["absolute_step_peak_c"],
            "absolute_step_peak_time_s": state["absolute_step_peak_time_s"],
            "frozen_coolant_predicted_final_c": frozen["predicted_final_increment_c"],
            "frozen_coolant_signed_final_residual_c": frozen["signed_final_residual_c"],
            "frozen_coolant_predicted_peak_c": frozen["predicted_peak_increment_c"],
            "peak_to_peak_scalar_residual_c": frozen["peak_to_peak_scalar_residual_c"],
            "curve_residual_at_observed_peak_time_c": frozen["curve_residual_at_observed_peak_time_c"],
            "curve_time_mean_abs_error_c": frozen["curve_time_integrated_mean_abs_error_c"],
            "curve_max_abs_error_c": frozen["curve_max_abs_error_c"],
            "cdu_01_return_paired_final_c": state["cdu_01_primary_return_response"]["final_increment"],
            "cdu_01_return_paired_peak_c": state["cdu_01_primary_return_response"]["peak_increment"],
            "neighbor_max_abs_increment_c": state["neighbor_max_abs_increment_c"],
        })
    table_path = ROOT / "state_observables_and_outcomes.csv"
    write_csv(table_path, rows)

    models = config["regression"]["fixed_models"]
    outcomes = ("final_paired_increment_c", "peak_paired_increment_c")
    residual_rows = []
    aggregate = {}
    for outcome in outcomes:
        y = np.asarray([row[outcome] for row in rows], dtype=float)
        aggregate[outcome] = {}
        for model_name, predictors in models.items():
            x = np.asarray([[row[variable] for variable in predictors] for row in rows], dtype=float)
            predicted = loo_ridge(x, y)
            errors = y - predicted
            aggregate[outcome][model_name] = {
                "predictors": predictors,
                "held_out_mae_c": float(np.mean(np.abs(errors))),
                "held_out_max_abs_error_c": float(np.max(np.abs(errors))),
            }
            for row, observed, estimate, error in zip(rows, y, predicted, errors):
                residual_rows.append({
                    "outcome": outcome,
                    "model": model_name,
                    "held_out_profile": row["profile"],
                    "observed_c": float(observed),
                    "predicted_c": float(estimate),
                    "signed_residual_c": float(error),
                    "absolute_error_c": float(abs(error)),
                })
    residual_path = ROOT / "held_out_residuals.csv"
    write_csv(residual_path, residual_rows)
    predictors = config["regression"]["predictors"]
    raw = np.asarray([[row[name] for name in predictors] for row in rows])
    standardized = (raw - raw.mean(axis=0)) / raw.std(axis=0)
    design = np.column_stack((np.ones(len(rows)), standardized))
    return_values = [row["cdu_01_primary_return_c"] for row in rows]
    final_values = [row["final_paired_increment_c"] for row in rows]
    result = {
        "analysis_script_sha256": sha256(Path(__file__)),
        "preregistration_sha256": sha256(PREREG_PATH),
        "selection_sha256": sha256(SELECTION_PATH),
        "run_01_metadata_sha256": sha256(RUN_PATH),
        "repeat_verification_sha256": sha256(ROOT / "repeat_verification.json"),
        "state_table_sha256": sha256(table_path),
        "held_out_residuals_sha256": sha256(residual_path),
        "n_profiles": len(rows),
        "predictor_names": predictors,
        "predictor_correlation_matrix": np.corrcoef(raw, rowvar=False).tolist(),
        "standardized_design_rank": int(np.linalg.matrix_rank(design)),
        "standardized_design_condition_number": float(np.linalg.cond(design)),
        "return_range_c": [min(return_values), max(return_values)],
        "final_paired_response_range_c": [min(final_values), max(final_values)],
        "aggregate_held_out_errors": aggregate,
        "metric_conventions": {
            "peak_to_peak_scalar_residual_c": "observed maximum paired increment minus frozen scalar model prediction of maximum paired increment",
            "curve_residual_at_observed_peak_time_c": "observed paired increment at its own peak time minus frozen predicted curve at that same time"
        },
        "inference_limit": config["regression"]["inference_limit"],
    }
    (ROOT / "analysis_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "n_profiles": len(rows),
        "return_range_c": result["return_range_c"],
        "final_response_range_c": result["final_paired_response_range_c"],
        "condition_number": result["standardized_design_condition_number"],
        "correlations": result["predictor_correlation_matrix"],
        "held_out_errors": aggregate,
    }, indent=2))


if __name__ == "__main__":
    main()
