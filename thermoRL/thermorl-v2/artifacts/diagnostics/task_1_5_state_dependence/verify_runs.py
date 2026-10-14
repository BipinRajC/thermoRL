"""Independently check paired ledgers and fresh-process repeat variation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
STATES = {"A_evolving": 1800, "B_warmed": 7200}
DT_S = 20
HORIZON_S = 3600


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def verify_run(directory: Path) -> dict:
    meta = json.loads((directory / "provenance_and_metrics.json").read_text())
    assert meta["source_sha256"]["experiment_script"] == sha256(ROOT / "run_state_dependence.py")
    assert meta["source_sha256"]["backend"] == sha256(PROJECT / "thermorl2/thermal/fmu_backend.py")
    assert meta["source_sha256"]["task_1_5_test"] == sha256(PROJECT / "tests/fmu/test_fmu_backend.py")
    assert meta["fmu_sha256"] == sha256(FMU)
    assert all(meta["file_sha256"][name] == sha256(directory / f"{name}.csv") for name in meta["file_sha256"])
    assert meta["plot_sha256"] == sha256(directory / "paired_response.png")
    assert meta["absolute_plot_sha256"] == sha256(directory / "absolute_trajectories.png")

    preconditioning = read_csv(directory / "preconditioning.csv")
    assert [float(row["elapsed_s"]) for row in preconditioning] == list(range(0, 7201, DT_S))
    checked_branch_rows = 0
    for state, state_time in STATES.items():
        control = read_csv(directory / f"{state}_control.csv")
        step = read_csv(directory / f"{state}_step.csv")
        difference = read_csv(directory / f"{state}_step_minus_control.csv")
        assert len(control) == len(step) == len(difference) == HORIZON_S // DT_S + 1
        assert control[0] == step[0]
        assert control[0] == preconditioning[state_time // DT_S] | {"elapsed_s": "0.0"}
        for held, stepped, delta in zip(control, step, difference):
            elapsed = float(held["elapsed_s"])
            assert elapsed == float(stepped["elapsed_s"]) == float(delta["elapsed_s"])
            assert float(held["fmu_time_s"]) == float(stepped["fmu_time_s"]) == state_time + elapsed
            for rack in range(1, 45):
                power = f"rack_{rack:02d}_power_kw"
                heat = f"rack_{rack:02d}_fmu_heat_input_w"
                assert float(held[power]) == 10.86
                assert float(held[heat]) == 10262.699999999999
                expected = 40.0 if elapsed > 0 and rack == 1 else 10.86
                assert float(stepped[power]) == expected
                assert float(stepped[heat]) == (37800.0 if expected == 40.0 else 10262.699999999999)
            for name, value in delta.items():
                if name == "elapsed_s":
                    continue
                assert abs(float(value) - (float(stepped[name]) - float(held[name]))) < 1e-12
            checked_branch_rows += 1
    a = read_csv(directory / "A_evolving_step_minus_control.csv")
    b = read_csv(directory / "B_warmed_step_minus_control.csv")
    cross = read_csv(directory / "B_minus_A_response.csv")
    for row_a, row_b, row_cross in zip(a, b, cross):
        for name, value in row_cross.items():
            if name == "elapsed_s":
                continue
            assert abs(float(value) - (float(row_b[name]) - float(row_a[name]))) < 1e-12
    return {"metadata": meta, "paired_time_rows_checked": checked_branch_rows}


def main() -> None:
    one = verify_run(ROOT / "run_01")
    two = verify_run(ROOT / "run_02")
    meta_one = one["metadata"]
    meta_two = two["metadata"]
    matching_csv = {
        name: meta_one["file_sha256"][name] == meta_two["file_sha256"][name]
        for name in meta_one["file_sha256"]
    }
    if all(matching_csv.values()):
        max_thermal_repeat_difference = 0.0
    else:
        max_thermal_repeat_difference = max(
            abs(float(a[name]) - float(b[name]))
            for file_name in matching_csv
            for a, b in zip(read_csv(ROOT / "run_01" / f"{file_name}.csv"), read_csv(ROOT / "run_02" / f"{file_name}.csv"))
            for name in a
            if name.endswith("_c")
        )
    old = json.loads((ROOT.parent / "task_1_5_matched_step_20s/provenance_and_metrics.json").read_text())
    summary = {
        "verification_script_sha256": sha256(Path(__file__)),
        "all_csv_byte_identical": all(matching_csv.values()),
        "csv_identical_by_file": matching_csv,
        "paired_response_plot_identical": meta_one["plot_sha256"] == meta_two["plot_sha256"],
        "absolute_trajectory_plot_identical": meta_one["absolute_plot_sha256"] == meta_two["absolute_plot_sha256"],
        "max_absolute_thermal_repeat_difference_c": max_thermal_repeat_difference,
        "run_01_paired_time_rows_checked": one["paired_time_rows_checked"],
        "run_02_paired_time_rows_checked": two["paired_time_rows_checked"],
        "backend_hash_unchanged_from_prior_diagnostic": (
            meta_one["source_sha256"]["backend"] == old["source_sha256"]["backend"]
        ),
        "task_1_5_test_hash_unchanged_from_prior_diagnostic": (
            meta_one["source_sha256"]["task_1_5_test"] == old["source_sha256"]["task_1_5_test"]
        ),
        "fmu_hash_unchanged_from_prior_diagnostic": meta_one["fmu_sha256"] == old["fmu_sha256"],
    }
    output = ROOT / "repeat_verification.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
