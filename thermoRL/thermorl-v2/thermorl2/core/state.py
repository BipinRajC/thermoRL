from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Ambient:
    t_air_k: float = 290.0
    t_ext_k: float = 290.0
    t_air_k_by_unit: tuple[float, ...] | None = None


@dataclass
class RackResource:
    free_nodes: np.ndarray
    total_nodes: np.ndarray
    power_kw: np.ndarray
    n_running: np.ndarray
    t_next_limit_s: np.ndarray


@dataclass
class RackThermal:
    t_c: np.ndarray
    extras: dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class GlobalFeatures:
    sim_time_s: float
    total_power_kw: float
    queue_depth: int
    queued_power_kw: float
    backend: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class JobRequest:
    job_id: int
    nodes_required: int
    est_power_per_node_kw: float
    time_limit_s: float
    wait_s: float
    priority: int
    defer_count: int


@dataclass
class Observation:
    rack: RackResource
    thermal: RackThermal
    thi: np.ndarray
    glob: GlobalFeatures


@dataclass(frozen=True)
class Scores:
    rack: np.ndarray
    defer: float


@dataclass(frozen=True)
class Placement:
    racks: tuple[int, ...]
    nodes: tuple[int, ...]
    rule: str


DEFER = Placement(racks=(), nodes=(), rule="defer")
