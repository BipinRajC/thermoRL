"""replay_v1 exporter: unit tests on tiny synthetic ledgers (no FMU, RAPS or real data)."""

import ast
from pathlib import Path

import numpy as np
import pytest

from thermorl2.experiments import replay_export as rx

MODULE = Path(rx.__file__)


def _scores(*values):
    return np.asarray(values, dtype=float)


def _row(scores, chosen, **extra):
    n = len(scores)
    base = {'t_s': 5, 'job_id': 7, 'nodes_required': 1, 'policy': 'packing', 'rule': 'single',
            'racks': list(chosen), 'nodes': [0], 'job_kw': 1.5, 'scores': list(map(float, scores)),
            't_c': [40.0 + i for i in range(n)], 'committed_kw': [10.0 + i for i in range(n)],
            'free': [18 - i for i in range(n)], 't_obs_s': 0.0, 'latency_us': None}
    base.update(extra)
    return base


def test_candidate_rows_rank_by_score_with_lower_rack_index_on_ties():
    rows = rx.candidate_rows(_scores(1, 5, 5, 0, 5, 2, 5), chosen_rack=1, k=5)
    assert rows[:5] == [1, 2, 4, 6, 5]
    assert rows[5] == rx.EMPTY_RACK


def test_candidate_rows_append_chosen_rack_when_not_in_top_k():
    rows = rx.candidate_rows(_scores(9, 8, 7, 6, 5, 4, 3), chosen_rack=6, k=5)
    assert rows == [0, 1, 2, 3, 4, 6]


def test_tie_count_and_logged_best_flag():
    assert rx.tie_stats(_scores(1, 5, 5, 0, 5), chosen_rack=0) == (3, False)
    assert rx.tie_stats(_scores(1, 5, 5, 0, 5), chosen_rack=1) == (3, True)
    assert rx.tie_stats(_scores(1, 5, 4), chosen_rack=1) == (1, True)


def test_event_racks_are_sorted_unique_node_floor_divisions():
    assert rx.event_racks([40, 0, 17, 18, 36, 19], nodes_per_rack=18) == [0, 1, 2]


def test_candidate_record_is_fifteen_little_endian_bytes():
    assert rx.CANDIDATE_DTYPE.itemsize == 15
    assert rx.CANDIDATE_DTYPE.names == ('rack', 'score', 't_c', 'committed_kw', 'free')
    assert [rx.CANDIDATE_DTYPE[n].str for n in rx.CANDIDATE_DTYPE.names] == ['<u2', '<f4', '<f4', '<f4', '|u1']
    assert rx.ROWS_PER_DECISION == 6


def test_decision_columns_hold_logged_values_and_pad_empty_rows():
    columns = rx.DecisionColumns(n_racks=7)
    columns.add(_row([1, 5, 5, 0, 5, 2, 5], chosen=[1], t_s=5, rule='single'))
    columns.add(_row([9, 8, 7, 6, 5, 4, 3], chosen=[6, 5], t_s=9, rule='span', job_id=8))
    meta = columns.as_json()
    assert meta['decision_index'] == [0, 1] and meta['raps_t_s'] == [5, 9] and meta['job_id'] == [7, 8]
    assert meta['rule'] == ['single', 'span'] and meta['chosen_offsets'] == [0, 1, 3]
    assert meta['chosen_racks'] == [1, 6, 5]
    assert meta['n_ties_at_logged_best'] == [4, 1] and meta['chosen_is_logged_best'] == [True, False]
    records = np.frombuffer(columns.candidates_bytes(), dtype=rx.CANDIDATE_DTYPE).reshape(2, 6)
    assert records['rack'][0].tolist() == [1, 2, 4, 6, 5, rx.EMPTY_RACK]
    assert records['rack'][1].tolist() == [0, 1, 2, 3, 4, 6]
    assert records['score'][1, 5] == np.float32(3.0) and records['free'][1, 5] == 12
    assert np.isnan(records['score'][0, 5]) and records['free'][0, 5] == 0


def test_decision_columns_reject_decreasing_raps_time_and_bad_vectors():
    columns = rx.DecisionColumns(n_racks=3)
    columns.add(_row([1, 2, 3], chosen=[2], t_s=9))
    with pytest.raises(ValueError, match='non-decreasing'):
        columns.add(_row([1, 2, 3], chosen=[2], t_s=8))
    with pytest.raises(ValueError, match='257|n_racks|length'):
        rx.DecisionColumns(n_racks=3).add(_row([1, 2], chosen=[0]))


def test_pulse_bounds_and_starts_follow_the_documented_rule():
    assert rx.pulse_bounds(10) == (-1, 10) and rx.pulse_bounds(3610) == (3580, 3610)
    events = {'kind': [0, 1, 0], 'raps_t_s': [25, 26, 55], 'rack_offsets': [0, 2, 3, 4],
              'racks': [2, 3, 5, 9]}
    assert rx.racks_started_in(events, -1, 30) == {2, 3}
    assert rx.racks_started_in(events, 25, 55) == {9}
    assert rx.racks_started_in(events, 30, 60) == {9}


def test_colormap_lut_is_the_256_entry_inferno_ramp():
    lut = rx.colormap_lut()
    assert len(lut) == 256 and lut[0] == '#000004' and lut[255] == '#fcffa4'
    assert all(len(c) == 7 and c == c.lower() and c[0] == '#' for c in lut)


def test_exporter_never_imports_scoring_placement_fmu_or_raps_code():
    tree = ast.parse(MODULE.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(('.' * node.level) + (node.module or ''))
    forbidden = ('thermorl2', 'raps', 'fmpy', '.')
    offenders = sorted(m for m in modules if m.split('.')[0] in forbidden or m.startswith('.'))
    assert offenders == []
