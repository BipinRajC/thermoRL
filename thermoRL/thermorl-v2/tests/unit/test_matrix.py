import json
from pathlib import Path

import pytest

from thermorl2.experiments import run_matrix
from thermorl2.raps_adapter.runner import config_for_seed


def test_seed_workload_selection_preserves_frozen_inputs():
    cfg=dict(workload=dict(kind='synthetic',rho=0.6,by_seed={1:dict(path='a',sha256='aaa'),2:dict(path='b',sha256='bbb')}))
    selected=config_for_seed(cfg,2)
    assert selected['workload']['path']=='b'
    assert selected['workload']['sha256']=='bbb'
    assert 'path' not in cfg['workload']
    with pytest.raises(KeyError): config_for_seed(cfg,3)


def test_listing_records_every_file_and_never_overwrites(tmp_path):
    out=tmp_path/'E11'
    path=out/'runs/packing_seed1'
    path.mkdir(parents=True)
    (path/'a.bin').write_bytes(b'abc')
    index=run_matrix.write_run_inventory(out)
    assert index['runs/packing_seed1/a.bin']==dict(bytes=3,sha256='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
    with pytest.raises(FileExistsError): run_matrix.write_run_inventory(out)


def test_failure_archived_with_trace_and_retry_cap(tmp_path):
    run=tmp_path/'runs/packing_seed1'
    run.mkdir(parents=True)
    (run/'failure.json').write_text('{"error":"fixture"}')
    destination=run_matrix.archive_failure(tmp_path,run,attempt=1,returncode=1)
    assert not run.exists()
    assert (destination/'failure.json').read_text()=='{"error":"fixture"}'
    trace=run_matrix.read_events(tmp_path)
    assert trace[-1]['event']=='failure_archived'
    assert trace[-1]['attempt']==1
    with pytest.raises(ValueError): run_matrix.assert_retry_allowed(tmp_path,run,2)
    run_matrix.assert_retry_allowed(tmp_path,run,1)


def test_skip_requires_same_config_hash_and_intact_files(tmp_path):
    cfg={'workload':{'path':'a','sha256':'aaa'},'horizon_h':6}
    run=tmp_path/'run'
    run.mkdir()
    (run/'manifest.json').write_text(json.dumps({'config_sha256':'wrong'}))
    assert not run_matrix.can_skip(run,cfg)


def test_orchestrator_smoke_two_subprocesses_no_fmu(tmp_path):
    # A real subprocess writes only temporary orchestration fixtures, no thermal
    # doubles or synthetic temperature artifacts in E11.
    code="from pathlib import Path; import sys; p=Path(sys.argv[1]); p.mkdir(parents=True); (p/'done').write_text('ok')"
    import sys
    jobs=[dict(policy=p,seed=1,run_dir=tmp_path/'runs'/p,
               command=[sys.executable,'-c',code,str(tmp_path/'runs'/p)])
          for p in ('packing','power_balance')]
    result=run_matrix.execute_jobs(jobs,tmp_path,workers=2,verify_runs=False)
    assert result['completed']==2
    assert all((job['run_dir']/'done').read_text()=='ok' for job in jobs)
    assert len(run_matrix.read_events(tmp_path))>=4


def test_postprocess_validation_failure_archives_completed_run(tmp_path,monkeypatch):
    import sys
    code="from pathlib import Path; import sys; p=Path(sys.argv[1]); p.mkdir(parents=True); (p/'done').write_text('ok')"
    path=tmp_path/'runs/packing_seed1'
    jobs=[dict(policy='packing',seed=1,run_dir=path,command=[sys.executable,'-c',code,str(path)])]
    def fail(_): raise AssertionError('fixture invariant failure')
    monkeypatch.setattr(run_matrix,'_verify_run',fail)
    with pytest.raises(AssertionError,match='fixture invariant'):
        run_matrix.execute_jobs(jobs,tmp_path,1)
    assert not path.exists()
    assert list((tmp_path/'provenance').glob('failed_*/packing_seed1/done'))


def test_failure_then_one_reviewed_resume_preserves_inventory(tmp_path):
    import sys
    path=tmp_path/'runs/packing_seed1'
    failed=dict(policy='packing',seed=1,run_dir=path,command=[sys.executable,'-c',
                "from pathlib import Path; import sys; p=Path(sys.argv[1]); p.mkdir(parents=True); (p/'failure').write_text('fixture'); sys.exit(1)",str(path)])
    with pytest.raises(RuntimeError,match='run failed'):
        run_matrix.execute_jobs([failed],tmp_path,1,verify_runs=False)
    before=list((tmp_path/'provenance').glob('failed_inventory_*.json'))
    assert len(before)==1
    original=before[0].read_bytes()
    success={**failed,'command':[sys.executable,'-c',
        "from pathlib import Path; import sys; p=Path(sys.argv[1]); p.mkdir(parents=True); (p/'done').write_text('ok')",str(path)]}
    result=run_matrix.execute_jobs([success],tmp_path,1,verify_runs=False,allow_retry=True)
    assert result['completed']==1
    listing=run_matrix.write_run_inventory(tmp_path)
    assert len(listing)==2 and before[0].read_bytes()==original
    assert [e['attempt'] for e in run_matrix.read_events(tmp_path) if e['event']=='started']==[1,2]


def test_all_matching_runs_skipped_without_overwriting_outputs(tmp_path,monkeypatch):
    import sys
    out=tmp_path/'E11'
    (out/'results').mkdir(parents=True)
    target=out/'results/run_files.json'
    target.write_text('{"preserved":true}')
    cfg=dict(system='summit',experiment_dir=str(out),policies=['packing','power_balance'],
             seeds=[1],workload={'path':'a','sha256':'aaa'})
    monkeypatch.setattr(run_matrix,'load_config',lambda _:cfg)
    monkeypatch.setattr(run_matrix,'can_skip',lambda *_:True)
    monkeypatch.setattr(run_matrix,'_verify_run',lambda _:None)
    def forbidden(*args,**kwargs): pytest.fail('matching runs must not launch any process')
    monkeypatch.setattr(run_matrix,'execute_jobs',forbidden)
    monkeypatch.setattr(sys,'argv',['run_matrix','--config','unused.yaml','--workers','3'])
    run_matrix.main()
    assert target.read_text()=='{"preserved":true}'
