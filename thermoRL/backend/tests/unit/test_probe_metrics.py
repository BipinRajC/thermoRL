import numpy as np

from thermorl2.experiments.probes import branch_statistics, g1_metrics, g3_metrics


def test_branch_statistics_uses_final_window_right_endpoints():
    times = np.array([0, 9000, 9020, 10800])
    temperatures = np.array([[99, 99], [80, 80], [20, 40], [40, 20]])
    result = branch_statistics(times, temperatures, 10800, 1800)
    # The hottest rack changes: mean(max across racks)=40, while
    # max(mean per rack)=30. This pins the preregistered metric definition.
    assert result == {"max_c": 40.0, "mean_c": 30.0, "spread_c": 20.0}


def test_g1_signed_crossing_fit_and_median():
    times = np.array([0, 20, 40, 60])
    branches = {}
    for f in (0, 0.25, 0.5, 0.75, 1):
        final = 20 + 10 * f
        temperatures = np.repeat(np.array([18, 18 + 0.5 * (final - 18), final, final])[:, None], 2, axis=1)
        branches[f"f{f:g}"] = (times, temperatures)
    result = g1_metrics(branches, 10, 30, horizon_s=60, tail_s=20)
    assert abs(result["fit"]["a_c"] - 15) < 1e-10
    assert abs(result["fit"]["b_c_per_kw"] - 0.5) < 1e-10
    assert result["fit"]["r2"] == 1
    assert result["tau_s"] == 40
    assert abs(result["t_hot_c"] - 29) < 1e-10
    assert result["reaches_40c"] is False and result["reaches_45c"] is False


def test_g3_control_subtraction_and_frozen_boundary():
    times = np.array([0, 20, 40])
    control = np.array([[30, 30], [29, 29], [28, 28]])
    intervention = control + np.array([[0, 0], [0.02, 1.0], [0.02, 1.0]])
    result = g3_metrics(times, control, intervention, (1,), True, horizon_s=40, tail_s=40)
    assert result["decision"] == "USABLE"
    assert result["delta_affected_c"] == 1.0
    assert abs(result["delta_unaffected_c"] - 0.02) < 1e-12
    assert g3_metrics(times, control, intervention, (1,), False, horizon_s=40, tail_s=40)["decision"] == "NOT_USABLE"
