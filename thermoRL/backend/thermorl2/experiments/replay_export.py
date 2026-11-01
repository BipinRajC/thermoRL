"""Read-only replay_v1 exporter: hash-verified, compact copies of recorded ledgers.

Reads existing run ledgers (manifest, intervals.parquet, decisions.jsonl, job_events.jsonl) and
frozen results; writes only new files under <experiment>/exports/replay_v1/ (opened with mode 'x').
Nothing is simulated, scored or recomputed: arrays are the ledger values (float32/uint8 casts),
per-tick maxima are plain reductions, and decision context is the logged six-decimal vectors.
Contract: docs/superpowers/specs/2026-11-01-replay-v1-contract.md.
"""

import argparse
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
from time import perf_counter

import numpy as np
import pandas as pd

SCHEMA = 'thermorl.replay.v1'
EMPTY_RACK = 65535
TOP_K = 5
ROWS_PER_DECISION = TOP_K + 1
PULSE_WINDOW_S = 30
CANDIDATE_DTYPE = np.dtype([('rack', '<u2'), ('score', '<f4'), ('t_c', '<f4'),
                            ('committed_kw', '<f4'), ('free', 'u1')])


def candidate_rows(scores, chosen_rack, k=TOP_K):
    """Top-k racks by logged score (ties to the lower rack index), then the chosen rack if absent."""
    order = np.argsort(-np.asarray(scores, dtype=float), kind='stable')[:k]
    rows = [int(r) for r in order]
    rows.append(EMPTY_RACK if chosen_rack in rows else int(chosen_rack))
    return rows


def tie_stats(scores, chosen_rack):
    scores = np.asarray(scores, dtype=float)
    best = scores.max()
    return int((scores == best).sum()), bool(scores[chosen_rack] == best)


def event_racks(nodes, nodes_per_rack):
    return sorted({int(n) // int(nodes_per_rack) for n in nodes})


def pulse_bounds(t_s, window_s=PULSE_WINDOW_S):
    """(lo exclusive, hi inclusive) RAPS seconds whose starts are marked at displayed time t_s."""
    return max(-1, t_s - window_s), t_s


def racks_started_in(events, lo, hi):
    racks = set()
    offsets = events['rack_offsets']
    for i, (kind, t) in enumerate(zip(events['kind'], events['raps_t_s'])):
        if kind == 0 and lo < t <= hi:
            racks.update(events['racks'][offsets[i]:offsets[i + 1]])
    return racks


def colormap_lut():
    from matplotlib import colormaps
    from matplotlib.colors import to_hex
    cmap = colormaps['inferno']
    return [to_hex(cmap(i / 255), keep_alpha=False).lower() for i in range(256)]


class DecisionColumns:
    """Columnar decision context built one logged line at a time (streaming)."""

    def __init__(self, n_racks):
        self.n_racks = int(n_racks)
        self.cols = {key: [] for key in ('raps_t_s', 'job_id', 'nodes_required', 'rule', 'job_kw',
                                         't_obs_s', 'n_ties_at_logged_best', 'chosen_is_logged_best')}
        self.chosen_offsets, self.chosen_racks = [0], []
        self._records = bytearray()

    def __len__(self):
        return len(self.cols['raps_t_s'])

    def add(self, row):
        n = self.n_racks
        for key in ('scores', 't_c', 'committed_kw', 'free'):
            if len(row[key]) != n:
                raise ValueError(f'decision {len(self)}: {key} length {len(row[key])} != n_racks {n}')
        t = row['t_s']
        if type(t) is not int:
            raise ValueError(f'decision {len(self)}: t_s must be an integer RAPS second')
        if self.cols['raps_t_s'] and t < self.cols['raps_t_s'][-1]:
            raise ValueError(f'decision {len(self)}: raps_t_s is not non-decreasing')
        chosen = [int(r) for r in row['racks']]
        if not chosen or not all(0 <= r < n for r in chosen):
            raise ValueError(f'decision {len(self)}: chosen racks out of range')
        scores = np.asarray(row['scores'], dtype=float)
        ties, best = tie_stats(scores, chosen[0])
        ranks = candidate_rows(scores, chosen[0])
        record = np.zeros(ROWS_PER_DECISION, dtype=CANDIDATE_DTYPE)
        record['rack'] = EMPTY_RACK
        record['score'] = record['t_c'] = record['committed_kw'] = np.nan
        for i, rack in enumerate(ranks):
            if rack == EMPTY_RACK:
                continue
            free = row['free'][rack]
            if not 0 <= free <= 255:
                raise ValueError(f'decision {len(self)}: free nodes out of range')
            record[i] = (rack, scores[rack], row['t_c'][rack], row['committed_kw'][rack], free)
        self._records += record.tobytes()
        for key, value in (('raps_t_s', t), ('job_id', int(row['job_id'])),
                           ('nodes_required', int(row['nodes_required'])), ('rule', row['rule']),
                           ('job_kw', float(row['job_kw'])), ('t_obs_s', float(row['t_obs_s'])),
                           ('n_ties_at_logged_best', ties), ('chosen_is_logged_best', best)):
            self.cols[key].append(value)
        self.chosen_racks.extend(chosen)
        self.chosen_offsets.append(len(self.chosen_racks))

    def as_json(self):
        c = self.cols
        return {'decision_index': list(range(len(self))), 'raps_t_s': c['raps_t_s'],
                'job_id': c['job_id'], 'nodes_required': c['nodes_required'], 'rule': c['rule'],
                'job_kw': c['job_kw'], 't_obs_s': c['t_obs_s'], 'chosen_offsets': self.chosen_offsets,
                'chosen_racks': self.chosen_racks,
                'n_ties_at_logged_best': c['n_ties_at_logged_best'],
                'chosen_is_logged_best': c['chosen_is_logged_best']}

    def candidates_bytes(self):
        return bytes(self._records)


# ---------------------------------------------------------------- contract constants

SYSTEM_LABEL = 'Summit POWER9 cooling FMU (modelled)'
SCENARIO = 'nominal (290 K)'
SCALE_POLICIES = ('packing', 'node_balance', 'power_balance', 'coolest_rack', 'thermal_predictive')
UNAVAILABLE_FIELDS = ['PUE', 'carbon', 'SLO', 'emergency', 'dual_prices', 'THI_counterfactual',
                      'regret', 'energy_savings']
COMPARISONS = [{'id': 'pb_vs_tp', 'left': 'power_balance', 'right': 'thermal_predictive', 'default': True},
               {'id': 'packing_vs_tp', 'left': 'packing', 'right': 'thermal_predictive'}]
TICK_COLUMNS = ['t_s', 'it_kw_total', 'n_running', 'n_queued', 'maxrack_c', 'minrack_c',
                'argmax_rack', 'pump_kw_sum']
GRID_COLS = 20
FILE_LIMIT_BYTES = 25_000_000
EXPERIMENT_LIMIT_BYTES = 100_000_000
SCALE_TOLERANCE = 1e-6
MAXRACK_TOLERANCE = 1e-9
F32_TOLERANCE = 5e-6
KW_TOLERANCE = 1e-6
STRINGS = {
    'interval_semantics': 'Rack power, free nodes and job counts are RAPS inputs at t − 10 s, held over '
                          'the 10 s interval ending at t; coolant temperature is the FMU output at the '
                          'end of that interval (t).',
    's2': 'published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it '
          '(≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision '
          'information; identical for all policies.',
    'precision_note': 'Logged six-decimal context. Live decisions used full precision; near-ties below '
                      'logging precision occur (thermal_predictive reproduces from logged context ≈ 94.8 % '
                      'in E11 and ≈ 97.7 % in E12). This view shows logged values only; it does not '
                      'reconstruct or rescore decisions.',
    'pulse_rule': 'Rings mark racks that received a job start in the 30 s ending at the displayed time '
                  '(RAPS start time). A placement\'s power first appears in the rack power of the following '
                  '10 s interval. Rings are not a cooling effect.',
}
RULE = ('power_balance − thermal_predictive time-mean max-rack coolant over 3600 < t ≤ 21600 s '
        'must be ≥ 0.5 °C in every seed')
REPRODUCIBILITY_SCOPE = (
    'Fresh-process reproducibility was verified for E10 packing seed 1 (2 h), for E11 seed-1 packing and '
    'power_balance over the first 2 h (exact prefix), and for E12 thermal_predictive seed 1 (6 h, '
    'byte-identical). No other configuration was directly repeated; no cross-machine portability is claimed.')
E11_STATEMENT = ('E11 (synthetic): no material value beyond power balancing (PB−TP +0.342, −0.147, −0.071 °C). '
                 'Packing ≈ thermal_predictive on the primary metric (packing−TP +0.08, −0.11, +0.28 °C); '
                 'no consistent primary ordering.')
E12_STATEMENT = ('In E12 (small, low-density, bursty Alibaba-derived jobs), thermal_predictive had the lowest '
                 'and packing the highest time-mean max-rack coolant temperature in all three seeds '
                 '(PB−TP 0.08–0.18 °C; packing−TP 0.35–0.44 °C). This is below the preregistered 0.5 °C '
                 'materiality threshold, rests on about two independent workload conditions (seed 3 ≈ seed 2 '
                 'shifted 33 s), and is descriptive only.')


@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    short: str
    workload_label: str
    workload_note: str
    seed_notes: dict
    experiment_statement: str
    eval_start_s: int = 3600
    verified_runs: frozenset = field(default_factory=frozenset)


EXPERIMENTS = {
    'E11_g4_synthetic': ExperimentSpec(
        'E11_g4_synthetic', 'E11', 'Synthetic',
        'Generated synthetic workload; 1–32-node jobs, high power density',
        {1: 'seed 1 of 3', 2: 'seed 2 of 3', 3: 'seed 3 of 3'}, E11_STATEMENT),
    'E12_g4_alibaba': ExperimentSpec(
        'E12_g4_alibaba', 'E12', 'Alibaba-derived',
        'Alibaba GPU 2023 (openb, default variant); small 1–2-node, low-density, bursty jobs',
        {1: 'seed 1 of 3', 2: 'seed 2 of 3',
         3: 'seed 3 of 3 — ≈ seed 2 shifted 33 s; about two independent workload conditions in E12'},
        E12_STATEMENT, verified_runs=frozenset({('thermal_predictive', 1)})),
}


# ---------------------------------------------------------------- small helpers

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1 << 22), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(obj, indent=None):
    kwargs = {'indent': indent} if indent else {'separators': (',', ':')}
    return (json.dumps(obj, allow_nan=False, ensure_ascii=False, **kwargs) + '\n').encode('utf-8')


def _write_new(path, data):
    with open(path, 'xb') as target:
        target.write(data)
    return {'bytes': len(data), 'sha256': sha256_bytes(data)}


def _read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _number(text):
    if re.fullmatch(r'[+-]?\d+', text):
        return int(text)
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value):
        raise ValueError(f'non-finite metrics value {text!r}')
    return value


def parse_metrics(path):
    """Every row of metrics.csv, in order; numeric columns parsed, other columns (except name/policy) omitted."""
    rows = []
    with Path(path).open(newline='') as source:
        for raw in csv.DictReader(source):
            row = {'name': raw['name'], 'policy': raw['policy']}
            for key, text in raw.items():
                if key in row or text is None or text == '':
                    continue
                value = _number(text)
                if value is not None:
                    row[key] = value
            rows.append(row)
    return rows


class _RawLedgers:
    """Raw ledger access with SHA-256 verification against results/run_files.json (read-only)."""

    def __init__(self, experiment_dir):
        self.dir = Path(experiment_dir)
        self.inventory = _read_json(self.dir / 'results/run_files.json')
        self._verified = {}

    def path(self, rel):
        return self.dir / rel

    def verify(self, rel):
        if rel not in self._verified:
            entry = self.inventory.get(rel)
            if entry is None:
                raise ValueError(f'{rel}: not listed in results/run_files.json')
            path = self.path(rel)
            if not path.is_file():
                raise ValueError(f'{rel}: raw ledger is missing')
            if path.stat().st_size != entry['bytes']:
                raise ValueError(f'{rel}: size differs from results/run_files.json')
            digest = sha256_file(path)
            if digest != entry['sha256']:
                raise ValueError(f'{rel}: sha256 differs from results/run_files.json')
            self._verified[rel] = digest
        return self._verified[rel]


def _run_rel(policy, seed, name):
    return f'runs/{policy}_seed{seed}/{name}'


_INTERVAL_COLUMNS = ['t_s', 'rack', 'kw', 't_c', 'pump_kw', 'free', 'it_kw_total', 'n_running', 'n_queued']


def _load_intervals(path, n_ticks, n_racks, tick_s, columns=None):
    frame = pd.read_parquet(path, columns=columns or _INTERVAL_COLUMNS)
    if len(frame) != n_ticks * n_racks:
        raise ValueError(f'{path}: expected {n_ticks * n_racks} interval rows, found {len(frame)}')
    shape = (n_ticks, n_racks)
    out = {}
    for name in frame.columns:
        out[name] = frame[name].to_numpy().reshape(shape)
    if 't_s' in out:
        expected = np.repeat(tick_s * (np.arange(n_ticks) + 1.0), n_racks).reshape(shape)
        if not np.array_equal(out['t_s'], expected):
            raise ValueError(f'{path}: t_s is not the contiguous endpoint grid {tick_s}..{tick_s * n_ticks}')
    if 'rack' in out and not np.array_equal(out['rack'], np.tile(np.arange(n_racks), (n_ticks, 1))):
        raise ValueError(f'{path}: racks are not ordered 0..{n_racks - 1} within every tick')
    return out


def order_events(rows, nodes_per_rack):
    events = []
    for row in rows:
        if row['event'] not in ('start', 'complete'):
            raise ValueError(f"unknown job event {row['event']!r}")
        start = row['event'] == 'start'
        events.append({'kind': 0 if start else 1, 't': int(row['t_s']), 'job_id': int(row['job_id']),
                       'decision_index': int(row['decision_index']) if start else -1,
                       'racks': event_racks(row['nodes'], nodes_per_rack)})
    events.sort(key=lambda e: (e['t'], 0 if e['kind'] == 1 else 1, e['decision_index'], e['job_id']))
    return events


def events_columns(events):
    offsets, racks = [0], []
    for event in events:
        racks.extend(event['racks'])
        offsets.append(len(racks))
    return {'kind': [e['kind'] for e in events], 'raps_t_s': [e['t'] for e in events],
            'job_id': [e['job_id'] for e in events], 'decision_index': [e['decision_index'] for e in events],
            'rack_offsets': offsets, 'racks': racks}


# ---------------------------------------------------------------- per-run export

def _stream_decisions(path, n_racks, policy):
    columns = DecisionColumns(n_racks)
    with Path(path).open(encoding='utf-8') as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            if row['policy'] != policy:
                raise ValueError(f'{path}: decision {len(columns)} belongs to policy {row["policy"]!r}')
            columns.add(row)
    return columns


def _frozen_row(metrics, policy, seed):
    name = f'{policy}_seed{seed}'
    rows = [m for m in metrics if m['name'] == name]
    if len(rows) != 1:
        raise ValueError(f'metrics.csv must hold exactly one row for {name}')
    return rows[0]


def _runtime_attempt(runtime, policy, seed):
    for entry in runtime['processes']:
        if entry['policy'] == policy and entry['seed'] == seed:
            return int(entry.get('selected_attempt', 1))
    raise ValueError(f'matrix_runtime.json has no process entry for {policy}_seed{seed}')


def _c_prime_status(evidence, spec, policy, seed):
    if 'per_configuration' in evidence:
        status = evidence['per_configuration'][f'{policy}_seed{seed}']['status']
    else:
        status = evidence['per_seed'][str(seed)]['status']
    verified = (policy, seed) in spec.verified_runs
    if status != ('verified_E12' if verified else 'inherited_not_remeasured'):
        raise ValueError(f'{policy}_seed{seed}: unexpected determinism status {status!r}')
    return status


def _export_run(raw, out_dir, spec, policy, seed, ctx):
    """Write one run directory; returns its run.json record."""
    manifest_rel = _run_rel(policy, seed, 'manifest.json')
    manifest_sha = raw.verify(manifest_rel)
    manifest = _read_json(raw.path(manifest_rel))
    n_ticks, n_racks, tick_s = int(manifest['power_ticks']), int(manifest['n_racks']), int(manifest['power_tick_s'])
    if manifest['policy'] != policy or manifest['seed'] != seed or manifest['system'] != 'summit':
        raise ValueError(f'{manifest_rel}: manifest identity differs from {policy}_seed{seed}')
    if manifest['config']['scenario']['name'] != 'nominal':
        raise ValueError(f'{manifest_rel}: only the nominal scenario is exported')
    source = {'manifest_sha256': manifest_sha}
    for key, name in (('decisions_sha256', 'decisions.jsonl'), ('intervals_sha256', 'intervals.parquet'),
                      ('job_events_sha256', 'provenance/job_events.jsonl')):
        digest = raw.verify(_run_rel(policy, seed, name))
        if digest != manifest[key]:
            raise ValueError(f'{policy}_seed{seed}: {key} differs from the manifest value')
        source[key] = digest

    data = _load_intervals(raw.path(_run_rel(policy, seed, 'intervals.parquet')), n_ticks, n_racks, tick_s)
    for key in ('it_kw_total', 'n_running', 'n_queued'):
        if not (data[key] == data[key][:, :1]).all():
            raise ValueError(f'{policy}_seed{seed}: {key} differs across racks within a tick')
    t_c = data['t_c']
    maxrack, minrack = t_c.max(axis=1), t_c.min(axis=1)
    t_s = data['t_s'][:, 0]
    window = (t_s > spec.eval_start_s) & (t_s <= t_s[-1])
    mean_c = float(np.mean(maxrack[window]))
    row = _frozen_row(ctx['metrics'], policy, seed)
    if abs(mean_c - row['maxrack_mean_c']) > MAXRACK_TOLERANCE:
        raise ValueError(f'{policy}_seed{seed}: maxrack_mean_c {mean_c!r} differs from metrics.csv '
                         f'{row["maxrack_mean_c"]!r}')
    tick = np.column_stack([t_s, data['it_kw_total'][:, 0], data['n_running'][:, 0], data['n_queued'][:, 0],
                            maxrack, minrack, t_c.argmax(axis=1), data['pump_kw'].sum(axis=1)]).astype('<f8')
    free = data['free']
    if free.min() < 0 or free.max() > 255:
        raise ValueError(f'{policy}_seed{seed}: free nodes outside uint8')

    decisions = _stream_decisions(raw.path(_run_rel(policy, seed, 'decisions.jsonl')), n_racks, policy)
    if len(decisions) != manifest['decision_rows']:
        raise ValueError(f'{policy}_seed{seed}: {len(decisions)} decisions != manifest decision_rows')
    job_lines = Path(raw.path(_run_rel(policy, seed, 'provenance/job_events.jsonl'))).read_text().splitlines()
    ordered = order_events([json.loads(line) for line in job_lines if line.strip()],
                           manifest['nodes_per_rack'])
    starts = sorted((e for e in ordered if e['kind'] == 0), key=lambda e: e['decision_index'])
    if [e['decision_index'] for e in starts] != list(range(len(decisions))):
        raise ValueError(f'{policy}_seed{seed}: start events do not match the decision count')
    if [e['job_id'] for e in starts] != decisions.cols['job_id'] or \
            [e['t'] for e in starts] != decisions.cols['raps_t_s']:
        raise ValueError(f'{policy}_seed{seed}: start events disagree with decisions (job id or RAPS second)')
    events = events_columns(ordered)

    run_dir = out_dir / 'runs' / f'{policy}_seed{seed}'
    run_dir.mkdir(parents=True)
    files = {}

    def put(key, name, data_bytes, dtype, **extra):
        files[key] = {'path': name, 'dtype': dtype, **extra, **_write_new(run_dir / name, data_bytes)}
    shape = [n_ticks, n_racks]
    put('rack_tc', 'rack_tc.f32', t_c.astype('<f4').tobytes(), 'float32', shape=shape)
    put('rack_kw', 'rack_kw.f32', data['kw'].astype('<f4').tobytes(), 'float32', shape=shape)
    put('rack_free', 'rack_free.u8', free.astype('u1').tobytes(), 'uint8', shape=shape)
    put('tick', 'tick.f64', tick.tobytes(), 'float64', shape=[n_ticks, len(TICK_COLUMNS)],
        columns=TICK_COLUMNS)
    put('events', 'events.json', _json_bytes(events), 'json')
    put('decisions', 'decisions.json', _json_bytes(decisions.as_json()), 'json')
    put('candidates', 'candidates.bin', decisions.candidates_bytes(), 'record',
        record_bytes=CANDIDATE_DTYPE.itemsize, rows_per_decision=ROWS_PER_DECISION,
        fields=[['rack', 'uint16'], ['score', 'float32'], ['t_c', 'float32'],
                ['committed_kw', 'float32'], ['free', 'uint8']], empty_rack=EMPTY_RACK)
    record = {'schema': SCHEMA, 'run_id': f'{spec.id}:{policy}_seed{seed}', 'experiment_id': spec.id,
              'policy': policy, 'seed': seed, 'launch_sha': manifest['git']['sha'],
              'selected_attempt': _runtime_attempt(ctx['runtime'], policy, seed),
              'c_prime_status': _c_prime_status(ctx['evidence'], spec, policy, seed),
              'n_ticks': n_ticks, 'n_racks': n_racks, 'n_decisions': len(decisions),
              'n_events': len(ordered), 'source': source, 'metrics': row, 'files': files,
              'precision_note': STRINGS['precision_note'],
              'empty_candidate_values': 'score, t_c and committed_kw are NaN and free is 0 where rack == empty_rack'}
    _write_new(run_dir / 'run.json', _json_bytes(record, indent=2))
    return record, manifest, {'tick_s': tick_s, 'n_ticks': n_ticks, 'n_racks': n_racks,
                              'idle_kw': manifest['idle_kw'], 'peak_kw': manifest['peak_kw'],
                              'fmu_sha256': manifest['fmu_sha256']}


def seed_colour_scales(raw, spec, seeds, tick_s, n_ticks, n_racks):
    """Min/max float64 t_c over all five policies of each seed (hash-verified raw parquet)."""
    scales = {}
    for seed in seeds:
        lows, highs = [], []
        for policy in SCALE_POLICIES:
            rel = _run_rel(policy, seed, 'intervals.parquet')
            raw.verify(rel)
            t_c = _load_intervals(raw.path(rel), n_ticks, n_racks, tick_s, columns=['t_s', 'rack', 't_c'])['t_c']
            lows.append(float(t_c.min()))
            highs.append(float(t_c.max()))
        scales[seed] = {'min': min(lows), 'max': max(highs),
                        'scope': 'all five policies of this seed'}
    return scales


def _check_recorded_scale(raw, scales):
    if 1 not in scales:
        return None
    recorded = _read_json(raw.dir / 'provenance/demo_asset_inventory.json')['temperature_colour_scale_c']
    diff = max(abs(scales[1]['min'] - recorded[0]), abs(scales[1]['max'] - recorded[1]))
    if diff > SCALE_TOLERANCE:
        raise ValueError(f'seed-1 colour scale {scales[1]["min"]!r}..{scales[1]["max"]!r} differs from the '
                         f'recorded demo scale {recorded!r} by {diff!r}')
    return diff


def _frozen_outcome(raw, spec, metrics):
    decision_path = raw.dir / 'results/decision.json'
    decision = _read_json(decision_path)
    return {'schema': SCHEMA, 'experiment_id': spec.id, 'headline': decision['decision'], 'rule': RULE,
            'decision': decision, 'decision_sha256': sha256_file(decision_path),
            'metrics_sha256': sha256_file(raw.dir / 'results/metrics.csv'), 'metrics': metrics,
            'experiment_statement': spec.experiment_statement, 'reproducibility_scope': REPRODUCIBILITY_SCOPE}


def _catalog(spec, policies, seeds, scales, shared, source_sha, generated_utc):
    n_racks = shared['n_racks']
    last_t = shared['tick_s'] * shared['n_ticks']
    return {
        'schema': SCHEMA,
        'experiment': {'id': spec.id, 'short': spec.short, 'workload_label': spec.workload_label,
                       'workload_note': spec.workload_note, 'system_label': SYSTEM_LABEL,
                       'scenario': SCENARIO, 'fmu_sha256': shared['fmu_sha256']},
        'grid': {'rows': math.ceil(n_racks / GRID_COLS), 'cols': GRID_COLS, 'n_racks': n_racks,
                 'nodes_per_rack': shared['nodes_per_rack'],
                 'mapping': 'row = r // 20, col = r % 20, origin lower-left', 'schematic_not_floor_plan': True},
        'time': {'tick_s': shared['tick_s'], 'n_ticks': shared['n_ticks'], 'first_t_s': shared['tick_s'],
                 'last_t_s': last_t, 'eval_start_exclusive_s': spec.eval_start_s,
                 'eval_end_inclusive_s': last_t, 'pulse_window_s': PULSE_WINDOW_S},
        'rack_kw_range': {'idle_kw': shared['idle_kw'], 'peak_kw': shared['peak_kw'],
                          'basis': 'RAPS loss-inclusive rack power, from run manifests'},
        'colormap': {'name': 'inferno', 'lut': colormap_lut()},
        'seeds': [{'seed': seed, 'note': spec.seed_notes[seed], 'colour_scale_c': scales[seed],
                   'runs': {p: f'runs/{p}_seed{seed}/run.json' for p in policies}} for seed in seeds],
        'default_seed': seeds[0],
        'comparisons': COMPARISONS,
        'strings': STRINGS,
        'unavailable_fields': UNAVAILABLE_FIELDS,
        'provenance': {'export_source_sha': source_sha,
                       'exporter': 'thermorl2/experiments/replay_export.py',
                       'generated_utc': generated_utc, 'raw_inventory': 'results/run_files.json'}}


def _inventory(root):
    files = [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
             for p in sorted(root.rglob('*')) if p.is_file()]
    return files


def export_experiment(experiment_dir, spec, policies, seeds, source_sha, generated_utc=None):
    """Write <experiment_dir>/exports/replay_v1 (refuses to overwrite). Raises before writing on any failed check."""
    policies, seeds = tuple(policies), tuple(int(s) for s in seeds)
    exp = Path(experiment_dir)
    dest, staging = exp / 'exports/replay_v1', exp / 'exports/.replay_v1.staging'
    if dest.exists():
        raise FileExistsError(f'{dest} already exists; the exporter never overwrites')
    for policy in policies:
        if policy not in SCALE_POLICIES:
            raise ValueError(f'unknown policy {policy!r}')
    generated_utc = generated_utc or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    raw = _RawLedgers(exp)
    metrics = parse_metrics(exp / 'results/metrics.csv')
    ctx = {'metrics': metrics, 'runtime': _read_json(exp / 'results/matrix_runtime.json'),
           'evidence': _read_json(exp / 'provenance/determinism_evidence.json')}
    created_exports = not (exp / 'exports').exists()
    staging.mkdir(parents=True)
    try:
        shared, records = None, {}
        for seed in seeds:
            for policy in policies:
                record, manifest, facts = _export_run(raw, staging, spec, policy, seed, ctx)
                facts['nodes_per_rack'] = manifest['nodes_per_rack']
                if shared is not None and facts != shared:
                    raise ValueError(f'{policy}_seed{seed}: shared run facts differ from the first run')
                shared = facts
                records[(policy, seed)] = record
        scales = seed_colour_scales(raw, spec, seeds, shared['tick_s'], shared['n_ticks'], shared['n_racks'])
        _check_recorded_scale(raw, scales)
        _write_new(staging / 'frozen_outcome.json', _json_bytes(_frozen_outcome(raw, spec, metrics), indent=2))
        _write_new(staging / 'catalog.json', _json_bytes(
            _catalog(spec, policies, seeds, scales, shared, source_sha, generated_utc), indent=2))
        files = _inventory(staging)
        too_big = [f['path'] for f in files if f['bytes'] >= FILE_LIMIT_BYTES]
        total = sum(f['bytes'] for f in files)
        if too_big or total > EXPERIMENT_LIMIT_BYTES:
            raise ValueError(f'size budget exceeded: total {total} bytes; files over {FILE_LIMIT_BYTES}: {too_big}')
        os.rename(staging, dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        if created_exports:
            try:
                (exp / 'exports').rmdir()
            except OSError:
                pass
        raise
    return {'experiment': spec.id, 'files': _inventory(dest), 'total_bytes': total,
            'max_file_bytes': max(f['bytes'] for f in files)}


# ---------------------------------------------------------------- independent verification

def _verify_run(exp, base, spec, policy, seed, raw, metrics):
    name = f'{policy}_seed{seed}'
    run_dir = base / 'runs' / name
    meta = _read_json(run_dir / 'run.json')
    manifest = _read_json(raw.path(_run_rel(policy, seed, 'manifest.json')))
    n_ticks, n_racks = meta['n_ticks'], meta['n_racks']
    listed = sorted([entry['path'] for entry in meta['files'].values()] + ['run.json'])
    actual = sorted(p.name for p in run_dir.iterdir())
    file_ok = listed == actual
    for entry in meta['files'].values():
        path = run_dir / entry['path']
        file_ok = file_ok and path.is_file() and path.stat().st_size == entry['bytes'] \
            and sha256_file(path) == entry['sha256']
    source_ok = True
    for key, rel in (('manifest_sha256', 'manifest.json'), ('decisions_sha256', 'decisions.jsonl'),
                     ('intervals_sha256', 'intervals.parquet'),
                     ('job_events_sha256', 'provenance/job_events.jsonl')):
        digest = sha256_file(raw.path(_run_rel(policy, seed, rel)))
        source_ok = source_ok and digest == meta['source'][key] == raw.inventory[_run_rel(policy, seed, rel)]['sha256']
        if key != 'manifest_sha256':
            source_ok = source_ok and digest == manifest[key]
    tc = np.frombuffer((run_dir / 'rack_tc.f32').read_bytes(), dtype='<f4').reshape(n_ticks, n_racks)
    kw = np.frombuffer((run_dir / 'rack_kw.f32').read_bytes(), dtype='<f4').reshape(n_ticks, n_racks)
    free = np.frombuffer((run_dir / 'rack_free.u8').read_bytes(), dtype='u1').reshape(n_ticks, n_racks)
    tick = np.frombuffer((run_dir / 'tick.f64').read_bytes(), dtype='<f8').reshape(n_ticks, len(TICK_COLUMNS))
    source = _load_intervals(raw.path(_run_rel(policy, seed, 'intervals.parquet')), n_ticks, n_racks,
                             int(manifest['power_tick_s']))
    window = (tick[:, 0] > spec.eval_start_s) & (tick[:, 0] <= tick[-1, 0])
    mean_c = float(np.mean(tick[window, 4]))
    row = _frozen_row(metrics, policy, seed)
    events = _read_json(run_dir / 'events.json')
    decisions = _read_json(run_dir / 'decisions.json')
    n_candidates = (run_dir / 'candidates.bin').stat().st_size // (CANDIDATE_DTYPE.itemsize * ROWS_PER_DECISION)
    result = {
        'maxrack_mean_c': mean_c, 'metrics_maxrack_mean_c': row['maxrack_mean_c'],
        'maxrack_mean_abs_err': abs(mean_c - row['maxrack_mean_c']),
        'tc_f32_max_abs_err': float(np.abs(tc.astype(np.float64) - source['t_c']).max()),
        'kw_f32_max_abs_err': float(np.abs(kw.astype(np.float64) - source['kw']).max()),
        'free_equal': bool(np.array_equal(free, source['free'])),
        'tick_t_s_grid_ok': bool(np.array_equal(tick[:, 0], source['t_s'][:, 0])),
        'n_decisions': len(decisions['decision_index']), 'n_candidate_records': int(n_candidates),
        'manifest_decision_rows': int(manifest['decision_rows']),
        'n_start_events': sum(1 for k in events['kind'] if k == 0),
        'run_json_n_decisions': meta['n_decisions'],
        'file_sha256_ok': bool(file_ok), 'source_sha256_ok': bool(source_ok)}
    result['passed'] = bool(
        result['maxrack_mean_abs_err'] <= MAXRACK_TOLERANCE and result['tc_f32_max_abs_err'] <= F32_TOLERANCE
        and result['kw_f32_max_abs_err'] <= F32_TOLERANCE and result['free_equal'] and result['tick_t_s_grid_ok']
        and result['n_decisions'] == result['n_candidate_records'] == result['manifest_decision_rows']
        == result['n_start_events'] == result['run_json_n_decisions'] and file_ok and source_ok)
    return result, tick[:, 1].copy()


def verify_export(experiment_dir, spec, policies, seeds):
    """Re-read the written export and the raw ledgers and report every A6 check with its numbers."""
    exp, policies, seeds = Path(experiment_dir), tuple(policies), tuple(int(s) for s in seeds)
    base = exp / 'exports/replay_v1'
    raw = _RawLedgers(exp)
    metrics = parse_metrics(exp / 'results/metrics.csv')
    catalog = _read_json(base / 'catalog.json')
    runs, it_kw_diff, passed = {}, {}, True
    for seed in seeds:
        totals = []
        for policy in policies:
            result, total = _verify_run(exp, base, spec, policy, seed, raw, metrics)
            runs[f'{policy}_seed{seed}'] = result
            passed = passed and result['passed']
            totals.append(total)
        diff = max(float(np.abs(t - totals[0]).max()) for t in totals)
        it_kw_diff[str(seed)] = diff
        passed = passed and diff <= KW_TOLERANCE
    first = _read_json(base / 'runs' / f'{policies[0]}_seed{seeds[0]}' / 'run.json')
    scales = seed_colour_scales(raw, spec, seeds, catalog['time']['tick_s'], first['n_ticks'], first['n_racks'])
    scale_diff = {str(s): max(abs(scales[s]['min'] - c['colour_scale_c']['min']),
                              abs(scales[s]['max'] - c['colour_scale_c']['max']))
                  for c in catalog['seeds'] for s in [c['seed']]}
    seed1_diff = _check_recorded_scale(raw, {1: catalog['seeds'][0]['colour_scale_c']}) if 1 in seeds else None
    passed = passed and all(d <= SCALE_TOLERANCE for d in scale_diff.values())
    return {'experiment': spec.id, 'runs': runs, 'it_kw_total_max_abs_diff_by_seed': it_kw_diff,
            'colour_scale_recomputed_abs_diff_by_seed': scale_diff,
            'colour_scale_seed1_abs_diff': seed1_diff,
            'colour_scale_c_by_seed': {str(c['seed']): c['colour_scale_c'] for c in catalog['seeds']},
            'all_passed': bool(passed)}


# ---------------------------------------------------------------- command line

def _git(args, cwd):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def _peak_rss():
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return {'ru_maxrss': value, 'unit': 'bytes' if sys.platform == 'darwin' else 'KiB',
            'scope': 'own process high-water resident set, including imports'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Write hash-verified replay_v1 exports (read-only on ledgers).')
    parser.add_argument('--experiment-dir', action='append', required=True)
    parser.add_argument('--policies', default='packing,power_balance,thermal_predictive')
    parser.add_argument('--seeds', default='1,2,3')
    parser.add_argument('--record', help='write a JSON record of the export and all checks (never overwrites)')
    args = parser.parse_args(argv)
    started = perf_counter()
    policies = tuple(args.policies.split(','))
    seeds = tuple(int(s) for s in args.seeds.split(','))
    dirs = [Path(d).resolve() for d in args.experiment_dir]
    head = _git(['rev-parse', 'HEAD'], dirs[0])
    package = Path(__file__).resolve().parents[1]
    dirty = _git(['status', '--porcelain', '--', str(package)], dirs[0])
    record = {'command': [sys.executable, '-m', 'thermorl2.experiments.replay_export', *(argv or sys.argv[1:])],
              'head': head, 'package_porcelain': dirty.splitlines(), 'experiments': {}}
    for exp in dirs:
        spec = EXPERIMENTS[exp.name]
        exported = export_experiment(exp, spec, policies, seeds, source_sha=head)
        checks = verify_export(exp, spec, policies, seeds)
        record['experiments'][spec.id] = {**exported, 'checks': checks}
        print(json.dumps({'experiment': spec.id, 'total_bytes': exported['total_bytes'],
                          'max_file_bytes': exported['max_file_bytes'], 'all_passed': checks['all_passed']}))
        if not checks['all_passed']:
            print('CHECK FAILURE: stop and report', file=sys.stderr)
            return 1
    record['wall_s'] = perf_counter() - started
    record['peak_rss'] = _peak_rss()
    record['generated_utc'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if args.record:
        _write_new(Path(args.record), _json_bytes(record, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
