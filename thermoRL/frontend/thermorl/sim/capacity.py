from __future__ import annotations

from thermorl.sim.config import FacilityConfig


def feasible(
    zone_id: int,
    rack_id: int,
    q_kw: float,
    mean_power_kw: float,
    density_kw_per_node: float,
    cfg: FacilityConfig,
) -> tuple[bool, str | None]:
    q_max = float(cfg.q_max_rack_kw[zone_id])
    if q_kw + mean_power_kw > q_max:
        return False, "capacity"
    lo = float(cfg.density_min[zone_id])
    hi = float(cfg.density_max[zone_id])
    if density_kw_per_node < lo or density_kw_per_node > hi:
        return False, "density"
    return True, None
