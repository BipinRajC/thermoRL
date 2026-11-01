import { beforeAll, expect, test, vi } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import type { LoadedRun } from "../../src/data/loader";
import { loadFixtureRun } from "../fixture/loadFixtureRun";
import { Timeline, shadeEndX } from "../../src/ui/timeline";

let run: LoadedRun;
let cat: Catalog;
beforeAll(async () => {
  ({ run, cat } = await loadFixtureRun("thermal_predictive", 1));
});

const N = 2160;

test("xToTick maps the ends to 0 and nTicks-1 and clamps outside", () => {
  expect(Timeline.xToTick(0, 800, N)).toBe(0);
  expect(Timeline.xToTick(800, 800, N)).toBe(N - 1);
  expect(Timeline.xToTick(-50, 800, N)).toBe(0);
  expect(Timeline.xToTick(900, 800, N)).toBe(N - 1);
});

test("xToTick is monotonic and inverts tickToX within one tick", () => {
  let prev = -1;
  for (let x = 0; x <= 800; x += 0.5) {
    const k = Timeline.xToTick(x, 800, N);
    expect(k).toBeGreaterThanOrEqual(prev);
    prev = k;
  }
  for (const k of [0, 1, 359, 360, 1000, N - 2, N - 1]) {
    const x = Timeline.tickToX(k, 800, N);
    expect(Math.abs(Timeline.xToTick(x, 800, N) - k)).toBeLessThanOrEqual(1);
  }
  expect(Timeline.tickToX(0, 800, N)).toBe(0);
  expect(Timeline.tickToX(N - 1, 800, N)).toBe(800);
});

test("degenerate widths and tick counts do not produce NaN", () => {
  expect(Timeline.xToTick(10, 0, N)).toBe(0);
  expect(Timeline.xToTick(10, 800, 1)).toBe(0);
  expect(Timeline.tickToX(0, 800, 1)).toBe(0);
});

test("the shaded region ends at tick 359 (t_s 3600), derived from the catalog", () => {
  const width = 900;
  expect(shadeEndX(cat, width)).toBe(Timeline.tickToX(359, width, cat.time.n_ticks));
  const moved = { ...cat, time: { ...cat.time, eval_start_exclusive_s: 1000 } };
  expect(shadeEndX(moved, width)).toBe(Timeline.tickToX(99, width, cat.time.n_ticks));
});

test("a Timeline without a 2D context still accepts runs, cursors and seek handlers", () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const canvas = document.createElement("canvas");
  const t = new Timeline(canvas, cat);
  let seeked = -1;
  t.onSeek((k) => (seeked = k));
  expect(() => {
    t.setRuns(run, run, ["thermal_predictive", "thermal_predictive"]);
    t.setCursor(5);
  }).not.toThrow();
  expect(seeked).toBe(-1);
  t.dispose();
});
