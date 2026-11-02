"""C7 unit-boundary tests. Power is kW inside the simulator; time is seconds."""

from __future__ import annotations

import pytest

from thermorl.contracts.units import (
    KW,
    Minutes,
    Seconds,
    Watts,
    minutes_to_seconds,
    watts_to_kw,
)


def test_watts_to_kw_divides_by_one_thousand() -> None:
    assert watts_to_kw(Watts(1000.0)) == KW(1.0)
    assert watts_to_kw(Watts(31100.0)) == KW(31.1)


def test_pm100_node_power_is_total_not_per_node() -> None:
    """PM100 node_power_consumption is a TOTAL across allocated nodes.

    power_kw = mean(node_power_consumption) / 1000.0
    Multiplying by num_nodes_alloc inflates power by up to 256x.
    """
    node_power_consumption_w = Watts(12400.0)
    num_nodes_alloc = 8
    power_kw = watts_to_kw(node_power_consumption_w)
    assert power_kw == KW(12.4)
    inflated = float(power_kw) * num_nodes_alloc
    assert inflated == pytest.approx(99.2)
    assert float(power_kw) != pytest.approx(inflated)


def test_minutes_to_seconds_multiplies_by_sixty() -> None:
    """PM100 time_limit is minutes. Everything else time-like is seconds."""
    assert minutes_to_seconds(Minutes(1.0)) == Seconds(60.0)
    assert minutes_to_seconds(Minutes(30.0)) == Seconds(1800.0)


def test_conversion_function_names_declare_units() -> None:
    assert watts_to_kw.__name__ == "watts_to_kw"
    assert minutes_to_seconds.__name__ == "minutes_to_seconds"


def test_no_nodes_scale_helper_in_units() -> None:
    import thermorl.contracts.units as units_mod

    forbidden = (
        "power_times_nodes",
        "scale_power_by_nodes",
        "per_node_watts_to_kw",
        "total_power_from_per_node",
    )
    for name in forbidden:
        assert not hasattr(units_mod, name)
