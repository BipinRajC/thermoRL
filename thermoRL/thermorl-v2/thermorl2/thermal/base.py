from __future__ import annotations

from typing import Protocol

import numpy as np

from thermorl2.core.state import Ambient, RackThermal


class ThermalBackend(Protocol):
    n_units: int

    def reset(self) -> None: ...

    def step(self, unit_power_kw: np.ndarray, dt_s: float, ambient: Ambient) -> None: ...

    def observe(self) -> RackThermal: ...

    def global_observe(self) -> dict[str, float]: ...

    def runtime_s(self) -> float: ...
