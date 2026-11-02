import numpy as np
import pytest

from thermorl2.core.placement import place


def test_single_rack_preferred():
    result = place(np.array([10.0, 9.0, 1.0]), [[0], [3, 1, 2], [4, 5, 6]], 3)
    assert result.racks == (1,) and result.nodes == (1, 2, 3) and result.rule == "single"


def test_span_in_score_order():
    free = [list(range(18)), list(range(18, 28)), list(range(36, 54))]
    result = place(np.array([2.0, 3.0, 1.0]), free, 30)
    assert result.racks == (1, 0, 2) and result.rule == "span"
    assert result.nodes == tuple(list(range(18, 28)) + list(range(18)) + [36, 37])
    assert len(set(result.nodes)) == 30


def test_ties_break_to_lower_index():
    result = place(np.array([1.0, 1.0]), [[2, 0, 1], [5, 3, 4]], 2)
    assert result.racks == (0,) and result.nodes == (0, 1)


def test_insufficient_raises():
    with pytest.raises(ValueError):
        place(np.array([1.0, 2.0]), [[0], [1]], 3)


def test_random_fragmentation_allocates_exact_distinct_free_nodes():
    rng = np.random.default_rng(1)
    for _ in range(100):
        free = [[rack * 18 + node for node in range(18) if rng.random() < 0.7] for rack in range(8)]
        available = set(node for nodes in free for node in nodes)
        n = int(rng.integers(1, len(available) + 1))
        result = place(rng.normal(size=8), free, n)
        assert len(result.nodes) == len(set(result.nodes)) == n
        assert set(result.nodes) <= available
