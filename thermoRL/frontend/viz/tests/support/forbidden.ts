const ALLOWED_IDENTIFIER = /unavailable_fields/g;

const WORD = "[\\p{L}\\p{N}_]";
const bounded = (body: string) => `(?<!${WORD})(?:${body})(?!${WORD})`;

export const FORBIDDEN: { term: string; pattern: RegExp }[] = [
  { term: "PUE", pattern: new RegExp(bounded("PUE"), "iu") },
  { term: "carbon", pattern: new RegExp(bounded("carbon"), "iu") },
  { term: "CO₂", pattern: /CO₂/iu },
  { term: "CO2", pattern: new RegExp(bounded("CO2"), "iu") },
  { term: "SLO", pattern: new RegExp(bounded("SLO"), "iu") },
  { term: "emergency", pattern: new RegExp(bounded("emergency"), "iu") },
  { term: "λ", pattern: /λ/iu },
  { term: "dual price(s)", pattern: new RegExp(bounded("dual[\\s_-]+prices?"), "iu") },
  { term: "THI", pattern: new RegExp(bounded("THI"), "iu") },
  { term: "regret", pattern: new RegExp(bounded("regret"), "iu") },
  { term: "counterfactual outcome", pattern: new RegExp(bounded("counterfactual\\s+outcome"), "iu") },
  { term: "energy saving(s)", pattern: new RegExp(bounded("energy\\s+savings?"), "iu") },
  { term: "cooling savings", pattern: new RegExp(bounded("cooling\\s+savings"), "iu") },
  { term: "removes hotspots", pattern: new RegExp(bounded("removes\\s+hotspots"), "iu") },
  { term: "hotspot removal", pattern: new RegExp(bounded("hotspot\\s+removal"), "iu") },
  { term: "winner", pattern: new RegExp(bounded("winner"), "iu") },
  { term: "best policy", pattern: new RegExp(bounded("best\\s+policy"), "iu") },
  { term: "significant(ly)", pattern: new RegExp(bounded("significant(?:ly)?"), "iu") },
  { term: "real Summit temperature", pattern: new RegExp(bounded("real\\s+Summit\\s+temperature"), "iu") },
  { term: "hardware temperature", pattern: new RegExp(bounded("hardware\\s+temperature"), "iu") },
  { term: "safety limit", pattern: new RegExp(bounded("safety\\s+limit"), "iu") },
];

export interface Hit {
  term: string;
  line: number;
  text: string;
}

export function scanText(text: string): Hit[] {
  const hits: Hit[] = [];
  text.split(/\r?\n/).forEach((raw, i) => {
    const line = raw.replace(ALLOWED_IDENTIFIER, "");
    for (const f of FORBIDDEN) if (f.pattern.test(line)) hits.push({ term: f.term, line: i + 1, text: raw.trim() });
  });
  return hits;
}
