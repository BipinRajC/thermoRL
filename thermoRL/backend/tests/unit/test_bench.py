import pytest

from thermorl2.experiments.bench import guard_result


@pytest.mark.parametrize("total,want", [(1200.0, False), (2700.0, False), (2700.01, True)])
def test_d2_guard_uses_unscaled_total_including_initialization(total, want):
    result = guard_result(total, 300.0)
    assert result["switch_required"] is want
    assert result["twice_total_s_information_only"] == 2 * total
    assert result["twice_after_warmup_instantiation_s_information_only"] == 2 * (total - 300)


def test_horizon_rule_remains_four_times_total_at_most_300():
    assert guard_result(75.0, 10.0)["horizon_h"] == 12
    assert guard_result(75.01, 10.0)["horizon_h"] == 6
