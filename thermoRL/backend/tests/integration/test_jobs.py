import pandas as pd
import pytest

from thermorl2.raps_adapter.jobs import jobs_from_frame
from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine

pytestmark = pytest.mark.integration


def frame(limit=900):
    return pd.DataFrame([{"id": 7, "nodes_required": 2, "cpu_util": 1.5, "gpu_util": 5.0, "submit_time": 25,
                          "expected_run_time": 600, "time_limit": limit}])


def test_jobs_roundtrip_and_id_counter_reset():
    a = jobs_from_frame(frame())[0]
    b = jobs_from_frame(frame())[0]
    assert a.id == b.id == 7
    assert a.nodes_required == 2 and a.cpu_trace == 1.5 and a.gpu_trace == 5.0
    assert a.submit_time == 25 and a.expected_run_time == 600 and a.time_limit == 900
    assert a.start_time is None and a.end_time is None
    assert type(a.cpu_trace) is float and type(a.gpu_trace) is float


def test_jobs_reject_time_limit_below_runtime():
    with pytest.raises(AssertionError):
        jobs_from_frame(frame(limit=599))


def test_integer_runtimes_complete_across_summit_power_ticks():
    records = []
    for i, runtime in enumerate(range(301, 311)):
        records.append({"id": i, "nodes_required": 1, "cpu_util": 1.0, "gpu_util": 1.0,
                        "submit_time": 25.0, "expected_run_time": runtime, "time_limit": 2 * runtime})
    jobs = jobs_from_frame(pd.DataFrame(records))
    engine = build_engine(EngineSpec("summit", "6m", 1), jobs=jobs)
    for _ in engine.run_simulation():
        pass
    assert engine.jobs_completed == 10
    for job in jobs:
        assert job.start_time == 25
        assert job.end_time == 25 + job.expected_run_time + 1
