from pathlib import Path

import numpy as np
import pytest
import yaml
from raps.job import Job, job_dict
from raps.policy import PolicyType

from thermorl2.core.scorers import make_scorer
from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine
from thermorl2.raps_adapter.power_model import legacy_config
from thermorl2.raps_adapter.rack_geometry import RackGeometry
from thermorl2.raps_adapter.scheduler import PlacementScheduler, ThermalView

PRIMARY = yaml.safe_load((Path(__file__).parents[2] / "thermorl2/experiments/configs/primary.yaml").read_text())["system"]
pytestmark = pytest.mark.integration


def make_job(i, n, submit=0):
    return Job(job_dict(nodes_required=n, name=f"j{i}", id=i, account="demo", cpu_trace=2.0, gpu_trace=4.0,
                        ntx_trace=0, nrx_trace=0, submit_time=submit, expected_run_time=600, time_limit=1200,
                        start_time=None, end_time=None))


def run(jobs, policy="power_balance", sink=None, prime_only=False):
    cfg = legacy_config(PRIMARY)
    engine = build_engine(EngineSpec(PRIMARY, "3m", 1), jobs=jobs)
    rows = []
    def record(row):
        rows.append(row)
        if sink:
            sink(row)
    geometry = RackGeometry.from_legacy_config(cfg)
    scheduler = PlacementScheduler(engine.resource_manager, geometry, make_scorer(policy, {}), cfg, record)
    scheduler.on_thermal(ThermalView(0, np.full(geometry.n_racks, 30.0), np.ones(geometry.n_racks)))
    engine.scheduler = scheduler
    generator = engine.run_simulation()
    if prime_only:
        next(generator)
        generator.close()
    else:
        for _ in generator:
            pass
    return engine, rows


def test_exact_nodes_allocated():
    _, rows = run([make_job(0, 32)])
    assert len(rows[0]["nodes"]) == len(set(rows[0]["nodes"])) == 32
    assert rows[0]["rule"] == "span"


def test_policy_attrs_survive_prepare_system_state():
    engine, _ = run([make_job(0, 4)], prime_only=True)
    assert engine.scheduler.policy == PolicyType.FCFS and engine.scheduler.bfpolicy is None


def test_power_balance_spreads_same_second_arrivals():
    _, rows = run([make_job(0, 4), make_job(1, 4)])
    assert rows[0]["racks"] != rows[1]["racks"]


def test_coolest_rack_herds_same_second_arrivals():
    _, rows = run([make_job(0, 4), make_job(1, 4)], "coolest_rack")
    assert rows[0]["racks"] == rows[1]["racks"] == [0]


def test_nodes_distinct_and_free():
    rng = np.random.default_rng(1)
    jobs = [make_job(i, int(rng.integers(1, 33)), int(rng.integers(0, 120))) for i in range(40)]
    allocated = set()
    def check(row):
        assert len(row["nodes"]) == len(set(row["nodes"])) == row["nodes_required"]
        assert allocated.isdisjoint(row["nodes"])
        allocated.update(row["nodes"])
    _, rows = run(jobs, sink=check)
    assert len(rows) == 40


def test_head_of_line_blocking():
    cfg = legacy_config(PRIMARY)
    engine, rows = run([make_job(0, cfg["TOTAL_NODES"] + 1), make_job(1, 1)])
    assert rows == [] and len(engine.queue) == 2
