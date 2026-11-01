import { beforeAll, expect, test } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import type { LoadedRun } from "../../src/data/loader";
import { fixtureFree, fixtureKw } from "../fixture/buildFixture";
import { loadFixtureRun } from "../fixture/loadFixtureRun";
import { frameColours, lutToRgb, mapValue, scaleFor, type Scale } from "../../src/model/colour";

let run: LoadedRun;
let cat: Catalog;
let lut: Float32Array;
beforeAll(async () => {
  ({ run } = await loadFixtureRun("thermal_predictive", 1));
  ({ cat } = await loadFixtureRun());
  lut = lutToRgb(cat.colormap.lut);
});

const scale: Scale = { min: 10, max: 20, unit: "u", label: "l" };
const lutAt = (i: number) => [lut[i * 3], lut[i * 3 + 1], lut[i * 3 + 2]];
const outAt = (o: Float32Array, off = 0) => [o[off], o[off + 1], o[off + 2]];

test("lutToRgb gives 256 RGB triples in 0..1", () => {
  expect(lut.length).toBe(256 * 3);
  expect(lutAt(0)).toEqual([0, 0, 1].map(Math.fround));
  expect(lutAt(255)[0]).toBeCloseTo(1, 6);
  expect(lutAt(255)[2]).toBeCloseTo(0, 6);
  expect(Math.max(...lut)).toBeLessThanOrEqual(1);
  expect(Math.min(...lut)).toBeGreaterThanOrEqual(0);
  expect(() => lutToRgb(["#000000"])).toThrow();
});

test("mapValue endpoints and midpoint", () => {
  const out = new Float32Array(6);
  expect(mapValue(10, scale, lut, out, 0)).toBe(0);
  expect(outAt(out)).toEqual(lutAt(0));
  expect(mapValue(20, scale, lut, out, 3)).toBe(0);
  expect(outAt(out, 3)).toEqual(lutAt(255));
  expect(mapValue(15, scale, lut, out, 0)).toBe(0);
  const mid = outAt(out);
  expect([lutAt(127), lutAt(128)]).toContainEqual(mid);
});

test("mapValue clamps below and above the scale and reports it", () => {
  const out = new Float32Array(3);
  expect(mapValue(9.999, scale, lut, out, 0)).toBe(-1);
  expect(outAt(out)).toEqual(lutAt(0));
  expect(mapValue(20.001, scale, lut, out, 0)).toBe(1);
  expect(outAt(out)).toEqual(lutAt(255));
});

test("mapValue never reads NaN as in range", () => {
  const out = new Float32Array(3);
  expect(mapValue(NaN, scale, lut, out, 0)).toBe(-1);
  expect(outAt(out)).toEqual(lutAt(0));
});

test("frameColours counts racks above the seed-1 scale (exactly 2 at tick 5)", () => {
  const s = scaleFor("tc", cat, 1);
  const n = run.meta.n_racks;
  const out = new Float32Array(n * 3);
  expect(frameColours(run, 5, "tc", s, lut, out)).toEqual({ below: 0, above: 2 });
  expect(outAt(out, (n - 1) * 3)).toEqual(lutAt(255));
  expect(outAt(out, (n - 2) * 3)).toEqual(lutAt(255));
  expect(outAt(out, 0)).not.toEqual(lutAt(255));
});

test("frameColours counts racks below the scale", () => {
  const s = { ...scaleFor("tc", cat, 1), min: 40.5 };
  const out = new Float32Array(run.meta.n_racks * 3);
  const { below } = frameColours(run, 5, "tc", s, lut, out);
  expect(below).toBeGreaterThan(0);
  expect(outAt(out, 0)).toEqual(lutAt(0));
});

test("scaleFor tc uses the requested seed's range", () => {
  const s1 = scaleFor("tc", cat, 1);
  const s2 = scaleFor("tc", cat, 2);
  expect(s1.max).toBe(cat.seeds[0].colour_scale_c.max);
  expect(s2).toMatchObject({ min: 39.5, max: 42.5, unit: "°C", label: "Modelled coolant °C" });
  expect(s2.max).not.toBe(s1.max);
  expect(() => scaleFor("tc", cat, 99)).toThrow();
});

test("scaleFor kw uses the catalog power range", () => {
  expect(scaleFor("kw", cat, 1)).toEqual({
    min: cat.rack_kw_range.idle_kw,
    max: cat.rack_kw_range.peak_kw,
    unit: "kW",
    label: "Rack power kW (RAPS input over the interval ending at t)",
  });
});

test("occupied scale is 0..nodes_per_rack and the value is nodes_per_rack − free", () => {
  const s = scaleFor("occupied", cat, 1);
  expect(s).toEqual({ min: 0, max: 18, unit: "nodes", label: "Occupied nodes (18 − free)" });
  const n = run.meta.n_racks;
  const out = new Float32Array(n * 3);
  const k = 4;
  expect(frameColours(run, k, "occupied", s, lut, out)).toEqual({ below: 0, above: 0 });
  for (const r of [0, 1, 7]) {
    const idx = Math.round(((18 - fixtureFree(k, r)) / 18) * 255);
    expect(outAt(out, r * 3)).toEqual(lutAt(idx));
  }
});

test("frameColours for kw reads the recorded rack power", () => {
  const s = scaleFor("kw", cat, 1);
  const out = new Float32Array(run.meta.n_racks * 3);
  frameColours(run, 3, "kw", s, lut, out);
  const v = fixtureKw(3, 2);
  const idx = Math.round(((v - s.min) / (s.max - s.min)) * 255);
  expect(outAt(out, 6)).toEqual(lutAt(Math.max(0, Math.min(255, idx))));
});
