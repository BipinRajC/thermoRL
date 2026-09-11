"""M2 gate: same seed produces a byte-identical state trace."""

from __future__ import annotations

import numpy as np

from thermorl.contracts.decision import Placement
from thermorl.sim.capacity import feasible
from thermorl.sim.config import FacilityConfig
from thermorl.sim.engine import step
from thermorl.sim.queue import JobQueue, QueuedJob


def _cfg() -> FacilityConfig:
    return FacilityConfig.from_base_yaml()


def test_capacity_rejects_overfill() -> None:
    cfg = _cfg()
    ok, reason = feasible(
        zone_id=0,
        rack_id=0,
        q_kw=240.0,
        mean_power_kw=20.0,
        density_kw_per_node=4.0,
        cfg=cfg,
    )
    assert ok is False
    assert reason == "capacity"


def test_capacity_rejects_density() -> None:
    cfg = _cfg()
    ok, reason = feasible(
        zone_id=0,
        rack_id=0,
        q_kw=0.0,
        mean_power_kw=20.0,
        density_kw_per_node=30.0,
        cfg=cfg,
    )
    assert ok is False
    assert reason == "density"


def test_capacity_accepts_in_range() -> None:
    cfg = _cfg()
    ok, reason = feasible(
        zone_id=0,
        rack_id=0,
        q_kw=0.0,
        mean_power_kw=31.1,
        density_kw_per_node=4.0,
        cfg=cfg,
    )
    assert ok is True
    assert reason is None


def test_queue_defer_then_force_after_max() -> None:
    q = JobQueue(max_deferrals=3, retry_delay_s=40.0, capacity=8)
    item = QueuedJob(job_id="j1", defer_count=0, next_eligible_s=0.0)
    q.defer(item, now_s=0.0)
    assert q.depth == 1
    assert q.items[0].defer_count == 1
    assert q.items[0].next_eligible_s == 40.0
    q.defer(q.items[0], now_s=40.0)
    q.defer(q.items[0], now_s=80.0)
    forced = q.defer(q.items[0], now_s=120.0)
    assert forced is True
    assert q.items[0].defer_count == 3


def test_same_seed_same_placements_byte_identical_trace() -> None:
    cfg = _cfg()
    placements = (
        Placement(job_id="a", zone_id=0, rack_id=1),
        Placement(job_id="b", zone_id=1, rack_id=2),
    )
    traces = []
    for _ in range(2):
        from thermorl.contracts.state import SimState

        state = SimState.empty(racks_per_zone=cfg.racks_per_zone, seed=42)
        frames = []
        for _tick in range(8):
            state = step(state, placements if _tick == 0 else (), cfg, dt_s=20.0, job_power_kw=31.1)
            frames.append(
                (
                    state.tick,
                    state.sim_time_s,
                    state.rack_T_c.tobytes(),
                    state.rack_Q_kw.tobytes(),
                    state.rack_d.tobytes(),
                    state.zone_pue_eff.tobytes(),
                    state.zone_emergency.tobytes(),
                    state.lambdas.tobytes(),
                )
            )
        traces.append(frames)
    assert traces[0] == traces[1]


def test_clone_then_step_does_not_mutate_parent() -> None:
    from thermorl.contracts.state import SimState

    cfg = _cfg()
    parent = SimState.empty(racks_per_zone=cfg.racks_per_zone, seed=7)
    child = parent.clone()
    child = step(
        child,
        (Placement(job_id="x", zone_id=2, rack_id=0),),
        cfg,
        dt_s=20.0,
        job_power_kw=40.0,
    )
    assert np.array_equal(parent.rack_Q_kw, np.zeros_like(parent.rack_Q_kw))
    assert child.rack_Q_kw[2, 0] > 0
    assert parent.tick == 0
    assert child.tick == 1
