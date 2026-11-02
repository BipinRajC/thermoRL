from __future__ import annotations

from dataclasses import dataclass

import numpy as np

N_ZONES = 3
LAMBDA_DIM = 5


@dataclass
class JobQueue:
    pass


@dataclass
class RunningSet:
    pass


@dataclass
class MetricsAccumulator:
    pass


@dataclass(frozen=True)
class ZoneState:
    zone_id: int
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
class RackState:
    rack_id: int
    T_c: float
    Q_kw: float
    d: float
    THI: float
    util: float


@dataclass(frozen=True)
class AmbientState:
    t_amb_c: tuple[float, ...]
    carbon_intensity: float


@dataclass
class SimState:
    tick: int
    sim_time_s: float
    rack_T_c: np.ndarray
    rack_Q_kw: np.ndarray
    rack_d: np.ndarray
    rack_util: np.ndarray
    zone_T_amb_c: np.ndarray
    zone_pue_eff: np.ndarray
    zone_emergency: np.ndarray
    queue: JobQueue
    running: RunningSet
    carbon_intensity: float
    lambdas: np.ndarray
    rng: np.random.Generator
    acc: MetricsAccumulator

    @classmethod
    def empty(cls, racks_per_zone: int, seed: int) -> SimState:
        zr = (N_ZONES, racks_per_zone)
        return cls(
            tick=0,
            sim_time_s=0.0,
            rack_T_c=np.zeros(zr, dtype=np.float32),
            rack_Q_kw=np.zeros(zr, dtype=np.float32),
            rack_d=np.zeros(zr, dtype=np.float32),
            rack_util=np.zeros(zr, dtype=np.float32),
            zone_T_amb_c=np.zeros(N_ZONES, dtype=np.float32),
            zone_pue_eff=np.ones(N_ZONES, dtype=np.float32),
            zone_emergency=np.zeros(N_ZONES, dtype=bool),
            queue=JobQueue(),
            running=RunningSet(),
            carbon_intensity=0.0,
            lambdas=np.zeros(LAMBDA_DIM, dtype=np.float32),
            rng=np.random.default_rng(seed),
            acc=MetricsAccumulator(),
        )

    def clone(self) -> SimState:
        return SimState(
            tick=self.tick,
            sim_time_s=self.sim_time_s,
            rack_T_c=self.rack_T_c.copy(),
            rack_Q_kw=self.rack_Q_kw.copy(),
            rack_d=self.rack_d.copy(),
            rack_util=self.rack_util.copy(),
            zone_T_amb_c=self.zone_T_amb_c.copy(),
            zone_pue_eff=self.zone_pue_eff.copy(),
            zone_emergency=self.zone_emergency.copy(),
            queue=self.queue,
            running=self.running,
            carbon_intensity=self.carbon_intensity,
            lambdas=self.lambdas.copy(),
            rng=self.rng.spawn(1)[0],
            acc=self.acc,
        )
