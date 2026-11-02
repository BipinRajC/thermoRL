from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RackGeometry:
    num_cdus: int
    racks_per_cdu: int
    nodes_per_rack: int

    @property
    def n_racks(self) -> int:
        return self.num_cdus * self.racks_per_cdu

    @property
    def total_nodes(self) -> int:
        return self.n_racks * self.nodes_per_rack

    def rack_of(self, node_id: int) -> int:
        return node_id // self.nodes_per_rack

    def nodes_of(self, rack: int) -> range:
        lo = rack * self.nodes_per_rack
        return range(lo, lo + self.nodes_per_rack)

    def free_per_rack(self, available_nodes: Iterable[int]) -> np.ndarray:
        node_ids = np.asarray(list(available_nodes), dtype=np.int64)
        return np.bincount(node_ids // self.nodes_per_rack, minlength=self.n_racks)

    def free_nodes_in_rack(self, rack: int, available_nodes: Iterable[int], k: int) -> list[int]:
        lo = rack * self.nodes_per_rack
        hi = lo + self.nodes_per_rack
        return sorted(n for n in available_nodes if lo <= n < hi)[:k]

    @classmethod
    def from_legacy_config(cls, cfg: dict) -> RackGeometry:
        return cls(
            num_cdus=cfg["NUM_CDUS"],
            racks_per_cdu=cfg["RACKS_PER_CDU"],
            nodes_per_rack=cfg["NODES_PER_RACK"],
        )
