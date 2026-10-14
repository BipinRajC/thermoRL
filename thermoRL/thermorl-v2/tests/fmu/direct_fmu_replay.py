"""Independent direct-FMPy reference for the Task 1.5 correctness gate.

This test-only helper intentionally imports neither RAPS nor thermorl2. The
Lassen value-reference names and power conversion are specified here directly.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from fmpy import extract, read_model_description
from fmpy.fmi2 import FMU2Slave


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _references(model_description) -> tuple[list[int], list[int], list[int], list[int], list[int], int, list[int]]:
    variables = {variable.name: variable.valueReference for variable in model_description.modelVariables}
    heat = [variables[f"simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_Q_flow_total"] for i in range(1, 45)]
    air = [variables[f"simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_T_Air"] for i in range(1, 45)]
    external = variables["simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"]
    coolant = [variables[f"simulator[1].datacenter[1].computeBlock[{i}].cabinet[1].volume.medium.T"] for i in range(1, 45)]
    primary_supply = [variables[f"simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary.T_prim_s_C"] for i in range(1, 45)]
    primary_return = [variables[f"simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary.T_prim_r_C"] for i in range(1, 45)]
    flow = variables["simulator[1].datacenter[1].summary.V_flow_prim_GPM"]
    return heat, air, coolant, primary_supply, primary_return, flow, [external]


def main(fmu_path: Path, sequence_path: Path, output_path: Path) -> None:
    sequence = json.loads(sequence_path.read_text())
    unzip_dir = Path(extract(str(fmu_path)))
    fmu = None
    snapshot = None
    try:
        description = read_model_description(str(fmu_path))
        heat_vrs, air_vrs, coolant_vrs, supply_vrs, return_vrs, flow_vr, external_vrs = _references(description)
        input_vrs = heat_vrs + air_vrs + external_vrs
        fmu = FMU2Slave(
            guid=description.guid,
            unzipDirectory=str(unzip_dir),
            modelIdentifier=description.coSimulation.modelIdentifier,
            instanceName="thermorl2_direct_reference",
        )
        fmu.instantiate()
        fmu.setupExperiment(tolerance=1e-5, startTime=0.0)
        fmu.enterInitializationMode()
        fmu.exitInitializationMode()

        def set_inputs(rack_kw: list[float], air_k: float, external_k: float) -> list[float]:
            heat_w = [float(power_kw * 1000.0 * 0.945) for power_kw in rack_kw]
            fmu.setReal(input_vrs, heat_w + [air_k] * 44 + [external_k])
            return heat_w

        def observe(elapsed_s: float, current_time_s: float) -> dict:
            coolant_c = [float(value - 273.15) for value in fmu.getReal(coolant_vrs)]
            supply_c = [float(value) for value in fmu.getReal(supply_vrs)]
            return_c = [float(value) for value in fmu.getReal(return_vrs)]
            flow_gpm = float(fmu.getReal([flow_vr])[0])
            return {
                "elapsed_s": elapsed_s,
                "fmu_time_s": current_time_s,
                "rack_coolant_c": coolant_c,
                "cdu_primary_supply_c": supply_c,
                "cdu_primary_return_c": return_c,
                "datacenter_primary_flow_gpm": flow_gpm,
            }

        current_time_s = 0.0
        for _ in range(360):
            set_inputs([10.86] * 44, 290.0, 290.0)
            fmu.doStep(current_time_s, 20.0)
            current_time_s += 20.0
        warmup_used_s = current_time_s
        assert warmup_used_s == 7200.0
        snapshot = fmu.getFMUstate()
        replays = []
        for _ in range(2):
            fmu.setFMUstate(snapshot)
            current_time_s = warmup_used_s
            samples = [observe(0.0, current_time_s)]
            calls = []
            heat_inputs = []
            air_inputs = []
            external_inputs = []
            for tick in sequence:
                start_s = float(tick["elapsed_start_s"])
                assert current_time_s == warmup_used_s + start_s
                heat_inputs.append(set_inputs(tick["rack_kw"], tick["t_air_k"], tick["t_ext_k"]))
                air_inputs.append(float(tick["t_air_k"]))
                external_inputs.append(float(tick["t_ext_k"]))
                calls.append({"elapsed_start_s": start_s, "current_communication_point_s": current_time_s, "step_size_s": 20.0})
                fmu.doStep(current_time_s, 20.0)
                current_time_s += 20.0
                samples.append(observe(start_s + 20.0, current_time_s))
            replays.append({
                "samples": samples,
                "communication_calls": calls,
                "heat_input_w": heat_inputs,
                "air_input_k": air_inputs,
                "external_input_k": external_inputs,
            })
        result = {
            "warmup_used_s": warmup_used_s,
            "warmup_status": "capped_preconditioned_not_settled",
            "snapshot_time_s": warmup_used_s,
            "fmu_sha256": _sha256(fmu_path),
            "sequence_sha256": _sha256(sequence_path),
            "replays": replays,
        }
        output_path.write_text(json.dumps(result, sort_keys=True) + "\n")
    finally:
        if fmu is not None:
            if snapshot is not None:
                fmu.freeFMUstate(snapshot)
            try:
                fmu.terminate()
            finally:
                fmu.freeInstance()
        shutil.rmtree(unzip_dir, ignore_errors=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
