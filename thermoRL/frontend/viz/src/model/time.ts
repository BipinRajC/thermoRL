import type { Catalog } from "../schema/replay";

const TICK_S = 10;

export const WINDOW_LABEL_BEFORE = "before evaluation window (t ≤ 1 h)";
export const WINDOW_LABEL_EVAL = "evaluation window (1 h < t ≤ 6 h)";

export const tickToTs = (k: number): number => TICK_S * (k + 1);

export const tsToTick = (t_s: number, nTicks: number): number =>
  Math.min(nTicks - 1, Math.max(0, Math.floor(t_s / TICK_S) - 1));

export const windowState = (t_s: number, cat: Catalog): "before" | "evaluation" =>
  t_s > cat.time.eval_start_exclusive_s ? "evaluation" : "before";

export const windowLabel = (t_s: number, cat: Catalog): string =>
  windowState(t_s, cat) === "evaluation" ? WINDOW_LABEL_EVAL : WINDOW_LABEL_BEFORE;

export function formatClock(t_s: number): string {
  const s = Math.max(0, Math.floor(t_s));
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
}

export const pulseBounds = (t_s: number, cat: Catalog): [loExclusive: number, hiInclusive: number] => [
  Math.max(-1, t_s - cat.time.pulse_window_s),
  t_s,
];
