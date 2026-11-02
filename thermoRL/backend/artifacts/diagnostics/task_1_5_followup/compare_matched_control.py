"""Compare the earlier matched step against its warmed no-step control.

Run from thermorl-v2 with ``.venv/bin/python artifacts/diagnostics/task_1_5_followup/compare_matched_control.py``.
The source CSVs are left unchanged.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
MATCHED = ROOT.parent / "task_1_5_matched_step_20s/temperature_series.csv"
CONTROL = ROOT / "matched_no_step_control_20s/temperature_series.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def main() -> None:
    matched = read(MATCHED)
    control = read(CONTROL)
    if len(matched) != len(control):
        raise ValueError("Matched and control sample counts differ")
    common_columns = [column for column in matched[0] if column in control[0] and column != "elapsed_s"]
    common_columns.remove("datacenter_primary_flow_gpm")
    common_columns.append("datacenter_primary_flow_gpm")
    for step_row, control_row in zip(matched, control):
        if float(step_row["elapsed_s"]) != float(control_row["sim_time_s"]):
            raise ValueError("Matched and control time axes differ")
    if any(float(matched[0][column]) != float(control[0][column]) for column in common_columns):
        raise ValueError("Matched and control initial observations differ")

    differences = []
    for step_row, control_row in zip(matched, control):
        row = {"elapsed_s": float(step_row["elapsed_s"])}
        row.update({column: float(step_row[column]) - float(control_row[column]) for column in common_columns})
        differences.append(row)

    difference_path = ROOT / "matched_minus_control_series.csv"
    with difference_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(differences[0]))
        writer.writeheader()
        writer.writerows(differences)

    selected = [
        "rack_01_coolant_c",
        "rack_02_coolant_c",
        "rack_44_coolant_c",
        "cdu_01_primary_supply_c",
        "cdu_01_primary_return_c",
    ]
    metrics = {}
    for column in selected:
        largest = max(differences, key=lambda row: abs(row[column]))
        metrics[column] = {
            "final_difference": differences[-1][column],
            "max_absolute_difference": abs(largest[column]),
            "max_absolute_difference_elapsed_s": largest["elapsed_s"],
            "signed_difference_at_max_absolute": largest[column],
        }
    neighbor_columns = [f"rack_{index:02d}_coolant_c" for index in range(2, 45)]
    metrics["racks_02_to_44_final_difference_range_c"] = [
        min(differences[-1][column] for column in neighbor_columns),
        max(differences[-1][column] for column in neighbor_columns),
    ]

    times = [row["elapsed_s"] for row in differences]
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(9, 8))
    for axis, columns, labels in (
        (axes[0], [selected[0]], ["Rack 1 coolant"]),
        (axes[1], selected[1:3], ["Rack 2 coolant", "Rack 44 coolant"]),
        (axes[2], selected[3:], ["CDU 1 primary supply", "CDU 1 primary return"]),
    ):
        for column, label in zip(columns, labels):
            axis.plot(times, [row[column] for row in differences], label=label)
        axis.legend()
        axis.grid(alpha=0.2)
        axis.set_ylabel("Step minus control (°C)")
    axes[-1].set_xlabel("Time since snapshot reset (s)")
    fig.tight_layout()
    plot_path = ROOT / "matched_minus_control.png"
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)

    summary = {
        "comparison": "40/10.86 kW matched step minus 10.86/10.86 kW no-step control",
        "initial_observations_identical_for_all_common_columns": True,
        "common_observation_columns": common_columns,
        "sample_count": len(differences),
        "source_csv_sha256": {"matched": sha256(MATCHED), "control": sha256(CONTROL)},
        "comparison_script_sha256": sha256(Path(__file__)),
        "difference_csv_sha256": sha256(difference_path),
        "difference_plot_sha256": sha256(plot_path),
        "metrics": metrics,
    }
    summary_path = ROOT / "matched_minus_control.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
