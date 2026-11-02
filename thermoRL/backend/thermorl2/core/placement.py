"""Deterministic placement on the free-node snapshot supplied by the adapter."""

import numpy as np

from thermorl2.core.state import Placement


def place(scores: np.ndarray, free_nodes_by_rack: list[list[int]], n: int) -> Placement:
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1 or len(scores) != len(free_nodes_by_rack) or not np.isfinite(scores).all():
        raise ValueError("one finite score is required per rack")
    available = [node for rack in free_nodes_by_rack for node in rack]
    if n < 1 or len(available) < n or len(set(available)) != len(available):
        raise ValueError("placement requires enough distinct free nodes")
    order = np.lexsort((np.arange(len(scores)), -scores))
    for rack in order:
        if len(free_nodes_by_rack[rack]) >= n:
            return Placement((int(rack),), tuple(sorted(free_nodes_by_rack[rack])[:n]), "single")
    racks, nodes = [], []
    for rack in order:
        take = sorted(free_nodes_by_rack[rack])[:n - len(nodes)]
        if take:
            racks.append(int(rack))
            nodes.extend(take)
        if len(nodes) == n:
            break
    return Placement(tuple(racks), tuple(nodes), "span")
