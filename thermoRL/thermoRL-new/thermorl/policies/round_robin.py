from __future__ import annotations

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, pick


class RoundRobinPolicy:
    policy_id = "round_robin"
    policy_mode = "Round-Robin"

    def __init__(self) -> None:
        self._cursor = 0

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        n = len(candidates)
        for i in range(n):
            idx = (self._cursor + i) % n
            c = candidates[idx]
            if c.feasible:
                self._cursor = (idx + 1) % n
                return pick(
                    job_id,
                    assign_action(c.zone_id),
                    c,
                    candidates,
                    "ROUND_ROBIN",
                    "thermally blind rotation",
                )
        return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")
