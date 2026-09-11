from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from thermorl.contracts.ledger import LedgerRow
from thermorl.contracts.viz import VizEvent, VizFrame, VizMetrics, VizZone

ZONE_NAMES = ("Air", "Direct-to-chip", "Immersion")


def _thi_hex(thi: float, p10: float, p90: float) -> str:
    span = max(p90 - p10, 1e-6)
    u = min(1.0, max(0.0, (thi - p10) / span))
    r = int((1.0 - u) * 255)
    g = int(u * 0.75 * 255)
    b = 38
    return f"#{r:02x}{g:02x}{b:02x}"


def _load_rows(path: Path) -> list[LedgerRow]:
    rows: list[LedgerRow] = []
    for line in path.read_text().splitlines():
        if line:
            rows.append(LedgerRow.from_jsonable(json.loads(line)))
    return rows


def _regime(scenario_id: str, sim_time_s: float) -> str:
    if scenario_id != "ramp":
        return scenario_id.replace("_", " ").title()
    if sim_time_s < 2400:
        return "Normal Operation"
    if sim_time_s < 4800:
        return "Demand Surge"
    return "Sustained Overload"


def _metrics_from_prefix(rows: list[LedgerRow], current: LedgerRow) -> VizMetrics:
    assigned = [r for r in rows if r.action != "DEFER"]
    completed = [
        r for r in assigned if r.sim_time_s + r.job_features.duration_s <= current.sim_time_s
    ]
    n_done = len(completed)
    denom = max(n_done, 1)
    zone_steps = 0
    violations = 0
    emergencies = 0
    for r in rows:
        for z in r.zone_state_before:
            zone_steps += 1
            if z.THI < 0.10:
                violations += 1
            if z.emergency_active:
                emergencies += 1
    load_kw = sum(z.Q_kw for z in current.zone_state_before)
    return VizMetrics(
        jobs_completed=n_done,
        mean_wait_s=0.0,
        slo_compliance=1.0,
        violations_per_1k_jobs=1000.0 * violations / denom,
        hotspot_minutes_per_1k_jobs=0.0,
        emergency_events_per_1k_jobs=1000.0 * emergencies / denom,
        kg_co2_per_job=0.0,
        kwh_cooling_per_job=0.0,
        offered_demand_ratio=0.35,
        physical_facility_load_kw=load_kw,
    )


def project(
    ledger_path: Path,
    frames_path: Path,
    metrics_path: Path,
    policy_mode: str,
) -> tuple[Path, Path]:
    rows = _load_rows(ledger_path)
    by_tick: dict[int, list[LedgerRow]] = {}
    for r in rows:
        by_tick.setdefault(r.tick, []).append(r)

    frames: list[VizFrame] = []
    thi_vals: list[float] = []
    seen: list[LedgerRow] = []
    for tick in sorted(by_tick):
        tick_rows = by_tick[tick]
        seen.extend(tick_rows)
        sample = tick_rows[0]
        zones = []
        racks = []
        for i, z in enumerate(sample.zone_state_before):
            zones.append(
                VizZone(
                    id=i,
                    name=ZONE_NAMES[i] if i < len(ZONE_NAMES) else f"Z{i}",
                    THI=z.THI,
                    T_c=z.T_c,
                    load_kw=z.Q_kw,
                    util=z.util,
                    PUE=z.PUE,
                    emergency=z.emergency_active,
                    min_rack_thi=z.min_rack_thi,
                    rack_spread=z.rack_spread,
                )
            )
            thi_vals.append(z.THI)
            thi_vals.append(z.min_rack_thi)
            if i < len(sample.rack_state_before) and sample.rack_state_before[i]:
                zone_racks = tuple(
                    {"THI": float(rk["THI"]), "T_c": float(rk["T_c"]), "util": float(rk["util"])}
                    for rk in sample.rack_state_before[i]
                )
                for rk in zone_racks:
                    thi_vals.append(rk["THI"])
            else:
                zone_racks = ({"THI": z.min_rack_thi, "T_c": z.T_c, "util": z.util},)
            racks.append(zone_racks)
        events = []
        for r in tick_rows:
            if r.action == "DEFER":
                events.append(VizEvent(type="defer", job_id=r.job_id, defer_count=r.defer_count))
            else:
                events.append(
                    VizEvent(
                        type="place",
                        job_id=r.job_id,
                        zone=r.chosen_zone,
                        rack=r.chosen_rack,
                        decision_id=r.decision_id,
                    )
                )
        frames.append(
            VizFrame(
                t=tick,
                sim_time_s=sample.sim_time_s,
                regime=_regime(sample.scenario_id, sample.sim_time_s),
                policy_mode=policy_mode,
                zones=tuple(zones),
                racks=tuple(racks),
                events=tuple(events),
                metrics=_metrics_from_prefix(seen, sample),
                advanced={"lambdas": [sample.lambdas[k] for k in sorted(sample.lambdas)]},
            )
        )

    arr = np.array(thi_vals, dtype=np.float64) if thi_vals else np.array([0.0, 1.0])
    p10 = float(np.percentile(arr, 10))
    p90 = float(np.percentile(arr, 90))
    anchors = {
        "thi_p10": p10,
        "thi_p90": p90,
        "policy_mode": policy_mode,
        "n_frames": len(frames),
    }
    for fr in frames:
        coloured = []
        for zone in fr.racks:
            coloured.append(
                tuple({**rk, "color": _thi_hex(float(rk["THI"]), p10, p90)} for rk in zone)
            )
        object.__setattr__(fr, "racks", tuple(coloured))

    frames_path.parent.mkdir(parents=True, exist_ok=True)
    with frames_path.open("w", encoding="utf-8") as fh:
        for fr in frames:
            fh.write(
                json.dumps(
                    {
                        "t": fr.t,
                        "sim_time_s": fr.sim_time_s,
                        "regime": fr.regime,
                        "policy_mode": fr.policy_mode,
                        "zones": [
                            {
                                "id": z.id,
                                "name": z.name,
                                "THI": z.THI,
                                "T_c": z.T_c,
                                "load_kw": z.load_kw,
                                "util": z.util,
                                "PUE": z.PUE,
                                "emergency": z.emergency,
                                "min_rack_thi": z.min_rack_thi,
                                "rack_spread": z.rack_spread,
                            }
                            for z in fr.zones
                        ],
                        "racks": [list(zone) for zone in fr.racks],
                        "events": [
                            {
                                "type": e.type,
                                "job_id": e.job_id,
                                "zone": e.zone,
                                "rack": e.rack,
                                "decision_id": e.decision_id,
                                "defer_count": e.defer_count,
                            }
                            for e in fr.events
                        ],
                        "metrics": {
                            "jobs_completed": fr.metrics.jobs_completed,
                            "mean_wait_s": fr.metrics.mean_wait_s,
                            "slo_compliance": fr.metrics.slo_compliance,
                            "violations_per_1k_jobs": fr.metrics.violations_per_1k_jobs,
                            "hotspot_minutes_per_1k_jobs": fr.metrics.hotspot_minutes_per_1k_jobs,
                            "emergency_events_per_1k_jobs": fr.metrics.emergency_events_per_1k_jobs,
                            "kg_co2_per_job": fr.metrics.kg_co2_per_job,
                            "kwh_cooling_per_job": fr.metrics.kwh_cooling_per_job,
                            "offered_demand_ratio": fr.metrics.offered_demand_ratio,
                            "physical_facility_load_kw": fr.metrics.physical_facility_load_kw,
                        },
                        "advanced": fr.advanced,
                    }
                )
                + "\n"
            )
    metrics_path.write_text(json.dumps(anchors, indent=2) + "\n")
    return frames_path, metrics_path
