"""Mechanical selection from the original three G2 summaries (spec §4.1)."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from thermorl2.experiments.provenance import sha256_file, write_manifest


def classify_delta(delta: float) -> str:
    return "GO" if delta >= 2.0 else "WEAK" if delta >= 1.0 else "STOP"


def select_primary(summaries: list[dict]) -> dict:
    eligible = [row for row in summaries if row["sane"]
                and math.isfinite(row["projected_closed_loop_min_6h"])
                and row["projected_closed_loop_min_6h"] <= 30.0
                and row["delta_max_c"] is not None and math.isfinite(row["delta_max_c"])]
    remaining = sorted(eligible, key=lambda row: (-row["delta_max_c"], row["system"]))
    ranking = []
    decisions = []
    while remaining:
        candidate = remaining[0]
        pool = [row for row in remaining if row is candidate or (row["class"] == candidate["class"]
                and row["delta_max_c"] >= 0.8 * candidate["delta_max_c"])]
        chosen = min(pool, key=lambda row: (row["projected_closed_loop_min_6h"], row["system"]))
        ranking.append(chosen["system"])
        decisions.append({"delta_candidate": candidate["system"], "tie_pool": [row["system"] for row in pool],
                          "chosen": chosen["system"], "changed_winner": chosen is not candidate})
        remaining = [row for row in remaining if row is not chosen]
    primary = ranking[0] if ranking else None
    selected = next((row for row in eligible if row["system"] == primary), None)
    return {
        "eligible": sorted(row["system"] for row in eligible),
        "ranking": ranking,
        "primary": primary,
        "runner_up": ranking[1] if len(ranking) > 1 else None,
        "class": selected["class"] if selected else "STOP",
        "tie_break_applied": bool(decisions and len(decisions[0]["tie_pool"]) > 1),
        "selection_stages": decisions,
        "rule_version": "spec-2026-10-27-§4.1",
    }


def main() -> None:
    start = perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("summaries", type=Path, nargs="+")
    args = parser.parse_args()
    if (args.out / "results/summary.json").exists():
        raise FileExistsError("selection output already exists; never overwrite an experiment")
    config = yaml.safe_load((args.out / "config.yaml").read_text())
    summaries = [json.loads(path.read_text()) for path in args.summaries]
    if sorted(row["system"] for row in summaries) != sorted(config["systems"]):
        raise ValueError("X01 must include exactly the preregistered original three systems")
    for row in summaries:
        if row["sane"] and row["class"] != classify_delta(row["delta_max_c"]):
            raise ValueError("source summary classification contradicts the frozen thresholds")
    result = select_primary(summaries)
    hashes = {str(path): sha256_file(path) for path in args.summaries}
    result["source_summary_sha256"] = hashes
    result["cost_source"] = "original G2 runs only"
    for sub in ("results", "plots", "provenance"):
        (args.out / sub).mkdir(parents=True, exist_ok=True)
    table = [{"system": row["system"], "delta_max_c": row["delta_max_c"], "class": row["class"],
              "fmu_s_per_sim_h": row["fmu_s_per_sim_h"],
              "projected_closed_loop_min_6h": row["projected_closed_loop_min_6h"],
              "sane": row["sane"], "eligible": row["system"] in result["eligible"]} for row in summaries]
    pd.DataFrame(table).to_csv(args.out / "results/g2_comparison.csv", index=False, lineterminator="\n")
    figure, axis = plt.subplots(figsize=(8, 5), layout="constrained")
    for i, row in enumerate(table):
        value = row["delta_max_c"]
        axis.bar(i, value if value is not None else 0, color={"GO": "#307d5b", "WEAK": "#c28a25", "STOP": "#a94b4b"}[row["class"]])
        axis.annotate(f"{row['class']}\nC={row['projected_closed_loop_min_6h']:.3f} min", (i, value or 0), xytext=(0, 6), textcoords="offset points", ha="center")
    axis.set_xticks(range(len(table)), [row["system"] for row in table])
    axis.set_ylabel("Packed − spread: final-30-min mean maximum coolant (°C)")
    axis.set_title(f"G2 across POWER9 twins; selected primary: {result['primary']}")
    axis.axhline(2.0, color="#307d5b", linestyle=":", label="GO ≥ 2.0 °C")
    axis.axhline(1.0, color="#c28a25", linestyle=":", label="WEAK ≥ 1.0 °C")
    axis.margins(y=0.25)
    axis.legend()
    figure.savefig(args.out / "plots/g2_cross_system.png", dpi=160)
    plt.close(figure)
    (args.out / "results/summary.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    write_manifest(args.out / "provenance", system="cross_system", fmu_sha256={row["system"]: row.get("fmu_sha256") for row in summaries},
                   workload_sha256=hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
                   config=config, config_sha256=sha256_file(args.out / "config.yaml"), policy=None, seed=None,
                   source_summary_sha256=hashes, timings={"total_s": perf_counter() - start})
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
