import type { LoadedRun } from "../data/loader";
import { rackKw, rackTc } from "../data/views";
import type { Catalog } from "../schema/replay";
import { COPY } from "./copy";
import { CachedCanvas, SERIES_COLOURS, extent, padRange, paintCursor, paintPanel, shadeEndX, tickToX } from "./plot";
import { rackTitle } from "./tooltip";

export interface Sparkline {
  setCursor(k: number): void;
  dispose(): void;
}

const LABEL_W = 40;
const PAD = 6;

const node = <K extends keyof HTMLElementTagNameMap>(tag: K, className: string, text = "") => {
  const n = document.createElement(tag);
  n.className = className;
  n.textContent = text;
  return n;
};

const column = (run: LoadedRun, r: number, n: number, read: typeof rackTc): Float64Array => {
  const out = new Float64Array(n);
  for (let k = 0; k < n; k++) out[k] = read(run, k, r);
  return out;
};

export function renderSparkline(el: HTMLElement, left: LoadedRun, right: LoadedRun, r: number, cat: Catalog): Sparkline {
  const n = cat.time.n_ticks;
  const title = rackTitle(r, cat.grid);
  const legend = node("div", "spark-legend");
  [left, right].forEach((run, i) => {
    const item = node("span", "spark-key");
    const swatch = node("span", "spark-swatch");
    swatch.style.background = SERIES_COLOURS[i];
    item.append(swatch, run.meta.policy);
    legend.append(item);
  });
  const panels = [
    { caption: COPY.rack.coolant, read: rackTc, digits: 2 },
    { caption: COPY.rack.power, read: rackKw, digits: 1 },
  ].map((spec) => {
    const series = [column(left, r, n, spec.read), column(right, r, n, spec.read)];
    const canvas = node("canvas", "spark-canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", `${title}: ${spec.caption}`);
    let cursor = 0;
    const box = (w: number, h: number) => ({ x: LABEL_W, y: PAD, w: Math.max(1, w - LABEL_W - PAD), h: Math.max(8, h - 2 * PAD) });
    const view = new CachedCanvas(
      canvas,
      (ctx, w, h) => {
        const b = box(w, h);
        paintPanel(ctx, { box: b, series, range: padRange(extent(series)), digits: spec.digits, nTicks: n, shadeEnd: shadeEndX(cat, b.w) });
      },
      (ctx, w, h) => {
        const b = box(w, h);
        paintCursor(ctx, b.x + tickToX(cursor, b.w, n), b.y, b.y + b.h);
      },
    );
    return { caption: spec.caption, canvas, view, setCursor: (k: number) => (cursor = k) };
  });

  const head = node("h2", "drawer-title", title);
  const sections = panels.map((p) => {
    const section = node("div", "spark-section");
    section.append(node("h3", "spark-caption", p.caption), p.canvas);
    return section;
  });
  el.replaceChildren(head, legend, ...sections, node("p", "spark-note", COPY.rack.shadeNote));
  panels.forEach((p) => p.view.invalidate());

  let shown = -1;
  return {
    setCursor(k) {
      if (k === shown) return;
      shown = k;
      for (const p of panels) {
        p.setCursor(k);
        p.view.present();
      }
    },
    dispose() {
      for (const p of panels) p.view.dispose();
    },
  };
}
