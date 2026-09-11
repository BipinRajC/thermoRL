from __future__ import annotations

import numpy as np

from thermorl.contracts.decision import Placement
from thermorl.contracts.state import MetricsAccumulator, SimState
from thermorl.sim.config import N_ZONES, FacilityConfig
from thermorl.sim.emergency import update_emergency
from thermorl.sim.kernels.degradation import degradation_step
from thermorl.sim.kernels.heat import heat_inject
from thermorl.sim.kernels.pue import pue_effective
from thermorl.sim.kernels.rc import rc_step
from thermorl.sim.kernels.thi import t_steady, thi_batch, thi_zone

__all__ = ["FacilityConfig", "step"]


def _broadcast_zone(values: np.ndarray, racks: int) -> np.ndarray:
    return np.repeat(values.reshape(N_ZONES, 1), racks, axis=1)


def _emergency_since(acc: MetricsAccumulator, n_zones: int) -> np.ndarray:
    raw = getattr(acc, "emergency_on_s", None)
    if raw is None:
        return np.full(n_zones, -1.0, dtype=np.float32)
    return np.asarray(raw, dtype=np.float32).copy()


def step(
    state: SimState,
    placements: tuple[Placement, ...],
    cfg: FacilityConfig,
    dt_s: float,
    job_power_kw: float = 0.0,
) -> SimState:
    s = state.clone()
    racks = s.rack_T_c.shape[1]
    for p in placements:
        s.rack_Q_kw = heat_inject(s.rack_Q_kw, p.zone_id, p.rack_id, job_power_kw)

    t_amb_z = cfg.t_amb_base_c + cfg.t_amb_amplitude_c * np.sin(
        2.0 * np.pi * (s.sim_time_s - cfg.ambient_phase_s) / cfg.ambient_period_s
    )
    s.zone_T_amb_c = t_amb_z.astype(np.float32)

    q_max = _broadcast_zone(cfg.q_max_rack_kw, racks)
    t_max = _broadcast_zone(cfg.t_max_c, racks)
    tau = _broadcast_zone(cfg.tau_s, racks)
    t_amb = _broadcast_zone(s.zone_T_amb_c, racks)
    rate = _broadcast_zone(cfg.degradation_rate, racks)
    recov = _broadcast_zone(cfg.degradation_recovery, racks)
    d_max = _broadcast_zone(cfg.d_max, racks)

    t_ss = t_steady(s.rack_Q_kw, q_max, t_amb, t_max)
    s.rack_T_c = rc_step(s.rack_T_c, t_ss, tau, dt_s)
    s.rack_d = degradation_step(s.rack_d, s.rack_T_c, t_amb, t_max, rate, recov, dt_s)
    thi = thi_batch(s.rack_T_c, t_ss, s.rack_d, t_max, d_max)
    thi_z = thi_zone(thi)

    since = _emergency_since(s.acc, N_ZONES)
    s.zone_emergency, since, n_new = update_emergency(
        thi_z, s.zone_emergency, since, s.sim_time_s, cfg
    )
    events = int(getattr(s.acc, "emergency_events", 0)) + n_new
    s.acc = MetricsAccumulator()
    s.acc.emergency_on_s = since
    s.acc.emergency_events = events

    t_zone = s.rack_T_c.max(axis=1)
    pue = pue_effective(
        t_zone, s.zone_T_amb_c, cfg.t_max_c, cfg.pue_base, cfg.k_z, cfg.pue_theta, cfg.pue_p
    )
    s.zone_pue_eff = np.where(s.zone_emergency, cfg.pue_emergency, pue).astype(np.float32)
    s.rack_util = np.divide(
        s.rack_Q_kw, q_max, out=np.zeros_like(s.rack_Q_kw), where=q_max != 0
    ).astype(np.float32)

    s.tick = s.tick + 1
    s.sim_time_s = s.sim_time_s + dt_s
    return s
