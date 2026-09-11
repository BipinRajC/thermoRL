from __future__ import annotations

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, first_feasible, pick


class FcfsNaivePolicy:
    policy_id = "fcfs_naive"
    policy_mode = "FCFS"

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        chosen = first_feasible(candidates)
        if chosen is None:
            return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")
        return pick(
            job_id,
            assign_action(chosen.zone_id),
            chosen,
            candidates,
            "FIRST_FEASIBLE",
            "capacity-only first feasible zone",
        )
