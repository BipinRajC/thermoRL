import { beforeAll, expect, test, vi } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import type { LoadedRun } from "../../src/data/loader";
import { candidatesFor, decisionAt, decisionsIn } from "../../src/data/views";
import { pulseBounds, tickToTs } from "../../src/model/time";
import { COPY } from "../../src/ui/copy";
import { renderWhy } from "../../src/ui/whyDrawer";
import { loadFixtureRun } from "../fixture/loadFixtureRun";

const PRECISION = "SENTINEL-PRECISION <b>raw</b> ≈ 94.8 %";
let run: LoadedRun;
let cat: Catalog;
beforeAll(async () => {
  ({ run, cat } = await loadFixtureRun());
  cat.strings = { ...cat.strings, precision_note: PRECISION };
});

const render = (t_s: number, page = 0, c: Catalog = cat, handlers?: Parameters<typeof renderWhy>[6]) => {
  const el = document.createElement("div");
  renderWhy(el, run, "left", t_s, c, page, handlers);
  return el;
};
const items = (el: HTMLElement) => Array.from(el.querySelectorAll<HTMLElement>(".why-item"));
const button = (el: HTMLElement, text: string) =>
  Array.from(el.querySelectorAll("button")).find((b) => b.textContent === text) as HTMLButtonElement;
const expand = (item: HTMLElement) => item.querySelector<HTMLButtonElement>(".why-item-head")!.click();
const itemFor = (el: HTMLElement, jobId: number) => items(el).find((i) => i.dataset.jobId === String(jobId))!;

test("an empty window shows the empty text and still the precision note", () => {
  const el = render(tickToTs(119));
  expect(el.querySelector(".why-empty")?.textContent).toBe("No job starts in this 30 s window.");
  expect(items(el)).toHaveLength(0);
  expect(el.querySelector(".why-precision")?.textContent).toBe(PRECISION);
  expect(el.querySelector(".why-count")?.textContent).toBe("0 decisions");
  expect(el.querySelector("table")).toBeNull();
});

test("the window length comes from the catalog", () => {
  const cat60: Catalog = { ...cat, time: { ...cat.time, pulse_window_s: 60 } };
  const el = render(90, 0, cat60);
  expect(el.querySelector(".why-header")?.textContent).toBe("Job starts in the 60 s ending at 00:01:30 — packing (seed 1)");
  expect(items(el)).toHaveLength(decisionsIn(run, ...pulseBounds(90, cat60)).length);
  expect(items(el).length).toBeGreaterThan(render(90).querySelectorAll(".why-item").length);
  expect(render(tickToTs(119), 0, cat60).querySelector(".why-empty")?.textContent).toBe("No job starts in this 60 s window.");
});

test("the header names the window end, policy and seed, and the count is shown", () => {
  const el = render(tickToTs(360));
  expect(el.querySelector(".why-header")?.textContent).toBe("Job starts in the 30 s ending at 01:00:10 — packing (seed 1)");
  expect(el.querySelector(".why-count")?.textContent).toBe("120 decisions");
});

test("the burst shows 50 items on page 0 with Next enabled and Prev disabled", () => {
  const el = render(tickToTs(360));
  expect(items(el)).toHaveLength(50);
  expect(button(el, "Next").disabled).toBe(false);
  expect(button(el, "Prev").disabled).toBe(true);
  expect(el.querySelector("table")).toBeNull();
});

test("page 2 shows the last 20 with Next disabled; out-of-range pages clamp", () => {
  const el = render(tickToTs(360), 2);
  expect(items(el)).toHaveLength(20);
  expect(button(el, "Next").disabled).toBe(true);
  expect(button(el, "Prev").disabled).toBe(false);
  expect(items(render(tickToTs(360), 99))).toHaveLength(20);
  expect(items(render(tickToTs(360), -4))).toHaveLength(50);
  const all = decisionsIn(run, ...pulseBounds(tickToTs(360), cat));
  const first = items(render(tickToTs(360), 1))[0];
  expect(first.dataset.jobId).toBe(String(decisionAt(run, all[50]).jobId));
});

test("Next and Prev page in place and report the page", () => {
  const onPage = vi.fn();
  const el = render(tickToTs(360), 0, cat, { onPage });
  button(el, "Next").click();
  expect(onPage).toHaveBeenLastCalledWith(1);
  expect(items(el)).toHaveLength(50);
  button(el, "Next").click();
  expect(items(el)).toHaveLength(20);
  expect(button(el, "Next").disabled).toBe(true);
  button(el, "Prev").click();
  expect(onPage).toHaveBeenLastCalledWith(1);
  expect(items(el)).toHaveLength(50);
});

test("each item shows job id, nodes, rule, chosen racks, logged-at time and RAPS start second", () => {
  const el = render(30);
  const span = itemFor(el, 0);
  const d = decisionAt(run, 0);
  expect(d.rule).toBe("span");
  expect(span.querySelector(".why-job")?.textContent).toBe(`Job ${d.jobId}`);
  expect(span.querySelector(".why-nodes")?.textContent).toBe(`${d.nodes} nodes`);
  expect(span.querySelector(".why-rule")?.textContent).toBe("span");
  expect(span.querySelector(".why-racks")?.textContent).toBe("racks 2, 3");
  expect(span.querySelector(".why-obs")?.textContent).toBe(`logged at ${d.tObs} s`);
  expect(span.querySelector(".why-raps")?.textContent).toBe(`RAPS start ${d.rapsTs} s`);
});

test("expanding shows at most 6 rows, highlights exactly the chosen racks, and collapses again", () => {
  const el = render(30);
  const span = itemFor(el, 0);
  expect(span.querySelector("table")).toBeNull();
  expand(span);
  const rows = Array.from(span.querySelectorAll("tbody tr"));
  const recorded = candidatesFor(run, 0);
  expect(rows.length).toBeLessThanOrEqual(6);
  expect(rows.map((r) => r.querySelector("td")?.textContent)).toEqual(recorded.map((c) => String(c.rack)));
  const chosen = new Set(decisionAt(run, 0).chosen);
  const highlighted = rows.filter((r) => r.classList.contains("is-chosen")).map((r) => Number(r.querySelector("td")!.textContent));
  expect(highlighted).toEqual(recorded.filter((c) => chosen.has(c.rack)).map((c) => c.rack));
  expect(highlighted.sort()).toEqual([2, 3]);
  const heads = Array.from(span.querySelectorAll("thead th")).map((h) => h.textContent);
  expect(heads).toEqual(["Rack", "Logged score", "Modelled coolant °C", "Committed kW", "Free"]);
  expect((rows[0].querySelectorAll("td")[1].textContent ?? "")).toBe(recorded[0].score.toFixed(6));
  expand(span);
  expect(span.querySelector("table")).toBeNull();
});

test("ties are shown, and the full-precision note appears only when the chosen rack is not the top logged score", () => {
  const el = render(90, 0, { ...cat, time: { ...cat.time, pulse_window_s: 60 } });
  const tied = items(el).find((i) => decisionAt(run, Number(i.dataset.decisionIndex)).chosenIsBest === false)!;
  const d = decisionAt(run, Number(tied.dataset.decisionIndex));
  expect(d.nTies).toBe(3);
  expand(tied);
  expect(tied.querySelector(".why-ties")?.textContent).toBe("Ties at logged precision: 3");
  expect(tied.querySelector(".why-note")?.textContent).toBe(
    "Chosen rack is not the top logged score — the live decision used full precision.",
  );
  const clean = items(el).find((i) => decisionAt(run, Number(i.dataset.decisionIndex)).chosenIsBest)!;
  expand(clean);
  expect(clean.querySelector(".why-ties")?.textContent).toBe("Ties at logged precision: 1");
  expect(clean.querySelector(".why-note")).toBeNull();
});

test("a chosen rack outside the six records is not invented", () => {
  const el = render(30);
  const span = itemFor(el, 0);
  expand(span);
  const racks = Array.from(span.querySelectorAll("tbody tr")).map((r) => Number(r.querySelector("td")!.textContent));
  expect(new Set(racks).size).toBe(racks.length);
  expect(racks).toEqual(candidatesFor(run, 0).map((c) => c.rack));
});

test("the precision note is always the first block, verbatim, and bundle text is not parsed as HTML", () => {
  for (const t of [tickToTs(119), tickToTs(360), 30]) {
    const el = render(t);
    expect(el.querySelector(".why-precision")?.textContent).toBe(PRECISION);
    expect(el.firstElementChild?.classList.contains("why-precision")).toBe(true);
    expect(el.querySelector("b")).toBeNull();
  }
});

test("the side toggle marks the current side and reports changes", () => {
  const onSide = vi.fn();
  const el = document.createElement("div");
  renderWhy(el, run, "right", 30, cat, 0, { onSide });
  const [left, right] = Array.from(el.querySelectorAll<HTMLButtonElement>(".why-side button"));
  expect(left.getAttribute("aria-pressed")).toBe("false");
  expect(right.getAttribute("aria-pressed")).toBe("true");
  left.click();
  expect(onSide).toHaveBeenCalledWith("left");
});

test("expanding reports through onExpand, and re-rendering replaces the content", () => {
  const onExpand = vi.fn();
  const el = render(30, 0, cat, { onExpand });
  expand(itemFor(el, 0));
  expect(onExpand).toHaveBeenLastCalledWith(0);
  renderWhy(el, run, "left", 30, cat);
  expect(el.querySelectorAll(".why-precision")).toHaveLength(1);
  expect(el.querySelector("table")).toBeNull();
});

test("no ranking wording or other-policy choices are rendered", () => {
  const text = render(tickToTs(360)).textContent ?? "";
  expect(text).not.toMatch(/winner|significan|power_balance|thermal_predictive/i);
});
