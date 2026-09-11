from __future__ import annotations

import numpy as np

from thermorl.contracts.decision import Candidate
from thermorl.contracts.state import SimState
from thermorl.sim.config import N_ZONES, FacilityConfig
from thermorl.sim.engine import step
from thermorl.sim.kernels.heat import heat_inject
from thermorl.sim.kernels.thi import t_steady, thi_batch, thi_zone


def _min_thi(state: SimState, cfg: FacilityConfig) -> float:
    racks = state.rack_T_c.shape[1]
    q_max = np.repeat(cfg.q_max_rack_kw.reshape(N_ZONES, 1), racks, axis=1)
    t_max = np.repeat(cfg.t_max_c.reshape(N_ZONES, 1), racks, axis=1)
    t_amb = np.repeat(state.zone_T_amb_c.reshape(N_ZONES, 1), racks, axis=1)
    d_max = np.repeat(cfg.d_max.reshape(N_ZONES, 1), racks, axis=1)
    t_ss = t_steady(state.rack_Q_kw, q_max, t_amb, t_max)
    return float(thi_zone(thi_batch(state.rack_T_c, t_ss, state.rack_d, t_max, d_max)).min())


def rollout_scores(
    state: SimState,
    candidates: tuple[Candidate, ...],
    cfg: FacilityConfig,
    mean_power_kw: float,
    horizon: int,
    dt_s: float,
    n_samples: int = 1,
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for c in candidates:
        if not c.feasible:
            continue
        acc = 0.0
        for _ in range(n_samples):
            s = state.clone()
            s.rack_Q_kw = heat_inject(s.rack_Q_kw, c.zone_id, c.rack_id, mean_power_kw)
            for _tick in range(horizon):
                s = step(s, (), cfg, dt_s=dt_s, job_power_kw=0.0)
            acc += _min_thi(s, cfg)
        scores[c.zone_id] = acc / n_samples
    return scores
