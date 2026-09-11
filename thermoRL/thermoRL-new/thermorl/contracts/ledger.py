from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from thermorl.contracts.decision import ACTIONS, Action, Candidate


@dataclass(frozen=True)
class JobFeatures:
    mean_power_kw: float
    duration_s: float
    nodes: int
    gpus: int
    density_kw_per_node: float
    workload_class: str
    qos: str
    priority: int
    wait_time_s: float


@dataclass(frozen=True)
class LedgerAmbientState:
    t_amb_c: tuple[float, ...]
    carbon_intensity: float


@dataclass(frozen=True)
class LedgerZoneState:
    T_c: float
    Q_kw: float
    d: float
    THI: float
    util: float
    PUE: float
    min_rack_thi: float
    rack_spread: float
    emergency_active: bool


@dataclass(frozen=True)
class LedgerOutcome:
    horizon_ticks: int
    thi_actual_h: tuple[float, ...]
    thi_predicted_h: tuple[float, ...]
    prediction_error: tuple[float, ...]
    emergency_triggered_within_h: bool
    regret_vs_best_counterfactual: float
    job_completed: bool
    job_completion_s: float | None


@dataclass(frozen=True)
class LedgerRow:
    decision_id: str
    run_id: str
    episode_id: str
    scenario_id: str
    scenario_mode: Literal["demo", "evaluation", "stress"]
    seed: int
    backend: str
    sim_time_s: float
    tick: int
    wall_time_ms: float
    policy_id: str
    policy_mode: str
    policy_version: str
    job_id: str
    job_features: JobFeatures
    ambient_state: LedgerAmbientState
    eligible_zones: tuple[int, ...]
    action: Action
    chosen_zone: int | None
    chosen_rack: int | None
    rack_rule_id: str
    candidates: tuple[Candidate, ...]
    zone_state_before: tuple[LedgerZoneState, ...]
    rack_state_before: tuple[tuple[dict[str, float], ...], ...]
    predicted_post_action_state: tuple[dict[str, float], ...]
    lambdas: dict[str, float]
    constraint_slack: dict[str, float]
    reward_components: dict[str, float]
    reason_code: str
    reason_text: str
    counterfactual_zone: int | None
    counterfactual_delta_thi: float | None
    emergency_cooling_active: tuple[bool, ...]
    defer_count: int
    next_eligible_s: float | None
    forced_placement_flag: bool
    queue_depth: int
    arrival_rate_est: float
    outcome: LedgerOutcome | None

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"action must be one of {sorted(ACTIONS)}, got {self.action!r}")

    def to_jsonable(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> LedgerRow:
        data = dict(payload)
        data["job_features"] = JobFeatures(**data["job_features"])
        data["ambient_state"] = LedgerAmbientState(
            t_amb_c=tuple(data["ambient_state"]["t_amb_c"]),
            carbon_intensity=data["ambient_state"]["carbon_intensity"],
        )
        data["eligible_zones"] = tuple(data["eligible_zones"])
        data["candidates"] = tuple(Candidate(**c) for c in data["candidates"])
        data["zone_state_before"] = tuple(LedgerZoneState(**z) for z in data["zone_state_before"])
        data["rack_state_before"] = tuple(
            tuple(r for r in zone) for zone in data["rack_state_before"]
        )
        data["predicted_post_action_state"] = tuple(data["predicted_post_action_state"])
        data["emergency_cooling_active"] = tuple(data["emergency_cooling_active"])
        if data.get("outcome") is not None:
            oc = dict(data["outcome"])
            oc["thi_actual_h"] = tuple(oc["thi_actual_h"])
            oc["thi_predicted_h"] = tuple(oc["thi_predicted_h"])
            oc["prediction_error"] = tuple(oc["prediction_error"])
            data["outcome"] = LedgerOutcome(**oc)
        return cls(**data)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value
