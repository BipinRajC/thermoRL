from __future__ import annotations

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, pick


class ThresholdReactivePolicy:
    policy_id = "threshold_reactive"
    policy_mode = "Threshold-Reactive"

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        safe = [c for c in candidates if c.feasible and c.thi_before >= 0.10]
        pool = safe or [c for c in candidates if c.feasible]
        if not pool:
            return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")
        chosen = max(pool, key=lambda c: c.thi_before)
        return pick(
            job_id,
            assign_action(chosen.zone_id),
            chosen,
            candidates,
            "THRESHOLD",
            "exclude zones already below epsilon if any remain",
        )
