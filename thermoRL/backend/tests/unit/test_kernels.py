import json
from pathlib import Path

import numpy as np

from thermorl2.core.kernels.rc import rc_alpha, rc_step
from thermorl2.core.kernels.thi import t_steady

G = json.loads((Path(__file__).parents[1] / "golden" / "kernel_vectors.json").read_text())


def test_rc_alpha_golden():
    g = G["rc_alpha"]
    assert abs(rc_alpha(60.0, g["dt_s"]) - g["air"]) < 1e-12
    assert abs(rc_alpha(15.0, g["dt_s"]) - g["d2c"]) < 1e-12
    assert abs(rc_alpha(300.0, g["dt_s"]) - g["immersion"]) < 1e-12


def test_rc_step_golden():
    g = G["rc_step_air"]
    out = rc_step(np.array([g["T"]], np.float32), np.array([g["T_ss"]], np.float32),
                  np.array([g["tau_s"]], np.float32), g["dt_s"])
    assert abs(float(out[0]) - g["expected"]) < 1e-5


def test_t_steady_golden():
    g = G["t_steady_air_mid"]
    out = t_steady(np.array([g["Q"]]), np.array([g["Q_max"]]), np.array([g["T_amb"]]), np.array([g["T_max"]]))
    assert abs(float(out[0]) - g["expected"]) < 1e-5
