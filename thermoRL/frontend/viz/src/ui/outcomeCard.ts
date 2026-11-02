import type { Catalog, FrozenOutcome, PolicyId } from "../schema/replay";
import { COPY } from "./copy";

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = "") => {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text) n.textContent = text;
  return n;
};

const numCell = (v: number | undefined, active = false) => {
  const c = el("td", active ? "num is-active-seed" : "num");
  if (v === undefined || !Number.isFinite(v)) {
    c.textContent = COPY.outcome.missing;
  } else {
    c.textContent = v.toFixed(3);
    c.title = String(v);
  }
  return c;
};

const row = (...cells: HTMLElement[]) => {
  const tr = el("tr");
  tr.append(...cells);
  return tr;
};

function gapTable(outcome: FrozenOutcome): HTMLTableElement {
  const t = el("table", "outcome-table outcome-gaps");
  t.append(el("caption", "", COPY.outcome.gapCaption));
  const head = el("thead");
  head.append(row(...[COPY.outcome.gapSeed, COPY.outcome.gapPower, COPY.outcome.gapPacking].map((h) => el("th", "", h))));
  const body = el("tbody");
  const seeds = Object.keys(outcome.decision.per_seed).sort((a, b) => Number(a) - Number(b));
  for (const s of seeds) {
    const d = outcome.decision.per_seed[s];
    body.append(row(el("th", "", s), numCell(d.power_minus_thermal_c), numCell(d.packing_minus_thermal_c)));
  }
  t.append(head, body);
  return t;
}

function metricsTable(outcome: FrozenOutcome, active: { seed: number; left: PolicyId; right: PolicyId }): HTMLTableElement {
  const policies = [...new Set(outcome.metrics.map((m) => m.policy))];
  const seeds = [...new Set(outcome.metrics.map((m) => m.seed))].sort((a, b) => a - b);
  const t = el("table", "outcome-table outcome-metrics");
  t.append(el("caption", "", COPY.outcome.metricsCaption));
  const head = el("thead");
  head.append(
    row(
      el("th", "", COPY.outcome.metricsPolicy),
      ...seeds.map((s) => el("th", s === active.seed ? "is-active-seed" : "", COPY.outcome.metricsSeed(s))),
    ),
  );
  const body = el("tbody");
  for (const p of policies) {
    const tr = row(
      el("th", "", p),
      ...seeds.map((s) => numCell(outcome.metrics.find((m) => m.policy === p && m.seed === s)?.maxrack_mean_c, s === active.seed)),
    );
    if (p === active.left || p === active.right) tr.className = "is-active";
    body.append(tr);
  }
  t.append(head, body);
  return t;
}

export function renderOutcome(
  root: HTMLElement,
  outcome: FrozenOutcome,
  _cat: Catalog,
  active: { seed: number; left: PolicyId; right: PolicyId },
): void {
  root.replaceChildren(
    el("p", "outcome-headline", outcome.headline),
    el("p", "outcome-rule", outcome.rule),
    gapTable(outcome),
    metricsTable(outcome, active),
    el("p", "outcome-statement is-callout", outcome.experiment_statement),
    el("p", "outcome-footer", COPY.outcome.footer),
  );
}
