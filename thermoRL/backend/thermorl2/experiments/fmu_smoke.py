"""Run exactly one system's smoke test in a fresh OS process."""

import argparse
import json
from time import perf_counter

import numpy as np

from thermorl2.core.state import Ambient
from thermorl2.experiments.provenance import sha256_file
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.raps_adapter.power_model import legacy_config, rack_power_bounds
from thermorl2.raps_adapter.systems import SYSTEMS, get_system, repo_root
from thermorl2.thermal.fmu_backend import FmuBackend


def smoke(system: str) -> dict:
    start = perf_counter()
    spec = get_system(system)
    path = repo_root() / spec.fmu_path
    actual_sha = sha256_file(path)
    if actual_sha != spec.fmu_sha256:
        raise ValueError(f"FMU hash mismatch for {system}: {actual_sha}")
    cfg = legacy_config(system)
    idle, peak = rack_power_bounds(cfg)
    backend = FmuBackend(path, CouplingParams.from_legacy_config(cfg))
    try:
        used = backend.warm_up(np.full(backend.n_units, idle), Ambient(), dt_s=cfg["POWER_UPDATE_FREQ"], max_s=600)
        observation = backend.observe()
        finite = all(np.isfinite(v).all() for v in [observation.t_c, *observation.extras.values(), list(backend.global_observe().values())])
        report = {"system": system, "n_units": backend.n_units, "t_c_min": float(observation.t_c.min()), "t_c_max": float(observation.t_c.max()), "finite": bool(finite), "idle_kw": idle, "peak_kw": peak, "warmup_used_s": used, "fmu_sha256": actual_sha}
    finally:
        backend.close()
    report["wall_s"] = perf_counter() - start
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=SYSTEMS, required=True)
    args = parser.parse_args()
    print(json.dumps(smoke(args.system), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
