"""Backend correctness gate against an independent direct-FMU replay."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


pytestmark = pytest.mark.fmu


def _fixed_sequence() -> list[dict]:
    levels = (8.0, 10.86, 15.0, 25.0)
    ticks = []
    for phase in range(4):
        for _ in range(12):
            power = [levels[(rack + phase) % 4] for rack in range(44)]
            if phase == 2:
                power[0] = 40.0
                power[43] = 5.0
            ticks.append({
                "elapsed_start_s": float(len(ticks) * 20),
                "rack_kw": power,
                "t_air_k": 290.0 if phase < 2 else 289.0,
                "t_ext_k": 290.0 if phase < 2 else 291.0,
            })
    return ticks


def _run_helper(path: Path, fmu_path: Path, sequence_path: Path, output_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(path), str(fmu_path), str(sequence_path), str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{path.name}: {result.stdout}\n{result.stderr}"
    return json.loads(output_path.read_text())


def _observations(samples: list[dict], key: str) -> np.ndarray:
    return np.asarray([sample[key] for sample in samples], dtype=float)


def test_backend_matches_independent_direct_fmu_with_snapshot_replay(fmu_path, tmp_path):
    direct_helper = Path(__file__).with_name("direct_fmu_replay.py")
    backend_helper = Path(__file__).with_name("backend_replay.py")
    assert direct_helper.is_file(), "independent direct-FMU helper is not implemented"
    assert backend_helper.is_file(), "backend replay helper is not implemented"

    sequence = _fixed_sequence()
    sequence_path = tmp_path / "fixed_asymmetric_sequence.json"
    sequence_path.write_text(json.dumps(sequence, indent=2) + "\n")
    direct = _run_helper(direct_helper, fmu_path, sequence_path, tmp_path / "direct.json")
    backend = _run_helper(backend_helper, fmu_path, sequence_path, tmp_path / "backend.json")

    assert direct["warmup_used_s"] == backend["warmup_used_s"] == 7200.0
    assert direct["snapshot_time_s"] == backend["snapshot_time_s"] == 7200.0
    assert backend["warmup_status"] == "capped_preconditioned_not_settled"
    assert len(direct["replays"]) == len(backend["replays"]) == 2
    assert backend["runtime_s"] > 0
    assert backend["close_twice_succeeded"] is True

    expected_elapsed = [float(20 * tick) for tick in range(49)]
    expected_points = [7200.0 + float(20 * tick) for tick in range(48)]
    expected_heat = np.asarray([tick["rack_kw"] for tick in sequence], dtype=float) * 945.0
    for side in (direct, backend):
        for replay in side["replays"]:
            samples = replay["samples"]
            assert [sample["elapsed_s"] for sample in samples] == expected_elapsed
            assert [sample["fmu_time_s"] for sample in samples] == [7200.0 + value for value in expected_elapsed]
            calls = replay["communication_calls"]
            assert [call["elapsed_start_s"] for call in calls] == expected_elapsed[:-1]
            assert [call["current_communication_point_s"] for call in calls] == expected_points
            assert [call["step_size_s"] for call in calls] == [20.0] * 48
            np.testing.assert_allclose(np.asarray(replay["heat_input_w"]), expected_heat, rtol=0, atol=1e-9)
            assert replay["air_input_k"] == [tick["t_air_k"] for tick in sequence]
            assert replay["external_input_k"] == [tick["t_ext_k"] for tick in sequence]
            for key in ("rack_coolant_c", "cdu_primary_supply_c", "cdu_primary_return_c", "datacenter_primary_flow_gpm"):
                assert np.isfinite(_observations(samples, key)).all()
        for key in ("rack_coolant_c", "cdu_primary_supply_c", "cdu_primary_return_c", "datacenter_primary_flow_gpm"):
            np.testing.assert_allclose(
                _observations(side["replays"][0]["samples"], key),
                _observations(side["replays"][1]["samples"], key),
                rtol=0,
                atol=1e-9,
            )

    assert [sample["elapsed_s"] for sample in direct["replays"][0]["samples"]] == [sample["elapsed_s"] for sample in backend["replays"][0]["samples"]]
    for direct_replay, backend_replay in zip(direct["replays"], backend["replays"]):
        assert [call["current_communication_point_s"] for call in direct_replay["communication_calls"]] == [call["current_communication_point_s"] for call in backend_replay["communication_calls"]]
        for key in ("rack_coolant_c", "cdu_primary_supply_c", "cdu_primary_return_c", "datacenter_primary_flow_gpm"):
            np.testing.assert_allclose(
                _observations(direct_replay["samples"], key),
                _observations(backend_replay["samples"], key),
                rtol=0,
                atol=1e-6,
            )
