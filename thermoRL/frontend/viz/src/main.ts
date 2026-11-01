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
import { RackGrid } from "./scene/rackGrid";
import { COPY } from "./ui/copy";
import { Controls, installKeyboard } from "./ui/controls";
import { hideFallback, renderFallback } from "./ui/fallback";
import { Header } from "./ui/header";
import { Status } from "./ui/status";

interface Session {
  exp: ExperimentBundle;
  left: LoadedRun;
  right: LoadedRun;
  leftGrid: RackGrid;
  rightGrid: RackGrid;
  lut: Float32Array;
  rgb: Float32Array;
  player: Player;
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
}

function endSession(): void {
  const s = session;
  session = null;
  if (s) {
    s.unsubscribe();
    s.leftGrid.dispose();
    s.rightGrid.dispose();
  }
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
  session = {
    exp,
    left,
    right,
    leftGrid: new RackGrid(cat.grid),
    rightGrid: new RackGrid(cat.grid),
    lut: lutToRgb(cat.colormap.lut),
    rgb: new Float32Array(cat.grid.n_racks * 3),
    player,
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
  for (const [run, grid] of [
    [s.left, s.leftGrid],
    [s.right, s.rightGrid],
  ] as const) {
    frameColours(run, k, st.overlay, scale, s.lut, s.rgb);
    grid.setColours(s.rgb);
    grid.setPulses(startRacksIn(run, lo, hi));
    grid.setPinned(st.pinnedRack);
  }
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
    store.set({ experimentId: entry.id, ...sel, tick: query.tick ?? 0 });
    header.sync(store.get());
    store.subscribe((s, prev) => {
      scheduleUrlUpdate();
      if (SELECTION_KEYS.some((key) => s[key] !== prev[key]) && dualView) void reload();
      if ((Object.keys(s) as (keyof AppState)[]).some((key) => key !== "tick" && s[key] !== prev[key])) {
        header.sync(s);
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
