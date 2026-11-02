"""Approved zero-run E11 prefix analysis and separately sealed evidence record."""

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from thermorl2.core.metrics import PROJECT
from thermorl2.experiments.provenance import sha256_file,require_assertions

E10=Path('experiments/summit/E10_c2_vertical_slice')


def compare_prefix(old,new):
    old,new=Path(old),Path(new)
    before=[line for line in (old/'decisions.jsonl').read_bytes().splitlines(keepends=True)
            if json.loads(line)['t_s'] < 7200]
    after=[line for line in (new/'decisions.jsonl').read_bytes().splitlines(keepends=True)
           if json.loads(line)['t_s'] < 7200]
    a,b=pd.read_parquet(old/'intervals.parquet'),pd.read_parquet(new/'intervals.parquet')
    a=a[a.t_s<=7200].reset_index(drop=True)
    b=b[b.t_s<=7200].reset_index(drop=True)
    error=None
    try:
        pd.testing.assert_frame_equal(a,b,check_exact=True)
        values=True
    except AssertionError as exc:
        values=False
        error=str(exc)
    return dict(result=before==after and values,decisions_byte_identical=before==after,
                interval_values_identical=values,old_decision_rows=len(before),new_decision_rows=len(after),
                old_interval_rows=len(a),new_interval_rows=len(b),interval_error=error)


def main():
    require_assertions()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_dir',type=Path)
    args=parser.parse_args()
    out=args.experiment_dir.resolve()
    cfg=yaml.safe_load((out/'config.yaml').read_text())
    inherited_path=PROJECT/E10/'provenance/rerun_1.json'
    inherited=json.loads(inherited_path.read_text())
    assert inherited['decisions_byte_identical'] and inherited['interval_values_identical'], 'accepted E10 proof must remain true'
    references={str(inherited_path.relative_to(PROJECT)):sha256_file(inherited_path)}
    prefix={}
    for policy in ('packing','power_balance'):
        old=PROJECT/E10/'runs'/f'{policy}_seed1'
        new=out/'runs'/f'{policy}_seed1'
        prefix[policy]=compare_prefix(old,new)
        for run in (old,new):
            for name in ('decisions.jsonl','intervals.parquet'):
                path=run/name
                references[str(path.relative_to(PROJECT))]=sha256_file(path)
    old_manifest=json.loads((PROJECT/E10/'runs/packing_seed1/manifest.json').read_text())
    old_workload=PROJECT/old_manifest['workload_path']
    new_workload=PROJECT/cfg['workload']['by_seed'][1]['path']
    a,b=pd.read_parquet(old_workload),pd.read_parquet(new_workload)
    try:
        pd.testing.assert_frame_equal(a,b.iloc[:len(a)].reset_index(drop=True),check_exact=True)
        workload_prefix=True
    except AssertionError:
        workload_prefix=False
    for path in (old_workload,new_workload):
        references[str(path.relative_to(PROJECT))]=sha256_file(path)
    result=workload_prefix and all(p['result'] for p in prefix.values())
    prefix_path=out/'provenance/prefix_vs_E10.json'
    with prefix_path.open('x') as target:
        target.write(json.dumps({'result':result,'workload_exact_prefix':workload_prefix,'policies':prefix,
                                 'scope':'NEW zero-run analysis; seed1 decisions t_s<7200 bytes, interval t_s<=7200 values'},indent=2,sort_keys=True)+'\n')
    ref=str(prefix_path.relative_to(PROJECT))
    references[ref]=sha256_file(prefix_path)
    items=[dict(kind='inherited_E10',scope='INHERITED: E10 packing seed1 2h same-config fresh-process rerun only',
                result=True,ref=str(inherited_path.relative_to(PROJECT)))]
    per_seed={str(seed):dict(status='inherited_not_remeasured',evidence=list(items)) for seed in (1,2,3)}
    per_seed['1']['evidence'].append(dict(kind='E11_prefix_vs_E10',
        scope='NEW: seed1 packing+power_balance 2h prefix; not full 6h E11 determinism',result=result,ref=ref))
    if not result: per_seed['1']['status']='failed'
    proof=dict(approved_scope='Bipin 2026-10-30: inherited E10 + seed1 prefix; exactly 15 runs, no reruns',
               six_hour_E11_determinism_remeasured=False,per_seed=per_seed,references_sha256=references)
    path=out/'provenance/determinism_evidence.json'
    with path.open('x') as target:
        target.write(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    with Path(str(path)+'.sha256').open('x') as target:
        target.write(sha256_file(path)+'\n')
    print(json.dumps({'prefix_result':result,'evidence':str(path),'sha256':sha256_file(path)},sort_keys=True))
    if not result: raise AssertionError('E11 prefix invariant failure; G4 INVALID pending review')


if __name__=='__main__':
    main()
