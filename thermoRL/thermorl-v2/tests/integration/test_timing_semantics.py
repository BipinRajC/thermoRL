import math
from pathlib import Path

import pytest
import yaml
from raps.job import Job, job_dict
from raps.policy import PolicyType

from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine, is_power_tick, rack_kw_from_power_df
from thermorl2.raps_adapter.power_model import legacy_config, raps_rack_kw

pytestmark = pytest.mark.integration
PRIMARY = yaml.safe_load((Path(__file__).parents[2] / "thermorl2/experiments/configs/primary.yaml").read_text())["system"]


class RecordingScheduler:
    policy = PolicyType.FCFS
    bfpolicy = None

    def __init__(self, manager):
        self.manager = manager
        self.calls = []

    def schedule(self, queue, running, current_time, accounts=None, sorted=False):
        self.calls.append(current_time)
        for job in list(queue):
            if len(self.manager.available_nodes) < job.nodes_required:
                break
            job.scheduled_nodes = self.manager.available_nodes[:job.nodes_required]
            self.manager.assign_nodes_to_job(job, current_time, PolicyType.REPLAY)
            running.append(job)
            queue.remove(job)


def job_for(cfg, submit_time, runtime=600, limit=1200):
    Job._id_counter = 0
    return Job(job_dict(nodes_required=cfg["NODES_PER_RACK"], name="timing", account="demo", id=0,
                        cpu_trace=cfg["CPUS_PER_NODE"], gpu_trace=cfg["GPUS_PER_NODE"], ntx_trace=0, nrx_trace=0,
                        submit_time=submit_time, expected_run_time=runtime, time_limit=limit, start_time=None, end_time=None))


@pytest.mark.parametrize("system", [PRIMARY])
def test_arrival_scheduled_at_t_powered_at_next_tick(system):
    cfg = legacy_config(system)
    job = job_for(cfg, 25)
    engine = build_engine(EngineSpec(system, "2m"), jobs=[job])
    scheduler = RecordingScheduler(engine.resource_manager)
    engine.scheduler = scheduler
    idle = raps_rack_kw(cfg, 0, 0)
    peak = raps_rack_kw(cfg, cfg["CPUS_PER_NODE"], cfg["GPUS_PER_NODE"])
    hot_ticks = []
    for tick in engine.run_simulation():
        if is_power_tick(tick, engine.time_delta):
            power = rack_kw_from_power_df(tick.power_df, cfg["RACKS_PER_CDU"])
            if power[0] > idle + 0.5 * (peak - idle):
                hot_ticks.append(tick.current_timestep)
    assert job.start_time == 25 and 25 in scheduler.calls
    assert hot_ticks[0] == math.ceil(25 / engine.time_delta) * engine.time_delta


@pytest.mark.parametrize("system", [PRIMARY])
def test_time_limit_overrun_raises(system):
    cfg = legacy_config(system)
    engine = build_engine(EngineSpec(system, "2m"), jobs=[job_for(cfg, 0, runtime=60, limit=10)])
    engine.scheduler = RecordingScheduler(engine.resource_manager)
    with pytest.raises(Exception, match="(?i)time limit"):
        list(engine.run_simulation())
