import pytest

from thermorl2.raps_adapter.power_model import job_increment_kw, legacy_config, node_power_kw, rack_power_bounds

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("system", ["lassen", "summit", "marconi100"])
def test_rack_power_bounds_all_systems(system):
    cfg = legacy_config(system)
    idle, peak = rack_power_bounds(cfg)
    print(f"{system}: idle={idle:.9f} kW, peak={peak:.9f} kW")
    assert idle < peak
    # Summit models switch power as zero; rack overhead need not be positive.
    assert cfg["NODES_PER_RACK"] * node_power_kw(cfg, 0, 0) <= idle


@pytest.mark.parametrize("system", ["lassen", "summit", "marconi100"])
def test_job_increment_zero_at_idle(system):
    cfg = legacy_config(system)
    assert job_increment_kw(cfg, 0, 0, 18) == 0.0
    assert job_increment_kw(cfg, 2, 1, 4) > 0
