"""Enumerate recorded A/B initial observables; n=2 permits no attribution."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent / "task_1_5_state_dependence/run_01"
STATE_TIMES = {"A_evolving": 1800, "B_warmed": 7200}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def range_summary(values: list[float]) -> dict[str, float]:
    return {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}


def main() -> None:
    with (PREVIOUS / "preconditioning.csv").open(newline="") as source:
        preconditioning = {float(row["elapsed_s"]): row for row in csv.DictReader(source)}
    states = {name: preconditioning[float(time)] for name, time in STATE_TIMES.items()}
    prior = {name: preconditioning[float(time - 20)] for name, time in STATE_TIMES.items()}
    a, b = states.values()
    rows = []
    fields = ("rack_coolant_c", "cdu_primary_supply_c", "cdu_primary_return_c", "rack_power_kw", "rack_fmu_heat_input_w")
    for rack in range(1, 45):
        number = f"{rack:02d}"
        source_names = {
            "rack_coolant_c": f"rack_{number}_coolant_c",
            "cdu_primary_supply_c": f"cdu_{number}_primary_supply_c",
            "cdu_primary_return_c": f"cdu_{number}_primary_return_c",
            "rack_power_kw": f"rack_{number}_power_kw",
            "rack_fmu_heat_input_w": f"rack_{number}_fmu_heat_input_w",
        }
        row = {"rack": rack}
        for field in fields:
            column = source_names[field]
            row[f"A_{field}"] = float(a[column])
            row[f"B_{field}"] = float(b[column])
            row[f"A_minus_B_{field}"] = float(a[column]) - float(b[column])
        for state in STATE_TIMES:
            column = source_names["rack_coolant_c"]
            row[f"{state}_coolant_slope_k_per_min"] = (
                float(states[state][column]) - float(prior[state][column])
            ) / 20.0 * 60.0
        rows.append(row)

    csv_path = ROOT / "initial_observable_differences.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "question": "How do the two recorded initial states differ across external observables?",
        "limitation": "n=2; this enumerates candidates but cannot attribute response differences to any one observable",
        "source_preconditioning_sha256": sha256(PREVIOUS / "preconditioning.csv"),
        "analysis_script_sha256": sha256(Path(__file__)),
        "state_times_s": STATE_TIMES,
        "per_rack_csv_sha256": sha256(csv_path),
        "per_rack_A_minus_B": {
            field: range_summary([row[f"A_minus_B_{field}"] for row in rows]) for field in fields
        },
        "rack_01": rows[0],
        "datacenter_primary_flow_gpm": {
            "A": float(a["datacenter_primary_flow_gpm"]),
            "B": float(b["datacenter_primary_flow_gpm"]),
            "A_minus_B": float(a["datacenter_primary_flow_gpm"]) - float(b["datacenter_primary_flow_gpm"]),
        },
        "one_tick_slope_definition": "(T(t) - T(t-20 s)) / 20 s * 60 s/min",
    }
    (ROOT / "initial_observable_differences.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ranges": summary["per_rack_A_minus_B"], "flow": summary["datacenter_primary_flow_gpm"], "rack_01": rows[0]}, indent=2))


if __name__ == "__main__":
    main()
