import type { Catalog, FrozenOutcome } from "../schema/replay";
import { COPY } from "./copy";

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = "") => {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text) n.textContent = text;
  return n;
};

const section = (heading: string, body: HTMLElement) => {
  const s = el("section", "about-section");
  s.append(el("h4", "about-heading", heading), body);
  return s;
};

export function renderAbout(root: HTMLElement, cat: Catalog, outcome: FrozenOutcome): void {
  const h = COPY.about.heading;
  const list = el("ul", "about-caveats");
  for (const b of COPY.about.bullets) list.append(el("li", "", b));
  const link = el("a", "", COPY.about.resultsLabel);
  link.href = COPY.about.resultsUrl;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  const linkWrap = el("p", "about-link");
  linkWrap.append(link);
  root.replaceChildren(
    el("p", "about-recorded", COPY.about.recorded),
    section(h.s2, el("p", "about-s2", cat.strings.s2)),
    section(h.interval, el("p", "about-interval", cat.strings.interval_semantics)),
    section(h.pulse, el("p", "about-pulse", cat.strings.pulse_rule)),
    section(h.precision, el("p", "about-precision", cat.strings.precision_note)),
    section(h.repro, el("p", "about-repro", outcome.reproducibility_scope)),
    section(h.caveats, list),
    linkWrap,
  );
}
