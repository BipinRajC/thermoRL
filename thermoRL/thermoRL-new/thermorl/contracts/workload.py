from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class BatchJobEvent:
    event_id: str
    arrival_s: float
    duration_s: float
    power_profile_kw: np.ndarray
    mean_power_kw: float
    peak_power_kw: float
    nodes: int
    gpus: int
    gpu_milli: int
    cpu_milli: int
    mem_mib: int
    density_kw_per_node: float
    workload_class: str
    qos: str
    priority: int
    eligible_zones: tuple[int, ...]
    kind: Literal["batch"] = "batch"


@dataclass(frozen=True)
class RequestEvent:
    event_id: str
    arrival_s: float
    model_class: str
    tokens_in: int
    tokens_out: int
    slo_ms: float
    kind: Literal["request"] = "request"


WorkloadEvent = BatchJobEvent | RequestEvent
