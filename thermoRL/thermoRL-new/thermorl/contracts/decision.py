from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["ASSIGN_Z1", "ASSIGN_Z2", "ASSIGN_Z3", "DEFER"]
ACTIONS: frozenset[str] = frozenset({"ASSIGN_Z1", "ASSIGN_Z2", "ASSIGN_Z3", "DEFER"})


@dataclass(frozen=True)
class Candidate:
    zone_id: int
    rack_id: int
    feasible: bool
    infeasible_reason: str | None
    thi_before: float
    thi_after_pred: float | None
    delta_thi: float | None
    cooling_cost_kw: float | None
    carbon_cost_kg: float | None
    constraint_slack: float
    lookahead_score: float | None


@dataclass(frozen=True)
class Decision:
    job_id: str
    action: Action
    chosen_zone: int | None
    chosen_rack: int | None
    rack_rule_id: str
    candidates: tuple[Candidate, ...]
    reason_code: str
    reason_text: str

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"action must be one of {sorted(ACTIONS)}, got {self.action!r}")


@dataclass(frozen=True)
class Placement:
    job_id: str
    zone_id: int
    rack_id: int
