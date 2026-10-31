import numpy as np
import pytest

from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, rack_kw_to_fmu_inputs, power_input_names

P = CouplingParams(num_cdus=3, racks_per_cdu=1, cooling_efficiency=0.945,
                   temperature_keys=("a_T_Air", "b_T_Air", "simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"),
                   wet_bulb_temp_k=290.0)


def test_power_scaling_and_names():
    out = rack_kw_to_fmu_inputs(np.array([10.0, 0.0, 40.0]), P, Ambient())
    names = power_input_names(P)
    assert names[0] == "simulator_1_datacenter_1_computeBlock_1_cabinet_1_sources_Q_flow_total"
    assert abs(out[names[0]] - 9450.0) < 1e-9 and out[names[1]] == 0.0 and abs(out[names[2]] - 37800.0) < 1e-9


def test_temperature_keys_default_290():
    out = rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient())
    assert out["a_T_Air"] == 290.0 and out["simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"] == 290.0
    assert len(out) == 6


def test_ambient_override_splits_air_and_ext():
    out = rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient(t_air_k=295.0, t_ext_k=288.0))
    assert out["a_T_Air"] == 295.0 and out["simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"] == 288.0


def test_per_unit_air_temperature_maps_by_index():
    keys = tuple(f"simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_T_Air" for i in range(1, 45))
    ext = "simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"
    p = CouplingParams(44, 1, 0.945, keys + (ext,), 290.0)
    out = rack_kw_to_fmu_inputs(np.full(44, 10.86), p, Ambient(t_ext_k=288.0, t_air_k_by_unit=tuple(290.0 + i for i in range(44))))
    assert out[keys[33]] == 323.0
    assert out[keys[0]] == 290.0 and out[keys[-1]] == 333.0
    assert out[ext] == 288.0


def test_default_ambient_unchanged():
    assert rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient()) == rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient(t_air_k_by_unit=None))


def test_per_unit_air_temperature_length_mismatch():
    with pytest.raises(ValueError):
        rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient(t_air_k_by_unit=(290.0, 291.0)))


def test_per_unit_air_temperature_missing_input_key_raises():
    keys = tuple(f"simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_T_Air" for i in (1, 2))
    params = CouplingParams(3, 1, 0.945, keys, 290.0)
    with pytest.raises(KeyError):
        rack_kw_to_fmu_inputs(np.zeros(3), params, Ambient(t_air_k_by_unit=(290.0, 291.0, 292.0)))
