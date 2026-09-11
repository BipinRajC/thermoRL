from __future__ import annotations

import numpy as np

from thermorl.sim.config import FacilityConfig


def update_emergency(
    thi_z: np.ndarray,
    emergency: np.ndarray,
    on_since_s: np.ndarray,
    now_s: float,
    cfg: FacilityConfig,
) -> tuple[np.ndarray, np.ndarray, int]:
    nxt = emergency.copy()
    since = on_since_s.copy()
    new_events = 0
    for z in range(thi_z.shape[0]):
        if (not nxt[z]) and thi_z[z] < cfg.eps_emergency:
            nxt[z] = True
            since[z] = now_s
            new_events += 1
        elif nxt[z]:
            held = (now_s - since[z]) >= cfg.emergency_min_duration_s
            if held and thi_z[z] > cfg.eps_release:
                nxt[z] = False
                since[z] = -1.0
    return nxt, since, new_events
