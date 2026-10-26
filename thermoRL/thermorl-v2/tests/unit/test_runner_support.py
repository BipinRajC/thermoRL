import hashlib
import json

import pytest
import pandas as pd
import yaml

from thermorl2.raps_adapter.runner import DecisionLedgers
from thermorl2.experiments.run import e10_metrics, load_config


def decision():
    return {"t_s": 25, "job_id": 7, "nodes_required": 1, "policy": "packing", "rule": "single",
            "racks": [0], "nodes": [0], "job_kw": 1.0, "scores": [0.0], "t_c": [40.0],
            "committed_kw": [14.0], "free": [18], "t_obs_s": 20.0, "latency_us": None}


def test_decision_and_latency_ledgers_join_and_preserve_integer_ns(tmp_path):
    ledgers = DecisionLedgers(tmp_path)
    ledgers.write_decision(decision())
    measured = {"decision_index": 0, "job_id": 7, "t_s": 25, "latency_ns": 9007199254740993}
    ledgers.write_timing(measured)
    metadata = ledgers.finalize()
    raw = (tmp_path / "decisions.jsonl").read_bytes()
    assert json.loads(raw)["latency_us"] is None
    assert raw == (json.dumps(decision(), sort_keys=True) + "\n").encode()
    timing = json.loads((tmp_path / "provenance/decision_latency.jsonl").read_text())
    assert timing == measured and type(timing["latency_ns"]) is int
    assert metadata["decision_rows"] == metadata["decision_latency_rows"] == 1
    assert metadata["decisions_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("timing", [None, {"decision_index": 0, "job_id": 8, "t_s": 25, "latency_ns": 1}, {"decision_index": 1, "job_id": 7, "t_s": 25, "latency_ns": 1}])
def test_ledger_join_rejects_missing_or_mismatched_timing(tmp_path, timing):
    ledgers = DecisionLedgers(tmp_path)
    ledgers.write_decision(decision())
    if timing:
        ledgers.write_timing(timing)
    with pytest.raises(AssertionError):
        ledgers.finalize()


def test_loads_exact_predictor_fields_from_primary(tmp_path):
    summary = tmp_path / "g1.json"
    summary.write_text(json.dumps({"fit": {"a_c": 20, "b_c_per_kw": 0.5, "r2": 0.9}, "tau_s": 4050}))
    (tmp_path / "primary.yaml").write_text(yaml.safe_dump({"system": "summit", "thermal_predictive": {"from": str(summary), "horizon_s": 600}}))
    path = tmp_path / "smoke.yaml"
    path.write_text(yaml.safe_dump({"include": "primary.yaml", "horizon_h": 2}))
    cfg = load_config(path)
    assert cfg["system"] == "summit"
    assert cfg["thermal_predictive_params"] == {"a_c": 20, "b_c_per_kw": 0.5, "tau_s": 4050, "horizon_s": 600}


def test_e10_metrics_use_strict_warm_in_boundary_and_time_maximum():
    frame = pd.DataFrame({"t_s": [3600,3600,3610,3610,7200,7200], "rack": [0,1,0,1,0,1],
                          "t_c": [99,99,30,40,50,20], "free": [2,2,1,1,0,1]})
    manifest = {"total_nodes": 4, "raps_s": 1, "fmu_s": 2, "total_s": 3, "t_idle_c": [20,20]}
    result = e10_metrics(frame, manifest, [{"job_id": 0}])
    assert result["maxrack_mean_c"] == 45
    assert abs(result["maxrack_p99_c"] - 49.9) < 1e-12
    assert result["mean_rack_c"] == 35
    assert result["raw_max_c"] == 99
    assert result["realised_node_utilisation_mean"] == 0.625
