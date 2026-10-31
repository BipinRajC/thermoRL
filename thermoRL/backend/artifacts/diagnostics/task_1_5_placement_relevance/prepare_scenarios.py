"""Prepare the fixed placement states without running placement action branches."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from raps.system_config import get_system_config

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
CDU_VARS = {"T_prim_s_C": CDU_SUMMARY + "T_prim_s_C", "T_prim_r_C": CDU_SUMMARY + "T_prim_r_C"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def predict(fit: dict, target_c: float, flow_gpm: float) -> float:
    x = np.asarray([target_c, flow_gpm])
    return float(fit["intercept_c"] + np.dot((x - fit["predictor_mean"]) / fit["predictor_std"], fit["standardized_weights"]))


def context_power(context: str) -> np.ndarray:
    vector = np.full(44, 10.86)
    if context == "other_racks_high":
        vector[1:43] = 20.0
    elif context == "other_racks_low":
        vector[1:43] = 5.0
    return vector


def choose_aware(scores: dict[int, dict]) -> int:
    candidates = sorted(scores)
    if abs(scores[candidates[0]]["predicted_peak_c"] - scores[candidates[1]]["predicted_peak_c"]) > 1e-9:
        return min(candidates, key=lambda rack: scores[rack]["predicted_peak_c"])
    if abs(scores[candidates[0]]["predicted_final_c"] - scores[candidates[1]]["predicted_final_c"]) > 1e-9:
        return min(candidates, key=lambda rack: scores[rack]["predicted_final_c"])
    return candidates[0]


def main() -> None:
    config_path = ROOT / "preregistration.json"
    model_path = ROOT / "frozen_placement_model.json"
    config = json.loads(config_path.read_text())
    model = json.loads(model_path.read_text())
    assert model["preregistration_sha256"] == sha256(config_path)
    p = config["scenario_preconditioning"]
    dt = p["measurement_interval_s"]
    ambient = Ambient(t_air_k=p["ambient_air_k"], t_ext_k=p["ambient_external_k"])
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    heat_keys = power_input_names(coupling)
    background = np.full(44, 10.86)
    rows = []
    states = {}
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    try:
        def capture(scenario: str, stage: str, elapsed: float, applied: np.ndarray) -> dict:
            th = backend.observe()
            gl = backend.global_observe()
            inputs = rack_kw_to_fmu_inputs(applied, coupling, ambient)
            row = {"scenario": scenario, "stage": stage, "elapsed_since_warm_s": elapsed, "fmu_time_s": backend.time_s}
            row.update({f"rack_{i:02d}_coolant_c": float(th.t_c[i - 1]) for i in range(1, 45)})
            row.update({f"cdu_{i:02d}_primary_supply_c": float(th.extras["T_prim_s_C"][i - 1]) for i in range(1, 45)})
            row.update({f"cdu_{i:02d}_primary_return_c": float(th.extras["T_prim_r_C"][i - 1]) for i in range(1, 45)})
            row.update({f"rack_{i:02d}_power_kw": float(applied[i - 1]) for i in range(1, 45)})
            row.update({f"rack_{i:02d}_fmu_heat_input_w": float(inputs[heat_keys[i - 1]]) for i in range(1, 45)})
            row["datacenter_primary_flow_gpm"] = float(gl["fmu.V_flow_prim_GPM"])
            return row

        for tick in range(1, p["initial_uniform_background_duration_s"] // dt + 1):
            backend.step(background, dt, ambient)
        warm_handle = backend.save_state()
        try:
            for scenario in config["ordered_scenarios"]:
                name = scenario["name"]
                backend.restore_state(warm_handle)
                rows.append(capture(name, "warm_start", 0.0, background))
                current = context_power(scenario["plant_context"])
                for tick in range(1, p["other_rack_context_pulse_duration_s"] // dt + 1):
                    backend.step(current, dt, ambient)
                    rows.append(capture(name, "plant_context", float(tick * dt), current))
                hot = background.copy()
                hot[scenario["hot_rack"] - 1] = p["hot_candidate_pulse_kw"]
                offset = p["other_rack_context_pulse_duration_s"]
                for tick in range(1, p["hot_candidate_pulse_duration_s"] // dt + 1):
                    backend.step(hot, dt, ambient)
                    rows.append(capture(name, "candidate_pulse", float(offset + tick * dt), hot))
                backend.step(background, dt, ambient)
                final = capture(name, "saved_decision_state", float(offset + p["hot_candidate_pulse_duration_s"] + dt), background)
                rows.append(final)
                assert all(final[f"rack_{i:02d}_power_kw"] == 10.86 for i in range(1, 45))
                flow = final["datacenter_primary_flow_gpm"]
                scores = {
                    rack: {
                        "initial_coolant_c": final[f"rack_{rack:02d}_coolant_c"],
                        "predicted_peak_c": predict(model["models"]["absolute_step_branch_peak_c"], final[f"rack_{rack:02d}_coolant_c"], flow),
                        "predicted_final_c": predict(model["models"]["absolute_step_branch_final_c"], final[f"rack_{rack:02d}_coolant_c"], flow),
                    }
                    for rack in (1, 44)
                }
                states[name] = {
                    "spec": scenario,
                    "fmu_time_s": backend.time_s,
                    "candidate_scores": scores,
                    "flow_gpm": flow,
                    "blind_choice": scenario["blind_round_robin_choice"],
                    "aware_choice": choose_aware(scores),
                    "full_initial_observation": final,
                }
        finally:
            backend.free_state(warm_handle)
    finally:
        backend.close()
    csv_path = ROOT / "scenario_preconditioning_pilot.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "status": "fixed_scenarios_prepared_before_placement_outcomes",
        "preregistration_sha256": sha256(config_path),
        "frozen_model_sha256": sha256(model_path),
        "pilot_script_sha256": sha256(Path(__file__)),
        "fmu_sha256": sha256(FMU),
        "pilot_csv_sha256": sha256(csv_path),
        "states": states,
        "decision_disagreements_before_outcomes": sum(v["blind_choice"] != v["aware_choice"] for v in states.values()),
    }
    (ROOT / "scenario_preparation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"disagreements": result["decision_disagreements_before_outcomes"], "states": {n:{k:v[k] for k in ("fmu_time_s","candidate_scores","flow_gpm","blind_choice","aware_choice")} for n,v in states.items()}}, indent=2))


if __name__ == "__main__":
    main()
