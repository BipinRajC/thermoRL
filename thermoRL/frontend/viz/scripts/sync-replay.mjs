import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCHEMA = "thermorl.replay.v1";
const REAL_IDS = ["E12_g4_alibaba", "E11_g4_synthetic"];
const DEMO_NAMES = [
  "heatmaps_seed1.png",
  "timeseries_seed1.png",
  "anim_packing_vs_thermal_predictive_seed1.gif",
  "anim_power_balance_vs_thermal_predictive_seed1.gif",
];

const scriptDir = dirname(fileURLToPath(import.meta.url));

class SyncError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

const exists = (p) =>
  stat(p).then(
    () => true,
    () => false,
  );
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const fmtBytes = (n) => `${n.toLocaleString("en-US")} B (${(n / 1048576).toFixed(1)} MiB)`;

function parseArgs(argv) {
  const opts = {
    source: resolve(scriptDir, "..", "..", "..", ".."),
    experiments: [...REAL_IDS],
    out: resolve(scriptDir, "..", "public"),
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === "--source" || a === "--out" || a === "--experiments") {
      if (v === undefined) throw new SyncError(64, `${a} needs a value`);
      i++;
      if (a === "--source") opts.source = resolve(v);
      else if (a === "--out") opts.out = resolve(v);
      else opts.experiments = v.split(",").map((s) => s.trim()).filter(Boolean);
    } else {
      throw new SyncError(64, `unknown argument ${a}\nusage: node scripts/sync-replay.mjs [--source <repoRoot>] [--experiments EID1,EID2] [--out <dir>]`);
    }
  }
  if (opts.experiments.length === 0) throw new SyncError(64, "--experiments is empty");
  const bad = opts.experiments.find((id) => !/^[A-Za-z0-9_]+$/.test(id));
  if (bad !== undefined) throw new SyncError(64, `--experiments: invalid id ${JSON.stringify(bad)} (allowed: letters, digits, underscore)`);
  return opts;
}

async function readJson(path, label) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch (e) {
    throw new SyncError(1, `${label}: cannot read JSON (${e.message})`);
  }
}

async function verifyFile(path, label, bytes, sha) {
  const buf = await readFile(path).catch(() => {
    throw new SyncError(1, `${label}: listed file is missing`);
  });
  if (buf.byteLength !== bytes) throw new SyncError(1, `${label}: byte length ${buf.byteLength} != recorded ${bytes}`);
  const got = sha256(buf);
  if (got !== sha) throw new SyncError(1, `${label}: sha256 ${got} != recorded ${sha}`);
}

async function planExperiment(source, eid) {
  const root = join(source, "thermoRL", "backend", "experiments", "summit", eid);
  const base = join(root, "exports", "replay_v1");
  const catalogPath = join(base, "catalog.json");
  if (!(await exists(catalogPath))) throw new SyncError(2, `${eid}: required file not found: ${catalogPath}`);

  const copies = [];
  const add = (src, rel) => copies.push({ src, rel });

  const catalog = await readJson(catalogPath, `${eid}/catalog.json`);
  if (catalog.schema !== SCHEMA) throw new SyncError(1, `${eid}/catalog.json: schema ${JSON.stringify(catalog.schema)} != ${SCHEMA}`);
  const { id: catalogId, short, workload_label: workload } = catalog.experiment ?? {};
  if (catalogId !== eid) throw new SyncError(1, `${eid}/catalog.json: experiment.id ${JSON.stringify(catalogId)} != requested ${eid}`);
  if (!short || !workload) throw new SyncError(1, `${eid}/catalog.json: experiment.short / workload_label missing`);
  add(catalogPath, "catalog.json");

  const frozenPath = join(base, "frozen_outcome.json");
  if (!(await exists(frozenPath))) throw new SyncError(1, `${eid}/frozen_outcome.json: file is missing`);
  const frozen = await readJson(frozenPath, `${eid}/frozen_outcome.json`);
  if (frozen.schema !== SCHEMA) throw new SyncError(1, `${eid}/frozen_outcome.json: schema ${JSON.stringify(frozen.schema)} != ${SCHEMA}`);
  add(frozenPath, "frozen_outcome.json");

  const runsDir = join(base, "runs");
  const runNames = (await readdir(runsDir, { withFileTypes: true }).catch(() => [])).filter((d) => d.isDirectory()).map((d) => d.name).sort();
  if (runNames.length === 0) throw new SyncError(1, `${eid}/runs: no run directories`);
  for (const name of runNames) {
    const dir = join(runsDir, name);
    const runJsonPath = join(dir, "run.json");
    const label = `${eid}/runs/${name}`;
    if (!(await exists(runJsonPath))) throw new SyncError(1, `${label}/run.json: file is missing`);
    const run = await readJson(runJsonPath, `${label}/run.json`);
    if (run.schema !== SCHEMA) throw new SyncError(1, `${label}/run.json: schema ${JSON.stringify(run.schema)} != ${SCHEMA}`);
    const listed = new Set(["run.json"]);
    for (const [key, f] of Object.entries(run.files ?? {})) {
      if (typeof f.path !== "string" || basename(f.path) !== f.path) throw new SyncError(1, `${label}/run.json: files.${key}.path is not a plain file name`);
      listed.add(f.path);
      await verifyFile(join(dir, f.path), `${label}/${f.path}`, f.bytes, f.sha256);
      add(join(dir, f.path), `runs/${name}/${f.path}`);
    }
    for (const entry of await readdir(dir)) {
      if (!listed.has(entry)) throw new SyncError(1, `${label}/${entry}: file is not listed in run.json`);
    }
    add(runJsonPath, `runs/${name}/run.json`);
  }

  for (const seed of catalog.seeds ?? []) {
    for (const [policy, rel] of Object.entries(seed.runs ?? {})) {
      if (!(await exists(join(base, rel)))) throw new SyncError(1, `${eid}/catalog.json: seed ${seed.seed} ${policy} run path ${rel} does not exist`);
    }
  }

  const fallback = await planFallback(root, eid);
  return { eid, entry: { short, workload }, copies, fallback };
}

async function planFallback(root, eid) {
  const demoDir = join(root, "plots", "demo");
  const required = REAL_IDS.includes(eid);
  if (!(await exists(demoDir))) {
    if (required) throw new SyncError(2, `${eid}: required fallback directory not found: ${demoDir}`);
    console.log(`${eid}: no plots/demo; fallback assets skipped`);
    return null;
  }
  const invPath = join(root, "provenance", "demo_asset_inventory.json");
  if (!(await exists(invPath))) throw new SyncError(2, `${eid}: required file not found: ${invPath}`);
  const inventory = (await readJson(invPath, `${eid}/provenance/demo_asset_inventory.json`)).assets ?? {};
  const present = (await readdir(demoDir)).filter((n) => /\.(png|gif)$/i.test(n)).sort();
  if (required) {
    for (const name of DEMO_NAMES) {
      if (!present.includes(name)) throw new SyncError(2, `${eid}/plots/demo/${name}: required fallback asset not found`);
    }
  }
  const files = [];
  for (const name of present) {
    const rec = inventory[`plots/demo/${name}`];
    const label = `${eid}/plots/demo/${name}`;
    if (!rec) throw new SyncError(1, `${label}: not listed in demo_asset_inventory.json`);
    await verifyFile(join(demoDir, name), label, rec.bytes, rec.sha256);
    files.push({ src: join(demoDir, name), rel: name });
  }
  return files;
}

async function copyAll(dest, copies) {
  let bytes = 0;
  for (const { src, rel } of copies) {
    const to = join(dest, rel);
    await mkdir(dirname(to), { recursive: true });
    await copyFile(src, to);
    bytes += (await stat(to)).size;
  }
  return { files: copies.length, bytes };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const plans = [];
  for (const eid of opts.experiments) plans.push(await planExperiment(opts.source, eid));

  const replayDir = join(opts.out, "replay");
  const fallbackDir = join(opts.out, "fallback");
  for (const p of plans) {
    await rm(join(replayDir, p.eid), { recursive: true, force: true });
    const t = await copyAll(join(replayDir, p.eid), p.copies);
    console.log(`${p.eid}: replay_v1 ${t.files} files, ${fmtBytes(t.bytes)}`);
    if (p.fallback) {
      await rm(join(fallbackDir, p.eid), { recursive: true, force: true });
      const f = await copyAll(join(fallbackDir, p.eid), p.fallback);
      console.log(`${p.eid}: fallback ${f.files} files, ${fmtBytes(f.bytes)}`);
    }
  }

  const index = {
    schema: SCHEMA,
    experiments: plans.map((p, i) => {
      const e = {
        id: p.eid,
        short: p.entry.short,
        label: `${p.entry.short} — ${p.entry.workload} workload`,
        catalog: `${p.eid}/catalog.json`,
      };
      if (i === 0) e.default = true;
      return e;
    }),
  };
  await mkdir(replayDir, { recursive: true });
  await writeFile(join(replayDir, "index.json"), JSON.stringify(index, null, 2) + "\n");
  console.log(`index.json: ${index.experiments.map((e) => e.id).join(", ")} (default ${index.experiments[0].id})`);
}

main().catch((e) => {
  if (e instanceof SyncError) {
    console.error(`sync-replay: ${e.message}`);
    process.exit(e.code);
  }
  console.error(e);
  process.exit(1);
});
