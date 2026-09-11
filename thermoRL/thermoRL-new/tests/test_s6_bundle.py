"""M6 gate: S4 backfills outcomes, S5 projects VizFrames, S6 emits a static bundle."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from thermorl.stages.s3_run import run_episode
from thermorl.stages.s4_enrich import enrich
from thermorl.stages.s5_project import project
from thermorl.stages.s6_bundle import bundle


def _tiny_episode(path: Path) -> Path:
    df = pd.DataFrame(
        {
            "event_id": [f"j{i}" for i in range(8)],
            "arrival_s": [float(i * 20) for i in range(8)],
            "duration_s": [80.0] * 8,
            "mean_power_kw": [31.1] * 8,
            "peak_power_kw": [37.0] * 8,
            "nodes": [4] * 8,
            "gpus": [8] * 8,
            "gpu_milli": [4000] * 8,
            "cpu_milli": [16000] * 8,
            "mem_mib": [65536] * 8,
            "density_kw_per_node": [7.775] * 8,
            "workload_class": ["training"] * 8,
            "qos": ["LS"] * 8,
            "priority": [3] * 8,
            "eligible_zones": [(0, 1, 2)] * 8,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def _run(tmp: Path, policy_id: str) -> Path:
    ep = _tiny_episode(tmp / f"{policy_id}_ep.parquet")
    out = tmp / policy_id
    run_episode(
        episode_path=ep,
        policy_id=policy_id,
        seed=5,
        tick_s=20.0,
        target_offered_load_ratio=0.35,
        out_dir=out,
        scenario_id="ramp",
    )
    return out


def test_s4_backfills_outcome(tmp_path: Path) -> None:
    run_dir = _run(tmp_path, "thi_greedy")
    out = tmp_path / "enriched.jsonl"
    enrich(run_dir / "ledger.jsonl", out, horizon_ticks=3, tick_s=20.0)
    rows = [json.loads(line) for line in out.read_text().splitlines() if line]
    assert len(rows) > 0
    assert all(r["outcome"] is not None for r in rows)
    first = rows[0]["outcome"]
    assert first["horizon_ticks"] == 3
    assert len(first["thi_actual_h"]) == 3
    assert len(first["thi_predicted_h"]) == 3
    assert len(first["prediction_error"]) == 3


def test_s5_writes_vizframes_and_colour_anchors(tmp_path: Path) -> None:
    run_dir = _run(tmp_path, "round_robin")
    enriched = tmp_path / "rr_enriched.jsonl"
    enrich(run_dir / "ledger.jsonl", enriched, horizon_ticks=3, tick_s=20.0)
    frames_path = tmp_path / "frames.jsonl"
    metrics_path = tmp_path / "metrics.json"
    project(enriched, frames_path, metrics_path, policy_mode="Round-Robin")
    frames = [json.loads(line) for line in frames_path.read_text().splitlines() if line]
    assert len(frames) > 0
    f0 = frames[0]
    assert "zones" in f0 and len(f0["zones"]) == 3
    assert "racks" in f0
    assert "metrics" in f0
    assert "offered_demand_ratio" in f0["metrics"]
    assert "physical_facility_load_kw" in f0["metrics"]
    anchors = json.loads(metrics_path.read_text())
    assert "thi_p10" in anchors
    assert "thi_p90" in anchors
    assert anchors["thi_p10"] <= anchors["thi_p90"]


def test_s6_emits_static_bundle(tmp_path: Path) -> None:
    rr = _run(tmp_path / "rr_src", "round_robin")
    th = _run(tmp_path / "th_src", "thi_lookahead")
    rr_en = tmp_path / "rr.jsonl"
    th_en = tmp_path / "th.jsonl"
    enrich(rr / "ledger.jsonl", rr_en, horizon_ticks=3, tick_s=20.0)
    enrich(th / "ledger.jsonl", th_en, horizon_ticks=3, tick_s=20.0)
    rr_frames = tmp_path / "rr_frames.jsonl"
    th_frames = tmp_path / "th_frames.jsonl"
    rr_m = tmp_path / "rr_m.json"
    th_m = tmp_path / "th_m.json"
    project(rr_en, rr_frames, rr_m, policy_mode="Round-Robin")
    project(th_en, th_frames, th_m, policy_mode="THI-Lookahead")
    dest = tmp_path / "bundle"
    bundle(
        frames_rr=rr_frames,
        frames_thermorl=th_frames,
        ledger_rr=rr_en,
        ledger_thermorl=th_en,
        metrics_rr=rr_m,
        metrics_thermorl=th_m,
        out_dir=dest,
        bundle_id="demo_ramp",
        seed=5,
        target_offered_load_ratio=0.35,
    )
    required = (
        "index.html",
        "manifest.json",
        "frames_rr.jsonl",
        "frames_thermorl.jsonl",
        "ledger_rr.jsonl",
        "ledger_thermorl.jsonl",
        "metrics.json",
    )
    for name in required:
        assert (dest / name).exists(), name
    man = json.loads((dest / "manifest.json").read_text())
    assert man["target_offered_load_ratio"] == 0.35
    assert man["policies"] == ["round_robin", "thi_lookahead"]
    metrics = json.loads((dest / "metrics.json").read_text())
    assert "thi_p10" in metrics
    assert "thi_p90" in metrics


def test_demo_bundle_has_player_and_inline_data() -> None:
    root = Path(__file__).resolve().parents[1]
    dest = root / "artifacts" / "bundles" / "demo_ramp"
    assert (dest / "index.html").exists()
    assert (dest / "bundle-data.js").exists()
    html = (dest / "index.html").read_text()
    assert "bundle-data.js" in html
    assert (dest / "frames_rr.jsonl").exists()
    assert (dest / "ledger_thermorl.jsonl").exists()
