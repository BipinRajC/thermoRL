import type { LoadedRun } from "../data/loader";
import type { Catalog, IndexFile } from "../schema/replay";
import type { Overlay } from "../model/colour";
import type { AppState, Drawer } from "../model/store";
import { COPY } from "./copy";

export interface HeaderHandlers {
  onExperiment(id: string): void;
  onSeed(seed: number): void;
  onComparison(id: string): void;
  onOverlay(overlay: Overlay): void;
  onDrawer(drawer: Exclude<Drawer, "rack" | null>): void;
}

const OVERLAYS: Overlay[] = ["tc", "kw", "occupied"];
const DRAWERS = ["outcome", "why", "about"] as const;

const byId = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing #${id} in index.html`);
  return el as T;
};

const fill = (select: HTMLSelectElement, options: { value: string; label: string }[]) => {
  select.replaceChildren(
    ...options.map((o) => {
      const opt = document.createElement("option");
      opt.value = o.value;
      opt.textContent = o.label;
      return opt;
    }),
  );
};

export class Header {
  private readonly selExp = byId<HTMLSelectElement>("sel-exp");
  private readonly selSeed = byId<HTMLSelectElement>("sel-seed");
  private readonly selCmp = byId<HTMLSelectElement>("sel-cmp");
  private readonly identity = byId("identity");
  private cat: Catalog | null = null;

  constructor(h: HeaderHandlers) {
    document.title = COPY.appTitle;
    byId("app-title").textContent = COPY.appTitle;
    byId("app-badge").textContent = COPY.badge;
    byId("lbl-exp").prepend(COPY.labels.experiment);
    byId("lbl-seed").prepend(COPY.labels.seed);
    byId("lbl-cmp").prepend(COPY.labels.comparison);
    byId("lbl-overlay").textContent = COPY.labels.overlay;
    this.selExp.addEventListener("change", () => h.onExperiment(this.selExp.value));
    this.selSeed.addEventListener("change", () => h.onSeed(Number(this.selSeed.value)));
    this.selCmp.addEventListener("change", () => h.onComparison(this.selCmp.value));
    for (const o of OVERLAYS) {
      const b = byId<HTMLButtonElement>(`overlay-${o}`);
      b.textContent = COPY.overlays[o];
      b.addEventListener("click", () => h.onOverlay(o));
    }
    for (const d of DRAWERS) {
      const b = byId<HTMLButtonElement>(`btn-${d}`);
      b.textContent = COPY.drawers[d];
      b.addEventListener("click", () => h.onDrawer(d));
    }
  }

  setExperiments(index: IndexFile): void {
    fill(this.selExp, index.experiments.map((e) => ({ value: e.id, label: e.label })));
  }

  setCatalog(cat: Catalog | null): void {
    this.cat = cat;
    fill(this.selSeed, (cat?.seeds ?? []).map((s) => ({ value: String(s.seed), label: String(s.seed) })));
    fill(this.selCmp, (cat?.comparisons ?? []).map((c) => ({ value: c.id, label: `${c.left} vs ${c.right}` })));
  }

  setPanels(left: LoadedRun | null, right: LoadedRun | null): void {
    for (const [side, run] of [["left", left], ["right", right]] as const) {
      byId(`title-${side}`).textContent = run?.meta.policy ?? "";
      const badge = byId(`badge-${side}`);
      const verified = run?.meta.c_prime_status === "verified_E12";
      badge.textContent = run ? (verified ? COPY.cPrimeVerified : COPY.cPrimeNot) : "";
      badge.classList.toggle("verified", verified);
      badge.hidden = !run;
    }
  }

  setDisabled(disabled: boolean): void {
    for (const el of [this.selSeed, this.selCmp]) el.disabled = disabled;
    for (const o of OVERLAYS) byId<HTMLButtonElement>(`overlay-${o}`).disabled = disabled;
    for (const d of DRAWERS) byId<HTMLButtonElement>(`btn-${d}`).disabled = disabled;
  }

  sync(s: AppState): void {
    if (this.selExp.value !== s.experimentId) this.selExp.value = s.experimentId;
    if (this.selSeed.value !== String(s.seed)) this.selSeed.value = String(s.seed);
    if (this.selCmp.value !== s.comparisonId) this.selCmp.value = s.comparisonId;
    for (const o of OVERLAYS) byId(`overlay-${o}`).setAttribute("aria-pressed", String(s.overlay === o));
    for (const d of DRAWERS) byId(`btn-${d}`).setAttribute("aria-pressed", String(s.drawer === d));
    const drawer = byId("drawer");
    drawer.hidden = s.drawer === null;
    drawer.dataset.drawer = s.drawer ?? "";
    const cat = this.cat;
    const note = cat?.seeds.find((x) => x.seed === s.seed)?.note;
    this.identity.textContent = cat
      ? [cat.experiment.workload_label, cat.experiment.system_label, cat.experiment.scenario, note].filter(Boolean).join(" · ")
      : "";
  }
}
