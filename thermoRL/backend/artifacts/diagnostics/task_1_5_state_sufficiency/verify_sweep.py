"""Independently verify paired branches, inputs, hashes, and repeat variation."""

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
PREREG = json.loads((ROOT / "preregistration.json").read_text())
STATES = PREREG["state_times_s"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def verify(directory: Path) -> dict:
    metadata = json.loads((directory / "metrics_and_provenance.json").read_text())
    assert metadata["source_sha256"]["run_script"] == sha256(ROOT / "run_sweep.py")
    assert metadata["source_sha256"]["preregistration"] == sha256(ROOT / "preregistration.json")
    assert metadata["source_sha256"]["backend"] == sha256(PROJECT / "thermorl2/thermal/fmu_backend.py")
    assert metadata["source_sha256"]["task_1_5_test"] == sha256(PROJECT / "tests/fmu/test_fmu_backend.py")
    assert metadata["fmu_sha256"] == sha256(FMU)
    assert all(metadata["file_sha256"][name] == sha256(directory / f"{name}.csv") for name in metadata["file_sha256"])
    preconditioning = read(directory / "preconditioning.csv")
    branches = read(directory / "branch_ledger.csv")
    responses = read(directory / "response_ledger.csv")
    assert len(preconditioning) == 361 and len(branches) == 2896 and len(responses) == 1448
    assert [float(row["elapsed_s"]) for row in preconditioning] == list(range(0, 7201, 20))
    grouped = defaultdict(list)
    for row in branches:
        grouped[(int(row["state_time_s"]), row["branch"])].append(row)
    grouped_response = defaultdict(list)
    for row in responses:
        grouped_response[int(row["state_time_s"])].append(row)
    checked = 0
    for state_time in STATES:
        control = grouped[(state_time, "control")]
        step = grouped[(state_time, "step")]
        delta = grouped_response[state_time]
        assert len(control) == len(step) == len(delta) == 181
        initial_control = {name: value for name, value in control[0].items() if name not in ("state_time_s", "branch")}
        initial_step = {name: value for name, value in step[0].items() if name not in ("state_time_s", "branch")}
        assert initial_control == initial_step
        for held, stepped, response in zip(control, step, delta):
            elapsed = float(held["elapsed_s"])
            assert elapsed == float(stepped["elapsed_s"]) == float(response["elapsed_s"])
            assert float(held["fmu_time_s"]) == float(stepped["fmu_time_s"]) == state_time + elapsed
            for rack in range(1, 45):
                power = f"rack_{rack:02d}_power_kw"
                heat = f"rack_{rack:02d}_fmu_heat_input_w"
                expected = 40.0 if elapsed > 0 and rack == 1 else 10.86
                assert float(held[power]) == 10.86 and float(held[heat]) == 10262.699999999999
                assert float(stepped[power]) == expected
                assert float(stepped[heat]) == (37800.0 if expected == 40.0 else 10262.699999999999)
            for name, value in response.items():
                if name in ("state_time_s", "elapsed_s"):
                    continue
                assert abs(float(value) - (float(stepped[name]) - float(held[name]))) < 1e-12
            checked += 1
    return {"metadata": metadata, "paired_rows_checked": checked}


def main() -> None:
    one = verify(ROOT / "run_01")
    two = verify(ROOT / "run_02")
    a, b = one["metadata"], two["metadata"]
    matching = {key: a["file_sha256"][key] == b["file_sha256"][key] for key in a["file_sha256"]}
    prior = json.loads((ROOT.parent / "task_1_5_state_dependence/run_01/provenance_and_metrics.json").read_text())
    result = {
        "verification_script_sha256": sha256(Path(__file__)),
        "all_csv_byte_identical": all(matching.values()),
        "csv_identical_by_file": matching,
        "max_repeat_thermal_difference_c": 0.0 if all(matching.values()) else None,
        "run_01_paired_rows_checked": one["paired_rows_checked"],
        "run_02_paired_rows_checked": two["paired_rows_checked"],
        "preregistered_state_times_s": STATES,
        "backend_hash_unchanged": a["source_sha256"]["backend"] == prior["source_sha256"]["backend"],
        "test_hash_unchanged": a["source_sha256"]["task_1_5_test"] == prior["source_sha256"]["task_1_5_test"],
        "fmu_hash_unchanged": a["fmu_sha256"] == prior["fmu_sha256"],
    }
    (ROOT / "repeat_verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
