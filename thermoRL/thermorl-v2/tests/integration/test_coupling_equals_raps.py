import numpy as np
import pytest

from raps.system_config import get_system_config
from raps.cooling import ThermoFluidsModel
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, rack_kw_to_fmu_inputs

pytestmark = pytest.mark.integration


def test_adapter_inputs_equal_raps_generate_runtime_values():
    legacy = get_system_config("lassen").get_legacy()
    tfm = ThermoFluidsModel(**legacy)  # no initialize(): no FMU needed
    rng = np.random.default_rng(1)
    rack_kw = rng.uniform(5.0, 36.0, size=legacy["NUM_CDUS"])
    raps_inputs = tfm.generate_runtime_values(rack_kw * 1000.0, engine=None)  # RAPS: cdu_power in W
    ours = rack_kw_to_fmu_inputs(rack_kw, CouplingParams.from_legacy_config(legacy), Ambient())
    assert set(ours) == set(raps_inputs)
    for k in raps_inputs:
        assert ours[k] == pytest.approx(raps_inputs[k], rel=0, abs=1e-9), k
