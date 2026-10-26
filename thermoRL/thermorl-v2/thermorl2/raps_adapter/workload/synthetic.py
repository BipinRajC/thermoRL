"""The fixed synthetic distribution from design spec §3.4."""

from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd


WORKLOAD_COLUMNS = ["id", "nodes_required", "cpu_util", "gpu_util", "submit_time", "expected_run_time", "time_limit"]


@dataclass(frozen=True)
class SyntheticSpec:
    rho: float = 0.6
    node_sizes: tuple = (1, 2, 4, 8, 16, 32)
    node_weights: tuple = (0.35, 0.2, 0.2, 0.12, 0.09, 0.04)
    runtime_median_s: float = 1800
    runtime_sigma: float = 0.8
    runtime_clip_s: tuple = (300, 14400)
    cpu_choices: tuple = (0.5, 1.0, 1.5, 2.0)
    limit_factor: float = 1.5

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def represented_runtimes(draws, spec: SyntheticSpec):
    """Approved R4 representation, shared by MC expectations and actual jobs."""
    return np.ceil(np.clip(draws, *spec.runtime_clip_s)).astype(np.int64)


def generate(spec: SyntheticSpec, seed, horizon_s, n_nodes, gpus_per_node) -> pd.DataFrame:
    if seed < 1 or horizon_s <= 0 or n_nodes < 1:
        raise ValueError("positive seed, horizon and node count required")
    rng = np.random.default_rng(seed)
    mc_nodes = rng.choice(spec.node_sizes, size=1_000_000, p=spec.node_weights)
    mc_runtime = represented_runtimes(rng.lognormal(np.log(spec.runtime_median_s), spec.runtime_sigma, size=1_000_000), spec)
    expected_node_seconds = float(np.mean(mc_nodes * mc_runtime))
    rate = spec.rho * n_nodes / expected_node_seconds
    rows = []
    submit = 0.0
    while True:
        submit += float(rng.exponential(1 / rate))
        if submit >= horizon_s:
            break
        nodes = int(rng.choice(spec.node_sizes, p=spec.node_weights))
        # RAPS advances on integer seconds. Represent the clipped duration at
        # the next second, identically in the MC expectation and actual jobs.
        runtime = int(represented_runtimes(rng.lognormal(np.log(spec.runtime_median_s), spec.runtime_sigma), spec))
        cpu = float(rng.choice(spec.cpu_choices))
        gpu = int(rng.integers(0, gpus_per_node + 1))
        limit = int(np.ceil(runtime * spec.limit_factor))
        assert limit >= runtime
        rows.append((len(rows), nodes, cpu, gpu, submit, runtime, limit))
    frame = pd.DataFrame(rows, columns=WORKLOAD_COLUMNS)
    frame.attrs = {"seed": int(seed), "spec": asdict(spec), "mc_samples": 1_000_000, "mc_expected_node_seconds": expected_node_seconds,
                   "arrival_rate_per_s": rate, "representation": "clipped lognormal rounded upward to one-second RAPS resolution; continuous submit times admitted at ceil(submit); completion occupancy adds one second",
                   "rng_draw_order": "MC node sizes; MC durations; then per job: interarrival, nodes, duration, cpu, gpu",
                   "generator_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "versions": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "pyarrow")}}
    assert (frame.time_limit >= frame.expected_run_time).all()
    return frame


def offered_utilisation(frame, horizon_s, n_nodes, window_start_s=3600) -> float:
    overlaps = np.maximum(0, np.minimum(frame.submit_time + frame.expected_run_time, horizon_s) - np.maximum(frame.submit_time, window_start_s))
    return float(np.sum(frame.nodes_required * overlaps) / ((horizon_s - window_start_s) * n_nodes))


def write_workload(frame, path, meta) -> str:
    path = Path(path)
    contents = frame.to_parquet(index=False)
    digest = hashlib.sha256(contents).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise FileExistsError(f"refusing to replace workload content: {path}")
    else:
        with path.open("xb") as output:
            output.write(contents)
    sidecar = Path(str(path) + ".meta.json")
    if not sidecar.exists():
        sidecar.write_text(json.dumps({**meta, **frame.attrs, "sha256": digest}, indent=2, sort_keys=True) + "\n")
    else:
        assert json.loads(sidecar.read_text())["sha256"] == digest
    return digest
