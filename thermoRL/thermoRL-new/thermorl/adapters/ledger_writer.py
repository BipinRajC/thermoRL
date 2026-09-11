from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from thermorl.contracts.decision import Decision
from thermorl.contracts.ledger import (
    JobFeatures,
    LedgerAmbientState,
    LedgerRow,
    LedgerZoneState,
)
from thermorl.contracts.state import SimState
from thermorl.sim.config import N_ZONES, FacilityConfig
from thermorl.sim.kernels.thi import t_steady, thi_batch, thi_zone


def zone_snapshots(state: SimState, cfg: FacilityConfig) -> tuple[LedgerZoneState, ...]:
    racks = state.rack_T_c.shape[1]
    q_max = np.repeat(cfg.q_max_rack_kw.reshape(N_ZONES, 1), racks, axis=1)
    t_max = np.repeat(cfg.t_max_c.reshape(N_ZONES, 1), racks, axis=1)
    t_amb = np.repeat(state.zone_T_amb_c.reshape(N_ZONES, 1), racks, axis=1)
    d_max = np.repeat(cfg.d_max.reshape(N_ZONES, 1), racks, axis=1)
    t_ss = t_steady(state.rack_Q_kw, q_max, t_amb, t_max)
    thi = thi_batch(state.rack_T_c, t_ss, state.rack_d, t_max, d_max)
    thi_z = thi_zone(thi)
    rows = []
    for z in range(N_ZONES):
        rows.append(
            LedgerZoneState(
                T_c=float(state.rack_T_c[z].mean()),
                Q_kw=float(state.rack_Q_kw[z].sum()),
                d=float(state.rack_d[z].mean()),
                THI=float(thi_z[z]),
                util=float(state.rack_util[z].mean()),
                PUE=float(state.zone_pue_eff[z]),
                min_rack_thi=float(thi[z].min()),
                rack_spread=float(thi[z].max() - thi[z].min()),
                emergency_active=bool(state.zone_emergency[z]),
            )
        )
    return tuple(rows)


def rack_snapshots(
    state: SimState, cfg: FacilityConfig
) -> tuple[tuple[dict[str, float], ...], ...]:
    racks = state.rack_T_c.shape[1]
    q_max = np.repeat(cfg.q_max_rack_kw.reshape(N_ZONES, 1), racks, axis=1)
    t_max = np.repeat(cfg.t_max_c.reshape(N_ZONES, 1), racks, axis=1)
    t_amb = np.repeat(state.zone_T_amb_c.reshape(N_ZONES, 1), racks, axis=1)
    d_max = np.repeat(cfg.d_max.reshape(N_ZONES, 1), racks, axis=1)
    t_ss = t_steady(state.rack_Q_kw, q_max, t_amb, t_max)
    thi = thi_batch(state.rack_T_c, t_ss, state.rack_d, t_max, d_max)
    out: list[tuple[dict[str, float], ...]] = []
    for z in range(N_ZONES):
        zone_racks = []
        for r in range(racks):
            zone_racks.append(
                {
                    "T_c": float(state.rack_T_c[z, r]),
                    "Q_kw": float(state.rack_Q_kw[z, r]),
                    "d": float(state.rack_d[z, r]),
                    "THI": float(thi[z, r]),
                    "util": float(state.rack_util[z, r]),
                }
            )
        out.append(tuple(zone_racks))
    return tuple(out)


def build_row(
    *,
    run_id: str,
    episode_id: str,
    scenario_id: str,
    seed: int,
    backend: str,
    policy_id: str,
    policy_mode: str,
    state: SimState,
    cfg: FacilityConfig,
    decision: Decision,
    job: dict,
    seq: int,
) -> LedgerRow:
    zones = zone_snapshots(state, cfg)
    racks = rack_snapshots(state, cfg)
    feats = JobFeatures(
        mean_power_kw=float(job["mean_power_kw"]),
        duration_s=float(job["duration_s"]),
        nodes=int(job["nodes"]),
        gpus=int(job["gpus"]),
        density_kw_per_node=float(job["density_kw_per_node"]),
        workload_class=str(job["workload_class"]),
        qos=str(job["qos"]),
        priority=int(job["priority"]),
        wait_time_s=0.0,
    )
    predicted = tuple({"THI": float(c.thi_after_pred or c.thi_before)} for c in decision.candidates)
    return LedgerRow(
        decision_id=f"{run_id}::{episode_id}::d_{seq:06d}",
        run_id=run_id,
        episode_id=episode_id,
        scenario_id=scenario_id,
        scenario_mode="evaluation",
        seed=seed,
        backend=backend,
        sim_time_s=state.sim_time_s,
        tick=state.tick,
        wall_time_ms=0.0,
        policy_id=policy_id,
        policy_mode=policy_mode,
        policy_version="1.0.0",
        job_id=decision.job_id,
        job_features=feats,
        ambient_state=LedgerAmbientState(
            t_amb_c=tuple(float(x) for x in state.zone_T_amb_c.tolist()),
            carbon_intensity=float(state.carbon_intensity),
        ),
        eligible_zones=tuple(int(z) for z in job["eligible_zones"]),
        action=decision.action,
        chosen_zone=decision.chosen_zone,
        chosen_rack=decision.chosen_rack,
        rack_rule_id=decision.rack_rule_id,
        candidates=decision.candidates,
        zone_state_before=zones,
        rack_state_before=racks,
        predicted_post_action_state=predicted,
        lambdas={
            "thi_z1": float(state.lambdas[0]),
            "thi_z2": float(state.lambdas[1]),
            "thi_z3": float(state.lambdas[2]),
            "throughput": float(state.lambdas[3]),
            "slo": float(state.lambdas[4]),
        },
        constraint_slack={
            "thi_z1": zones[0].THI - 0.10,
            "thi_z2": zones[1].THI - 0.10,
            "thi_z3": zones[2].THI - 0.10,
            "throughput": 0.0,
            "slo": 0.0,
        },
        reward_components={"carbon": 0.0, "cooling": 0.0, "total": 0.0},
        reason_code=decision.reason_code,
        reason_text=decision.reason_text,
        counterfactual_zone=None,
        counterfactual_delta_thi=None,
        emergency_cooling_active=tuple(bool(x) for x in state.zone_emergency.tolist()),
        defer_count=0,
        next_eligible_s=None,
        forced_placement_flag=False,
        queue_depth=0,
        arrival_rate_est=0.0,
        outcome=None,
    )


class LedgerWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")

    def write(self, row: LedgerRow) -> None:
        self._fh.write(json.dumps(row.to_jsonable()) + "\n")

    def close(self) -> None:
        self._fh.close()
