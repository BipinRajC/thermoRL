"""M4 gate: ledger emitted for every policy including Oracle LP."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from thermorl.policies.base import POLICY_IDS
from thermorl.stages.s3_run import run_episode

REQUIRED = (
    "fcfs_naive",
    "round_robin",
    "threshold_reactive",
    "carbon_only",
    "thi_greedy",
    "oracle_lp",
)


def test_policy_registry_includes_rungs_and_oracle() -> None:
    for pid in REQUIRED:
        assert pid in POLICY_IDS


def _tiny_episode(path: Path) -> Path:
    df = pd.DataFrame(
        {
            "event_id": [f"j{i}" for i in range(6)],
            "arrival_s": [0.0, 20.0, 40.0, 60.0, 80.0, 100.0],
            "duration_s": [80.0] * 6,
            "mean_power_kw": [31.1] * 6,
            "peak_power_kw": [37.0] * 6,
            "nodes": [4] * 6,
            "gpus": [8] * 6,
            "gpu_milli": [4000] * 6,
            "cpu_milli": [16000] * 6,
            "mem_mib": [65536] * 6,
            "density_kw_per_node": [7.775] * 6,
            "workload_class": ["training"] * 6,
            "qos": ["LS"] * 6,
            "priority": [3] * 6,
            "eligible_zones": [(0, 1, 2)] * 6,
        }
    )
    df.to_parquet(path, index=False)
    return path


@pytest.mark.parametrize("policy_id", REQUIRED)
def test_s3_emits_ledger_for_policy(tmp_path: Path, policy_id: str) -> None:
    ep_path = _tiny_episode(tmp_path / "ep.parquet")
    out = tmp_path / policy_id
    manifest = run_episode(
        episode_path=ep_path,
        policy_id=policy_id,
        seed=3,
        tick_s=20.0,
        target_offered_load_ratio=0.35,
        out_dir=out,
    )
    ledger = out / "ledger.jsonl"
    assert ledger.exists()
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    assert len(rows) > 0
    actions = {r["action"] for r in rows}
    assert actions <= {"ASSIGN_Z1", "ASSIGN_Z2", "ASSIGN_Z3", "DEFER"}
    assert all(r["policy_id"] == policy_id for r in rows)
    assert all("candidates" in r and len(r["candidates"]) >= 1 for r in rows)
    assert manifest.target_offered_load_ratio == 0.35
