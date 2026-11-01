import { TICK_COLUMNS, type TickColumn } from "../schema/replay";
import type { LoadedRun } from "./loader";

const ROWS_PER_DECISION = 6;
const RECORD_BYTES = 15;
const EMPTY_RACK = 65535;
const TICK_STRIDE = TICK_COLUMNS.length;

export const rackTc = (run: LoadedRun, k: number, r: number): number => run.tc[k * run.meta.n_racks + r];
export const rackKw = (run: LoadedRun, k: number, r: number): number => run.kw[k * run.meta.n_racks + r];
export const rackFree = (run: LoadedRun, k: number, r: number): number => run.free[k * run.meta.n_racks + r];

export const tickValue = (run: LoadedRun, k: number, col: TickColumn): number =>
  run.tick[k * TICK_STRIDE + TICK_COLUMNS.indexOf(col)];

function firstAbove(values: Int32Array, lo: number): number {
  let a = 0;
  let b = values.length;
  while (a < b) {
    const m = (a + b) >>> 1;
    if (values[m] > lo) b = m;
    else a = m + 1;
  }
  return a;
}

export function startRacksIn(run: LoadedRun, lo: number, hi: number): Set<number> {
  const { kind, raps_t_s, rack_offsets, racks } = run.events;
  const out = new Set<number>();
  for (let i = firstAbove(raps_t_s, lo); i < raps_t_s.length && raps_t_s[i] <= hi; i++) {
    if (kind[i] !== 0) continue;
    for (let j = rack_offsets[i]; j < rack_offsets[i + 1]; j++) out.add(racks[j]);
  }
  return out;
}

export function decisionsIn(run: LoadedRun, lo: number, hi: number): number[] {
  const t = run.decisions.raps_t_s;
  const out: number[] = [];
  for (let i = firstAbove(t, lo); i < t.length && t[i] <= hi; i++) out.push(i);
  return out;
}

export interface DecisionView {
  index: number;
  rapsTs: number;
  jobId: number;
  nodes: number;
  rule: "single" | "span";
  jobKw: number;
  tObs: number;
  chosen: number[];
  nTies: number;
  chosenIsBest: boolean;
}

export function decisionAt(run: LoadedRun, i: number): DecisionView {
  const d = run.decisions;
  return {
    index: i,
    rapsTs: d.raps_t_s[i],
    jobId: d.job_id[i],
    nodes: d.nodes_required[i],
    rule: d.rule[i] as "single" | "span",
    jobKw: d.job_kw[i],
    tObs: d.t_obs_s[i],
    chosen: Array.from(d.chosen_racks.subarray(d.chosen_offsets[i], d.chosen_offsets[i + 1])),
    nTies: d.n_ties_at_logged_best[i],
    chosenIsBest: d.chosen_is_logged_best[i] === 1,
  };
}

export interface CandidateRow {
  rack: number;
  score: number;
  tc: number;
  committedKw: number;
  free: number;
  chosen: boolean;
}

export function candidatesFor(run: LoadedRun, i: number): CandidateRow[] {
  const chosen = new Set(decisionAt(run, i).chosen);
  const dv = run.candidates;
  const rows: CandidateRow[] = [];
  for (let j = 0; j < ROWS_PER_DECISION; j++) {
    const off = (i * ROWS_PER_DECISION + j) * RECORD_BYTES;
    const rack = dv.getUint16(off, true);
    if (rack === EMPTY_RACK) continue;
    rows.push({
      rack,
      score: dv.getFloat32(off + 2, true),
      tc: dv.getFloat32(off + 6, true),
      committedKw: dv.getFloat32(off + 10, true),
      free: dv.getUint8(off + 14),
      chosen: chosen.has(rack),
    });
  }
  return rows;
}
