"""Analyze only the preregistered eight-state sweep metrics and model ladder."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
PREREG = json.loads((ROOT / "preregistration.json").read_text())
METADATA_PATH = ROOT / "run_01/metrics_and_provenance.json"
METADATA = json.loads(METADATA_PATH.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ridge_loo_predictions(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
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


def verify_raw_metrics() -> None:
    responses = defaultdict(list)
    for row in read_csv(ROOT / "run_01/response_ledger.csv"):
        responses[int(row["state_time_s"])].append(row)
    branches = defaultdict(list)
    for row in read_csv(ROOT / "run_01/branch_ledger.csv"):
        if row["branch"] == "step":
            branches[int(row["state_time_s"])].append(row)
    for state_time in PREREG["state_times_s"]:
        recorded = METADATA["state_metrics"][str(state_time)]
        rows = responses[state_time]
        x = [float(row["rack_01_coolant_c"]) for row in rows]
        times = [float(row["elapsed_s"]) for row in rows]
        first_peak_index = int(np.argmax(x))
        assert abs(recorded["target_paired_response"]["final_increment"] - x[-1]) < 1e-10
        assert abs(recorded["target_paired_response"]["peak_increment"] - x[first_peak_index]) < 1e-10
        assert recorded["target_paired_response"]["time_of_window_max_s"] == times[first_peak_index]
        raw_peak = max(float(row["rack_01_coolant_c"]) for row in branches[state_time])
        assert abs(recorded["target_absolute_step_peak_c"] - raw_peak) < 1e-10


def main() -> None:
    verify_raw_metrics()
    repeat = json.loads((ROOT / "repeat_verification.json").read_text())
    assert repeat["all_csv_byte_identical"] is True
    assert METADATA["source_sha256"]["preregistration"] == sha256(ROOT / "preregistration.json")
    states = PREREG["state_times_s"]
    metrics = METADATA["state_metrics"]
    values = []
    for state_time in states:
        record = metrics[str(state_time)]
        values.append({
            "state_time_s": state_time,
            "target_rack_coolant_c": record["initial_rack_coolant_c"][0],
            "target_rack_coolant_slope_k_per_min": record["target_rack_coolant_slope_k_per_min"],
            "cdu_01_primary_supply_c": record["initial_cdu_primary_supply_c"][0],
            "cdu_01_primary_return_c": record["initial_cdu_primary_return_c"][0],
            "datacenter_primary_flow_gpm": record["initial_datacenter_primary_flow_gpm"],
            "paired_final_increment_c": record["target_paired_response"]["final_increment"],
            "paired_peak_increment_c": record["target_paired_response"]["peak_increment"],
            "paired_time_of_window_max_s": record["target_paired_response"]["time_of_window_max_s"],
            "paired_max_at_horizon": record["target_paired_response"]["window_max_at_horizon"],
            "absolute_step_peak_c": record["target_absolute_step_peak_c"],
            "absolute_step_peak_time_s": record["target_absolute_step_peak_time_s"],
            "cdu_01_return_paired_peak_c": record["cdu_01_primary_return_response"]["peak_increment"],
            "neighbor_max_abs_increment_c": record["neighbor_max_abs_increment_c"],
        })
    table_path = ROOT / "state_observables_and_responses.csv"
    write_csv(table_path, values)

    model_ladder = PREREG["regression"]["model_ladder"]
    target_metrics = list(PREREG["target_response_metrics"])
    alpha = 1.0
    residual_rows = []
    aggregate = {}
    for subset_name, subset_times in (
        ("all_eight", states),
        ("without_60_s_initialization_transient", states[1:]),
    ):
        subset = [row for row in values if row["state_time_s"] in subset_times]
        aggregate[subset_name] = {}
        for response_name in target_metrics:
            y = np.asarray([row[response_name] for row in subset], dtype=np.float64)
            aggregate[subset_name][response_name] = {}
            for model_name, predictors in model_ladder.items():
                x = np.asarray([[row[name] for name in predictors] for row in subset], dtype=np.float64)
                predicted = ridge_loo_predictions(x, y, alpha)
                errors = y - predicted
                aggregate[subset_name][response_name][model_name] = {
                    "n_states": len(subset),
                    "predictors": predictors,
                    "held_out_mae": float(np.mean(np.abs(errors))),
                    "held_out_max_abs_error": float(np.max(np.abs(errors))),
                    "unit": "s" if response_name.endswith("_s") else "degC",
                }
                for row, truth, estimate, error in zip(subset, y, predicted, errors):
                    residual_rows.append({
                        "subset": subset_name,
                        "response_metric": response_name,
                        "model": model_name,
                        "held_out_state_time_s": row["state_time_s"],
                        "paired_max_at_horizon": row["paired_max_at_horizon"],
                        "observed": float(truth),
                        "predicted": float(estimate),
                        "signed_residual": float(error),
                        "absolute_error": float(abs(error)),
                    })
    residual_path = ROOT / "held_out_residuals.csv"
    write_csv(residual_path, residual_rows)
    peak_values = [row["absolute_step_peak_c"] for row in values]
    peak_times = [row["absolute_step_peak_time_s"] for row in values]
    summary = {
        "analysis_script_sha256": sha256(Path(__file__)),
        "preregistration_sha256": sha256(ROOT / "preregistration.json"),
        "run_01_metadata_sha256": sha256(METADATA_PATH),
        "run_01_response_ledger_sha256": sha256(ROOT / "run_01/response_ledger.csv"),
        "repeat_verification_sha256": sha256(ROOT / "repeat_verification.json"),
        "state_table_sha256": sha256(table_path),
        "residual_csv_sha256": sha256(residual_path),
        "regression_method": PREREG["regression"]["method"],
        "aggregate_held_out_errors": aggregate,
        "absolute_step_peak_c_range": [min(peak_values), max(peak_values)],
        "absolute_step_peak_time_s_range": [min(peak_times), max(peak_times)],
        "n_states": len(states),
        "interpretation_limit": PREREG["regression"]["interpretation_limit"],
    }
    (ROOT / "analysis_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "n_states": len(states),
        "absolute_step_peak_c_range": summary["absolute_step_peak_c_range"],
        "absolute_step_peak_time_s_range": summary["absolute_step_peak_time_s_range"],
        "aggregate_held_out_errors": aggregate,
    }, indent=2))


if __name__ == "__main__":
    main()
