"""Plot preregistered aware-minus-blind thermal outcomes by scenario."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
METADATA = ROOT / "run_01/metrics_and_provenance.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    metadata = json.loads(METADATA.read_text())
    outcomes = list(metadata["outcomes"].values())
    labels = [row["scenario"].replace("_", "\n") for row in outcomes]
    colors = ["tab:orange" if row["rules_disagree"] else "tab:gray" for row in outcomes]
    fields = (
        ("aware_minus_blind_placed_rack_absolute_peak_c", 1000.0, "Peak difference (m°C)"),
        ("aware_minus_blind_placed_rack_absolute_final_c", 1.0, "Final difference (°C)"),
        ("aware_minus_blind_paired_peak_increment_c", 1.0, "Paired rise difference (°C)"),
    )
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(9, 8))
    fig.suptitle("State-aware minus round-robin outcome", fontsize=12)
    for axis, (field, multiplier, ylabel) in zip(axes, fields):
        values = [row[field] * multiplier for row in outcomes]
        axis.bar(range(len(outcomes)), values, color=colors)
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.2)
        for index, value in enumerate(values):
            axis.annotate(f"{value:+.3f}", (index, value), xytext=(0, 4 if value >= 0 else -14), textcoords="offset points", ha="center", fontsize="small")
    axes[-1].set_xticks(range(len(labels)), labels)
    fig.tight_layout()
    path = ROOT / "decision_outcomes.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    manifest = {"plot_script_sha256": sha256(Path(__file__)), "metadata_sha256": sha256(METADATA), "plot_sha256": sha256(path)}
    (ROOT / "plot_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
