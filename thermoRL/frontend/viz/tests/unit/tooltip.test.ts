import { beforeAll, expect, test } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import type { LoadedRun } from "../../src/data/loader";
import { fixtureFree, fixtureKw, fixtureTc } from "../fixture/buildFixture";
import { loadFixtureRun } from "../fixture/loadFixtureRun";
import { scaleFor, type Scale } from "../../src/model/colour";
import { rackTitle, tooltipHtml } from "../../src/ui/tooltip";

let run: LoadedRun;
let cat: Catalog;
beforeAll(async () => {
  ({ run, cat } = await loadFixtureRun("thermal_predictive", 1));
});

const LAST = 10;

test("rackTitle gives the rack index with (row, col)", () => {
  expect(rackTitle(LAST, cat.grid)).toBe("Rack 10 (row 2, col 2)");
  expect(rackTitle(0, cat.grid)).toBe("Rack 0 (row 0, col 0)");
});

test("a value above the scale is marked outside scale and carries the catalog interval semantics", () => {
  const html = tooltipHtml(run, 5, LAST, scaleFor("tc", cat, 1), cat);
  expect(html).toContain("outside scale");
  expect(html).toContain("Modelled coolant");
  expect(html).toContain("interval");
  expect(html).toContain(cat.strings.interval_semantics);
  expect(html).toContain("Rack 10 (row 2, col 2)");
});

test("an in-scale rack has no outside-scale marker", () => {
  const html = tooltipHtml(run, 5, 0, scaleFor("tc", cat, 1), cat);
  expect(html).not.toContain("outside scale");
});

test("all three values are always shown with the specified precision", () => {
  const html = tooltipHtml(run, 5, 3, scaleFor("tc", cat, 1), cat);
  expect(html).toContain(`Modelled coolant ${fixtureTc("thermal_predictive", 5, 3).toFixed(2)} °C`);
  expect(html).toContain(`Rack power ${fixtureKw(5, 3).toFixed(1)} kW`);
  expect(html).toContain(`Free nodes ${fixtureFree(5, 3)} / ${cat.grid.nodes_per_rack}`);
});

test("the marker follows the active overlay, not the coolant value", () => {
  const kwNarrow: Scale = { ...scaleFor("kw", cat, 1), max: 15 };
  const kw = fixtureKw(5, 3);
  expect(kw).toBeGreaterThan(15);
  expect(tooltipHtml(run, 5, 3, kwNarrow, cat)).toContain("outside scale");
  expect(tooltipHtml(run, 5, 3, scaleFor("kw", cat, 1), cat)).not.toContain("outside scale");
  const tcWide: Scale = { ...scaleFor("tc", cat, 1), max: 100 };
  expect(tooltipHtml(run, 5, LAST, tcWide, cat)).not.toContain("outside scale");
});

test("a value inside the float32 slack is not outside scale", () => {
  const edge = Math.fround(fixtureTc("thermal_predictive", 5, LAST));
  const s: Scale = { ...scaleFor("tc", cat, 1), max: edge - 1e-6 };
  expect(tooltipHtml(run, 5, LAST, s, cat)).not.toContain("outside scale");
});

test("catalog text is escaped before it is placed in HTML", () => {
  const hostile = { ...cat, strings: { ...cat.strings, interval_semantics: "<img src=x onerror=1> & more" } };
  const html = tooltipHtml(run, 5, 0, scaleFor("tc", cat, 1), hostile);
  expect(html).not.toContain("<img");
  expect(html).toContain("&lt;img src=x onerror=1&gt; &amp; more");
});
