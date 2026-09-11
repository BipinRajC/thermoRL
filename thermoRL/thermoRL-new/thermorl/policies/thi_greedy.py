from __future__ import annotations

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, pick


class ThiGreedyPolicy:
    policy_id = "thi_greedy"
    policy_mode = "THI-Greedy"

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        feas = [c for c in candidates if c.feasible and c.thi_after_pred is not None]
        if not feas:
            return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")
        chosen = max(feas, key=lambda c: float(c.thi_after_pred))
        return pick(
            job_id,
            assign_action(chosen.zone_id),
            chosen,
            candidates,
            "MAX_THI_AFTER",
            "highest predicted post-placement THI",
        )
