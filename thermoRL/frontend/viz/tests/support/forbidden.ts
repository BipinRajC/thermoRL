const ALLOWED_IDENTIFIER = /unavailable_fields/g;

const SEP = "[\\s_-]*";
const LETTER_OR_DIGIT = "\\p{L}\\p{N}";

const ci = (fragment: string) =>
  Array.from(fragment)
    .map((c) => (c.toLowerCase() !== c.toUpperCase() ? `[${c.toLowerCase()}${c.toUpperCase()}]` : c))
    .join("");

type Kind = "word" | "long";

function term(atoms: string[], kind: Kind): RegExp {
  const body = atoms.map(ci).join(SEP);
  const [first, ...rest] = atoms;
  const camel = [first[0].toUpperCase() + ci(first.slice(1)), ...rest.map(ci)].join(SEP);
  const left = `(?:(?<![${LETTER_OR_DIGIT}])${body}|(?<=[\\p{Ll}\\p{N}])${camel})`;
  const right = kind === "word" ? `(?![${LETTER_OR_DIGIT}])` : `(?![\\p{Ll}\\p{N}])`;
  return new RegExp(`${left}${right}`, "u");
}

export const FORBIDDEN: { term: string; pattern: RegExp }[] = [
  { term: "PUE", pattern: term(["PUEs?"], "word") },
  { term: "carbon", pattern: term(["carbons?"], "long") },
  { term: "CO₂", pattern: /CO₂/iu },
  { term: "CO2", pattern: term(["CO2"], "word") },
  { term: "SLO", pattern: term(["SLO"], "word") },
  { term: "emergency", pattern: term(["emergenc(?:y|ies)"], "long") },
  { term: "λ", pattern: /λ/iu },
  { term: "dual price(s)", pattern: term(["dual", "prices?"], "long") },
  { term: "THI", pattern: term(["THI"], "word") },
  { term: "regret", pattern: term(["regrets?"], "long") },
  { term: "counterfactual outcome", pattern: term(["counterfactual", "outcomes?"], "long") },
  { term: "energy saving(s)", pattern: term(["energy", "savings?"], "long") },
  { term: "cooling savings", pattern: term(["cooling", "savings?"], "long") },
  { term: "removes hotspots", pattern: term(["removes?", "hotspots?"], "long") },
  { term: "hotspot removal", pattern: term(["hotspot", "removal"], "long") },
  { term: "winner", pattern: term(["winners?"], "long") },
  { term: "best policy", pattern: term(["best", "polic(?:y|ies)"], "long") },
  { term: "significant(ly)", pattern: term(["significant(?:ly)?"], "word") },
  { term: "real Summit temperature", pattern: term(["real", "summit", "temperatures?"], "long") },
  { term: "hardware temperature", pattern: term(["hardware", "temperatures?"], "long") },
  { term: "safety limit", pattern: term(["safety", "limits?"], "long") },
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
