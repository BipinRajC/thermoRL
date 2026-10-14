import time

import numpy as np
import pytest

from raps.system_config import get_system_config
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.thermal.fmu_backend import FmuBackend

pytestmark = pytest.mark.fmu


@pytest.fixture(scope="module")
def backend(fmu_path):
    cp = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    b = FmuBackend(fmu_path, cp)
    yield b
    b.close()


def test_warm_up_settles_and_observe_shapes(backend):
    used = backend.warm_up(np.full(44, 10.86), Ambient(), dt_s=20.0, max_s=7200.0)
    assert 600.0 <= used <= 7200.0
    th = backend.observe()
    assert th.t_c.shape == (44,) and 15.0 < th.t_c.min() and th.t_c.max() < 45.0
    assert set(th.extras) >= {"T_sec_r_C", "T_sec_s_C", "W_flow_CDUP_kW"}
    g = backend.global_observe()
    assert "fmu.T_prim_supply_C" in g and 5.0 < g["fmu.T_prim_supply_C"] < 40.0


def test_reset_reproduces_trajectory(backend):
    backend.reset()
    p = np.full(44, 10.86); p[0] = 35.0
    a = [backend.step(p, 20.0, Ambient()) or backend.observe().t_c.copy() for _ in range(30)]
    backend.reset()
    b = [backend.step(p, 20.0, Ambient()) or backend.observe().t_c.copy() for _ in range(30)]
    np.testing.assert_allclose(np.array(a), np.array(b), atol=1e-9)


def test_single_rack_step_is_local_and_matches_probe(backend):
    backend.reset()
    idle = backend.observe().t_c.copy()
    p = np.full(44, 10.0); p[0] = 40.0
    t = []
    for _ in range(int(3600 / 20)):
        backend.step(p, 20.0, Ambient()); t.append(backend.observe().t_c.copy())
    t = np.array(t)
    rise0 = t[-1, 0] - idle[0]
    assert rise0 > 4.0  # probe: +5.8 degC after 10->40 kW
    frac = (t[:, 0] - idle[0]) / rise0
    t63 = 20.0 * int(np.argmax(frac >= 0.632))
    assert 500.0 <= t63 <= 1000.0  # probe: ~750 s, tolerance 20-33 %
    assert abs(t[-1, 1] - idle[1]) < 0.5 and abs(t[-1, 43] - idle[43]) < 0.5


def test_second_instance_in_process_is_refused(backend, fmu_path):
    cp = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    with pytest.raises(RuntimeError):
        FmuBackend(fmu_path, cp)
