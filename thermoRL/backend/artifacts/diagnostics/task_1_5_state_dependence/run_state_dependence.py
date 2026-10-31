"""Paired Lassen FMU state-dependence characterization, without acceptance gates.

From thermorl-v2, run once per fresh process:
  .venv/bin/python artifacts/diagnostics/task_1_5_state_dependence/run_state_dependence.py run_01
  .venv/bin/python artifacts/diagnostics/task_1_5_state_dependence/run_state_dependence.py run_02
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
from thermorl2.raps_adapter.coupling import (
    CouplingParams,
    power_input_names,
    rack_kw_to_fmu_inputs,
)
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
CDU_VARS = {
    "T_prim_s_C": CDU_SUMMARY + "T_prim_s_C",
    "T_prim_r_C": CDU_SUMMARY + "T_prim_r_C",
}
DT_S = 20
PRECONDITION_S = 7200
STATE_TIMES = {"A_evolving": 1800, "B_warmed": 7200}
HORIZON_S = 3600
BACKGROUND_KW = 10.86
TARGET_KW = 40.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def columns(n: int) -> dict[str, list[str]]:
    return {
        "coolant": [f"rack_{i:02d}_coolant_c" for i in range(1, n + 1)],
        "supply": [f"cdu_{i:02d}_primary_supply_c" for i in range(1, n + 1)],
        "return": [f"cdu_{i:02d}_primary_return_c" for i in range(1, n + 1)],
        "power": [f"rack_{i:02d}_power_kw" for i in range(1, n + 1)],
        "heat": [f"rack_{i:02d}_fmu_heat_input_w" for i in range(1, n + 1)],
    }


def response_metrics(rows: list[dict[str, float]], column: str) -> dict:
    peak = max(rows, key=lambda row: row[column])
    minimum = min(rows, key=lambda row: row[column])
    final = rows[-1][column]
    start = rows[0][column]

    def crossing(reference: float) -> float | None:
        if reference <= 0:
            return None
        threshold = start + 0.632 * reference
        return next((row["elapsed_s"] for row in rows[1:] if row[column] >= threshold), None)

    return {
        "initial_increment": start,
        "final_increment": final,
        "peak_increment": peak[column],
        "time_to_peak_s": peak["elapsed_s"],
        "minimum_increment": minimum[column],
        "time_to_minimum_s": minimum["elapsed_s"],
        "peak_minus_final": peak[column] - final,
        "first_63pct_of_final_increment_s": crossing(final - start),
        "first_63pct_of_peak_increment_s": crossing(peak[column] - start),
    }


def paired_difference(step: list[dict], control: list[dict], thermal_columns: list[str]) -> list[dict]:
    if len(step) != len(control):
        raise ValueError("Paired branches have different lengths")
    if step[0] != control[0]:
        raise ValueError("Branch-time observations or power inputs differ")
    result = []
    for stepped, held in zip(step, control):
        if stepped["elapsed_s"] != held["elapsed_s"] or stepped["fmu_time_s"] != held["fmu_time_s"]:
            raise ValueError("Paired branches are not time-aligned")
        result.append({
            "elapsed_s": stepped["elapsed_s"],
            **{column: stepped[column] - held[column] for column in thermal_columns},
        })
    return result


def plot_response(path: Path, differences: dict[str, list[dict]], names: dict[str, list[str]]) -> None:
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(9, 10))
    colors = {"A_evolving": "tab:orange", "B_warmed": "tab:blue"}
    for state, rows in differences.items():
        x = [row["elapsed_s"] for row in rows]
        color = colors[state]
        axes[0].plot(x, [row[names["coolant"][0]] for row in rows], color=color, label=state)
        axes[1].plot(x, [row[names["coolant"][1]] for row in rows], color=color, label=f"{state}: rack 2")
        axes[2].plot(x, [row[names["supply"][0]] for row in rows], color=color, label=f"{state}: CDU 1 supply")
        axes[3].plot(x, [row[names["return"][0]] for row in rows], color=color, label=f"{state}: CDU 1 return")
    for axis, label in zip(axes, ("Rack 1 coolant", "Rack 2 coolant", "CDU 1 supply", "CDU 1 return")):
        axis.set_ylabel(f"{label}\nstep − control (°C)")
        axis.grid(alpha=0.2)
        axis.legend()
    axes[-1].set_xlabel("Time after branch (s)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_absolute(path: Path, branches: dict[str, dict[str, list[dict]]], names: dict[str, list[str]]) -> None:
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(9, 10))
    colors = {"A_evolving": "tab:orange", "B_warmed": "tab:blue"}
    for state, state_branches in branches.items():
        for branch, rows in state_branches.items():
            x = [row["elapsed_s"] for row in rows]
            label = f"{state}: {branch}"
            style = "-" if branch == "step" else "--"
            for axis, column in zip(axes, (
                names["coolant"][0], names["coolant"][1],
                names["supply"][0], names["return"][0],
            )):
                axis.plot(x, [row[column] for row in rows], color=colors[state], linestyle=style, label=label)
    for axis, label in zip(axes, ("Rack 1 coolant", "Rack 2 coolant", "CDU 1 supply", "CDU 1 return")):
        axis.set_ylabel(f"{label} (°C)")
        axis.grid(alpha=0.2)
        axis.legend(fontsize="small")
    axes[-1].set_xlabel("Time after branch (s)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(run_name: str) -> None:
    output_dir = ROOT / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    ambient = Ambient()
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    names = columns(coupling.num_cdus)
    heat_keys = power_input_names(coupling)
    thermal_columns = names["coolant"] + names["supply"] + names["return"] + ["datacenter_primary_flow_gpm"]
    background = np.full(coupling.num_cdus, BACKGROUND_KW, dtype=np.float64)
    stepped = background.copy()
    stepped[0] = TARGET_KW
    input_profiles = {
        "background": rack_kw_to_fmu_inputs(background, coupling, ambient),
        "step": rack_kw_to_fmu_inputs(stepped, coupling, ambient),
    }
    start_wall = perf_counter()
    handles: dict[str, object] = {}
    preconditioning: list[dict] = []
    branches: dict[str, dict[str, list[dict]]] = {}
    differences: dict[str, list[dict]] = {}
    branch_checks: dict[str, bool] = {}
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    try:
        def capture(elapsed_s: float, power_kw: np.ndarray) -> dict:
            thermal = backend.observe()
            globals_ = backend.global_observe()
            fmu_inputs = rack_kw_to_fmu_inputs(power_kw, coupling, ambient)
            row = {"elapsed_s": elapsed_s, "fmu_time_s": backend.time_s}
            row.update(zip(names["coolant"], map(float, thermal.t_c)))
            row.update(zip(names["supply"], map(float, thermal.extras["T_prim_s_C"])))
            row.update(zip(names["return"], map(float, thermal.extras["T_prim_r_C"])))
            row.update(zip(names["power"], map(float, power_kw)))
            row.update(zip(names["heat"], (float(fmu_inputs[key]) for key in heat_keys)))
            row["datacenter_primary_flow_gpm"] = float(globals_["fmu.V_flow_prim_GPM"])
            return row

        preconditioning.append(capture(0.0, background))
        for tick in range(1, PRECONDITION_S // DT_S + 1):
            backend.step(background, DT_S, ambient)
            now = tick * DT_S
            preconditioning.append(capture(float(now), background))
            for state, state_time in STATE_TIMES.items():
                if now == state_time:
                    handles[state] = backend.save_state()

        for state, handle in handles.items():
            branches[state] = {}
            for branch, power in (("control", background), ("step", stepped)):
                backend.restore_state(handle)
                rows = [capture(0.0, background)]
                for tick in range(1, HORIZON_S // DT_S + 1):
                    backend.step(power, DT_S, ambient)
                    rows.append(capture(float(tick * DT_S), power))
                branches[state][branch] = rows
            branch_checks[state] = branches[state]["control"][0] == branches[state]["step"][0]
            if not branch_checks[state]:
                raise ValueError(f"{state}: branch-time observations differ")
            differences[state] = paired_difference(
                branches[state]["step"], branches[state]["control"], thermal_columns
            )
        runtime = {"wall_until_last_sample_s": perf_counter() - start_wall, "fmu_calls_s": backend.runtime_s()}
    finally:
        for handle in handles.values():
            backend.free_state(handle)
        backend.close()

    files = {"preconditioning": "preconditioning.csv"}
    write_csv(output_dir / files["preconditioning"], preconditioning)
    for state in STATE_TIMES:
        for branch in ("control", "step"):
            key = f"{state}_{branch}"
            files[key] = f"{key}.csv"
            write_csv(output_dir / files[key], branches[state][branch])
        key = f"{state}_step_minus_control"
        files[key] = f"{key}.csv"
        write_csv(output_dir / files[key], differences[state])

    cross_state = []
    for a, b in zip(differences["A_evolving"], differences["B_warmed"]):
        if a["elapsed_s"] != b["elapsed_s"]:
            raise ValueError("State responses are not time-aligned")
        cross_state.append({
            "elapsed_s": a["elapsed_s"],
            **{column: b[column] - a[column] for column in thermal_columns},
        })
    files["B_minus_A_response"] = "B_minus_A_response.csv"
    write_csv(output_dir / files["B_minus_A_response"], cross_state)
    plot_path = output_dir / "paired_response.png"
    plot_response(plot_path, differences, names)
    absolute_plot_path = output_dir / "absolute_trajectories.png"
    plot_absolute(absolute_plot_path, branches, names)

    summaries = {}
    for state in STATE_TIMES:
        delta = differences[state]
        initial = branches[state]["control"][0]
        neighbor_cols = names["coolant"][1:]
        neighbor_max = max(
            ((abs(row[column]), row["elapsed_s"], column) for row in delta for column in neighbor_cols)
        )
        summaries[state] = {
            "saved_fmu_time_s": STATE_TIMES[state],
            "branch_initial_observations_match_exactly": branch_checks[state],
            "initial_rack_coolant_c": [initial[column] for column in names["coolant"]],
            "initial_cdu_primary_supply_c": [initial[column] for column in names["supply"]],
            "initial_cdu_primary_return_c": [initial[column] for column in names["return"]],
            "initial_datacenter_primary_flow_gpm": initial["datacenter_primary_flow_gpm"],
            "target_rack_01": response_metrics(delta, names["coolant"][0]),
            "neighbor_rack_02": response_metrics(delta, names["coolant"][1]),
            "neighbor_rack_44": response_metrics(delta, names["coolant"][-1]),
            "neighbor_final_increment_range_c": [
                min(delta[-1][column] for column in neighbor_cols),
                max(delta[-1][column] for column in neighbor_cols),
            ],
            "neighbor_max_abs_increment_c_time_column": neighbor_max,
            "cdu_01_primary_supply": response_metrics(delta, names["supply"][0]),
            "cdu_01_primary_return": response_metrics(delta, names["return"][0]),
        }
    cross_metrics = {
        column: {
            "B_minus_A_final": cross_state[-1][column],
            "B_minus_A_max_abs": max(abs(row[column]) for row in cross_state),
            "B_minus_A_max_abs_time_s": max(cross_state, key=lambda row: abs(row[column]))["elapsed_s"],
            "mean_abs_over_3600s": float(np.trapezoid(
                [abs(row[column]) for row in cross_state],
                [row["elapsed_s"] for row in cross_state],
            ) / HORIZON_S),
        }
        for column in (
            names["coolant"][0], names["coolant"][1], names["coolant"][-1],
            names["supply"][0], names["return"][0],
        )
    }
    metadata = {
        "experiment": "Task 1.5 state-dependent response characterization; no acceptance test",
        "run_name": run_name,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "source_sha256": {
            "experiment_script": sha256(Path(__file__)),
            "backend": sha256(PROJECT / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT / "tests/fmu/test_fmu_backend.py"),
            "lassen_config": sha256(REPO / "sim-raps/config/lassen.yaml"),
            "characterization_design": sha256(ROOT.parent / "task_1_5_followup/characterization_report.md"),
        },
        "fmu_sha256": sha256(FMU),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "fmpy_version": version("fmpy"),
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "protocol": {
            "dt_s": DT_S,
            "preconditioning_background_kw_per_rack": BACKGROUND_KW,
            "state_times_s": STATE_TIMES,
            "post_branch_horizon_s": HORIZON_S,
            "step_rack_01_power_kw": TARGET_KW,
            "other_racks_power_kw": BACKGROUND_KW,
            "background_power_kw_vector": list(map(float, background)),
            "step_power_kw_vector": list(map(float, stepped)),
            "background_fmu_heat_input_w_vector": [input_profiles["background"][key] for key in heat_keys],
            "step_fmu_heat_input_w_vector": [input_profiles["step"][key] for key in heat_keys],
            "fmu_setup_tolerance": 1e-5,
            "branch_order": ["control", "step"],
            "difference_definition": "step branch minus same-state no-step control",
            "cross_state_definition": "B_warmed difference response minus A_evolving difference response",
        },
        "summaries": summaries,
        "cross_state_metrics": cross_metrics,
        "runtime": runtime,
        "file_sha256": {key: sha256(output_dir / value) for key, value in files.items()},
        "plot_sha256": sha256(plot_path),
        "absolute_plot_sha256": sha256(absolute_plot_path),
    }
    (output_dir / "provenance_and_metrics.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "run": run_name,
        "A_target": summaries["A_evolving"]["target_rack_01"],
        "B_target": summaries["B_warmed"]["target_rack_01"],
        "cross_state_target": cross_metrics[names["coolant"][0]],
        "branch_checks": branch_checks,
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", choices=("run_01", "run_02"))
    args = parser.parse_args()
    run(args.run_name)
