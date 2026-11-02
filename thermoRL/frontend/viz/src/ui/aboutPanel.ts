import type { Catalog, FrozenOutcome } from "../schema/replay";
import { COPY } from "./copy";

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = "") => {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text) n.textContent = text;
  return n;
};

const section = (heading: string, ...body: HTMLElement[]) => {
  const s = el("section", "about-section");
  s.append(el("h4", "about-heading", heading), ...body);
  return s;
};

const plainSection = (heading: string, plain: string, verbatim: HTMLElement) => {
  const tech = el("details", "about-tech");
  tech.append(el("summary", "", COPY.about.technicalDetail), verbatim);
  return section(heading, el("p", "about-plain", plain), tech);
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
    plainSection(h.s2, COPY.about.plain.s2, el("p", "about-s2", cat.strings.s2)),
    plainSection(h.interval, COPY.about.plain.interval, el("p", "about-interval", cat.strings.interval_semantics)),
    plainSection(h.pulse, COPY.about.plain.pulse, el("p", "about-pulse", cat.strings.pulse_rule)),
    plainSection(h.precision, COPY.about.plain.precision, el("p", "about-precision", cat.strings.precision_note)),
    plainSection(h.repro, COPY.about.plain.repro, el("p", "about-repro", outcome.reproducibility_scope)),
    section(h.caveats, list),
    linkWrap,
  );
}
