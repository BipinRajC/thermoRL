import pytest

from thermorl2.experiments.select_fmu import classify_delta, select_primary


def row(system, delta, cost, classification="GO", sane=True):
    return {"system": system, "delta_max_c": delta, "projected_closed_loop_min_6h": cost, "class": classification, "sane": sane}


def test_highest_delta_wins():
    result = select_primary([row("lassen", 3, 2), row("summit", 2, 1)])
    assert result["primary"] == "lassen" and result["runner_up"] == "summit"
    assert result["tie_break_applied"] is False


def test_cost_above_30_is_ineligible():
    result = select_primary([row("lassen", 2.2, 30), row("summit", 4, 30.01)])
    assert result["primary"] == "lassen"
    assert result["eligible"] == ["lassen"]


def test_tie_break_prefers_lower_cost_in_same_class():
    result = select_primary([row("lassen", 2.5, 5), row("summit", 2.2, 1)])
    assert result["primary"] == "summit"
    assert result["ranking"] == ["summit", "lassen"]
    assert result["tie_break_applied"] is True


def test_tie_boundary_inclusive():
    assert select_primary([row("a", 2.5, 5), row("b", 2.0, 1)])["primary"] == "b"


def test_different_class_does_not_tie():
    assert select_primary([row("a", 2.1, 5), row("b", 1.9, 1, "WEAK")])["primary"] == "a"


def test_all_stop_remains_stop():
    result = select_primary([row("a", 0.5, 1, "STOP"), row("b", 0.7, 2, "STOP")])
    assert result["class"] == "STOP"


def test_insane_system_excluded():
    result = select_primary([row("a", 4, 1, sane=False), row("b", 2.5, 2)])
    assert result["primary"] == "b" and "a" not in result["eligible"]


def test_no_eligible_system_stops():
    result = select_primary([row("a", 4, 31)])
    assert result["primary"] is None and result["class"] == "STOP"


def test_negative_contrast_still_selects_stop_candidate():
    result = select_primary([row("a", -0.5, 1, "STOP"), row("b", -1.0, 2, "STOP")])
    assert result["primary"] == "a" and result["class"] == "STOP"


@pytest.mark.parametrize("delta,want", [(0.9999, "STOP"), (1.0, "WEAK"), (1.9999, "WEAK"), (2.0, "GO")])
def test_frozen_class_boundaries(delta, want):
    assert classify_delta(delta) == want
