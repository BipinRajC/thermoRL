# Copied verbatim from thermoRL-new (thermorl/sim/kernels/thi.py), 2026-09-12.
from __future__ import annotations

import numpy as np


def t_steady(
    Q: np.ndarray,
    Q_max: np.ndarray,
    T_amb: np.ndarray,
    T_max: np.ndarray,
) -> np.ndarray:
    load = np.divide(Q, Q_max, out=np.zeros_like(Q, dtype=np.float32), where=Q_max != 0)
    return (T_amb + load * (T_max - T_amb)).astype(np.float32)
