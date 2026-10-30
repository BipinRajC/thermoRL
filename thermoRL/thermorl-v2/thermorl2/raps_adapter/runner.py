"""One-process RAPS/FMU episode with separate deterministic and timing ledgers."""

from itertools import zip_longest
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np
import pandas as pd

from thermorl2.core.scorers import make_scorer
from thermorl2.core.state import Ambient
from thermorl2.experiments.provenance import git_state, sha256_file, write_manifest
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine, is_power_tick, rack_kw_from_power_df
from thermorl2.raps_adapter.jobs import jobs_from_frame
from thermorl2.raps_adapter.power_model import legacy_config, rack_power_bounds, raps_rack_kw
from thermorl2.raps_adapter.rack_geometry import RackGeometry
from thermorl2.raps_adapter.scheduler import LATENCY_SPAN, PlacementScheduler, ThermalView
from thermorl2.raps_adapter.systems import get_system, repo_root
from thermorl2.thermal.fmu_backend import FmuBackend


DECISION_KEYS = {"t_s", "job_id", "nodes_required", "policy", "rule", "racks", "nodes", "job_kw", "scores", "t_c", "committed_kw", "free", "t_obs_s", "latency_us"}


def config_for_seed(cfg, seed):
    """Resolve an immutable per-seed workload without mutating shared config."""
    selected = deepcopy(cfg)
    workload = selected['workload']
    if 'by_seed' in workload:
        entry = workload['by_seed'].get(seed, workload['by_seed'].get(str(seed)))
        if entry is None:
            raise KeyError(f'no workload registered for seed {seed}')
        workload.update(entry)
    return selected


def read_jsonl(path):
    with Path(path).open() as source:
        return [json.loads(line) for line in source if line.strip()]


class DecisionLedgers:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        (self.run_dir / "provenance").mkdir(parents=True, exist_ok=True)
        self.decision_path = self.run_dir / "decisions.jsonl"
        self.timing_path = self.run_dir / "provenance/decision_latency.jsonl"
        self._decisions = self.decision_path.open("x")
        self._timings = self.timing_path.open("x")

    def write_decision(self, row):
        assert set(row) == DECISION_KEYS and row["latency_us"] is None
        self._decisions.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")

    def write_timing(self, row):
        assert set(row) == {"decision_index", "job_id", "t_s", "latency_ns"}
        assert type(row["latency_ns"]) is int and row["latency_ns"] >= 0
        self._timings.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")

    def close(self):
        self._decisions.close()
        self._timings.close()

    def finalize(self):
        self.close()
        decisions, times = read_jsonl(self.decision_path), read_jsonl(self.timing_path)
        assert len(decisions) == len(times), "decision/timing row count mismatch"
        for index, pair in enumerate(zip_longest(decisions, times)):
            decision, timing = pair
            assert (index, decision["job_id"], decision["t_s"]) == (timing["decision_index"], timing["job_id"], timing["t_s"]), "decision/timing join mismatch"
        return {"decisions_sha256": sha256_file(self.decision_path), "decision_rows": len(decisions),
                "decision_latency_sha256": sha256_file(self.timing_path), "decision_latency_rows": len(times),
                "decision_latency_span": LATENCY_SPAN, "decision_latency_join_verified": True,
                "decision_latency_ns_sum": sum(row["latency_ns"] for row in times)}


class EpisodeRunner:
    def __init__(self, cfg, policy, seed, run_dir):
        self.cfg, self.policy, self.seed, self.run_dir = config_for_seed(cfg,seed), policy, seed, Path(run_dir)

    def run(self):
        total_start = perf_counter()
        cfg, system = self.cfg, self.cfg["system"]
        assert self.policy in cfg["policies"] and self.seed in cfg["seeds"] and self.seed >= 1
        assert cfg["scenario"]["name"] == "nominal", "only nominal episodes are authorized"
        horizon_s = int(cfg["horizon_h"] * 3600)
        legacy = legacy_config(system)
        geometry = RackGeometry.from_legacy_config(legacy)
        delta = legacy["POWER_UPDATE_FREQ"]
        assert horizon_s % delta == 0 and cfg["warmup_s"] == 7200
        spec = get_system(system)
        fmu_path = repo_root() / spec.fmu_path
        assert sha256_file(fmu_path) == spec.fmu_sha256, "FMU SHA mismatch"
        workload_path = Path(cfg["workload"]["path"])
        if not workload_path.is_absolute():
            workload_path = repo_root() / 'thermoRL/thermorl-v2' / workload_path
        assert sha256_file(workload_path) == cfg["workload"]["sha256"], "workload SHA mismatch"
        sidecar = json.loads(Path(str(workload_path)+'.meta.json').read_text())
        assert sidecar['horizon_s'] == horizon_s, 'workload horizon does not match episode horizon'
        frame = pd.read_parquet(workload_path)
        assert frame.attrs["seed"] == self.seed
        git = git_state()
        porcelain = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root(), text=True)
        source_hashes = {str(path.relative_to(repo_root())): sha256_file(path)
                         for path in (repo_root() / "thermoRL/thermorl-v2/thermorl2").rglob("*.py")}
        for path in (repo_root() / "sim-raps/raps/engine.py", repo_root() / "sim-raps/raps/power.py", repo_root() / "sim-raps/config" / f"{system}.yaml"):
            source_hashes[str(path.relative_to(repo_root()))] = sha256_file(path)
        self.run_dir.mkdir(parents=True, exist_ok=False)
        ledgers = DecisionLedgers(self.run_dir)
        jobs = jobs_from_frame(frame)
        start = perf_counter()
        engine = build_engine(EngineSpec(system, f"{horizon_s}s", self.seed), jobs=jobs)
        raps_s = perf_counter() - start
        events = []
        decision_index = 0

        def decision_sink(row):
            nonlocal decision_index
            ledgers.write_decision(row)
            events.append({"event": "start", "t_s": row["t_s"], "job_id": row["job_id"], "nodes": row["nodes"], "decision_index": decision_index})
            decision_index += 1

        scorer = make_scorer(self.policy, cfg["thermal_predictive_params"] if self.policy == "thermal_predictive" else {})
        scheduler = PlacementScheduler(engine.resource_manager, geometry, scorer, legacy, decision_sink, timing_sink=ledgers.write_timing)
        engine.scheduler = scheduler
        scheduler_wall_s = 0.0
        original_schedule = scheduler.schedule

        def timed_schedule(*args, **kwargs):
            nonlocal scheduler_wall_s
            start = perf_counter()
            try:
                return original_schedule(*args, **kwargs)
            finally:
                scheduler_wall_s += perf_counter() - start

        scheduler.schedule = timed_schedule
        idle = raps_rack_kw(legacy, 0, 0)
        peak = raps_rack_kw(legacy, legacy["CPUS_PER_NODE"], legacy["GPUS_PER_NODE"])
        probe_idle, probe_peak = rack_power_bounds(legacy)
        backend = None
        rows = []
        publications = []
        step_calls = 0
        power_ticks = 0
        max_reconciliation = 0.0
        over_70_samples = 0
        over_70_racks = set()
        raw_max = -float("inf")
        try:
            start = perf_counter()
            backend = FmuBackend(fmu_path, CouplingParams.from_legacy_config(legacy))
            instantiation_s = perf_counter() - start
            start = perf_counter()
            warmup_used = backend.warm_up(np.full(geometry.n_racks, idle), Ambient(), dt_s=delta, max_s=7200, settle_k_per_min=-1.0)
            assert warmup_used == 7200.0
            warmup_wall_s = perf_counter() - start
            initial = backend.observe()
            if not np.isfinite(initial.t_c).all():
                raise ValueError("non-finite initial coolant")
            t_idle = initial.t_c.tolist()
            scheduler.on_thermal(ThermalView(0.0, initial.t_c, initial.extras["W_flow_CDUP_kW"]))
            initial_globals = backend.global_observe()
            real_step = backend.step

            def counted_step(*args, **kwargs):
                nonlocal step_calls
                step_calls += 1
                return real_step(*args, **kwargs)

            backend.step = counted_step
            episode_start = perf_counter()
            episode_fmu_before = backend.runtime_s()
            print(f"RUN {self.policy}: fixed warm-up complete; {horizon_s}s episode starting", flush=True)
            generator = engine.run_simulation()
            while True:
                start = perf_counter()
                scheduler_before = scheduler_wall_s
                try:
                    tick = next(generator)
                except StopIteration:
                    raps_s += perf_counter() - start - (scheduler_wall_s - scheduler_before)
                    break
                raps_s += perf_counter() - start - (scheduler_wall_s - scheduler_before)
                for job in tick.completed:
                    events.append({"event": "complete", "t_s": int(tick.current_timestep), "job_id": int(job.id), "nodes": list(map(int, job.scheduled_nodes))})
                if not is_power_tick(tick, delta):
                    continue
                rack_kw = rack_kw_from_power_df(tick.power_df, legacy["RACKS_PER_CDU"])
                assert rack_kw.shape == (geometry.n_racks,) and np.isfinite(rack_kw).all()
                total_it = float(tick.power_df["Sum"].sum())
                error = abs(float(rack_kw.sum()) - total_it)
                assert error <= 1e-6, "rack power sum mismatch"
                max_reconciliation = max(max_reconciliation, error)
                assert backend.time_s == float(tick.current_timestep)
                scheduler.on_power_tick(rack_kw)
                backend.step(rack_kw, delta, Ambient())
                thermal = backend.observe()
                if not np.isfinite(thermal.t_c).all():
                    raise ValueError("non-finite closed-loop coolant")
                pump = thermal.extras["W_flow_CDUP_kW"]
                scheduler.on_thermal(ThermalView(float(backend.time_s), thermal.t_c, pump))
                publications.append({"raps_power_tick_s": float(tick.current_timestep), "fmu_episode_endpoint_s": float(backend.time_s), "t_obs_s": float(backend.time_s)})
                free = geometry.free_per_rack(engine.resource_manager.available_nodes)
                rows.append(pd.DataFrame({"t_s": float(backend.time_s), "rack": np.arange(geometry.n_racks),
                                          "kw": rack_kw, "t_c": thermal.t_c, "pump_kw": pump, "free": free,
                                          "it_kw_total": total_it, "n_running": len(tick.running), "n_queued": len(tick.queue), "scenario_active": False}))
                over = np.flatnonzero(thermal.t_c > 70)
                over_70_samples += len(over)
                over_70_racks.update(map(int, over))
                raw_max = max(raw_max, float(thermal.t_c.max()))
                power_ticks += 1
                if power_ticks % (1800 // delta) == 0:
                    print(f"RUN {self.policy}: {backend.time_s:.0f}/{horizon_s}s; step calls={step_calls}; jobs started={decision_index}", flush=True)
            assert power_ticks == horizon_s // delta
            assert step_calls == horizon_s // delta
            assert backend.time_s == float(horizon_s)
            episode_wall_s = perf_counter() - episode_start
            episode_fmu_s = backend.runtime_s() - episode_fmu_before
            final_elapsed = backend.time_s
        except Exception as error:
            (self.run_dir / "provenance/failure.json").write_text(json.dumps({"type": type(error).__name__, "error": str(error), "policy": self.policy, "power_ticks": power_ticks, "step_calls": step_calls}, sort_keys=True) + "\n")
            raise
        finally:
            if backend is not None:
                backend.close()
            ledgers.close()
        ledger_metadata = ledgers.finalize()
        intervals = pd.concat(rows, ignore_index=True)
        assert len(intervals) == (horizon_s // delta) * geometry.n_racks
        intervals_path = self.run_dir / "intervals.parquet"
        intervals.to_parquet(intervals_path, index=False)
        events.sort(key=lambda event: (event["t_s"], 0 if event["event"] == "complete" else 1, event.get("decision_index", event["job_id"])))
        with (self.run_dir / "provenance/job_events.jsonl").open("x") as output:
            for event in events:
                output.write(json.dumps(event, sort_keys=True) + "\n")
        with (self.run_dir / "provenance/thermal_publications.jsonl").open("x") as output:
            for publication in publications:
                output.write(json.dumps(publication, sort_keys=True) + "\n")
        config_sha = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
        manifest = {
            "git": git, "git_status_porcelain": porcelain, "system": system, "fmu_sha256": spec.fmu_sha256,
            "workload_path": cfg['workload']['path'], "workload_sha256": cfg["workload"]["sha256"],
            "workload_meta_sha256": sha256_file(Path(str(workload_path) + ".meta.json")),
            "config": cfg, "config_sha256": config_sha, "policy": self.policy, "seed": self.seed,
            "thermal_predictive_params": cfg["thermal_predictive_params"], "g1_sha256": cfg["g1_sha256"],
            "rack_kw_reference": {"raps_idle_kw": idle, "raps_peak_kw": peak, "probe_idle_kw": probe_idle, "probe_peak_kw": probe_peak},
            "power_tick_s": delta, "power_ticks": power_ticks, "fmu_steps": step_calls, "backend_elapsed_s": final_elapsed,
            "warmup_used_s": warmup_used, "warmup_status": "capped_preconditioned_not_settled", "t_idle_c": t_idle,
            "initial_globals": initial_globals, "idle_kw": idle, "peak_kw": peak,
            "total_nodes": geometry.total_nodes, "n_racks": geometry.n_racks, "nodes_per_rack": geometry.nodes_per_rack,
            "raps_s": raps_s, "fmu_s": backend.runtime_s(), "total_s": perf_counter() - total_start,
            "scheduler_wall_s": scheduler_wall_s, "instantiation_s": instantiation_s, "warmup_wall_s": warmup_wall_s,
            "episode_wall_s": episode_wall_s, "episode_fmu_s": episode_fmu_s,
            "raps_s_scope": "engine construction and generator execution excluding scheduler callbacks",
            "fmu_s_scope": "FmuBackend runtime_s: timed archive extraction/model-description reading, instantiation, warm-up, episode FMU API operations including observe/state management, and teardown; excludes RAPS and ledger serialization",
            "total_s_scope": "EpisodeRunner.run including setup, warm-up, episode and ledger serialization; interpreter imports excluded",
            "interval_time_axis": "t_s is FMU episode interval endpoint: Delta..horizon_s; kw/free/n_running/n_queued/it_kw_total are RAPS-t inputs, t_c/pump_kw are t+Delta endpoints; power tick t applies (t,t+Delta], publishes post-step view before resuming generator; see thermal_publications.jsonl",
            "power_reconciliation_max_abs_kw": max_reconciliation, "source_sha256": source_hashes,
            "intervals_sha256": sha256_file(intervals_path), "raw_max_c": raw_max,
            "coolant_over_70_samples": over_70_samples, "coolant_over_70_racks": sorted(over_70_racks),
            "negative_episode_pump_samples": int((intervals.pump_kw < 0).sum()), **ledger_metadata,
        }
        # Per-run manifest is at the exact plan path; write_manifest also adds
        # backend and package/platform environment without importing FMPy here.
        write_manifest(self.run_dir, **manifest)
        print(json.dumps({"run_dir": str(self.run_dir), "policy": self.policy, "fmu_steps": step_calls, "jobs_started": decision_index, "total_s": manifest["total_s"]}, sort_keys=True), flush=True)
        return self.run_dir
