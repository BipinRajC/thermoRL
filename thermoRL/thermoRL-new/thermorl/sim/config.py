from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

N_ZONES = 3
_BASE_YAML = Path(__file__).resolve().parents[2] / "config" / "base.yaml"


@dataclass
class FacilityConfig:
    racks_per_zone: int
    q_max_rack_kw: np.ndarray
    t_max_c: np.ndarray
    tau_s: np.ndarray
    pue_base: np.ndarray
    pue_emergency: np.ndarray
    k_z: np.ndarray
    t_amb_base_c: np.ndarray
    density_min: np.ndarray
    density_max: np.ndarray
    degradation_rate: np.ndarray
    degradation_recovery: np.ndarray
    d_max: np.ndarray
    pue_theta: float
    pue_p: float
    eps_emergency: float
    eps_release: float
    emergency_min_duration_s: float
    t_amb_amplitude_c: np.ndarray = field(
        default_factory=lambda: np.zeros(N_ZONES, dtype=np.float32)
    )
    ambient_period_s: float = 86400.0
    ambient_phase_s: float = 0.0

    @classmethod
    def from_base_yaml(cls, path: Path | None = None) -> FacilityConfig:
        data = yaml.safe_load((path or _BASE_YAML).read_text())
        zones = data["zones"]
        return cls(
            racks_per_zone=int(data["racks_per_zone"]),
            q_max_rack_kw=np.array([z["q_max_rack_kw"] for z in zones], dtype=np.float32),
            t_max_c=np.array([z["t_max_c"] for z in zones], dtype=np.float32),
            tau_s=np.array([z["tau_s"] for z in zones], dtype=np.float32),
            pue_base=np.array([z["pue_base"] for z in zones], dtype=np.float32),
            pue_emergency=np.array([z["pue_emergency"] for z in zones], dtype=np.float32),
            k_z=np.array(data["pue"]["k_z"], dtype=np.float32),
            t_amb_base_c=np.array([z["t_amb_base_c"] for z in zones], dtype=np.float32),
            density_min=np.array([z["density_kw_per_node_min"] for z in zones], dtype=np.float32),
            density_max=np.array([z["density_kw_per_node_max"] for z in zones], dtype=np.float32),
            degradation_rate=np.array([z["degradation_rate"] for z in zones], dtype=np.float32),
            degradation_recovery=np.array(
                [z["degradation_recovery"] for z in zones], dtype=np.float32
            ),
            d_max=np.array([z["d_max"] for z in zones], dtype=np.float32),
            pue_theta=float(data["pue"]["theta"]),
            pue_p=float(data["pue"]["p"]),
            eps_emergency=float(data["emergency"]["epsilon_trigger"]),
            eps_release=float(data["emergency"]["epsilon_release"]),
            emergency_min_duration_s=float(data["emergency"]["min_duration_s"]),
            t_amb_amplitude_c=np.array([z["t_amb_amplitude_c"] for z in zones], dtype=np.float32),
            ambient_period_s=float(data["ambient"]["period_s"]),
            ambient_phase_s=float(data["ambient"]["phase_s"]),
        )
