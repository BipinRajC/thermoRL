from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from thermorl.contracts.manifest import StageManifest
from thermorl.data.synthetic import generate_calibrated_demand, offered_ratio

FACILITY_MW = 20.0
MAX_REL_ERR = 0.05


def generate_episode(
    calibration_dir: Path,
    target_offered_load_ratio: float,
    duration_s: float,
    tick_s: float,
    seed: int,
    out_path: Path,
    force_arrival_rate: float | None = None,
) -> tuple[pd.DataFrame, StageManifest]:
    cal = json.loads((calibration_dir / "calibration.json").read_text())
    mean_power = float(cal["mean_job_power_kw"])
    mean_dur = float(cal["mean_duration_s"])

    if force_arrival_rate is not None:
        n = max(1, int(force_arrival_rate * duration_s))
        df = generate_calibrated_demand(
            target_offered_load_ratio=target_offered_load_ratio,
            duration_s=duration_s,
            seed=seed,
            mean_power_kw=mean_power,
            mean_duration_s=mean_dur,
        ).head(n)
        realised = offered_ratio(
            force_arrival_rate, float(df["mean_power_kw"].mean()), float(df["duration_s"].mean())
        )
    else:
        df = generate_calibrated_demand(
            target_offered_load_ratio=target_offered_load_ratio,
            duration_s=duration_s,
            seed=seed,
            mean_power_kw=mean_power,
            mean_duration_s=mean_dur,
        )
        arrival_rate = len(df) / duration_s
        realised = offered_ratio(
            arrival_rate, float(df["mean_power_kw"].mean()), float(df["duration_s"].mean())
        )

    rel_err = abs(realised - target_offered_load_ratio) / target_offered_load_ratio
    if rel_err > MAX_REL_ERR:
        raise ValueError(
            f"offered load realised {realised:.4f} vs target {target_offered_load_ratio:.4f} "
            f"(rel err {rel_err:.2%} > 5%)"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    manifest = StageManifest(
        stage="s2",
        inputs=(str(calibration_dir / "calibration.json"),),
        outputs=(str(out_path),),
        target_offered_load_ratio=target_offered_load_ratio,
        realised_offered_load_ratio=realised,
        seed=seed,
    )
    return df, manifest
