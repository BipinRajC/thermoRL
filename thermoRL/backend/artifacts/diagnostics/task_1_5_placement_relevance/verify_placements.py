"""Independently verify counterfactual branches, decisions, and repeat identity."""

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def verify(directory: Path, config: dict, frozen: dict, prepared: dict) -> dict:
    metadata = json.loads((directory / "metrics_and_provenance.json").read_text())
    src = metadata["source_sha256"]
    assert src["run_script"] == sha256(ROOT / "run_placements.py")
    assert src["preregistration"] == sha256(ROOT / "preregistration.json")
    assert src["frozen_model"] == sha256(ROOT / "frozen_placement_model.json")
    assert src["pre_outcome_preparation"] == sha256(ROOT / "scenario_preparation.json")
    assert src["backend"] == sha256(PROJECT / "thermorl2/thermal/fmu_backend.py")
    assert src["task_1_5_test"] == sha256(PROJECT / "tests/fmu/test_fmu_backend.py")
    assert metadata["fmu_sha256"] == sha256(FMU)
    for key, digest in metadata["file_sha256"].items():
        path = directory / ("decisions.jsonl" if key == "decisions" else f"{key}.csv")
        assert digest == sha256(path)
    warmup = read_csv(directory / "warmup.csv")
    precondition = read_csv(directory / "scenario_preconditioning.csv")
    branches = read_csv(directory / "branch_ledger.csv")
    decisions = read_jsonl(directory / "decisions.jsonl")
    assert len(warmup) == 361 and len(branches) == 2172 and len(decisions) == 4
    assert [float(row["elapsed_s"]) for row in warmup] == list(range(0, 7201, 20))
    grouped = defaultdict(list)
    for row in branches:
        grouped[(row["scenario"], row["branch"])].append(row)
    checked = 0
    disagreements = 0
    for specification, decision in zip(config["ordered_scenarios"], decisions):
        name = specification["name"]
        assert decision["scenario"] == name
        assert decision["blind_choice"] == specification["blind_round_robin_choice"]
        assert decision["aware_choice"] == prepared["states"][name]["aware_choice"]
        held = grouped[(name, "no_step_control")]
        one = grouped[(name, "place_on_rack_01")]
        forty_four = grouped[(name, "place_on_rack_44")]
        assert len(held) == len(one) == len(forty_four) == 181
        initial = {key: value for key, value in held[0].items() if key not in ("scenario", "branch")}
        assert initial == {key: value for key, value in one[0].items() if key not in ("scenario", "branch")}
        assert initial == {key: value for key, value in forty_four[0].items() if key not in ("scenario", "branch")}
        assert all(float(initial[f"rack_{rack:02d}_power_kw"]) == 10.86 for rack in range(1, 45))
        for control, rack_one, rack_forty_four in zip(held, one, forty_four):
            elapsed = float(control["elapsed_s"])
            assert elapsed == float(rack_one["elapsed_s"]) == float(rack_forty_four["elapsed_s"])
            for rack in range(1, 45):
                key = f"rack_{rack:02d}_power_kw"
                heat = f"rack_{rack:02d}_fmu_heat_input_w"
                assert float(control[key]) == 10.86 and float(control[heat]) == 10262.699999999999
                expected_one = 40.0 if elapsed > 0 and rack == 1 else 10.86
                expected_forty_four = 40.0 if elapsed > 0 and rack == 44 else 10.86
                assert float(rack_one[key]) == expected_one
                assert float(rack_forty_four[key]) == expected_forty_four
            checked += 1
        for rack, rows in ((1, one), (44, forty_four)):
            key = f"rack_{rack:02d}_coolant_c"
            measured_peak = max(float(row[key]) for row in rows)
            measured_final = float(rows[-1][key])
            measured_system_peak = max(float(row[f"rack_{index:02d}_coolant_c"]) for row in rows for index in range(1, 45))
            stored = decision["candidate_outcomes"][str(rack)]
            assert abs(stored["placed_rack_absolute_peak_c"] - measured_peak) < 1e-12
            assert abs(stored["placed_rack_absolute_final_c"] - measured_final) < 1e-12
            assert abs(stored["system_absolute_peak_c"] - measured_system_peak) < 1e-12
        blind = decision["candidate_outcomes"][str(decision["blind_choice"])]
        aware = decision["candidate_outcomes"][str(decision["aware_choice"])]
        assert decision["rules_disagree"] == (decision["blind_choice"] != decision["aware_choice"])
        assert abs(decision["aware_minus_blind_placed_rack_absolute_peak_c"] - (aware["placed_rack_absolute_peak_c"] - blind["placed_rack_absolute_peak_c"])) < 1e-12
        assert abs(decision["aware_minus_blind_system_absolute_peak_c"] - (aware["system_absolute_peak_c"] - blind["system_absolute_peak_c"])) < 1e-12
        assert abs(decision["aware_minus_blind_placed_rack_absolute_final_c"] - (aware["placed_rack_absolute_final_c"] - blind["placed_rack_absolute_final_c"])) < 1e-12
        scores = decision["candidate_scores"]
        peak_model = frozen["models"]["absolute_step_branch_peak_c"]
        score_difference = scores["1"]["predicted_peak_c"] - scores["44"]["predicted_peak_c"]
        temperature_difference = scores["1"]["initial_coolant_c"] - scores["44"]["initial_coolant_c"]
        expected_difference = temperature_difference * peak_model["standardized_weights"][0] / peak_model["predictor_std"][0]
        assert abs(score_difference - expected_difference) < 1e-12
        if decision["rules_disagree"]:
            disagreements += 1
    assert disagreements == metadata["summary"]["n_decision_disagreements"] == 2
    return {"metadata": metadata, "paired_time_rows_checked": checked}


def main() -> None:
    config = json.loads((ROOT / "preregistration.json").read_text())
    frozen = json.loads((ROOT / "frozen_placement_model.json").read_text())
    prepared = json.loads((ROOT / "scenario_preparation.json").read_text())
    first = verify(ROOT / "run_01", config, frozen, prepared)
    second = verify(ROOT / "run_02", config, frozen, prepared)
    a, b = first["metadata"], second["metadata"]
    matching = {key: a["file_sha256"][key] == b["file_sha256"][key] for key in a["file_sha256"]}
    previous = json.loads((ROOT.parent / "task_1_5_state_identification/run_01/metrics_and_provenance.json").read_text())
    result = {
        "verification_script_sha256": sha256(Path(__file__)),
        "all_ledgers_byte_identical": all(matching.values()),
        "identical_by_file": matching,
        "maximum_repeat_thermal_difference_c": 0.0 if all(matching.values()) else None,
        "paired_time_rows_checked_per_run": first["paired_time_rows_checked"],
        "n_decision_disagreements": a["summary"]["n_decision_disagreements"],
        "global_flow_cancels_from_additive_within_state_peak_ranking": True,
        "backend_hash_unchanged": a["source_sha256"]["backend"] == previous["source_sha256"]["backend"],
        "task_1_5_test_hash_unchanged": a["source_sha256"]["task_1_5_test"] == previous["source_sha256"]["task_1_5_test"],
        "fmu_hash_unchanged": a["fmu_sha256"] == previous["fmu_sha256"],
        "frozen_model_sha256": sha256(ROOT / "frozen_placement_model.json"),
    }
    (ROOT / "repeat_verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
