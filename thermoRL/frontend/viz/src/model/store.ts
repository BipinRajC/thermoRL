import {
  ReplayError,
  assertComparable,
  loadExperiment,
  loadIndex,
  loadRun,
  type Fetcher,
  type LoadedRun,
} from "../data/loader";
import type { Catalog, FrozenOutcome, IndexEntry, IndexFile } from "../schema/replay";
import type { Overlay } from "./colour";
import { tickToTs, tsToTick } from "./time";

export type Drawer = "outcome" | "why" | "about" | "rack" | null;

export interface AppState {
  experimentId: string;
  seed: number;
  comparisonId: string;
  tick: number;
  overlay: Overlay;
  pinnedRack: number | null;
  drawer: Drawer;
  whySide: "left" | "right";
}

export const DEFAULT_STATE: AppState = {
  experimentId: "",
  seed: 1,
  comparisonId: "",
  tick: 0,
  overlay: "tc",
  pinnedRack: null,
  drawer: null,
  whySide: "left",
};

export const DEFAULT_DATA_DIR = "replay";
const DEFAULT_N_TICKS = 2160;

export class Store {
  private state: AppState;
  private readonly subs = new Set<(s: AppState, prev: AppState) => void>();

  constructor(initial: Partial<AppState> = {}) {
    this.state = { ...DEFAULT_STATE, ...initial };
  }

  get(): AppState {
    return this.state;
  }

  set(p: Partial<AppState>): void {
    const prev = this.state;
    const changed = (Object.keys(p) as (keyof AppState)[]).some((k) => p[k] !== prev[k]);
    if (!changed) return;
    this.state = { ...prev, ...p };
    for (const fn of [...this.subs]) fn(this.state, prev);
  }

  subscribe(fn: (s: AppState, prev: AppState) => void): () => void {
    this.subs.add(fn);
    return () => {
      this.subs.delete(fn);
    };
  }
}

export interface ExperimentBundle {
  catalog: Catalog;
  outcome: FrozenOutcome;
}

export class RunCache {
  private readonly runs = new Map<string, LoadedRun>();
  private readonly indexes = new Map<string, Promise<IndexFile>>();
  private readonly experiments = new Map<string, Promise<ExperimentBundle>>();
  private readonly ready = new Map<string, ExperimentBundle>();

  constructor(readonly maxRuns = 6) {}

  get(id: string): LoadedRun | undefined {
    const run = this.runs.get(id);
    if (run) {
      this.runs.delete(id);
      this.runs.set(id, run);
    }
    return run;
  }

  put(id: string, run: LoadedRun): void {
    this.runs.delete(id);
    this.runs.set(id, run);
    while (this.runs.size > this.maxRuns) this.runs.delete(this.runs.keys().next().value as string);
  }

  index(base: string, f?: Fetcher): Promise<IndexFile> {
    return memo(this.indexes, base, () => loadIndex(base, f));
  }

  experiment(base: string, entry: IndexEntry, f?: Fetcher): Promise<ExperimentBundle> {
    const key = `${base}|${entry.id}`;
    return memo(this.experiments, key, async () => {
      const bundle = await loadExperiment(base, entry, f);
      this.ready.set(key, bundle);
      return bundle;
    });
  }

  loadedExperiment(base: string, id: string): ExperimentBundle | undefined {
    return this.ready.get(`${base}|${id}`);
  }
}

function memo<T>(map: Map<string, Promise<T>>, key: string, make: () => Promise<T>): Promise<T> {
  let p = map.get(key);
  if (!p) {
    p = make();
    map.set(key, p);
    p.catch(() => map.delete(key));
  }
  return p;
}

const dirOf = (path: string) => path.slice(0, Math.max(0, path.lastIndexOf("/")));
const join = (a: string, b: string) => (a ? `${a}/${b}` : b);

interface LoadSlot {
  token: number;
  controller: AbortController | null;
}
const slots = new WeakMap<Store, LoadSlot>();

export type LoadProgress = (file: string, done: number, total: number) => void;

export async function loadComparison(
  base: string,
  store: Store,
  cache: RunCache,
  f?: Fetcher,
  onProgress?: LoadProgress,
): Promise<{ left: LoadedRun; right: LoadedRun } | "stale"> {
  const slot = slots.get(store) ?? { token: 0, controller: null };
  slots.set(store, slot);
  slot.controller?.abort();
  const controller = (slot.controller = new AbortController());
  const mine = ++slot.token;
  const { experimentId, seed, comparisonId } = store.get();
  const current = () => slot.token === mine;

  try {
    const index = await cache.index(base, f);
    const entry = index.experiments.find((e) => e.id === experimentId);
    if (!entry) throw new ReplayError("schema", `Experiment ${experimentId} is not listed in index.json`, "index.json");
    const { catalog } = await cache.experiment(base, entry, f);
    if (!current()) return "stale";
    const seedEntry = catalog.seeds.find((s) => s.seed === seed);
    if (!seedEntry) throw new ReplayError("schema", `Seed ${seed} is not in the ${experimentId} catalog`, entry.catalog);
    const cmp = catalog.comparisons.find((c) => c.id === comparisonId);
    if (!cmp) throw new ReplayError("schema", `Comparison ${comparisonId} is not in the ${experimentId} catalog`, entry.catalog);

    const expDir = dirOf(entry.catalog);
    const done = [0, 0];
    const total = [0, 0];
    const fetchRun = async (policy: typeof cmp.left, side: 0 | 1): Promise<LoadedRun> => {
      const key = `${experimentId}:${policy}:${seed}`;
      const hit = cache.get(key);
      if (hit) return hit;
      const path = seedEntry.runs[policy];
      if (!path) throw new ReplayError("schema", `No ${policy} run for seed ${seed}`, entry.catalog);
      const run = await loadRun(base, expDir, path, f, controller.signal, (file, d, t) => {
        done[side] = d;
        total[side] = t;
        if (current() && !controller.signal.aborted) onProgress?.(file, done[0] + done[1], total[0] + total[1]);
      });
      const { experiment_id, policy: runPolicy, seed: runSeed } = run.meta;
      if (experiment_id !== experimentId || runPolicy !== policy || runSeed !== seed) {
        const runFile = join(expDir, path);
        throw new ReplayError(
          "mismatch",
          `${path}: run.json describes ${experiment_id} ${runPolicy} seed ${runSeed}, but the catalog slot is ${experimentId} ${policy} seed ${seed}`,
          runFile,
        );
      }
      return run;
    };
    const [left, right] = await Promise.all([fetchRun(cmp.left, 0), fetchRun(cmp.right, 1)]);
    if (!current()) return "stale";
    try {
      assertComparable(left, right);
    } catch (e) {
      if (e instanceof ReplayError) {
        throw new ReplayError(e.kind, `${e.message} (${left.meta.run_id} vs ${right.meta.run_id})`, e.file);
      }
      throw e;
    }
    cache.put(`${experimentId}:${cmp.left}:${seed}`, left);
    cache.put(`${experimentId}:${cmp.right}:${seed}`, right);
    return { left, right };
  } catch (e) {
    if (!current()) return "stale";
    controller.abort();
    throw e;
  }
}

export function stateFromQuery(search: string, nTicks = DEFAULT_N_TICKS): Partial<AppState> {
  const p = new URLSearchParams(search);
  const out: Partial<AppState> = {};
  const exp = p.get("exp");
  if (exp) out.experimentId = exp;
  const seed = p.get("seed");
  if (seed && Number.isInteger(Number(seed))) out.seed = Number(seed);
  const cmp = p.get("cmp");
  if (cmp) out.comparisonId = cmp;
  const t = p.get("t");
  if (t && Number.isFinite(Number(t))) out.tick = tsToTick(Number(t), nTicks);
  return out;
}

export const dataDirFromQuery = (search: string): string => new URLSearchParams(search).get("data") || DEFAULT_DATA_DIR;

export function stateToQuery(s: AppState, dataDir: string): string {
  const p = new URLSearchParams();
  p.set("data", dataDir);
  if (s.experimentId) p.set("exp", s.experimentId);
  p.set("seed", String(s.seed));
  if (s.comparisonId) p.set("cmp", s.comparisonId);
  p.set("t", String(tickToTs(s.tick)));
  return `?${p}`;
}

export function defaultSelection(cat: Catalog): { seed: number; comparisonId: string } {
  const cmp = cat.comparisons.find((c) => c.default) ?? cat.comparisons[0];
  return { seed: cat.default_seed, comparisonId: cmp?.id ?? "" };
}

export function resolveSelection(
  cat: Catalog,
  want: { seed?: number; comparisonId?: string },
): { seed: number; comparisonId: string } {
  const def = defaultSelection(cat);
  return {
    seed: cat.seeds.some((s) => s.seed === want.seed) ? want.seed! : def.seed,
    comparisonId: cat.comparisons.some((c) => c.id === want.comparisonId) ? want.comparisonId! : def.comparisonId,
  };
}
