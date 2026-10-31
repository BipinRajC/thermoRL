from math import exp

import numpy as np

from thermorl2.core.scorers import RackContext, ThermalPredictive, make_scorer


def context():
    return RackContext(free_count=np.array([18, 10]), committed_kw=np.array([10.0, 20.0]),
                       t_c=np.array([30.0, 30.0]), job_kw=5.0, job_nodes=4)


def test_thermal_predictive_formula():
    scorer = ThermalPredictive(a_c=20, b_c_per_kw=0.5, tau_s=900)
    score = scorer.score(context())
    expected = -(30 + (20 + 0.5 * 15 - 30) * (1 - exp(-600 / 900)))
    assert abs(score[0] - expected) < 1e-12 and score[0] > score[1]


def test_power_balance_prefers_lowest_committed():
    np.testing.assert_array_equal(make_scorer("power_balance", {}).score(context()), [-10, -20])


def test_make_scorer_names():
    expected = {"packing": [0, -1], "node_balance": [18, 10], "power_balance": [-10, -20], "coolest_rack": [-30, -30]}
    for name, values in expected.items():
        scorer = make_scorer(name, {})
        assert scorer.name == name
        np.testing.assert_array_equal(scorer.score(context()), values)
    params = {"a_c": 20, "b_c_per_kw": 0.5, "tau_s": 900, "horizon_s": 600}
    scorer = make_scorer("thermal_predictive", params)
    assert scorer.name == "thermal_predictive" and scorer.params == params
