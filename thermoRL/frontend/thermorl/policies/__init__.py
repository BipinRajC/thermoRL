from __future__ import annotations

from thermorl.policies.carbon_only import CarbonOnlyPolicy
from thermorl.policies.fcfs_naive import FcfsNaivePolicy
from thermorl.policies.oracle_lp import OracleLpPolicy
from thermorl.policies.round_robin import RoundRobinPolicy
from thermorl.policies.thi_greedy import ThiGreedyPolicy
from thermorl.policies.thi_lookahead import ThiLookaheadPolicy
from thermorl.policies.threshold_reactive import ThresholdReactivePolicy

_POLICIES = {
    "fcfs_naive": FcfsNaivePolicy,
    "round_robin": RoundRobinPolicy,
    "threshold_reactive": ThresholdReactivePolicy,
    "carbon_only": CarbonOnlyPolicy,
    "thi_greedy": ThiGreedyPolicy,
    "thi_lookahead": ThiLookaheadPolicy,
    "oracle_lp": OracleLpPolicy,
}

POLICY_IDS: frozenset[str] = frozenset(_POLICIES)


def get_policy(policy_id: str):
    return _POLICIES[policy_id]()
