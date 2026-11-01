import { cellOf } from "../scene/rackGrid";
import type { LoadedRun } from "../data/loader";
import { rackFree, rackKw, rackTc } from "../data/views";
import { scaleSide, type Scale } from "../model/colour";
import type { Catalog } from "../schema/replay";

export const escapeHtml = (s: string): string =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

export function rackTitle(r: number, grid: Catalog["grid"]): string {
  const { row, col } = cellOf(r, grid.cols);
  return `Rack ${r} (row ${row}, col ${col})`;
}

function activeValue(run: LoadedRun, k: number, r: number, scale: Scale, cat: Catalog): number {
  if (scale.unit === "kW") return rackKw(run, k, r);
  if (scale.unit === "nodes") return cat.grid.nodes_per_rack - rackFree(run, k, r);
  return rackTc(run, k, r);
}

export function tooltipHtml(run: LoadedRun, k: number, r: number, scale: Scale, cat: Catalog): string {
  const side = scaleSide(activeValue(run, k, r, scale, cat), scale);
  const rows = [
    `<div class="tip-title">${escapeHtml(rackTitle(r, cat.grid))}</div>`,
    `<div>Modelled coolant ${rackTc(run, k, r).toFixed(2)} °C</div>`,
    `<div>Rack power ${rackKw(run, k, r).toFixed(1)} kW</div>`,
    `<div>Free nodes ${rackFree(run, k, r)} / ${cat.grid.nodes_per_rack}</div>`,
  ];
  if (side !== 0) rows.push(`<div class="tip-out">outside scale (${side > 0 ? "above" : "below"})</div>`);
  rows.push(`<div class="tip-note">${escapeHtml(cat.strings.interval_semantics)}</div>`);
  return rows.join("");
}

export function placeTooltip(el: HTMLElement, clientX: number, clientY: number): void {
  const gap = 14;
  const { width, height } = el.getBoundingClientRect();
  const x = clientX + gap + width > window.innerWidth ? clientX - gap - width : clientX + gap;
  const y = clientY + gap + height > window.innerHeight ? clientY - gap - height : clientY + gap;
  el.style.left = `${Math.max(0, x)}px`;
  el.style.top = `${Math.max(0, y)}px`;
}
