"""Plot six-state response families and predeclared predictor associations."""

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
    state_path = ROOT / "state_observables_and_outcomes.csv"
    response_path = ROOT / "run_01/response_ledger.csv"
    prediction_path = ROOT / "run_01/frozen_prediction_ledger.csv"
    states = read(state_path)
    responses = defaultdict(list)
    predictions = defaultdict(list)
    for row in read(response_path):
        responses[row["profile"]].append(row)
    for row in read(prediction_path):
        predictions[row["profile"]].append(row)
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(states)))
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(9, 8))
    for state, color in zip(states, colors):
        name = state["profile"]
        rows = responses[name]
        x = [float(row["elapsed_s"]) for row in rows]
        axes[0].plot(x, [float(row["rack_01_coolant_c"]) for row in rows], color=color, label=name)
        axes[1].plot(x, [float(row["cdu_01_primary_return_c"]) for row in rows], color=color, label=name)
        axes[2].plot(x, [float(row["rack_02_coolant_c"]) for row in rows], color=color, label=name)
    for axis, label in zip(axes, ("Rack 1 coolant", "CDU 1 primary return", "Rack 2 coolant")):
        axis.set_ylabel(f"{label}\nstep − control (°C)")
        axis.grid(alpha=0.2)
    axes[0].legend(fontsize="small", ncol=2)
    axes[-1].set_xlabel("Time after branch (s)")
    fig.tight_layout()
    family_path = ROOT / "paired_response_family.png"
    fig.savefig(family_path, dpi=160)
    plt.close(fig)

    predictors = (
        ("cdu_01_primary_return_c", "CDU 1 primary return (°C)"),
        ("rack_01_coolant_slope_k_per_min", "Rack 1 coolant slope (K/min)"),
        ("datacenter_primary_flow_gpm", "Datacenter primary flow (GPM)"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for axis, (column, label) in zip(axes, predictors):
        for state, color in zip(states, colors):
            x = float(state[column])
            y = float(state["final_paired_increment_c"])
            axis.scatter(x, y, color=color, label=state["profile"])
        axis.set_xlabel(label)
        axis.set_ylabel("Final rack 1 paired increment (°C)")
        axis.grid(alpha=0.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize="small")
    fig.tight_layout()
    association_path = ROOT / "predictor_associations.png"
    fig.savefig(association_path, dpi=160)
    plt.close(fig)
    manifest = {
        "plot_script_sha256": sha256(Path(__file__)),
        "state_table_sha256": sha256(state_path),
        "response_ledger_sha256": sha256(response_path),
        "prediction_ledger_sha256": sha256(prediction_path),
        "paired_response_plot_sha256": sha256(family_path),
        "predictor_association_plot_sha256": sha256(association_path),
    }
    (ROOT / "plot_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
