from __future__ import annotations

from typing import Protocol

import numpy as np

from thermorl.contracts.decision import Candidate, Decision
from thermorl.contracts.state import SimState
from thermorl.sim.capacity import feasible
from thermorl.sim.config import N_ZONES, FacilityConfig
from thermorl.sim.kernels.thi import t_steady, thi_batch, thi_zone


class Policy(Protocol):
    policy_id: str
    policy_mode: str

    def decide(self, state: SimState, candidates: tuple[Candidate, ...], ctx: dict) -> Decision: ...


def coolest_eligible_rack(state: SimState, zone_id: int) -> int:
    return int(np.argmin(state.rack_T_c[zone_id]))


def score_candidates(
    state: SimState,
    cfg: FacilityConfig,
    mean_power_kw: float,
    density_kw_per_node: float,
    eligible_zones: tuple[int, ...],
) -> tuple[Candidate, ...]:
    racks = state.rack_T_c.shape[1]
    q_max = np.repeat(cfg.q_max_rack_kw.reshape(N_ZONES, 1), racks, axis=1)
    t_max = np.repeat(cfg.t_max_c.reshape(N_ZONES, 1), racks, axis=1)
    t_amb = np.repeat(state.zone_T_amb_c.reshape(N_ZONES, 1), racks, axis=1)
    d_max = np.repeat(cfg.d_max.reshape(N_ZONES, 1), racks, axis=1)
    t_ss = t_steady(state.rack_Q_kw, q_max, t_amb, t_max)
    thi = thi_batch(state.rack_T_c, t_ss, state.rack_d, t_max, d_max)
    thi_z = thi_zone(thi)

    out: list[Candidate] = []
    for z in range(N_ZONES):
        rack = coolest_eligible_rack(state, z)
        ok, reason = feasible(
            z,
            rack,
            float(state.rack_Q_kw[z, rack]),
            mean_power_kw,
            density_kw_per_node,
            cfg,
        )
        if z not in eligible_zones and ok:
            ok, reason = False, "none_eligible"
        q_after = float(state.rack_Q_kw[z, rack] + mean_power_kw)
        t_ss_after = float(
            t_steady(
                np.array([[q_after]], dtype=np.float32),
                np.array([[float(cfg.q_max_rack_kw[z])]], dtype=np.float32),
                np.array([[float(state.zone_T_amb_c[z])]], dtype=np.float32),
                np.array([[float(cfg.t_max_c[z])]], dtype=np.float32),
            )[0, 0]
        )
        thi_after = float(
            thi_batch(
                np.array([[float(state.rack_T_c[z, rack])]], dtype=np.float32),
                np.array([[t_ss_after]], dtype=np.float32),
                np.array([[float(state.rack_d[z, rack])]], dtype=np.float32),
                np.array([[float(cfg.t_max_c[z])]], dtype=np.float32),
                np.array([[float(cfg.d_max[z])]], dtype=np.float32),
            )[0, 0]
        )
        pue = float(state.zone_pue_eff[z])
        cooling = mean_power_kw * max(pue - 1.0, 0.0)
        carbon = state.carbon_intensity * mean_power_kw * pue
        thi_before = float(thi_z[z])
        out.append(
            Candidate(
                zone_id=z,
                rack_id=rack,
                feasible=ok,
                infeasible_reason=None if ok else reason,
                thi_before=thi_before,
                thi_after_pred=thi_after if ok else None,
                delta_thi=(thi_after - thi_before) if ok else None,
                cooling_cost_kw=cooling if ok else None,
                carbon_cost_kg=carbon if ok else None,
                constraint_slack=thi_before - 0.10,
                lookahead_score=None,
            )
        )
    return tuple(out)


def pick(
    job_id: str,
    action: str,
    cand: Candidate | None,
    candidates: tuple[Candidate, ...],
    reason_code: str,
    reason_text: str,
    rack_rule_id: str = "coolest_eligible",
) -> Decision:
    return Decision(
        job_id=job_id,
        action=action,  # type: ignore[arg-type]
        chosen_zone=None if cand is None else cand.zone_id,
        chosen_rack=None if cand is None else cand.rack_id,
        rack_rule_id=rack_rule_id,
        candidates=candidates,
        reason_code=reason_code,
        reason_text=reason_text,
    )


def assign_action(zone_id: int) -> str:
    return f"ASSIGN_Z{zone_id + 1}"


def first_feasible(candidates: tuple[Candidate, ...]) -> Candidate | None:
    for c in candidates:
        if c.feasible:
            return c
    return None


POLICY_IDS: frozenset[str] = frozenset(
    {
        "fcfs_naive",
        "round_robin",
        "threshold_reactive",
        "carbon_only",
        "thi_greedy",
        "thi_lookahead",
        "oracle_lp",
    }
)
