"""Scheduler contract tests without an engine, time loop, or FMU (D2 isolation)."""

from types import SimpleNamespace

import numpy as np
from raps.policy import PolicyType

from thermorl2.core.scorers import make_scorer
from thermorl2.raps_adapter.power_model import legacy_config
from thermorl2.raps_adapter.rack_geometry import RackGeometry
from thermorl2.raps_adapter.scheduler import PlacementScheduler, ThermalView


class AllocationPort:
    """Minimal allocation boundary; real RAPS integration runs after the bench."""

    def __init__(self, nodes):
        self.available_nodes = list(nodes)
        self.calls = []

    def assign_nodes_to_job(self, job, current_time, policy):
        self.calls.append((job.id, current_time, policy, tuple(job.scheduled_nodes)))
        assert policy == PolicyType.REPLAY
        assert set(job.scheduled_nodes) <= set(self.available_nodes)
        self.available_nodes = [node for node in self.available_nodes if node not in job.scheduled_nodes]
        job.start_time = current_time


def setup(policy="power_balance"):
    manager = AllocationPort(range(54))
    rows = []
    scheduler = PlacementScheduler(manager, RackGeometry(3, 1, 18), make_scorer(policy, {}), legacy_config("lassen"), rows.append)
    scheduler.on_power_tick(np.full(3, 10.0))
    scheduler.on_thermal(ThermalView(0, np.array([30.0, 31.0, 32.0]), np.ones(3)))
    return scheduler, manager, rows


def job(i, n=4, submit=0):
    return SimpleNamespace(id=i, nodes_required=n, submit_time=submit, cpu_trace=2.0, gpu_trace=4.0, scheduled_nodes=[])


def test_power_balance_updates_committed_power_between_same_second_jobs():
    scheduler, manager, rows = setup()
    queue = [job(2), job(1)]
    running = []
    scheduler.schedule(queue, running, 0)
    assert [row["job_id"] for row in rows] == [1, 2]
    assert [row["racks"] for row in rows] == [[0], [1]]
    assert rows[0]["committed_kw"] == [10.0, 10.0, 10.0]
    assert rows[1]["committed_kw"][0] > 10.0
    assert len(manager.available_nodes) == 46 and not queue and len(running) == 2


def test_coolest_rack_herds_while_thermal_view_is_unchanged():
    scheduler, _, rows = setup("coolest_rack")
    scheduler.schedule([job(0), job(1)], [], 0)
    assert [row["racks"] for row in rows] == [[0], [0]]
    assert set(rows[0]["nodes"]).isdisjoint(rows[1]["nodes"])


def test_head_of_line_blocking_keeps_smaller_job_queued():
    scheduler, _, rows = setup()
    queue = [job(0, n=55), job(1, n=1)]
    scheduler.schedule(queue, [], 0)
    assert len(queue) == 2 and rows == []


def test_decision_schema_and_pre_action_context():
    scheduler, manager, rows = setup()
    scheduler.schedule([job(0)], [], 25)
    expected = {"t_s", "job_id", "nodes_required", "policy", "rule", "racks", "nodes", "job_kw", "scores", "t_c", "committed_kw", "free", "t_obs_s", "latency_us"}
    assert set(rows[0]) == expected
    assert rows[0]["free"] == [18, 18, 18]
    assert rows[0]["t_obs_s"] == 0 and rows[0]["t_s"] == 25
    assert manager.calls[0][2] == PolicyType.REPLAY
    assert rows[0]["nodes"] == [0, 1, 2, 3]
