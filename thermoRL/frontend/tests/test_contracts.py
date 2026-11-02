"""Frozen contract tests. Schemas must construct, clone cheaply, and stay closed."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import get_args, get_type_hints

import numpy as np
import pytest
import yaml

from thermorl.contracts.decision import (
    ACTIONS,
    Candidate,
    Decision,
    Placement,
)
from thermorl.contracts.ledger import (
    JobFeatures,
    LedgerAmbientState,
    LedgerOutcome,
    LedgerRow,
    LedgerZoneState,
)
from thermorl.contracts.manifest import RunManifest, StageManifest
from thermorl.contracts.state import (
    AmbientState,
    JobQueue,
    MetricsAccumulator,
    RackState,
    RunningSet,
    SimState,
    ZoneState,
)
from thermorl.contracts.viz import VizEvent, VizFrame, VizMetrics, VizZone
from thermorl.contracts.workload import BatchJobEvent, RequestEvent, WorkloadEvent

Z = 3
R = 16


def _batch_job(**overrides: object) -> BatchJobEvent:
    fields: dict[str, object] = {
        "event_id": "alb-0001",
        "kind": "batch",
        "arrival_s": 0.0,
        "duration_s": 1998.0,
        "power_profile_kw": np.array([31.1], dtype=np.float32),
        "mean_power_kw": 31.1,
        "peak_power_kw": 40.0,
        "nodes": 4,
        "gpus": 8,
        "gpu_milli": 8000,
        "cpu_milli": 16000,
        "mem_mib": 65536,
        "density_kw_per_node": 7.775,
        "workload_class": "training",
        "qos": "LS",
        "priority": 3,
        "eligible_zones": (0, 1, 2),
    }
    fields.update(overrides)
    return BatchJobEvent(**fields)  # type: ignore[arg-type]


def test_batch_job_event_fields_match_spec() -> None:
    job = _batch_job()
    assert job.kind == "batch"
    assert job.event_id == "alb-0001"
    assert job.arrival_s == 0.0
    assert job.duration_s == 1998.0
    assert job.mean_power_kw == 31.1
    assert job.peak_power_kw == 40.0
    assert job.nodes == 4
    assert job.gpus == 8
    assert job.gpu_milli == 8000
    assert job.cpu_milli == 16000
    assert job.mem_mib == 65536
    assert job.density_kw_per_node == pytest.approx(7.775)
    assert job.workload_class == "training"
    assert job.qos == "LS"
    assert job.priority == 3
    assert job.eligible_zones == (0, 1, 2)
    assert isinstance(job.power_profile_kw, np.ndarray)


def test_request_event_is_defined_not_implemented() -> None:
    ev = RequestEvent(
        event_id="req-1",
        kind="request",
        arrival_s=1.0,
        model_class="llama",
        tokens_in=128,
        tokens_out=64,
        slo_ms=50.0,
    )
    assert ev.kind == "request"
    assert RequestEvent in get_args(WorkloadEvent)
    assert BatchJobEvent in get_args(WorkloadEvent)


def test_simstate_arrays_are_shaped_z_by_r() -> None:
    state = SimState.empty(racks_per_zone=R, seed=42)
    assert state.rack_T_c.shape == (Z, R)
    assert state.rack_Q_kw.shape == (Z, R)
    assert state.rack_d.shape == (Z, R)
    assert state.rack_util.shape == (Z, R)
    assert state.zone_T_amb_c.shape == (Z,)
    assert state.zone_pue_eff.shape == (Z,)
    assert state.zone_emergency.shape == (Z,)
    assert state.lambdas.shape == (5,)
    assert state.rack_T_c.dtype == np.float32
    assert state.rack_Q_kw.dtype == np.float32
    assert state.rack_d.dtype == np.float32
    assert state.rack_util.dtype == np.float32


def test_simstate_clone_is_independent() -> None:
    state = SimState.empty(racks_per_zone=R, seed=7)
    state.rack_T_c[0, 0] = 25.0
    cloned = state.clone()
    cloned.rack_T_c[0, 0] = 40.0
    assert state.rack_T_c[0, 0] == pytest.approx(25.0)
    assert cloned.rack_T_c[0, 0] == pytest.approx(40.0)
    assert cloned.tick == state.tick
    assert cloned.sim_time_s == state.sim_time_s
    assert cloned.rng is not state.rng


def test_snapshot_types_are_frozen() -> None:
    zone = ZoneState(
        zone_id=0,
        T_c=24.1,
        Q_kw=3620.0,
        d=0.11,
        THI=0.21,
        util=0.905,
        PUE=1.52,
        min_rack_thi=0.21,
        rack_spread=0.14,
        emergency_active=False,
    )
    rack = RackState(rack_id=0, T_c=25.0, Q_kw=230.0, d=0.12, THI=0.19, util=0.94)
    amb = AmbientState(t_amb_c=(19.2, 28.4, 30.1), carbon_intensity=0.62)
    with pytest.raises(FrozenInstanceError):
        zone.T_c = 99.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        rack.T_c = 99.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        amb.carbon_intensity = 1.0  # type: ignore[misc]


def test_scheduling_stubs_exist() -> None:
    assert is_dataclass(JobQueue)
    assert is_dataclass(RunningSet)
    assert is_dataclass(MetricsAccumulator)
    q = JobQueue()
    r = RunningSet()
    a = MetricsAccumulator()
    assert q is not None and r is not None and a is not None


def test_actions_are_exactly_four_placement_actions() -> None:
    assert ACTIONS == frozenset({"ASSIGN_Z1", "ASSIGN_Z2", "ASSIGN_Z3", "DEFER"})
    assert "THROTTLE" not in ACTIONS


def test_decision_rejects_unknown_action() -> None:
    with pytest.raises((ValueError, TypeError)):
        Decision(
            job_id="j1",
            action="THROTTLE",  # type: ignore[arg-type]
            chosen_zone=None,
            chosen_rack=None,
            rack_rule_id="coolest_eligible",
            candidates=(),
            reason_code="BAD",
            reason_text="throttle is not a Phase 1 action",
        )


def test_candidate_and_decision_and_placement_construct() -> None:
    cand = Candidate(
        zone_id=1,
        rack_id=7,
        feasible=True,
        infeasible_reason=None,
        thi_before=0.44,
        thi_after_pred=0.39,
        delta_thi=-0.05,
        cooling_cost_kw=6.3,
        carbon_cost_kg=0.42,
        constraint_slack=0.34,
        lookahead_score=2.71,
    )
    dec = Decision(
        job_id="alb-0004517",
        action="ASSIGN_Z2",
        chosen_zone=1,
        chosen_rack=7,
        rack_rule_id="coolest_eligible",
        candidates=(cand,),
        reason_code="MAX_LOOKAHEAD_SCORE",
        reason_text="Z2 preserves the most headroom",
    )
    plc = Placement(job_id="alb-0004517", zone_id=1, rack_id=7)
    assert dec.action == "ASSIGN_Z2"
    assert dec.candidates[0].zone_id == 1
    assert plc.zone_id == 1


def test_ledger_row_round_trips_json() -> None:
    row = LedgerRow(
        decision_id="run_7f3a::ep_012::d_004517",
        run_id="run_7f3a",
        episode_id="ep_012",
        scenario_id="ramp",
        scenario_mode="demo",
        seed=42,
        backend="python",
        sim_time_s=3480.0,
        tick=174,
        wall_time_ms=1712.0,
        policy_id="thi_lookahead",
        policy_mode="THI-Lookahead",
        policy_version="1.0.0",
        job_id="alb-0004517",
        job_features=JobFeatures(
            mean_power_kw=31.4,
            duration_s=1980.0,
            nodes=4,
            gpus=8,
            density_kw_per_node=7.85,
            workload_class="training",
            qos="LS",
            priority=3,
            wait_time_s=40.0,
        ),
        ambient_state=LedgerAmbientState(t_amb_c=(19.2, 28.4, 30.1), carbon_intensity=0.62),
        eligible_zones=(1, 2),
        action="ASSIGN_Z2",
        chosen_zone=1,
        chosen_rack=7,
        rack_rule_id="coolest_eligible",
        candidates=(
            Candidate(
                zone_id=1,
                rack_id=7,
                feasible=True,
                infeasible_reason=None,
                thi_before=0.44,
                thi_after_pred=0.39,
                delta_thi=-0.05,
                cooling_cost_kw=6.3,
                carbon_cost_kg=0.42,
                constraint_slack=0.34,
                lookahead_score=2.71,
            ),
        ),
        zone_state_before=(
            LedgerZoneState(
                T_c=24.1,
                Q_kw=3620.0,
                d=0.11,
                THI=0.21,
                util=0.905,
                PUE=1.52,
                min_rack_thi=0.21,
                rack_spread=0.14,
                emergency_active=False,
            ),
        ),
        rack_state_before=(),
        predicted_post_action_state=({"THI": 0.39},),
        lambdas={
            "thi_z1": 1.31,
            "thi_z2": 1.12,
            "thi_z3": 1.04,
            "throughput": 0.42,
            "slo": 0.18,
        },
        constraint_slack={
            "thi_z1": 0.11,
            "thi_z2": 0.34,
            "thi_z3": 0.48,
            "throughput": 0.06,
            "slo": 0.22,
        },
        reward_components={"carbon": -0.42, "cooling": -0.31, "total": -0.73},
        reason_code="MAX_LOOKAHEAD_SCORE",
        reason_text="Z2 preserves the most headroom over 10 ticks",
        counterfactual_zone=2,
        counterfactual_delta_thi=-0.02,
        emergency_cooling_active=(False, False, False),
        defer_count=0,
        next_eligible_s=None,
        forced_placement_flag=False,
        queue_depth=84,
        arrival_rate_est=0.42,
        outcome=None,
    )
    payload = row.to_jsonable()
    text = json.dumps(payload)
    restored = LedgerRow.from_jsonable(json.loads(text))
    assert restored.decision_id == row.decision_id
    assert restored.action == "ASSIGN_Z2"
    assert restored.outcome is None
    assert restored.job_features.mean_power_kw == 31.4


def test_ledger_outcome_is_optional_s4_backfill() -> None:
    outcome = LedgerOutcome(
        horizon_ticks=10,
        thi_actual_h=(0.19, 0.36, 0.57),
        thi_predicted_h=(0.21, 0.39, 0.58),
        prediction_error=(-0.02, -0.03, -0.01),
        emergency_triggered_within_h=False,
        regret_vs_best_counterfactual=0.014,
        job_completed=True,
        job_completion_s=5460.0,
    )
    assert outcome.horizon_ticks == 10
    assert outcome.job_completed is True


def test_viz_frame_matches_section_9() -> None:
    frame = VizFrame(
        t=174,
        sim_time_s=3480.0,
        regime="Demand Surge",
        policy_mode="THI-Lookahead",
        zones=(
            VizZone(
                id=0,
                name="Air",
                THI=0.21,
                T_c=24.1,
                load_kw=3620.0,
                util=0.905,
                PUE=1.52,
                emergency=False,
                min_rack_thi=0.19,
                rack_spread=0.14,
            ),
        ),
        racks=(({"THI": 0.19, "T_c": 25.0, "util": 0.94},),),
        events=(VizEvent(type="place", job_id="alb-0004517", zone=1, rack=7, decision_id="d1"),),
        metrics=VizMetrics(
            jobs_completed=1284,
            mean_wait_s=71.2,
            slo_compliance=0.94,
            violations_per_1k_jobs=43.8,
            hotspot_minutes_per_1k_jobs=12.1,
            emergency_events_per_1k_jobs=2.3,
            kg_co2_per_job=7.06,
            kwh_cooling_per_job=4.70,
            offered_demand_ratio=2.4,
            physical_facility_load_kw=18420.0,
        ),
        advanced={"lambdas": [1.31, 1.12, 1.04, 0.42, 0.18]},
    )
    assert frame.metrics.offered_demand_ratio == 2.4
    assert "offered_demand_ratio" in frame.metrics.__dataclass_fields__
    assert "physical_facility_load_kw" in frame.metrics.__dataclass_fields__
    assert frame.events[0].type == "place"


def test_manifest_requires_target_offered_load_ratio() -> None:
    hints = get_type_hints(RunManifest)
    assert "target_offered_load_ratio" in hints
    stage_hints = get_type_hints(StageManifest)
    assert (
        "target_offered_load_ratio" in stage_hints
        or "target_offered_load_ratio" in get_type_hints(RunManifest)
    )
    with pytest.raises(TypeError):
        RunManifest(  # type: ignore[call-arg]
            run_id="r1",
            seed=42,
            scenario_id="ramp",
            policy_id="round_robin",
            backend="python",
        )
    man = RunManifest(
        run_id="r1",
        seed=42,
        scenario_id="ramp",
        policy_id="round_robin",
        backend="python",
        target_offered_load_ratio=3.1,
        workload_source="alibaba_gpu_v2023",
        power_calibration_source="pm100",
        facility_capacity_kw=20000.0,
        arrival_process="poisson_with_diurnal_multiplier",
        scaling_method="explicit_rate_calibration",
    )
    assert man.target_offered_load_ratio == 3.1


def test_stage_manifest_constructs() -> None:
    sm = StageManifest(
        stage="s2",
        inputs=("calibration.json",),
        outputs=("episode.parquet",),
        target_offered_load_ratio=0.35,
        realised_offered_load_ratio=0.34,
        seed=42,
    )
    assert sm.stage == "s2"
    assert sm.target_offered_load_ratio == 0.35


def test_base_yaml_locks_o3_and_o2() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / "config" / "base.yaml").read_text())
    zones = cfg["zones"]
    assert len(zones) == 3
    assert all(z["racks"] == 16 for z in zones)
    assert [z["capacity_kw"] for z in zones] == [4000.0, 8000.0, 8000.0]
    assert [z["tau_s"] for z in zones] == [60.0, 15.0, 300.0]
    assert cfg["pue"]["k_z"] == [0.35, 0.15, 0.08]
    assert cfg["pue"]["theta"] == 0.70
    assert cfg["pue"]["p"] == 2
    assert cfg["thi"]["epsilon"] == 0.10
    assert cfg["facility_capacity_kw"] == 20000.0


def test_scenario_yaml_matches_spec_ratios() -> None:
    root = Path(__file__).resolve().parents[1] / "config" / "scenarios"
    normal = yaml.safe_load((root / "normal_operation.yaml").read_text())
    surge = yaml.safe_load((root / "demand_surge.yaml").read_text())
    overload = yaml.safe_load((root / "sustained_overload.yaml").read_text())
    ramp = yaml.safe_load((root / "ramp.yaml").read_text())
    assert normal["ratio_offpeak"] == 0.35
    assert normal["ratio_peak"] == 0.85
    assert surge["ratio_offpeak"] == 0.90
    assert surge["ratio_peak"] == 3.0
    assert overload["ratio_offpeak"] == 3.1
    assert overload["ratio_peak"] == 7.8
    assert ramp["duration_sim_s"] == 7200
    assert ramp["tick_s"] == 20
    assert [s["name"] for s in ramp["segments"]] == [
        "Normal Operation",
        "Demand Surge",
        "Sustained Overload",
    ]


def test_profiles_exist() -> None:
    root = Path(__file__).resolve().parents[1] / "config" / "profiles"
    default = yaml.safe_load((root / "phase1_default.yaml").read_text())
    paper = yaml.safe_load((root / "paper_parity.yaml").read_text())
    assert default["tick_s"] == 20
    assert paper["tick_s"] == 300
    assert paper["thi_form"] == "legacy_q_over_qmax"
    assert default["thi_form"] == "t_ss"
