"""Synthetic ledgers in pytest tmp_path only; these tests instantiate no FMU."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thermorl2.core.metrics import load_run
from thermorl2.experiments import e12_evidence,report
from thermorl2.raps_adapter.systems import get_system


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,sort_keys=True)+'\n')


def rehash(path):
    m=json.loads((path/'manifest.json').read_text())
    for filename,key in [('decisions.jsonl','decisions_sha256'),('intervals.parquet','intervals_sha256'),
        ('provenance/decision_latency.jsonl','decision_latency_sha256'),('provenance/job_events.jsonl','job_events_sha256')]:
        m[key]=report._sha(path/filename)
    write_json(path/'manifest.json',m)


@pytest.fixture
def pair(tmp_path):
    workload=tmp_path/'work.parquet'
    f=pd.DataFrame([dict(id=0,nodes_required=1,submit_time=0.,expected_run_time=600,time_limit=900,cpu_util=1.,gpu_util=1.)])
    f.attrs['seed']=1;f.to_parquet(workload,index=False)
    meta=Path(str(workload)+'.meta.json');write_json(meta,dict(seed=1,horizon_s=21600))
    params=dict(a_c=28.,b_c_per_kw=.8,tau_s=4050.,horizon_s=600)
    cfg=dict(system='summit',horizon_h=6,warmup_s=7200,policies=list(report.POLICIES),seeds=[1,2,3],
        workload=dict(kind='alibaba',variant='default',path=str(workload),sha256=report._sha(workload),meta_sha256=report._sha(meta)),
        thermal_predictive_params=params)
    a=tmp_path/'E12/runs/thermal_predictive_seed1'
    b=tmp_path/'E12/provenance/rerun_1/runs/thermal_predictive_seed1'
    for path in (a,b):
        (path/'provenance').mkdir(parents=True)
        row=dict(t_s=0,job_id=0,nodes_required=1,policy='thermal_predictive',rule='single',racks=[0],nodes=[0],
                 job_kw=1.,scores=[1.,2.,3.],t_c=[40.]*3,committed_kw=[1.]*3,free=[2]*3,t_obs_s=0.,latency_us=None)
        write_json(path/'decisions.jsonl',row)
        write_json(path/'provenance/decision_latency.jsonl',dict(decision_index=0,job_id=0,t_s=0,latency_ns=100))
        events=[dict(event='start',t_s=0,job_id=0,nodes=[0],decision_index=0),dict(event='complete',t_s=601,job_id=0,nodes=[0])]
        (path/'provenance/job_events.jsonl').write_text(''.join(json.dumps(e,sort_keys=True)+'\n' for e in events))
        write_json(path/'provenance/thermal_publications.jsonl',dict(raps_power_tick_s=0.,fmu_episode_endpoint_s=10.,t_obs_s=10.))
        frame=pd.DataFrame([dict(t_s=float(t),rack=r,kw=1.,t_c=40.+r,pump_kw=1.,free=2,it_kw_total=3.)
                            for t in range(10,21601,10) for r in range(3)])
        frame.to_parquet(path/'intervals.parquet',index=False)
        m=dict(git={'sha':'fixture','dirty':False},git_status_porcelain='',system='summit',backend='fmu',
            fmu_sha256=get_system('summit').fmu_sha256,workload_path=str(workload),workload_sha256=cfg['workload']['sha256'],
            workload_meta_sha256=cfg['workload']['meta_sha256'],config=cfg,
            config_sha256=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),policy='thermal_predictive',seed=1,
            thermal_predictive_params=params,rack_kw_reference={},power_tick_s=10,power_ticks=2160,fmu_steps=2160,
            backend_elapsed_s=21600.,warmup_used_s=7200.,t_idle_c=[30.]*3,raps_s=1.,fmu_s=2.,total_s=3.,
            environment={'python':'fixture'},decision_rows=1,decision_latency_rows=1,decision_latency_span='fixture',
            source_sha256={'fixture.py':'fixture'},total_nodes=6,nodes_per_rack=2,n_racks=3,power_reconciliation_max_abs_kw=0.)
        write_json(path/'manifest.json',m);rehash(path)
    return tmp_path/'E12',a,b,cfg


def test_identical_pair_verified_and_timing_only_difference_excluded(pair):
    out,a,b,cfg=pair
    result=e12_evidence.compare_full_rerun(a,b,cfg)
    assert result['result'] and result['preconditions_passed']
    timing=json.loads((b/'provenance/decision_latency.jsonl').read_text());timing['latency_ns']=999
    write_json(b/'provenance/decision_latency.jsonl',timing);rehash(b)
    assert e12_evidence.compare_full_rerun(a,b,cfg)['result']


@pytest.mark.parametrize('change',['decision_byte','interval'])
def test_measured_difference_fails_and_report_is_invalid(pair,change,tmp_path,monkeypatch):
    out,a,b,cfg=pair
    if change=='decision_byte':
        raw=(b/'decisions.jsonl').read_bytes();(b/'decisions.jsonl').write_bytes(raw.replace(b': 0,',b':0,',1))
    else:
        f=pd.read_parquet(b/'intervals.parquet');f.loc[0,'t_c']+=.001;f.to_parquet(b/'intervals.parquet',index=False)
    rehash(b)
    proof=e12_evidence.generate_evidence(out,cfg)
    assert proof['per_configuration']['thermal_predictive_seed1']['status']=='failed'
    assert not report.approved_e12_determinism(proof)
    runs=[]
    for seed in (1,2,3):
        for policy in report.POLICIES:
            run=load_run(a);run.name=f'{policy}_seed{seed}';run.manifest=deepcopy(run.manifest)
            run.manifest.update(seed=seed,policy=policy);runs.append(run)
    def validation(group,*args,**kwargs):
        return {'invariants':{'1_fixture':True,'3_fixture':{}},'determinism_evidence':proof}
    monkeypatch.setattr(report,'validate_seed',validation)
    with pytest.raises(AssertionError,match='invariant failure'):
        report.build_report(runs,tmp_path/'invalid',3600,63.3,(1,3),animations=False,determinism_evidence=proof,expected_config=cfg)
    assert 'INVALID' in json.loads((tmp_path/'invalid/results/summary.json').read_text())['decision']


@pytest.mark.parametrize('key',['config_sha256','workload_sha256','workload_meta_sha256','fmu_sha256',
    'source_sha256','git','environment','warmup_used_s','fmu_steps','backend_elapsed_s'])
def test_every_exact_precondition_mismatch_refused(pair,key):
    out,a,b,cfg=pair;m=json.loads((b/'manifest.json').read_text())
    if key=='source_sha256':m[key]={'other.py':'different'}
    elif key=='git':m[key]={'sha':'different','dirty':False}
    elif key=='environment':m[key]={'python':'different'}
    elif isinstance(m[key],(int,float)):m[key]-=1
    else:m[key]='different'
    write_json(b/'manifest.json',m)
    with pytest.raises(e12_evidence.ComparisonPreconditionError):
        e12_evidence.compare_full_rerun(a,b,cfg)


def test_exact_C_prime_pattern_and_no_A_prime_fallback(pair):
    out,a,b,cfg=pair;proof=e12_evidence.generate_evidence(out,cfg)
    assert report.approved_e12_determinism(proof)
    for name in list(proof['per_configuration']):
        changed=deepcopy(proof)
        if name=='thermal_predictive_seed1':changed['per_configuration'][name]['status']='inherited_not_remeasured'
        else:changed['per_configuration'][name]['status']='verified_E12'
        assert not report.approved_e12_determinism(changed)
    changed=deepcopy(proof);changed['fallback_to_A_prime']=True
    assert not report.approved_e12_determinism(changed)
    changed=deepcopy(proof);del changed['per_configuration']['packing_seed3']
    assert not report.approved_e12_determinism(changed)


def test_E11_committed_evidence_still_passes():
    root=Path(__file__).resolve().parents[2]/'experiments/summit/E11_g4_synthetic'
    checks=json.loads((root/'results/invariants.json').read_text())
    assert all(report.seed_gate(check,seed) for seed,check in checks.items())


@pytest.mark.parametrize('existing',['determinism_evidence.json','determinism_evidence.json.sha256','full_rerun_comparison.json'])
def test_evidence_and_seal_never_overwrite(pair,existing):
    out,a,b,cfg=pair;path=out/'provenance'/existing;path.write_text('preserve')
    with pytest.raises(FileExistsError):e12_evidence.generate_evidence(out,cfg)
    assert path.read_text()=='preserve'


def test_rerun_inventory_and_guard_refuse_existing_directory(pair):
    out,a,b,cfg=pair;base=out/'provenance/rerun_1'
    listing=e12_evidence.write_rerun_inventory(base)
    assert 'runs/thermal_predictive_seed1/decisions.jsonl' in listing
    with pytest.raises(FileExistsError):e12_evidence.write_rerun_inventory(base)
    with pytest.raises(FileExistsError):e12_evidence.run_rerun(cfg,'fixture.yaml',out)


def test_interval_file_bytes_are_information_only(pair):
    out,a,b,cfg=pair
    f=pd.read_parquet(b/'intervals.parquet');f.to_parquet(b/'intervals.parquet',index=False,compression=None);rehash(b)
    result=e12_evidence.compare_full_rerun(a,b,cfg)
    assert result['result'] and not result['information']['interval_file_bytes_identical']


def test_guard_runs_one_subprocess_and_preserves_primary_inventory(pair,tmp_path,monkeypatch):
    import shutil
    from types import SimpleNamespace
    out,a,b,cfg=pair;target=tmp_path/'guarded'
    primary=target/'results/run_files.json';primary.parent.mkdir(parents=True);primary.write_text('{"primary":"preserve"}')
    monkeypatch.setattr(e12_evidence,'_matrix_complete',lambda *_:None)
    calls=[]
    def execute(command,**kwargs):
        calls.append(command)
        destination=Path(command[command.index('--run-dir')+1]);shutil.copytree(a,destination)
        kwargs['stdout'].write('temporary engineering fixture, no FMU\n')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(e12_evidence.subprocess,'run',execute)
    actual=e12_evidence.run_rerun(cfg,'fixture.yaml',target)
    assert len(calls)==1 and calls[0][calls[0].index('--policy')+1]=='thermal_predictive'
    assert calls[0][calls[0].index('--seed')+1]=='1'
    assert primary.read_text()=='{"primary":"preserve"}'
    assert (target/'provenance/rerun_1/manifest.json').read_bytes()==(actual/'manifest.json').read_bytes()
    assert (target/'provenance/rerun_1/run_files.json').exists()
    with pytest.raises(FileExistsError):e12_evidence.run_rerun(cfg,'fixture.yaml',target)
    assert len(calls)==1


def test_report_primary_path_list_never_includes_rerun(pair,tmp_path,monkeypatch):
    import sys
    from thermorl2.experiments import run
    out,a,b,cfg=pair
    proof=e12_evidence.generate_evidence(out,cfg)
    source=tmp_path/'g1.json';write_json(source,{'t_hot_c':63.3})
    cfg.update(thermal_predictive={'from':str(source)},g1_sha256=report._sha(source))
    monkeypatch.setattr(run,'load_config',lambda _:cfg)
    selected=[]
    def capture(paths,*args,**kwargs):
        selected.extend(paths)
        return {'decision':'fixture','value_beyond_power':False,'per_seed':{}}
    monkeypatch.setattr(report,'build_report_from_paths',capture)
    monkeypatch.setattr(sys,'argv',['report',str(out),'--evidence',str(out/'provenance/determinism_evidence.json')])
    report.main()
    assert len(selected)==15 and all(p.parent==out/'runs' for p in selected)
    assert b not in selected


def test_each_seed_gate_accepts_only_its_exact_C_prime_records(pair):
    out,a,b,cfg=pair;proof=e12_evidence.generate_evidence(out,cfg)
    for seed in (1,2,3):
        record=report.determinism_for_seed(proof,seed)
        check={'invariants':{'1_fixture':True,'3_fixture':record},'determinism_evidence':proof}
        assert report.seed_gate(check,seed)
        wrong=deepcopy(check);wrong['invariants']['3_fixture']['per_configuration'].pop(f'packing_seed{seed}')
        assert not report.seed_gate(wrong,seed)
