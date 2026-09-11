"""PM100 power calibration.

node_power_consumption is a TOTAL across allocated nodes, not per-node.
    power_kw = mean(node_power_consumption) / 1000.0
Never multiply by num_nodes_alloc.
time_limit is minutes; convert with minutes_to_seconds.
"""

from __future__ import annotations

import json
from pathlib import Path

PAPER_MEAN_POWER_KW = 31.1
PAPER_MEAN_DURATION_S = 1998.0


def default_power_model() -> dict[str, float | str]:
    return {
        "source": "pm100",
        "unit_rule": "node_power_consumption is TOTAL watts; divide by 1000; do not * nodes",
        "mean_power_kw": PAPER_MEAN_POWER_KW,
        "mean_duration_s": PAPER_MEAN_DURATION_S,
        "time_limit_unit": "minutes",
    }


def write_power_model(path: Path) -> Path:
    path.write_text(json.dumps(default_power_model(), indent=2) + "\n")
    return path
