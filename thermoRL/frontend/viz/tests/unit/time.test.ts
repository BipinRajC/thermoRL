import { expect, test } from "vitest";
import { buildFixture } from "../fixture/buildFixture";
import type { Catalog } from "../../src/schema/replay";
import { formatClock, pulseBounds, tickToTs, tsToTick, windowLabel, windowState } from "../../src/model/time";

const cat = JSON.parse(new TextDecoder().decode((await buildFixture()).get("EFIX/catalog.json")!)) as Catalog;
const N = 2160;

test("windowState boundaries", () => {
  expect(windowState(3600, cat)).toBe("before");
  expect(windowState(3610, cat)).toBe("evaluation");
  expect(windowState(21600, cat)).toBe("evaluation");
});

test("windowLabel strings", () => {
  expect(windowLabel(3600, cat)).toBe("before evaluation window (t ≤ 1 h)");
  expect(windowLabel(3610, cat)).toBe("evaluation window (1 h < t ≤ 6 h)");
});

test("tick <-> t_s", () => {
  expect(tickToTs(0)).toBe(10);
  expect(tickToTs(2159)).toBe(21600);
  expect(tsToTick(10, N)).toBe(0);
  expect(tsToTick(3610, N)).toBe(360);
  expect(tsToTick(-5, N)).toBe(0);
  expect(tsToTick(99999, N)).toBe(N - 1);
  expect(tsToTick(3619, N)).toBe(360);
  expect(tsToTick(3615.5, N)).toBe(360);
});

test("formatClock", () => {
  expect(formatClock(3610)).toBe("01:00:10");
  expect(formatClock(10)).toBe("00:00:10");
  expect(formatClock(21600)).toBe("06:00:00");
});

test("pulseBounds", () => {
  expect(pulseBounds(10, cat)).toEqual([-1, 10]);
  expect(pulseBounds(3610, cat)).toEqual([3580, 3610]);
});
