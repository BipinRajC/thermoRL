import { beforeAll, expect, test } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import { loadFixtureRun } from "../fixture/loadFixtureRun";
import { lutToRgb, scaleFor } from "../../src/model/colour";
import { LEGEND_NOTE } from "../../src/ui/copy";
import { renderLegend } from "../../src/ui/legend";

let cat: Catalog;
let lut: Float32Array;
beforeAll(async () => {
  ({ cat } = await loadFixtureRun());
  lut = lutToRgb(cat.colormap.lut);
});

const mount = () => document.createElement("div");

test("legend prints min and max to 2 decimals, the unit label and the fixed-scale note", () => {
  const el = mount();
  const scale = { ...scaleFor("tc", cat, 1), min: 40, max: 40.5 };
  renderLegend(el, scale, lut, { below: 0, above: 0 });
  expect(el.textContent).toContain("40.00");
  expect(el.textContent).toContain("40.50");
  expect(el.textContent).toContain("Modelled coolant °C");
  expect(el.textContent).toContain("Scale fixed per experiment and seed; E11 and E12 scales differ");
  expect(LEGEND_NOTE).toBe("Scale fixed per experiment and seed; E11 and E12 scales differ");
  expect(el.textContent).not.toContain("outside scale");
});

test("legend counts out-of-range racks, singular and plural, below plus above", () => {
  const el = mount();
  const scale = scaleFor("tc", cat, 1);
  renderLegend(el, scale, lut, { below: 0, above: 2 });
  expect(el.textContent).toContain("2 racks outside scale this frame");
  renderLegend(el, scale, lut, { below: 1, above: 0 });
  expect(el.textContent).toContain("1 rack outside scale this frame");
  expect(el.textContent).not.toContain("1 racks");
  renderLegend(el, scale, lut, { below: 3, above: 2 });
  expect(el.textContent).toContain("5 racks outside scale this frame");
  renderLegend(el, scale, lut, { below: 0, above: 0 });
  expect(el.textContent).not.toContain("outside scale");
});

test("legend leaves the DOM alone when nothing changed and rebuilds when the scale does", () => {
  const el = mount();
  const scale = scaleFor("tc", cat, 1);
  renderLegend(el, scale, lut, { below: 0, above: 2 });
  const first = el.firstElementChild;
  renderLegend(el, { ...scale }, lut, { below: 0, above: 2 });
  expect(el.firstElementChild).toBe(first);
  renderLegend(el, { ...scale, max: 99 }, lut, { below: 0, above: 2 });
  expect(el.firstElementChild).not.toBe(first);
  expect(el.textContent).toContain("99.00");
});
