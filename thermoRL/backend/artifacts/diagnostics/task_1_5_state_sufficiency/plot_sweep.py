"""Plot preregistered sweep trajectories and observed state/peak relations."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def main() -> None:
    response_path = ROOT / "run_01/response_ledger.csv"
    table_path = ROOT / "state_observables_and_responses.csv"
    by_state = defaultdict(list)
    for row in read(response_path):
        by_state[int(row["state_time_s"])].append(row)
    table = read(table_path)
    states = sorted(by_state)
    colors = plt.cm.viridis(np.linspace(0.05, 0.95, len(states)))
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(9, 11))
    columns = [
        ("rack_01_coolant_c", "Rack 1 coolant"),
        ("rack_02_coolant_c", "Rack 2 coolant"),
        ("cdu_01_primary_supply_c", "CDU 1 primary supply"),
        ("cdu_01_primary_return_c", "CDU 1 primary return"),
    ]
    for state, color in zip(states, colors):
        rows = by_state[state]
        x = [float(row["elapsed_s"]) for row in rows]
        for axis, (column, _) in zip(axes, columns):
            axis.plot(x, [float(row[column]) for row in rows], color=color, label=f"{state} s")
    for axis, (_, label) in zip(axes, columns):
        axis.set_ylabel(f"{label}\nstep − control (°C)")
        axis.grid(alpha=0.2)
    axes[0].legend(ncol=4, fontsize="small")
    axes[-1].set_xlabel("Time after branch (s)")
    fig.tight_layout()
    family_path = ROOT / "response_family.png"
    fig.savefig(family_path, dpi=160)
    plt.close(fig)

    x = [float(row["target_rack_coolant_c"]) for row in table]
    y_peak = [float(row["absolute_step_peak_c"]) for row in table]
    y_time = [float(row["absolute_step_peak_time_s"]) for row in table]
    fig, (peak_ax, time_ax) = plt.subplots(1, 2, figsize=(10, 4))
    for index, row in enumerate(table):
        state = int(row["state_time_s"])
        peak_ax.scatter(x[index], y_peak[index], color=colors[index])
        time_ax.scatter(x[index], y_time[index], color=colors[index])
        peak_ax.annotate(str(state), (x[index], y_peak[index]), xytext=(3, 3), textcoords="offset points", fontsize="small")
        time_ax.annotate(str(state), (x[index], y_time[index]), xytext=(3, 3), textcoords="offset points", fontsize="small")
    peak_ax.set_xlabel("Initial rack 1 coolant (°C)")
    peak_ax.set_ylabel("Absolute step-branch peak (°C)")
    time_ax.set_xlabel("Initial rack 1 coolant (°C)")
    time_ax.set_ylabel("Time to absolute step peak (s)")
    for axis in (peak_ax, time_ax):
        axis.grid(alpha=0.2)
    fig.tight_layout()
    attractor_path = ROOT / "absolute_peak_vs_initial_state.png"
    fig.savefig(attractor_path, dpi=160)
    plt.close(fig)

    manifest = {
        "plot_script_sha256": sha256(Path(__file__)),
        "response_ledger_sha256": sha256(response_path),
        "state_table_sha256": sha256(table_path),
        "response_family_png_sha256": sha256(family_path),
        "absolute_peak_png_sha256": sha256(attractor_path),
    }
    (ROOT / "plot_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
