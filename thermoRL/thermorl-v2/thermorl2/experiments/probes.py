"""Frozen FMU-only G1/G2/G3 protocols; one FMU per invocation/process."""

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from thermorl2.core.state import Ambient
from thermorl2.experiments.provenance import environment, git_state, sha256_file, write_manifest
from thermorl2.experiments.select_fmu import classify_delta
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.raps_adapter.power_model import legacy_config, rack_power_bounds
from thermorl2.raps_adapter.systems import SYSTEMS, get_system, repo_root
from thermorl2.thermal.fmu_backend import FmuBackend


TIMING_KEYS = ("fmu_s_per_sim_h", "projected_closed_loop_min_6h")


def uniform_vector(n, idle_kw, peak_kw, f) -> np.ndarray:
    if n < 1 or not 0 <= f <= 1 or peak_kw <= idle_kw:
        raise ValueError("invalid uniform load")
    return np.full(n, idle_kw + f * (peak_kw - idle_kw), dtype=np.float64)


def packed_vector(n, idle_kw, peak_kw, total_kw) -> np.ndarray:
    if n < 1 or peak_kw <= idle_kw or not n * idle_kw - 1e-9 <= total_kw <= n * peak_kw + 1e-9:
        raise ValueError("total power cannot be represented within rack bounds")
    result = np.full(n, idle_kw, dtype=np.float64)
    remaining = max(0.0, total_kw - n * idle_kw)
    for i in range(n):
        increment = min(peak_kw - idle_kw, remaining)
        result[i] = peak_kw if increment == peak_kw - idle_kw else idle_kw + increment
        remaining = max(0.0, remaining - increment)
    if abs(float(result.sum()) - total_kw) > 1e-9:
        raise ValueError("packed total does not reconcile")
    return result


def scientific_summary(summary: dict) -> dict:
    return {key: value for key, value in summary.items() if key not in TIMING_KEYS}


def branch_statistics(times, temperatures, horizon_s=10800, tail_s=1800) -> dict:
    mask = (times > horizon_s - tail_s) & (times <= horizon_s)
    tail = temperatures[mask]
    if not len(tail):
        raise ValueError("empty evaluation window")
    return {"max_c": float(tail.max(axis=1).mean()), "mean_c": float(tail.mean()),
            "spread_c": float(np.ptp(tail, axis=1).mean())}


def g1_metrics(branches: dict, idle_kw, peak_kw, horizon_s=10800, tail_s=900) -> dict:
    levels = []
    for f in (0, 0.25, 0.5, 0.75, 1):
        times, temperatures = branches[f"f{f:g}"]
        mask = (times > horizon_s - tail_s) & (times <= horizon_s)
        rack_means = temperatures[mask].mean(axis=0)
        mean_trace = temperatures.mean(axis=1)
        final_mean = float(rack_means.mean())
        rise = final_mean - mean_trace[0]
        fractions = (mean_trace - mean_trace[0]) / rise if rise != 0 else np.full(len(times), np.nan)
        crossing = np.flatnonzero(fractions >= 0.632)
        levels.append({"f": f, "rack_kw": idle_kw + f * (peak_kw - idle_kw), "mean_c": final_mean,
                       "min_c": float(rack_means.min()), "max_c": float(rack_means.max()),
                       "initial_mean_c": float(mean_trace[0]), "signed_final_rise_c": float(rise),
                       "t63_s": float(times[crossing[0]]) if len(crossing) else None,
                       "trajectory_peak_c": float(temperatures.max())})
    x = np.array([level["rack_kw"] for level in levels])
    y = np.array([level["mean_c"] for level in levels])
    b, a = np.polyfit(x, y, 1)
    fitted = a + b * x
    denom = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(np.sum((y - fitted) ** 2)) / denom if denom else None
    crossings = [level["t63_s"] for level in levels if level["f"] in (0.25, 0.5, 0.75)]
    return {"levels": levels, "fit": {"a_c": float(a), "b_c_per_kw": float(b), "r2": r2},
            "tau_s": float(np.median(crossings)) if all(value is not None for value in crossings) else None,
            "t_hot_c": float(a + b * (idle_kw + 0.9 * (peak_kw - idle_kw))),
            "reaches_40c": bool(any(level["trajectory_peak_c"] >= 40 for level in levels)),
            "reaches_45c": bool(any(level["trajectory_peak_c"] >= 45 for level in levels)),
            "rack_spread_at_f1_c": levels[-1]["max_c"] - levels[-1]["min_c"]}


def g3_metrics(times, control, intervention, affected_racks, sane, horizon_s=10800, tail_s=1800) -> dict:
    mask = (times > horizon_s - tail_s) & (times <= horizon_s)
    delta = intervention[mask] - control[mask]
    affected = np.asarray(affected_racks, dtype=int)
    unaffected = np.setdiff1d(np.arange(control.shape[1]), affected)
    affected_delta = float(delta[:, affected].mean())
    unaffected_delta = float(delta[:, unaffected].mean())
    return {"affected_racks": list(affected_racks), "t_air_k_affected": 308.15,
            "delta_affected_c": affected_delta, "delta_unaffected_c": unaffected_delta,
            "sane": bool(sane), "decision": "USABLE" if sane and affected_delta >= 1.0 else "NOT_USABLE"}


def _json(path: Path, value) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _candidate_parameters(fmu_path: Path, out: Path) -> None:
    with zipfile.ZipFile(fmu_path) as archive:
        tree = ET.fromstring(archive.read("modelDescription.xml"))
    rows = []
    for variable in tree.findall("./ModelVariables/ScalarVariable"):
        name = variable.get("name", "")
        if variable.get("causality") == "parameter" and variable.get("variability") == "tunable" and "computeBlock[1].cdu[1]" in name:
            real = variable.find("Real")
            rows.append(f"{name}\tstart={real.get('start', '') if real is not None else ''}")
    out.write_text("# Tunable CDU-1 parameters: listed only; none applied.\n" + "\n".join(sorted(rows)) + "\n")


def _plot(kind, system, branches, summary, out) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for name, (times, temperatures) in branches.items():
        axes[0].plot(times / 3600, temperatures.max(axis=1), label=name)
    axes[0].set(xlabel="Elapsed branch time (h)", ylabel="Maximum rack coolant (°C)")
    axes[0].legend()
    if kind == "g2":
        for name, (_, temperatures) in branches.items():
            axes[1].plot(np.arange(temperatures.shape[1]), temperatures[-1], label=name)
        axes[1].set(xlabel="Rack index", ylabel="Final coolant (°C)")
        axes[1].legend()
        title = f"{system}: G2 packed vs spread, Δ={summary['delta_max_c']:.6f} °C ({summary['class']})"
    elif kind == "g1":
        x = np.array([level["rack_kw"] for level in summary["levels"]])
        y = [level["mean_c"] for level in summary["levels"]]
        axes[1].plot(x, y, "o", label="Final-15-min mean")
        axes[1].plot(x, summary["fit"]["a_c"] + summary["fit"]["b_c_per_kw"] * x, label="Linear fit")
        axes[1].set(xlabel="Uniform rack power (kW)", ylabel="Coolant (°C)")
        axes[1].legend()
        title = f"{system}: G1 five-level uniform load; capped initialization"
    else:
        times, control = branches["control"]
        delta = branches["intervention"][1] - control
        affected = summary["affected_racks"]
        unaffected = np.setdiff1d(np.arange(control.shape[1]), affected)
        axes[1].plot(times / 3600, delta[:, affected].mean(axis=1), label="Affected, intervention − control")
        axes[1].plot(times / 3600, delta[:, unaffected].mean(axis=1), label="Unaffected, intervention − control")
        axes[1].set(xlabel="Elapsed branch time (h)", ylabel="Paired coolant difference (°C)")
        axes[1].legend()
        title = f"G3: What-if: room-air cooling failure on one floor section (not observed {system} behaviour)\n{summary['decision']}"
    figure.suptitle(title)
    figure.savefig(out / f"{kind}_trajectories.png", dpi=160)
    plt.close(figure)


def run_probe(kind: str, system: str, out: Path) -> dict:
    start = perf_counter()
    start_git = git_state()
    config_path = out / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    if config["system"] != system or config["experiment"] != kind:
        raise ValueError("CLI and frozen config disagree")
    for sub in ("results", "plots", "provenance"):
        (out / sub).mkdir(parents=True, exist_ok=True)
        if any(path.name != ".gitkeep" for path in (out / sub).iterdir()):
            raise FileExistsError(f"{out / sub} is not empty; never overwrite a run")
    spec = get_system(system)
    fmu_path = repo_root() / spec.fmu_path
    fmu_sha = sha256_file(fmu_path)
    if fmu_sha != spec.fmu_sha256:
        raise ValueError(f"FMU SHA mismatch: {system}")
    cfg = legacy_config(system)
    idle, peak = rack_power_bounds(cfg)
    n, dt = cfg["NUM_CDUS"], cfg["POWER_UPDATE_FREQ"]
    if config["dt_s"] != dt or config["horizon_s"] != 10800 or config["warmup_s"] != 7200:
        raise ValueError("config contradicts frozen cadence/horizon/warm-up")
    for key, actual in (("idle_kw", idle), ("peak_kw", peak)):
        if key in config and abs(config[key] - actual) > 1e-10:
            raise ValueError(f"RAPS power bounds changed: {key}")
    if kind == "g2":
        spread = uniform_vector(n, idle, peak, 0.6)
        actions = [("spread", spread, Ambient()), ("packed", packed_vector(n, idle, peak, float(spread.sum())), Ambient())]
    elif kind == "g1":
        actions = [(f"f{f:g}", uniform_vector(n, idle, peak, f), Ambient()) for f in (0, 0.25, 0.5, 0.75, 1)]
    else:
        air = tuple(308.15 if rack in spec.whatif_racks else 290.0 for rack in range(n))
        power = uniform_vector(n, idle, peak, 0.6)
        actions = [("control", power, Ambient()), ("intervention", power, Ambient(t_air_k_by_unit=air))]
    input_sequence = {"system": system, "dt_s": dt, "warmup_s": 7200, "warmup_rack_kw": [idle] * n,
                      "horizon_s": 10800, "branches": [{"branch": label, "rack_kw": power.tolist(),
                      "t_air_k": ambient.t_air_k, "t_air_k_by_unit": ambient.t_air_k_by_unit,
                      "t_ext_k": ambient.t_ext_k} for label, power, ambient in actions]}
    _json(out / "provenance/input_sequence.json", input_sequence)
    source_hashes = {str(path.relative_to(repo_root())): sha256_file(path)
                     for path in (repo_root() / "thermoRL/thermorl-v2/thermorl2").rglob("*.py")}
    sanity = {"all_outputs_finite": True, "coolant_min_c": None, "coolant_max_c": None, "warmup_completed": False}
    warm_samples = {}
    warming = True
    backend = FmuBackend(fmu_path, CouplingParams.from_legacy_config(cfg))
    original_observe, original_globals = backend.observe, backend.global_observe

    def checked_observe():
        th = original_observe()
        sanity["all_outputs_finite"] &= all(bool(np.isfinite(values).all()) for values in [th.t_c, *th.extras.values()])
        minimum, maximum = float(th.t_c.min()), float(th.t_c.max())
        sanity["coolant_min_c"] = minimum if sanity["coolant_min_c"] is None else min(sanity["coolant_min_c"], minimum)
        sanity["coolant_max_c"] = maximum if sanity["coolant_max_c"] is None else max(sanity["coolant_max_c"], maximum)
        if warming:
            warm_samples[backend.time_s] = (th.t_c.copy(), th.extras["W_flow_CDUP_kW"].copy())
            if backend.time_s % 600 == 0:
                print(f"{system} {kind}: warm-up {backend.time_s:.0f}/7200 s", flush=True)
        return th

    def checked_globals():
        values = original_globals()
        sanity["all_outputs_finite"] &= bool(np.isfinite(list(values.values())).all())
        return values

    backend.observe, backend.global_observe = checked_observe, checked_globals
    branches, frames, globals_rows, reset_rows = {}, [], [], []
    used = None
    try:
        used = backend.warm_up(np.full(n, idle), Ambient(), dt_s=dt, max_s=7200, settle_k_per_min=-1.0)
        assert used == 7200.0
        sanity["warmup_completed"] = True
        warming = False
        snapshot = None
        snapshot_globals = None
        snapshot_extras = None
        for label, power, ambient in actions:
            backend.reset()
            observations = []
            times = []
            for tick in range(10800 // dt + 1):
                if tick:
                    backend.step(power, dt, ambient)
                th, globals_ = backend.observe(), backend.global_observe()
                if tick == 0:
                    if snapshot is None:
                        snapshot = th.t_c.copy()
                        snapshot_globals = dict(globals_)
                        snapshot_extras = {key: value.copy() for key, value in th.extras.items()}
                    np.testing.assert_array_equal(th.t_c, snapshot)
                    assert globals_ == snapshot_globals
                    for key, value in th.extras.items():
                        np.testing.assert_array_equal(value, snapshot_extras[key])
                    reset_rows.append({"branch": label, "elapsed_s": backend.time_s, "rack_coolant_c": th.t_c.tolist(),
                                       "extras": {key: value.tolist() for key, value in th.extras.items()}, "global": globals_})
                times.append(backend.time_s)
                observations.append(th.t_c.copy())
                frames.append(pd.DataFrame({"branch": label, "t_s": backend.time_s, "rack": np.arange(n),
                                           "t_c": th.t_c, "pump_kw": th.extras["W_flow_CDUP_kW"],
                                           "rack_kw": power if tick else np.full(n, idle),
                                           "t_air_k": (ambient.t_air_k_by_unit or (ambient.t_air_k,) * n) if tick else (290.0,) * n}))
                globals_rows.append({"branch": label, "t_s": backend.time_s, **globals_})
                if tick and backend.time_s % 1800 == 0:
                    print(f"{system} {kind}: {label} {backend.time_s:.0f}/10800 s", flush=True)
            branches[label] = (np.asarray(times), np.asarray(observations))
    except Exception as error:
        _json(out / "provenance/failure.json", {"error_type": type(error).__name__, "error": str(error), "system": system, "warmup_used_s": used, "sanity": sanity})
        raise
    finally:
        backend.close()
    fmu_s = backend.runtime_s()
    completed_wall_s = perf_counter() - start
    sim_hours = (used + 10800 * len(actions)) / 3600
    fmu_cost = fmu_s / sim_hours
    sane = bool(sanity["warmup_completed"] and sanity["all_outputs_finite"] and sanity["coolant_min_c"] >= 10 and sanity["coolant_max_c"] <= 70)
    common = {"system": system, "n_racks": n, "dt_s": dt, "idle_kw": idle, "peak_kw": peak,
              "fmu_sha256": fmu_sha, "warmup_used_s": used, "warmup_status": "capped_preconditioned_not_settled",
              "fmu_s_per_sim_h": fmu_cost, "projected_closed_loop_min_6h": fmu_cost * 6 * 1.5 / 60,
              "sane": sane, "sanity_detail": sanity}
    if kind == "g2":
        spread_stats = branch_statistics(*branches["spread"])
        packed_stats = branch_statistics(*branches["packed"])
        delta = packed_stats["max_c"] - spread_stats["max_c"]
        summary = {**common, "total_kw": float(actions[0][1].sum()),
                   "k_full_racks": int(np.count_nonzero(actions[1][1] == peak)),
                   "spread": spread_stats, "packed": packed_stats, "delta_max_c": delta, "class": classify_delta(delta)}
    elif kind == "g1":
        summary = {**common, **g1_metrics(branches, idle, peak)}
    else:
        summary = {**common, **g3_metrics(branches["control"][0], branches["control"][1], branches["intervention"][1], spec.whatif_racks, sane)}
        _candidate_parameters(fmu_path, out / "results/candidate_cdu_parameters.txt")
    series_path = out / "results/series.parquet"
    pd.concat(frames, ignore_index=True).to_parquet(series_path, index=False)
    pd.DataFrame(globals_rows).to_parquet(out / "results/globals.parquet", index=False)
    warm_frames = [pd.DataFrame({"t_s": time, "rack": np.arange(n), "t_c": temp, "pump_kw": pump, "rack_kw": idle}) for time, (temp, pump) in sorted(warm_samples.items())]
    pd.concat(warm_frames, ignore_index=True).to_parquet(out / "results/warmup.parquet", index=False)
    _json(out / "provenance/branch_initial_observations.json", reset_rows)
    _json(out / "results/summary.json", summary)
    _json(out / "results/scientific_summary.json", scientific_summary(summary))
    _plot(kind, system, branches, summary, out / "plots")
    env = environment()
    (out / "provenance/environment.txt").write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")
    write_manifest(out / "provenance", git=start_git, system=system, fmu_sha256=fmu_sha,
                   workload_sha256=sha256_file(out / "provenance/input_sequence.json"), config=config,
                   config_sha256=sha256_file(config_path), policy=None, seed=None, warmup_used_s=used,
                   warmup_status="capped_preconditioned_not_settled", snapshot_time_s=used,
                   source_sha256=source_hashes, uv_lock_sha256=sha256_file(Path("uv.lock")),
                   fmu_s_per_sim_h=fmu_cost, fmu_cost_denominator_sim_h=sim_hours,
                   timings={"fmu_s": fmu_s, "simulation_wall_s": completed_wall_s, "total_s": perf_counter() - start},
                   series_sha256=sha256_file(series_path))
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def verify_rerun(original: Path, rerun: Path) -> dict:
    comparison = original / "provenance/rerun_1.json"
    if comparison.exists():
        raise FileExistsError(comparison)
    a, b = original / "results", rerun / "results"
    scientific_bytes_equal = (a / "scientific_summary.json").read_bytes() == (b / "scientific_summary.json").read_bytes()
    series_equal = (a / "series.parquet").read_bytes() == (b / "series.parquet").read_bytes()
    pd.testing.assert_frame_equal(pd.read_parquet(a / "series.parquet"), pd.read_parquet(b / "series.parquet"), check_exact=True)
    full_a, full_b = json.loads((a / "summary.json").read_text()), json.loads((b / "summary.json").read_text())
    result = {"scientific_summary_byte_identical": scientific_bytes_equal, "thermal_series_byte_identical": series_equal,
              "thermal_series_values_identical": True, "full_summary_byte_identical": (a / "summary.json").read_bytes() == (b / "summary.json").read_bytes(),
              "excluded_timing_keys": list(TIMING_KEYS), "original_timing": {key: full_a[key] for key in TIMING_KEYS},
              "rerun_timing": {key: full_b[key] for key in TIMING_KEYS}, "cost_used_for_x01": "original",
              "original_summary_sha256": sha256_file(a / "summary.json"), "rerun_summary_sha256": sha256_file(b / "summary.json"),
              "original_series_sha256": sha256_file(a / "series.parquet"), "rerun_series_sha256": sha256_file(b / "series.parquet"),
              "rerun_path": str(rerun)}
    _json(comparison, result)
    if not scientific_bytes_equal or not series_equal:
        raise AssertionError("Lassen G2 rerun is not byte-identical on deterministic content")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("g1", "g2", "g3"))
    parser.add_argument("--system", choices=SYSTEMS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verify-against", type=Path)
    args = parser.parse_args()
    run_probe(args.kind, args.system, args.out)
    if args.verify_against:
        print(json.dumps(verify_rerun(args.verify_against, args.out), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
