from __future__ import annotations

import numpy as np


def pue_effective(
    T: np.ndarray,
    T_amb: np.ndarray,
    T_max: np.ndarray,
    pue_base: np.ndarray,
    k_z: np.ndarray,
    theta: float,
    p: float,
) -> np.ndarray:
    span = T_max - T_amb
    s = np.divide(T - T_amb, span, out=np.zeros_like(T, dtype=np.float32), where=span != 0)
    excess = np.maximum(s - theta, 0.0)
    return (pue_base + k_z * np.power(excess, p)).astype(np.float32)
