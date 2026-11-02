from math import ceil

import pytest

from thermorl2.experiments.provenance import sha256_file
from thermorl2.raps_adapter.systems import get_system, repo_root


@pytest.mark.parametrize("name,n", [("lassen", 44), ("summit", 257), ("marconi100", 49)])
def test_systems_registry(name, n):
    system = get_system(name)
    assert system.name == name
    assert len(system.whatif_racks) == ceil(n / 4)
    assert system.whatif_racks[-1] == n - 1
    assert system.grid[0] * system.grid[1] >= n
    assert sha256_file(repo_root() / system.fmu_path) == system.fmu_sha256
