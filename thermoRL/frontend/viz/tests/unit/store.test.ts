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

test("RACE: the newest comparison load wins and the superseded one is stale", async () => {
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

test("RACE: a superseded load whose fetches ignore the abort signal is still stale", async () => {
  const { f } = await fixtureFetcher({ seed: 1, ms: 50, honourAbort: false });
  const store = newStore({ seed: 1 });
  const cache = new RunCache();
  const first = loadComparison(BASE, store, cache, f);
  store.set({ seed: 2 });
  const second = loadComparison(BASE, store, cache, f);
  expect(await second).not.toBe("stale");
  expect(await first).toBe("stale");
  expect(cache.get("EFIX:power_balance:1")).toBeUndefined();
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
