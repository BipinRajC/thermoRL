"""E10 uses one fresh CLI subprocess/FMU per policy run and determinism rerun."""

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

pytestmark = [pytest.mark.fmu, pytest.mark.slow]
PROJECT = Path(__file__).resolve().parents[2]


def test_vertical_slice(tmp_path):
    assert (PROJECT / "thermorl2/experiments/run.py").is_file(), "run CLI not implemented"
    from thermorl2.experiments.run import complete_e10, load_config
    cfg_path = PROJECT / "thermorl2/experiments/configs/smoke_2h.yaml"
    cfg = load_config(cfg_path)
    out = Path(os.environ.get("THERMORL2_E10_ROOT", str(tmp_path / "E10"))).resolve()
    logs = out / "provenance"
    logs.mkdir(parents=True, exist_ok=True)
    paths = {"packing": out / "runs/packing_seed1", "power_balance": out / "runs/power_balance_seed1",
             "packing_rerun": out / "provenance/rerun_1_packing_seed1"}
    actors = []
    try:
        for label, run_dir in paths.items():
            log = logs / f"{label}_console.log"
            handle = log.open("x")
            policy = "power_balance" if label == "power_balance" else "packing"
            command = [sys.executable, "-m", "thermorl2.experiments.run", "--config", str(cfg_path),
                       "--policy", policy, "--seed", "1", "--run-dir", str(run_dir)]
            process = subprocess.Popen(command, cwd=PROJECT, stdout=handle, stderr=subprocess.STDOUT)
            actors.append((process, handle, log))
        pending = list(actors)
        while pending:
            for actor in list(pending):
                process, handle, log = actor
                code = process.poll()
                if code is None:
                    continue
                handle.close()
                assert code == 0, log.read_text()[-12000:]
                pending.remove(actor)
            if pending:
                time.sleep(1)
        result = complete_e10(out, cfg, paths)
        assert result["decision"] == "PASS"
        assert all(result["invariants"].values())
    finally:
        for process, handle, _ in actors:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=30)
            if not handle.closed:
                handle.close()
