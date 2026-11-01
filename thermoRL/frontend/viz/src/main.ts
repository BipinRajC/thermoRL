import "./style.css";
import { ReplayError } from "./data/loader";
import { startRacksIn } from "./data/views";
import type { LoadedRun } from "./data/loader";
import { frameColours, lutToRgb, scaleFor } from "./model/colour";
import {
  RunCache,
  Store,
  dataDirFromQuery,
  defaultSelection,
  loadComparison,
  resolveSelection,
  stateFromQuery,
  stateToQuery,
  type AppState,
  type ExperimentBundle,
} from "./model/store";
import { pulseBounds, tickToTs } from "./model/time";
import { Player } from "./replay/player";
import { DualView } from "./scene/dualView";
import { RackGrid, pointerToNorm, rackAt } from "./scene/rackGrid";
import { renderAbout } from "./ui/aboutPanel";
import { COPY } from "./ui/copy";
import { Controls, installKeyboard } from "./ui/controls";
import { hideFallback, renderFallback } from "./ui/fallback";
import { Header } from "./ui/header";
import { renderLegend } from "./ui/legend";
import { renderOutcome } from "./ui/outcomeCard";
import { renderSparkline, type Sparkline } from "./ui/sparkline";
import { Status } from "./ui/status";
import { Timeline } from "./ui/timeline";
import { placeTooltip, tooltipHtml } from "./ui/tooltip";
import { renderWhy } from "./ui/whyDrawer";

interface Session {
  exp: ExperimentBundle;
  left: LoadedRun;
  right: LoadedRun;
  leftGrid: RackGrid;
  rightGrid: RackGrid;
  lut: Float32Array;
  rgb: Float32Array;
  player: Player;
  timeline: Timeline;
  unsubscribe: () => void;
}

const MAX_FRAME_MS = 250;
const URL_DEBOUNCE_MS = 250;

const byId = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing #${id} in index.html`);
  return el as T;
};

const dataDir = dataDirFromQuery(location.search);
const query = stateFromQuery(location.search);
const store = new Store();
const cache = new RunCache();
const status = new Status(byId("status"));
const stage = byId("stage");
const panels = byId("panels");
const fallbackEl = byId("fallback");
const leftEl = byId("view-left");
const rightEl = byId("view-right");
const timelineEl = byId("timeline");
const tooltipEl = byId("tooltip");
const drawerBody = byId("drawer-body");
const legendEls = { left: byId("legend-left"), right: byId("legend-right") };
const viewEls = { left: leftEl, right: rightEl };
type Side = "left" | "right";

let dualView: DualView | null = null;
if (DualView.webglAvailable()) {
  try {
    dualView = new DualView(byId<HTMLCanvasElement>("gl"));
  } catch {
    dualView = null;
  }
}

let session: Session | null = null;
let selectSeq = 0;
let urlTimer: number | undefined;

const header = new Header({
  onExperiment: (id) => void selectExperiment(id),
  onSeed: (seed) => store.set({ seed }),
  onComparison: (comparisonId) => store.set({ comparisonId }),
  onOverlay: (overlay) => store.set({ overlay }),
  onDrawer: (d) => store.set({ drawer: store.get().drawer === d ? null : d }),
});
const controls = new Controls(byId("controls"));
installKeyboard(
  () => controls,
  () => session?.player ?? null,
  () => session?.exp.catalog ?? null,
);

function setStage(state: "loading" | "error" | "ready" | "fallback"): void {
  stage.dataset.state = state;
  panels.hidden = state !== "ready";
  timelineEl.classList.toggle("is-idle", state !== "ready");
}

let hover: { side: Side; r: number; x: number; y: number } | null = null;
let tooltipHtmlShown = "";

function updateTooltip(s: Session | null): void {
  if (!hover || !s) {
    tooltipEl.hidden = true;
    tooltipHtmlShown = "";
    return;
  }
  const st = store.get();
  const html = tooltipHtml(hover.side === "left" ? s.left : s.right, s.player.tick, hover.r, scaleFor(st.overlay, s.exp.catalog, st.seed), s.exp.catalog);
  if (html !== tooltipHtmlShown) {
    tooltipEl.innerHTML = html;
    tooltipHtmlShown = html;
  }
  tooltipEl.hidden = false;
  placeTooltip(tooltipEl, hover.x, hover.y);
}

function rackUnderPointer(e: MouseEvent, side: Side): number | null {
  const s = session;
  if (!s) return null;
  const grid = s.exp.catalog.grid;
  const p = pointerToNorm(e.clientX, e.clientY, viewEls[side].getBoundingClientRect(), grid);
  return rackAt(p.x, p.y, grid);
}

for (const side of ["left", "right"] as const) {
  const el = viewEls[side];
  el.addEventListener("pointermove", (e) => {
    const r = rackUnderPointer(e, side);
    hover = r === null ? null : { side, r, x: e.clientX, y: e.clientY };
    updateTooltip(session);
  });
  el.addEventListener("pointerleave", () => {
    hover = null;
    updateTooltip(session);
  });
  el.addEventListener("click", (e) => {
    const r = rackUnderPointer(e, side);
    if (r !== null) store.set({ pinnedRack: r, drawer: "rack" });
  });
}

window.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const st = store.get();
  if (st.pinnedRack !== null) store.set({ pinnedRack: null, drawer: st.drawer === "rack" ? null : st.drawer });
});

const rackPane = document.createElement("div");
rackPane.dataset.pane = "rack";
let sparkline: Sparkline | null = null;
let sparkFor: { session: Session; rack: number } | null = null;

function syncRackDrawer(s: Session | null): void {
  const st = store.get();
  const rack = s && st.drawer === "rack" ? st.pinnedRack : null;
  if (rack === null || !s) {
    if (sparkFor) {
      sparkline?.dispose();
      sparkline = null;
      sparkFor = null;
      rackPane.remove();
    }
    return;
  }
  if (sparkFor?.session === s && sparkFor.rack === rack && rackPane.isConnected) return;
  sparkline?.dispose();
  if (!rackPane.isConnected) drawerBody.append(rackPane);
  sparkline = renderSparkline(rackPane, s.left, s.right, rack, s.exp.catalog);
  sparkFor = { session: s, rack };
}

const infoPane = document.createElement("div");
infoPane.dataset.pane = "info";
let infoKey = "";

function syncInfoDrawer(): void {
  const st = store.get();
  const info = st.drawer === "outcome" || st.drawer === "about" ? st.drawer : null;
  const exp = info ? cache.loadedExperiment(dataDir, st.experimentId) : undefined;
  if (!info || !exp) {
    infoKey = "";
    infoPane.remove();
    return;
  }
  const cmp = exp.catalog.comparisons.find((c) => c.id === st.comparisonId) ?? exp.catalog.comparisons.find((c) => c.default) ?? exp.catalog.comparisons[0];
  const key = [info, st.experimentId, st.seed, cmp?.id].join("|");
  if (key === infoKey && infoPane.isConnected) return;
  infoKey = key;
  if (info === "about") renderAbout(infoPane, exp.catalog, exp.outcome);
  else if (cmp) renderOutcome(infoPane, exp.outcome, exp.catalog, { seed: st.seed, left: cmp.left, right: cmp.right });
  if (!infoPane.isConnected) drawerBody.append(infoPane);
}

const whyPane = document.createElement("div");
whyPane.dataset.pane = "why";
let whyBase = "";
let whyPage = 0;
let whyKey = "";

function syncWhyDrawer(s: Session | null): void {
  const st = store.get();
  if (!s || st.drawer !== "why") {
    whyBase = "";
    whyKey = "";
    whyPane.remove();
    return;
  }
  const base = [s.left.meta.run_id, s.right.meta.run_id, s.player.tick, st.whySide].join("|");
  if (base !== whyBase) {
    whyBase = base;
    whyPage = 0;
  }
  const key = `${base}|${whyPage}`;
  if (key === whyKey && whyPane.isConnected) return;
  whyKey = key;
  const handlers = {
    onSide: (side: Side) => store.set({ whySide: side }),
    onPage: (page: number) => {
      whyPage = page;
      whyKey = `${base}|${page}`;
    },
  };
  renderWhy(whyPane, st.whySide === "left" ? s.left : s.right, st.whySide, tickToTs(s.player.tick), s.exp.catalog, whyPage, handlers);
  if (!whyPane.isConnected) drawerBody.append(whyPane);
}

function endSession(): void {
  const s = session;
  session = null;
  if (s) {
    s.unsubscribe();
    s.timeline.dispose();
    s.leftGrid.dispose();
    s.rightGrid.dispose();
  }
  hover = null;
  updateTooltip(null);
  syncRackDrawer(null);
  syncWhyDrawer(null);
  controls.bind(null, null);
  header.setPanels(null, null);
  dualView?.clear();
}

function startSession(left: LoadedRun, right: LoadedRun, exp: ExperimentBundle): void {
  const cat = exp.catalog;
  for (const run of [left, right]) {
    if (run.meta.n_racks !== cat.grid.n_racks || run.meta.n_ticks !== cat.time.n_ticks) {
      throw new ReplayError("mismatch", `${run.meta.run_id} does not match the catalog grid or time axis`);
    }
  }
  endSession();
  const player = new Player(cat.time.n_ticks);
  player.seek(store.get().tick);
  const unsubscribe = player.onChange((tick) => store.set({ tick }));
  const timeline = new Timeline(byId<HTMLCanvasElement>("timeline-canvas"), cat);
  timeline.setRuns(left, right, [left.meta.policy, right.meta.policy]);
  timeline.onSeek((k) => player.seek(k));
  session = {
    exp,
    left,
    right,
    leftGrid: new RackGrid(cat.grid),
    rightGrid: new RackGrid(cat.grid),
    lut: lutToRgb(cat.colormap.lut),
    rgb: new Float32Array(cat.grid.n_racks * 3),
    player,
    timeline,
    unsubscribe,
  };
  header.setPanels(left, right);
  controls.bind(player, cat);
  setStage("ready");
  status.hide();
  store.set({ tick: player.tick });
  dualView?.resize();
}

async function reload(): Promise<void> {
  endSession();
  setStage("loading");
  status.loading();
  try {
    const res = await loadComparison(dataDir, store, cache, undefined, (file, done, total) => status.loading(file, done, total));
    if (res === "stale") return;
    const exp = cache.loadedExperiment(dataDir, store.get().experimentId);
    if (!exp) throw new ReplayError("schema", "Experiment catalog was not loaded");
    startSession(res.left, res.right, exp);
  } catch (e) {
    endSession();
    setStage("error");
    status.error(e);
  }
}

async function entryFor(id: string | undefined) {
  const index = await cache.index(dataDir);
  if (!index.experiments.length) throw new Error(COPY.emptyNoExperiments);
  const entry = index.experiments.find((e) => e.id === id) ?? index.experiments.find((e) => e.default) ?? index.experiments[0];
  return { index, entry, exp: await cache.experiment(dataDir, entry) };
}

async function selectExperiment(id: string): Promise<void> {
  const mine = ++selectSeq;
  try {
    const { entry, exp } = await entryFor(id);
    if (mine !== selectSeq) return;
    if (!dualView) {
      store.set({ experimentId: entry.id });
      return;
    }
    header.setCatalog(exp.catalog);
    store.set({ experimentId: entry.id, ...defaultSelection(exp.catalog), pinnedRack: null });
  } catch (e) {
    if (mine !== selectSeq) return;
    endSession();
    setStage("error");
    status.error(e);
  }
}

function scheduleUrlUpdate(): void {
  window.clearTimeout(urlTimer);
  urlTimer = window.setTimeout(() => history.replaceState(null, "", stateToQuery(store.get(), dataDir)), URL_DEBOUNCE_MS);
}

const SELECTION_KEYS: (keyof AppState)[] = ["experimentId", "seed", "comparisonId"];

function draw(s: Session): void {
  const st = store.get();
  const cat = s.exp.catalog;
  const k = s.player.tick;
  const scale = scaleFor(st.overlay, cat, st.seed);
  const [lo, hi] = pulseBounds(tickToTs(k), cat);
  for (const [side, run, grid] of [
    ["left", s.left, s.leftGrid],
    ["right", s.right, s.rightGrid],
  ] as const) {
    const outOfRange = frameColours(run, k, st.overlay, scale, s.lut, s.rgb);
    grid.setColours(s.rgb);
    grid.setPulses(startRacksIn(run, lo, hi));
    grid.setPinned(st.pinnedRack);
    grid.setHover(hover?.side === side ? hover.r : null);
    renderLegend(legendEls[side], scale, s.lut, outOfRange);
  }
  s.timeline.setCursor(k);
  syncRackDrawer(s);
  syncWhyDrawer(s);
  sparkline?.setCursor(k);
  updateTooltip(s);
  dualView!.render(s.leftGrid, s.rightGrid, leftEl, rightEl);
}

let last = performance.now();
function frame(now: number): void {
  const dt = Math.max(0, Math.min(MAX_FRAME_MS, now - last));
  last = now;
  const s = session;
  if (s && dualView) {
    if (s.player.playing) s.player.advance(dt);
    controls.refresh();
    draw(s);
  }
  requestAnimationFrame(frame);
}

async function boot(): Promise<void> {
  status.loading();
  setStage("loading");
  try {
    const { index, entry, exp } = await entryFor(query.experimentId);
    header.setExperiments(index);
    header.setCatalog(exp.catalog);
    const sel = resolveSelection(exp.catalog, entry.id === query.experimentId ? query : {});
    store.set({ experimentId: entry.id, ...sel, tick: query.tick ?? 0, drawer: "outcome" });
    header.sync(store.get());
    syncInfoDrawer();
    store.subscribe((s, prev) => {
      scheduleUrlUpdate();
      if (SELECTION_KEYS.some((key) => s[key] !== prev[key]) && dualView) void reload();
      if ((Object.keys(s) as (keyof AppState)[]).some((key) => key !== "tick" && s[key] !== prev[key])) {
        header.sync(s);
        syncInfoDrawer();
        if (!dualView) renderFallback(fallbackEl, s.experimentId);
      }
    });
    if (!dualView) {
      header.setDisabled(true);
      setStage("fallback");
      status.hide();
      renderFallback(fallbackEl, entry.id);
      return;
    }
    hideFallback(fallbackEl);
    await reload();
  } catch (e) {
    setStage("error");
    status.error(e);
  }
}

if (dualView) {
  const view = dualView;
  window.addEventListener("resize", () => view.resize());
  new ResizeObserver(() => view.resize()).observe(stage);
  requestAnimationFrame(frame);
}
void boot();
