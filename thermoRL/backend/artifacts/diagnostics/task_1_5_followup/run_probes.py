"""Run the unchanged Task 1.5 cold-start probe or warmed no-step control.

From thermorl-v2:
  .venv/bin/python artifacts/diagnostics/task_1_5_followup/run_probes.py exact
  .venv/bin/python artifacts/diagnostics/task_1_5_followup/run_probes.py control

Each command starts one FMU in a fresh process and writes its own full series.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from subprocess import check_output
from time import perf_counter

import matplotlib
import numpy as np
from raps.system_config import get_system_config

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


OUT_ROOT = Path(__file__).resolve().parent
PROJECT_DIR = OUT_ROOT.parents[2]
REPO_DIR = OUT_ROOT.parents[4]
FMU_PATH = REPO_DIR / "models/POWER9CSM/fmus/lassen.fmu"
RECON_NOTE = Path("/home/bipin/.claude/plans/thermorl-exadigit-raps-quirky-bird.md")
CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
CDU_VARS = {
    "T_prim_s_C": CDU_SUMMARY + "T_prim_s_C",
    "T_prim_r_C": CDU_SUMMARY + "T_prim_r_C",
}
CASES = {
    "exact": {
        "directory": "exact_spec_probe_15s",
        "label": "Original §3.2 cold-start probe",
        "dt_s": 15.0,
        "total_s": 7200.0,
        "intervention_s": 1800.0,
        "background_kw": 10.0,
        "target_kw": 40.0,
        "warm_up": False,
    },
    "control": {
        "directory": "matched_no_step_control_20s",
        "label": "Warmed matched-load no-step control",
        "dt_s": 20.0,
        "total_s": 3600.0,
        "intervention_s": 0.0,
        "background_kw": 10.86,
        "target_kw": 10.86,
        "warm_up": True,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(*args: str) -> str:
    return check_output(["git", *args], cwd=REPO_DIR, text=True).strip()


def make_columns(n_racks: int) -> tuple[list[str], list[str], list[str]]:
    rack = [f"rack_{i:02d}_coolant_c" for i in range(1, n_racks + 1)]
    supply = [f"cdu_{i:02d}_primary_supply_c" for i in range(1, n_racks + 1)]
    ret = [f"cdu_{i:02d}_primary_return_c" for i in range(1, n_racks + 1)]
    return rack, supply, ret


def metric_for(rows: list[dict[str, float]], column: str, baseline: dict[str, float]) -> dict:
    maximum = max(rows, key=lambda row: row[column])
    minimum = min(rows, key=lambda row: row[column])
    return {
        "baseline_c": baseline[column],
        "final_c": rows[-1][column],
        "change_c": rows[-1][column] - baseline[column],
        "peak_c": maximum[column],
        "peak_sim_time_s": maximum["sim_time_s"],
        "minimum_c": minimum[column],
        "minimum_sim_time_s": minimum["sim_time_s"],
    }


def run(case_name: str) -> None:
    case = CASES[case_name]
    output_dir = OUT_ROOT / case["directory"]
    output_dir.mkdir(parents=True, exist_ok=True)
    ambient = Ambient()
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    n_racks = coupling.num_cdus
    rack_cols, supply_cols, return_cols = make_columns(n_racks)
    background_kw = np.full(n_racks, case["background_kw"], dtype=np.float64)
    post_kw = background_kw.copy()
    post_kw[0] = case["target_kw"]
    background_inputs = rack_kw_to_fmu_inputs(background_kw, coupling, ambient)
    post_inputs = rack_kw_to_fmu_inputs(post_kw, coupling, ambient)
    rows: list[dict[str, float]] = []

    start = perf_counter()
    backend = FmuBackend(FMU_PATH, coupling, extra_rack_vars=CDU_VARS)
    try:
        warm_up_used_s = None
        if case["warm_up"]:
            warm_up_used_s = backend.warm_up(background_kw, ambient, case["dt_s"], max_s=7200.0)
            backend.reset()

        def capture(sim_time_s: float) -> None:
            thermal = backend.observe()
            globals_ = backend.global_observe()
            row = {"sim_time_s": sim_time_s}
            row.update(zip(rack_cols, map(float, thermal.t_c)))
            row.update(zip(supply_cols, map(float, thermal.extras["T_prim_s_C"])))
            row.update(zip(return_cols, map(float, thermal.extras["T_prim_r_C"])))
            row["datacenter_primary_flow_gpm"] = float(globals_["fmu.V_flow_prim_GPM"])
            rows.append(row)

        capture(0.0)
        dt_s = case["dt_s"]
        for index in range(1, int(case["total_s"] / dt_s) + 1):
            start_of_interval_s = (index - 1) * dt_s
            power_kw = post_kw if start_of_interval_s >= case["intervention_s"] else background_kw
            backend.step(power_kw, dt_s, ambient)
            capture(index * dt_s)
        runtime_s = {
            "wall_until_last_sample": perf_counter() - start,
            "fmu_calls_until_last_sample": backend.runtime_s(),
        }
    finally:
        backend.close()

    baseline_index = int(case["intervention_s"] / case["dt_s"])
    baseline = rows[baseline_index]
    post_rows = rows[baseline_index:]
    target_col = rack_cols[0]
    target = metric_for(post_rows, target_col, baseline)
    target_rise = target["change_c"]
    if case_name == "exact" and target_rise > 0:
        threshold_c = baseline[target_col] + 0.632 * target_rise
        crossing = next((row for row in post_rows[1:] if row[target_col] >= threshold_c), None)
        crossing_metrics = {
            "reference": "63.2% of rack 1 rise from pre-step 1800 s sample to final 7200 s sample",
            "threshold_c": threshold_c,
            "crossing_sim_time_s": None if crossing is None else crossing["sim_time_s"],
            "crossing_elapsed_after_step_s": None if crossing is None else crossing["sim_time_s"] - case["intervention_s"],
        }
    else:
        crossing_metrics = None

    metrics = {
        "target_rack_01": target,
        "neighbor_rack_02": metric_for(post_rows, rack_cols[1], baseline),
        "neighbor_rack_44": metric_for(post_rows, rack_cols[-1], baseline),
        "cdu_01_primary_supply": metric_for(post_rows, supply_cols[0], baseline),
        "cdu_01_primary_return": metric_for(post_rows, return_cols[0], baseline),
        "racks_02_to_44_final_change_min_c": min(rows[-1][name] - baseline[name] for name in rack_cols[1:]),
        "racks_02_to_44_final_change_max_c": max(rows[-1][name] - baseline[name] for name in rack_cols[1:]),
        "target_63pct_crossing": crossing_metrics,
    }

    csv_path = output_dir / "temperature_series.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    times = [row["sim_time_s"] for row in rows]
    fig, (rack_ax, cdu_ax) = plt.subplots(2, 1, sharex=True, figsize=(9, 6))
    for column, label in (
        (rack_cols[0], "Rack 1 coolant"),
        (rack_cols[1], "Rack 2 coolant"),
        (rack_cols[-1], "Rack 44 coolant"),
    ):
        rack_ax.plot(times, [row[column] for row in rows], label=label)
    rack_ax.set_ylabel("Coolant temperature (°C)")
    rack_ax.legend()
    rack_ax.grid(alpha=0.2)
    for column, label in (
        (supply_cols[0], "CDU 1 primary supply"),
        (return_cols[0], "CDU 1 primary return"),
    ):
        cdu_ax.plot(times, [row[column] for row in rows], label=label)
    cdu_ax.set_ylabel("Primary temperature (°C)")
    cdu_ax.set_xlabel("FMU simulation time (s)" if case_name == "exact" else "Time since snapshot reset (s)")
    cdu_ax.legend()
    cdu_ax.grid(alpha=0.2)
    if case_name == "exact":
        for axis in (rack_ax, cdu_ax):
            axis.axvline(case["intervention_s"], linestyle="--", color="black", alpha=0.45)
    fig.tight_layout()
    plot_path = output_dir / "temperature_trajectory.png"
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)

    input_names = list(background_inputs)[:n_racks]
    provenance = {
        "experiment": case["label"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_output("rev-parse", "HEAD"),
        "git_status_porcelain": git_output("status", "--porcelain"),
        "source_sha256": {
            "diagnostic": sha256(Path(__file__)),
            "backend": sha256(PROJECT_DIR / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT_DIR / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT_DIR / "tests/fmu/test_fmu_backend.py"),
            "lassen_config": sha256(REPO_DIR / "sim-raps/config/lassen.yaml"),
            "design_spec": sha256(REPO_DIR / "docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md"),
            "implementation_plan": sha256(REPO_DIR / "docs/superpowers/plans/2026-09-12-thermorl-v2-raps-demo.md"),
            "original_probe_reconnaissance": sha256(RECON_NOTE) if RECON_NOTE.exists() else None,
        },
        "fmu_path": str(FMU_PATH.relative_to(REPO_DIR)),
        "fmu_sha256": sha256(FMU_PATH),
        "python_version": platform.python_version(),
        "fmpy_version": version("fmpy"),
        "numpy_version": np.__version__,
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "protocol": {
            **case,
            "warm_up_used_s": warm_up_used_s,
            "snapshot_reset_before_observation": bool(case["warm_up"]),
            "rack_power_kw_before_intervention": list(map(float, background_kw)),
            "rack_power_kw_after_intervention": list(map(float, post_kw)),
            "fmu_heat_input_w_before_intervention": [background_inputs[name] for name in input_names],
            "fmu_heat_input_w_after_intervention": [post_inputs[name] for name in input_names],
            "input_air_k": ambient.t_air_k,
            "input_external_k": ambient.t_ext_k,
            "fmu_setup_tolerance": 1e-5,
        },
        "initial_at_sim_time_0": {
            "rack_coolant_c": [rows[0][name] for name in rack_cols],
            "cdu_primary_supply_c": [rows[0][name] for name in supply_cols],
            "cdu_primary_return_c": [rows[0][name] for name in return_cols],
        },
        "pre_intervention_at_sim_time_s": baseline["sim_time_s"],
        "pre_intervention": {
            "rack_coolant_c": [baseline[name] for name in rack_cols],
            "cdu_primary_supply_c": [baseline[name] for name in supply_cols],
            "cdu_primary_return_c": [baseline[name] for name in return_cols],
        },
        "metrics": metrics,
        "runtime_s": runtime_s,
        "sample_count_including_t0": len(rows),
        "series_sha256": sha256(csv_path),
        "plot_sha256": sha256(plot_path),
    }
    json_path = output_dir / "provenance_and_metrics.json"
    json_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"experiment": case_name, "metrics": metrics, "series_sha256": provenance["series_sha256"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", choices=CASES)
    arguments = parser.parse_args()
    run(arguments.experiment)
