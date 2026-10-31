from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]  # /home/bipin/thermoRL
FMU_PATH = REPO_ROOT / "models" / "POWER9CSM" / "fmus" / "lassen.fmu"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def fmu_path() -> Path:
    if not FMU_PATH.exists():
        pytest.skip(f"FMU not found at {FMU_PATH}")
    return FMU_PATH
