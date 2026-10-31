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


def thi_batch(
    T: np.ndarray,
    T_ss: np.ndarray,
    d: np.ndarray,
    T_max: np.ndarray,
    d_max: np.ndarray,
) -> np.ndarray:
    t_ratio = np.divide(T, T_max, out=np.zeros_like(T, dtype=np.float32), where=T_max != 0)
    ss_ratio = np.divide(T_ss, T_max, out=np.zeros_like(T_ss, dtype=np.float32), where=T_max != 0)
    d_ratio = np.divide(d, d_max, out=np.zeros_like(d, dtype=np.float32), where=d_max != 0)
    return (1.0 - np.maximum(np.maximum(t_ratio, ss_ratio), d_ratio)).astype(np.float32)


def thi_zone(thi_racks: np.ndarray) -> np.ndarray:
    return np.min(thi_racks, axis=-1).astype(np.float32)
