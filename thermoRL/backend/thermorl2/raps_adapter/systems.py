"""SHA-pinned POWER9 systems from the 2026-10-27 design spec §3.1."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SystemSpec:
    name: str
    fmu_path: Path
    fmu_sha256: str
    grid: tuple[int, int]
    whatif_racks: tuple[int, ...]


SYSTEMS = {
    "lassen": SystemSpec("lassen", Path("models/POWER9CSM/fmus/lassen.fmu"), "2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b", (4, 11), tuple(range(33, 44))),
    "summit": SystemSpec("summit", Path("models/POWER9CSM/fmus/summit.fmu"), "0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233", (13, 20), tuple(range(192, 257))),
    "marconi100": SystemSpec("marconi100", Path("models/POWER9CSM/fmus/marconi100.fmu"), "9dac7818338d0be7fcb887ee88acab01a62eeb7aff4bd286e65874e0ef5c3f77", (7, 7), tuple(range(36, 49))),
}


def get_system(name: str) -> SystemSpec:
    return SYSTEMS[name]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
