import type { LoadedRun } from "../data/loader";
import { candidatesFor, decisionAt, decisionsIn, type DecisionView } from "../data/views";
import { formatClock, pulseBounds } from "../model/time";
import type { Catalog } from "../schema/replay";
import { COPY } from "./copy";

export const WHY_PAGE_SIZE = 50;

type Side = "left" | "right";

export interface WhyHandlers {
  onSide?(side: Side): void;
  onPage?(page: number): void;
  onExpand?(decisionIndex: number | null): void;
}

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = "") => {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text) n.textContent = text;
  return n;
};

function candidatesBlock(run: LoadedRun, d: DecisionView): HTMLElement {
  const box = el("div", "why-candidates");
  const table = el("table", "why-table");
  table.append(el("caption", "", COPY.why.candidatesCaption));
  const head = el("tr");
  for (const h of Object.values(COPY.why.columns)) head.append(el("th", "", h));
  const thead = el("thead");
  thead.append(head);
  const tbody = el("tbody");
  for (const c of candidatesFor(run, d.index)) {
    const tr = el("tr", c.chosen ? "is-chosen" : "");
    const cells: [string, string?][] = [
      [String(c.rack)],
      [c.score.toFixed(6), c.score.toPrecision(9)],
      [c.tc.toFixed(3), c.tc.toPrecision(9)],
      [c.committedKw.toFixed(2), c.committedKw.toPrecision(9)],
      [String(c.free)],
    ];
    cells.forEach(([text, title], i) => {
      const td = el("td", i ? "num" : "", text);
      if (title) td.title = title;
      tr.append(td);
    });
    tbody.append(tr);
  }
  table.append(thead, tbody);
  box.append(table, el("p", "why-ties", COPY.why.ties(d.nTies)));
  if (!d.chosenIsBest) box.append(el("p", "why-note", COPY.why.notBest));
  return box;
}

function itemNode(run: LoadedRun, d: DecisionView, handlers?: WhyHandlers): HTMLElement {
  const li = el("li", "why-item");
  li.dataset.decisionIndex = String(d.index);
  li.dataset.jobId = String(d.jobId);
  const head = el("button", "why-item-head");
  head.type = "button";
  head.setAttribute("aria-expanded", "false");
  const parts = [
    el("span", "why-job", COPY.why.job(d.jobId)),
    el("span", "why-nodes", COPY.why.nodes(d.nodes)),
    el("span", "why-rule", d.rule),
    el("span", "why-racks", COPY.why.racks(d.chosen)),
    el("span", "why-obs", COPY.why.loggedAt(d.tObs)),
    el("span", "why-raps", COPY.why.rapsStart(d.rapsTs)),
  ];
  head.append(...parts.flatMap((n, i) => (i ? [" ", n] : [n])));
  let body: HTMLElement | null = null;
  head.addEventListener("click", () => {
    if (body) {
      body.remove();
      body = null;
    } else {
      body = candidatesBlock(run, d);
      li.append(body);
    }
    head.setAttribute("aria-expanded", String(body !== null));
    handlers?.onExpand?.(body ? d.index : null);
  });
  li.append(head);
  return li;
}

export function whyWindowKey(run: LoadedRun, t_s: number, cat: Catalog): string {
  const ids = decisionsIn(run, ...pulseBounds(t_s, cat));
  return `${run.meta.run_id}|${ids.length}|${ids[0] ?? ""}|${ids[ids.length - 1] ?? ""}`;
}

const headerText = (run: LoadedRun, t_s: number, cat: Catalog) =>
  COPY.why.header(cat.time.pulse_window_s, formatClock(t_s), run.meta.policy, run.meta.seed);

export function updateWhyHeader(root: HTMLElement, run: LoadedRun, t_s: number, cat: Catalog): void {
  const h = root.querySelector(".why-header");
  const text = headerText(run, t_s, cat);
  if (h && h.textContent !== text) h.textContent = text;
}

const FOCUS_FALLBACK: Record<string, string> = { prev: "next", next: "prev" };

export function renderWhy(
  root: HTMLElement,
  run: LoadedRun,
  side: Side,
  t_s: number,
  cat: Catalog,
  page = 0,
  handlers?: WhyHandlers,
): void {
  const windowS = cat.time.pulse_window_s;
  const ids = decisionsIn(run, ...pulseBounds(t_s, cat));
  const pages = Math.max(1, Math.ceil(ids.length / WHY_PAGE_SIZE));
  const p = Math.min(pages - 1, Math.max(0, Math.trunc(page) || 0));
  const from = p * WHY_PAGE_SIZE;
  const to = Math.min(ids.length, from + WHY_PAGE_SIZE);

  const active = document.activeElement instanceof HTMLElement && root.contains(document.activeElement) ? document.activeElement.dataset.focus : undefined;
  const restoreFocus = () => {
    if (!active) return;
    const find = (id: string) => root.querySelector<HTMLButtonElement>(`[data-focus="${id}"]:not(:disabled)`);
    (find(active) ?? find(FOCUS_FALLBACK[active] ?? ""))?.focus();
  };

  const toggle = el("div", "why-side");
  toggle.setAttribute("role", "group");
  toggle.append(el("span", "why-side-label", COPY.why.sideLabel));
  for (const s of ["left", "right"] as const) {
    const b = el("button", "", COPY.why.sides[s]);
    b.type = "button";
    b.dataset.focus = s;
    b.setAttribute("aria-pressed", String(s === side));
    b.addEventListener("click", () => handlers?.onSide?.(s));
    toggle.append(b);
  }

  root.replaceChildren(
    el("p", "why-precision", cat.strings.precision_note),
    el("h3", "why-header", headerText(run, t_s, cat)),
    toggle,
    el("p", "why-count", COPY.why.count(ids.length)),
  );
  if (!ids.length) {
    root.append(el("p", "why-empty", COPY.why.empty(windowS)));
    restoreFocus();
    return;
  }

  const go = (next: number) => {
    renderWhy(root, run, side, t_s, cat, next, handlers);
    handlers?.onPage?.(Math.min(pages - 1, Math.max(0, next)));
  };
  const pager = el("div", "why-pager");
  const prev = el("button", "", COPY.why.prev);
  const next = el("button", "", COPY.why.next);
  prev.type = next.type = "button";
  prev.dataset.focus = "prev";
  next.dataset.focus = "next";
  prev.disabled = p === 0;
  next.disabled = p >= pages - 1;
  prev.addEventListener("click", () => go(p - 1));
  next.addEventListener("click", () => go(p + 1));
  pager.append(prev, el("span", "why-page", COPY.why.page(p + 1, pages, from + 1, to, ids.length)), next);

  const list = el("ol", "why-list");
  list.start = from + 1;
  for (let i = from; i < to; i++) list.append(itemNode(run, decisionAt(run, ids[i]), handlers));
  root.append(pager, list);
  restoreFocus();
}
