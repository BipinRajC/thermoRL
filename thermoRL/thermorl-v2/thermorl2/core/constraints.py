from __future__ import annotations

import numpy as np

THI_MIN, THI_MAX = -0.5, 1.0


def _safe_div(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64))
    return np.divide(a, b, out=np.zeros_like(a), where=b != 0)


def thi_headroom(t_c, t_idle_c, t_max_c, p_kw, p_max_kw):
    """Baseline-normalised headroom index (spec §7 primary). 1.0 at idle & zero power, 0.0 at limit."""
    t_term = _safe_div(np.asarray(t_c) - np.asarray(t_idle_c), np.asarray(t_max_c) - np.asarray(t_idle_c))
    p_term = _safe_div(p_kw, p_max_kw)
    return np.clip(1.0 - np.maximum(t_term, p_term), THI_MIN, THI_MAX)


def thi_paper_raw(t_c, t_max_c, p_kw, p_max_kw):
    """Paper eq. 1 without the degradation term: 1 - max(T/Tmax, P/Pmax), T in degC."""
    return np.clip(1.0 - np.maximum(_safe_div(t_c, t_max_c), _safe_div(p_kw, p_max_kw)), THI_MIN, THI_MAX)


def compute_thi(form: str, *, t_c, t_max_c, p_kw, p_max_kw, t_idle_c=None):
    if form == "headroom":
        if t_idle_c is None:
            raise ValueError("headroom form requires t_idle_c")
        return thi_headroom(t_c, t_idle_c, t_max_c, p_kw, p_max_kw)
    if form == "paper_raw":
        return thi_paper_raw(t_c, t_max_c, p_kw, p_max_kw)
    raise ValueError(f"unknown thi form {form!r}")


def hinge(thi, eps: float):
    return np.maximum(0.0, eps - np.asarray(thi, dtype=np.float64))


def violation(thi, eps: float):
    return np.asarray(thi) < eps
