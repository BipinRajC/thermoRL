from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VizZone:
    id: int
    name: str
    THI: float
    T_c: float
    load_kw: float
    util: float
    PUE: float
    emergency: bool
    min_rack_thi: float
    rack_spread: float


@dataclass(frozen=True)
class VizEvent:
    type: str
    job_id: str | None = None
    zone: int | None = None
    rack: int | None = None
    decision_id: str | None = None
    defer_count: int | None = None


@dataclass(frozen=True)
class VizMetrics:
    jobs_completed: int
    mean_wait_s: float
    slo_compliance: float
    violations_per_1k_jobs: float
    hotspot_minutes_per_1k_jobs: float
    emergency_events_per_1k_jobs: float
    kg_co2_per_job: float
    kwh_cooling_per_job: float
    offered_demand_ratio: float
    physical_facility_load_kw: float


@dataclass(frozen=True)
class VizFrame:
    t: int
    sim_time_s: float
    regime: str
    policy_mode: str
    zones: tuple[VizZone, ...]
    racks: tuple[tuple[dict[str, float], ...], ...]
    events: tuple[VizEvent, ...]
    metrics: VizMetrics
    advanced: dict[str, Any]
