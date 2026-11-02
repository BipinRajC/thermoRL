"""Independently verify six saved-state pairs and fresh-process identity."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
FROZEN = ROOT.parent / "task_1_5_off_trajectory/frozen_coolant_only_model.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def predict(fit: dict, x: float) -> float:
    return fit["intercept"] + fit["standardized_slope"] * (x - fit["predictor_mean_c"]) / fit["predictor_std_c"]


def verify(directory: Path, selection: dict, frozen: dict) -> dict:
    metadata = json.loads((directory / "metrics_and_provenance.json").read_text())
    sources = metadata["source_sha256"]
    assert sources["run_script"] == sha256(ROOT / "run_identification.py")
    assert sources["original_preregistration"] == sha256(ROOT / "preregistration.json")
    assert sources["spatial_addendum"] == sha256(ROOT / "preregistration_spatial_addendum.json")
    assert sources["profile_selection"] == sha256(ROOT / "selection_spatial.json")
    assert sources["frozen_coolant_model"] == sha256(FROZEN)
    assert sources["backend"] == sha256(PROJECT / "thermorl2/thermal/fmu_backend.py")
    assert sources["task_1_5_test"] == sha256(PROJECT / "tests/fmu/test_fmu_backend.py")
    assert metadata["fmu_sha256"] == sha256(FMU)
    for name, digest in metadata["file_sha256"].items():
        assert digest == sha256(directory / f"{name}.csv")
    preconditioning = read(directory / "preconditioning.csv")
    branches = read(directory / "branch_ledger.csv")
    responses = read(directory / "response_ledger.csv")
    predictions = read(directory / "frozen_prediction_ledger.csv")
    assert len(branches) == 2172 and len(responses) == len(predictions) == 1086
    groups = defaultdict(list)
    for row in branches:
        groups[(row["profile"], row["branch"])].append(row)
    effects = defaultdict(list)
    for row in responses:
        effects[row["profile"]].append(row)
    estimates = defaultdict(list)
    for row in predictions:
        estimates[row["profile"]].append(row)
    checked = 0
    for name in selection["selected_profiles"]:
        state_time = float(selection["all_candidates"][name]["selected"]["elapsed_s"])
        saved = [row for row in preconditioning if row["profile"] == name and float(row["elapsed_s"]) == state_time]
        assert len(saved) == 1
        held = groups[(name, "control")]
        step = groups[(name, "step")]
        delta = effects[name]
        pred = estimates[name]
        assert len(held) == len(step) == len(delta) == len(pred) == 181
        initial_control = {key: value for key, value in held[0].items() if key not in ("profile", "branch")}
        initial_step = {key: value for key, value in step[0].items() if key not in ("profile", "branch")}
        assert initial_control == initial_step
        assert abs(float(initial_control["rack_01_coolant_c"]) - 32.0) <= 0.1
        assert all(float(initial_control[f"rack_{rack:02d}_power_kw"]) == 10.86 for rack in range(1, 45))
        initial_t = float(initial_control["rack_01_coolant_c"])
        for control_row, step_row, effect_row, prediction_row, curve_model in zip(held, step, delta, pred, frozen["curve_models"]):
            elapsed = float(control_row["elapsed_s"])
            assert elapsed == float(step_row["elapsed_s"]) == float(effect_row["elapsed_s"]) == float(prediction_row["elapsed_s"]) == curve_model["elapsed_s"]
            assert float(control_row["fmu_time_s"]) == float(step_row["fmu_time_s"]) == state_time + elapsed
            for rack in range(1, 45):
                power = f"rack_{rack:02d}_power_kw"
                heat = f"rack_{rack:02d}_fmu_heat_input_w"
                expected = 40.0 if elapsed > 0 and rack == 1 else 10.86
                assert float(control_row[power]) == 10.86 and float(control_row[heat]) == 10262.699999999999
                assert float(step_row[power]) == expected
                assert float(step_row[heat]) == (37800.0 if expected == 40.0 else 10262.699999999999)
            for key, value in effect_row.items():
                if key in ("profile", "elapsed_s"):
                    continue
                assert abs(float(value) - (float(step_row[key]) - float(control_row[key]))) < 1e-12
            observed = float(effect_row["rack_01_coolant_c"])
            predicted = predict(curve_model, initial_t)
            assert abs(float(prediction_row["frozen_curve_prediction_c"]) - predicted) < 1e-12
            assert abs(float(prediction_row["curve_signed_residual_c"]) - (observed - predicted)) < 1e-12
            checked += 1
        summary = metadata["profiles"][name]
        target = summary["target_paired_response"]
        peak_time = target["time_of_window_max_s"]
        curve_at_peak = next(float(row["frozen_curve_prediction_c"]) for row in pred if float(row["elapsed_s"]) == peak_time)
        scalar_peak = predict(frozen["scalar_models"]["paired_peak_increment_c"], initial_t)
        assert abs(summary["frozen_coolant_model"]["peak_to_peak_scalar_residual_c"] - (target["peak_increment"] - scalar_peak)) < 1e-12
        assert abs(summary["frozen_coolant_model"]["curve_residual_at_observed_peak_time_c"] - (target["peak_increment"] - curve_at_peak)) < 1e-12
    return {"metadata": metadata, "paired_rows_checked": checked}


def main() -> None:
    selection = json.loads((ROOT / "selection_spatial.json").read_text())
    frozen = json.loads(FROZEN.read_text())
    first = verify(ROOT / "run_01", selection, frozen)
    second = verify(ROOT / "run_02", selection, frozen)
    a, b = first["metadata"], second["metadata"]
    matching = {name: a["file_sha256"][name] == b["file_sha256"][name] for name in a["file_sha256"]}
    prior = json.loads((ROOT.parent / "task_1_5_state_sufficiency/run_01/metrics_and_provenance.json").read_text())
    result = {
        "verification_script_sha256": sha256(Path(__file__)),
        "all_csv_byte_identical": all(matching.values()),
        "csv_identical_by_file": matching,
        "maximum_repeat_thermal_difference_c": 0.0 if all(matching.values()) else None,
        "paired_rows_checked_per_run": first["paired_rows_checked"],
        "backend_hash_unchanged": a["source_sha256"]["backend"] == prior["source_sha256"]["backend"],
        "task_1_5_test_hash_unchanged": a["source_sha256"]["task_1_5_test"] == prior["source_sha256"]["task_1_5_test"],
        "fmu_hash_unchanged": a["fmu_sha256"] == prior["fmu_sha256"],
        "frozen_model_sha256": sha256(FROZEN),
        "selection_sha256": sha256(ROOT / "selection_spatial.json"),
    }
    (ROOT / "repeat_verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
