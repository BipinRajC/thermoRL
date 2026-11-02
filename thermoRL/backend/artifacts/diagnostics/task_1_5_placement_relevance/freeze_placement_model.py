"""Freeze prospective coolant+flow absolute-peak/final models before scenarios."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
DIAG = ROOT.parent
PREREG = ROOT / "preregistration.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def fit(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> dict:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    z = (x - mean) / scale
    intercept = float(y.mean())
    weights = np.linalg.solve(z.T @ z + alpha * np.eye(x.shape[1]), z.T @ (y - intercept))
    return {
        "predictor_mean": mean.tolist(),
        "predictor_std": scale.tolist(),
        "intercept_c": intercept,
        "standardized_weights": weights.tolist(),
    }


def predict(model: dict, x: np.ndarray) -> float:
    return float(model["intercept_c"] + np.dot((x - model["predictor_mean"]) / model["predictor_std"], model["standardized_weights"]))


def main() -> None:
    config = json.loads(PREREG.read_text())
    original_table = DIAG / "task_1_5_state_sufficiency/state_observables_and_responses.csv"
    original_branches = DIAG / "task_1_5_state_sufficiency/run_01/branch_ledger.csv"
    spatial_table = DIAG / "task_1_5_state_identification/state_observables_and_outcomes.csv"
    spatial_branches = DIAG / "task_1_5_state_identification/run_01/branch_ledger.csv"
    original_final = {}
    for row in read(original_branches):
        if row["branch"] == "step" and float(row["elapsed_s"]) == 3600.0:
            original_final[int(row["state_time_s"])] = float(row["rack_01_coolant_c"])
    spatial_final = {}
    for row in read(spatial_branches):
        if row["branch"] == "step" and float(row["elapsed_s"]) == 3600.0:
            spatial_final[row["profile"]] = float(row["rack_01_coolant_c"])
    training = []
    for row in read(original_table):
        state_time = int(row["state_time_s"])
        if state_time == 60:
            continue
        training.append({
            "source": f"original_{state_time}",
            "candidate_rack_coolant_c": float(row["target_rack_coolant_c"]),
            "datacenter_primary_flow_gpm": float(row["datacenter_primary_flow_gpm"]),
            "absolute_step_branch_peak_c": float(row["absolute_step_peak_c"]),
            "absolute_step_branch_final_c": original_final[state_time],
        })
    for row in read(spatial_table):
        training.append({
            "source": f"spatial_{row['profile']}",
            "candidate_rack_coolant_c": float(row["rack_01_coolant_c"]),
            "datacenter_primary_flow_gpm": float(row["datacenter_primary_flow_gpm"]),
            "absolute_step_branch_peak_c": float(row["absolute_step_peak_c"]),
            "absolute_step_branch_final_c": spatial_final[row["profile"]],
        })
    assert len(training) == config["training_data"]["n_training_states_expected"]
    names = config["training_data"]["predictors"]
    x = np.asarray([[row[name] for name in names] for row in training], dtype=float)
    models = {}
    cv = {}
    for target in config["training_data"]["targets"]:
        y = np.asarray([row[target] for row in training], dtype=float)
        models[target] = fit(x, y)
        residuals = []
        for holdout in range(len(training)):
            keep = np.arange(len(training)) != holdout
            estimate = predict(fit(x[keep], y[keep]), x[holdout])
            residuals.append({"source": training[holdout]["source"], "observed_c": float(y[holdout]), "predicted_c": estimate, "signed_residual_c": float(y[holdout] - estimate)})
        cv[target] = {
            "leave_one_state_out_mae_c": float(np.mean([abs(row["signed_residual_c"]) for row in residuals])),
            "leave_one_state_out_max_abs_error_c": max(abs(row["signed_residual_c"]) for row in residuals),
            "residuals": residuals,
        }
    frozen = {
        "status": "frozen before new placement-scenario FMU runs",
        "preregistration_sha256": sha256(PREREG),
        "source_sha256": {
            "original_table": sha256(original_table),
            "original_branches": sha256(original_branches),
            "spatial_table": sha256(spatial_table),
            "spatial_branches": sha256(spatial_branches),
            "freeze_script": sha256(Path(__file__)),
        },
        "training_rows": training,
        "predictor_names": names,
        "ridge_alpha": 1.0,
        "models": models,
        "internal_leave_one_state_out": cv,
        "ranking_limit": "Primary flow is shared by candidate racks in one state and enters additively, so it cancels from pairwise score differences. This model cannot test flow-specific ranking value."
    }
    path = ROOT / "frozen_placement_model.json"
    path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"path": str(path), "sha256": sha256(path), "models": models, "internal_errors": {k: {n:v for n,v in d.items() if n!='residuals'} for k,d in cv.items()}}, indent=2))


if __name__ == "__main__":
    main()
