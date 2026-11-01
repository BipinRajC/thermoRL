import type { Catalog } from "../schema/replay";
import { tsToTick } from "../model/time";

export const SERIES_COLOURS = ["#38bdf8", "#f472b6"] as const;

const SHADE_FILL = "rgba(148, 163, 184, 0.22)";
const FRAME = "#262b36";
const TEXT = "#9aa3b2";
const CURSOR = "#e6e9ef";
export const FONT = "11px system-ui, -apple-system, 'Segoe UI', sans-serif";

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function xToTick(x: number, width: number, nTicks: number): number {
  if (nTicks <= 1 || !(width > 0)) return 0;
  return Math.min(nTicks - 1, Math.max(0, Math.round((x / width) * (nTicks - 1))));
}

export function tickToX(k: number, width: number, nTicks: number): number {
  return nTicks <= 1 ? 0 : (k / (nTicks - 1)) * width;
}

export function shadeEndX(cat: Catalog, width: number): number {
  const n = cat.time.n_ticks;
  return tickToX(tsToTick(cat.time.eval_start_exclusive_s, n), width, n);
}

export function extent(series: ArrayLike<number>[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const s of series) {
    for (let i = 0; i < s.length; i++) {
      const v = s[i];
      if (!Number.isFinite(v)) continue;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
  }
  return lo <= hi ? [lo, hi] : [0, 1];
}

export function padRange([lo, hi]: [number, number]): [number, number] {
  if (hi - lo < 1e-9) return [lo - 0.5, hi + 0.5];
  const pad = (hi - lo) * 0.05;
  return [lo - pad, hi + pad];
}

export interface PanelSpec {
  box: Box;
  series: ArrayLike<number>[];
  range: [number, number];
  digits: number;
  nTicks: number;
  shadeEnd: number;
  shadeLabel?: string;
}

export function paintPanel(ctx: CanvasRenderingContext2D, p: PanelSpec): void {
  const { box, range } = p;
  const span = range[1] - range[0];
  const yOf = (v: number) => box.y + box.h - ((v - range[0]) / span) * box.h;
  ctx.fillStyle = SHADE_FILL;
  ctx.fillRect(box.x, box.y, p.shadeEnd, box.h);
  ctx.strokeStyle = FRAME;
  ctx.lineWidth = 1;
  ctx.strokeRect(box.x + 0.5, box.y + 0.5, box.w - 1, box.h - 1);
  ctx.font = FONT;
  ctx.fillStyle = TEXT;
  ctx.textAlign = "right";
  ctx.textBaseline = "top";
  ctx.fillText(range[1].toFixed(p.digits), box.x - 4, box.y);
  ctx.textBaseline = "bottom";
  ctx.fillText(range[0].toFixed(p.digits), box.x - 4, box.y + box.h);
  if (p.shadeLabel) {
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText(p.shadeLabel, box.x + 4, box.y + 3);
  }
  ctx.lineWidth = 1.5;
  ctx.lineJoin = "round";
  p.series.forEach((s, i) => {
    ctx.strokeStyle = SERIES_COLOURS[i % SERIES_COLOURS.length];
    ctx.beginPath();
    let pen = false;
    for (let k = 0; k < s.length; k++) {
      if (!Number.isFinite(s[k])) {
        pen = false;
        continue;
      }
      const x = box.x + tickToX(k, box.w, p.nTicks);
      if (pen) ctx.lineTo(x, yOf(s[k]));
      else ctx.moveTo(x, yOf(s[k]));
      pen = true;
    }
    ctx.stroke();
  });
}

export function paintCursor(ctx: CanvasRenderingContext2D, x: number, y0: number, y1: number): void {
  ctx.strokeStyle = CURSOR;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(Math.round(x) + 0.5, y0);
  ctx.lineTo(Math.round(x) + 0.5, y1);
  ctx.stroke();
}

export class CachedCanvas {
  private readonly base = document.createElement("canvas");
  private w = 0;
  private h = 0;
  private dpr = 1;
  private baseReady = false;
  private observer: ResizeObserver | null = null;

  constructor(
    readonly canvas: HTMLCanvasElement,
    private readonly paintBase: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
    private readonly paintTop: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
  ) {
    if (typeof ResizeObserver !== "undefined") {
      this.observer = new ResizeObserver(() => this.present());
      this.observer.observe(canvas);
    }
  }

  invalidate(): void {
    this.baseReady = false;
    this.present();
  }

  present(): void {
    const ctx = this.canvas.getContext("2d");
    if (!ctx) return;
    const rect = this.canvas.getBoundingClientRect();
    const w = Math.floor(rect.width);
    const h = Math.floor(rect.height);
    if (w < 2 || h < 2) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (w !== this.w || h !== this.h || dpr !== this.dpr) {
      this.w = w;
      this.h = h;
      this.dpr = dpr;
      this.canvas.width = this.base.width = Math.round(w * dpr);
      this.canvas.height = this.base.height = Math.round(h * dpr);
      this.baseReady = false;
    }
    if (!this.baseReady) {
      const bctx = this.base.getContext("2d");
      if (!bctx) return;
      bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      bctx.clearRect(0, 0, w, h);
      this.paintBase(bctx, w, h);
      this.baseReady = true;
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.drawImage(this.base, 0, 0);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.paintTop(ctx, w, h);
  }

  dispose(): void {
    this.observer?.disconnect();
    this.observer = null;
  }
}
