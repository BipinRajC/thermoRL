import type { LoadedRun } from "../data/loader";
import { tickValue } from "../data/views";
import type { Catalog } from "../schema/replay";
import { COPY } from "./copy";
import {
  CachedCanvas,
  FONT,
  SERIES_COLOURS,
  extent,
  padRange,
  paintCursor,
  paintPanel,
  shadeEndX,
  tickToX,
  xToTick,
  type Box,
} from "./plot";

export { shadeEndX };

const MARGIN = { left: 46, right: 10, top: 4, bottom: 4 };
const TITLE_H = 14;
const GAP = 6;
const MAIN_SHARE = 0.62;

export interface TimelineLayout {
  plotLeft: number;
  plotWidth: number;
  main: Box;
  spread: Box;
  mainTitleY: number;
  spreadTitleY: number;
}

export function layoutFor(w: number, h: number): TimelineLayout {
  const plotWidth = Math.max(1, w - MARGIN.left - MARGIN.right);
  const inner = h - MARGIN.top - MARGIN.bottom - 2 * TITLE_H - GAP;
  const mainH = Math.max(8, inner * MAIN_SHARE);
  const spreadH = Math.max(8, inner - mainH);
  const mainTitleY = MARGIN.top;
  const main = { x: MARGIN.left, y: mainTitleY + TITLE_H, w: plotWidth, h: mainH };
  const spreadTitleY = main.y + main.h + GAP;
  const spread = { x: MARGIN.left, y: spreadTitleY + TITLE_H, w: plotWidth, h: spreadH };
  return { plotLeft: MARGIN.left, plotWidth, main, spread, mainTitleY, spreadTitleY };
}

const column = (run: LoadedRun, col: "maxrack_c" | "minrack_c", n: number): Float64Array => {
  const out = new Float64Array(n);
  for (let k = 0; k < n; k++) out[k] = tickValue(run, k, col);
  return out;
};

export class Timeline {
  static xToTick = xToTick;
  static tickToX = tickToX;

  private runs: { max: Float64Array[]; spread: Float64Array[]; labels: [string, string] } | null = null;
  private cursor = 0;
  private seek: ((k: number) => void) | null = null;
  private dragging = false;
  private readonly view: CachedCanvas;
  private readonly onDown = (e: PointerEvent) => {
    if (e.button !== 0) return;
    this.dragging = true;
    this.el.setPointerCapture?.(e.pointerId);
    this.seekFrom(e);
  };
  private readonly onMove = (e: PointerEvent) => {
    if (this.dragging) this.seekFrom(e);
  };
  private readonly onUp = (e: PointerEvent) => {
    this.dragging = false;
    this.el.releasePointerCapture?.(e.pointerId);
  };

  constructor(
    private readonly el: HTMLCanvasElement,
    private readonly cat: Catalog,
  ) {
    this.view = new CachedCanvas(el, (ctx, w, h) => this.paintBase(ctx, w, h), (ctx, w, h) => this.paintTop(ctx, w, h));
    el.setAttribute("role", "img");
    el.setAttribute("aria-label", COPY.timeline.label);
    el.addEventListener("pointerdown", this.onDown);
    el.addEventListener("pointermove", this.onMove);
    el.addEventListener("pointerup", this.onUp);
    el.addEventListener("pointercancel", this.onUp);
  }

  setRuns(left: LoadedRun, right: LoadedRun, labels: [string, string]): void {
    const n = this.cat.time.n_ticks;
    const max = [column(left, "maxrack_c", n), column(right, "maxrack_c", n)];
    const min = [column(left, "minrack_c", n), column(right, "minrack_c", n)];
    const spread = max.map((m, i) => m.map((v, k) => v - min[i][k]));
    this.runs = { max, spread, labels };
    this.view.invalidate();
  }

  setCursor(k: number): void {
    if (k === this.cursor) return;
    this.cursor = k;
    this.view.present();
  }

  onSeek(fn: (k: number) => void): void {
    this.seek = fn;
  }

  dispose(): void {
    this.view.dispose();
    this.el.removeEventListener("pointerdown", this.onDown);
    this.el.removeEventListener("pointermove", this.onMove);
    this.el.removeEventListener("pointerup", this.onUp);
    this.el.removeEventListener("pointercancel", this.onUp);
  }

  private seekFrom(e: PointerEvent): void {
    const rect = this.el.getBoundingClientRect();
    const l = layoutFor(rect.width, rect.height);
    this.seek?.(xToTick(e.clientX - rect.left - l.plotLeft, l.plotWidth, this.cat.time.n_ticks));
  }

  private paintBase(ctx: CanvasRenderingContext2D, w: number, h: number): void {
    if (!this.runs) return;
    const l = layoutFor(w, h);
    const n = this.cat.time.n_ticks;
    const shadeEnd = shadeEndX(this.cat, l.plotWidth);
    paintPanel(ctx, {
      box: l.main,
      series: this.runs.max,
      range: padRange(extent(this.runs.max)),
      digits: 2,
      nTicks: n,
      shadeEnd,
      shadeLabel: COPY.timeline.before,
    });
    const [, hi] = extent(this.runs.spread);
    paintPanel(ctx, { box: l.spread, series: this.runs.spread, range: [0, hi > 0 ? hi * 1.05 : 1], digits: 2, nTicks: n, shadeEnd });
    ctx.font = FONT;
    ctx.fillStyle = "#e6e9ef";
    ctx.textBaseline = "top";
    ctx.textAlign = "left";
    ctx.fillText(COPY.timeline.yAxis, l.main.x, l.mainTitleY);
    ctx.fillText(COPY.timeline.spreadAxis, l.spread.x, l.spreadTitleY);
    ctx.textAlign = "right";
    let x = l.main.x + l.main.w;
    for (let i = 1; i >= 0; i--) {
      const label = this.runs.labels[i];
      ctx.fillStyle = "#e6e9ef";
      ctx.fillText(label, x, l.mainTitleY);
      x -= ctx.measureText(label).width + 6;
      ctx.fillStyle = SERIES_COLOURS[i];
      ctx.fillRect(x - 14, l.mainTitleY + 5, 14, 3);
      x -= 26;
    }
  }

  private paintTop(ctx: CanvasRenderingContext2D, w: number, h: number): void {
    const l = layoutFor(w, h);
    const x = l.plotLeft + tickToX(this.cursor, l.plotWidth, this.cat.time.n_ticks);
    paintCursor(ctx, x, l.main.y, l.spread.y + l.spread.h);
  }
}
