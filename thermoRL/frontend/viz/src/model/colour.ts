import type { Catalog } from "../schema/replay";
import type { LoadedRun } from "../data/loader";

export type Overlay = "tc" | "kw" | "occupied";

export interface Scale {
  min: number;
  max: number;
  unit: string;
  label: string;
  overlay: Overlay;
}

export const F32_SLACK = 5e-6;

export const TC_LABEL = "Modelled coolant °C";
export const KW_LABEL = "Rack power kW (RAPS input over the interval ending at t)";
export const occupiedLabel = (nodesPerRack: number) => `Occupied nodes (${nodesPerRack} − free)`;

export function scaleFor(overlay: Overlay, cat: Catalog, seed: number): Scale {
  if (overlay === "tc") {
    const entry = cat.seeds.find((s) => s.seed === seed);
    if (!entry) throw new Error(`No colour scale for seed ${seed}`);
    return { min: entry.colour_scale_c.min, max: entry.colour_scale_c.max, unit: "°C", label: TC_LABEL, overlay };
  }
  if (overlay === "kw") {
    return { min: cat.rack_kw_range.idle_kw, max: cat.rack_kw_range.peak_kw, unit: "kW", label: KW_LABEL, overlay };
  }
  const n = cat.grid.nodes_per_rack;
  return { min: 0, max: n, unit: "nodes", label: occupiedLabel(n), overlay };
}

export function lutToRgb(lut: string[]): Float32Array {
  if (lut.length !== 256) throw new Error(`Colour LUT must have 256 entries, got ${lut.length}`);
  const out = new Float32Array(256 * 3);
  lut.forEach((hex, i) => {
    if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`Bad LUT colour "${hex}" at ${i}`);
    for (let c = 0; c < 3; c++) out[i * 3 + c] = parseInt(hex.slice(1 + 2 * c, 3 + 2 * c), 16) / 255;
  });
  return out;
}

export function scaleSide(v: number, s: Scale): -1 | 0 | 1 {
  if (Number.isNaN(v) || v < s.min - F32_SLACK) return -1;
  return v > s.max + F32_SLACK ? 1 : 0;
}

export function mapValue(v: number, s: Scale, lut: Float32Array, out: Float32Array, offset: number): -1 | 0 | 1 {
  const code = scaleSide(v, s);
  const span = s.max - s.min;
  const idx =
    code < 0 ? 0 : code > 0 ? 255 : span > 0 ? Math.min(255, Math.max(0, Math.round(((v - s.min) / span) * 255))) : 0;
  out[offset] = lut[idx * 3];
  out[offset + 1] = lut[idx * 3 + 1];
  out[offset + 2] = lut[idx * 3 + 2];
  return code;
}

export function frameColours(
  run: LoadedRun,
  k: number,
  overlay: Overlay,
  scale: Scale,
  lut: Float32Array,
  out: Float32Array,
): { below: number; above: number } {
  const n = run.meta.n_racks;
  const base = k * n;
  const nodes = overlay === "occupied" ? scale.max : 0;
  let below = 0;
  let above = 0;
  for (let r = 0; r < n; r++) {
    const v = overlay === "tc" ? run.tc[base + r] : overlay === "kw" ? run.kw[base + r] : nodes - run.free[base + r];
    const code = mapValue(v, scale, lut, out, r * 3);
    if (code < 0) below++;
    else if (code > 0) above++;
  }
  return { below, above };
}
