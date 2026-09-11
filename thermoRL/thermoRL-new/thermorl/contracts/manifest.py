from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageManifest:
    stage: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    target_offered_load_ratio: float
    realised_offered_load_ratio: float | None
    seed: int


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    seed: int
    scenario_id: str
    policy_id: str
    backend: str
    target_offered_load_ratio: float
    workload_source: str
    power_calibration_source: str
    facility_capacity_kw: float
    arrival_process: str
    scaling_method: str
    realised_offered_load_ratio: float | None = None
    target_offered_load_ratio_off_peak: float | None = None
    target_offered_load_ratio_peak: float | None = None
    arrival_rate_jobs_per_s: float | None = None
    peak_arrival_multiplier: float | None = None
    mean_job_power_kw: float | None = None
    mean_duration_s: float | None = None
    step_s: float | None = None
    git_sha: str | None = None
