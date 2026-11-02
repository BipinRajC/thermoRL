import { expect, test, vi } from "vitest";
import { buildFixture } from "../fixture/buildFixture";
import type { Fetcher, LoadedRun } from "../../src/data/loader";
import { ReplayError } from "../../src/data/loader";
import {
  RunCache,
  Store,
  dataDirFromQuery,
  loadComparison,
  stateFromQuery,
  stateToQuery,
  type AppState,
} from "../../src/model/store";

const BASE = "replay-fixture";

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const id = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(id);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

async function fixtureFetcher(delaySeed?: { seed: number; ms: number; honourAbort: boolean }) {
  const files = await buildFixture({ seeds: [1, 2] });
  const seen: string[] = [];
  const f: Fetcher = async (url, init) => {
    seen.push(url);
    if (delaySeed && url.includes(`_seed${delaySeed.seed}/`)) {
      await sleep(delaySeed.ms, delaySeed.honourAbort ? init?.signal : undefined);
    }
    const bytes = files.get(url.startsWith(`${BASE}/`) ? url.slice(BASE.length + 1) : url);
    return bytes ? new Response(bytes as BodyInit) : new Response(null, { status: 404 });
  };
  return { f, seen, files };
}

const newStore = (over: Partial<AppState> = {}) =>
  new Store({ experimentId: "EFIX", seed: 1, comparisonId: "pb_vs_tp", ...over });

test("set merges and notifies with the previous state", () => {
  const store = newStore();
  const calls: [AppState, AppState][] = [];
  const off = store.subscribe((s, prev) => calls.push([s, prev]));
  store.set({ tick: 42, overlay: "kw" });
  expect(store.get().tick).toBe(42);
  expect(store.get().overlay).toBe("kw");
  expect(store.get().seed).toBe(1);
  expect(calls).toHaveLength(1);
  expect(calls[0][0].tick).toBe(42);
  expect(calls[0][1].tick).toBe(0);
  expect(calls[0][1].overlay).toBe("tc");
  store.set({ tick: 42 });
  expect(calls).toHaveLength(1);
  off();
  store.set({ tick: 43 });
  expect(calls).toHaveLength(1);
});

test("RACE: a load superseded before the catalog resolves is stale and the newest wins", async () => {
  const { f } = await fixtureFetcher({ seed: 1, ms: 50, honourAbort: true });
  const store = newStore({ seed: 1 });
  const cache = new RunCache();
  const first = loadComparison(BASE, store, cache, f);
  store.set({ seed: 2 });
  const second = loadComparison(BASE, store, cache, f);
  const [a, b] = await Promise.all([first, second]);
  expect(a).toBe("stale");
  expect(b).not.toBe("stale");
  if (b === "stale") return;
  expect(b.left.meta.seed).toBe(2);
  expect(b.right.meta.seed).toBe(2);
  expect(b.left.meta.policy).toBe("power_balance");
  expect(b.right.meta.policy).toBe("thermal_predictive");
  expect(store.get().seed).toBe(2);
  expect(cache.get("EFIX:power_balance:1")).toBeUndefined();
  expect(cache.get("EFIX:power_balance:2")).toBe(b.left);
});

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((r) => (resolve = r));
  return { promise, resolve };
}

async function gatedFetcher(onGate: "serve" | "fail") {
  const files = await buildFixture({ seeds: [1, 2] });
  const started = deferred();
  const gate = deferred();
  const f: Fetcher = async (url) => {
    if (url.includes("_seed1/") && !url.endsWith("run.json")) {
      started.resolve();
      await gate.promise;
      if (onGate === "fail") throw new TypeError("network down");
    }
    const bytes = files.get(url.startsWith(`${BASE}/`) ? url.slice(BASE.length + 1) : url);
    return bytes ? new Response(bytes as BodyInit) : new Response(null, { status: 404 });
  };
  const warm = async (cache: RunCache) => {
    const index = await cache.index(BASE, f);
    await cache.experiment(BASE, index.experiments[0], f);
  };
  return { f, warm, started: started.promise, release: gate.resolve };
}

test("RACE: a load superseded while its run files are in flight is stale and reports no further progress", async () => {
  const { f, warm, started, release } = await gatedFetcher("serve");
  const store = newStore({ seed: 1 });
  const cache = new RunCache();
  await warm(cache);
  const progress = vi.fn();
  const first = loadComparison(BASE, store, cache, f, progress);
  await started;
  const before = progress.mock.calls.length;
  expect(before).toBeGreaterThan(0);
  store.set({ seed: 2 });
  const second = loadComparison(BASE, store, cache, f);
  release();
  const [a, b] = await Promise.all([first, second]);
  expect(a).toBe("stale");
  expect(b).not.toBe("stale");
  expect(progress.mock.calls.length).toBe(before);
  expect(store.get().seed).toBe(2);
  expect(cache.get("EFIX:power_balance:1")).toBeUndefined();
  expect(cache.get("EFIX:power_balance:2")).toBeDefined();
});

test("RACE: an in-flight load that rejects after being superseded resolves stale, not an error", async () => {
  const { f, warm, started, release } = await gatedFetcher("fail");
  const store = newStore({ seed: 1 });
  const cache = new RunCache();
  await warm(cache);
  const first = loadComparison(BASE, store, cache, f);
  await started;
  store.set({ seed: 2 });
  const second = loadComparison(BASE, store, cache, f);
  release();
  await expect(first).resolves.toBe("stale");
  const b = await second;
  expect(b).not.toBe("stale");
  expect(cache.get("EFIX:power_balance:1")).toBeUndefined();
});

test("RACE: a load that finishes after being superseded is stale and does not touch the cache", async () => {
  const { f } = await fixtureFetcher();
  const store = newStore({ seed: 1 });
  const puts: string[] = [];
  let hook: (() => void) | null = null;
  class HookCache extends RunCache {
    get(id: string) {
      const h = hook;
      hook = null;
      h?.();
      return super.get(id);
    }
    put(id: string, run: LoadedRun) {
      puts.push(id);
      super.put(id, run);
    }
  }
  const cache = new HookCache();
  expect(await loadComparison(BASE, store, cache, f)).not.toBe("stale");
  puts.length = 0;
  let second!: ReturnType<typeof loadComparison>;
  hook = () => {
    store.set({ seed: 2 });
    second = loadComparison(BASE, store, cache, f);
  };
  const first = await loadComparison(BASE, store, cache, f);
  expect(first).toBe("stale");
  const b = await second;
  expect(b).not.toBe("stale");
  expect(store.get().seed).toBe(2);
  expect(puts.every((id) => id.endsWith(":2"))).toBe(true);
  expect(puts).toHaveLength(2);
});

test("progress is only reported for the current load", async () => {
  const { f } = await fixtureFetcher();
  const store = newStore();
  const cache = new RunCache();
  const progress = vi.fn();
  const res = await loadComparison(BASE, store, cache, f, progress);
  expect(res).not.toBe("stale");
  expect(progress).toHaveBeenCalled();
  const last = progress.mock.calls[progress.mock.calls.length - 1];
  expect(last[1]).toBe(16);
  expect(last[2]).toBe(16);
  expect(String(progress.mock.calls[0][0])).toContain("runs/");
});

test("a cached comparison loads without fetching run files", async () => {
  const { f, seen } = await fixtureFetcher();
  const store = newStore();
  const cache = new RunCache();
  await loadComparison(BASE, store, cache, f);
  seen.length = 0;
  const again = await loadComparison(BASE, store, cache, f);
  expect(again).not.toBe("stale");
  expect(seen.filter((u) => u.includes("/runs/"))).toEqual([]);
});

test("an unknown seed or comparison rejects with a schema error", async () => {
  const { f } = await fixtureFetcher();
  await expect(loadComparison(BASE, newStore({ seed: 9 }), new RunCache(), f)).rejects.toMatchObject({ kind: "schema" });
  await expect(loadComparison(BASE, newStore({ comparisonId: "nope" }), new RunCache(), f)).rejects.toMatchObject({
    kind: "schema",
  });
});

test("a corrupted run file rejects with the file named, never stale", async () => {
  const { f, files } = await fixtureFetcher();
  const bad = files.get("EFIX/runs/power_balance_seed1/rack_tc.f32")!.slice();
  bad[0] ^= 1;
  files.set("EFIX/runs/power_balance_seed1/rack_tc.f32", bad);
  const progress = vi.fn();
  const err = await loadComparison(BASE, newStore(), new RunCache(), f, progress).catch((e) => e);
  expect(err).toBeInstanceOf(ReplayError);
  expect(err.kind).toBe("hash");
  expect(err.file).toContain("power_balance_seed1/rack_tc.f32");
  const n = progress.mock.calls.length;
  await sleep(50);
  expect(progress.mock.calls.length).toBe(n);
});

test("a run whose meta names another experiment, policy or seed than the catalog slot is rejected", async () => {
  const cases: [string, (m: any) => void, RegExp][] = [
    ["experiment_id", (m) => (m.experiment_id = "EOTHER"), /EOTHER/],
    ["policy", (m) => (m.policy = "packing"), /packing/],
    ["seed", (m) => (m.seed = 2), /seed/],
  ];
  for (const [field, edit, text] of cases) {
    const { f, files } = await fixtureFetcher();
    const path = "EFIX/runs/power_balance_seed1/run.json";
    const m = JSON.parse(new TextDecoder().decode(files.get(path)!));
    edit(m);
    files.set(path, new TextEncoder().encode(JSON.stringify(m)));
    const err = await loadComparison(BASE, newStore(), new RunCache(), f).catch((e) => e);
    expect(err, field).toBeInstanceOf(ReplayError);
    expect(err.kind, field).toBe("mismatch");
    expect(err.message, field).toContain("power_balance_seed1");
    expect(err.message, field).toMatch(text);
    expect(err.file, field).toContain("power_balance_seed1/run.json");
  }
});

test("a mismatched run is never cached", async () => {
  const { f, files } = await fixtureFetcher();
  const path = "EFIX/runs/thermal_predictive_seed1/run.json";
  const good = files.get(path)!;
  const m = JSON.parse(new TextDecoder().decode(good));
  m.seed = 2;
  files.set(path, new TextEncoder().encode(JSON.stringify(m)));
  const cache = new RunCache();
  await expect(loadComparison(BASE, newStore(), cache, f)).rejects.toMatchObject({ kind: "mismatch" });
  expect(cache.get("EFIX:thermal_predictive:1")).toBeUndefined();
  expect(cache.get("EFIX:power_balance:1")).toBeUndefined();
  files.set(path, good);
  const res = await loadComparison(BASE, newStore(), cache, f);
  expect(res).not.toBe("stale");
});

test("RunCache evicts the least recently used entry beyond 6", () => {
  const cache = new RunCache();
  const run = (n: number) => ({ n }) as unknown as LoadedRun;
  for (const id of ["a", "b", "c", "d", "e", "f"]) cache.put(id, run(1));
  expect(cache.get("a")).toBeDefined();
  cache.put("g", run(2));
  expect(cache.get("b")).toBeUndefined();
  for (const id of ["a", "c", "d", "e", "f", "g"]) expect(cache.get(id)).toBeDefined();
  cache.put("h", run(3));
  expect(cache.get("a")).toBeUndefined();
  expect(cache.get("c")).toBeDefined();
});

test("URL round-trip", () => {
  const q = "?exp=EFIX&seed=2&cmp=packing_vs_tp&t=3610";
  const s = stateFromQuery(q);
  expect(s).toMatchObject({ experimentId: "EFIX", seed: 2, comparisonId: "packing_vs_tp", tick: 360 });
  const full = new Store(s).get();
  const out = stateToQuery(full, "replay-fixture");
  expect(out).toBe("?data=replay-fixture&exp=EFIX&seed=2&cmp=packing_vs_tp&t=3610");
  expect(stateFromQuery(out)).toEqual(s);
  expect(dataDirFromQuery(out)).toBe("replay-fixture");
});

test("query parsing ignores malformed values and clamps time", () => {
  expect(stateFromQuery("")).toEqual({});
  expect(stateFromQuery("?seed=abc&t=x&exp=")).toEqual({});
  expect(stateFromQuery("?t=0").tick).toBe(0);
  expect(stateFromQuery("?t=99999").tick).toBe(2159);
  expect(stateFromQuery("?t=99999", 400).tick).toBe(399);
  expect(dataDirFromQuery("")).toBe("replay");
});
