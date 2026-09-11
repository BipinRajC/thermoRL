"""M3 gate: realised offered-load ratio within 5% of target."""

from __future__ import annotations

from pathlib import Path

import pytest

from thermorl.stages.s1_extract import extract
from thermorl.stages.s2_episode import generate_episode


@pytest.mark.parametrize("rho", [0.35, 0.90, 3.10])
def test_realised_offered_load_within_five_percent(tmp_path: Path, rho: float) -> None:
    cal_dir = tmp_path / "cal"
    extract(out_dir=cal_dir, seed=42)
    episode, manifest = generate_episode(
        calibration_dir=cal_dir,
        target_offered_load_ratio=rho,
        duration_s=7200.0,
        tick_s=20.0,
        seed=42,
        out_path=tmp_path / f"ep_{rho}.parquet",
    )
    assert manifest.target_offered_load_ratio == rho
    assert manifest.realised_offered_load_ratio is not None
    err = abs(manifest.realised_offered_load_ratio - rho) / rho
    assert err <= 0.05, (
        f"realised {manifest.realised_offered_load_ratio} vs target {rho} ({err:.2%})"
    )
    assert len(episode) > 0
    assert "arrival_s" in episode.columns
    assert "mean_power_kw" in episode.columns
    assert "duration_s" in episode.columns


def test_s2_fails_loudly_when_ratio_drifts(tmp_path: Path) -> None:
    cal_dir = tmp_path / "cal"
    extract(out_dir=cal_dir, seed=1)
    with pytest.raises(ValueError, match="offered.load"):
        generate_episode(
            calibration_dir=cal_dir,
            target_offered_load_ratio=3.1,
            duration_s=7200.0,
            tick_s=20.0,
            seed=1,
            out_path=tmp_path / "bad.parquet",
            force_arrival_rate=0.01,
        )
