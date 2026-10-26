"""Small provenance helpers shared by the FMU-only and closed-loop experiments."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

from thermorl2.raps_adapter.systems import repo_root


def git_state() -> dict:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root(), text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root(), text=True)
    return {"sha": sha, "dirty": bool(status.strip())}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def environment() -> dict:
    return {
        "python": platform.python_version(),
        "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
        "fmpy": importlib.metadata.version("fmpy"),
        "numpy": importlib.metadata.version("numpy"),
        "platform": platform.platform(),
    }


def write_manifest(out_dir: Path, **fields) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "manifest.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite provenance: {path}")
    manifest = {"git": git_state(), "environment": environment(), **fields, "backend": "fmu"}
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return path
