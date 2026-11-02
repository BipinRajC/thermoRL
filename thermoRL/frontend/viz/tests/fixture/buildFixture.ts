import { createHash } from "node:crypto";
import {
  SCHEMA,
  TICK_COLUMNS,
  type Catalog,
  type FileEntry,
  type FrozenOutcome,
  type IndexFile,
  type MetricsRow,
  type PolicyId,
  type RunMeta,
} from "../../src/schema/replay";

export interface FixtureOptions {
  nTicks?: number;
  rows?: number;
  cols?: number;
  nRacks?: number;
  seeds?: number[];
  decisionsPerTick?: (k: number) => number;
  corrupt?: { file: string };
}

export const EXP = "EFIX";
export const FIXTURE_POLICIES: PolicyId[] = ["packing", "power_balance", "thermal_predictive"];
export const POLICY_OFFSET_C: Partial<Record<PolicyId, number>> = {
  thermal_predictive: 0,
  power_balance: 0.2,
  packing: 0.4,
};
export const EMPTY_RACK = 65535;
export const RECORD_BYTES = 15;
export const ROWS_PER_DECISION = 6;

const NODES_PER_RACK = 18;
const COMPLETE_AFTER_S = 300;
const enc = new TextEncoder();
const sha256 = (b: Uint8Array | string) => createHash("sha256").update(b).digest("hex");
const avg = (a: number[]) => a.reduce((sum, x) => sum + x, 0) / a.length;
const round6 = (x: number) => Math.round(x * 1e6) / 1e6;

export const fixtureTc = (policy: PolicyId, k: number, r: number) =>
  40 + 0.01 * k + 0.1 * r + (POLICY_OFFSET_C[policy] ?? 0);
export const fixtureKw = (k: number, r: number) => 14 + ((r * 5 + k) % 30);
export const fixtureFree = (k: number, r: number) => (r * 3 + k) % 19;

const defaultDecisionsPerTick = (k: number) =>
  k >= 358 && k <= 360 ? 40 : k % 10 === 3 ? 1 : 0;

interface Decision {
  t: number;
  rule: "single" | "span";
  nodes: number;
  racks: number[];
  scores: number[];
  maxScore: number;
  nTies: number;
  isBest: boolean;
}

const rampScores = (nRacks: number, best: number) =>
  Array.from({ length: nRacks }, (_, r) => round6(1 - 0.001 * ((r - best + nRacks) % nRacks)));

function buildDecisions(nTicks: number, nRacks: number, perTick: (k: number) => number): Decision[] {
  const raw: { t: number; rule: "single" | "span"; nodes: number; racks: number[]; scores?: number[] }[] = [];
  let n = 0;
  for (let k = 0; k < nTicks; k++) {
    const count = perTick(k);
    for (let i = 0; i < count; i++) {
      const rack = (n * 3 + 1) % nRacks;
      raw.push({ t: 10 * k + 1 + Math.floor((i * 10) / count), rule: "single", nodes: 1 + (n % 4), racks: [rack] });
      n++;
    }
  }
  raw.push({ t: 25, rule: "span", nodes: 24, racks: [2, 3] });
  const tied = Array.from({ length: nRacks }, (_, r) => round6(0.5 - 0.01 * r));
  for (const r of [4, 5, 6]) tied[r] = 0.9;
  raw.push({ t: 85, rule: "single", nodes: 1, racks: [7], scores: tied });
  raw.sort((a, b) => a.t - b.t);
  return raw.map((d) => {
    const scores = d.scores ?? rampScores(nRacks, d.racks[0]);
    const maxScore = Math.max(...scores);
    return {
      t: d.t,
      rule: d.rule,
      nodes: d.nodes,
      racks: d.racks,
      scores,
      maxScore,
      nTies: scores.filter((s) => s === maxScore).length,
      isBest: scores[d.racks[0]] === maxScore,
    };
  });
}

function buildEvents(decisions: Decision[], horizonS: number) {
  const ev: { kind: 0 | 1; t: number; job: number; di: number; racks: number[] }[] = [];
  decisions.forEach((d, i) => {
    ev.push({ kind: 0, t: d.t, job: i, di: i, racks: d.racks });
    if (d.t + COMPLETE_AFTER_S <= horizonS) ev.push({ kind: 1, t: d.t + COMPLETE_AFTER_S, job: i, di: -1, racks: d.racks });
  });
  ev.sort((a, b) => a.t - b.t || b.kind - a.kind || a.di - b.di || a.job - b.job);
  const out = { kind: [] as number[], raps_t_s: [] as number[], job_id: [] as number[], decision_index: [] as number[], rack_offsets: [0], racks: [] as number[] };
  for (const e of ev) {
    out.kind.push(e.kind);
    out.raps_t_s.push(e.t);
    out.job_id.push(e.job);
    out.decision_index.push(e.di);
    out.racks.push(...[...new Set(e.racks)].sort((a, b) => a - b));
    out.rack_offsets.push(out.racks.length);
  }
  return out;
}

function buildCandidates(decisions: Decision[], policy: PolicyId, nTicks: number, nRacks: number) {
  const buf = new ArrayBuffer(decisions.length * ROWS_PER_DECISION * RECORD_BYTES);
  const dv = new DataView(buf);
  decisions.forEach((d, i) => {
    const k = Math.min(nTicks - 1, Math.max(0, Math.floor(d.t / 10) - 1));
    const order = Array.from(d.scores.keys()).sort((a, b) => d.scores[b] - d.scores[a] || a - b);
    const rows = order.slice(0, 5);
    while (rows.length < 5) rows.push(-1);
    rows.push(rows.includes(d.racks[0]) ? -1 : d.racks[0]);
    rows.forEach((r, j) => {
      const off = (i * ROWS_PER_DECISION + j) * RECORD_BYTES;
      const empty = r < 0 || r >= nRacks;
      dv.setUint16(off, empty ? EMPTY_RACK : r, true);
      dv.setFloat32(off + 2, empty ? NaN : d.scores[r], true);
      dv.setFloat32(off + 6, empty ? NaN : round6(fixtureTc(policy, k, r)), true);
      dv.setFloat32(off + 10, empty ? NaN : fixtureKw(k, r), true);
      dv.setUint8(off + 14, empty ? 0 : fixtureFree(k, r));
    });
  });
  return new Uint8Array(buf);
}

const f32 = (a: Float32Array) => new Uint8Array(a.buffer, a.byteOffset, a.byteLength);
const json = (v: unknown) => enc.encode(JSON.stringify(v));

export async function buildFixture(opts: FixtureOptions = {}): Promise<Map<string, Uint8Array>> {
  const nTicks = opts.nTicks ?? 400;
  const rows = opts.rows ?? 3;
  const cols = opts.cols ?? 4;
  const nRacks = opts.nRacks ?? 11;
  const seeds = opts.seeds ?? [1, 2];
  const perTick = opts.decisionsPerTick ?? defaultDecisionsPerTick;
  if (nRacks < 8) throw new Error(`buildFixture: nRacks must be >= 8 (got ${nRacks})`);
  if (nTicks < 360) throw new Error(`buildFixture: nTicks must be >= 360 so an evaluation window exists (got ${nTicks})`);
  const files = new Map<string, Uint8Array>();

  const decisions = buildDecisions(nTicks, nRacks, perTick);
  const eventsCols = buildEvents(decisions, nTicks * 10);
  const decisionsCols = {
    decision_index: decisions.map((_, i) => i),
    raps_t_s: decisions.map((d) => d.t),
    job_id: decisions.map((_, i) => i),
    nodes_required: decisions.map((d) => d.nodes),
    rule: decisions.map((d) => d.rule),
    job_kw: decisions.map((d) => d.nodes * 0.5),
    t_obs_s: decisions.map((d) => Math.max(10, Math.floor(d.t / 10) * 10)),
    chosen_offsets: decisions.reduce((o, d) => (o.push(o[o.length - 1] + d.racks.length), o), [0]),
    chosen_racks: decisions.flatMap((d) => d.racks),
    n_ties_at_logged_best: decisions.map((d) => d.nTies),
    chosen_is_logged_best: decisions.map((d) => d.isBest),
  };
  const eventsBytes = json(eventsCols);
  const decisionsBytes = json(decisionsCols);

  const rackKw = new Float32Array(nTicks * nRacks);
  const rackFree = new Uint8Array(nTicks * nRacks);
  const itKw: number[] = [];
  for (let k = 0; k < nTicks; k++) {
    let sum = 0;
    for (let r = 0; r < nRacks; r++) {
      rackKw[k * nRacks + r] = fixtureKw(k, r);
      rackFree[k * nRacks + r] = fixtureFree(k, r);
      sum += rackKw[k * nRacks + r];
    }
    itKw.push(sum);
  }

  const metricsRows: MetricsRow[] = [];
  const runsBySeed = new Map<number, Partial<Record<PolicyId, string>>>();

  for (const seed of seeds) {
    const runs: Partial<Record<PolicyId, string>> = {};
    for (const policy of FIXTURE_POLICIES) {
      const dir = `runs/${policy}_seed${seed}`;
      runs[policy] = `${dir}/run.json`;

      const rackTc = new Float32Array(nTicks * nRacks);
      const tick = new Float64Array(nTicks * TICK_COLUMNS.length);
      const maxes: number[] = [];
      for (let k = 0; k < nTicks; k++) {
        for (let r = 0; r < nRacks; r++) rackTc[k * nRacks + r] = fixtureTc(policy, k, r);
        const maxC = fixtureTc(policy, k, nRacks - 1);
        maxes.push(maxC);
        tick.set(
          [10 * (k + 1), itKw[k], 1 + (k % 5), k % 3, maxC, fixtureTc(policy, k, 0), nRacks - 1, 0.3 * nRacks],
          k * TICK_COLUMNS.length,
        );
      }
      const evalMaxes = maxes.filter((_, k) => 10 * (k + 1) > 3600 && 10 * (k + 1) <= 21600);
            const row: MetricsRow = {
        name: `${policy}_seed${seed}`,
        policy,
        seed,
        maxrack_mean_c: avg(evalMaxes),
        raw_max_c: Math.max(...maxes),
        it_kw_mean: avg(itKw),
        jobs_started: decisions.length,
      };
      metricsRows.push(row);

      const candBytes = buildCandidates(decisions, policy, nTicks, nRacks);
      const entry = (path: string, dtype: FileEntry["dtype"], bytes: Uint8Array, extra: Partial<FileEntry> = {}): FileEntry => {
        files.set(`${EXP}/${dir}/${path}`, bytes);
        return { path, dtype, ...extra, bytes: bytes.byteLength, sha256: sha256(bytes) };
      };
      const run: RunMeta = {
        schema: SCHEMA,
        run_id: `${EXP}:${policy}_seed${seed}`,
        experiment_id: EXP,
        policy,
        seed,
        launch_sha: sha256(`launch:${policy}:${seed}`).slice(0, 40),
        selected_attempt: 1,
        c_prime_status: policy === "thermal_predictive" && seed === 1 ? "verified_E12" : "inherited_not_remeasured",
        n_ticks: nTicks,
        n_racks: nRacks,
        n_decisions: decisions.length,
        n_events: eventsCols.kind.length,
        source: {
          manifest_sha256: sha256(`manifest:${policy}:${seed}`),
          decisions_sha256: sha256(`decisions:${policy}:${seed}`),
          intervals_sha256: sha256(`intervals:${policy}:${seed}`),
          job_events_sha256: sha256(`job_events:${policy}:${seed}`),
        },
        metrics: row,
        files: {
          rack_tc: entry("rack_tc.f32", "float32", f32(rackTc), { shape: [nTicks, nRacks] }),
          rack_kw: entry("rack_kw.f32", "float32", f32(rackKw), { shape: [nTicks, nRacks] }),
          rack_free: entry("rack_free.u8", "uint8", rackFree, { shape: [nTicks, nRacks] }),
          tick: entry("tick.f64", "float64", new Uint8Array(tick.buffer), {
            shape: [nTicks, TICK_COLUMNS.length],
            columns: [...TICK_COLUMNS],
          }),
          events: entry("events.json", "json", eventsBytes),
          decisions: entry("decisions.json", "json", decisionsBytes),
          candidates: entry("candidates.bin", "record", candBytes, {
            record_bytes: RECORD_BYTES,
            rows_per_decision: ROWS_PER_DECISION,
            fields: [
              ["rack", "uint16"],
              ["score", "float32"],
              ["t_c", "float32"],
              ["committed_kw", "float32"],
              ["free", "uint8"],
            ],
            empty_rack: EMPTY_RACK,
          }),
        },
      };
      files.set(`${EXP}/${dir}/run.json`, json(run));
    }
    runsBySeed.set(seed, runs);
  }

  const hex = (n: number) => n.toString(16).padStart(2, "0");
  const lut = Array.from({ length: 256 }, (_, i) => `#${hex(i)}${hex(Math.floor(i / 2))}${hex(255 - i)}`);

  const catalog: Catalog = {
    schema: SCHEMA,
    experiment: {
      id: EXP,
      short: EXP,
      workload_label: "Fixture",
      workload_note: "Generated test fixture; deterministic values",
      system_label: "Fixture cooling model (modelled)",
      scenario: "nominal",
      fmu_sha256: sha256("fixture-fmu"),
    },
    grid: {
      rows,
      cols,
      n_racks: nRacks,
      nodes_per_rack: NODES_PER_RACK,
      mapping: `row = r // ${cols}, col = r % ${cols}, origin lower-left`,
      schematic_not_floor_plan: true,
    },
    time: {
      tick_s: 10,
      n_ticks: nTicks,
      first_t_s: 10,
      last_t_s: 10 * nTicks,
      eval_start_exclusive_s: 3600,
      eval_end_inclusive_s: 21600,
      pulse_window_s: 30,
    },
    rack_kw_range: {
      idle_kw: 13.822619047619046,
      peak_kw: 49.32325680272109,
      basis: "RAPS loss-inclusive rack power, from run manifests",
    },
    colormap: { name: "fixture", lut },
    seeds: seeds.map((seed) => ({
      seed,
      note: `seed ${seed} of ${seeds.length}`,
      colour_scale_c:
        seed === 1
          ? { min: 40, max: round6(fixtureTc("thermal_predictive", 5, nRacks - 3) + 0.05), scope: "all five policies of this seed" }
          : { min: 39.5, max: 42.5, scope: "all five policies of this seed" },
      runs: runsBySeed.get(seed)!,
    })),
    default_seed: seeds[0],
    comparisons: [
      { id: "pb_vs_tp", left: "power_balance", right: "thermal_predictive", default: true },
      { id: "packing_vs_tp", left: "packing", right: "thermal_predictive" },
    ],
    strings: {
      interval_semantics: "fixture interval semantics text",
      s2: "fixture s2 text",
      precision_note: "fixture precision note text",
      pulse_rule: "fixture pulse rule text",
    },
    unavailable_fields: ["fixture_unavailable_field"],
    provenance: {
      export_source_sha: sha256("fixture-source").slice(0, 40),
      exporter: "tests/fixture/buildFixture.ts",
      generated_utc: "2026-01-01T00:00:00Z",
      raw_inventory: "none",
    },
  };

  const meanOf = (policy: PolicyId, seed: number) =>
    metricsRows.find((m) => m.policy === policy && m.seed === seed)!.maxrack_mean_c;
  const perSeed: FrozenOutcome["decision"]["per_seed"] = {};
  for (const seed of seeds) {
    perSeed[String(seed)] = {
      packing_minus_thermal_c: meanOf("packing", seed) - meanOf("thermal_predictive", seed),
      power_minus_thermal_c: meanOf("power_balance", seed) - meanOf("thermal_predictive", seed),
    };
  }
  const decisionRule = "fixture decision rule text";
  const frozen: FrozenOutcome = {
    schema: SCHEMA,
    experiment_id: EXP,
    headline: "fixture headline text",
    rule: "fixture rule text",
    decision: { decision: "fixture decision text", per_seed: perSeed, rule: decisionRule, value_beyond_power: false },
    decision_sha256: sha256("fixture-decision"),
    metrics_sha256: sha256("fixture-metrics"),
    metrics: metricsRows,
    experiment_statement: "fixture experiment statement text",
    reproducibility_scope: "fixture reproducibility scope text",
  };
  const index: IndexFile = {
    schema: SCHEMA,
    experiments: [{ id: EXP, short: EXP, label: "EFIX — Fixture workload", catalog: `${EXP}/catalog.json`, default: true }],
  };

  files.set("index.json", json(index));
  files.set(`${EXP}/catalog.json`, json(catalog));
  files.set(`${EXP}/frozen_outcome.json`, json(frozen));

  if (opts.corrupt) {
    const bytes = files.get(opts.corrupt.file);
    if (!bytes) throw new Error(`corrupt: no such fixture file ${opts.corrupt.file}`);
    if (opts.corrupt.file.endsWith(".json")) {
      const grown = new Uint8Array(bytes.byteLength + 1);
      grown.set(bytes);
      grown[bytes.byteLength] = 0x20;
      files.set(opts.corrupt.file, grown);
    } else {
      const flipped = bytes.slice();
      flipped[flipped.byteLength - 1] ^= 0x01;
      files.set(opts.corrupt.file, flipped);
    }
  }
  return files;
}
