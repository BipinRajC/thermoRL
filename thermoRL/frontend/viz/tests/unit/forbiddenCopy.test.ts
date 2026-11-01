import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, test } from "vitest";
import { FORBIDDEN, scanText } from "../support/forbidden";

const ROOT = join(__dirname, "..", "..");

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

const SAMPLES: Record<string, string[]> = {
  PUE: ["PUE", "the pue value", "(PUE)"],
  carbon: ["carbon", "Carbon footprint"],
  "CO₂": ["CO₂", "co₂ output", "pCO₂"],
  CO2: ["CO2", "co2 emitted"],
  SLO: ["SLO", "an slo breach"],
  emergency: ["emergency", "Emergency stop"],
  "λ": ["λ", "Λ weight", "λ2"],
  "dual price(s)": ["dual price", "Dual Prices", "dual_prices", "dual-price"],
  THI: ["THI", "thi score"],
  regret: ["regret", "Regret term"],
  "counterfactual outcome": ["counterfactual outcome", "Counterfactual   Outcome"],
  "energy saving(s)": ["energy saving", "Energy Savings"],
  "cooling savings": ["cooling savings", "Cooling  Savings"],
  "removes hotspots": ["removes hotspots", "Removes Hotspots"],
  "hotspot removal": ["hotspot removal", "Hotspot  Removal"],
  winner: ["winner", "The Winner is"],
  "best policy": ["best policy", "Best  Policy"],
  "significant(ly)": ["significant", "significantly lower", "Significant"],
  "real Summit temperature": ["real Summit temperature", "Real summit Temperature"],
  "hardware temperature": ["hardware temperature", "Hardware  Temperature"],
  "safety limit": ["safety limit", "Safety Limit"],
};

const CLEAN: [string, string][] = [
  ["PUE", "pueblo, queue, opuel"],
  ["carbon", "carbonate"],
  ["SLO", "slow, slope, close"],
  ["THI", "this, think, within"],
  ["emergency", "emergent"],
  ["regret", "regrettable"],
  ["winner", "winnerless"],
  ["CO2", "CO22, ACO2"],
  ["significant(ly)", "significance"],
  ["dual price(s)", "dual pricer"],
];

describe("scanner self-test", () => {
  test("every forbidden term has samples, and every pattern is covered", () => {
    expect(Object.keys(SAMPLES).sort()).toEqual(FORBIDDEN.map((f) => f.term).sort());
  });

  for (const [term, samples] of Object.entries(SAMPLES)) {
    test(`flags ${term}`, () => {
      for (const s of samples) {
        const hits = scanText(`some text ${s} more text`);
        expect(hits.map((h) => h.term), `sample "${s}"`).toContain(term);
        expect(scanText(s).length, `bare sample "${s}"`).toBeGreaterThan(0);
      }
    });
  }

  test("flags terms in later lines with the right line number", () => {
    const hits = scanText("fine\nstill fine\nmentions a Winner here");
    expect(hits).toEqual([{ term: "winner", line: 3, text: "mentions a Winner here" }]);
  });

  test("does not flag look-alike words", () => {
    for (const [, text] of CLEAN) expect(scanText(text), text).toEqual([]);
  });

  test("the unavailable_fields identifier is the only allowed exception", () => {
    expect(scanText("catalog.unavailable_fields")).toEqual([]);
    expect(scanText("const unavailable_fields = []; PUE").map((h) => h.term)).toEqual(["PUE"]);
  });
});

describe("shipped copy", () => {
  const files = [...walk(join(ROOT, "src")), join(ROOT, "index.html")];

  test("the scan covers the app sources", () => {
    const rel = files.map((f) => relative(ROOT, f));
    expect(rel).toContain("index.html");
    expect(rel).toContain(join("src", "main.ts"));
    expect(rel).toContain(join("src", "ui", "copy.ts"));
    expect(rel).toContain(join("src", "style.css"));
  });

  test("no forbidden wording anywhere under src/ or in index.html", () => {
    const found = files.flatMap((f) =>
      scanText(readFileSync(f, "utf8")).map((h) => `${relative(ROOT, f)}:${h.line} [${h.term}] ${h.text}`),
    );
    expect(found).toEqual([]);
  });
});
