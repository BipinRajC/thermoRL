import json
from pathlib import Path

import pandas as pd
import pytest

from thermorl2.core.metrics import Run
from thermorl2.experiments import plots, report


def fixture_runs():
    frame = pd.DataFrame([dict(t_s=t,rack=r,t_c=30+r+t/21600,kw=1)
                          for t in (10,10800,21600) for r in range(3)])
    return [Run(name,frame.copy(),[dict(t_s=10800,racks=[1])],
                dict(config={'horizon_h':6,'scenario':{'name':'nominal'}}))
            for name in ('packing','thermal_predictive')]


def test_plot_functions_write_files_and_use_episode_horizon(tmp_path):
    runs = fixture_runs()
    plots.heatmaps(runs,tmp_path/'heat.png',30,34)
    plots.timeseries(runs,tmp_path/'time.png')
    plots.metrics_table([dict(policy='packing',seed=1,maxrack_mean_c=32),
                         dict(policy='packing',seed=2,maxrack_mean_c=34)],tmp_path/'table.md')
    plots.animate_grid(runs,tmp_path/'anim.gif',(1,4),stride_ticks=1)
    assert all(p.stat().st_size > 0 for p in tmp_path.iterdir())
    assert '33.000000 [32.000000, 34.000000]' in (tmp_path/'table.md').read_text()
    assert plots.episode_hours(runs[0]) == 6


def test_g4_rule_requires_half_degree_in_every_seed():
    rows = [dict(policy=p,seed=s,maxrack_mean_c=value)
            for s,gap in ((1,0.7),(2,0.3),(3,0.6))
            for p,value in [('power_balance',50),('thermal_predictive',50-gap),('packing',52)]]
    decision = report.g4_decision(rows)
    assert decision['value_beyond_power'] is False
    assert decision['per_seed']['2']['power_minus_thermal_c'] == pytest.approx(0.3)
    assert decision['per_seed']['1']['packing_minus_thermal_c'] == pytest.approx(2.7)


def test_e10_reporting_uses_ledgers_without_overwriting_e10(tmp_path):
    root=Path(__file__).resolve().parents[2]/'experiments/summit/E10_c2_vertical_slice'
    runs=[report.load_run(root/'runs'/f'{p}_seed1') for p in ('packing','power_balance')]
    result=report.build_report(runs,tmp_path,eval_start_s=3600,t_hot_c=63.30492211035258,
                               grid=(13,20),g4=False,animations=False)
    assert result['scope'] == 'ledger analysis; no G4 decision'
    assert result['runs']['power_balance_seed1']['hot_rack_seconds'] == 0
    assert (tmp_path/'results/max_rack_attribution.json').is_file()
    with pytest.raises(FileExistsError):
        report.build_report(runs,tmp_path,3600,63.3,(13,20),g4=False,animations=False)


def test_g2_plot_writes_existing_fmu_evidence_only(tmp_path):
    source=Path(__file__).resolve().parents[2]/'experiments/summit/E02_g2_packed_vs_spread'
    plots.g2_figure(source,tmp_path/'g2.png')
    assert (tmp_path/'g2.png').stat().st_size > 0


def test_expected_preregistration_rejects_self_consistent_wrong_config():
    from copy import deepcopy
    root=Path(__file__).resolve().parents[2]/'experiments/summit/E10_c2_vertical_slice/runs/packing_seed1'
    run=report.load_run(root)
    expected=deepcopy(run.manifest['config'])
    assert report.validate_expected(run,expected)
    expected['workload']['rho']=0.5
    with pytest.raises(AssertionError): report.validate_expected(run,expected)
