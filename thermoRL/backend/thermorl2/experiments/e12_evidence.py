"""E12 C′: one guarded fresh-process TP seed1 rerun, exact scoped evidence."""

import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import pandas as pd

from thermorl2.core.metrics import PROJECT,load_run
from thermorl2.experiments.provenance import sha256_file,require_assertions,process_memory
from thermorl2.experiments.report import (POLICIES,E12_SCOPE_ID,E12_INHERITED_SCOPE,
    manifest_valid,validate_expected)


class ComparisonPreconditionError(ValueError):
    pass


def _ref(path):
    return os.path.relpath(Path(path).resolve(),PROJECT)


def _json_x(path,data):
    with Path(path).open('x') as out:out.write(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')


def _files(path):
    return [Path(path)/name for name in ('manifest.json','decisions.jsonl','intervals.parquet',
        'provenance/decision_latency.jsonl','provenance/job_events.jsonl','provenance/thermal_publications.jsonl')]


def compare_full_rerun(original,rerun,cfg):
    """Refuse unmatched experiments before comparing their measured outputs."""
    require_assertions()
    original,rerun=Path(original),Path(rerun)
    try:
        for path in _files(original)+_files(rerun):
            if not path.is_file():raise ValueError(f'missing comparison file: {path}')
        a,b=load_run(original),load_run(rerun)
        for run in (a,b):
            assert manifest_valid(run,require_job_events=True), 'manifest invalid'
            assert validate_expected(run,cfg), 'expected config invalid'
            m=run.manifest
            assert m['policy']=='thermal_predictive' and m['seed']==1, 'C-prime verifies TP seed1 only'
            assert m['warmup_used_s']==7200 and m['fmu_steps']==2160 and m['backend_elapsed_s']==21600, 'warm-up/step/clock mismatch'
        ma,mb=a.manifest,b.manifest
        for key in ('config_sha256','workload_sha256','workload_meta_sha256','fmu_sha256','source_sha256','environment'):
            assert ma[key]==mb[key], f'exact precondition mismatch: {key}'
        assert ma['git']['sha']==mb['git']['sha'], 'exact precondition mismatch: git.sha'
        for m in (ma,mb):
            work=Path(m['workload_path'])
            if not work.is_absolute():work=PROJECT/work
            sidecar=Path(str(work)+'.meta.json')
            assert sha256_file(sidecar)==m['workload_meta_sha256']==m['config']['workload']['meta_sha256'], 'meta_sha256 mismatch'
    except (AssertionError,KeyError,ValueError,TypeError,IndexError,FileNotFoundError) as exc:
        raise ComparisonPreconditionError(f'C-prime preconditions refused: {exc}') from exc
    decisions_equal=(original/'decisions.jsonl').read_bytes()==(rerun/'decisions.jsonl').read_bytes()
    error=None
    try:
        pd.testing.assert_frame_equal(a.intervals,b.intervals,check_exact=True)
        values_equal=True
    except AssertionError as exc:
        values_equal=False;error=str(exc)
    refs={_ref(path):sha256_file(path) for path in _files(original)+_files(rerun)}
    work=Path(ma['workload_path'])
    if not work.is_absolute():work=PROJECT/work
    for path in (work,Path(str(work)+'.meta.json')):refs[_ref(path)]=sha256_file(path)
    return {'result':bool(decisions_equal and values_equal),'preconditions_passed':True,
        'decisions_byte_identical':decisions_equal,'interval_values_identical':values_equal,
        'interval_difference':error,'timing_ledger_excluded_from_comparison':True,
        'meta_sha256_field':'manifest workload_meta_sha256, checked against pinned config sidecar meta_sha256',
        'information':{'interval_file_bytes_identical':sha256_file(original/'intervals.parquet')==sha256_file(rerun/'intervals.parquet'),
            'job_events_byte_identical':(original/'provenance/job_events.jsonl').read_bytes()==(rerun/'provenance/job_events.jsonl').read_bytes(),
            'thermal_publications_byte_identical':(original/'provenance/thermal_publications.jsonl').read_bytes()==(rerun/'provenance/thermal_publications.jsonl').read_bytes()},
        'references_sha256':refs}


def generate_evidence(out,cfg):
    out=Path(out);prov=out/'provenance';prov.mkdir(parents=True,exist_ok=True)
    target=prov/'determinism_evidence.json';seal=Path(str(target)+'.sha256');comparison_path=prov/'full_rerun_comparison.json'
    for path in (target,seal,comparison_path):
        if path.exists():raise FileExistsError(f'never overwrite evidence: {path}')
    original=out/'runs/thermal_predictive_seed1';rerun=prov/'rerun_1/runs/thermal_predictive_seed1'
    try:
        comparison=compare_full_rerun(original,rerun,cfg)
    except ComparisonPreconditionError as exc:
        comparison={'result':False,'preconditions_passed':False,'refusal':str(exc),
                    'references_sha256':{_ref(p):sha256_file(p) for p in _files(original)+_files(rerun) if p.is_file()}}
    _json_x(comparison_path,comparison)
    inherited=PROJECT/'experiments/summit/E10_c2_vertical_slice/provenance/rerun_1.json'
    old=json.loads(inherited.read_text())
    assert old['decisions_byte_identical'] and old['interval_values_identical'], 'inherited E10 evidence must remain accepted'
    refs={**comparison['references_sha256'],_ref(comparison_path):sha256_file(comparison_path),_ref(inherited):sha256_file(inherited)}
    records={}
    for seed in (1,2,3):
        for policy in POLICIES:
            name=f'{policy}_seed{seed}';direct=name=='thermal_predictive_seed1'
            records[name]={'status':('verified_E12' if comparison['result'] else 'failed') if direct else 'inherited_not_remeasured',
                'evidence':[{'kind':'E12_full_rerun_6h' if direct else 'inherited_E10',
                    'scope':'thermal_predictive seed1 6h, same-config fresh-process rerun only' if direct else E12_INHERITED_SCOPE,
                    'result':bool(comparison['result']) if direct else True,
                    'ref':_ref(comparison_path) if direct else _ref(inherited)}]}
    proof={'scope_id':E12_SCOPE_ID,'fallback_to_A_prime':False,'per_configuration':records,
           'references_sha256':refs,'scope':'direct verification is TP seed1 only; the other14 primary configurations are inherited and unrepeated'}
    _json_x(target,proof)
    with seal.open('x') as dest:dest.write(sha256_file(target)+'\n')
    return proof


def write_rerun_inventory(base):
    base=Path(base);target=base/'run_files.json'
    if target.exists():raise FileExistsError(target)
    listing={str(p.relative_to(base)):{'bytes':p.stat().st_size,'sha256':sha256_file(p)}
             for p in sorted(base.rglob('*')) if p.is_file() and p!=target}
    _json_x(target,listing)
    return listing


def _matrix_complete(out,cfg):
    from thermorl2.experiments.run_matrix import lightweight_invariants,primary_attempt_summary
    runtime=json.loads((out/'results/matrix_runtime.json').read_text())
    assert runtime['completed']==15 and runtime['workers']==3, 'primary matrix must complete first'
    assert {(r['policy'],r['seed']) for r in runtime['processes']}=={(p,s) for s in (1,2,3) for p in POLICIES}, 'primary matrix identities incomplete'
    accounting=primary_attempt_summary(out,POLICIES,(1,2,3))
    assert accounting['completed']==15, 'exactly15 successful primary configurations required'
    assert accounting['attempts_started']==runtime.get('attempts_started',15), 'primary attempt accounting mismatch'
    for seed in (1,2,3):
        check=lightweight_invariants([out/'runs'/f'{p}_seed{seed}' for p in POLICIES])
        assert check['it_kw_identical'] and check['start_times_identical'] and check['fmu_steps_ok'], f'primary seed check failed: {seed}'


def run_rerun(cfg,config_path,out):
    require_assertions();out=Path(out);base=out/'provenance/rerun_1'
    if base.exists():raise FileExistsError(f'never overwrite rerun directory: {base}')
    _matrix_complete(out,cfg)
    primary_inventory=out/'results/run_files.json';primary_hash=sha256_file(primary_inventory)
    base.mkdir(parents=True,exist_ok=False)
    path=base/'runs/thermal_predictive_seed1';log=base/'console_thermal_predictive_seed1.log';journal=base/'journal.jsonl'
    command=[sys.executable,'-m','thermorl2.experiments.run','--config',str(config_path),
             '--policy','thermal_predictive','--seed','1','--run-dir',str(path)]
    def event(kind,**fields):
        with journal.open('a') as dest:dest.write(json.dumps({'event':kind,'utc':datetime.now(timezone.utc).isoformat(),**fields},sort_keys=True)+'\n')
    event('rerun_started',command=command,primary_inventory_sha256=primary_hash)
    start=perf_counter()
    try:
        with log.open('x') as handle:
            process=subprocess.run(command,cwd=PROJECT,stdout=handle,stderr=subprocess.STDOUT)
        if process.returncode!=0:raise RuntimeError(f'fresh-process rerun crashed, exit {process.returncode}; STOP pending review')
        from thermorl2.experiments.run_matrix import _verify_run
        _verify_run(path)
        with (base/'manifest.json').open('xb') as dest:dest.write((path/'manifest.json').read_bytes())
        assert sha256_file(primary_inventory)==primary_hash, 'primary inventory changed during rerun'
        event('rerun_completed',process_wall_s=perf_counter()-start,process_memory=process_memory())
        write_rerun_inventory(base)
    except Exception as exc:
        event('rerun_failed',failure_kind='memory_error' if isinstance(exc,MemoryError) else 'rerun_failure',message=str(exc))
        if not (base/'run_files.json').exists():write_rerun_inventory(base)
        raise
    return path


def main():
    require_assertions()
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['rerun','generate'])
    parser.add_argument('--config',type=Path,required=True);args=parser.parse_args()
    from thermorl2.experiments.run import load_config
    cfg=load_config(args.config);out=Path(cfg['experiment_dir'].format(system=cfg['system']))
    if args.action=='rerun':
        print(run_rerun(cfg,args.config,out),flush=True)
    else:
        proof=generate_evidence(out,cfg)
        ok=proof['per_configuration']['thermal_predictive_seed1']['status']=='verified_E12'
        print(json.dumps({'C_prime_verified_TP_seed1':ok,'evidence':str(out/'provenance/determinism_evidence.json')},sort_keys=True),flush=True)
        if not ok:raise AssertionError('C-prime failed: G4 INVALID pending review; no A-prime fallback')


if __name__=='__main__':main()
