import type { Scale } from "../model/colour";
import { COPY, LEGEND_NOTE } from "./copy";

const GRADIENT_STOPS = 32;
const rendered = new WeakMap<HTMLElement, { lut: Float32Array; key: string }>();

const part = (tag: "div" | "span", className: string, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

function gradient(lut: Float32Array): string {
  const stops: string[] = [];
  for (let i = 0; i <= GRADIENT_STOPS; i++) {
    const idx = Math.round((i / GRADIENT_STOPS) * 255);
    const [r, g, b] = [0, 1, 2].map((c) => Math.round(lut[idx * 3 + c] * 255));
    stops.push(`rgb(${r}, ${g}, ${b}) ${((i / GRADIENT_STOPS) * 100).toFixed(1)}%`);
  }
  return `linear-gradient(to top, ${stops.join(", ")})`;
}

export function renderLegend(el: HTMLElement, scale: Scale, lut: Float32Array, outOfRange: { below: number; above: number }): void {
  const n = outOfRange.below + outOfRange.above;
  const key = [scale.min, scale.max, scale.unit, scale.label, n].join("|");
  const prev = rendered.get(el);
  if (prev && prev.lut === lut && prev.key === key) return;
  rendered.set(el, { lut, key });

  const bar = part("div", "legend-bar");
  bar.style.background = gradient(lut);
  const ends = part("div", "legend-ends");
  ends.append(part("span", "legend-max", `${scale.max.toFixed(2)} ${scale.unit}`), part("span", "legend-min", `${scale.min.toFixed(2)} ${scale.unit}`));
  const ramp = part("div", "legend-ramp");
  ramp.append(bar, ends);
  const children: HTMLElement[] = [ramp, part("div", "legend-label", scale.label), part("div", "legend-note", LEGEND_NOTE)];
  if (n > 0) children.push(part("div", "legend-out", COPY.legend.outOfRange(n)));
  el.replaceChildren(...children);
}
