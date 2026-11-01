import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildFixture } from "../tests/fixture/buildFixture.ts";

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), "sync-replay.mjs");
const DEMO_NAMES = [
  "heatmaps_seed1.png",
  "timeseries_seed1.png",
  "anim_packing_vs_thermal_predictive_seed1.gif",
  "anim_power_balance_vs_thermal_predictive_seed1.gif",
];

const tmp = mkdtempSync(join(tmpdir(), "sync-replay-"));
process.on("exit", () => rmSync(tmp, { recursive: true, force: true }));

function expRoot(source, eid) {
  return join(source, "thermoRL", "backend", "experiments", "summit", eid);
}

function writeTree(source, eid, files, withDemo = null) {
  const root = expRoot(source, eid);
  for (const [rel, bytes] of files) {
    const dest = join(root, "exports", "replay_v1", rel.slice(rel.indexOf("/") + 1));
    if (rel.indexOf("/") < 0) continue;
    mkdirSync(dirname(dest), { recursive: true });
    if (rel.endsWith("/catalog.json")) {
      const catalog = JSON.parse(new TextDecoder().decode(bytes));
      if (catalog.experiment.id === "EFIX") catalog.experiment.id = eid;
      writeFileSync(dest, JSON.stringify(catalog));
    } else {
      writeFileSync(dest, bytes);
    }
  }
  if (withDemo) {
    const assets = {};
    mkdirSync(join(root, "plots", "demo"), { recursive: true });
    mkdirSync(join(root, "provenance"), { recursive: true });
    for (const name of DEMO_NAMES) {
      const bytes = Buffer.from(`demo asset ${eid} ${name}`);
      writeFileSync(join(root, "plots", "demo", name), bytes);
      assets[`plots/demo/${name}`] = { bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex") };
    }
    if (withDemo.badHash) assets[`plots/demo/${DEMO_NAMES[0]}`].sha256 = "0".repeat(64);
    writeFileSync(join(root, "provenance", "demo_asset_inventory.json"), JSON.stringify({ assets }));
  }
}

function snapshot(dir) {
  const out = [];
  const walk = (d) => {
    for (const name of readdirSync(d).sort()) {
      const p = join(d, name);
      if (statSync(p).isDirectory()) walk(p);
      else out.push(`${p.slice(dir.length)}:${createHash("sha256").update(readFileSync(p)).digest("hex")}`);
    }
  };
  walk(dir);
  return out;
}

function run(source, out, experiments) {
  return spawnSync(process.execPath, [SCRIPT, "--source", source, "--out", out, "--experiments", experiments], {
    encoding: "utf8",
  });
}

const fixture = await buildFixture();

test("syncs a verified fixture tree and writes index.json", () => {
  const source = join(tmp, "ok-src");
  const out = join(tmp, "ok-out");
  writeTree(source, "EFIX", fixture);
  const r = run(source, out, "EFIX");
  assert.equal(r.status, 0, r.stderr + r.stdout);
  const index = JSON.parse(readFileSync(join(out, "replay", "index.json"), "utf8"));
  assert.equal(index.schema, "thermorl.replay.v1");
  assert.deepEqual(index.experiments, [
    { id: "EFIX", short: "EFIX", label: "EFIX — Fixture workload", catalog: "EFIX/catalog.json", default: true },
  ]);
  const copied = readFileSync(join(out, "replay", "EFIX", "runs", "packing_seed1", "rack_tc.f32"));
  assert.equal(copied.byteLength, fixture.get("EFIX/runs/packing_seed1/rack_tc.f32").byteLength);
  assert.match(r.stdout, /EFIX/);
  assert.match(r.stdout, /files/);
});

test("a corrupted file exits 1, names the file and copies nothing", async () => {
  const source = join(tmp, "bad-src");
  const out = join(tmp, "bad-out");
  writeTree(source, "EFIX", fixture);
  assert.equal(run(source, out, "EFIX").status, 0);
  const before = snapshot(out);

  const target = "EFIX/runs/power_balance_seed2/rack_kw.f32";
  const corrupt = await buildFixture({ corrupt: { file: target } });
  const source2 = join(tmp, "bad-src2");
  writeTree(source2, "EFIX", corrupt);
  const r = run(source2, out, "EFIX");
  assert.equal(r.status, 1, r.stderr + r.stdout);
  assert.match(r.stderr, /power_balance_seed2[\\/]rack_kw\.f32/);
  assert.deepEqual(snapshot(out), before);
});

test("a corrupted file into an empty out dir leaves nothing behind", async () => {
  const source = join(tmp, "bad3-src");
  const out = join(tmp, "bad3-out");
  const corrupt = await buildFixture({ corrupt: { file: "EFIX/runs/packing_seed1/events.json" } });
  writeTree(source, "EFIX", corrupt);
  const r = run(source, out, "EFIX");
  assert.equal(r.status, 1, r.stderr + r.stdout);
  assert.match(r.stderr, /packing_seed1[\\/]events\.json/);
  assert.throws(() => statSync(join(out, "replay")));
});

test("a stray file in a run directory exits 1", () => {
  const source = join(tmp, "stray-src");
  const out = join(tmp, "stray-out");
  writeTree(source, "EFIX", fixture);
  writeFileSync(join(expRoot(source, "EFIX"), "exports", "replay_v1", "runs", "packing_seed1", "stray.bin"), "x");
  const r = run(source, out, "EFIX");
  assert.equal(r.status, 1, r.stderr + r.stdout);
  assert.match(r.stderr, /stray\.bin/);
  assert.throws(() => statSync(join(out, "replay")));
});

test("a missing catalog exits 2", () => {
  const source = join(tmp, "nocat-src");
  const out = join(tmp, "nocat-out");
  mkdirSync(expRoot(source, "EFIX"), { recursive: true });
  const r = run(source, out, "EFIX");
  assert.equal(r.status, 2, r.stderr + r.stdout);
  assert.match(r.stderr, /catalog\.json/);
});

test("real experiment ids copy verified fallback assets; the first id is the default", () => {
  const source = join(tmp, "real-src");
  const out = join(tmp, "real-out");
  writeTree(source, "E12_g4_alibaba", fixture, {});
  writeTree(source, "E11_g4_synthetic", fixture, {});
  const r = run(source, out, "E12_g4_alibaba,E11_g4_synthetic");
  assert.equal(r.status, 0, r.stderr + r.stdout);
  const index = JSON.parse(readFileSync(join(out, "replay", "index.json"), "utf8"));
  assert.deepEqual(
    index.experiments.map((e) => [e.id, e.default === true]),
    [
      ["E12_g4_alibaba", true],
      ["E11_g4_synthetic", false],
    ],
  );
  for (const eid of ["E12_g4_alibaba", "E11_g4_synthetic"]) {
    assert.deepEqual(readdirSync(join(out, "fallback", eid)).sort(), [...DEMO_NAMES].sort());
  }
});

test("a hash-mismatched fallback asset exits 1 and copies nothing", () => {
  const source = join(tmp, "fb-src");
  const out = join(tmp, "fb-out");
  writeTree(source, "E11_g4_synthetic", fixture, { badHash: true });
  const r = run(source, out, "E11_g4_synthetic");
  assert.equal(r.status, 1, r.stderr + r.stdout);
  assert.match(r.stderr, /heatmaps_seed1\.png/);
  assert.throws(() => statSync(join(out, "replay")));
  assert.throws(() => statSync(join(out, "fallback")));
});

test("a real id without plots/demo exits 2; a test id without it is skipped", () => {
  const source = join(tmp, "nodemo-src");
  writeTree(source, "E11_g4_synthetic", fixture);
  const r = run(source, join(tmp, "nodemo-out"), "E11_g4_synthetic");
  assert.equal(r.status, 2, r.stderr + r.stdout);
  assert.match(r.stderr, /plots[\\/]demo/);

  const ok = run(join(tmp, "ok-src"), join(tmp, "nodemo-out2"), "EFIX");
  assert.equal(ok.status, 0, ok.stderr + ok.stdout);
  assert.match(ok.stdout, /skip/i);
});

test("experiment ids outside [A-Za-z0-9_] exit 64 before touching anything", () => {
  const out = join(tmp, "badid-out");
  for (const ids of ["../escape", "EFIX/../x", "E 1", "EFIX,E-2", "a.b"]) {
    const r = run(join(tmp, "ok-src"), out, ids);
    assert.equal(r.status, 64, `${ids}: ${r.stderr + r.stdout}`);
    assert.match(r.stderr, /--experiments/);
  }
  assert.throws(() => statSync(join(out, "replay")));
});

test("a catalog whose experiment.id differs from the requested id exits 1 naming the file", () => {
  const source = join(tmp, "idmismatch-src");
  const out = join(tmp, "idmismatch-out");
  const files = new Map(fixture);
  const catalog = JSON.parse(new TextDecoder().decode(files.get("EFIX/catalog.json")));
  catalog.experiment.id = "EOTHER";
  files.set("EFIX/catalog.json", new TextEncoder().encode(JSON.stringify(catalog)));
  writeTree(source, "EFIX", files);
  const r = run(source, out, "EFIX");
  assert.equal(r.status, 1, r.stderr + r.stdout);
  assert.match(r.stderr, /EFIX[\\/]catalog\.json/);
  assert.match(r.stderr, /EOTHER/);
  assert.throws(() => statSync(join(out, "replay")));
});
