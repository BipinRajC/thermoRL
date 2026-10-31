import numpy as np
import pytest

from thermorl2.experiments.probes import packed_vector, scientific_summary, uniform_vector


def test_packed_vector_preserves_total_and_bounds():
    idle, peak = 10.0, 30.0
    total = 3.5 * peak + 40.5 * idle
    vector = packed_vector(44, idle, peak, total)
    np.testing.assert_array_equal(vector[:4], [30.0, 30.0, 30.0, 20.0])
    np.testing.assert_array_equal(vector[4:], [10.0] * 40)
    assert abs(vector.sum() - total) < 1e-9
    assert np.all((vector >= idle) & (vector <= peak))


@pytest.mark.parametrize("n,idle,peak", [(44, 10.85768, 34.42868), (257, 13.201714285714285, 47.282326530612245), (49, 12.3652, 38.5552)])
def test_real_system_vectors(n, idle, peak):
    spread = uniform_vector(n, idle, peak, 0.6)
    packed = packed_vector(n, idle, peak, float(spread.sum()))
    assert abs(packed.sum() - spread.sum()) < 1e-9
    assert np.all((packed >= idle) & (packed <= peak))


def test_uniform_endpoints():
    np.testing.assert_array_equal(uniform_vector(3, 10, 30, 0), [10, 10, 10])
    np.testing.assert_array_equal(uniform_vector(3, 10, 30, 1), [30, 30, 30])


@pytest.mark.parametrize("total", [29.0, 91.0])
def test_packed_vector_rejects_impossible_total(total):
    with pytest.raises(ValueError):
        packed_vector(3, 10, 30, total)


def test_scientific_summary_excludes_only_approved_timing_keys():
    original = {"delta_max_c": 2.1, "fmu_s_per_sim_h": 1.0, "projected_closed_loop_min_6h": 0.15, "sane": True}
    rerun = {**original, "fmu_s_per_sim_h": 1.2, "projected_closed_loop_min_6h": 0.18}
    assert scientific_summary(original) == scientific_summary(rerun) == {"delta_max_c": 2.1, "sane": True}
    assert scientific_summary({**rerun, "delta_max_c": 2.2}) != scientific_summary(original)
