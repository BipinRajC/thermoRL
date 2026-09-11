from __future__ import annotations

from pathlib import Path

import pandas as pd

from thermorl.adapters.ledger_writer import LedgerWriter, build_row
from thermorl.contracts.manifest import StageManifest
from thermorl.contracts.state import SimState
from thermorl.policies import get_policy
from thermorl.policies.base import score_candidates
from thermorl.sim.config import FacilityConfig
from thermorl.sim.engine import step
from thermorl.sim.kernels.heat import heat_inject, heat_release


def _job_dict(row: pd.Series) -> dict:
    ez = row["eligible_zones"]
    if hasattr(ez, "tolist"):
        ez = tuple(int(x) for x in ez)
    else:
        ez = tuple(int(x) for x in ez)
    return {
        "event_id": str(row["event_id"]),
        "arrival_s": float(row["arrival_s"]),
        "duration_s": float(row["duration_s"]),
        "mean_power_kw": float(row["mean_power_kw"]),
        "nodes": int(row["nodes"]),
        "gpus": int(row["gpus"]),
        "density_kw_per_node": float(row["density_kw_per_node"]),
        "workload_class": str(row["workload_class"]),
        "qos": str(row["qos"]),
        "priority": int(row["priority"]),
        "eligible_zones": ez,
    }


def run_episode(
    episode_path: Path,
    policy_id: str,
    seed: int,
    tick_s: float,
    target_offered_load_ratio: float,
    out_dir: Path,
    scenario_id: str = "normal_operation",
) -> StageManifest:
    cfg = FacilityConfig.from_base_yaml()
    jobs = pd.read_parquet(episode_path).sort_values("arrival_s").reset_index(drop=True)
    policy = get_policy(policy_id)
    state = SimState.empty(racks_per_zone=cfg.racks_per_zone, seed=seed)
    state.zone_T_amb_c = cfg.t_amb_base_c.copy()
    state.zone_pue_eff = cfg.pue_base.copy()
    state.carbon_intensity = 0.4

    out_dir.mkdir(parents=True, exist_ok=True)
    writer = LedgerWriter(out_dir / "ledger.jsonl")
    run_id = f"run_{policy_id}_{seed}"
    horizon = float(jobs["arrival_s"].max()) + tick_s
    job_i = 0
    seq = 0
    running: list[tuple[float, int, int, float]] = []

    while state.sim_time_s <= horizon and job_i < len(jobs):
        still = []
        for end_s, z, r, pkw in running:
            if end_s <= state.sim_time_s:
                state.rack_Q_kw = heat_release(state.rack_Q_kw, z, r, pkw)
            else:
                still.append((end_s, z, r, pkw))
        running = still

        while job_i < len(jobs) and float(jobs.loc[job_i, "arrival_s"]) <= state.sim_time_s:
            job = _job_dict(jobs.loc[job_i])
            cands = score_candidates(
                state, cfg, job["mean_power_kw"], job["density_kw_per_node"], job["eligible_zones"]
            )
            decision = policy.decide(
                state,
                cands,
                {"job_id": job["event_id"], "cfg": cfg, "mean_power_kw": job["mean_power_kw"]},
            )
            writer.write(
                build_row(
                    run_id=run_id,
                    episode_id="ep_000",
                    scenario_id=scenario_id,
                    seed=seed,
                    backend="python",
                    policy_id=policy.policy_id,
                    policy_mode=policy.policy_mode,
                    state=state,
                    cfg=cfg,
                    decision=decision,
                    job=job,
                    seq=seq,
                )
            )
            seq += 1
            if decision.action != "DEFER" and decision.chosen_zone is not None:
                z = decision.chosen_zone
                r = int(decision.chosen_rack or 0)
                state.rack_Q_kw = heat_inject(state.rack_Q_kw, z, r, job["mean_power_kw"])
                running.append((state.sim_time_s + job["duration_s"], z, r, job["mean_power_kw"]))
            job_i += 1

        state = step(state, (), cfg, dt_s=tick_s, job_power_kw=0.0)

    writer.close()
    return StageManifest(
        stage="s3",
        inputs=(str(episode_path),),
        outputs=(str(out_dir / "ledger.jsonl"),),
        target_offered_load_ratio=target_offered_load_ratio,
        realised_offered_load_ratio=None,
        seed=seed,
    )
