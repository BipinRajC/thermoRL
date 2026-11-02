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
  PUE: ["PUE", "the pue value", "(PUE)", "PUEs", "pue_value", "PUE-ratio", "computePUE"],
  carbon: ["carbon", "Carbon footprint", "carbons", "carbonFootprint", "carbon_x", "carbon-x", "fooCarbon", "CARBON"],
  "CO₂": ["CO₂", "co₂ output", "pCO₂"],
  CO2: ["CO2", "co2 emitted", "co2_kg", "totalCO2"],
  SLO: ["SLO", "an slo breach", "slo_target", "slo-target"],
  emergency: ["emergency", "Emergency stop", "emergencies", "emergencyStop", "emergency_mode", "isEmergency", "EMERGENCY"],
  "λ": ["λ", "Λ weight", "λ2", "lambda_λ"],
  "dual price(s)": ["dual price", "Dual Prices", "dual_prices", "dual-price", "dualPrice", "dualprices"],
  THI: ["THI", "thi score", "thi_value", "THI-index", "getTHI"],
  regret: ["regret", "Regret term", "regrets", "regretBound", "regret_x", "cumulativeRegret"],
  "counterfactual outcome": ["counterfactual outcome", "Counterfactual   Outcome", "counterfactualOutcome", "counterfactual_outcome", "counterfactual-outcomes"],
  "energy saving(s)": ["energy saving", "Energy Savings", "energySavings", "energy_savings", "energy-saving", "EnergySaving"],
  "cooling savings": ["cooling savings", "Cooling  Savings", "coolingSavings", "cooling_savings", "cooling-saving"],
  "removes hotspots": ["removes hotspots", "Removes Hotspots", "removesHotspots", "removes_hotspots", "remove-hotspot", "removes-hotspots"],
  "hotspot removal": ["hotspot removal", "Hotspot  Removal", "hotspotRemoval", "hotspot_removal", "hotspot-removal"],
  winner: ["winner", "The Winner is", "winners", "winnerBadge", "winner_x", "isWinner", "WINNERS"],
  "best policy": ["best policy", "Best  Policy", "bestPolicy", "best_policy", "best-policy", "BestPolicy", "best policies"],
  "significant(ly)": ["significant", "significantly lower", "Significant", "isSignificant", "significant_x", "significantly-lower"],
  "real Summit temperature": ["real Summit temperature", "Real summit Temperature", "realSummitTemperature", "real_summit_temperature", "real-summit-temperature"],
  "hardware temperature": ["hardware temperature", "Hardware  Temperature", "hardwareTemperature", "hardware_temperature", "hardware-temperatures"],
  "safety limit": ["safety limit", "Safety Limit", "safetyLimit", "safety_limit", "safety-limits"],
};

// Flagged: a term (case-insensitive, optional plural) that starts at a word start, an "_"/"-" boundary or a
// camelCase hump, with its words joined by whitespace, "_", "-", camelCase or nothing (bestPolicy, hotspot_removal).
// Long terms (emergency, carbon, regret, winner, multi-word terms) may be followed directly by an upper-case
// letter, "_", "-" (emergencyStop, carbon_x); short terms (PUE, SLO, THI, CO2, significant)
// need a non-letter after them. λ and CO₂ are matched anywhere.
// Not flagged: words that merely start with a term and continue in lower case (carbonate, regrettable, slow).
const CLEAN = [
  "pueblo, queue, opuel, puerto",
  "carbonate, carbonated",
  "slow, slope, close, slot, sloth",
  "this, think, within, thing, thin, nothing",
  "emergent, emergence",
  "regrettable, regretted",
  "winnerless, winnow",
  "CO22, ACO2, cocoa2",
  "significance, insignificant",
  "dual pricer, dualpricing",
  "bestow, best practice, best-effort",
  "energy use, saving time, cooling loop, safety first, hardware node, real data",
  "emergencyless",
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
    for (const text of CLEAN) expect(scanText(text), text).toEqual([]);
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
