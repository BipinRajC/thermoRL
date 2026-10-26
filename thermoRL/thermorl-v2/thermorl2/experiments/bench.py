"""Isolated Task 5 idle RAPS+FMU benchmark and approved D2 cost guard.

A lightweight parent measures the complete lifetime of one simulation worker,
including interpreter startup/imports, FMU initialization/warm-up and shutdown.
Only the worker creates a RAPS engine or FMU. Run with no other simulations.
"""

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter


def guard_result(total_s: float, warmup_instantiation_s: float) -> dict:
    return {
        "switch_required": total_s > 2700.0,
        "guard": "D2: isolated end-to-end total_s > 2700",
        "twice_total_s_information_only": 2 * total_s,
        "twice_after_warmup_instantiation_s_information_only": 2 * (total_s - warmup_instantiation_s),
        "horizon_h": 12 if total_s * 2 * 2 <= 300 else 6,
    }


def _worker(system: str, hours: int) -> dict:
    import numpy as np
    from thermorl2.core.state import Ambient
    from thermorl2.experiments.provenance import environment, git_state, sha256_file
    from thermorl2.raps_adapter.coupling import CouplingParams
    from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine, is_power_tick, rack_kw_from_power_df
    from thermorl2.raps_adapter.power_model import legacy_config, rack_power_bounds, raps_rack_kw
    from thermorl2.raps_adapter.systems import get_system, repo_root
    from thermorl2.thermal.fmu_backend import FmuBackend

    git = git_state()
    porcelain = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root(), text=True)
    cfg = legacy_config(system)
    spec = get_system(system)
    fmu_path = repo_root() / spec.fmu_path
    fmu_sha = sha256_file(fmu_path)
    if fmu_sha != spec.fmu_sha256:
        raise ValueError("FMU SHA mismatch")
    source_hashes = {str(path.relative_to(repo_root())): sha256_file(path)
                     for path in (repo_root() / "thermoRL/thermorl-v2/thermorl2").rglob("*.py")}
    idle = raps_rack_kw(cfg, 0, 0)
    peak = raps_rack_kw(cfg, cfg["CPUS_PER_NODE"], cfg["GPUS_PER_NODE"])
    probe_idle, probe_peak = rack_power_bounds(cfg)
    n = cfg["NUM_CDUS"] * cfg["RACKS_PER_CDU"]
    delta = cfg["POWER_UPDATE_FREQ"]
    start = perf_counter()
    engine = build_engine(EngineSpec(system, f"{hours}h", seed=1), jobs=[])
    raps_s = perf_counter() - start
    start = perf_counter()
    backend = FmuBackend(fmu_path, CouplingParams.from_legacy_config(cfg))
    instantiation_s = perf_counter() - start
    power_ticks = 0
    finite = True
    max_c = -float("inf")
    try:
        start = perf_counter()
        used = backend.warm_up(np.full(n, idle), Ambient(), dt_s=delta, max_s=7200, settle_k_per_min=-1.0)
        assert used == 7200.0
        warmup_wall_s = perf_counter() - start
        initial_c = backend.observe().t_c.tolist()
        print(f"BENCH {system}: 7200 s capped warm-up complete; isolated {hours} h idle episode starting", flush=True)
        episode_start = perf_counter()
        before_fmu_s = backend.runtime_s()
        generator = engine.run_simulation()
        while True:
            start = perf_counter()
            try:
                tick = next(generator)
            except StopIteration:
                raps_s += perf_counter() - start
                break
            raps_s += perf_counter() - start
            if not is_power_tick(tick, delta):
                continue
            rack_kw = rack_kw_from_power_df(tick.power_df, cfg["RACKS_PER_CDU"])
            assert abs(float(rack_kw.sum()) - float(tick.power_df["Sum"].sum())) < 1e-6
            assert abs(float(rack_kw.mean()) - idle) < 0.05
            backend.step(rack_kw, delta, Ambient())
            thermal = backend.observe()
            if not np.isfinite(thermal.t_c).all():
                raise ValueError("non-finite coolant in isolated bench")
            finite &= bool(np.isfinite(thermal.extras["W_flow_CDUP_kW"]).all())
            max_c = max(max_c, float(thermal.t_c.max()))
            power_ticks += 1
            if power_ticks % (1800 // delta) == 0:
                print(f"BENCH {system}: {power_ticks * delta}/{hours * 3600} s; {power_ticks} FMU steps", flush=True)
        assert power_ticks == hours * 3600 // delta
        episode_wall_s = perf_counter() - episode_start
        episode_fmu_s = backend.runtime_s() - before_fmu_s
    finally:
        backend.close()
    return {
        "system": system, "backend": "fmu", "git": git, "git_status_porcelain": porcelain,
        "environment": environment(), "fmu_sha256": fmu_sha,
        "source_sha256": source_hashes,
        "workload_sha256": hashlib.sha256(json.dumps({"kind": "idle", "rack_kw": [idle] * n, "hours": hours}, sort_keys=True).encode()).hexdigest(),
        "config": {"system": system, "hours": hours, "seed": 1, "power_tick_s": delta, "warmup_s": 7200, "cooling": False, "output": "none", "noui": True},
        "policy": "idle", "seed": 1, "power_tick_s": delta, "power_ticks": power_ticks,
        "fmu_steps": power_ticks, "warmup_used_s": used, "warmup_status": "capped_preconditioned_not_settled",
        "t_idle_c": initial_c, "instantiation_s": instantiation_s, "warmup_wall_s": warmup_wall_s,
        "warmup_instantiation_s": instantiation_s + warmup_wall_s,
        "raps_s": raps_s, "fmu_s": backend.runtime_s(), "episode_fmu_s": episode_fmu_s, "episode_wall_s": episode_wall_s,
        "finite": finite, "raw_max_c": max_c,
        "rack_kw_reference": {"raps_idle_kw": idle, "raps_peak_kw": peak, "probe_idle_kw": probe_idle, "probe_peak_kw": probe_peak},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True)
    parser.add_argument("--hours", type=int, default=6)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.hours != 6:
        parser.error("Task 5 D2 requires the fixed 6 h benchmark")
    if args.worker:
        print("BENCH_RESULT " + json.dumps(_worker(args.system, args.hours), sort_keys=True, allow_nan=False), flush=True)
        return
    started = datetime.now(UTC)
    start = perf_counter()
    child = subprocess.Popen([sys.executable, "-m", "thermorl2.experiments.bench", "--system", args.system, "--hours", str(args.hours), "--worker"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result = None
    for line in child.stdout:
        if line.startswith("BENCH_RESULT "):
            result = json.loads(line[len("BENCH_RESULT "):])
        else:
            print(line, end="", flush=True)
    code = child.wait()
    total_s = perf_counter() - start
    if code or result is None:
        raise RuntimeError(f"isolated benchmark worker failed (exit {code})")
    result.update(total_s=total_s, started_utc=started.isoformat(), finished_utc=datetime.now(UTC).isoformat(), simulation_pid=child.pid,
                  **guard_result(total_s, result["warmup_instantiation_s"]))
    result["config_sha256"] = hashlib.sha256(json.dumps(result["config"], sort_keys=True).encode()).hexdigest()
    out = Path("experiments") / args.system / "_bench"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"task5_bench_{started.strftime('%Y%m%dT%H%M%S_%fZ')}.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    env_path = out / "environment.txt"
    if not env_path.exists():
        env_path.write_text(json.dumps(result["environment"], indent=2, sort_keys=True) + "\n")
    print(json.dumps({"artifact": str(path), **result}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
