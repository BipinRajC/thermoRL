import { beforeAll, expect, test } from "vitest";
import type { Catalog, FrozenOutcome } from "../../src/schema/replay";
import { buildFixture } from "../fixture/buildFixture";
import { renderAbout } from "../../src/ui/aboutPanel";
import { COPY } from "../../src/ui/copy";
import { renderOutcome } from "../../src/ui/outcomeCard";

let cat: Catalog;
let outcome: FrozenOutcome;
beforeAll(async () => {
  const files = await buildFixture();
  const read = (p: string) => JSON.parse(new TextDecoder().decode(files.get(p)!));
  cat = read("EFIX/catalog.json");
  outcome = read("EFIX/frozen_outcome.json");
  outcome.headline = "SENTINEL-HEADLINE <b>x</b> & more";
  outcome.rule = "SENTINEL-RULE";
  outcome.experiment_statement = "SENTINEL-STATEMENT";
  outcome.reproducibility_scope = "SENTINEL-REPRO";
  cat.strings = {
    interval_semantics: "SENTINEL-INTERVAL",
    s2: "SENTINEL-S2 (≤9 s) ≈ <i>raw</i>",
    precision_note: "SENTINEL-PRECISION",
    pulse_rule: "SENTINEL-PULSE",
  };
});

const active = { seed: 2, left: "power_balance", right: "thermal_predictive" } as const;
const render = () => {
  const el = document.createElement("div");
  renderOutcome(el, outcome, cat, active);
  return el;
};

test("headline, rule, tables, statement and footer appear in that order, verbatim", () => {
  const el = render();
  const text = el.textContent ?? "";
  const order = [
    outcome.headline,
    outcome.rule,
    "Seed",
    outcome.experiment_statement,
    COPY.outcome.footer,
  ].map((s) => text.indexOf(s));
  expect(order.every((i) => i >= 0)).toBe(true);
  expect([...order].sort((a, b) => a - b)).toEqual(order);
  expect(el.querySelector(".outcome-headline")?.textContent).toBe(outcome.headline);
  expect(el.querySelector(".outcome-rule")?.textContent).toBe(outcome.rule);
  expect(el.querySelector(".outcome-statement")?.textContent).toBe(outcome.experiment_statement);
  expect(el.querySelector(".outcome-footer")?.textContent).toBe("The preregistered rule decides; this viewer is descriptive.");
  expect(el.querySelector("b")).toBeNull();
});

test("the gap table has one row per seed with 3 decimals and the full value in title", () => {
  const el = render();
  const rows = Array.from(el.querySelectorAll("table.outcome-gaps tbody tr"));
  const seeds = Object.keys(outcome.decision.per_seed);
  expect(rows).toHaveLength(seeds.length);
  seeds.forEach((s, i) => {
    const d = outcome.decision.per_seed[s];
    const cells = Array.from(rows[i].querySelectorAll("td"));
    expect(rows[i].querySelector("th")?.textContent).toBe(s);
    expect(cells[0].textContent).toBe(d.power_minus_thermal_c.toFixed(3));
    expect(cells[0].getAttribute("title")).toBe(String(d.power_minus_thermal_c));
    expect(cells[1].textContent).toBe(d.packing_minus_thermal_c.toFixed(3));
    expect(cells[1].getAttribute("title")).toBe(String(d.packing_minus_thermal_c));
  });
  expect(String(outcome.decision.per_seed["1"].power_minus_thermal_c).length).toBeGreaterThan(5);
});

test("the 0.5 requirement is noted in the power_balance gap header and not in the packing header", () => {
  const heads = Array.from(render().querySelectorAll("table.outcome-gaps thead th")).map((h) => h.textContent ?? "");
  expect(heads).toHaveLength(3);
  expect(heads[1]).toContain("power_balance − thermal_predictive");
  expect(heads[1]).toContain("≥ 0.5");
  expect(heads[2]).toContain("packing − thermal_predictive");
  expect(heads[2]).not.toContain("0.5");
  expect(heads[0]).not.toContain("0.5");
});

test("the policy table shows maxrack_mean_c for the policies in metrics order and marks the active seed and policies", () => {
  const el = render();
  const table = el.querySelector("table.outcome-metrics")!;
  const policies = [...new Set(outcome.metrics.map((m) => m.policy))];
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  expect(rows.map((r) => r.querySelector("th")?.textContent)).toEqual(policies);
  const heads = Array.from(table.querySelectorAll("thead th")).map((h) => h.textContent);
  expect(heads.slice(1)).toEqual(["seed 1", "seed 2"]);
  for (const row of rows) {
    const policy = row.querySelector("th")!.textContent!;
    const cells = Array.from(row.querySelectorAll("td"));
    [1, 2].forEach((seed, i) => {
      const m = outcome.metrics.find((x) => x.policy === policy && x.seed === seed)!;
      expect(cells[i].textContent).toBe(m.maxrack_mean_c.toFixed(3));
      expect(cells[i].getAttribute("title")).toBe(String(m.maxrack_mean_c));
    });
    expect(row.classList.contains("is-active")).toBe(policy === "power_balance" || policy === "thermal_predictive");
    expect(cells[0].classList.contains("is-active-seed")).toBe(false);
    expect(cells[1].classList.contains("is-active-seed")).toBe(true);
  }
  expect(table.querySelectorAll("thead th.is-active-seed")).toHaveLength(1);
  expect(table.querySelector("thead th.is-active-seed")?.textContent).toBe("seed 2");
});

test("no ranking or verdict wording is rendered and bundle text is not parsed as HTML", () => {
  const el = render();
  const offending = Array.from(el.querySelectorAll("*")).filter((n) => /winner|best|significan/i.test(n.textContent ?? ""));
  expect(offending).toEqual([]);
  expect(el.innerHTML).not.toContain("<b>x</b>");
  expect(el.querySelector(".outcome-headline")?.textContent).toContain("<b>x</b> & more");
});

test("re-rendering replaces the content instead of appending", () => {
  const el = render();
  renderOutcome(el, outcome, cat, { ...active, seed: 1 });
  expect(el.querySelectorAll(".outcome-headline")).toHaveLength(1);
  expect(el.querySelector("thead th.is-active-seed")?.textContent).toBe("seed 1");
});

test("renderAbout includes S2 and the other bundle strings exactly", () => {
  const el = document.createElement("div");
  renderAbout(el, cat, outcome);
  expect(el.querySelector(".about-s2")?.textContent).toBe(cat.strings.s2);
  expect(el.querySelector(".about-interval")?.textContent).toBe(cat.strings.interval_semantics);
  expect(el.querySelector(".about-pulse")?.textContent).toBe(cat.strings.pulse_rule);
  expect(el.querySelector(".about-precision")?.textContent).toBe(cat.strings.precision_note);
  expect(el.querySelector(".about-repro")?.textContent).toBe(outcome.reproducibility_scope);
  expect(el.querySelector("b, i")).toBeNull();
});

test("renderAbout lists the fixed caveats, the recorded-runs statement and the results link", () => {
  const el = document.createElement("div");
  renderAbout(el, cat, outcome);
  const items = Array.from(el.querySelectorAll("li")).map((li) => li.textContent);
  for (const b of COPY.about.bullets) expect(items).toContain(b);
  expect(COPY.about.bullets).toEqual([
    "Warm-up is capped (7200 s), not settled",
    "G1 thermal predictor parameters are a frozen heuristic",
    "Temperatures are modelled by the POWER9 cooling FMU, not measured on hardware",
    "45 °C is a reference value only",
  ]);
  expect(el.textContent).toContain(COPY.about.recorded);
  expect(COPY.about.recorded).toMatch(/recorded runs/);
  expect(COPY.about.recorded).toMatch(/no new simulation/i);
  const a = el.querySelector("a")!;
  expect(a.getAttribute("href")).toContain("feat/parasparam-demo");
  expect(a.getAttribute("href")).toContain("docs/results/2026-11-parasparam-demo-results.md");
  expect(a.rel).toContain("noopener");
});
