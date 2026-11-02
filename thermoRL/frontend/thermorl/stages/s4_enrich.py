from __future__ import annotations

import json
from pathlib import Path

from thermorl.contracts.ledger import LedgerOutcome, LedgerRow


def _load_rows(path: Path) -> list[LedgerRow]:
    rows: list[LedgerRow] = []
    for line in path.read_text().splitlines():
        if line:
            rows.append(LedgerRow.from_jsonable(json.loads(line)))
    return rows


def _thi_at(row: LedgerRow) -> tuple[float, float, float]:
    vals = tuple(float(z.THI) for z in row.zone_state_before)
    padded = (vals + (0.0, 0.0, 0.0))[:3]
    return padded


def _predicted(row: LedgerRow) -> tuple[float, float, float]:
    vals = tuple(float(p.get("THI", 0.0)) for p in row.predicted_post_action_state)
    padded = (vals + (0.0, 0.0, 0.0))[:3]
    return padded


def enrich(
    ledger_in: Path,
    ledger_out: Path,
    horizon_ticks: int,
    tick_s: float,
) -> Path:
    rows = _load_rows(ledger_in)
    by_tick: dict[int, list[LedgerRow]] = {}
    for r in rows:
        by_tick.setdefault(r.tick, []).append(r)
    ticks = sorted(by_tick)
    last_time = rows[-1].sim_time_s if rows else 0.0

    enriched: list[LedgerRow] = []
    for r in rows:
        target = r.tick + horizon_ticks
        actual = _thi_at(r)
        emergency = False
        for t in ticks:
            if r.tick < t <= target:
                for fr in by_tick[t]:
                    if any(fr.emergency_cooling_active):
                        emergency = True
            if t >= target:
                actual = _thi_at(by_tick[t][0])
                break
        else:
            actual = _thi_at(rows[-1])

        predicted = _predicted(r)
        error = tuple(a - p for a, p in zip(actual, predicted, strict=True))
        job_end = r.sim_time_s + r.job_features.duration_s
        feas = [c for c in r.candidates if c.feasible and c.thi_after_pred is not None]
        regret = 0.0
        if feas:
            best = max(feas, key=lambda c: float(c.thi_after_pred or 0.0))
            chosen = next((c for c in feas if c.zone_id == r.chosen_zone), None)
            if chosen is not None:
                regret = float(best.thi_after_pred or 0.0) - float(chosen.thi_after_pred or 0.0)

        outcome = LedgerOutcome(
            horizon_ticks=horizon_ticks,
            thi_actual_h=actual,
            thi_predicted_h=predicted,
            prediction_error=error,
            emergency_triggered_within_h=emergency,
            regret_vs_best_counterfactual=regret,
            job_completed=job_end <= last_time,
            job_completion_s=job_end if job_end <= last_time else None,
        )
        payload = r.to_jsonable()
        payload["outcome"] = {
            "horizon_ticks": outcome.horizon_ticks,
            "thi_actual_h": list(outcome.thi_actual_h),
            "thi_predicted_h": list(outcome.thi_predicted_h),
            "prediction_error": list(outcome.prediction_error),
            "emergency_triggered_within_h": outcome.emergency_triggered_within_h,
            "regret_vs_best_counterfactual": outcome.regret_vs_best_counterfactual,
            "job_completed": outcome.job_completed,
            "job_completion_s": outcome.job_completion_s,
        }
        enriched.append(LedgerRow.from_jsonable(payload))

    ledger_out.parent.mkdir(parents=True, exist_ok=True)
    with ledger_out.open("w", encoding="utf-8") as fh:
        for row in enriched:
            fh.write(json.dumps(row.to_jsonable()) + "\n")
    return ledger_out
