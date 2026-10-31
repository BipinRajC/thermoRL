import json
import subprocess
import sys

import pytest

pytestmark = pytest.mark.fmu


@pytest.mark.parametrize("system,n", [("lassen", 44), ("summit", 257), ("marconi100", 49)])
def test_fmu_smoke_all_systems(system, n):
    result = subprocess.run([sys.executable, "-m", "thermorl2.experiments.fmu_smoke", "--system", system], capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    print(json.dumps(report, sort_keys=True))
    assert report["system"] == system and report["n_units"] == n
    assert report["finite"] is True
