from __future__ import annotations

import numpy as np

K_B_EV_PER_K = 8.617333262145e-5
EA_EV_DEFAULT = 0.7
T_REF_C_DEFAULT = 40.0
STRESS_THRESHOLD = 0.85


def arrhenius(
    t_c: float | np.ndarray,
    ea_ev: float = EA_EV_DEFAULT,
    t_ref_c: float = T_REF_C_DEFAULT,
) -> float | np.ndarray:
    t_k = np.asarray(t_c, dtype=np.float64) + 273.15
    t_ref_k = t_ref_c + 273.15
    ratio = np.exp(-ea_ev / (K_B_EV_PER_K * t_k)) / np.exp(-ea_ev / (K_B_EV_PER_K * t_ref_k))
    if np.ndim(t_c) == 0:
        return float(ratio)
    return ratio.astype(np.float32)


def degradation_step(
    d: np.ndarray,
    T: np.ndarray,
    T_amb: np.ndarray,
    T_max: np.ndarray,
    rate: np.ndarray,
    recovery: np.ndarray,
    dt_s: float,
    ea_ev: float = EA_EV_DEFAULT,
    t_ref_c: float = T_REF_C_DEFAULT,
    stress_threshold: float = STRESS_THRESHOLD,
) -> np.ndarray:
    span = T_max - T_amb
    s = np.divide(T - T_amb, span, out=np.zeros_like(T, dtype=np.float32), where=span != 0)
    arr = arrhenius(T, ea_ev=ea_ev, t_ref_c=t_ref_c)
    accrue = rate * np.maximum(s - stress_threshold, 0.0) * arr * dt_s
    recover = recovery * dt_s
    hot = s > stress_threshold
    nxt = np.where(hot, d + accrue, d - recover)
    return np.clip(nxt, 0.0, 1.0).astype(np.float32)
