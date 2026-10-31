import numpy as np

from thermorl2.core.constraints import thi_headroom, thi_paper_raw, hinge, violation, compute_thi


def test_headroom_is_one_at_idle_zero_power():
    out = thi_headroom(np.array([30.0]), np.array([30.0]), 45.0, np.array([0.0]), 36.0)
    assert out[0] == 1.0


def test_headroom_is_zero_at_limit():
    out = thi_headroom(np.array([45.0]), np.array([30.0]), 45.0, np.array([0.0]), 36.0)
    assert abs(out[0]) < 1e-9


def test_power_term_dominates_paper_example():
    # paper: Q/Qmax = 0.95 -> THI = 0.05 when temperature term is smaller
    out = thi_paper_raw(np.array([20.0]), 45.0, np.array([34.2]), 36.0)
    assert abs(out[0] - 0.05) < 1e-9


def test_clip_to_minus_half_one():
    out = thi_headroom(np.array([80.0]), np.array([30.0]), 45.0, np.array([0.0]), 36.0)
    assert out[0] == -0.5


def test_hinge_and_violation():
    thi = np.array([0.5, 0.10, 0.05, -0.2])
    np.testing.assert_allclose(hinge(thi, 0.10), [0.0, 0.0, 0.05, 0.30])
    assert violation(thi, 0.10).tolist() == [False, False, True, True]


def test_dispatcher():
    a = compute_thi("headroom", t_c=np.array([37.5]), t_idle_c=np.array([30.0]), t_max_c=45.0,
                    p_kw=np.array([18.0]), p_max_kw=36.0)
    assert abs(a[0] - 0.5) < 1e-9
