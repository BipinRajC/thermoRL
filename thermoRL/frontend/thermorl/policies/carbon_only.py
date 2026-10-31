from __future__ import annotations

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, pick


class CarbonOnlyPolicy:
    policy_id = "carbon_only"
    policy_mode = "Carbon-Only"

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        feas = [c for c in candidates if c.feasible and c.carbon_cost_kg is not None]
        if not feas:
            return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")
        chosen = min(feas, key=lambda c: float(c.carbon_cost_kg))
        return pick(
            job_id,
            assign_action(chosen.zone_id),
            chosen,
            candidates,
            "MIN_CARBON",
            "lowest carbon times PUE; thermally blind",
        )
