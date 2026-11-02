"""Plot frozen-model transfer errors and paired plant responses."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run_01"
NAMES = ("constant_hold", "late_high_then_base", "low_then_raised_base")
COLORS = {"constant_hold": "tab:blue", "late_high_then_base": "tab:red", "low_then_raised_base": "tab:green"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def main() -> None:
    responses = defaultdict(list)
    predictions = defaultdict(list)
    for row in read(RUN / "response_ledger.csv"):
        responses[row["profile"]].append(row)
    for row in read(RUN / "prediction_ledger.csv"):
        predictions[row["profile"]].append(row)
    fig, axes = plt.subplots(5, 1, sharex=True, figsize=(9, 12))
    for name in NAMES:
        response = responses[name]
        predicted = predictions[name]
        x = [float(row["elapsed_s"]) for row in response]
        color = COLORS[name]
        axes[0].plot(x, [float(row["rack_01_coolant_c"]) for row in response], color=color, label=f"{name}: observed")
        axes[0].plot(x, [float(row["frozen_model_predicted_c"]) for row in predicted], color=color, linestyle="--", alpha=0.75, label=f"{name}: frozen prediction")
        axes[1].plot(x, [float(row["signed_residual_c"]) for row in predicted], color=color, label=name)
        axes[2].plot(x, [float(row["rack_02_coolant_c"]) for row in response], color=color, label=name)
        axes[3].plot(x, [float(row["cdu_01_primary_supply_c"]) for row in response], color=color, label=name)
        axes[4].plot(x, [float(row["cdu_01_primary_return_c"]) for row in response], color=color, label=name)
    for axis, ylabel in zip(axes, (
        "Rack 1 step − control (°C)",
        "Observed − predicted (°C)",
        "Rack 2 step − control (°C)",
        "CDU 1 supply step − control (°C)",
        "CDU 1 return step − control (°C)",
    )):
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.2)
        axis.legend(fontsize="small", ncol=2)
    axes[-1].set_xlabel("Time after branch (s)")
    fig.tight_layout()
    plot_path = ROOT / "frozen_model_transfer.png"
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)
    manifest = {
        "plot_script_sha256": sha256(Path(__file__)),
        "response_ledger_sha256": sha256(RUN / "response_ledger.csv"),
        "prediction_ledger_sha256": sha256(RUN / "prediction_ledger.csv"),
        "plot_sha256": sha256(plot_path),
    }
    (ROOT / "plot_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
