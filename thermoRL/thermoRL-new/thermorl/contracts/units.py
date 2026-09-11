"""Declared unit newtypes. Power is kW inside the simulator. Time is seconds.

Any function that accepts watts or minutes must say so in its name.
PM100 `node_power_consumption` is a TOTAL across allocated nodes — never
multiply by `num_nodes_alloc`. PM100 `time_limit` is minutes.
"""

from __future__ import annotations

from typing import NewType

KW = NewType("KW", float)
Watts = NewType("Watts", float)
Seconds = NewType("Seconds", float)
Minutes = NewType("Minutes", float)


def watts_to_kw(power_w: Watts) -> KW:
    return KW(float(power_w) / 1000.0)


def minutes_to_seconds(duration_min: Minutes) -> Seconds:
    return Seconds(float(duration_min) * 60.0)
