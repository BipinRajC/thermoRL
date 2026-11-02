"""Reproduce the Task 1.5 matched-background-power FMU step diagnostic.

Run from thermorl-v2 with ``.venv/bin/python artifacts/diagnostics/task_1_5_matched_step_20s/run_matched_step.py``.
The script keeps every non-target rack at its 10.86 kW warm-up load.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
from dataclasses import asdict
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


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
REPO_DIR = OUT_DIR.parents[4]
FMU_PATH = REPO_DIR / "models/POWER9CSM/fmus/lassen.fmu"
DT_S = 20.0
WARM_UP_MAX_S = 7200.0
STEP_DURATION_S = 3600.0
BACKGROUND_KW = 10.86
TARGET_KW = 40.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head() -> str:
    return check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()


def main() -> None:
    ambient = Ambient()
    coupling = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    idle_power = np.full(coupling.num_cdus, BACKGROUND_KW, dtype=np.float64)
    stepped_power = idle_power.copy()
    stepped_power[0] = TARGET_KW
    fmu_inputs = rack_kw_to_fmu_inputs(stepped_power, coupling, ambient)
    output_names = [f"rack_{i:02d}_coolant_c" for i in range(1, coupling.num_cdus + 1)]
    global_names = {
        "fmu.T_prim_supply_C": "cdu_01_primary_supply_c",
        "fmu.T_prim_return_C": "cdu_01_primary_return_c",
        "fmu.V_flow_prim_GPM": "datacenter_primary_flow_gpm",
    }
    rows: list[dict[str, float]] = []

    with_backend_start = perf_counter()
    backend = FmuBackend(FMU_PATH, coupling)
    try:
        warm_up_used_s = backend.warm_up(idle_power, ambient, DT_S, WARM_UP_MAX_S)
        backend.reset()

        def capture(elapsed_s: float) -> None:
            coolant = backend.observe().t_c
            globals_ = backend.global_observe()
            row = {"elapsed_s": elapsed_s}
            row.update(zip(output_names, map(float, coolant)))
            row.update({column: float(globals_[key]) for key, column in global_names.items()})
            rows.append(row)

        capture(0.0)
        for index in range(1, int(STEP_DURATION_S / DT_S) + 1):
            backend.step(stepped_power, DT_S, ambient)
            capture(index * DT_S)

        wall_s = perf_counter() - with_backend_start
        fmu_runtime_s = backend.runtime_s()
    finally:
        backend.close()

    initial = rows[0]
    final = rows[-1]
    rack_01 = "rack_01_coolant_c"
    rack_01_peak = max(rows, key=lambda row: row[rack_01])
    supply_peak = max(rows, key=lambda row: row["cdu_01_primary_supply_c"])
    rise_c = final[rack_01] - initial[rack_01]
    threshold_c = initial[rack_01] + 0.632 * rise_c
    first_crossing = next((row["elapsed_s"] for row in rows[1:] if row[rack_01] >= threshold_c), None)
    metrics = {
        "rack_01_initial_c": initial[rack_01],
        "rack_01_final_c": final[rack_01],
        "rack_01_peak_c": rack_01_peak[rack_01],
        "rack_01_peak_elapsed_s": rack_01_peak["elapsed_s"],
        "rack_01_rise_c": rise_c,
        "rack_01_63pct_threshold_c": threshold_c,
        "rack_01_63pct_elapsed_s": first_crossing,
        "rack_01_63pct_test_index_s": None if first_crossing is None else first_crossing - DT_S,
        "rack_02_change_c": final["rack_02_coolant_c"] - initial["rack_02_coolant_c"],
        "rack_44_change_c": final["rack_44_coolant_c"] - initial["rack_44_coolant_c"],
        "racks_02_to_44_change_min_c": min(
            final[name] - initial[name] for name in output_names[1:]
        ),
        "racks_02_to_44_change_max_c": max(
            final[name] - initial[name] for name in output_names[1:]
        ),
        "cdu_01_primary_supply_initial_c": initial["cdu_01_primary_supply_c"],
        "cdu_01_primary_supply_final_c": final["cdu_01_primary_supply_c"],
        "cdu_01_primary_supply_min_c": min(row["cdu_01_primary_supply_c"] for row in rows),
        "cdu_01_primary_supply_max_c": max(row["cdu_01_primary_supply_c"] for row in rows),
        "cdu_01_primary_supply_peak_elapsed_s": supply_peak["elapsed_s"],
    }

    csv_path = OUT_DIR / "temperature_series.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    elapsed = [row["elapsed_s"] for row in rows]
    fig, (rack_ax, supply_ax) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))
    for key, label in (
        ("rack_01_coolant_c", "Rack 1 coolant: 40 kW"),
        ("rack_02_coolant_c", "Rack 2 coolant: 10.86 kW"),
        ("rack_44_coolant_c", "Rack 44 coolant: 10.86 kW"),
    ):
        rack_ax.plot(elapsed, [row[key] for row in rows], label=label)
    rack_ax.set_ylabel("Coolant temperature (°C)")
    rack_ax.legend()
    rack_ax.grid(alpha=0.2)
    supply_ax.plot(elapsed, [row["cdu_01_primary_supply_c"] for row in rows], color="tab:purple")
    supply_ax.set_xlabel("Time after step (s)")
    supply_ax.set_ylabel("CDU 1 primary supply (°C)")
    supply_ax.grid(alpha=0.2)
    fig.tight_layout()
    plot_path = OUT_DIR / "temperature_trajectory.png"
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)

    provenance = {
        "experiment": "Task 1.5 matched-background-power step diagnostic",
        "git_head": git_head(),
        "source_sha256": {
            "diagnostic": sha256(Path(__file__)),
            "backend": sha256(PROJECT_DIR / "thermorl2/thermal/fmu_backend.py"),
            "coupling": sha256(PROJECT_DIR / "thermorl2/raps_adapter/coupling.py"),
            "task_1_5_test": sha256(PROJECT_DIR / "tests/fmu/test_fmu_backend.py"),
        },
        "fmu_path": str(FMU_PATH.relative_to(REPO_DIR)),
        "fmu_sha256": sha256(FMU_PATH),
        "python": platform.python_version(),
        "fmpy_version": version("fmpy"),
        "numpy_version": np.__version__,
        "ambient": asdict(ambient),
        "coupling": asdict(coupling),
        "protocol": {
            "warm_up_load_kw_each_rack": BACKGROUND_KW,
            "warm_up_max_s": WARM_UP_MAX_S,
            "warm_up_used_s": warm_up_used_s,
            "warm_up_dt_s": DT_S,
            "snapshot_reset_before_step": True,
            "step_rack_01_kw": TARGET_KW,
            "step_racks_02_to_44_kw_each": BACKGROUND_KW,
            "step_duration_s": STEP_DURATION_S,
            "step_dt_s": DT_S,
            "fmu_rack_01_Q_flow_total_W": fmu_inputs[next(iter(fmu_inputs))],
            "fmu_rack_02_Q_flow_total_W": list(fmu_inputs.values())[1],
            "sample_count_including_t0": len(rows),
        },
        "metrics": metrics,
        "runtime_s": {"wall_until_last_sample": wall_s, "fmu_calls_until_last_sample": fmu_runtime_s},
        "series_sha256": sha256(csv_path),
        "plot_sha256": sha256(plot_path),
    }
    json_path = OUT_DIR / "provenance_and_metrics.json"
    json_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"series": str(csv_path), "metadata": str(json_path), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
