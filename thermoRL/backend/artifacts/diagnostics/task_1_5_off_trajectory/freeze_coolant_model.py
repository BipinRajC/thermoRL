"""Freeze the original eight-state coolant-only ridge model before new FMU runs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
TRAIN = ROOT.parent / "task_1_5_state_sufficiency"
PREREG = ROOT / "preregistration.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> dict:
    center = float(x.mean())
    spread = float(x.std())
    z = (x - center) / spread
    intercept = float(y.mean())
    slope = float(np.dot(z, y - intercept) / (np.dot(z, z) + alpha))
    return {"predictor_mean_c": center, "predictor_std_c": spread, "intercept": intercept, "standardized_slope": slope}


def main() -> None:
    config = json.loads(PREREG.read_text())
    table_path = TRAIN / "state_observables_and_responses.csv"
    curve_path = TRAIN / "run_01/response_ledger.csv"
    table = read_csv(table_path)
    states = [int(row["state_time_s"]) for row in table]
    assert states == [60, 120, 600, 1200, 1800, 3600, 5400, 7200]
    x = np.asarray([float(row["target_rack_coolant_c"]) for row in table])
    scalar = {
        name: fit_ridge(x, np.asarray([float(row[name]) for row in table]))
        for name in config["frozen_model"]["scalar_targets"]
    }
    by_time = defaultdict(dict)
    for row in read_csv(curve_path):
        by_time[float(row["elapsed_s"])][int(row["state_time_s"])] = float(row["rack_01_coolant_c"])
    assert len(by_time) == 181
    curve = []
    for elapsed in sorted(by_time):
        assert set(by_time[elapsed]) == set(states)
        fit = fit_ridge(x, np.asarray([by_time[elapsed][state] for state in states]))
        curve.append({"elapsed_s": elapsed, **fit})
    model = {
        "status": "frozen before new FMU preconditioning or step branches",
        "preregistration_sha256": sha256(PREREG),
        "training_table_sha256": sha256(table_path),
        "training_response_ledger_sha256": sha256(curve_path),
        "model_script_sha256": sha256(Path(__file__)),
        "training_state_times_s": states,
        "training_initial_rack_01_c": x.tolist(),
        "ridge_alpha": 1.0,
        "scalar_models": scalar,
        "curve_models": curve,
        "prediction_formula": "intercept + standardized_slope * (initial_rack_01_c - predictor_mean_c) / predictor_std_c"
    }
    path = ROOT / "frozen_coolant_only_model.json"
    path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"path": str(path), "sha256": sha256(path), "scalar_models": scalar}, indent=2))


if __name__ == "__main__":
    main()
