from __future__ import annotations

import numpy as np


def rc_alpha(tau_s: float, dt_s: float) -> float:
    return float(1.0 - np.exp(-dt_s / tau_s))


def rc_step(T: np.ndarray, T_ss: np.ndarray, tau: np.ndarray, dt_s: float) -> np.ndarray:
    alpha = 1.0 - np.exp(-dt_s / tau)
    return (T + alpha * (T_ss - T)).astype(np.float32)
