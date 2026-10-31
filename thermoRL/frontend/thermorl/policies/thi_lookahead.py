from __future__ import annotations

from dataclasses import replace

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, pick
from thermorl.sim.config import FacilityConfig
from thermorl.sim.rollout import rollout_scores


class ThiLookaheadPolicy:
    policy_id = "thi_lookahead"
    policy_mode = "THI-Lookahead"

    def __init__(self, horizon: int = 10, dt_s: float = 20.0, n_samples: int = 1) -> None:
        self.horizon = horizon
        self.dt_s = dt_s
        self.n_samples = n_samples

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        cfg: FacilityConfig = ctx["cfg"]
        mean_power_kw = float(ctx["mean_power_kw"])
        feas = [c for c in candidates if c.feasible]
        if not feas:
            return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")
        scores = rollout_scores(
            state,
            candidates,
            cfg,
            mean_power_kw=mean_power_kw,
            horizon=self.horizon,
            dt_s=self.dt_s,
            n_samples=self.n_samples,
        )
        scored = tuple(
            replace(c, lookahead_score=scores.get(c.zone_id)) if c.feasible else c
            for c in candidates
        )
        best = max(
            (c for c in scored if c.feasible), key=lambda c: float(c.lookahead_score or -1e9)
        )
        return pick(
            job_id,
            assign_action(best.zone_id),
            best,
            scored,
            "MAX_LOOKAHEAD_SCORE",
            f"preserves the most min-THI over {self.horizon} ticks",
        )
