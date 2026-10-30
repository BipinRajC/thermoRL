import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from thermorl2.experiments import report, run_matrix


def test_report_main_uses_pinned_g1_registry_and_separate_evidence(tmp_path,monkeypatch):
    from thermorl2.experiments import run
    g1=tmp_path/'g1.json'
    g1.write_text(json.dumps({'t_hot_c':63.3}))
    cfg={'system':'summit','policies':['packing'],'seeds':[1],
         'thermal_predictive':{'from':str(g1)},'g1_sha256':report._sha(g1)}
    evidence=tmp_path/'evidence.json'
    evidence.write_text('{"per_seed":{}}')
    Path(str(evidence)+'.sha256').write_text(report._sha(evidence)+'\n')
    monkeypatch.setattr(run,'load_config',lambda _:cfg)
    monkeypatch.setattr(report,'load_run',lambda _:object())
    captured={}
    def build(*args,**kwargs):
        captured.update(args=args,kwargs=kwargs)
        return dict(decision='fixture',value_beyond_power=False,per_seed={})
    monkeypatch.setattr(report,'build_report',build)
    monkeypatch.setattr(sys,'argv',['report',str(tmp_path),'--evidence',str(evidence)])
    report.main()
    assert captured['args'][3]==63.3
    assert captured['args'][4]==(13,20)
    assert captured['kwargs']['determinism_evidence']['sha256']==report._sha(evidence)


def test_all_job_preflight_happens_before_any_subprocess(tmp_path,monkeypatch):
    existing=tmp_path/'runs/b'
    existing.mkdir(parents=True)
    jobs=[dict(policy=p,seed=1,run_dir=tmp_path/'runs'/p,command=['unused']) for p in ('a','b')]
    def forbidden(*args,**kwargs): pytest.fail('preflight must precede every process launch')
    monkeypatch.setattr(run_matrix.subprocess,'Popen',forbidden)
    with pytest.raises(FileExistsError): run_matrix.execute_jobs(jobs,tmp_path,3)


def test_non_scientific_failure_drains_inflight_and_does_not_launch_pending(tmp_path):
    def job(policy,code):
        path=tmp_path/'runs'/policy
        return dict(policy=policy,seed=1,run_dir=path,command=[sys.executable,'-c',code,str(path)])
    jobs=[job('fails',"import sys; from pathlib import Path; p=Path(sys.argv[1]); p.mkdir(parents=True); sys.exit(1)"),
          job('healthy',"import sys,time; from pathlib import Path; time.sleep(1); p=Path(sys.argv[1]); p.mkdir(parents=True); (p/'done').write_text('ok')"),
          job('pending',"raise RuntimeError('must not launch')")]
    with pytest.raises(RuntimeError): run_matrix.execute_jobs(jobs,tmp_path,2,verify_runs=False)
    assert (tmp_path/'runs/healthy/done').read_text()=='ok'
    assert not (tmp_path/'runs/pending').exists()
    failures=[e for e in run_matrix.read_events(tmp_path) if e['event'] in ('failure_archived','matrix_stopped')]
    assert failures and all(e['failure_kind'] and e['message'] for e in failures)


def test_scientific_failure_cannot_be_retried_without_reviewed_override(tmp_path):
    path=tmp_path/'runs/packing_seed1'
    path.mkdir(parents=True)
    run_matrix.archive_failure(tmp_path,path,1,1,failure_kind='fmu_error',message='fixture solver error')
    with pytest.raises(ValueError,match='scientific'):
        run_matrix.assert_retry_allowed(tmp_path,path,1)


def test_inventory_includes_console_logs_and_matrix_journal(tmp_path):
    prov=tmp_path/'provenance'
    prov.mkdir()
    (prov/'console_packing_seed1_attempt1.log').write_text('fixture')
    (prov/'matrix_events.jsonl').write_text('{}\n')
    listing=run_matrix.write_run_inventory(tmp_path)
    assert 'provenance/console_packing_seed1_attempt1.log' in listing
    assert 'provenance/matrix_events.jsonl' in listing


@pytest.mark.parametrize('module',['thermorl2.experiments.run','thermorl2.experiments.run_matrix','thermorl2.experiments.report'])
def test_optimized_python_refused_before_work(module):
    process=subprocess.run([sys.executable,'-O','-m',module,'--help'],capture_output=True,text=True)
    assert process.returncode!=0
    assert 'optimized Python' in process.stderr


def test_g4_decision_rejects_incomplete_matrix():
    rows=[dict(policy=p,seed=1,maxrack_mean_c=50) for p in report.POLICIES]
    with pytest.raises(AssertionError,match='3 seeds'):
        report.g4_decision(rows)


def test_g4_requires_job_event_file():
    root=Path(__file__).resolve().parents[2]/'experiments/summit/E10_c2_vertical_slice/runs/packing_seed1'
    run=report.load_run(root)
    with pytest.raises(AssertionError,match='job_events'):
        report.manifest_valid(run,require_job_events=True)


def test_later_scientific_failure_escalates_a_draining_stop(tmp_path):
    def job(policy,code):
        path=tmp_path/'runs'/policy
        return dict(policy=policy,seed=1,run_dir=path,command=[sys.executable,'-c',code,str(path)])
    jobs=[job('io',"import sys; from pathlib import Path; p=Path(sys.argv[1]); p.mkdir(parents=True); sys.exit(1)"),
          job('fmu',"import sys,time,json; from pathlib import Path; time.sleep(.6); p=Path(sys.argv[1]); (p/'provenance').mkdir(parents=True); (p/'provenance/failure.json').write_text(json.dumps(dict(failure_kind='fmu_error',message='fixture solver error'))); sys.exit(1)")]
    with pytest.raises(RuntimeError): run_matrix.execute_jobs(jobs,tmp_path,2,verify_runs=False)
    assert run_matrix.read_events(tmp_path)[-1]['failure_kind']=='fmu_error'


def test_nested_failed_archives_are_gitignored():
    path='thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/failed_fixture/packing_seed1/decisions.jsonl'
    process=subprocess.run(['git','check-ignore','-q',path],cwd=Path(__file__).resolve().parents[4])
    assert process.returncode==0
