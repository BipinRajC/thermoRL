"""Bounded subprocess matrix; preserve failures and immutable run file hashes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter, sleep

import numpy as np

from thermorl2.experiments.provenance import sha256_file
from thermorl2.experiments.run import PROJECT, load_config
from thermorl2.raps_adapter.runner import config_for_seed


def read_events(out):
    path=Path(out)/'provenance/matrix_events.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _event(out,**fields):
    path=Path(out)/'provenance/matrix_events.jsonl'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as target:
        target.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),**fields},sort_keys=True)+'\n')


def assert_retry_allowed(out,run_dir,retry):
    if retry not in (0,1):
        raise ValueError('at most one retry is allowed')
    previous=[e for e in read_events(out) if e.get('run_dir')==str(run_dir) and e['event']=='started']
    if len(previous) > 1:
        raise ValueError('retry cap exhausted')


def archive_failure(out,run_dir,attempt,returncode):
    run_dir=Path(run_dir)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    destination=Path(out)/'provenance'/f'failed_{stamp}'/run_dir.name
    destination.parent.mkdir(parents=True,exist_ok=False)
    if run_dir.exists():
        run_dir.rename(destination)
    else:
        destination.mkdir()
    _event(out,event='failure_archived',run_dir=str(run_dir),archive=str(destination),
           attempt=attempt,returncode=returncode)
    return destination


def write_run_inventory(out,relative_target='results/run_files.json'):
    out=Path(out)
    target=out/relative_target
    target.parent.mkdir(parents=True,exist_ok=True)
    paths=list((out/'runs').rglob('*')) if (out/'runs').exists() else []
    for failed in (out/'provenance').glob('failed_*'):
        paths.extend(failed.rglob('*'))
    listing={str(path.relative_to(out)):{'bytes':path.stat().st_size,'sha256':sha256_file(path)}
             for path in sorted(paths) if path.is_file()}
    with target.open('x') as dest:
        dest.write(json.dumps(listing,indent=2,sort_keys=True)+'\n')
    return listing


def can_skip(run_dir,cfg):
    path=Path(run_dir)
    manifest=path/'manifest.json'
    if not manifest.exists():
        return False
    m=json.loads(manifest.read_text())
    digest=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    if m.get('config_sha256') != digest:
        return False
    files={'decisions.jsonl':'decisions_sha256','intervals.parquet':'intervals_sha256',
           'provenance/decision_latency.jsonl':'decision_latency_sha256'}
    return all((path/name).is_file() and sha256_file(path/name)==m.get(key) for name,key in files.items())


def _verify_run(path):
    from thermorl2.core.metrics import load_run
    from thermorl2.experiments.report import allocation_valid,manifest_valid
    from thermorl2.core.metrics import invariants
    run=load_run(path)
    assert allocation_valid(run) and manifest_valid(run)
    assert invariants([run])['fmu_steps_ok']
    g=run.intervals.groupby('t_s')
    assert float(np.abs(g.kw.sum()-g.it_kw_total.first()).max()) <= 1e-6
    assert np.isfinite(run.intervals.t_c).all()


def execute_jobs(jobs,out,workers,verify_runs=True,seed_check=None,allow_retry=False):
    """No automatic retries: FMU, invariant or unexplained failures stop all work.

    Failure directories are archived before returning non-zero. A later retry
    requires reviewed external-failure recovery, is recorded, and is capped at
    one. This operational support never overrides scientific stop conditions.
    """
    out=Path(out)
    assert workers >= 1
    pending=list(enumerate(jobs))
    active={}
    completed=[]
    start=perf_counter()
    first_wave_ids=set(range(min(workers,len(jobs))))
    first_wave_written=False
    try:
        while pending or active:
            while pending and len(active)<workers:
                index,job=pending.pop(0)
                run_dir=Path(job['run_dir'])
                if run_dir.exists():
                    raise FileExistsError(f'never overwrite existing run: {run_dir}')
                prior=sum(e['event']=='started' and e.get('run_dir')==str(run_dir) for e in read_events(out))
                if prior and not allow_retry:
                    raise RuntimeError('prior failed attempt: explicit reviewed --retry-failed required')
                assert_retry_allowed(out,run_dir,prior)
                log=out/'provenance'/f"console_{job['policy']}_seed{job['seed']}_attempt{prior+1}.log"
                log.parent.mkdir(parents=True,exist_ok=True)
                handle=log.open('x')
                process=subprocess.Popen(job['command'],cwd=PROJECT,stdout=handle,stderr=subprocess.STDOUT)
                active[index]=(process,handle,job,perf_counter(),prior+1)
                _event(out,event='started',run_dir=str(run_dir),policy=job['policy'],seed=job['seed'],
                       attempt=prior+1,pid=process.pid,command=job['command'],log=str(log))
                print(f"START {job['policy']} seed {job['seed']}, pid={process.pid}",flush=True)
            for index,actor in list(active.items()):
                process,handle,job,started,attempt=actor
                code=process.poll()
                if code is None:
                    continue
                handle.close()
                del active[index]
                wall=perf_counter()-started
                if code != 0:
                    archive_failure(out,job['run_dir'],attempt,code)
                    raise RuntimeError(f"run failed (exit {code}): {job['policy']} seed {job['seed']}; stop, no automatic retry")
                if verify_runs:
                    try:
                        _verify_run(job['run_dir'])
                    except BaseException:
                        archive_failure(out,job['run_dir'],attempt,code)
                        raise
                row=dict(index=index,policy=job['policy'],seed=job['seed'],process_wall_s=wall,run_dir=str(job['run_dir']))
                completed.append(row)
                _event(out,event='completed',**row)
                print(f"DONE {job['policy']} seed {job['seed']}: {wall:.2f} s",flush=True)
                if seed_check is not None:
                    seed_check(job['seed'])
            if not first_wave_written and first_wave_ids <= {r['index'] for r in completed}:
                path=out/'results/first_wave.json'
                if path.exists():
                    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
                    path=out/'provenance'/f'first_wave_resume_{stamp}.json'
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('x') as dest:
                    dest.write(json.dumps([r for r in completed if r['index'] in first_wave_ids],indent=2,sort_keys=True)+'\n')
                first_wave_written=True
            if pending or active:
                sleep(0.5)
    except BaseException:
        for process,handle,job,_,attempt in active.values():
            if process.poll() is None:
                process.terminate()
        for process,handle,job,_,attempt in active.values():
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            handle.close()
            archive_failure(out,job['run_dir'],attempt,process.returncode)
        _event(out,event='matrix_stopped',completed=len(completed))
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        write_run_inventory(out,f'provenance/failed_inventory_{stamp}.json')
        raise
    return {'completed':len(completed),'processes':completed,'matrix_wall_s':perf_counter()-start,'workers':workers}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--policies')
    parser.add_argument('--seeds')
    parser.add_argument('--workers',type=int,default=max(1,min(6,(os.cpu_count() or 1)-2)))
    parser.add_argument('--retry-failed',action='store_true',help='only after reviewed external-failure recovery; never bypass a scientific stop')
    args=parser.parse_args()
    cfg=load_config(args.config)
    policies=args.policies.split(',') if args.policies else cfg['policies']
    seeds=list(map(int,args.seeds.split(','))) if args.seeds else cfg['seeds']
    assert set(policies)<=set(cfg['policies']) and set(seeds)<=set(cfg['seeds'])
    out=Path(cfg['experiment_dir'].format(system=cfg['system']))
    jobs=[]
    for seed in seeds:
        selected=config_for_seed(cfg,seed)
        for policy in policies:
            path=out/'runs'/f'{policy}_seed{seed}'
            if can_skip(path,selected):
                _verify_run(path)
                _event(out,event='skipped_matching_config',run_dir=str(path),policy=policy,seed=seed)
                continue
            jobs.append(dict(policy=policy,seed=seed,run_dir=path,command=[sys.executable,'-m',
                'thermorl2.experiments.run','--config',str(args.config.resolve()),'--policy',policy,
                '--seed',str(seed),'--run-dir',str(path)]))
    checked=set()
    def seed_check(seed):
        paths=[out/'runs'/f'{p}_seed{seed}' for p in policies]
        if seed in checked or not all((p/'manifest.json').exists() for p in paths):
            return
        from thermorl2.core.metrics import load_run,invariants
        check=invariants([load_run(p) for p in paths])
        assert check['it_kw_identical'] and check['start_times_identical'] and check['fmu_steps_ok'], f'cross-policy invariant failure, seed {seed}: {check}'
        checked.add(seed)
        _event(out,event='seed_cross_policy_invariants_passed',seed=seed,checks=check)
    if not jobs:
        print('All runs match config and intact ledgers; no simulations launched.',flush=True)
        return
    result=execute_jobs(jobs,out,args.workers,seed_check=seed_check,allow_retry=args.retry_failed)
    for seed in seeds:
        seed_check(seed)
    write_run_inventory(out)
    with (out/'results/matrix_runtime.json').open('x') as target:
        target.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':
    main()
