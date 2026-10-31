import numpy as np

from thermorl2.raps_adapter.rack_geometry import RackGeometry


def geo():
    return RackGeometry(num_cdus=44, racks_per_cdu=1, nodes_per_rack=18)


def test_rack_of_and_nodes_of():
    g = geo()
    assert g.n_racks == 44 and g.total_nodes == 792
    assert g.rack_of(0) == 0 and g.rack_of(17) == 0 and g.rack_of(18) == 1 and g.rack_of(791) == 43
    assert list(g.nodes_of(43)) == list(range(774, 792))


def test_free_per_rack_and_lowest_free():
    g = geo()
    avail = [0, 1, 5, 18, 19, 791]
    counts = g.free_per_rack(avail)
    assert counts[0] == 3 and counts[1] == 2 and counts[43] == 1 and counts.sum() == 6
    assert g.free_nodes_in_rack(0, avail, 2) == [0, 1]
    assert g.free_nodes_in_rack(1, avail, 5) == [18, 19]  # fewer than k available -> returns what exists


def test_from_legacy_config():
    g = RackGeometry.from_legacy_config({"NUM_CDUS": 44, "RACKS_PER_CDU": 1, "NODES_PER_RACK": 18})
    assert g.n_racks == 44
