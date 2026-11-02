from __future__ import annotations

from pathlib import Path

import pandas as pd

from thermorl.stages.s3_run import run_episode
from thermorl.stages.s4_enrich import enrich
from thermorl.stages.s5_project import project
from thermorl.stages.s6_bundle import bundle


def _episode(path: Path, n: int = 24) -> Path:
    df = pd.DataFrame(
        {
            "event_id": [f"j{i}" for i in range(n)],
            "arrival_s": [float(i * 20) for i in range(n)],
            "duration_s": [120.0] * n,
            "mean_power_kw": [80.0] * n,
            "peak_power_kw": [96.0] * n,
            "nodes": [8] * n,
            "gpus": [8] * n,
            "gpu_milli": [8000] * n,
            "cpu_milli": [16000] * n,
            "mem_mib": [65536] * n,
            "density_kw_per_node": [10.0] * n,
            "workload_class": ["training"] * n,
            "qos": ["LS"] * n,
            "priority": [3] * n,
            "eligible_zones": [(1, 2)] * n,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def main(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parents[2]
    work = root / "artifacts" / "demo_work"
    dest = root / "artifacts" / "bundles" / "demo_ramp"
    ep = _episode(work / "ep.parquet")
    rr = work / "rr"
    th = work / "th"
    run_episode(ep, "round_robin", 7, 20.0, 0.35, rr, scenario_id="ramp")
    run_episode(ep, "thi_lookahead", 7, 20.0, 0.35, th, scenario_id="ramp")
    rr_en = work / "rr_en.jsonl"
    th_en = work / "th_en.jsonl"
    enrich(rr / "ledger.jsonl", rr_en, horizon_ticks=5, tick_s=20.0)
    enrich(th / "ledger.jsonl", th_en, horizon_ticks=5, tick_s=20.0)
    rr_f, rr_m = project(rr_en, work / "rr_frames.jsonl", work / "rr_m.json", "Round-Robin")
    th_f, th_m = project(th_en, work / "th_frames.jsonl", work / "th_m.json", "THI-Lookahead")
    return bundle(
        frames_rr=rr_f,
        frames_thermorl=th_f,
        ledger_rr=rr_en,
        ledger_thermorl=th_en,
        metrics_rr=rr_m,
        metrics_thermorl=th_m,
        out_dir=dest,
        bundle_id="demo_ramp",
        seed=7,
        target_offered_load_ratio=0.35,
    )


if __name__ == "__main__":
    print(main())
