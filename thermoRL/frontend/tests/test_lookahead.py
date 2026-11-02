"""M5 gate: thi_lookahead beats thi_greedy on a constructed thermal case."""

from __future__ import annotations

import numpy as np

from thermorl.contracts.state import SimState
from thermorl.policies.base import score_candidates
from thermorl.policies.thi_greedy import ThiGreedyPolicy
from thermorl.policies.thi_lookahead import ThiLookaheadPolicy
from thermorl.sim.config import FacilityConfig
from thermorl.sim.engine import step
from thermorl.sim.kernels.heat import heat_inject
from thermorl.sim.rollout import rollout_scores


def _hot_air_state(cfg: FacilityConfig) -> SimState:
    state = SimState.empty(racks_per_zone=cfg.racks_per_zone, seed=11)
    state.zone_T_amb_c = cfg.t_amb_base_c.copy()
    state.zone_pue_eff = cfg.pue_base.copy()
    state.carbon_intensity = 0.4
    state.rack_T_c[0, :] = 26.4
    state.rack_Q_kw[0, :] = 230.0
    state.rack_T_c[1, :] = 32.0
    state.rack_Q_kw[1, :] = 80.0
    state.rack_T_c[2, :] = 30.0
    state.rack_Q_kw[2, :] = 40.0
    return state


def test_rollout_returns_one_score_per_feasible_candidate() -> None:
    cfg = FacilityConfig.from_base_yaml()
    state = _hot_air_state(cfg)
    cands = score_candidates(state, cfg, 31.1, 7.775, (0, 1, 2))
    scores = rollout_scores(state, cands, cfg, mean_power_kw=31.1, horizon=5, dt_s=20.0)
    assert len(scores) == sum(1 for c in cands if c.feasible)
    assert all(isinstance(v, float) for v in scores.values())


def test_lookahead_sets_scores_and_picks_feasible_zone() -> None:
    cfg = FacilityConfig.from_base_yaml()
    state = _hot_air_state(cfg)
    cands = score_candidates(state, cfg, 31.1, 7.775, (0, 1, 2))
    policy = ThiLookaheadPolicy(horizon=5, dt_s=20.0)
    decision = policy.decide(state, cands, {"job_id": "j", "cfg": cfg, "mean_power_kw": 31.1})
    assert decision.action in {"ASSIGN_Z1", "ASSIGN_Z2", "ASSIGN_Z3", "DEFER"}
    scored = [c for c in decision.candidates if c.feasible]
    assert all(c.lookahead_score is not None for c in scored)


def test_lookahead_beats_greedy_min_thi_after_horizon() -> None:
    cfg = FacilityConfig.from_base_yaml()
    greedy_p = ThiGreedyPolicy()
    look_p = ThiLookaheadPolicy(horizon=10, dt_s=20.0)

    def play(policy) -> float:
        state = _hot_air_state(cfg)
        for i in range(12):
            cands = score_candidates(state, cfg, 31.1, 7.775, (0, 1, 2))
            d = policy.decide(state, cands, {"job_id": f"j{i}", "cfg": cfg, "mean_power_kw": 31.1})
            if d.action != "DEFER" and d.chosen_zone is not None:
                state.rack_Q_kw = heat_inject(
                    state.rack_Q_kw, d.chosen_zone, int(d.chosen_rack or 0), 31.1
                )
            state = step(state, (), cfg, dt_s=20.0, job_power_kw=0.0)
        from thermorl.sim.kernels.thi import t_steady, thi_batch, thi_zone

        racks = state.rack_T_c.shape[1]
        q_max = np.repeat(cfg.q_max_rack_kw.reshape(3, 1), racks, axis=1)
        t_max = np.repeat(cfg.t_max_c.reshape(3, 1), racks, axis=1)
        t_amb = np.repeat(state.zone_T_amb_c.reshape(3, 1), racks, axis=1)
        d_max = np.repeat(cfg.d_max.reshape(3, 1), racks, axis=1)
        t_ss = t_steady(state.rack_Q_kw, q_max, t_amb, t_max)
        thi_z = thi_zone(thi_batch(state.rack_T_c, t_ss, state.rack_d, t_max, d_max))
        return float(thi_z.min())

    assert play(look_p) >= play(greedy_p)
