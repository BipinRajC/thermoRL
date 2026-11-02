"""Builds a tiny, self-consistent synthetic experiment directory for replay_v1 exporter tests.

3 racks x 4 ticks (10 s), five policies, a few seeds; ledger formats mirror the real ones
(intervals.parquet, decisions.jsonl, provenance/job_events.jsonl, manifest.json, results/*).
Everything is generated here from closed-form numbers; no simulation of any kind.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

POLICIES = ('packing', 'node_balance', 'power_balance', 'coolest_rack', 'thermal_predictive')
N_RACKS, N_TICKS, NODES_PER_RACK = 3, 4, 18
EVAL_START_S = 20
EXPERIMENT_ID = 'EFIX_synthetic'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tc_array(policy_index, seed):
    k = np.arange(N_TICKS)[:, None]
    r = np.arange(N_RACKS)[None, :]
    tc = 40.0 + 0.5 * k + 0.1 * r + 0.013 * policy_index + 0.0071 * seed
    tc[2, 0] = tc[2, 2]  # exact tie for the maximum at tick 2: lowest rack index wins
    return tc


def kw_array(policy_index):
    k = np.arange(N_TICKS)[:, None]
    r = np.arange(N_RACKS)[None, :]
    base = 10.0 + r + 0.5 * k
    return np.roll(base, policy_index, axis=1)  # different placement, identical IT power


def free_array(policy_index):
    k = np.arange(N_TICKS)[:, None]
    r = np.arange(N_RACKS)[None, :]
    return 18 - r - ((k + policy_index) % 2)


def decision_rows(policy, seed):
    def vec(offset):
        return [round(5.0 - i * 0.25 + offset, 6) for i in range(N_RACKS)]
    rows = []
    for i, (t, job, nodes, rule, racks) in enumerate(
            [(1, 0, [0], 'single', [0]), (12, 1, [17, 18], 'span', [0, 1]), (25, 2, [36], 'single', [2])]):
        scores = vec(0.0)
        if i == 2:
            scores = [3.0, 3.0, 2.0]  # chosen rack 2 is not the logged best; two racks tie at the top
        rows.append({'t_s': t, 'job_id': job, 'nodes_required': len(nodes), 'policy': policy,
                     'rule': rule, 'racks': racks, 'nodes': nodes, 'job_kw': 1.5 + i,
                     'scores': scores, 't_c': vec(35.0), 'committed_kw': vec(5.0),
                     'free': [18 - r - i for r in range(N_RACKS)], 't_obs_s': float(10 * (t // 10)),
                     'latency_us': None})
    return rows


def event_rows():
    return [{'decision_index': 0, 'event': 'start', 'job_id': 0, 'nodes': [0], 't_s': 1},
            {'decision_index': 1, 'event': 'start', 'job_id': 1, 'nodes': [17, 18], 't_s': 12},
            {'event': 'complete', 'job_id': 0, 'nodes': [0], 't_s': 12},
            {'decision_index': 2, 'event': 'start', 'job_id': 2, 'nodes': [36], 't_s': 25}]


def build_experiment(root, seeds=(1, 2), experiment_id=EXPERIMENT_ID, selected_attempts=None):
    exp = Path(root) / experiment_id
    (exp / 'results').mkdir(parents=True)
    (exp / 'provenance').mkdir()
    run_files, metrics, scale = {}, [], {}
    for seed in seeds:
        lows, highs = [], []
        for p_index, policy in enumerate(POLICIES):
            run = exp / 'runs' / f'{policy}_seed{seed}'
            (run / 'provenance').mkdir(parents=True)
            tc, kw, free = tc_array(p_index, seed), kw_array(p_index), free_array(p_index)
            rows = []
            for k in range(N_TICKS):
                for r in range(N_RACKS):
                    rows.append({'t_s': 10.0 * (k + 1), 'rack': r, 'kw': kw[k, r], 't_c': tc[k, r],
                                 'pump_kw': 1.0 + 0.1 * r, 'free': int(free[k, r]),
                                 'it_kw_total': float(kw[k].sum()), 'n_running': k, 'n_queued': 2 * k,
                                 'scenario_active': False})
            pd.DataFrame(rows).to_parquet(run / 'intervals.parquet')
            with (run / 'decisions.jsonl').open('w') as f:
                for row in decision_rows(policy, seed):
                    f.write(json.dumps(row) + '\n')
            with (run / 'provenance/job_events.jsonl').open('w') as f:
                for row in event_rows():
                    f.write(json.dumps(row) + '\n')
            manifest = {'policy': policy, 'seed': seed, 'system': 'summit', 'n_racks': N_RACKS,
                        'nodes_per_rack': NODES_PER_RACK, 'power_tick_s': 10, 'power_ticks': N_TICKS,
                        'decision_rows': 3, 'idle_kw': 10.0, 'peak_kw': 20.0,
                        'fmu_sha256': 'f' * 64, 'git': {'sha': 'a' * 40, 'dirty': False},
                        'config': {'scenario': {'name': 'nominal'}, 'horizon_h': N_TICKS * 10 / 3600},
                        'decisions_sha256': sha(run / 'decisions.jsonl'),
                        'intervals_sha256': sha(run / 'intervals.parquet'),
                        'job_events_sha256': sha(run / 'provenance/job_events.jsonl')}
            (run / 'manifest.json').write_text(json.dumps(manifest))
            for rel in ('manifest.json', 'decisions.jsonl', 'intervals.parquet', 'provenance/job_events.jsonl'):
                run_files[f'runs/{run.name}/{rel}'] = {'bytes': (run / rel).stat().st_size,
                                                       'sha256': sha(run / rel)}
            window = tc[np.arange(1, N_TICKS + 1) * 10 > EVAL_START_S]
            metrics.append({'name': run.name, 'policy': policy, 'seed': seed,
                            'maxrack_mean_c': float(window.max(axis=1).mean()),
                            'jobs_started': 3, 'coolant_over_70_racks': '[]'})
            lows.append(tc.min())
            highs.append(tc.max())
        scale[seed] = [float(min(lows)), float(max(highs))]
    cols = ['name', 'policy', 'seed', 'maxrack_mean_c', 'jobs_started', 'coolant_over_70_racks']
    (exp / 'results/metrics.csv').write_text(
        ','.join(cols) + '\n' + '\n'.join(','.join(str(m[c]) for c in cols) for m in metrics) + '\n')
    (exp / 'results/decision.json').write_text(json.dumps({
        'decision': 'no material value on the homogeneous twin',
        'per_seed': {str(s): {'packing_minus_thermal_c': 0.25, 'power_minus_thermal_c': 0.125} for s in seeds},
        'rule': 'power_balance.maxrack_mean_c - thermal_predictive.maxrack_mean_c >= 0.5 C in every seed',
        'value_beyond_power': False}))
    attempts = selected_attempts or {}
    (exp / 'results/matrix_runtime.json').write_text(json.dumps({'processes': [
        {'policy': pol, 'seed': s, 'selected_attempt': attempts.get((pol, s), 1)}
        for s in seeds for pol in POLICIES]}))
    (exp / 'results/run_files.json').write_text(json.dumps(run_files))
    (exp / 'provenance/demo_asset_inventory.json').write_text(
        json.dumps({'temperature_colour_scale_c': scale[seeds[0]]}))
    (exp / 'provenance/determinism_evidence.json').write_text(json.dumps({'per_configuration': {
        f'{pol}_seed{s}': {'status': 'verified_E12' if (pol, s) == ('thermal_predictive', 1)
                           else 'inherited_not_remeasured'} for s in seeds for pol in POLICIES}}))
    return exp, scale
