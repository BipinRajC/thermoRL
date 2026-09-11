"""Hand-computed golden vectors for Phase 1 thermal kernels."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from thermorl.sim.kernels.degradation import arrhenius, degradation_step
from thermorl.sim.kernels.heat import heat_inject, heat_release
from thermorl.sim.kernels.pue import pue_effective
from thermorl.sim.kernels.rc import rc_alpha, rc_step
from thermorl.sim.kernels.thi import t_steady, thi_batch, thi_zone

GOLDEN = Path(__file__).resolve().parent / "golden" / "kernel_vectors.json"


def test_t_steady_mid_load_air() -> None:
    # T_ss = 18 + (2000/4000)*(27-18) = 22.5
    got = t_steady(
        Q=np.array([[2000.0]], dtype=np.float32),
        Q_max=np.array([[4000.0]], dtype=np.float32),
        T_amb=np.array([[18.0]], dtype=np.float32),
        T_max=np.array([[27.0]], dtype=np.float32),
    )
    assert got[0, 0] == pytest.approx(22.5, abs=1e-6)


def test_t_steady_zero_and_full_load() -> None:
    Q = np.array([[0.0, 4000.0]], dtype=np.float32)
    Q_max = np.array([[4000.0, 4000.0]], dtype=np.float32)
    T_amb = np.array([[18.0, 18.0]], dtype=np.float32)
    T_max = np.array([[27.0, 27.0]], dtype=np.float32)
    got = t_steady(Q, Q_max, T_amb, T_max)
    assert got[0, 0] == pytest.approx(18.0, abs=1e-6)
    assert got[0, 1] == pytest.approx(27.0, abs=1e-6)


def test_thi_temperature_term_dominates() -> None:
    # T/T_max = 24/27 = 8/9; T_ss/T_max = 22.5/27 = 5/6; d = 0.11
    # THI = 1 - 8/9 = 1/9
    T = np.array([[24.0]], dtype=np.float32)
    T_ss = np.array([[22.5]], dtype=np.float32)
    d = np.array([[0.11]], dtype=np.float32)
    T_max = np.array([[27.0]], dtype=np.float32)
    d_max = np.array([[1.0]], dtype=np.float32)
    got = thi_batch(T, T_ss, d, T_max, d_max)
    assert got[0, 0] == pytest.approx(1.0 / 9.0, abs=1e-6)


def test_thi_t_ss_replaces_q_over_qmax() -> None:
    # Q/Q_max = 0.95 would dominate paper form (THI=0.05).
    # T_ss = 18 + 0.95*(27-18) = 26.55; T_ss/T_max = 26.55/27
    # THI_phase1 = 1 - 26.55/27 = 0.016666...
    T = np.array([[20.0]], dtype=np.float32)
    T_ss = np.array([[26.55]], dtype=np.float32)
    d = np.array([[0.05]], dtype=np.float32)
    T_max = np.array([[27.0]], dtype=np.float32)
    d_max = np.array([[1.0]], dtype=np.float32)
    got = thi_batch(T, T_ss, d, T_max, d_max)
    assert got[0, 0] == pytest.approx(1.0 - 26.55 / 27.0, abs=1e-6)


def test_thi_zone_is_min_over_racks() -> None:
    thi = np.array([[0.40, 0.21, 0.33]], dtype=np.float32)
    assert thi_zone(thi)[0] == pytest.approx(0.21, abs=1e-6)


def test_rc_alpha_matches_spec_percentages() -> None:
    # Δt=20: air 28%, D2C 74%, immersion 6.5%
    assert rc_alpha(tau_s=60.0, dt_s=20.0) == pytest.approx(0.2834686894262107, rel=1e-12)
    assert rc_alpha(tau_s=15.0, dt_s=20.0) == pytest.approx(0.7364028618842733, rel=1e-12)
    assert rc_alpha(tau_s=300.0, dt_s=20.0) == pytest.approx(0.06449301496838222, rel=1e-12)


def test_rc_step_air_one_tick() -> None:
    # T' = 20 + (1-e^{-20/60})*(22.5-20) = 20.708671723565527
    T = np.array([[20.0]], dtype=np.float32)
    T_ss = np.array([[22.5]], dtype=np.float32)
    tau = np.array([[60.0]], dtype=np.float32)
    got = rc_step(T, T_ss, tau, dt_s=20.0)
    assert float(got[0, 0]) == pytest.approx(20.708671723565527, rel=1e-6)


def test_pue_below_theta_is_base() -> None:
    T = np.array([20.0], dtype=np.float32)
    T_amb = np.array([18.0], dtype=np.float32)
    T_max = np.array([27.0], dtype=np.float32)
    pue_base = np.array([1.45], dtype=np.float32)
    k_z = np.array([0.35], dtype=np.float32)
    got = pue_effective(T, T_amb, T_max, pue_base, k_z, theta=0.70, p=2.0)
    assert got[0] == pytest.approx(1.45, abs=1e-6)


def test_pue_above_theta_quadratic() -> None:
    # s = (25-18)/(27-18) = 7/9
    # PUE = 1.45 + 0.35 * (7/9 - 0.7)^2 = 1.4521172839506173
    T = np.array([25.0], dtype=np.float32)
    T_amb = np.array([18.0], dtype=np.float32)
    T_max = np.array([27.0], dtype=np.float32)
    pue_base = np.array([1.45], dtype=np.float32)
    k_z = np.array([0.35], dtype=np.float32)
    got = pue_effective(T, T_amb, T_max, pue_base, k_z, theta=0.70, p=2.0)
    assert got[0] == pytest.approx(1.4521172839506173, rel=1e-6)


def test_arrhenius_is_one_at_t_ref() -> None:
    assert arrhenius(t_c=40.0, ea_ev=0.7, t_ref_c=40.0) == pytest.approx(1.0, abs=1e-12)


def test_degradation_accrues_above_stress_threshold() -> None:
    # s = (26-18)/(27-18) = 8/9 > 0.85
    # excess = 8/9 - 0.85
    # arrhenius(26)/arrhenius(40) < 1; d' = 0 + rate * excess * arr * dt
    d = np.array([[0.0]], dtype=np.float32)
    T = np.array([[26.0]], dtype=np.float32)
    T_amb = np.array([[18.0]], dtype=np.float32)
    T_max = np.array([[27.0]], dtype=np.float32)
    rate = np.array([[0.0008]], dtype=np.float32)
    recovery = np.array([[0.0015]], dtype=np.float32)
    got = degradation_step(d, T, T_amb, T_max, rate, recovery, dt_s=20.0)
    excess = (8.0 / 9.0) - 0.85
    expected = 0.0008 * excess * arrhenius(26.0) * 20.0
    assert float(got[0, 0]) == pytest.approx(expected, rel=1e-5)
    assert 0.0 < float(got[0, 0]) < 1.0


def test_degradation_recovers_below_threshold() -> None:
    d = np.array([[0.10]], dtype=np.float32)
    T = np.array([[20.0]], dtype=np.float32)
    T_amb = np.array([[18.0]], dtype=np.float32)
    T_max = np.array([[27.0]], dtype=np.float32)
    rate = np.array([[0.0008]], dtype=np.float32)
    recovery = np.array([[0.0015]], dtype=np.float32)
    got = degradation_step(d, T, T_amb, T_max, rate, recovery, dt_s=20.0)
    assert float(got[0, 0]) == pytest.approx(0.10 - 0.0015 * 20.0, abs=1e-6)


def test_degradation_clips_to_unit_interval() -> None:
    d = np.array([[0.001]], dtype=np.float32)
    T = np.array([[20.0]], dtype=np.float32)
    T_amb = np.array([[18.0]], dtype=np.float32)
    T_max = np.array([[27.0]], dtype=np.float32)
    rate = np.array([[0.0008]], dtype=np.float32)
    recovery = np.array([[0.0015]], dtype=np.float32)
    got = degradation_step(d, T, T_amb, T_max, rate, recovery, dt_s=20.0)
    assert float(got[0, 0]) == pytest.approx(0.0, abs=1e-6)


def test_heat_inject_and_release() -> None:
    Q = np.zeros((3, 16), dtype=np.float32)
    Q2 = heat_inject(Q, zone_id=0, rack_id=3, power_kw=31.1)
    assert Q2[0, 3] == pytest.approx(31.1, abs=1e-6)
    assert Q[0, 3] == pytest.approx(0.0, abs=1e-6)
    Q3 = heat_release(Q2, zone_id=0, rack_id=3, power_kw=31.1)
    assert Q3[0, 3] == pytest.approx(0.0, abs=1e-6)


def test_golden_file_matches_hand_computed() -> None:
    data = json.loads(GOLDEN.read_text())
    assert data["t_steady_air_mid"]["expected"] == 22.5
    assert data["thi_temp_dominates"]["expected"] == pytest.approx(1.0 / 9.0)
    assert data["rc_alpha"]["air"] == pytest.approx(0.2834686894262107)
    T = t_steady(
        Q=np.array([[data["t_steady_air_mid"]["Q"]]], dtype=np.float32),
        Q_max=np.array([[data["t_steady_air_mid"]["Q_max"]]], dtype=np.float32),
        T_amb=np.array([[data["t_steady_air_mid"]["T_amb"]]], dtype=np.float32),
        T_max=np.array([[data["t_steady_air_mid"]["T_max"]]], dtype=np.float32),
    )
    assert float(T[0, 0]) == pytest.approx(data["t_steady_air_mid"]["expected"], abs=1e-6)
