"""Eight-state paired FMU sweep using the immutable preregistration file."""

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

import numpy as np
from raps.system_config import get_system_config

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs
from thermorl2.thermal.fmu_backend import FmuBackend


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
REPO = ROOT.parents[4]
FMU = REPO / "models/POWER9CSM/fmus/lassen.fmu"
PREREG_PATH = ROOT / "preregistration.json"
CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
CDU_VARS = {
    "T_prim_s_C": CDU_SUMMARY + "T_prim_s_C",
    "T_prim_r_C": CDU_SUMMARY + "T_prim_r_C",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def response_metric(rows: list[dict], column: str) -> dict:
    peak = max(rows, key=lambda row: row[column])
    minimum = min(rows, key=lambda row: row[column])
    return {
        "final_increment": rows[-1][column],
        "peak_increment": peak[column],
        "time_of_window_max_s": peak["elapsed_s"],
        "window_max_at_horizon": peak["elapsed_s"] == rows[-1]["elapsed_s"],
        "minimum_increment": minimum[column],
        "time_of_window_min_s": minimum["elapsed_s"],
        "peak_minus_final": peak[column] - rows[-1][column],
    }


def run(run_name: str) -> None:
    prereg = json.loads(PREREG_PATH.read_text())
    protocol = prereg["protocol"]
    times = prereg["state_times_s"]
    dt = protocol["communication_interval_s"]
    horizon = protocol["branch_horizon_s"]
    assert times == [60, 120, 600, 1200, 1800, 3600, 5400, 7200]
    assert dt == 20 and horizon == 3600
    output_dir = ROOT / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    ambient = Ambient(t_air_k=protocol["ambient_air_k"], t_ext_k=protocol["ambient_external_k"])
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    names = columns(coupling.num_cdus)
    heat_keys = power_input_names(coupling)
    thermal_columns = names["coolant"] + names["supply"] + names["return"] + ["datacenter_primary_flow_gpm"]
    background = np.full(coupling.num_cdus, protocol["background_rack_kw_each"], dtype=np.float64)
    stepped = background.copy()
    stepped[protocol["step_target_rack_index_zero_based"]] = protocol["step_target_rack_kw"]
    start_wall = perf_counter()
    handles = {}
    preconditioning = []
    branch_ledger = []
    response_ledger = []
    state_metrics = {}
    backend = FmuBackend(FMU, coupling, extra_rack_vars=CDU_VARS)
    try:
        def capture(elapsed_s: float, power_kw: np.ndarray) -> dict:
            thermal = backend.observe()
            globals_ = backend.global_observe()
            inputs = rack_kw_to_fmu_inputs(power_kw, coupling, ambient)
            row = {"elapsed_s": elapsed_s, "fmu_time_s": backend.time_s}
            row.update(zip(names["coolant"], map(float, thermal.t_c)))
            row.update(zip(names["supply"], map(float, thermal.extras["T_prim_s_C"])))
            row.update(zip(names["return"], map(float, thermal.extras["T_prim_r_C"])))
            row.update(zip(names["power"], map(float, power_kw)))
            row.update(zip(names["heat"], (float(inputs[key]) for key in heat_keys)))
            row["datacenter_primary_flow_gpm"] = float(globals_["fmu.V_flow_prim_GPM"])
            return row

        preconditioning.append(capture(0.0, background))
        for tick in range(1, max(times) // dt + 1):
            backend.step(background, dt, ambient)
            now = tick * dt
            preconditioning.append(capture(float(now), background))
            if now in times:
                handles[now] = backend.save_state()

        for state_time in times:
            handle = handles[state_time]
            branches = {}
            for branch, power in (("control", background), ("step", stepped)):
                backend.restore_state(handle)
                rows = [capture(0.0, background)]
                for tick in range(1, horizon // dt + 1):
                    backend.step(power, dt, ambient)
                    rows.append(capture(float(tick * dt), power))
                branches[branch] = rows
                branch_ledger.extend({"state_time_s": state_time, "branch": branch, **row} for row in rows)
            if branches["control"][0] != branches["step"][0]:
                raise ValueError(f"Branch-time observation mismatch at state {state_time}")
            if branches["control"][0] != {**preconditioning[state_time // dt], "elapsed_s": 0.0}:
                raise ValueError(f"Saved state differs from uninterrupted preconditioning at {state_time}")
            paired = []
            for control, step in zip(branches["control"], branches["step"]):
                if control["elapsed_s"] != step["elapsed_s"] or control["fmu_time_s"] != step["fmu_time_s"]:
                    raise ValueError("Paired branch times differ")
                row = {"state_time_s": state_time, "elapsed_s": step["elapsed_s"]}
                row.update({column: step[column] - control[column] for column in thermal_columns})
                paired.append(row)
            response_ledger.extend(paired)
            initial = branches["control"][0]
            previous = preconditioning[state_time // dt - 1]
            target = names["coolant"][0]
            raw_peak = max(branches["step"], key=lambda row: row[target])
            neighbors = names["coolant"][1:]
            state_metrics[str(state_time)] = {
                "branch_time_observations_match_exactly": True,
                "initial_rack_coolant_c": [initial[name] for name in names["coolant"]],
                "initial_cdu_primary_supply_c": [initial[name] for name in names["supply"]],
                "initial_cdu_primary_return_c": [initial[name] for name in names["return"]],
                "initial_datacenter_primary_flow_gpm": initial["datacenter_primary_flow_gpm"],
                "initial_rack_power_kw": [initial[name] for name in names["power"]],
                "initial_fmu_heat_input_w": [initial[name] for name in names["heat"]],
                "target_rack_coolant_slope_k_per_min": (initial[target] - previous[target]) / dt * 60.0,
                "target_paired_response": response_metric(paired, target),
                "target_absolute_step_peak_c": raw_peak[target],
                "target_absolute_step_peak_time_s": raw_peak["elapsed_s"],
                "target_absolute_step_final_c": branches["step"][-1][target],
                "target_absolute_control_final_c": branches["control"][-1][target],
                "cdu_01_primary_supply_response": response_metric(paired, names["supply"][0]),
                "cdu_01_primary_return_response": response_metric(paired, names["return"][0]),
                "neighbor_final_increment_range_c": [
                    min(paired[-1][name] for name in neighbors),
                    max(paired[-1][name] for name in neighbors),
                ],
                "neighbor_max_abs_increment_c": max(abs(row[name]) for row in paired for name in neighbors),
            }
        runtime = {"wall_until_last_sample_s": perf_counter() - start_wall, "fmu_calls_s": backend.runtime_s()}
    finally:
        for handle in handles.values():
            backend.free_state(handle)
        backend.close()

    paths = {
        "preconditioning": output_dir / "preconditioning.csv",
        "branch_ledger": output_dir / "branch_ledger.csv",
        "response_ledger": output_dir / "response_ledger.csv",
    }
    write_csv(paths["preconditioning"], preconditioning)
    write_csv(paths["branch_ledger"], branch_ledger)
    write_csv(paths["response_ledger"], response_ledger)
    metadata = {
        "experiment": "preregistered eight-state paired response sweep; no acceptance threshold",
        "run_name": run_name,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "source_sha256": {
            "run_script": sha256(Path(__file__)),
            "preregistration": sha256(PREREG_PATH),
            "backend": sha256(PROJECT / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT / "tests/fmu/test_fmu_backend.py"),
            "lassen_config": sha256(REPO / "sim-raps/config/lassen.yaml"),
        },
        "fmu_sha256": sha256(FMU),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "fmpy_version": version("fmpy"),
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "protocol": protocol,
        "state_times_s": times,
        "state_metrics": state_metrics,
        "runtime": runtime,
        "file_sha256": {name: sha256(path) for name, path in paths.items()},
        "ledger_row_counts": {"preconditioning": len(preconditioning), "branches": len(branch_ledger), "responses": len(response_ledger)},
    }
    (output_dir / "metrics_and_provenance.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "run": run_name,
        "rows": metadata["ledger_row_counts"],
        "state_target_response": {k: v["target_paired_response"] for k, v in state_metrics.items()},
        "file_sha256": metadata["file_sha256"],
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", choices=("run_01", "run_02"))
    args = parser.parse_args()
    run(args.run_name)
