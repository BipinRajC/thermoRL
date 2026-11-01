import { createHash } from "node:crypto";
import { expect, test } from "vitest";
import { buildFixture } from "../fixture/buildFixture";

const dec = (b: Uint8Array) => new TextDecoder().decode(b);
const sha256Hex = async (b: Uint8Array) => createHash("sha256").update(b).digest("hex");

test("fixture is a complete, hash-correct replay_v1 tree", async () => {
  const files = await buildFixture();
  const index = JSON.parse(dec(files.get("index.json")!));
  expect(index.schema).toBe("thermorl.replay.v1");
  const cat = JSON.parse(dec(files.get("EFIX/catalog.json")!));
  expect(cat.grid).toMatchObject({ rows: 3, cols: 4, n_racks: 11 });
  expect(cat.colormap.lut).toHaveLength(256);
  const run = JSON.parse(dec(files.get("EFIX/runs/power_balance_seed1/run.json")!));
  for (const f of Object.values(run.files) as any[]) {
    const bytes = files.get(`EFIX/runs/power_balance_seed1/${f.path}`)!;
    expect(bytes.byteLength).toBe(f.bytes);
    expect(await sha256Hex(bytes)).toBe(f.sha256);
  }
});

const load = (files: Map<string, Uint8Array>, path: string) => JSON.parse(dec(files.get(path)!));

test("fixture honours the required contract specifics", async () => {
  const files = await buildFixture();
  const cat = load(files, "EFIX/catalog.json");
  const base = "EFIX/runs/thermal_predictive_seed1";
  const run = load(files, `${base}/run.json`);
  const dcs = load(files, `${base}/decisions.json`);
  const evs = load(files, `${base}/events.json`);
  const t: number[] = dcs.raps_t_s;

  expect(t.filter((x) => x > 3580 && x <= 3610)).toHaveLength(120);
  expect(t.filter((x) => x > 1170 && x <= 1200)).toHaveLength(0);
  expect([...t].sort((a, b) => a - b)).toEqual(t);

  const i25 = t.indexOf(25);
  expect(dcs.rule[i25]).toBe("span");
  expect(dcs.chosen_racks.slice(dcs.chosen_offsets[i25], dcs.chosen_offsets[i25 + 1])).toEqual([2, 3]);
  const iStart = evs.raps_t_s.indexOf(25);
  expect(evs.kind[iStart]).toBe(0);
  expect(evs.racks.slice(evs.rack_offsets[iStart], evs.rack_offsets[iStart + 1])).toEqual([2, 3]);

  const notBest = (dcs.chosen_is_logged_best as boolean[]).flatMap((b, i) => (b ? [] : [i]));
  expect(notBest).toHaveLength(1);
  expect(dcs.n_ties_at_logged_best[notBest[0]]).toBe(3);
  expect(dcs.chosen_offsets).toHaveLength(run.n_decisions + 1);
  expect(evs.rack_offsets).toHaveLength(run.n_events + 1);

  const tc = new Float32Array(files.get(`${base}/rack_tc.f32`)!.slice().buffer);
  const row5 = Array.from(tc.slice(5 * 11, 6 * 11));
  expect(row5.filter((v) => v > cat.seeds[0].colour_scale_c.max)).toHaveLength(2);
  expect(cat.seeds[1].colour_scale_c).not.toEqual(cat.seeds[0].colour_scale_c);

  const cand = files.get(`${base}/candidates.bin`)!;
  expect(cand.byteLength).toBe(run.n_decisions * 6 * 15);
  const dv = new DataView(cand.buffer, cand.byteOffset, cand.byteLength);
  expect(dv.getUint16(i25 * 90 + 5 * 15, true)).toBe(65535);
  expect(dv.getFloat32(i25 * 90 + 5 * 15 + 2, true)).toBeNaN();
  expect(dv.getUint8(i25 * 90 + 5 * 15 + 14)).toBe(0);
  expect(dv.getUint16(notBest[0] * 90 + 5 * 15, true)).toBe(7);

  const status = (p: string, s: number) =>
    load(files, `EFIX/runs/${p}_seed${s}/run.json`).c_prime_status;
  expect(status("thermal_predictive", 1)).toBe("verified_E12");
  expect(status("thermal_predictive", 2)).toBe("inherited_not_remeasured");
  expect(status("power_balance", 1)).toBe("inherited_not_remeasured");
  expect([...files.keys()].filter((k) => k.endsWith("run.json"))).toHaveLength(6);
});

test("corrupt option changes bytes without changing the recorded hash", async () => {
  const path = "EFIX/runs/packing_seed1/rack_tc.f32";
  const bad = await buildFixture({ corrupt: { file: path } });
  const run = load(bad, "EFIX/runs/packing_seed1/run.json");
  const bytes = bad.get(path)!;
  expect(bytes.byteLength).toBe(run.files.rack_tc.bytes);
  expect(await sha256Hex(bytes)).not.toBe(run.files.rack_tc.sha256);
});

test("fixture exact values and sentinel strings that later tasks rely on", async () => {
  const files = await buildFixture();
  const cat = load(files, "EFIX/catalog.json");
  expect(cat.strings).toEqual({
    interval_semantics: "fixture interval semantics text",
    s2: "fixture s2 text",
    precision_note: "fixture precision note text",
    pulse_rule: "fixture pulse rule text",
  });
  const f64 = (p: string) => {
    const b = files.get(`EFIX/runs/${p}/tick.f64`)!;
    return new Float64Array(b.slice().buffer);
  };
  const f32 = (p: string) => new Float32Array(files.get(`EFIX/runs/${p}/rack_tc.f32`)!.slice().buffer);
  const tp = f32("thermal_predictive_seed1");
  const pb = f32("power_balance_seed1");
  for (const [k, r] of [[0, 0], [5, 9], [359, 10], [399, 3]]) {
    expect(tp[k * 11 + r]).toBeCloseTo(40 + 0.01 * k + 0.1 * r, 5);
    expect(pb[k * 11 + r]).toBeCloseTo(40 + 0.01 * k + 0.1 * r + 0.2, 5);
  }
  const ticks = ["packing", "power_balance", "thermal_predictive"].map((p) => f64(`${p}_seed1`));
  for (let k = 0; k < 400; k++) {
    for (const t of ticks) expect(t[k * 8]).toBe(10 * (k + 1));
    expect(ticks[0][k * 8 + 1]).toBe(ticks[1][k * 8 + 1]);
    expect(ticks[1][k * 8 + 1]).toBe(ticks[2][k * 8 + 1]);
  }
});

test("fixture rejects shapes it cannot honour", async () => {
  await expect(buildFixture({ nRacks: 7 })).rejects.toThrow(/nRacks/);
  await expect(buildFixture({ nTicks: 100 })).rejects.toThrow(/nTicks/);
});
