"""Engineering wiring fixture only: real RAPS, test-double thermal dependency.

Artifacts stay in pytest's temp directory and are never E10 evidence. The real
FMU vertical-slice test separately exercises the complete production path.
"""

import json

import numpy as np
import pandas as pd

from thermorl2.core.state import RackThermal
from thermorl2.experiments.provenance import sha256_file
from thermorl2.experiments.run import load_config, CONFIGS
from thermorl2.raps_adapter import runner


class ThermalDouble:
    calls = 0

    def __init__(self, path, coupling):
        self.n = coupling.num_cdus
        self.time_s = 0.0

    def warm_up(self, *args, **kwargs):
        return 7200.0

    def step(self, power, dt, ambient):
        self.time_s += dt
        type(self).calls += 1

    def observe(self):
        return RackThermal(np.full(self.n, 40.0), {"W_flow_CDUP_kW": np.ones(self.n)})

    def global_observe(self):
        return {"test_double": 1.0}

    def runtime_s(self):
        return 1.0

    def close(self):
        pass


def test_runner_wiring_counts_steps_and_records_completion_reuse(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "FmuBackend", ThermalDouble)
    ThermalDouble.calls = 0
    frame = pd.DataFrame([{"id": i, "nodes_required": 2, "cpu_util": 1.0, "gpu_util": 1.0,
                           "submit_time": float(submit), "expected_run_time": runtime, "time_limit": 600}
                          for i, submit, runtime in ((0, 0, 301), (1, 25, 303))])
    frame.attrs["seed"] = 1
    path = tmp_path / "fixture.parquet"
    frame.to_parquet(path, index=False)
    meta = path.with_name(path.name + ".meta.json")
    meta.write_text("{}")
    cfg = load_config(CONFIGS / "smoke_2h.yaml")
    cfg["horizon_h"] = 0.1
    cfg["workload"].update(path=str(path), sha256=sha256_file(path))
    out = runner.EpisodeRunner(cfg, "packing", 1, tmp_path / "run").run()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["fmu_steps"] == manifest["power_ticks"] == ThermalDouble.calls == 36
    assert manifest["backend_elapsed_s"] == 360.0
    intervals = pd.read_parquet(out / "intervals.parquet")
    assert sorted(intervals.t_s.unique()) == list(range(10, 361, 10))
    assert intervals[intervals.t_s == 360].free.sum() == 4626
    decisions = runner.read_jsonl(out / "decisions.jsonl")
    assert [row["t_s"] for row in decisions] == [0, 25]
    assert all(row["latency_us"] is None for row in decisions)
    assert manifest["decision_rows"] == manifest["decision_latency_rows"] == 2
    events = runner.read_jsonl(out / "provenance/job_events.jsonl")
    assert sum(event["event"] == "complete" for event in events) == 2
