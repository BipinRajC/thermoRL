import { beforeAll, expect, test } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import type { LoadedRun } from "../../src/data/loader";
import { fixtureKw, fixtureFree, fixtureTc } from "../fixture/buildFixture";
import { loadFixtureRun } from "../fixture/loadFixtureRun";
import {
  candidatesFor,
  decisionAt,
  decisionsIn,
  rackFree,
  rackKw,
  rackTc,
  startRacksIn,
  tickValue,
} from "../../src/data/views";

let run: LoadedRun;
let cat: Catalog;
beforeAll(async () => {
  ({ run, cat } = await loadFixtureRun());
});

test("rack and tick accessors", () => {
  expect(rackTc(run, 7, 4)).toBe(Math.fround(fixtureTc("packing", 7, 4)));
  expect(rackKw(run, 7, 4)).toBe(fixtureKw(7, 4));
  expect(rackFree(run, 7, 4)).toBe(fixtureFree(7, 4));
  expect(tickValue(run, 0, "t_s")).toBe(10);
  expect(tickValue(run, 5, "t_s")).toBe(60);
  expect(tickValue(run, 5, "argmax_rack")).toBe(10);
  expect(tickValue(run, 5, "pump_kw_sum")).toBeCloseTo(0.3 * 11, 12);
});

test("startRacksIn uses (lo, hi] and counts only starts", () => {
  expect([...startRacksIn(run, -1, 30)].sort()).toEqual([2, 3]);
  expect(startRacksIn(run, 25, 55).has(2)).toBe(false);
  expect(startRacksIn(run, 25, 55).has(3)).toBe(false);
  expect(startRacksIn(run, 24, 25)).toEqual(new Set([2, 3]));
  expect(startRacksIn(run, 1170, 1200).size).toBe(0);
  expect(startRacksIn(run, 25, 25).size).toBe(0);
});

test("completes are not start events", () => {
  const completes: number[] = [];
  run.events.kind.forEach((kind, i) => kind === 1 && completes.push(run.events.raps_t_s[i]));
  const t = completes[0];
  const starts = new Set<number>();
  run.events.kind.forEach((kind, i) => {
    if (kind === 0 && run.events.raps_t_s[i] === t) {
      for (let j = run.events.rack_offsets[i]; j < run.events.rack_offsets[i + 1]; j++) starts.add(run.events.racks[j]);
    }
  });
  expect(startRacksIn(run, t - 1, t)).toEqual(starts);
});

test("decisionsIn", () => {
  expect(decisionsIn(run, 3580, 3610)).toHaveLength(120);
  expect(decisionsIn(run, 1170, 1200)).toEqual([]);
  expect(decisionsIn(run, -1, 30)).toEqual([0]);
  const all = decisionsIn(run, -1, 1e9);
  expect(all).toHaveLength(run.meta.n_decisions);
  expect(all[0]).toBe(0);
  expect(all[all.length - 1]).toBe(run.meta.n_decisions - 1);
  const burst = decisionsIn(run, 3580, 3610);
  expect(burst).toEqual(Array.from({ length: burst.length }, (_, j) => burst[0] + j));
});

test("decisionAt", () => {
  const span = decisionAt(run, 0);
  expect(span).toMatchObject({ index: 0, rapsTs: 25, rule: "span", nodes: 24, chosen: [2, 3], chosenIsBest: expect.any(Boolean) });
  expect(span.jobKw).toBe(12);
  const single = decisionAt(run, 1);
  expect(single.rule).toBe("single");
  expect(single.chosen).toHaveLength(1);
  const tied = decisionAt(run, 2);
  expect(tied).toMatchObject({ rapsTs: 85, nTies: 3, chosenIsBest: false, chosen: [7] });
});

test("candidatesFor single-rack decision", () => {
  const rows = candidatesFor(run, 1);
  expect(rows.length).toBeLessThanOrEqual(6);
  for (let j = 1; j < Math.min(5, rows.length); j++) expect(rows[j - 1].score).toBeGreaterThanOrEqual(rows[j].score);
  expect(rows.filter((r) => r.chosen)).toHaveLength(1);
  expect(rows.every((r) => r.rack !== 65535 && Number.isFinite(r.score) && Number.isFinite(r.tc))).toBe(true);
  expect(rows[0].chosen).toBe(true);
  expect(rows[0].committedKw).toBeGreaterThan(0);
});

test("candidatesFor span decision has two chosen racks", () => {
  const rows = candidatesFor(run, 0);
  expect(rows.filter((r) => r.chosen).map((r) => r.rack)).toEqual([2, 3]);
  expect(decisionAt(run, 0).chosen).toEqual([2, 3]);
});

test("non-best decision: chosen rack appears in row 5 and ties are reported", () => {
  const rows = candidatesFor(run, 2);
  expect(rows).toHaveLength(6);
  expect(rows[5].rack).toBe(7);
  expect(rows[5].chosen).toBe(true);
  expect(rows.slice(0, 5).some((r) => r.chosen)).toBe(false);
  expect(new Set(rows.slice(0, 3).map((r) => r.rack))).toEqual(new Set([4, 5, 6]));
  expect(rows.slice(0, 3).every((r) => r.score === rows[0].score)).toBe(true);
  expect(cat.grid.n_racks).toBe(11);
});
