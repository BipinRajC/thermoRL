"""Verify saved-state pairs, frozen predictions, and repeated-run identity."""

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
PROFILES = ("constant_hold", "late_high_then_base", "low_then_raised_base")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def predict(model: dict, x: float) -> float:
    return model["intercept"] + model["standardized_slope"] * (x - model["predictor_mean_c"]) / model["predictor_std_c"]


def verify(directory: Path, selection: dict, frozen: dict) -> dict:
    metadata = json.loads((directory / "metrics_and_provenance.json").read_text())
    sources = metadata["source_sha256"]
    assert sources["run_script"] == sha256(ROOT / "run_off_trajectory.py")
    assert sources["frozen_model"] == sha256(ROOT / "frozen_coolant_only_model.json")
    assert sources["match_selection_v3"] == sha256(ROOT / "match_selection_v3.json")
    assert sources["backend"] == sha256(PROJECT / "thermorl2/thermal/fmu_backend.py")
    assert sources["task_1_5_test"] == sha256(PROJECT / "tests/fmu/test_fmu_backend.py")
    assert metadata["fmu_sha256"] == sha256(FMU)
    for name, digest in metadata["file_sha256"].items():
        assert digest == sha256(directory / f"{name}.csv")
    preconditioning = read(directory / "preconditioning.csv")
    branches = read(directory / "branch_ledger.csv")
    responses = read(directory / "response_ledger.csv")
    predictions = read(directory / "prediction_ledger.csv")
    assert len(responses) == len(predictions) == 543
    assert len(branches) == 1086
    groups = defaultdict(list)
    for row in branches:
        groups[(row["profile"], row["branch"])].append(row)
    effects = defaultdict(list)
    for row in responses:
        effects[row["profile"]].append(row)
    predicted = defaultdict(list)
    for row in predictions:
        predicted[row["profile"]].append(row)
    checked = 0
    for profile in PROFILES:
        selected = selection["selected"][profile]["selected"]
        state_time = float(selected["elapsed_s"])
        matched = [row for row in preconditioning if row["profile"] == profile and float(row["elapsed_s"]) == state_time]
        assert len(matched) == 1
        held = groups[(profile, "control")]
        step = groups[(profile, "step")]
        delta = effects[profile]
        pred = predicted[profile]
        assert len(held) == len(step) == len(delta) == len(pred) == 181
        a = {key: value for key, value in held[0].items() if key not in ("profile", "branch")}
        b = {key: value for key, value in step[0].items() if key not in ("profile", "branch")}
        assert a == b
        assert abs(float(a["rack_01_coolant_c"]) - 32.0) <= 0.1
        assert all(float(a[f"rack_{rack:02d}_power_kw"]) == 10.86 for rack in range(1, 45))
        initial_t = float(a["rack_01_coolant_c"])
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
            effect = float(effect_row["rack_01_coolant_c"])
            estimate = predict(curve_model, initial_t)
            assert abs(float(prediction_row["frozen_model_predicted_c"]) - estimate) < 1e-12
            assert abs(float(prediction_row["observed_paired_rack_01_c"]) - effect) < 1e-12
            assert abs(float(prediction_row["signed_residual_c"]) - (effect - estimate)) < 1e-12
            checked += 1
        summary = metadata["profiles"][profile]
        final_expected = predict(frozen["scalar_models"]["paired_final_increment_c"], initial_t)
        peak_expected = predict(frozen["scalar_models"]["paired_peak_increment_c"], initial_t)
        assert abs(summary["frozen_model_scalar_predictions"]["paired_final_increment_c"] - final_expected) < 1e-12
        assert abs(summary["frozen_model_scalar_predictions"]["paired_peak_increment_c"] - peak_expected) < 1e-12
    return {"metadata": metadata, "paired_rows_checked": checked}


def main() -> None:
    selection = json.loads((ROOT / "match_selection_v3.json").read_text())
    frozen = json.loads((ROOT / "frozen_coolant_only_model.json").read_text())
    assert selection["status"] == "matched"
    a = verify(ROOT / "run_01", selection, frozen)
    b = verify(ROOT / "run_02", selection, frozen)
    one, two = a["metadata"], b["metadata"]
    matching = {name: one["file_sha256"][name] == two["file_sha256"][name] for name in one["file_sha256"]}
    previous = json.loads((ROOT.parent / "task_1_5_state_sufficiency/run_01/metrics_and_provenance.json").read_text())
    result = {
        "verification_script_sha256": sha256(Path(__file__)),
        "all_csv_byte_identical": all(matching.values()),
        "csv_identical_by_file": matching,
        "maximum_repeat_thermal_difference_c": 0.0 if all(matching.values()) else None,
        "run_01_paired_rows_checked": a["paired_rows_checked"],
        "run_02_paired_rows_checked": b["paired_rows_checked"],
        "backend_hash_unchanged": one["source_sha256"]["backend"] == previous["source_sha256"]["backend"],
        "task_1_5_test_hash_unchanged": one["source_sha256"]["task_1_5_test"] == previous["source_sha256"]["task_1_5_test"],
        "fmu_hash_unchanged": one["fmu_sha256"] == previous["fmu_sha256"],
        "frozen_model_sha256": sha256(ROOT / "frozen_coolant_only_model.json"),
        "match_selection_v3_sha256": sha256(ROOT / "match_selection_v3.json"),
    }
    (ROOT / "repeat_verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
