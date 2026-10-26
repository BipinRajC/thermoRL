from pathlib import Path

import numpy as np
import pytest
import yaml

from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine, is_power_tick, rack_kw_from_power_df
from thermorl2.raps_adapter.power_model import legacy_config, rack_power_bounds, raps_rack_kw

pytestmark = pytest.mark.integration
PRIMARY = yaml.safe_load((Path(__file__).parents[2] / "thermorl2/experiments/configs/primary.yaml").read_text())["system"]


@pytest.mark.parametrize("system", [PRIMARY])
def test_build_engine_defaults(system):
    engine = build_engine(EngineSpec(system, "2m"), jobs=[])
    cfg = legacy_config(system)
    assert engine.cooling_model is None
    assert engine.config["NUM_CDUS"] * engine.config["RACKS_PER_CDU"] == cfg["NUM_CDUS"] * cfg["RACKS_PER_CDU"]
    assert engine.timestep_start == 0 and engine.time_delta == cfg["POWER_UPDATE_FREQ"]
    assert engine.sim_config.output == "none" and engine.noui is True


@pytest.mark.parametrize("system", [PRIMARY])
def test_idle_power_reconciles(system):
    cfg = legacy_config(system)
    engine = build_engine(EngineSpec(system, "2m"), jobs=[])
    ticks = [tick for tick in engine.run_simulation() if is_power_tick(tick, engine.time_delta)]
    assert len(ticks) == 120 // engine.time_delta
    reference = raps_rack_kw(cfg, 0, 0)
    for tick in ticks:
        power = rack_kw_from_power_df(tick.power_df, cfg["RACKS_PER_CDU"])
        assert power.shape == (cfg["NUM_CDUS"] * cfg["RACKS_PER_CDU"],)
        assert abs(power.sum() - tick.power_df["Sum"].sum()) < 1e-6
        assert abs(power.mean() - reference) < 0.05


@pytest.mark.parametrize("system", [PRIMARY])
def test_power_df_is_stale_between_ticks(system):
    engine = build_engine(EngineSpec(system, "2m"), jobs=[])
    frames = [tick.power_df for tick in engine.run_simulation()]
    assert len(frames) == 120 and all(frame is not None for frame in frames)
    # Hold every reference, so Python cannot reuse ids of collected frames.
    assert len({id(frame) for frame in frames}) == 120 // engine.time_delta


def test_raps_rack_reference_matches_lossless_lassen():
    cfg = legacy_config("lassen")
    idle, peak = rack_power_bounds(cfg)
    assert raps_rack_kw(cfg, 0, 0) == idle
    assert raps_rack_kw(cfg, cfg["CPUS_PER_NODE"], cfg["GPUS_PER_NODE"]) == peak


def test_raps_rack_reference_accounts_for_summit_losses():
    cfg = legacy_config("summit")
    idle, peak = rack_power_bounds(cfg)
    actual_idle = raps_rack_kw(cfg, 0, 0)
    actual_peak = raps_rack_kw(cfg, cfg["CPUS_PER_NODE"], cfg["GPUS_PER_NODE"])
    assert actual_idle == pytest.approx(13.822619, abs=0.01)
    assert actual_peak == pytest.approx(49.323257, abs=0.01)
    assert actual_idle - idle == pytest.approx(0.620905, abs=0.01)
    assert actual_peak - peak == pytest.approx(2.040930, abs=0.01)


def test_rack_power_flattening_is_row_major():
    import pandas as pd
    frame = pd.DataFrame({"Rack 1": [1.0, 3.0], "Rack 2": [2.0, 4.0], "Sum": [3.0, 7.0]})
    np.testing.assert_array_equal(rack_kw_from_power_df(frame, 2), [1, 2, 3, 4])
