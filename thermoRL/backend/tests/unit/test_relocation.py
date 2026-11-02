"""Relocation safety after the thermorl-v2 -> backend rename (c09f735).

The package must resolve its own inputs and provenance from its current
location. Historical manifests keep their recorded old paths; these tests only
cover current executable path resolution. No FMU or RAPS simulation runs here.
"""

import json
from pathlib import Path

from thermorl2.experiments.provenance import application_source_hashes
from thermorl2.raps_adapter.runner import load_episode_workload
from thermorl2.raps_adapter.systems import project_root, repo_root

PACKAGE = Path(__file__).resolve().parents[2]


def test_project_root_is_the_current_backend_package_root():
    assert project_root() == PACKAGE
    assert (project_root() / 'thermorl2').is_dir()
    assert project_root().relative_to(repo_root()) == Path('thermoRL/backend')


def test_relative_workload_resolves_under_current_package_without_old_root():
    # The removed historical root must not be needed (nor silently traversed).
    old_root = repo_root() / 'thermoRL/thermorl-v2'
    cfg = json.loads((PACKAGE / 'experiments/summit/E12_g4_alibaba/provenance/preregistration.json').read_text())
    relative = 'experiments/summit/_workloads/7415a80132d0bcf993071b30bfdc586803c848e1ab582bc9730a71dfddab4c2c.parquet'
    workload = {'kind': 'alibaba', 'path': relative,
                'sha256': '7415a80132d0bcf993071b30bfdc586803c848e1ab582bc9730a71dfddab4c2c',
                'meta_sha256': cfg['input_sha256'][relative + '.meta.json']}
    path, frame, meta = load_episode_workload({'workload': workload}, 1, 21600)
    assert path == project_root() / relative
    assert old_root not in path.parents
    assert meta['horizon_s'] == 21600 and frame.attrs['seed'] == 1 and len(frame) == 21885


def test_application_source_map_covers_the_current_package():
    hashes = application_source_hashes()
    files = sorted(str(p.relative_to(repo_root())) for p in (project_root() / 'thermorl2').rglob('*.py'))
    assert len(files) >= 39
    assert sorted(hashes) == files
    assert all(key.startswith('thermoRL/backend/thermorl2/') for key in hashes)


def test_no_removed_root_literal_in_executable_package_code():
    offenders = [str(p.relative_to(PACKAGE)) for p in (PACKAGE / 'thermorl2').rglob('*.py')
                 if 'thermorl-v2' in p.read_text()]
    assert offenders == []
