"""Execute fixed FMU counterfactual placements from four saved plant states."""

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

from prepare_scenarios import CDU_VARS, choose_aware, context_power, predict
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def measure_action(rows: list[dict], control: list[dict], rack: int) -> dict:
    key = f"rack_{rack:02d}_coolant_c"
    raw_peak = max(rows, key=lambda row: row[key])
    raw_system_peak = max((row[f"rack_{i:02d}_coolant_c"], row["elapsed_s"], i) for row in rows for i in range(1, 45))
    effects = [(row[key] - held[key], row["elapsed_s"]) for row, held in zip(rows, control)]
    effect_peak = max(effects)
    return {
        "placed_rack": rack,
        "placed_rack_initial_c": rows[0][key],
        "placed_rack_absolute_peak_c": raw_peak[key],
        "placed_rack_absolute_peak_time_s": raw_peak["elapsed_s"],
        "placed_rack_absolute_final_c": rows[-1][key],
        "system_absolute_peak_c": raw_system_peak[0],
        "system_absolute_peak_time_s": raw_system_peak[1],
        "system_peak_rack": raw_system_peak[2],
        "placed_rack_paired_peak_increment_c": effect_peak[0],
        "placed_rack_paired_peak_time_s": effect_peak[1],
        "placed_rack_paired_final_increment_c": effects[-1][0],
    }


def run(run_name: str) -> None:
    prereg_path = ROOT / "preregistration.json"
    model_path = ROOT / "frozen_placement_model.json"
    preparation_path = ROOT / "scenario_preparation.json"
    config = json.loads(prereg_path.read_text())
    model = json.loads(model_path.read_text())
    preparation = json.loads(preparation_path.read_text())
    assert model["preregistration_sha256"] == sha256(prereg_path)
    assert preparation["preregistration_sha256"] == sha256(prereg_path)
    assert preparation["frozen_model_sha256"] == sha256(model_path)
    p = config["scenario_preconditioning"]
    branch_protocol = config["counterfactual_branches"]
    dt = p["measurement_interval_s"]
    horizon = branch_protocol["horizon_s"]
    ambient = Ambient(t_air_k=p["ambient_air_k"], t_ext_k=p["ambient_external_k"])
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    heat_keys = power_input_names(coupling)
    background = np.full(44, p["current_power_at_decision_kw_each_rack"])
    rack_names = [f"rack_{i:02d}_coolant_c" for i in range(1, 45)]
    supply_names = [f"cdu_{i:02d}_primary_supply_c" for i in range(1, 45)]
    return_names = [f"cdu_{i:02d}_primary_return_c" for i in range(1, 45)]
    power_names = [f"rack_{i:02d}_power_kw" for i in range(1, 45)]
    heat_names = [f"rack_{i:02d}_fmu_heat_input_w" for i in range(1, 45)]
    warm_rows = []
    preconditioning_rows = []
    branch_rows = []
    outcomes = {}
    decision_rows = []
    start_wall = perf_counter()
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    try:
        def capture(elapsed: float, applied: np.ndarray) -> dict:
            th = backend.observe()
            gl = backend.global_observe()
            inputs = rack_kw_to_fmu_inputs(applied, coupling, ambient)
            row = {"elapsed_s": elapsed, "fmu_time_s": backend.time_s}
            row.update(zip(rack_names, map(float, th.t_c)))
            row.update(zip(supply_names, map(float, th.extras["T_prim_s_C"])))
            row.update(zip(return_names, map(float, th.extras["T_prim_r_C"])))
            row.update(zip(power_names, map(float, applied)))
            row.update(zip(heat_names, (float(inputs[key]) for key in heat_keys)))
            row["datacenter_primary_flow_gpm"] = float(gl["fmu.V_flow_prim_GPM"])
            return row

        warm_rows.append(capture(0.0, background))
        for tick in range(1, p["initial_uniform_background_duration_s"] // dt + 1):
            backend.step(background, dt, ambient)
            warm_rows.append(capture(float(tick * dt), background))
        warm_handle = backend.save_state()
        try:
            for scenario in config["ordered_scenarios"]:
                name = scenario["name"]
                backend.restore_state(warm_handle)
                precondition = [capture(0.0, background)]
                applied_context = context_power(scenario["plant_context"])
                for tick in range(1, p["other_rack_context_pulse_duration_s"] // dt + 1):
                    backend.step(applied_context, dt, ambient)
                    precondition.append(capture(float(tick * dt), applied_context))
                hot = background.copy()
                hot[scenario["hot_rack"] - 1] = p["hot_candidate_pulse_kw"]
                offset = p["other_rack_context_pulse_duration_s"]
                for tick in range(1, p["hot_candidate_pulse_duration_s"] // dt + 1):
                    backend.step(hot, dt, ambient)
                    precondition.append(capture(float(offset + tick * dt), hot))
                backend.step(background, dt, ambient)
                precondition.append(capture(float(offset + p["hot_candidate_pulse_duration_s"] + dt), background))
                decision_state = precondition[-1]
                pilot = preparation["states"][name]["full_initial_observation"]
                for field in rack_names + supply_names + return_names + power_names + heat_names + ["datacenter_primary_flow_gpm"]:
                    if abs(decision_state[field] - pilot[field]) > 1e-8:
                        raise ValueError(f"{name}: pilot mismatch at {field}")
                if decision_state["fmu_time_s"] != pilot["fmu_time_s"]:
                    raise ValueError(f"{name}: pilot FMU time differs")
                preconditioning_rows.extend({"scenario": name, **row} for row in precondition)
                flow = decision_state["datacenter_primary_flow_gpm"]
                scores = {
                    rack: {
                        "initial_coolant_c": decision_state[f"rack_{rack:02d}_coolant_c"],
                        "predicted_peak_c": predict(model["models"]["absolute_step_branch_peak_c"], decision_state[f"rack_{rack:02d}_coolant_c"], flow),
                        "predicted_final_c": predict(model["models"]["absolute_step_branch_final_c"], decision_state[f"rack_{rack:02d}_coolant_c"], flow),
                    }
                    for rack in (1, 44)
                }
                aware_choice = choose_aware(scores)
                blind_choice = scenario["blind_round_robin_choice"]
                if aware_choice != preparation["states"][name]["aware_choice"]:
                    raise ValueError(f"{name}: aware decision differs from pre-outcome preparation")
                state_handle = backend.save_state()
                try:
                    branches = {}
                    for branch, chosen_rack in (("no_step_control", None), ("place_on_rack_01", 1), ("place_on_rack_44", 44)):
                        backend.restore_state(state_handle)
                        power = background.copy()
                        if chosen_rack is not None:
                            power[chosen_rack - 1] = 40.0
                        rows = [capture(0.0, background)]
                        for tick in range(1, horizon // dt + 1):
                            backend.step(power, dt, ambient)
                            rows.append(capture(float(tick * dt), power))
                        branches[branch] = rows
                        branch_rows.extend({"scenario": name, "branch": branch, **row} for row in rows)
                    initial = branches["no_step_control"][0]
                    if any(initial != branches[branch][0] for branch in ("place_on_rack_01", "place_on_rack_44")):
                        raise ValueError(f"{name}: branch-time observations differ")
                    if initial != {**decision_state, "elapsed_s": 0.0}:
                        raise ValueError(f"{name}: saved state differs from preconditioning")
                    action_outcomes = {
                        1: measure_action(branches["place_on_rack_01"], branches["no_step_control"], 1),
                        44: measure_action(branches["place_on_rack_44"], branches["no_step_control"], 44),
                    }
                    blind = action_outcomes[blind_choice]
                    aware = action_outcomes[aware_choice]
                    result = {
                        "scenario": name,
                        "saved_fmu_time_s": decision_state["fmu_time_s"],
                        "branch_initial_observations_match_exactly": True,
                        "flow_gpm": flow,
                        "candidate_scores": scores,
                        "blind_choice": blind_choice,
                        "aware_choice": aware_choice,
                        "rules_disagree": blind_choice != aware_choice,
                        "candidate_outcomes": action_outcomes,
                        "aware_minus_blind_placed_rack_absolute_peak_c": aware["placed_rack_absolute_peak_c"] - blind["placed_rack_absolute_peak_c"],
                        "aware_minus_blind_system_absolute_peak_c": aware["system_absolute_peak_c"] - blind["system_absolute_peak_c"],
                        "aware_minus_blind_placed_rack_absolute_final_c": aware["placed_rack_absolute_final_c"] - blind["placed_rack_absolute_final_c"],
                        "aware_minus_blind_paired_peak_increment_c": aware["placed_rack_paired_peak_increment_c"] - blind["placed_rack_paired_peak_increment_c"],
                        "oracle_best_placed_peak_rack": min(action_outcomes, key=lambda rack: action_outcomes[rack]["placed_rack_absolute_peak_c"]),
                        "oracle_best_system_peak_rack": min(action_outcomes, key=lambda rack: action_outcomes[rack]["system_absolute_peak_c"]),
                    }
                    outcomes[name] = result
                    decision_rows.append(result)
                finally:
                    backend.free_state(state_handle)
        finally:
            backend.free_state(warm_handle)
        runtime = {"wall_until_last_sample_s": perf_counter() - start_wall, "fmu_calls_s": backend.runtime_s()}
    finally:
        backend.close()

    output_dir = ROOT / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "warmup": output_dir / "warmup.csv",
        "scenario_preconditioning": output_dir / "scenario_preconditioning.csv",
        "branch_ledger": output_dir / "branch_ledger.csv",
    }
    write_csv(paths["warmup"], warm_rows)
    write_csv(paths["scenario_preconditioning"], preconditioning_rows)
    write_csv(paths["branch_ledger"], branch_rows)
    decision_path = output_dir / "decisions.jsonl"
    decision_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in decision_rows))
    disagreements = [row for row in decision_rows if row["rules_disagree"]]
    summary = {
        "n_scenarios": len(decision_rows),
        "n_decision_disagreements": len(disagreements),
        "disagreement_aware_minus_blind_placed_peak_c": [row["aware_minus_blind_placed_rack_absolute_peak_c"] for row in disagreements],
        "disagreement_aware_minus_blind_system_peak_c": [row["aware_minus_blind_system_absolute_peak_c"] for row in disagreements],
        "mean_aware_minus_blind_placed_peak_all_scenarios_c": float(np.mean([row["aware_minus_blind_placed_rack_absolute_peak_c"] for row in decision_rows])),
        "mean_aware_minus_blind_system_peak_all_scenarios_c": float(np.mean([row["aware_minus_blind_system_absolute_peak_c"] for row in decision_rows])),
    }
    metadata = {
        "experiment": "preregistered four-scenario FMU counterfactual placement relevance",
        "run_name": run_name,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "source_sha256": {
            "run_script": sha256(Path(__file__)),
            "preregistration": sha256(prereg_path),
            "frozen_model": sha256(model_path),
            "pre_outcome_preparation": sha256(preparation_path),
            "preparation_script": sha256(ROOT / "prepare_scenarios.py"),
            "backend": sha256(PROJECT / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT / "tests/fmu/test_fmu_backend.py"),
        },
        "fmu_sha256": sha256(FMU),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "fmpy_version": version("fmpy"),
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "outcomes": outcomes,
        "summary": summary,
        "runtime": runtime,
        "row_counts": {"warmup": len(warm_rows), "scenario_preconditioning": len(preconditioning_rows), "branches": len(branch_rows), "decisions": len(decision_rows)},
        "file_sha256": {name: sha256(path) for name, path in paths.items()} | {"decisions": sha256(decision_path)},
    }
    (output_dir / "metrics_and_provenance.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"run": run_name, "summary": summary, "outcomes": {name:{k:v[k] for k in ("blind_choice","aware_choice","rules_disagree","aware_minus_blind_placed_rack_absolute_peak_c","aware_minus_blind_system_absolute_peak_c")} for name,v in outcomes.items()}, "file_sha256": metadata["file_sha256"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", choices=("run_01", "run_02"))
    args = parser.parse_args()
    run(args.run_name)
