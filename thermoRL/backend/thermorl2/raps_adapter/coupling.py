from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from thermorl2.core.state import Ambient


@dataclass(frozen=True)
class CouplingParams:
    num_cdus: int
    racks_per_cdu: int
    cooling_efficiency: float
    temperature_keys: tuple[str, ...]
    wet_bulb_temp_k: float

    @classmethod
    def from_legacy_config(cls, cfg: dict) -> CouplingParams:
        return cls(
            num_cdus=cfg["NUM_CDUS"],
            racks_per_cdu=cfg["RACKS_PER_CDU"],
            cooling_efficiency=cfg["COOLING_EFFICIENCY"],
            temperature_keys=tuple(cfg["TEMPERATURE_KEYS"]),
            wet_bulb_temp_k=cfg["WET_BULB_TEMP"],
        )


def power_input_names(p: CouplingParams) -> list[str]:
    return [
        f"simulator_1_datacenter_1_computeBlock_{i + 1}_cabinet_1_sources_Q_flow_total"
        for i in range(p.num_cdus)
    ]


def rack_kw_to_fmu_inputs(rack_kw: np.ndarray, p: CouplingParams, ambient: Ambient) -> dict[str, float]:
    if ambient.t_air_k_by_unit is not None and len(ambient.t_air_k_by_unit) != p.num_cdus:
        raise ValueError("per-unit air temperatures must match the number of CDUs")
    out = {
        name: float((rack_kw[i] * 1000.0) * p.cooling_efficiency / p.racks_per_cdu)
        for i, name in enumerate(power_input_names(p))
    }
    for key in p.temperature_keys:
        out[key] = ambient.t_ext_k if key.endswith("_T_ext") else ambient.t_air_k
    if ambient.t_air_k_by_unit is not None:
        for i, temperature in enumerate(ambient.t_air_k_by_unit, start=1):
            key = f"simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_T_Air"
            if key not in out:
                raise KeyError(f"missing per-unit T_Air input: {key}")
            out[key] = float(temperature)
    return out
