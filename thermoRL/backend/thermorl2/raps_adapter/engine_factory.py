"""Construct RAPS without cooling; expose its system-specific power ticks."""

from dataclasses import dataclass

import numpy as np
from raps.engine import Engine
from raps.sim_config import SingleSimConfig

from thermorl2.raps_adapter.power_model import legacy_config


@dataclass(frozen=True)
class EngineSpec:
    system: str
    sim_time: str = "6h"
    seed: int = 1


def build_engine(spec: EngineSpec, jobs=None) -> Engine:
    if spec.seed < 1:
        raise ValueError("seeds must be >= 1")
    delta = legacy_config(spec.system)["POWER_UPDATE_FREQ"]
    config = SingleSimConfig.model_validate({
        "system": spec.system, "time": spec.sim_time, "time_delta": f"{delta}s",
        "seed": spec.seed, "noui": True, "output": "none", "cooling": False,
        "scheduler": "default", "policy": "fcfs", "workload": "random", "numjobs": 1,
    })
    engine = Engine(config)
    if jobs is not None:
        engine.jobs = list(jobs)
        engine.total_initial_jobs = len(engine.jobs)
    assert engine.timestep_start == 0
    assert engine.time_delta == delta
    return engine


def rack_kw_from_power_df(power_df, racks_per_cdu: int) -> np.ndarray:
    columns = [f"Rack {i}" for i in range(1, racks_per_cdu + 1)]
    return power_df[columns].to_numpy(dtype=np.float64).reshape(-1)


def is_power_tick(tick, time_delta: int) -> bool:
    return tick.current_timestep % time_delta == 0
