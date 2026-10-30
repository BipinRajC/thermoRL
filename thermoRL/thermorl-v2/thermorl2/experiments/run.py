"""Episode CLI and bounded E10 mechanics report (not a policy matrix)."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from thermorl2.experiments.provenance import environment, sha256_file, write_manifest, require_assertions
from thermorl2.raps_adapter.power_model import legacy_config
from thermorl2.raps_adapter.runner import DECISION_KEYS, EpisodeRunner, read_jsonl
from thermorl2.raps_adapter.systems import get_system
from thermorl2.raps_adapter.workload.synthetic import SyntheticSpec, generate, write_workload

PROJECT = Path(__file__).resolve().parents[2]
CONFIGS = Path(__file__).with_name("configs")


def load_config(path):
    path = Path(path)
    cfg = yaml.safe_load(path.read_text())
    include = path.parent / cfg["include"]
    if not include.is_file():
        include = CONFIGS / cfg["include"]
    primary = yaml.safe_load(include.read_text())
    if "system" in cfg and cfg["system"] != primary["system"]:
        raise ValueError("config system contradicts frozen primary")
    cfg = {**primary, **cfg}
    source = Path(primary["thermal_predictive"]["from"])
    if not source.is_absolute():
        source = PROJECT / source
    g1 = json.loads(source.read_text())
    cfg["thermal_predictive_params"] = {
        "a_c": g1["fit"]["a_c"], "b_c_per_kw": g1["fit"]["b_c_per_kw"],
        "tau_s": g1["tau_s"], "horizon_s": primary["thermal_predictive"]["horizon_s"],
    }
    cfg["g1_sha256"] = sha256_file(source)
    cfg["primary_yaml_sha256"] = sha256_file(include)
    return cfg


def prepare_workload(cfg, seed):
    legacy = legacy_config(cfg["system"])
    spec = SyntheticSpec.from_dict({"rho": cfg["workload"]["rho"]})
    frame = generate(spec, seed, int(cfg["horizon_h"] * 3600), legacy["TOTAL_NODES"], legacy["GPUS_PER_NODE"])
    digest = hashlib.sha256(frame.to_parquet(index=False)).hexdigest()
    path = Path("experiments") / cfg["system"] / "_workloads" / f"{digest}.parquet"
    actual = write_workload(frame, path, {"system": cfg["system"], "seed": seed, "horizon_s": int(cfg["horizon_h"] * 3600),
                                        "n_nodes": legacy["TOTAL_NODES"], "gpus_per_node": legacy["GPUS_PER_NODE"]})
    assert digest == actual
    return {"path": str(path), "sha256": actual, "jobs_offered": len(frame), "meta_path": str(path) + ".meta.json"}


def e10_metrics(frame, manifest, decisions):
    tail = frame[(frame.t_s > 3600) & (frame.t_s <= 7200)]
    maxima = tail.groupby("t_s").t_c.max()
    free = tail.groupby("t_s").free.sum()
    idle = np.asarray(manifest["t_idle_c"])[tail.rack.to_numpy(dtype=int)]
    thi = 1 - (tail.t_c.to_numpy() - idle) / (45.0 - idle)
    return {"maxrack_mean_c": float(maxima.mean()), "maxrack_p99_c": float(np.percentile(maxima, 99)),
            "mean_rack_c": float(tail.t_c.mean()), "raw_max_c": float(frame.t_c.max()),
            "realised_node_utilisation_mean": float((1 - free / manifest["total_nodes"]).mean()),
            "jobs_started": len(decisions), "raps_s": manifest["raps_s"], "fmu_s": manifest["fmu_s"], "total_s": manifest["total_s"],
            "temperature_only_thi_below_0p1_fraction": float(np.mean(thi < 0.10)),
            "episode_pump_min_kw": float(frame.pump_kw.min()) if "pump_kw" in frame else None}


def _allocation_ok(path, decisions, manifest):
    assert len({row["job_id"] for row in decisions}) == len(decisions)
    requests = pd.read_parquet(Path(manifest["workload_path"])).set_index("id")
    free = set(range(manifest["total_nodes"]))
    active = {}
    starts = 0
    for event in read_jsonl(path / "provenance/job_events.jsonl"):
        nodes = set(event["nodes"])
        if event["event"] == "complete":
            assert active.pop(event["job_id"]) == nodes
            assert free.isdisjoint(nodes)
            free.update(nodes)
        else:
            index = event["decision_index"]
            assert index == starts
            row = decisions[index]
            assert row["job_id"] == event["job_id"] and row["t_s"] == event["t_s"]
            assert row["nodes_required"] == int(requests.loc[row["job_id"], "nodes_required"])
            assert row["t_s"] >= np.ceil(requests.loc[row["job_id"], "submit_time"])
            assert len(nodes) == len(event["nodes"]) == row["nodes_required"]
            assert event["nodes"] == row["nodes"] and nodes <= free
            counts = np.bincount(np.asarray(sorted(free)) // manifest["nodes_per_rack"], minlength=manifest["n_racks"])
            assert counts.tolist() == row["free"]
            free.difference_update(nodes)
            assert event["job_id"] not in active
            active[event["job_id"]] = nodes
            starts += 1
    assert starts == len(decisions)
    return True


def _manifest_ok(path, manifest, cfg, decisions):
    required = {"git", "git_status_porcelain", "system", "fmu_sha256", "workload_path", "workload_sha256", "config", "config_sha256", "policy", "seed", "backend", "thermal_predictive_params", "rack_kw_reference", "power_tick_s", "fmu_steps", "warmup_used_s", "t_idle_c", "raps_s", "fmu_s", "total_s", "environment", "decision_latency_span", "decisions_sha256", "decision_rows", "decision_latency_sha256", "decision_latency_rows"}
    assert required <= manifest.keys()
    assert manifest["backend"] == "fmu" and manifest["system"] == "summit" and manifest["seed"] == 1
    assert manifest["fmu_sha256"] == get_system(cfg["system"]).fmu_sha256
    assert manifest["workload_sha256"] == cfg["workload"]["sha256"] == sha256_file(Path(manifest["workload_path"]))
    assert manifest["thermal_predictive_params"] == cfg["thermal_predictive_params"]
    assert manifest["warmup_used_s"] == 7200.0
    assert hashlib.sha256(json.dumps(manifest["config"], sort_keys=True).encode()).hexdigest() == manifest["config_sha256"]
    assert sha256_file(path / "decisions.jsonl") == manifest["decisions_sha256"]
    assert sha256_file(path / "intervals.parquet") == manifest["intervals_sha256"]
    timing_path = path / "provenance/decision_latency.jsonl"
    assert sha256_file(timing_path) == manifest["decision_latency_sha256"]
    times = read_jsonl(timing_path)
    assert len(times) == len(decisions) == manifest["decision_rows"] == manifest["decision_latency_rows"]
    for index, (row, timing) in enumerate(zip(decisions, times)):
        assert set(row) == DECISION_KEYS and row["latency_us"] is None and type(row["t_obs_s"]) is float
        assert set(timing) == {"decision_index", "job_id", "t_s", "latency_ns"}
        assert (index, row["job_id"], row["t_s"]) == (timing["decision_index"], timing["job_id"], timing["t_s"])
        assert type(timing["latency_ns"]) is int and timing["latency_ns"] >= 0
    return True


def complete_e10(out, cfg, paths):
    out = Path(out)
    if (out / "results/summary.json").exists():
        raise FileExistsError("E10 summary already exists; never overwrite results")
    runs = {label: {"path": Path(path), "manifest": json.loads((Path(path) / "manifest.json").read_text()),
                    "frame": pd.read_parquet(Path(path) / "intervals.parquet"), "decisions": read_jsonl(Path(path) / "decisions.jsonl")}
            for label, path in paths.items()}
    packing, balance, rerun = (runs[key] for key in ("packing", "power_balance", "packing_rerun"))
    totals = [run["frame"].groupby("t_s").it_kw_total.first() for run in (packing, balance)]
    same_grid = totals[0].index.equals(totals[1].index)
    it_error = float(np.max(np.abs(totals[0].to_numpy() - totals[1].to_numpy()))) if same_grid else None
    starts = [{row["job_id"]: row["t_s"] for row in run["decisions"]} for run in (packing, balance)]
    bytes_equal = (packing["path"] / "decisions.jsonl").read_bytes() == (rerun["path"] / "decisions.jsonl").read_bytes()
    try:
        pd.testing.assert_frame_equal(packing["frame"], rerun["frame"], check_exact=True)
        intervals_equal = True
    except AssertionError:
        intervals_equal = False
    allocation_ok = True
    manifest_ok = True
    step_ok = True
    power_ok = True
    details = {}
    for label, run in runs.items():
        path, frame, manifest, decisions = (run[key] for key in ("path", "frame", "manifest", "decisions"))
        try:
            _allocation_ok(path, decisions, manifest)
        except (AssertionError, KeyError, IndexError) as error:
            allocation_ok = False
            details[f"{label}_allocation_error"] = str(error)
        try:
            _manifest_ok(path, manifest, cfg, decisions)
        except (AssertionError, KeyError, IndexError) as error:
            manifest_ok = False
            details[f"{label}_manifest_error"] = str(error)
        times = np.asarray(sorted(frame.t_s.unique()))
        step_ok &= manifest["fmu_steps"] == manifest["power_ticks"] == 720 and manifest["backend_elapsed_s"] == 7200.0
        step_ok &= bool(np.array_equal(times, np.arange(10, 7201, 10)))
        step_ok &= bool((frame.groupby("t_s").size() == manifest["n_racks"]).all())
        grouped = frame.groupby("t_s")
        error = float(np.max(np.abs(grouped.kw.sum().to_numpy() - grouped.it_kw_total.first().to_numpy())))
        power_ok &= error <= 1e-6 and manifest["power_reconciliation_max_abs_kw"] <= 1e-6
        details[f"{label}_power_sum_max_abs_error_kw"] = error
        if not np.isfinite(frame.t_c).all():
            raise ValueError("non-finite serialized closed-loop coolant")
    invariants = {"1_it_kw_and_start_times_identical": bool(same_grid and it_error <= 1e-6 and starts[0] == starts[1]),
                  "2_exact_distinct_free_nodes": bool(allocation_ok), "3_decisions_byte_identical_and_interval_values_identical": bool(bytes_equal and intervals_equal),
                  "4_rack_power_sums_reconcile": bool(power_ok), "5_independent_step_count_and_clock": bool(step_ok),
                  "6_manifests_and_joinable_ledgers_complete": bool(manifest_ok)}
    result = {"experiment": "E10", "system": "summit", "scope": "closed-loop mechanics; no G4 policy-comparison conclusion",
              "decision": "PASS" if all(invariants.values()) else "FAIL", "invariants": invariants, "invariant_detail": details,
              "max_abs_it_kw_difference": it_error, "job_start_times_identical": starts[0] == starts[1],
              "workload_sha256": cfg["workload"]["sha256"], "evaluation_window": "3600 < t_s <= 7200; right endpoints; p99 uses linear percentile",
              "runs": {label: e10_metrics(run["frame"], run["manifest"], run["decisions"]) for label, run in runs.items()},
              "coolant_over_70": {label: {"samples": run["manifest"]["coolant_over_70_samples"], "racks": run["manifest"]["coolant_over_70_racks"], "raw_max_c": run["manifest"]["raw_max_c"]} for label, run in runs.items()}}
    for sub in ("results", "plots", "provenance"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    (out / "results/invariants.json").write_text(json.dumps({"invariants": invariants, "details": details}, indent=2, sort_keys=True) + "\n")
    (out / "results/summary.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (out / "provenance/rerun_1.json").write_text(json.dumps({"decisions_byte_identical": bytes_equal, "interval_values_identical": intervals_equal,
        "interval_file_bytes_identical": (packing["path"] / "intervals.parquet").read_bytes() == (rerun["path"] / "intervals.parquet").read_bytes(),
        "original_decisions_sha256": sha256_file(packing["path"] / "decisions.jsonl"), "rerun_decisions_sha256": sha256_file(rerun["path"] / "decisions.jsonl"),
        "timing_ledger_excluded_from_byte_comparison": True, "rerun_path": str(rerun["path"])}, indent=2, sort_keys=True) + "\n")
    if not all(invariants.values()):
        raise AssertionError(f"E10 invariant failure: {invariants}")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(13, 6), sharex=True, sharey=True, layout="constrained")
    vmin = min(run["frame"].t_c.min() for run in (packing, balance))
    vmax = max(run["frame"].t_c.max() for run in (packing, balance))
    for axis, (name, run) in zip(axes, (("packing", packing), ("power_balance", balance))):
        matrix = run["frame"].pivot(index="rack", columns="t_s", values="t_c").sort_index()
        panel = axis.imshow(matrix.to_numpy(), origin="lower", aspect="auto", extent=(0, 2, 0, len(matrix)), vmin=vmin, vmax=vmax, cmap="inferno")
        axis.set(title=name, xlabel="Episode time (h), warm-up excluded")
    axes[0].set_ylabel("Rack index")
    figure.colorbar(panel, ax=axes, label="Coolant temperature (°C)")
    figure.suptitle("E10 closed-loop mechanics — Summit, seed 1, shared scale")
    figure.savefig(out / "plots/heatmaps.png", dpi=160)
    plt.close(figure)
    (out / "provenance/environment.txt").write_text(json.dumps(environment(), indent=2, sort_keys=True) + "\n")
    write_manifest(out / "provenance", system="summit", fmu_sha256=packing["manifest"]["fmu_sha256"], workload_sha256=cfg["workload"]["sha256"],
                   config=cfg, policy=["packing", "power_balance"], seed=1,
                   run_manifest_sha256={label: sha256_file(run["path"] / "manifest.json") for label, run in runs.items()},
                   timings={label: run["manifest"]["total_s"] for label, run in runs.items()})
    return result


def main():
    require_assertions()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--policy")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--horizon-h", type=float)
    parser.add_argument("--experiment-dir", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--prepare-workload", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.horizon_h is not None:
        cfg["horizon_h"] = args.horizon_h
    if args.prepare_workload:
        print(json.dumps(prepare_workload(cfg, args.seed), sort_keys=True))
        return
    if args.policy is None:
        parser.error("--policy is required for an episode")
    out = args.experiment_dir or Path(cfg["experiment_dir"].format(system=cfg["system"]))
    run_dir = args.run_dir or out / "runs" / f"{args.policy}_seed{args.seed}"
    EpisodeRunner(cfg, args.policy, args.seed, run_dir).run()


if __name__ == "__main__":
    main()
