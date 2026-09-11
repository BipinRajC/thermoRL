from __future__ import annotations

import json
from pathlib import Path

from thermorl.data.pm100_calibrator import (
    PAPER_MEAN_DURATION_S,
    PAPER_MEAN_POWER_KW,
    write_power_model,
)


def extract(out_dir: Path, seed: int) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    power_path = write_power_model(out_dir / "power_model.json")
    calibration = {
        "workload_source": "alibaba_gpu_v2023",
        "power_calibration_source": "pm100",
        "facility_capacity_kw": 20000.0,
        "mean_job_power_kw": PAPER_MEAN_POWER_KW,
        "mean_duration_s": PAPER_MEAN_DURATION_S,
        "seed": seed,
        "arrival_process": "poisson_with_diurnal_multiplier",
        "scaling_method": "explicit_rate_calibration",
    }
    cal_path = out_dir / "calibration.json"
    cal_path.write_text(json.dumps(calibration, indent=2) + "\n")
    return {"calibration": cal_path, "power_model": power_path}
