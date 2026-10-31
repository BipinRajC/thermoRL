import numpy as np
import pandas as pd
import hashlib
import json
from pathlib import Path
import pytest

from thermorl2.raps_adapter.workload.synthetic import SyntheticSpec, generate, offered_utilisation, represented_runtimes, write_workload


def test_synthetic_determinism_and_sha(tmp_path):
    spec = SyntheticSpec()
    first = generate(spec, 1, 21600, 4626, 6)
    second = generate(spec, 1, 21600, 4626, 6)
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    assert write_workload(first, tmp_path / "a.parquet", {"seed": 1}) == write_workload(second, tmp_path / "b.parquet", {"seed": 1})


def test_offered_utilisation_and_frozen_bounds():
    frame = generate(SyntheticSpec(), 1, 21600, 4626, 6)
    assert 0.54 <= offered_utilisation(frame, 21600, 4626) <= 0.66
    assert list(frame.columns) == ["id", "nodes_required", "cpu_util", "gpu_util", "submit_time", "expected_run_time", "time_limit"]
    assert set(frame.nodes_required) <= {1, 2, 4, 8, 16, 32}
    assert set(frame.cpu_util) <= {0.5, 1.0, 1.5, 2.0}
    assert set(frame.gpu_util) <= set(range(7))
    assert frame.expected_run_time.between(300, 14400).all()
    assert pd.api.types.is_integer_dtype(frame.expected_run_time)
    assert pd.api.types.is_integer_dtype(frame.time_limit)
    assert frame.time_limit.between(450, 21600).all()
    assert (frame.time_limit >= frame.expected_run_time).all()
    assert frame.submit_time.is_monotonic_increasing
    assert frame.submit_time.between(0, 21600, inclusive="left").all()
    np.testing.assert_array_equal(frame.time_limit.to_numpy(), np.ceil(1.5 * frame.expected_run_time).astype(int))


def test_shared_runtime_representation_clips_then_ceils():
    values = np.array([299.1, 300.0, 300.01, 14399.2, 14400.9])
    actual = represented_runtimes(values, SyntheticSpec())
    np.testing.assert_array_equal(actual, [300, 300, 301, 14400, 14400])
    assert np.issubdtype(actual.dtype, np.integer)


def test_workload_metadata_and_overwrite_protection(tmp_path):
    from thermorl2.raps_adapter.workload import synthetic
    frame = generate(SyntheticSpec(), 1, 7200, 4626, 6)
    path = tmp_path / "workload.parquet"
    sha = write_workload(frame, path, {"seed": 1})
    meta = json.loads(Path(str(path) + ".meta.json").read_text())
    assert meta["spec"]["rho"] == 0.6 and meta["spec"]["runtime_sigma"] == 0.8
    assert meta["mc_samples"] == 1_000_000 and meta["mc_expected_node_seconds"] > 0
    assert meta["arrival_rate_per_s"] > 0 and meta["representation"] and meta["rng_draw_order"]
    assert meta["generator_source_sha256"] == hashlib.sha256(Path(synthetic.__file__).read_bytes()).hexdigest()
    assert set(meta["versions"]) == {"numpy", "pandas", "pyarrow"}
    assert meta["sha256"] == sha
    changed = frame.copy()
    changed.loc[0, "cpu_util"] = 0.25
    with pytest.raises(FileExistsError):
        write_workload(changed, path, {"seed": 1})
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
