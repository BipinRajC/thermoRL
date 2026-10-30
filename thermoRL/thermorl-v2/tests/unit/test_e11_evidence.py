import json
from pathlib import Path

import pandas as pd
import pytest

from thermorl2.experiments import evidence,report


def test_prefix_comparison_is_bytes_for_decisions_and_exact_values_for_intervals(tmp_path):
    old,new=tmp_path/'old',tmp_path/'new'
    for path in (old,new): path.mkdir()
    line=b'{"job_id": 0, "t_s": 5}\n'
    (old/'decisions.jsonl').write_bytes(line)
    (new/'decisions.jsonl').write_bytes(line+b'{"job_id": 1, "t_s": 7200}\n')
    frame=pd.DataFrame({'t_s':[10.,7200.],'rack':[0,0],'t_c':[40.,42.]})
    frame.to_parquet(old/'intervals.parquet')
    pd.concat([frame,pd.DataFrame({'t_s':[7210.],'rack':[0],'t_c':[43.]})],ignore_index=True).to_parquet(new/'intervals.parquet')
    assert evidence.compare_prefix(old,new)['result'] is True
    (new/'decisions.jsonl').write_bytes(line.replace(b': 0',b':0'))
    result=evidence.compare_prefix(old,new)
    assert not result['result'] and not result['decisions_byte_identical']


def test_approved_scope_is_not_full_e11_remeasurement():
    inherited={'kind':'inherited_E10','scope':'packing seed1 2h','result':True,'ref':'E10.json'}
    prefix={'kind':'E11_prefix_vs_E10','scope':'seed1 2h prefix','result':True,'ref':'prefix.json'}
    for seed in (1,2,3):
        record={'status':'inherited_not_remeasured','evidence':[inherited]+([prefix] if seed==1 else [])}
        assert report.approved_determinism(record,seed)
        assert not report.approved_determinism({**record,'status':'verified_E11'},seed)
    assert not report.approved_determinism({'status':'inherited_not_remeasured','evidence':[inherited]},1)
    assert not report.approved_determinism({'status':'inherited_not_remeasured','evidence':[inherited,{**prefix,'result':False}]},1)


def test_g4_build_path_accepts_scope_and_invalidates_measured_failure(tmp_path,monkeypatch):
    from thermorl2.core.metrics import Run
    frame=pd.DataFrame([dict(t_s=t,rack=r,t_c=40.+r,kw=1.,pump_kw=1.,free=1,it_kw_total=3.)
                        for t in (10.,20.) for r in range(3)])
    params=dict(a_c=28,b_c_per_kw=.8,tau_s=4050,horizon_s=600)
    runs=[]
    for seed in (1,2,3):
        for policy in report.POLICIES:
            m=dict(seed=seed,policy=policy,n_racks=3,nodes_per_rack=2,total_nodes=6,power_tick_s=10,
                   fmu_steps=2,backend_elapsed_s=20.,config={'horizon_h':20/3600},t_idle_c=[30]*3,
                   raps_s=1.,fmu_s=2.,total_s=3.,power_reconciliation_max_abs_kw=0.,thermal_predictive_params=params)
            runs.append(Run(f'{policy}_seed{seed}',frame.copy(),[],m))
    monkeypatch.setattr(report,'allocation_valid',lambda _:True)
    monkeypatch.setattr(report,'manifest_valid',lambda _,**kwargs:True)
    monkeypatch.setattr(report,'validate_expected',lambda *_:True)
    inherited=dict(kind='inherited_E10',scope='2h packing seed1',result=True,ref='E10')
    prefix=dict(kind='E11_prefix_vs_E10',scope='2h prefix',result=True,ref='prefix')
    proof={'per_seed':{str(s):dict(status='inherited_not_remeasured',evidence=[inherited]+([prefix] if s==1 else [])) for s in (1,2,3)}}
    result=report.build_report(runs,tmp_path/'valid',0,63.3,(1,3),animations=False,
                               determinism_evidence=proof,expected_config={'fixture':True})
    assert result['value_beyond_power'] is False
    prefix['result']=False
    with pytest.raises(AssertionError,match='invariant failure'):
        report.build_report(runs,tmp_path/'invalid',0,63.3,(1,3),animations=False,
                            determinism_evidence=proof,expected_config={'fixture':True})
    assert 'INVALID' in json.loads((tmp_path/'invalid/results/summary.json').read_text())['decision']
