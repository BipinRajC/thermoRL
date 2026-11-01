"""A6 real-data checks of the committed replay_v1 exports against the verified raw ledgers.

Raw ledgers (experiments/summit/<EID>/runs, gitignored) exist only on machines that hold the verified
copies; without them the raw-comparison tests skip. Nothing here simulates or rewrites anything.
"""

import json
from pathlib import Path

import pytest

from thermorl2.experiments import replay_export as rx

SUMMIT = Path(__file__).resolve().parents[2] / 'experiments/summit'
POLICIES = ('packing', 'power_balance', 'thermal_predictive')
SEEDS = (1, 2, 3)
RECORDED_SEED1_SCALE = {'E11_g4_synthetic': (39.252402, 56.233641), 'E12_g4_alibaba': (38.702230, 42.413286)}
IDS = sorted(RECORDED_SEED1_SCALE)


def _raw_present(eid):
    return all((SUMMIT / eid / 'runs' / f'{p}_seed{s}' / 'decisions.jsonl').is_file()
               for p in rx.SCALE_POLICIES for s in SEEDS)


def _need_raw(eid):
    if not _raw_present(eid):
        pytest.skip(f'{eid}: raw ledgers are not present on this machine (recorded as skipped)')


@pytest.fixture(scope='module', params=IDS)
def verified(request):
    eid = request.param
    _need_raw(eid)
    exp = SUMMIT / eid
    if not (exp / 'exports/replay_v1/catalog.json').is_file():
        pytest.skip(f'{eid}: replay_v1 export is not on disk (recorded as skipped)')
    return eid, rx.verify_export(exp, rx.EXPERIMENTS[eid], POLICIES, SEEDS)


def test_every_run_mean_maxrack_equals_metrics_csv_within_1e_9(verified):
    eid, result = verified
    assert len(result['runs']) == 9
    for name, run in result['runs'].items():
        assert run['maxrack_mean_abs_err'] <= 1e-9, (eid, name, run['maxrack_mean_abs_err'])


def test_float32_rack_tc_error_is_at_most_5e_6_c(verified):
    eid, result = verified
    for name, run in result['runs'].items():
        assert run['tc_f32_max_abs_err'] <= 5e-6, (eid, name, run['tc_f32_max_abs_err'])
        assert run['kw_f32_max_abs_err'] <= 5e-6 and run['free_equal'], (eid, name)


def test_it_kw_total_is_identical_across_policies_in_every_seed(verified):
    eid, result = verified
    assert set(result['it_kw_total_max_abs_diff_by_seed']) == {'1', '2', '3'}
    assert all(d <= 1e-6 for d in result['it_kw_total_max_abs_diff_by_seed'].values())


def test_decision_and_start_event_counts_equal_manifest_decision_rows(verified):
    eid, result = verified
    for name, run in result['runs'].items():
        assert run['n_decisions'] == run['manifest_decision_rows'] == run['n_start_events'], (eid, name)
        assert run['n_candidate_records'] == run['manifest_decision_rows'], (eid, name)


def test_every_exported_file_hash_and_every_source_ledger_hash_is_correct(verified):
    eid, result = verified
    for name, run in result['runs'].items():
        assert run['file_sha256_ok'] and run['source_sha256_ok'], (eid, name)


def test_seed_1_colour_scale_equals_the_recorded_demo_scale(verified):
    eid, result = verified
    low, high = RECORDED_SEED1_SCALE[eid]
    scale = result['colour_scale_c_by_seed']['1']
    assert abs(scale['min'] - low) <= 1e-6 and abs(scale['max'] - high) <= 1e-6
    assert result['colour_scale_seed1_abs_diff'] <= 1e-6
    assert all(d <= 1e-6 for d in result['colour_scale_recomputed_abs_diff_by_seed'].values())


def test_verification_passes_overall(verified):
    assert verified[1]['all_passed'] is True


@pytest.mark.parametrize('eid', IDS)
def test_committed_export_is_self_consistent_and_within_the_size_budget(eid):
    base = SUMMIT / eid / 'exports/replay_v1'
    if not base.is_dir():
        pytest.skip(f'{eid}: no replay_v1 export on disk')
    catalog = json.loads((base / 'catalog.json').read_text())
    assert catalog['schema'] == rx.SCHEMA and catalog['default_seed'] == 1
    assert [s['seed'] for s in catalog['seeds']] == [1, 2, 3]
    total = 0
    for seed in catalog['seeds']:
        for rel in seed['runs'].values():
            meta = json.loads((base / rel).read_text())
            for entry in meta['files'].values():
                path = (base / rel).parent / entry['path']
                assert path.stat().st_size == entry['bytes'] and rx.sha256_file(path) == entry['sha256']
    for path in base.rglob('*'):
        if path.is_file():
            size = path.stat().st_size
            total += size
            assert size < 25_000_000, path
    assert total <= 100_000_000
