import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thermorl2.core import metrics
from thermorl2.core.scorers import Packing, PowerBalance


def fixture_run():
    frame = pd.DataFrame([
        dict(t_s=t, rack=r, t_c=temp, kw=r + 1, pump_kw=1.0, free=1,
             it_kw_total=6.0, n_running=1, n_queued=0)
        for t, temps in [(10, [99, 99, 99]), (20, [30, 40, 50]),
                         (30, [35, 45, 55]), (40, [20, 30, 40])]
        for r, temp in enumerate(temps)])
    return metrics.Run('fixture', frame, [], dict(
        t_idle_c=[20]*3, power_tick_s=10, total_nodes=6, nodes_per_rack=2,
        n_racks=3, fmu_steps=4, backend_elapsed_s=40,
        config={'horizon_h': 40/3600}, raps_s=1, fmu_s=2, total_s=3))


def test_hand_computed_thermal_metrics_strict_window_and_energy():
    row = metrics.run_metrics(fixture_run(), 10, 47)
    assert row['maxrack_mean_c'] == pytest.approx(145/3)
    assert row['spread_mean_c'] == 20
    assert row['hot_rack_seconds'] == 20
    assert row['pump_energy_kwh'] == pytest.approx(120/3600)
    assert row['it_energy_kwh'] == pytest.approx(240/3600)
    assert row['rack_t_std_mean_c'] == pytest.approx(np.std([30,40,50]))
    assert row['top_decile_mean_c'] == pytest.approx(145/3)
    assert row['rack_kw_std_mean'] == pytest.approx(np.std([1,2,3]))
    assert row['decision_latency_mean_us'] is None


def context_row(power, logged_rack=0):
    return dict(free=[1,1,1], committed_kw=power, t_c=[40,40,40],
                job_kw=1, nodes_required=2, racks=[logged_rack], job_id=0, t_s=2)


def test_counterfactuals_use_same_context_and_distinct_free_node_ids():
    rows = [context_row([1,2,3], 2), context_row([3,2,1], 2)]
    assert metrics.disagreement_rate(rows, Packing(), PowerBalance()) == 0.5
    assert metrics.self_reproduction_rate(rows, Packing()) == 0.0


def test_cross_policy_invariants_detect_power_and_start_differences():
    a, b = fixture_run(), fixture_run()
    assert metrics.invariants([a,b])['it_kw_identical']
    b.intervals.loc[b.intervals.t_s == 20, 'it_kw_total'] += 1
    b.decisions = [dict(job_id=0,t_s=2)]
    result = metrics.invariants([a,b])
    assert not result['it_kw_identical']
    assert result['max_abs_it_kw_diff'] == 1
    assert not result['start_times_identical']


def test_load_run_resolves_workload_and_waits_censoring_latency(tmp_path, monkeypatch):
    run = fixture_run()
    workload = pd.DataFrame(dict(id=[0,1],submit_time=[1.2,39.5]))
    workload.to_parquet(tmp_path/'work.parquet')
    run.manifest['workload_path'] = 'work.parquet'
    run.decisions = [dict(job_id=0,t_s=2,latency_us=None)]
    out = tmp_path/'run'
    (out/'provenance').mkdir(parents=True)
    run.intervals.to_parquet(out/'intervals.parquet')
    (out/'manifest.json').write_text(json.dumps(run.manifest))
    (out/'decisions.jsonl').write_text(json.dumps(run.decisions[0])+'\n')
    (out/'provenance/decision_latency.jsonl').write_text(json.dumps(
        dict(decision_index=0,job_id=0,t_s=2,latency_ns=1500))+'\n')
    monkeypatch.setattr(metrics,'PROJECT',tmp_path)
    loaded = metrics.load_run(out)
    result = metrics.run_metrics(loaded,10,47)
    assert result['wait_mean_s'] == pytest.approx(0.8)
    assert result['jobs_censored'] == 1
    assert result['decision_latency_mean_us'] == 1.5


def test_max_attribution_uses_power_tick_residency_not_endpoint_events():
    run = fixture_run()
    run.job_events = [dict(event='start',t_s=0,job_id=7,nodes=[4]),
                      dict(event='complete',t_s=25,job_id=7,nodes=[4])]
    result = metrics.max_rack_attribution(run,10)
    assert [row['resident_job_ids'] for row in result['ticks']] == [[7],[7],[]]
    assert result['rack_shares'] == {'2': 1.0}


def test_e10_ledgers_reproduce_reviewed_metrics_and_rounding_diagnostic():
    root = Path(__file__).resolve().parents[2]/'experiments/summit/E10_c2_vertical_slice/runs'
    run = metrics.load_run(root/'power_balance_seed1')
    result = metrics.run_metrics(run,3600,63.30492211035258)
    assert result['maxrack_mean_c'] == pytest.approx(54.115585106899964)
    assert result['hot_rack_seconds'] == 0
    rate = metrics.self_reproduction_rate(run.decisions, PowerBalance())
    assert 0.994 < rate < 0.996
