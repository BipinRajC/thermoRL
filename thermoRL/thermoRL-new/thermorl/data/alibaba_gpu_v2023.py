from __future__ import annotations

from pathlib import Path


class AlibabaGpuV2023:
    name = "alibaba_gpu_v2023"

    def __init__(self, csv_dir: Path | None = None) -> None:
        self.csv_dir = csv_dir
