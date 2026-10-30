"""Ledger-only metrics. No simulation imports or reconstruction of thermal state.

Rows labelled t_s contain RAPS inputs at t_s-Delta (kw/free/n_running/
n_queued/it_kw_total) and FMU endpoint outputs at t_s (t_c/pump_kw).
Thermal windows are strict: eval_start_s < t_s <= horizon. Energy covers the
whole episode: IT is the exact held-input sum kw*Delta; pump is a right-endpoint
rectangle. Neither includes warm-up. Waits use continuous offered submit times;
unstarted jobs are censored, not assigned a zero wait. Latency is measurement
ledger only; canonical null is never interpreted as zero.
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from thermorl2.core.placement import place
from thermorl2.core.scorers import RackContext

PROJECT = Path(__file__).resolve().parents[2]


@dataclass
class Run:
    name: str
    intervals: pd.DataFrame
    decisions: list
    manifest: dict
    path: Path | None = None
    workload: pd.DataFrame | None = None
    timings: list | None = None
    job_events: list = field(default_factory=list)


def _jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def load_run(run_dir) -> Run:
    path = Path(run_dir)
    manifest = json.loads((path/'manifest.json').read_text())
    workload_path = Path(manifest['workload_path'])
    if not workload_path.is_absolute():
        workload_path = PROJECT / workload_path
    timing = path/'provenance/decision_latency.jsonl'
    events = path/'provenance/job_events.jsonl'
    return Run(path.name, pd.read_parquet(path/'intervals.parquet'),
               _jsonl(path/'decisions.jsonl'), manifest, path,
               pd.read_parquet(workload_path), _jsonl(timing) if timing.exists() else None,
               _jsonl(events) if events.exists() else [])


def _tail(run, start):
    horizon = float(run.manifest['config']['horizon_h'])*3600
    tail = run.intervals[(run.intervals.t_s > start) & (run.intervals.t_s <= horizon)]
    if tail.empty:
        raise ValueError('empty evaluation window')
    return tail


def run_metrics(run, eval_start_s, t_hot_c, t_max_c=45.0) -> dict:
    frame, m = run.intervals, run.manifest
    tail = _tail(run, eval_start_s)
    groups = tail.groupby('t_s', sort=True)
    maxima, minima = groups.t_c.max(), groups.t_c.min()
    n_racks = int(m['n_racks'])
    hottest = int(np.ceil(0.1*n_racks))
    temp = tail.pivot(index='t_s', columns='rack', values='t_c').sort_index(axis=1)
    power = tail.pivot(index='t_s', columns='rack', values='kw').sort_index(axis=1)
    idle = np.asarray(m['t_idle_c'])[tail.rack.to_numpy(dtype=int)]
    thi = 1 - (tail.t_c.to_numpy()-idle)/(t_max_c-idle)
    delta = m['power_tick_s']
    waits = None
    censored = None
    if run.workload is not None:
        submits = run.workload.set_index('id').submit_time
        waits = np.asarray([r['t_s']-float(submits.loc[r['job_id']]) for r in run.decisions])
        assert (waits >= 0).all()
        censored = len(run.workload) - len(run.decisions)
    latency = None
    if run.timings is not None:
        assert len(run.timings) == len(run.decisions)
        for i,(row,timing) in enumerate(zip(run.decisions,run.timings)):
            assert (i,row['job_id'],row['t_s']) == (timing['decision_index'],timing['job_id'],timing['t_s'])
            assert type(timing['latency_ns']) is int and timing['latency_ns'] >= 0
        latency = np.asarray([t['latency_ns']/1000 for t in run.timings])
    def mean(values):
        return float(np.mean(values)) if values is not None and len(values) else None
    def p95(values):
        return float(np.percentile(values,95)) if values is not None and len(values) else None
    return dict(
        maxrack_mean_c=float(maxima.mean()), maxrack_p99_c=float(np.percentile(maxima,99)),
        spread_mean_c=float((maxima-minima).mean()), mean_rack_c=float(tail.t_c.mean()),
        raw_max_c=float(frame.t_c.max()),
        hot_rack_seconds=int((tail.t_c > t_hot_c).sum())*delta,
        thi_t_below_0p1_frac=float(np.mean(thi < 0.1)),
        pump_energy_kwh=float(frame.pump_kw.sum()*delta/3600),
        it_energy_kwh=float(frame.kw.sum()*delta/3600),
        jobs_started=len(run.decisions), jobs_censored=censored,
        wait_mean_s=mean(waits), wait_p95_s=p95(waits),
        decision_latency_mean_us=mean(latency), decision_latency_p95_us=p95(latency),
        rack_t_std_mean_c=float(np.std(temp.to_numpy(),axis=1,ddof=0).mean()),
        top_decile_mean_c=float(np.sort(temp.to_numpy(),axis=1)[:,-hottest:].mean()),
        rack_kw_std_mean=float(np.std(power.to_numpy(),axis=1,ddof=0).mean()),
        realised_node_utilisation_mean=float((1-groups.free.sum()/m['total_nodes']).mean()),
        coolant_over_70_samples=int((frame.t_c > 70).sum()),
        coolant_over_70_racks=sorted(map(int,frame.loc[frame.t_c > 70,'rack'].unique())),
        **{key:m[key] for key in ('raps_s','fmu_s','total_s')})


def invariants(runs) -> dict:
    if not runs:
        raise ValueError('at least one run required')
    reference = runs[0].intervals.groupby('t_s').it_kw_total.first()
    starts = lambda run: {r['job_id']:r['t_s'] for r in run.decisions}
    same_grid, maximum, steps = True, 0.0, True
    for run in runs:
        series = run.intervals.groupby('t_s').it_kw_total.first()
        if not reference.index.equals(series.index):
            same_grid = False
        else:
            maximum = max(maximum,float(np.max(np.abs(reference.to_numpy()-series.to_numpy()))))
        m = run.manifest
        horizon = float(m['config']['horizon_h'])*3600
        expected = np.arange(m['power_tick_s'],horizon+1,m['power_tick_s'])
        steps &= (m['fmu_steps'] == horizon/m['power_tick_s'] and
                  m['backend_elapsed_s'] == horizon and
                  np.array_equal(series.index.to_numpy(),expected) and
                  (run.intervals.groupby('t_s').size() == m['n_racks']).all())
    return dict(it_kw_identical=bool(same_grid and maximum <= 1e-6),
                start_times_identical=all(starts(run)==starts(runs[0]) for run in runs),
                max_abs_it_kw_diff=maximum if same_grid else None, fmu_steps_ok=bool(steps))


def _rescore(row, scorer):
    free = np.asarray(row['free'],dtype=int)
    # Unique artificial node ids preserve rack counts and place's distinctness
    # contract. Node identities do not enter rack scoring or first-rack choice.
    edges = np.concatenate(([0],np.cumsum(free)))
    nodes = [list(range(int(edges[i]),int(edges[i+1]))) for i in range(len(free))]
    ctx = RackContext(free,np.asarray(row['committed_kw']),np.asarray(row['t_c']),
                      row['job_kw'],row['nodes_required'])
    return place(scorer.score(ctx),nodes,row['nodes_required']).racks[0]


def disagreement_rate(decisions, scorer_a, scorer_b) -> float | None:
    """Both scorers re-applied to each identical six-decimal logged context."""
    return float(np.mean([_rescore(row,scorer_a)!=_rescore(row,scorer_b) for row in decisions])) if decisions else None


def self_reproduction_rate(decisions, scorer) -> float | None:
    """Diagnostic only: rounded context vs live unrounded rack choice."""
    return float(np.mean([_rescore(row,scorer)==row['racks'][0] for row in decisions])) if decisions else None


def affected_metrics(run, racks, eval_start_s):
    tail = _tail(run,eval_start_s)
    return {'maxrack_mean_c':float(tail[tail.rack.isin(racks)].groupby('t_s').t_c.max().mean())}


def max_rack_attribution(run, eval_start_s):
    """Endpoint argmax (lower index for ties), resident jobs at driving RAPS t.

    Intervening placements during (t,t+Delta) do not drive this row. Job events
    at t are applied before residency is captured; completions precede starts.
    """
    tail = _tail(run,eval_start_s).sort_values(['t_s','rack'])
    maxima = tail.loc[tail.groupby('t_s').t_c.idxmax()]
    events = iter(sorted(run.job_events,key=lambda e:(e['t_s'],e['event']!='complete',e.get('decision_index',e['job_id']))))
    pending = next(events,None)
    resident = {}
    ticks = []
    for row in maxima.itertuples():
        driving_t = float(row.t_s-run.manifest['power_tick_s'])
        while pending is not None and pending['t_s'] <= driving_t:
            if pending['event'] == 'complete':
                resident.pop(pending['job_id'],None)
            else:
                resident[pending['job_id']] = {node//run.manifest['nodes_per_rack'] for node in pending['nodes']}
            pending = next(events,None)
        ticks.append(dict(t_s=float(row.t_s),raps_power_tick_s=driving_t,rack=int(row.rack),
                          t_c=float(row.t_c),kw=float(row.kw),
                          resident_job_ids=sorted(job for job,racks in resident.items() if row.rack in racks)))
    counts = pd.Series([r['rack'] for r in ticks]).value_counts().sort_index()
    return {'ticks':ticks,'rack_shares':{str(int(r)):float(n/len(ticks)) for r,n in counts.items()}}
