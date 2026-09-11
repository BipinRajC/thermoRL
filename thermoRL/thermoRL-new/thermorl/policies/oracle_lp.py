from __future__ import annotations

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.policies.base import assign_action, pick


class OracleLpPolicy:
    policy_id = "oracle_lp"
    policy_mode = "Oracle-LP"

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision:
        job_id = ctx["job_id"]
        feas = [c for c in candidates if c.feasible]
        if not feas:
            return pick(job_id, "DEFER", None, candidates, "NO_CAPACITY", "no feasible zone")

        def score(c: Candidate) -> tuple[float, float]:
            thi = float(c.thi_after_pred) if c.thi_after_pred is not None else -1.0
            carbon = float(c.carbon_cost_kg) if c.carbon_cost_kg is not None else 0.0
            return (thi, -carbon)

        chosen = max(feas, key=score)
        return pick(
            job_id,
            assign_action(chosen.zone_id),
            chosen,
            candidates,
            "ORACLE_BOUND",
            "offline bound: max predicted THI then min carbon",
        )
