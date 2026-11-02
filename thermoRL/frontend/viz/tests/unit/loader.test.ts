import { createHash } from "node:crypto";
import { afterEach, expect, test, vi } from "vitest";
import { buildFixture, fixtureFree, fixtureKw, fixtureTc } from "../fixture/buildFixture";
import { sha256Hex } from "../../src/data/hash";
import {
  ReplayError,
  assertComparable,
  loadExperiment,
  loadIndex,
  loadRun,
  type Fetcher,
  type LoadedRun,
} from "../../src/data/loader";

const BASE = "replay-fixture";
const RUN_DIR = "EFIX/runs/packing_seed1";
const RUN_JSON = "runs/packing_seed1/run.json";
const dec = (b: Uint8Array) => new TextDecoder().decode(b);
const enc = (v: unknown) => new TextEncoder().encode(JSON.stringify(v));

const fetcherFor =
  (files: Map<string, Uint8Array>, base = BASE): Fetcher =>
  async (url, init) => {
    if (init?.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const bytes = files.get(url.startsWith(`${base}/`) ? url.slice(base.length + 1) : url);
    return bytes ? new Response(bytes as BodyInit) : new Response(null, { status: 404 });
  };

const edit = (files: Map<string, Uint8Array>, path: string, fn: (j: any) => void) => {
  const j = JSON.parse(dec(files.get(path)!));
  fn(j);
  files.set(path, enc(j));
};

const load = (files: Map<string, Uint8Array>, policy = "packing", seed = 1) =>
  loadRun(BASE, "EFIX", `runs/${policy}_seed${seed}/run.json`, fetcherFor(files));

test("sha256Hex matches a known digest", async () => {
  expect(await sha256Hex(new TextEncoder().encode("abc"))).toBe(
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  );
  expect(await sha256Hex(new TextEncoder().encode("abc").buffer)).toBe(
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  );
});

afterEach(() => vi.unstubAllGlobals());

test("sha256Hex without crypto.subtle (non-secure origin) rejects with a hash ReplayError", async () => {
  vi.stubGlobal("crypto", { subtle: undefined });
  const err = await sha256Hex(new Uint8Array([1])).catch((e) => e);
  expect(err).toBeInstanceOf(ReplayError);
  expect(err).toMatchObject({ kind: "hash", message: "Hash verification needs a secure context (localhost or https)" });
});

test("loadRun on a non-secure origin reports the secure-context error, not a TypeError", async () => {
  const files = await buildFixture();
  vi.stubGlobal("crypto", { subtle: undefined });
  await expect(load(files)).rejects.toMatchObject({ kind: "hash", message: /secure context/ });
});

test("loads a valid run", async () => {
  const files = await buildFixture();
  const progress: [string, number, number][] = [];
  const run = await loadRun(BASE, "EFIX", RUN_JSON, fetcherFor(files), undefined, (f, d, t) =>
    progress.push([f, d, t]),
  );
  expect(run.meta.run_id).toBe("EFIX:packing_seed1");
  expect(run.tc.length).toBe(400 * 11);
  expect(run.tc[0]).toBe(Math.fround(fixtureTc("packing", 0, 0)));
  expect(run.tc[7 * 11 + 4]).toBe(Math.fround(fixtureTc("packing", 7, 4)));
  expect(run.kw[7 * 11 + 4]).toBe(fixtureKw(7, 4));
  expect(run.free[7 * 11 + 4]).toBe(fixtureFree(7, 4));
  expect(run.tick.length).toBe(400 * 8);
  expect(run.tick[0]).toBe(10);
  expect(run.tick[8]).toBe(20);
  expect(run.events.kind.length).toBe(run.meta.n_events);
  expect(run.events.rack_offsets.length).toBe(run.meta.n_events + 1);
  expect(run.decisions.raps_t_s.length).toBe(run.meta.n_decisions);
  expect(run.decisions.raps_t_s).toBeInstanceOf(Int32Array);
  expect(run.decisions.job_kw).toBeInstanceOf(Float64Array);
  expect(run.decisions.t_obs_s).toBeInstanceOf(Float64Array);
  expect(run.decisions.chosen_is_logged_best).toBeInstanceOf(Uint8Array);
  expect(Array.isArray(run.decisions.rule)).toBe(true);
  expect(["single", "span"]).toContain(run.decisions.rule[0]);
  for (let i = 1; i < run.decisions.raps_t_s.length; i++) {
    expect(run.decisions.raps_t_s[i]).toBeGreaterThanOrEqual(run.decisions.raps_t_s[i - 1]);
  }
  expect(run.candidates.byteLength).toBe(run.meta.n_decisions * 6 * 15);
  const rack0 = run.candidates.getUint16(0, true);
  expect(rack0).toBeLessThan(11);
  expect(progress).toHaveLength(8);
  expect(progress.map((p) => p[1])).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  expect(progress.every((p) => p[2] === 8)).toBe(true);
  expect(progress[0][0]).toBe(`${RUN_DIR}/run.json`);
});

test("loads index and experiment, validating schema", async () => {
  const files = await buildFixture();
  const f = fetcherFor(files);
  const index = await loadIndex(BASE, f);
  expect(index.experiments[0].id).toBe("EFIX");
  const { catalog, outcome } = await loadExperiment(BASE, index.experiments[0], f);
  expect(catalog.grid.n_racks).toBe(11);
  expect(outcome.experiment_id).toBe("EFIX");
});

test("index schema mismatch rejects with schema", async () => {
  const files = await buildFixture();
  edit(files, "index.json", (j) => (j.schema = "x"));
  await expect(loadIndex(BASE, fetcherFor(files))).rejects.toMatchObject({ kind: "schema", file: "index.json" });
});

test("catalog schema mismatch rejects with schema", async () => {
  const files = await buildFixture();
  edit(files, "EFIX/catalog.json", (j) => (j.schema = "x"));
  const f = fetcherFor(files);
  const index = await loadIndex(BASE, f);
  await expect(loadExperiment(BASE, index.experiments[0], f)).rejects.toMatchObject({
    kind: "schema",
    file: "EFIX/catalog.json",
  });
});

test("frozen outcome schema mismatch rejects with schema", async () => {
  const files = await buildFixture();
  edit(files, "EFIX/frozen_outcome.json", (j) => (j.schema = "x"));
  const f = fetcherFor(files);
  const index = await loadIndex(BASE, f);
  await expect(loadExperiment(BASE, index.experiments[0], f)).rejects.toMatchObject({
    kind: "schema",
    file: "EFIX/frozen_outcome.json",
  });
});

test("run schema mismatch rejects with schema", async () => {
  const files = await buildFixture();
  edit(files, `${RUN_DIR}/run.json`, (j) => (j.schema = "x"));
  await expect(load(files)).rejects.toMatchObject({ kind: "schema", file: `${RUN_DIR}/run.json` });
});

test("missing file rejects with missing and the path", async () => {
  const files = await buildFixture();
  files.delete(`${RUN_DIR}/rack_kw.f32`);
  const err = await load(files).catch((e) => e);
  expect(err).toBeInstanceOf(ReplayError);
  expect(err).toMatchObject({ kind: "missing", file: `${RUN_DIR}/rack_kw.f32` });
});

test("missing run.json rejects with missing", async () => {
  const files = await buildFixture();
  files.delete(`${RUN_DIR}/run.json`);
  await expect(load(files)).rejects.toMatchObject({ kind: "missing", file: `${RUN_DIR}/run.json` });
});

test("non-404 HTTP failure and thrown fetch reject with network", async () => {
  const files = await buildFixture();
  const server500: Fetcher = async () => new Response(null, { status: 500 });
  await expect(loadRun(BASE, "EFIX", RUN_JSON, server500)).rejects.toMatchObject({ kind: "network" });
  const offline: Fetcher = async () => {
    throw new TypeError("Failed to fetch");
  };
  await expect(loadRun(BASE, "EFIX", RUN_JSON, offline)).rejects.toMatchObject({ kind: "network" });
  await expect(loadIndex(BASE, offline)).rejects.toMatchObject({ kind: "network", file: "index.json" });
  expect(files.size).toBeGreaterThan(0);
});

test("size mismatch rejects with size", async () => {
  const files = await buildFixture();
  const p = `${RUN_DIR}/rack_tc.f32`;
  const b = files.get(p)!;
  files.set(p, b.slice(0, b.byteLength - 4));
  await expect(load(files)).rejects.toMatchObject({ kind: "size", file: p });
});

test("hash mismatch rejects with hash", async () => {
  const p = `${RUN_DIR}/rack_tc.f32`;
  const files = await buildFixture({ corrupt: { file: p } });
  await expect(load(files)).rejects.toMatchObject({ kind: "hash", file: p });
});

test("corrupt json file is caught by size, or by hash before decoding", async () => {
  const p = `${RUN_DIR}/decisions.json`;
  const grown = await buildFixture({ corrupt: { file: p } });
  await expect(load(grown)).rejects.toMatchObject({ kind: "size", file: p });
  const files = await buildFixture();
  const bytes = files.get(p)!.slice();
  bytes[0] = 0x5b;
  files.set(p, bytes);
  await expect(load(files)).rejects.toMatchObject({ kind: "hash", file: p });
});

test("shape mismatch rejects with shape", async () => {
  const files = await buildFixture();
  edit(files, `${RUN_DIR}/run.json`, (j) => (j.files.rack_tc.shape = [399, 11]));
  await expect(load(files)).rejects.toMatchObject({ kind: "shape", file: `${RUN_DIR}/rack_tc.f32` });
});

test("assertComparable", async () => {
  const files = await buildFixture();
  const a = await load(files, "packing");
  const b = await load(files, "thermal_predictive");
  expect(() => assertComparable(a, b)).not.toThrow();

  const mismatch = (x: LoadedRun, y: LoadedRun) => {
    try {
      assertComparable(x, y);
    } catch (e) {
      expect(e).toBeInstanceOf(ReplayError);
      expect((e as ReplayError).kind).toBe("mismatch");
      return;
    }
    throw new Error("expected assertComparable to throw");
  };

  mismatch(a, { ...b, meta: { ...b.meta, n_ticks: b.meta.n_ticks - 1 } });
  mismatch(a, { ...b, meta: { ...b.meta, n_racks: b.meta.n_racks + 1 } });
  for (const k of [0, 123, 399]) {
    const tick = b.tick.slice();
    tick[k * 8] += 1;
    mismatch(a, { ...b, tick });
  }
  const other = b.tick.slice();
  other[3 * 8 + 4] += 1;
  expect(() => assertComparable(a, { ...b, tick: other })).not.toThrow();
});

test("an aborted signal rejects with AbortError, not ReplayError", async () => {
  const files = await buildFixture();
  const ctl = new AbortController();
  ctl.abort();
  const err = await loadRun(BASE, "EFIX", RUN_JSON, fetcherFor(files), ctl.signal).catch((e) => e);
  expect(err).not.toBeInstanceOf(ReplayError);
  expect(err).toBeInstanceOf(DOMException);
  expect(err.name).toBe("AbortError");
});

test("abort during a fetch is not reported as network", async () => {
  const files = await buildFixture();
  const ctl = new AbortController();
  const f = fetcherFor(files);
  const aborting: Fetcher = async (url, init) => {
    const r = await f(url, init);
    if (url.endsWith("run.json")) ctl.abort();
    return r;
  };
  const err = await loadRun(BASE, "EFIX", RUN_JSON, aborting, ctl.signal).catch((e) => e);
  expect(err).not.toBeInstanceOf(ReplayError);
  expect(err.name).toBe("AbortError");
});

const hex = (b: Uint8Array) => createHash("sha256").update(b).digest("hex");

function rewrite(
  files: Map<string, Uint8Array>,
  key: string,
  mutate: (bytes: Uint8Array) => Uint8Array,
  entry: (e: any) => void = () => {},
  meta: (m: any) => void = () => {},
) {
  const runPath = `${RUN_DIR}/run.json`;
  const m = JSON.parse(dec(files.get(runPath)!));
  const e = m.files[key];
  const path = `${RUN_DIR}/${e.path}`;
  const bytes = mutate(files.get(path)!);
  files.set(path, bytes);
  e.bytes = bytes.byteLength;
  e.sha256 = hex(bytes);
  entry(e);
  meta(m);
  files.set(runPath, enc(m));
  return path;
}

const dropJson = (fn: (j: any) => void) => (b: Uint8Array) => {
  const j = JSON.parse(dec(b));
  fn(j);
  return enc(j);
};

test("hash-consistent files whose shape disagrees with run.json meta are rejected, naming the file", async () => {
  const cases: [string, string, (b: Uint8Array) => Uint8Array, number[]][] = [
    ["rack_tc", "short ticks", (b) => b.slice(0, b.byteLength - 11 * 4), [399, 11]],
    ["rack_kw", "short ticks", (b) => b.slice(0, b.byteLength - 11 * 4), [399, 11]],
    ["rack_free", "short ticks", (b) => b.slice(0, b.byteLength - 11), [399, 11]],
    ["rack_tc", "wrong layout", (b) => b, [200, 22]],
    ["rack_free", "wrong layout", (b) => b, [11, 400]],
    ["tick", "short ticks", (b) => b.slice(0, b.byteLength - 8 * 8), [399, 8]],
    ["tick", "wrong columns", (b) => b, [800, 4]],
  ];
  for (const [key, label, mutate, shape] of cases) {
    const files = await buildFixture();
    const path = rewrite(files, key, mutate, (e) => (e.shape = shape));
    const err = await load(files).catch((e) => e);
    expect(err, `${key} ${label}`).toBeInstanceOf(ReplayError);
    expect(err, `${key} ${label}`).toMatchObject({ kind: "shape", file: path });
  }
});

test("meta.n_ticks or meta.n_racks that disagree with the decoded arrays are rejected", async () => {
  for (const edit of [(m: any) => (m.n_ticks = 401), (m: any) => (m.n_racks = 12)]) {
    const files = await buildFixture();
    const m = JSON.parse(dec(files.get(`${RUN_DIR}/run.json`)!));
    edit(m);
    files.set(`${RUN_DIR}/run.json`, enc(m));
    await expect(load(files)).rejects.toMatchObject({ kind: "shape", file: `${RUN_DIR}/rack_tc.f32` });
  }
});

test("a dtype that disagrees with the file role is rejected", async () => {
  const files = await buildFixture();
  const path = rewrite(files, "rack_tc", (b) => b, (e) => {
    e.dtype = "float64";
    e.shape = [200, 11];
  });
  await expect(load(files)).rejects.toMatchObject({ kind: "shape", file: path });
});

test("candidates.bin whose size is not n_decisions x 6 x 15 is rejected", async () => {
  const files = await buildFixture();
  const path = rewrite(files, "candidates", (b) => b.slice(0, b.byteLength - 90));
  await expect(load(files)).rejects.toMatchObject({ kind: "shape", file: path });
});

test("decision columns whose length disagrees with meta.n_decisions are rejected", async () => {
  for (const col of ["decision_index", "raps_t_s", "job_kw", "chosen_is_logged_best", "rule"]) {
    const files = await buildFixture();
    const path = rewrite(files, "decisions", dropJson((j) => j[col].pop()));
    await expect(load(files), col).rejects.toMatchObject({ kind: "mismatch", file: path });
  }
  const files = await buildFixture();
  const path = rewrite(files, "decisions", dropJson((j) => j.chosen_offsets.pop()));
  await expect(load(files)).rejects.toMatchObject({ kind: "mismatch", file: path });
});

test("flat rack lists that disagree with their offsets are rejected", async () => {
  for (const [key, col] of [
    ["events", "racks"],
    ["decisions", "chosen_racks"],
  ]) {
    const files = await buildFixture();
    const path = rewrite(files, key, dropJson((j) => j[col].pop()));
    await expect(load(files), col).rejects.toMatchObject({ kind: "mismatch", file: path });
  }
});

test("event columns whose length disagrees with meta.n_events are rejected", async () => {
  for (const col of ["kind", "rack_offsets", "raps_t_s", "decision_index"]) {
    const files = await buildFixture();
    const path = rewrite(files, "events", dropJson((j) => j[col].pop()));
    await expect(load(files), col).rejects.toMatchObject({ kind: "mismatch", file: path });
  }
  const files = await buildFixture();
  const path = rewrite(files, "events", (b) => b, () => {}, (m) => (m.n_events += 1));
  await expect(load(files)).rejects.toMatchObject({ kind: "mismatch", file: path });
});

test("meta.n_decisions that disagrees with the decoded decisions is rejected", async () => {
  const files = await buildFixture();
  const path = rewrite(files, "decisions", (b) => b, () => {}, (m) => (m.n_decisions += 1));
  await expect(load(files)).rejects.toMatchObject({ kind: "mismatch", file: path });
});

test("a missing column in events/decisions JSON is a schema ReplayError, not a TypeError", async () => {
  for (const [key, col] of [
    ["decisions", "job_kw"],
    ["decisions", "chosen_racks"],
    ["events", "racks"],
    ["events", "rack_offsets"],
  ]) {
    const files = await buildFixture();
    const path = rewrite(files, key, dropJson((j) => delete j[col]));
    const err = await load(files).catch((e) => e);
    expect(err, `${key}.${col}`).toBeInstanceOf(ReplayError);
    expect(err, `${key}.${col}`).toMatchObject({ kind: "schema", file: path });
    expect(err.message).toContain(col);
  }
  const files = await buildFixture();
  const path = rewrite(files, "events", () => enc([1, 2, 3]));
  await expect(load(files)).rejects.toMatchObject({ kind: "schema", file: path });
});
