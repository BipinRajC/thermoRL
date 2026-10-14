"""Backend side of the Task 1.5 independent replay correctness gate."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from raps.system_config import get_system_config

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


_CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
_PRIMARY_VARS = {
    "T_prim_s_C": _CDU_SUMMARY + "T_prim_s_C",
    "T_prim_r_C": _CDU_SUMMARY + "T_prim_r_C",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(fmu_path: Path, sequence_path: Path, output_path: Path) -> None:
    sequence = json.loads(sequence_path.read_text())
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    backend = FmuBackend(fmu_path, coupling, extra_rack_vars=_PRIMARY_VARS)
    closed_twice = False
    try:
        # warm_up currently uses strict '<' for its settle test. With a zero
        # threshold, nonnegative absolute rates cannot stop it early; a
        # negative threshold would also withstand a future '<=' change.
        warmup_used_s = backend.warm_up(
            np.full(44, 10.86), Ambient(), dt_s=20.0,
            max_s=7200.0, settle_k_per_min=0.0,
        )
        assert warmup_used_s == 7200.0
        snapshot_time_s = backend._snapshot_time_s
        assert snapshot_time_s == 7200.0

        actual_do_step = backend.fmu.doStep
        observed_calls = []

        def recording_do_step(current_communication_point, step_size, *args, **kwargs):
            observed_calls.append((float(current_communication_point), float(step_size)))
            return actual_do_step(current_communication_point, step_size, *args, **kwargs)

        backend.fmu.doStep = recording_do_step

        def observe() -> dict:
            thermal = backend.observe()
            globals_ = backend.global_observe()
            return {
                "elapsed_s": backend.time_s,
                "fmu_time_s": snapshot_time_s + backend.time_s,
                "rack_coolant_c": list(map(float, thermal.t_c)),
                "cdu_primary_supply_c": list(map(float, thermal.extras["T_prim_s_C"])),
                "cdu_primary_return_c": list(map(float, thermal.extras["T_prim_r_C"])),
                "datacenter_primary_flow_gpm": float(globals_["fmu.V_flow_prim_GPM"]),
            }

        heat_names = power_input_names(coupling)
        replays = []
        for _ in range(2):
            backend.reset()
            samples = [observe()]
            calls = []
            heat_inputs = []
            air_inputs = []
            external_inputs = []
            for tick in sequence:
                start_s = float(tick["elapsed_start_s"])
                assert backend.time_s == start_s
                ambient = Ambient(t_air_k=float(tick["t_air_k"]), t_ext_k=float(tick["t_ext_k"]))
                rack_kw = np.asarray(tick["rack_kw"], dtype=float)
                inputs = rack_kw_to_fmu_inputs(rack_kw, coupling, ambient)
                heat_inputs.append([inputs[name] for name in heat_names])
                air_inputs.append(ambient.t_air_k)
                external_inputs.append(ambient.t_ext_k)
                before = len(observed_calls)
                backend.step(rack_kw, 20.0, ambient)
                assert len(observed_calls) == before + 1
                actual_point, actual_size = observed_calls[-1]
                assert actual_point == snapshot_time_s + start_s
                assert actual_size == 20.0
                calls.append({"elapsed_start_s": start_s, "current_communication_point_s": actual_point, "step_size_s": actual_size})
                samples.append(observe())
            replays.append({
                "samples": samples,
                "communication_calls": calls,
                "heat_input_w": heat_inputs,
                "air_input_k": air_inputs,
                "external_input_k": external_inputs,
            })
        runtime_s = backend.runtime_s()
        assert runtime_s > 0
    finally:
        backend.close()
        backend.close()
        closed_twice = True
    result = {
        "warmup_used_s": warmup_used_s,
        "warmup_status": "capped_preconditioned_not_settled",
        "snapshot_time_s": snapshot_time_s,
        "runtime_s": runtime_s,
        "close_twice_succeeded": closed_twice,
        "fmu_sha256": _sha256(fmu_path),
        "sequence_sha256": _sha256(sequence_path),
        "replays": replays,
    }
    output_path.write_text(json.dumps(result, sort_keys=True) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
