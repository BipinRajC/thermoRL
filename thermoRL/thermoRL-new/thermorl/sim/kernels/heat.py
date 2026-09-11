from __future__ import annotations

import numpy as np


def heat_inject(Q: np.ndarray, zone_id: int, rack_id: int, power_kw: float) -> np.ndarray:
    out = Q.copy()
    out[zone_id, rack_id] = out[zone_id, rack_id] + np.float32(power_kw)
    return out


def heat_release(Q: np.ndarray, zone_id: int, rack_id: int, power_kw: float) -> np.ndarray:
    out = Q.copy()
    out[zone_id, rack_id] = out[zone_id, rack_id] - np.float32(power_kw)
    return out
