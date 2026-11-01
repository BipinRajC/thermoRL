"""replay_v1 export + verification on the synthetic experiment (3 racks x 4 ticks)."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import replay_fixture as fx
from thermorl2.experiments import replay_export as rx

POLICIES = ('packing', 'power_balance', 'thermal_predictive')
SPEC = rx.ExperimentSpec(
    id=fx.EXPERIMENT_ID, short='EFIX', workload_label='Synthetic', workload_note='fixture note',
    seed_notes={1: 'seed 1 of 3', 2: 'seed 2 of 3'}, experiment_statement='fixture statement',
    eval_start_s=fx.EVAL_START_S, verified_runs=frozenset({('thermal_predictive', 1)}))
HEAD = 'c' * 40


@pytest.fixture()
def built(tmp_path):
    exp, scale = fx.build_experiment(tmp_path, selected_attempts={('packing', 2): 2})
    return exp, scale


def export(exp, **kw):
    return rx.export_experiment(exp, SPEC, POLICIES, (1, 2), source_sha=HEAD,
                                generated_utc='2026-11-01T00:00:00Z', **kw)


def tree_digest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


def load(exp, *parts):
    return json.loads((exp / 'exports/replay_v1' / Path(*parts)).read_text())


def test_layout_is_exactly_catalog_frozen_outcome_and_seven_files_per_run(built):
    exp, _ = built
    export(exp)
    base = exp / 'exports/replay_v1'
    runs = sorted(p.name for p in (base / 'runs').iterdir())
    assert runs == sorted(f'{p}_seed{s}' for p in POLICIES for s in (1, 2))
    assert sorted(p.name for p in base.iterdir() if p.is_file()) == ['catalog.json', 'frozen_outcome.json']
    for run in runs:
        names = sorted(p.name for p in (base / 'runs' / run).iterdir())
        assert names == ['candidates.bin', 'decisions.json', 'events.json', 'rack_free.u8', 'rack_kw.f32',
                         'rack_tc.f32', 'run.json', 'tick.f64']


def test_arrays_have_contract_shapes_dtypes_and_values(built):
    exp, _ = built
    export(exp)
    run = exp / 'exports/replay_v1/runs/power_balance_seed1'
    index = fx.POLICIES.index('power_balance')
    tc = np.frombuffer((run / 'rack_tc.f32').read_bytes(), dtype='<f4').reshape(4, 3)
    kw = np.frombuffer((run / 'rack_kw.f32').read_bytes(), dtype='<f4').reshape(4, 3)
    free = np.frombuffer((run / 'rack_free.u8').read_bytes(), dtype='u1').reshape(4, 3)
    tick = np.frombuffer((run / 'tick.f64').read_bytes(), dtype='<f8').reshape(4, 8)
    np.testing.assert_array_equal(tc, fx.tc_array(index, 1).astype(np.float32))
    np.testing.assert_array_equal(kw, fx.kw_array(index).astype(np.float32))
    np.testing.assert_array_equal(free, fx.free_array(index))
    assert tick[:, 0].tolist() == [10.0, 20.0, 30.0, 40.0]
    assert tick[:, 2].tolist() == [0, 1, 2, 3] and tick[:, 3].tolist() == [0, 2, 4, 6]
    np.testing.assert_array_equal(tick[:, 4], fx.tc_array(index, 1).max(axis=1))
    np.testing.assert_array_equal(tick[:, 5], fx.tc_array(index, 1).min(axis=1))
    np.testing.assert_allclose(tick[:, 7], 3.3)
    assert tick[2, 6] == 0 and tick[0, 6] == 2  # exact tie at tick 2 -> lowest rack index


def test_it_kw_total_is_identical_across_policies(built):
    exp, _ = built
    export(exp)
    totals = [np.frombuffer((exp / f'exports/replay_v1/runs/{p}_seed1/tick.f64').read_bytes(),
                            dtype='<f8').reshape(4, 8)[:, 1] for p in POLICIES]
    assert all(np.array_equal(totals[0], t) for t in totals[1:])


def test_run_json_indexes_files_with_matching_bytes_hashes_and_source_shas(built):
    exp, _ = built
    export(exp)
    run_dir = exp / 'exports/replay_v1/runs/thermal_predictive_seed1'
    meta = json.loads((run_dir / 'run.json').read_text())
    assert meta['schema'] == rx.SCHEMA and meta['run_id'] == f'{fx.EXPERIMENT_ID}:thermal_predictive_seed1'
    assert meta['n_ticks'] == 4 and meta['n_racks'] == 3 and meta['n_decisions'] == 3
    assert meta['n_events'] == 4 and meta['launch_sha'] == 'a' * 40
    assert meta['c_prime_status'] == 'verified_E12' and meta['selected_attempt'] == 1
    assert set(meta['files']) == {'rack_tc', 'rack_kw', 'rack_free', 'tick', 'events', 'decisions', 'candidates'}
    for entry in meta['files'].values():
        data = (run_dir / entry['path']).read_bytes()
        assert entry['bytes'] == len(data) and entry['sha256'] == hashlib.sha256(data).hexdigest()
    assert meta['files']['rack_tc']['shape'] == [4, 3] and meta['files']['rack_tc']['dtype'] == 'float32'
    assert meta['files']['tick']['columns'][4] == 'maxrack_c'
    cand = meta['files']['candidates']
    assert cand['record_bytes'] == 15 and cand['rows_per_decision'] == 6 and cand['empty_rack'] == 65535
    assert cand['fields'] == [['rack', 'uint16'], ['score', 'float32'], ['t_c', 'float32'],
                              ['committed_kw', 'float32'], ['free', 'uint8']]
    manifest = json.loads((exp / 'runs/thermal_predictive_seed1/manifest.json').read_text())
    assert meta['source']['decisions_sha256'] == manifest['decisions_sha256']
    assert meta['source']['intervals_sha256'] == manifest['intervals_sha256']
    assert meta['source']['job_events_sha256'] == manifest['job_events_sha256']
    assert meta['source']['manifest_sha256'] == fx.sha(exp / 'runs/thermal_predictive_seed1/manifest.json')


def test_c_prime_is_verified_only_for_the_one_recorded_run_and_attempt_comes_from_runtime(built):
    exp, _ = built
    export(exp)
    status = {(p, s): load(exp, 'runs', f'{p}_seed{s}', 'run.json')['c_prime_status']
              for p in POLICIES for s in (1, 2)}
    assert [k for k, v in status.items() if v == 'verified_E12'] == [('thermal_predictive', 1)]
    assert set(status.values()) == {'verified_E12', 'inherited_not_remeasured'}
    assert load(exp, 'runs', 'packing_seed2', 'run.json')['selected_attempt'] == 2
    assert load(exp, 'runs', 'packing_seed1', 'run.json')['selected_attempt'] == 1


def test_events_are_columnar_ordered_and_mapped_to_racks(built):
    exp, _ = built
    export(exp)
    ev = load(exp, 'runs', 'packing_seed1', 'events.json')
    assert ev['kind'] == [0, 1, 0, 0] and ev['raps_t_s'] == [1, 12, 12, 25]
    assert ev['decision_index'] == [0, -1, 1, 2] and ev['job_id'] == [0, 0, 1, 2]
    assert ev['rack_offsets'] == [0, 1, 2, 4, 5] and ev['racks'] == [0, 0, 0, 1, 2]


def test_events_put_completes_before_starts_at_the_same_second(built):
    exp, _ = built
    lines = (exp / 'runs/packing_seed1/provenance/job_events.jsonl').read_text().splitlines()
    assert json.loads(lines[1])['t_s'] == 12 and json.loads(lines[2])['event'] == 'complete'
    ordered = rx.order_events([json.loads(line) for line in lines], nodes_per_rack=18)
    assert [(e['t'], e['kind']) for e in ordered] == [(1, 0), (12, 1), (12, 0), (25, 0)]


def test_decisions_and_candidates_carry_logged_context(built):
    exp, _ = built
    export(exp)
    d = load(exp, 'runs', 'packing_seed1', 'decisions.json')
    assert d['decision_index'] == [0, 1, 2] and d['raps_t_s'] == [1, 12, 25]
    assert d['rule'] == ['single', 'span', 'single'] and d['chosen_offsets'] == [0, 1, 3, 4]
    assert d['chosen_racks'] == [0, 0, 1, 2] and d['n_ties_at_logged_best'] == [1, 1, 2]
    assert d['chosen_is_logged_best'] == [True, True, False]
    raw = (exp / 'exports/replay_v1/runs/packing_seed1/candidates.bin').read_bytes()
    assert len(raw) == 3 * 6 * 15
    rec = np.frombuffer(raw, dtype=rx.CANDIDATE_DTYPE).reshape(3, 6)
    assert rec['rack'][2].tolist() == [0, 1, 2, 65535, 65535, 65535] and rec['rack'][0][3] == 65535


def test_catalog_follows_the_contract(built):
    exp, scale = built
    export(exp)
    cat = load(exp, 'catalog.json')
    assert cat['schema'] == 'thermorl.replay.v1' and cat['default_seed'] == 1
    assert cat['experiment']['id'] == fx.EXPERIMENT_ID and cat['experiment']['fmu_sha256'] == 'f' * 64
    assert cat['experiment']['scenario'] == 'nominal (290 K)'
    assert cat['grid'] == {'rows': 1, 'cols': 20, 'n_racks': 3, 'nodes_per_rack': 18,
                           'mapping': 'row = r // 20, col = r % 20, origin lower-left',
                           'schematic_not_floor_plan': True}
    assert cat['time'] == {'tick_s': 10, 'n_ticks': 4, 'first_t_s': 10, 'last_t_s': 40,
                           'eval_start_exclusive_s': 20, 'eval_end_inclusive_s': 40, 'pulse_window_s': 30}
    assert cat['rack_kw_range']['idle_kw'] == 10.0 and cat['rack_kw_range']['peak_kw'] == 20.0
    assert cat['colormap']['name'] == 'inferno' and len(cat['colormap']['lut']) == 256
    assert [s['seed'] for s in cat['seeds']] == [1, 2] and cat['seeds'][0]['note'] == 'seed 1 of 3'
    assert cat['seeds'][0]['colour_scale_c']['min'] == scale[1][0] and cat['seeds'][0]['colour_scale_c']['max'] == scale[1][1]
    assert cat['seeds'][1]['colour_scale_c'] != cat['seeds'][0]['colour_scale_c']
    assert cat['seeds'][0]['runs']['packing'] == 'runs/packing_seed1/run.json'
    assert [c['id'] for c in cat['comparisons']] == ['pb_vs_tp', 'packing_vs_tp'] and cat['comparisons'][0]['default']
    assert cat['unavailable_fields'] == ['PUE', 'carbon', 'SLO', 'emergency', 'dual_prices',
                                         'THI_counterfactual', 'regret', 'energy_savings']
    assert cat['provenance']['export_source_sha'] == HEAD
    for key, text in rx.STRINGS.items():
        assert cat['strings'][key] == text


def test_contract_strings_are_verbatim():
    assert rx.STRINGS['s2'].startswith('published view = FMU endpoint t+Δ of interval driven by P(t);')
    assert rx.STRINGS['s2'].endswith('identical for all policies.')
    assert 'thermal_predictive reproduces from logged context ≈ 94.8 % in E11 and ≈ 97.7 % in E12' in rx.STRINGS['precision_note']
    assert rx.STRINGS['interval_semantics'].startswith('Rack power, free nodes and job counts are RAPS inputs at t − 10 s')
    assert rx.STRINGS['pulse_rule'].endswith('Rings are not a cooling effect.')
    assert rx.REPRODUCIBILITY_SCOPE.endswith('no cross-machine portability is claimed.')
    assert rx.RULE == ('power_balance − thermal_predictive time-mean max-rack coolant over '
                       '3600 < t ≤ 21600 s must be ≥ 0.5 °C in every seed')


def test_frozen_outcome_copies_decision_and_parses_metrics(built):
    exp, _ = built
    export(exp)
    out = load(exp, 'frozen_outcome.json')
    assert out['decision'] == json.loads((exp / 'results/decision.json').read_text())
    assert out['headline'] == 'no material value on the homogeneous twin'
    assert out['decision_sha256'] == fx.sha(exp / 'results/decision.json')
    assert out['metrics_sha256'] == fx.sha(exp / 'results/metrics.csv')
    assert len(out['metrics']) == 10 and out['metrics'][0]['name'] == 'packing_seed1'
    row = out['metrics'][0]
    assert row['seed'] == 1 and isinstance(row['seed'], int) and isinstance(row['maxrack_mean_c'], float)
    assert 'coolant_over_70_racks' not in row and row['jobs_started'] == 3
    assert out['experiment_statement'] == 'fixture statement'
    assert out['reproducibility_scope'] == rx.REPRODUCIBILITY_SCOPE and out['rule'] == rx.RULE
    meta = load(exp, 'runs', 'packing_seed2', 'run.json')
    assert meta['metrics'] == next(m for m in out['metrics'] if m['name'] == 'packing_seed2')


def test_export_refuses_to_overwrite_and_never_touches_sources(built):
    exp, _ = built
    before = tree_digest(exp)
    export(exp)
    after_first = tree_digest(exp)
    assert {k: v for k, v in after_first.items() if not k.startswith('exports/')} == before
    with pytest.raises(FileExistsError):
        export(exp)
    assert tree_digest(exp) == after_first


def test_corrupt_source_ledger_stops_before_anything_is_written(built):
    exp, _ = built
    path = exp / 'runs/packing_seed1/decisions.jsonl'
    path.write_text(path.read_text().replace('job_id', 'job_ic', 1))  # same size, different bytes
    with pytest.raises(ValueError, match='sha256'):
        export(exp)
    assert not (exp / 'exports').exists()


def test_scale_that_disagrees_with_the_recorded_inventory_stops(built):
    exp, scale = built
    (exp / 'provenance/demo_asset_inventory.json').write_text(
        json.dumps({'temperature_colour_scale_c': [scale[1][0], scale[1][1] + 1e-3]}))
    with pytest.raises(ValueError, match='colour scale'):
        export(exp)
    assert not (exp / 'exports').exists()


def test_metrics_row_that_disagrees_with_the_ledger_stops(built):
    exp, _ = built
    text = (exp / 'results/metrics.csv').read_text().replace('packing_seed1,packing,1,', 'packing_seed1,packing,1,9')
    (exp / 'results/metrics.csv').write_text(text)
    with pytest.raises(ValueError, match='maxrack_mean_c'):
        export(exp)
    assert not (exp / 'exports').exists()


def test_verify_export_reports_every_check_and_passes_on_a_good_export(built):
    exp, scale = built
    export(exp)
    result = rx.verify_export(exp, SPEC, POLICIES, (1, 2))
    assert result['all_passed'] is True
    run = result['runs']['thermal_predictive_seed1']
    assert run['maxrack_mean_abs_err'] <= 1e-9 and run['tc_f32_max_abs_err'] <= 5e-6
    assert run['n_decisions'] == run['manifest_decision_rows'] == run['n_start_events'] == 3
    assert run['file_sha256_ok'] and run['source_sha256_ok']
    assert result['it_kw_total_max_abs_diff_by_seed'] == {'1': 0.0, '2': 0.0}
    assert result['colour_scale_seed1_abs_diff'] <= 1e-6


def test_verify_export_detects_a_flipped_byte(built):
    exp, _ = built
    export(exp)
    path = exp / 'exports/replay_v1/runs/packing_seed1/rack_tc.f32'
    data = bytearray(path.read_bytes())
    data[0] ^= 0xFF
    path.write_bytes(bytes(data))
    result = rx.verify_export(exp, SPEC, POLICIES, (1, 2))
    assert result['all_passed'] is False
    assert result['runs']['packing_seed1']['file_sha256_ok'] is False


def test_truncated_source_ledger_stops_on_size(built):
    exp, _ = built
    path = exp / 'runs/packing_seed1/decisions.jsonl'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='size differs'):
        export(exp)
    assert not (exp / 'exports').exists()


def test_cli_exports_verifies_and_writes_a_record_that_cannot_be_overwritten(built, tmp_path, monkeypatch):
    exp, _ = built
    monkeypatch.setitem(rx.EXPERIMENTS, fx.EXPERIMENT_ID, SPEC)
    monkeypatch.setattr(rx, '_git', lambda args, cwd: HEAD if args[0] == 'rev-parse' else '')
    record = tmp_path / 'record.json'
    argv = ['--experiment-dir', str(exp), '--seeds', '1,2', '--record', str(record)]
    assert rx.main(argv) == 0
    data = json.loads(record.read_text())
    entry = data['experiments'][fx.EXPERIMENT_ID]
    assert data['head'] == HEAD and data['wall_s'] >= 0 and data['peak_rss']['ru_maxrss'] > 0
    assert entry['checks']['all_passed'] is True and entry['total_bytes'] > 0
    assert {f['path'] for f in entry['files']} >= {'catalog.json', 'frozen_outcome.json'}
    with pytest.raises(FileExistsError):
        rx.main(argv)


def test_cli_reports_failure_and_writes_no_record_when_a_check_fails(built, tmp_path, monkeypatch):
    exp, _ = built
    monkeypatch.setitem(rx.EXPERIMENTS, fx.EXPERIMENT_ID, SPEC)
    monkeypatch.setattr(rx, '_git', lambda args, cwd: HEAD if args[0] == 'rev-parse' else '')
    monkeypatch.setattr(rx, 'verify_export', lambda *a, **k: {'all_passed': False})
    record = tmp_path / 'record.json'
    assert rx.main(['--experiment-dir', str(exp), '--seeds', '1,2', '--record', str(record)]) == 1
    assert not record.exists()
