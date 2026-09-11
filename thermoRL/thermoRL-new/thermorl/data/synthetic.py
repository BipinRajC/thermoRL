from __future__ import annotations

import numpy as np
import pandas as pd

from thermorl.data.pm100_calibrator import PAPER_MEAN_DURATION_S, PAPER_MEAN_POWER_KW

FACILITY_MW = 20.0


def arrival_rate_for_ratio(
    target_ratio: float,
    mean_power_kw: float = PAPER_MEAN_POWER_KW,
    mean_duration_s: float = PAPER_MEAN_DURATION_S,
) -> float:
    offered_mw = target_ratio * FACILITY_MW
    return offered_mw * 1000.0 / (mean_power_kw * mean_duration_s)


def offered_ratio(
    arrival_rate_jobs_s: float,
    mean_power_kw: float,
    mean_duration_s: float,
) -> float:
    offered_mw = arrival_rate_jobs_s * mean_power_kw * mean_duration_s / 1000.0
    return offered_mw / FACILITY_MW


def generate_calibrated_demand(
    target_offered_load_ratio: float,
    duration_s: float,
    seed: int,
    mean_power_kw: float = PAPER_MEAN_POWER_KW,
    mean_duration_s: float = PAPER_MEAN_DURATION_S,
    peak_multiplier: float = 1.0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rate = arrival_rate_for_ratio(target_offered_load_ratio, mean_power_kw, mean_duration_s)
    n = int(rng.poisson(rate * duration_s))
    if n == 0:
        n = 1
    arrivals = np.sort(rng.uniform(0.0, duration_s, size=n))
    durations = rng.exponential(mean_duration_s, size=n)
    durations = np.clip(durations, 20.0, None)
    scale = mean_duration_s / float(durations.mean())
    durations = durations * scale
    powers = np.full(n, mean_power_kw, dtype=np.float64)
    nodes = np.maximum(1, np.round(powers / 7.775).astype(np.int32))
    return pd.DataFrame(
        {
            "event_id": [f"syn-{i:06d}" for i in range(n)],
            "arrival_s": arrivals,
            "duration_s": durations,
            "mean_power_kw": powers,
            "peak_power_kw": powers * 1.2,
            "nodes": nodes,
            "gpus": np.minimum(nodes * 2, 8),
            "gpu_milli": nodes * 1000,
            "cpu_milli": nodes * 4000,
            "mem_mib": nodes * 16384,
            "density_kw_per_node": powers / nodes,
            "workload_class": "training",
            "qos": "LS",
            "priority": 3,
            "eligible_zones": [(0, 1, 2)] * n,
        }
    )
