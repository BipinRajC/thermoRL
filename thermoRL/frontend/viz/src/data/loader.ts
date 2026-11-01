import { SCHEMA, type Catalog, type FileEntry, type FrozenOutcome, type IndexEntry, type IndexFile, type RunMeta } from "../schema/replay";
import { sha256Hex } from "./hash";

export type ReplayErrorKind = "missing" | "schema" | "size" | "hash" | "shape" | "mismatch" | "network";

export class ReplayError extends Error {
  constructor(
    public kind: ReplayErrorKind,
    message: string,
    public file?: string,
  ) {
    super(message);
    this.name = "ReplayError";
  }
}

export type Fetcher = (url: string, init?: { signal?: AbortSignal }) => Promise<Response>;

export interface EventsColumns {
  kind: Int32Array;
  raps_t_s: Int32Array;
  job_id: Int32Array;
  decision_index: Int32Array;
  rack_offsets: Int32Array;
  racks: Int32Array;
}

export interface DecisionColumns {
  decision_index: Int32Array;
  raps_t_s: Int32Array;
  job_id: Int32Array;
  nodes_required: Int32Array;
  rule: string[];
  job_kw: Float64Array;
  t_obs_s: Float64Array;
  chosen_offsets: Int32Array;
  chosen_racks: Int32Array;
  n_ties_at_logged_best: Int32Array;
  chosen_is_logged_best: Uint8Array;
}

export interface LoadedRun {
  meta: RunMeta;
  tc: Float32Array;
  kw: Float32Array;
  free: Uint8Array;
  tick: Float64Array;
  events: EventsColumns;
  decisions: DecisionColumns;
  candidates: DataView;
}

const ELEMENT_BYTES: Record<string, number> = { float32: 4, float64: 8, uint8: 1 };
const TICK_STRIDE = 8;

const abortError = () => new DOMException("The operation was aborted.", "AbortError");
const isAbort = (e: unknown) => e instanceof DOMException && e.name === "AbortError";
const join = (...parts: string[]) => parts.map((p, i) => (i === 0 ? p.replace(/\/+$/, "") : p.replace(/^\/+|\/+$/g, ""))).filter((p) => p !== "").join("/");
const dirOf = (path: string) => path.slice(0, Math.max(0, path.lastIndexOf("/")));

const defaultFetcher: Fetcher = (url, init) => fetch(url, init);

async function fetchBytes(base: string, path: string, f: Fetcher, signal?: AbortSignal): Promise<ArrayBuffer> {
  if (signal?.aborted) throw abortError();
  let res: Response;
  try {
    res = await f(join(base, path), { signal });
  } catch (e) {
    if (isAbort(e) || signal?.aborted) throw abortError();
    throw new ReplayError("network", `Could not fetch ${path}`, path);
  }
  if (res.status === 404) throw new ReplayError("missing", `Missing file ${path}`, path);
  if (!res.ok) throw new ReplayError("network", `Fetching ${path} failed with HTTP ${res.status}`, path);
  try {
    return await res.arrayBuffer();
  } catch (e) {
    if (isAbort(e) || signal?.aborted) throw abortError();
    throw new ReplayError("network", `Could not read ${path}`, path);
  }
}

const parseJson = <T>(buf: ArrayBuffer, path: string): T => {
  try {
    return JSON.parse(new TextDecoder().decode(buf)) as T;
  } catch {
    throw new ReplayError("schema", `${path} is not valid JSON`, path);
  }
};

async function fetchJson<T extends { schema: string }>(base: string, path: string, f: Fetcher, signal?: AbortSignal): Promise<T> {
  const json = parseJson<T>(await fetchBytes(base, path, f, signal), path);
  if (json?.schema !== SCHEMA) throw new ReplayError("schema", `${path} does not declare schema ${SCHEMA}`, path);
  return json;
}

export const loadIndex = (base: string, f: Fetcher = defaultFetcher): Promise<IndexFile> =>
  fetchJson<IndexFile>(base, "index.json", f);

export async function loadExperiment(
  base: string,
  entry: IndexEntry,
  f: Fetcher = defaultFetcher,
): Promise<{ catalog: Catalog; outcome: FrozenOutcome }> {
  const dir = dirOf(entry.catalog);
  const [catalog, outcome] = await Promise.all([
    fetchJson<Catalog>(base, entry.catalog, f),
    fetchJson<FrozenOutcome>(base, join(dir, "frozen_outcome.json"), f),
  ]);
  return { catalog, outcome };
}

function verifyShape(entry: FileEntry, path: string) {
  if (!entry.shape) return;
  const size = ELEMENT_BYTES[entry.dtype];
  const count = entry.shape.reduce((a, b) => a * b, 1);
  if (!size || count * size !== entry.bytes) {
    throw new ReplayError("shape", `${path}: shape [${entry.shape.join(", ")}] does not match ${entry.bytes} bytes`, path);
  }
}

export async function loadRun(
  base: string,
  expDir: string,
  runJsonPath: string,
  f: Fetcher = defaultFetcher,
  signal?: AbortSignal,
  onProgress?: (file: string, done: number, total: number) => void,
): Promise<LoadedRun> {
  const runPath = join(expDir, runJsonPath);
  const runDir = dirOf(runPath);
  const meta = await fetchJson<RunMeta>(base, runPath, f, signal);
  const entries = Object.values(meta.files);
  const total = entries.length + 1;
  let done = 1;
  onProgress?.(runPath, done, total);

  const read = async (entry: FileEntry): Promise<ArrayBuffer> => {
    const path = join(runDir, entry.path);
    const buf = await fetchBytes(base, path, f, signal);
    if (buf.byteLength !== entry.bytes) {
      throw new ReplayError("size", `${path}: expected ${entry.bytes} bytes, got ${buf.byteLength}`, path);
    }
    if ((await sha256Hex(buf)) !== entry.sha256) throw new ReplayError("hash", `${path}: sha256 mismatch`, path);
    verifyShape(entry, path);
    onProgress?.(path, ++done, total);
    return buf;
  };

  const fl = meta.files;
  const [tc, kw, free, tick, events, decisions, candidates] = await Promise.all([
    read(fl.rack_tc),
    read(fl.rack_kw),
    read(fl.rack_free),
    read(fl.tick),
    read(fl.events),
    read(fl.decisions),
    read(fl.candidates),
  ]);
  if (signal?.aborted) throw abortError();

  const ev = parseJson<Record<keyof EventsColumns, number[]>>(events, join(runDir, fl.events.path));
  const dc = parseJson<Record<string, any[]>>(decisions, join(runDir, fl.decisions.path));
  const i32 = (a: number[]) => Int32Array.from(a);
  return {
    meta,
    tc: new Float32Array(tc),
    kw: new Float32Array(kw),
    free: new Uint8Array(free),
    tick: new Float64Array(tick),
    events: {
      kind: i32(ev.kind),
      raps_t_s: i32(ev.raps_t_s),
      job_id: i32(ev.job_id),
      decision_index: i32(ev.decision_index),
      rack_offsets: i32(ev.rack_offsets),
      racks: i32(ev.racks),
    },
    decisions: {
      decision_index: i32(dc.decision_index),
      raps_t_s: i32(dc.raps_t_s),
      job_id: i32(dc.job_id),
      nodes_required: i32(dc.nodes_required),
      rule: dc.rule as string[],
      job_kw: Float64Array.from(dc.job_kw),
      t_obs_s: Float64Array.from(dc.t_obs_s),
      chosen_offsets: i32(dc.chosen_offsets),
      chosen_racks: i32(dc.chosen_racks),
      n_ties_at_logged_best: i32(dc.n_ties_at_logged_best),
      chosen_is_logged_best: Uint8Array.from(dc.chosen_is_logged_best as boolean[], (b) => (b ? 1 : 0)),
    },
    candidates: new DataView(candidates),
  };
}

export function assertComparable(a: LoadedRun, b: LoadedRun): void {
  if (a.meta.n_ticks !== b.meta.n_ticks) {
    throw new ReplayError("mismatch", `Runs differ in tick count (${a.meta.n_ticks} vs ${b.meta.n_ticks})`);
  }
  if (a.meta.n_racks !== b.meta.n_racks) {
    throw new ReplayError("mismatch", `Runs differ in rack count (${a.meta.n_racks} vs ${b.meta.n_racks})`);
  }
  if (a.tick.length !== b.tick.length) throw new ReplayError("mismatch", "Runs differ in tick table length");
  for (let k = 0; k < a.tick.length; k += TICK_STRIDE) {
    if (a.tick[k] !== b.tick[k]) {
      throw new ReplayError("mismatch", `Runs differ in time at tick ${k / TICK_STRIDE}`);
    }
  }
}
