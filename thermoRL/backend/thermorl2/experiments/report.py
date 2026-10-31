"""Offline G4 report. Frozen primary rule; secondary metrics are descriptive."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import yaml

from thermorl2.core.metrics import (PROJECT, load_run, run_metrics, invariants,
    disagreement_rate, self_reproduction_rate, max_rack_attribution)
from thermorl2.core.scorers import PowerBalance, ThermalPredictive, make_scorer
from thermorl2.experiments import plots
from thermorl2.experiments.provenance import require_assertions,process_memory

POLICIES = ('packing','node_balance','power_balance','coolest_rack','thermal_predictive')
E12_SCOPE_ID='E12_C_prime_2026_10_30'
E12_INHERITED_SCOPE='E10 synthetic packing seed1 2h only; weak cross-workload evidence'


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def _write(path,data):
    with Path(path).open('x') as out:
        out.write(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')


def g4_decision(rows):
    frame = pd.DataFrame(rows)
    assert sorted(frame.seed.unique().tolist()) == [1,2,3], 'G4 requires all 3 seeds'
    assert len(frame) == 15, 'G4 requires exactly 15 policy/seed outcomes'
    per_seed = {}
    for seed,group in frame.groupby('seed',sort=True):
        group = group.set_index('policy')
        assert group.index.is_unique and sorted(group.index) == sorted(POLICIES), 'G4 requires all 5 distinct policies in every seed'
        per_seed[str(int(seed))] = {
            'power_minus_thermal_c':float(group.loc['power_balance','maxrack_mean_c']-group.loc['thermal_predictive','maxrack_mean_c']),
            'packing_minus_thermal_c':float(group.loc['packing','maxrack_mean_c']-group.loc['thermal_predictive','maxrack_mean_c'])}
    value = all(row['power_minus_thermal_c'] >= 0.5 for row in per_seed.values())
    return {'value_beyond_power':value,'per_seed':per_seed,
            'decision':'value beyond power' if value else 'no material value on the homogeneous twin',
            'rule':'power_balance.maxrack_mean_c - thermal_predictive.maxrack_mean_c >= 0.5 C in every seed'}


def allocation_valid(run):
    """Replay actual node lifecycle, checking requests and pre-action free counts."""
    m = run.manifest
    free = set(range(m['total_nodes']))
    active = {}
    requests = run.workload.set_index('id')
    starts = 0
    for event in run.job_events:
        nodes = set(event['nodes'])
        job = event['job_id']
        if event['event'] == 'complete':
            assert active.pop(job) == nodes and free.isdisjoint(nodes), 'allocation lifecycle invariant failure'
            free.update(nodes)
        else:
            row = run.decisions[starts]
            assert event['decision_index'] == starts, 'allocation lifecycle invariant failure'
            assert (row['job_id'],row['t_s'],row['nodes']) == (job,event['t_s'],event['nodes']), 'allocation lifecycle invariant failure'
            assert len(nodes) == len(event['nodes']) == row['nodes_required'] == requests.loc[job,'nodes_required'], 'allocation lifecycle invariant failure'
            assert nodes <= free and job not in active, 'allocation lifecycle invariant failure'
            assert row['t_s'] >= np.ceil(requests.loc[job,'submit_time']), 'allocation lifecycle invariant failure'
            counts = np.bincount(np.asarray(sorted(free),dtype=int)//m['nodes_per_rack'],minlength=m['n_racks'])
            assert counts.tolist() == row['free'], 'allocation lifecycle invariant failure'
            assert set(row['racks']) == {node//m['nodes_per_rack'] for node in nodes}, 'allocation lifecycle invariant failure'
            free.difference_update(nodes)
            active[job] = nodes
            starts += 1
    assert starts == len(run.decisions) == len({r['job_id'] for r in run.decisions}), 'allocation lifecycle invariant failure'
    return True


def manifest_valid(run,require_job_events=False):
    m = run.manifest
    required = {'git','git_status_porcelain','system','fmu_sha256','workload_path',
        'workload_sha256','config','config_sha256','policy','seed','backend',
        'thermal_predictive_params','rack_kw_reference','power_tick_s','fmu_steps',
        'warmup_used_s','t_idle_c','raps_s','fmu_s','total_s','environment',
        'decisions_sha256','intervals_sha256','decision_rows','decision_latency_rows',
        'decision_latency_sha256','decision_latency_span'}
    assert required <= m.keys() and m['backend'] == 'fmu' and m['warmup_used_s'] == 7200.0, 'run manifest/provenance validation failure'
    assert hashlib.sha256(json.dumps(m['config'],sort_keys=True).encode()).hexdigest() == m['config_sha256'], 'run manifest/provenance validation failure'
    assert m['thermal_predictive_params'] == m['config']['thermal_predictive_params'], 'run manifest/provenance validation failure'
    assert set(m['thermal_predictive_params']) == {'a_c','b_c_per_kw','tau_s','horizon_s'}, 'run manifest/provenance validation failure'
    workload = Path(m['workload_path'])
    if not workload.is_absolute():
        workload = PROJECT/workload
    assert _sha(workload) == m['workload_sha256'], 'run manifest/provenance validation failure'
    assert _sha(run.path/'decisions.jsonl') == m['decisions_sha256'], 'run manifest/provenance validation failure'
    assert _sha(run.path/'intervals.parquet') == m['intervals_sha256'], 'run manifest/provenance validation failure'
    assert _sha(run.path/'provenance/decision_latency.jsonl') == m['decision_latency_sha256'], 'run manifest/provenance validation failure'
    assert len(run.decisions) == len(run.timings) == m['decision_rows'] == m['decision_latency_rows'], 'run manifest/provenance validation failure'
    keys = {'t_s','job_id','nodes_required','policy','rule','racks','nodes','job_kw',
            'scores','t_c','committed_kw','free','t_obs_s','latency_us'}
    for i,(row,timing) in enumerate(zip(run.decisions,run.timings)):
        assert set(row) == keys and row['latency_us'] is None and type(row['t_obs_s']) is float, 'run manifest/provenance validation failure'
        assert set(timing) == {'decision_index','job_id','t_s','latency_ns'}, 'run manifest/provenance validation failure'
        assert (i,row['job_id'],row['t_s']) == (timing['decision_index'],timing['job_id'],timing['t_s']), 'run manifest/provenance validation failure'
        assert type(timing['latency_ns']) is int and timing['latency_ns'] >= 0, 'run manifest/provenance validation failure'
    assert np.isfinite(run.intervals.t_c).all(), 'run manifest/provenance validation failure'
    if require_job_events:
        path = run.path/'provenance/job_events.jsonl'
        assert path.is_file() and 'job_events_sha256' in m, 'G4 requires job_events.jsonl and its manifest SHA'
        assert _sha(path) == m['job_events_sha256'], 'job_events SHA mismatch'
    return True


def validate_expected(run,cfg):
    """Compare execution identity and exact config with preregistered inputs."""
    from thermorl2.raps_adapter.systems import get_system
    m=run.manifest
    seed=m['seed']
    assert seed in cfg['seeds'] and m['policy'] in cfg['policies'], 'executed config differs from preregistration'
    assert run.name == f"{m['policy']}_seed{seed}", 'executed config differs from preregistration'
    expected=deepcopy(cfg)
    if 'by_seed' in expected['workload']:
        by_seed=expected['workload']['by_seed']
        entry=by_seed.get(seed,by_seed.get(str(seed)))
        assert entry is not None, 'executed config differs from preregistration'
        expected['workload'].update(entry)
    assert m['config_sha256'] == hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest(), 'executed config differs from preregistration'
    assert m['config'] == json.loads(json.dumps(expected)), 'executed config differs from preregistration'
    assert m['system'] == cfg['system'], 'executed config differs from preregistration'
    assert m['fmu_sha256'] == get_system(cfg['system']).fmu_sha256, 'executed config differs from preregistration'
    assert m['workload_sha256'] == expected['workload']['sha256'], 'executed config differs from preregistration'
    assert m['workload_path'] == expected['workload']['path'], 'executed config differs from preregistration'
    assert m['warmup_used_s'] == cfg['warmup_s'], 'executed config differs from preregistration'
    assert m['backend_elapsed_s'] == cfg['horizon_h']*3600, 'executed config differs from preregistration'
    return True


def validate_seed(runs,determinism_evidence=None,expected_config=None,require_job_events=False):
    base = invariants(runs)
    errors = {}
    allocation,manifests,power = True,True,True
    reconciliation = {}
    for run in runs:
        for key,check in [('allocation',allocation_valid),('manifest',manifest_valid)]:
            try:
                check(run,require_job_events=require_job_events) if key == 'manifest' else check(run)
                if key == 'manifest' and expected_config is not None:
                    validate_expected(run,expected_config)
            except (AssertionError,KeyError,ValueError,IndexError,FileNotFoundError,TypeError) as exc:
                errors[f'{run.name}_{key}'] = f'{type(exc).__name__}: {exc}'
                if key == 'allocation': allocation=False
                else: manifests=False
        grouped = run.intervals.groupby('t_s')
        error = float(np.abs(grouped.kw.sum()-grouped.it_kw_total.first()).max())
        reconciliation[run.name] = error
        power &= error <= 1e-6 and run.manifest['power_reconciliation_max_abs_kw'] <= 1e-6
    seed=str(runs[0].manifest['seed'])
    deterministic = determinism_for_seed(determinism_evidence or {},seed)
    flags = {
        '1_it_kw_and_start_times_identical':base['it_kw_identical'] and base['start_times_identical'],
        '2_exact_distinct_free_nodes':allocation,
        '3_decisions_byte_identical_and_interval_values_identical':deterministic,
        '4_rack_power_sums_reconcile':bool(power),
        '5_independent_step_count_and_clock':base['fmu_steps_ok'],
        '6_manifests_and_joinable_ledgers_complete':manifests}
    return {'invariants':flags,'cross_policy':base,'errors':errors,
            'power_reconciliation_max_abs_kw':reconciliation,'determinism_evidence':determinism_evidence}


def approved_determinism(record,seed):
    """Accept only Bipin's inherited scope plus the measured seed-1 prefix."""
    kinds=['inherited_E10','E11_prefix_vs_E10'] if int(seed)==1 else ['inherited_E10']
    items=record.get('evidence',[])
    return (record.get('status')=='inherited_not_remeasured' and
            [item.get('kind') for item in items]==kinds and
            all(item.get('result') is True and item.get('scope') and item.get('ref') for item in items))


def approved_e12_determinism(proof):
    if proof.get('scope_id')!=E12_SCOPE_ID or proof.get('fallback_to_A_prime') is not False:return False
    records=proof.get('per_configuration',{})
    expected={f'{p}_seed{s}' for s in (1,2,3) for p in POLICIES}
    if set(records)!=expected:return False
    for name,record in records.items():
        items=record.get('evidence',[])
        direct=name=='thermal_predictive_seed1'
        if record.get('status')!=('verified_E12' if direct else 'inherited_not_remeasured'):return False
        if len(items)!=1:return False
        item=items[0]
        if item.get('kind')!=('E12_full_rerun_6h' if direct else 'inherited_E10'):return False
        if item.get('result') is not True or not item.get('scope') or not item.get('ref'):return False
        if not direct and item['scope']!=E12_INHERITED_SCOPE:return False
    return True


def determinism_for_seed(proof,seed):
    if proof.get('scope_id')==E12_SCOPE_ID:
        records=proof.get('per_configuration',{})
        return {'scope_id':E12_SCOPE_ID,'per_configuration':
            {f'{p}_seed{seed}':records.get(f'{p}_seed{seed}',{'status':'missing','evidence':[]}) for p in POLICIES}}
    return proof.get('per_seed',{}).get(str(seed),{'status':'missing','evidence':[]})


def seed_gate(check,seed):
    proof=check.get('determinism_evidence') or {}
    scope=proof.get('scope_id')
    if scope==E12_SCOPE_ID:
        return approved_e12_determinism(proof) and all(
            value==determinism_for_seed(proof,seed) if key.startswith('3_') else value is True
            for key,value in check['invariants'].items())
    if scope is not None:return False
    return all(approved_determinism(value,seed) if key.startswith('3_') else value is True
               for key,value in check['invariants'].items())


def _summarize_runs(runs,eval_start_s,t_hot_c,with_diagnostics=True):
    rows,diagnostics,attribution = [],{},{}
    for run in runs:
        row = run_metrics(run,eval_start_s,t_hot_c)
        rows.append(dict(name=run.name,policy=run.manifest['policy'],seed=run.manifest['seed'],**row))
        if with_diagnostics:
            params = run.manifest['thermal_predictive_params']
            diagnostics[run.name] = {
                'power_vs_thermal_disagreement_rate':disagreement_rate(run.decisions,PowerBalance(),ThermalPredictive(**params)),
                'self_reproduction_rate':self_reproduction_rate(run.decisions,make_scorer(run.manifest['policy'],params if run.manifest['policy']=='thermal_predictive' else {})),
                'context':'both scorers use the same six-decimal logged context; self reproduction is separate'}
            attribution[run.name] = max_rack_attribution(run,eval_start_s)
    return rows,diagnostics,attribution


def _publish_report(rows,diagnostics,attribution,checks,selected,out,eval_start_s,grid,g4,animations,determinism_evidence):
    seeds=sorted({r.manifest['seed'] for r in selected})
    pd.DataFrame(rows).to_csv(out/'results/metrics.csv',index=False)
    plots.metrics_table(rows,out/'results/metrics.md')
    _write(out/'results/max_rack_attribution.json',attribution)
    _write(out/'results/decision_diagnostics.json',diagnostics)
    decision = g4_decision(rows) if g4 else {'scope':'ledger analysis; no G4 decision'}
    _write(out/'results/decision.json',decision)
    result = {**decision,'runs':{row['name']:row for row in rows},'diagnostics':diagnostics,
              'evaluation_window':f'{eval_start_s} < t_s <= episode horizon; right endpoints',
              'invariants':checks,'determinism_evidence_sha256':(determinism_evidence or {}).get('sha256')}
    _write(out/'results/summary.json',result)
    low = min(float(r.intervals.t_c.min()) for r in selected)
    high = max(float(r.intervals.t_c.max()) for r in selected)
    plots.heatmaps(selected,out/f'plots/heatmaps_seed{seeds[0]}.png',low,high)
    plots.timeseries(selected,out/f'plots/timeseries_seed{seeds[0]}.png')
    if animations:
        by_policy = {r.manifest['policy']:r for r in selected}
        for base in ('packing','power_balance'):
            plots.animate_grid([by_policy[base],by_policy['thermal_predictive']],
                out/f'plots/anim_{base}_vs_thermal_predictive_seed{seeds[0]}.gif',grid)
    return result



def build_report(runs,out,eval_start_s,t_hot_c,grid,g4=True,animations=True,determinism_evidence=None,expected_config=None):
    require_assertions()
    out = Path(out)
    if (out/'results/summary.json').exists():
        raise FileExistsError('report exists; never overwrite')
    for sub in ('results','plots','provenance'):
        (out/sub).mkdir(parents=True,exist_ok=True)
    seeds = sorted({r.manifest['seed'] for r in runs})
    if g4:
        assert expected_config is not None, 'G4 requires preregistered expected configuration'
        assert seeds == [1,2,3], 'G4 requires all 3 seeds'
        assert all(sorted(r.manifest['policy'] for r in runs if r.manifest['seed']==s) == sorted(POLICIES) for s in seeds), 'G4 requires all 5 policies per seed'
    checks = {str(seed):validate_seed([r for r in runs if r.manifest['seed']==seed],determinism_evidence,expected_config,require_job_events=g4) for seed in seeds}
    _write(out/'results/invariants.json',checks)
    if g4 and not all(seed_gate(check,seed) for seed,check in checks.items()):
        _write(out/'results/summary.json',{'decision':'INVALID: invariant failure','invariants':checks})
        raise AssertionError('G4 invariant failure; stop before interpreting policy outcomes')
    rows,diagnostics,attribution=_summarize_runs(runs,eval_start_s,t_hot_c)
    selected=[r for r in runs if r.manifest['seed']==seeds[0]]
    return _publish_report(rows,diagnostics,attribution,checks,selected,out,eval_start_s,grid,g4,animations,determinism_evidence)


def _collect_seed(paths,eval_start_s,t_hot_c,proof,cfg,metrics_only):
    # No Run object escapes this function; each seed is released before the next.
    runs=[load_run(path) for path in paths]
    check=validate_seed(runs,proof,cfg,require_job_events=True)
    if not seed_gate(check,runs[0].manifest['seed']):
        return check,[],{},{}
    rows,diagnostics,attribution=_summarize_runs(runs,eval_start_s,t_hot_c,with_diagnostics=not metrics_only)
    return check,rows,diagnostics,attribution


def build_report_from_paths(paths,out,eval_start_s,t_hot_c,grid,determinism_evidence,expected_config,
                            metrics_only=False,animations=True):
    """Metric-neutral G4 loading, capped at one five-policy seed in memory.

    metrics_only is for offline D5 regeneration into a fresh scratch directory.
    It performs the same invariant checks and run_metrics calculations without
    recalculating counterfactuals or rendering figures. No simulation is run.
    """
    require_assertions()
    paths=list(map(Path,paths));out=Path(out)
    metadata=[(path,json.loads((path/'manifest.json').read_text())) for path in paths]
    assert expected_config is not None, 'preregistered configuration required'
    assert sorted(expected_config['seeds'])==[1,2,3], 'G4 requires all 3 seeds'
    assert len(paths)==15 and len(set(paths))==15, 'G4 requires 15 distinct run directories'
    for seed in expected_config['seeds']:
        names=[m['policy'] for _,m in metadata if m['seed']==seed]
        assert sorted(names)==sorted(POLICIES), 'G4 requires all 5 policies in every seed'
    if (out/'results/summary.json').exists() or (out/'results/metrics.csv').exists():
        raise FileExistsError('report exists; never overwrite')
    for sub in ('results','plots','provenance'):
        (out/sub).mkdir(parents=True,exist_ok=True)
    rows=[];diagnostics={};attribution={};checks={}
    for seed in expected_config['seeds']:
        group=[path for path,m in metadata if m['seed']==seed]
        check,seed_rows,seed_diagnostics,seed_attribution=_collect_seed(group,eval_start_s,t_hot_c,
            determinism_evidence,expected_config,metrics_only)
        checks[str(seed)]=check
        if not seed_gate(check,seed):
            _write(out/'results/invariants.json',checks)
            _write(out/'results/summary.json',{'decision':'INVALID: invariant failure','invariants':checks})
            raise AssertionError('G4 invariant failure; stop before interpreting policy outcomes')
        rows.extend(seed_rows);diagnostics.update(seed_diagnostics);attribution.update(seed_attribution)
    _write(out/'results/invariants.json',checks)
    _write(out/'provenance/report_loading.json',{'mode':'one five-policy seed at a time',
        'maximum_loaded_runs':5,'metrics_only':metrics_only})
    if metrics_only:
        pd.DataFrame(rows).to_csv(out/'results/metrics.csv',index=False)
        return {'scope':'metrics-only regeneration; no new simulation','rows':len(rows),'metrics_csv':str(out/'results/metrics.csv')}
    selected=[load_run(path) for path,m in metadata if m['seed']==expected_config['seeds'][0]]
    return _publish_report(rows,diagnostics,attribution,checks,selected,out,eval_start_s,grid,True,animations,determinism_evidence)



def main():
    require_assertions()
    report_start=perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_dir',type=Path)
    parser.add_argument('--output-dir',type=Path,help='fresh offline report destination; input config remains unchanged')
    parser.add_argument('--metrics-only',action='store_true',help='D5 offline metric regeneration without plots/counterfactual diagnostics')
    parser.add_argument('--evidence',type=Path,required=True,help='separate evidence JSON with .sha256 sidecar')
    args = parser.parse_args()
    from thermorl2.experiments.run import load_config
    cfg = load_config(args.experiment_dir/'config.yaml')
    evidence_path = args.evidence
    digest=Path(str(evidence_path)+'.sha256').read_text().strip()
    assert _sha(evidence_path) == digest, 'determinism evidence SHA mismatch'
    evidence = {**json.loads(evidence_path.read_text()),'path':str(evidence_path),'sha256':digest}
    for ref,digest in evidence.get('references_sha256',{}).items():
        assert _sha(PROJECT/ref)==digest, f'evidence reference SHA mismatch: {ref}'
    source=Path(cfg['thermal_predictive']['from'])
    if not source.is_absolute(): source=PROJECT/source
    assert _sha(source)==cfg['g1_sha256'], 'pinned G1 summary SHA mismatch'
    t_hot_c=json.loads(source.read_text())['t_hot_c']
    from thermorl2.raps_adapter.systems import get_system
    grid=get_system(cfg['system']).grid
    paths = [args.experiment_dir/'runs'/f'{p}_seed{s}' for s in cfg['seeds'] for p in cfg['policies']]
    result = build_report_from_paths(paths,args.output_dir or args.experiment_dir,3600,t_hot_c,grid,determinism_evidence=evidence,expected_config=cfg,metrics_only=args.metrics_only)
    runtime_path=(args.output_dir or args.experiment_dir)/'provenance/report_runtime.json'
    runtime_path.parent.mkdir(parents=True,exist_ok=True)
    _write(runtime_path,{'main_wall_s':perf_counter()-report_start,'process_memory':process_memory(),
        'scope':'offline report main after imports, including validation, metrics and requested rendering; memory is process lifetime peak'})
    print(json.dumps(result if args.metrics_only else {k:result[k] for k in ('decision','value_beyond_power','per_seed')},indent=2))


if __name__ == '__main__':
    main()
