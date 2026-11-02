export interface SplitterOptions {
  axis: "x" | "y";
  get(): number;
  set(px: number): void;
  min(): number;
  max(): number;
  initial: number | (() => number);
  step?: number;
  invert?: boolean;
  total?(): number;
}

export type SplitterHandle = (() => void) & { reclamp(): void; refresh(): void };

export function clampSize(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(v, max));
}

export const STAGE_MIN_PX = 640;
export const DRAWER_MIN_PX = 300;
export const DRAWER_MAX_SHARE = 0.7;
const PANEL_MIN_SHARE = 0.2;
const PANEL_MIN_PX = 264;

export function drawerMax(bodyWidth: number): number {
  return Math.max(DRAWER_MIN_PX, Math.min(bodyWidth * DRAWER_MAX_SHARE, bodyWidth - STAGE_MIN_PX));
}

export function panelMin(panelsTotal: number): number {
  return Math.min(panelsTotal / 2, Math.max(panelsTotal * PANEL_MIN_SHARE, PANEL_MIN_PX));
}

const DEFAULT_STEP = 16;

export function attachSplitter(handle: HTMLElement, opts: SplitterOptions): SplitterHandle {
  const step = opts.step ?? DEFAULT_STEP;
  const sign = opts.invert ? -1 : 1;
  let drag: { id: number; origin: number; start: number } | null = null;
  let disposed = false;

  const bounds = (): [number, number] => [opts.min(), opts.max()];

  const refresh = (): void => {
    const [lo, hi] = bounds();
    const now = opts.get();
    handle.setAttribute("aria-valuenow", String(Math.round(now)));
    handle.setAttribute("aria-valuemin", String(Math.round(lo)));
    handle.setAttribute("aria-valuemax", String(Math.round(hi)));
    const total = opts.total?.() ?? 0;
    if (total > 0) handle.setAttribute("aria-valuetext", `${Math.round((now / total) * 100)}%`);
  };

  const reclamp = (): void => {
    if (disposed) return;
    const now = opts.get();
    if (!(now > 0)) return;
    const [lo, hi] = bounds();
    const next = clampSize(now, lo, hi);
    if (Math.abs(next - now) >= 0.5) opts.set(next);
    refresh();
  };

  const apply = (v: number): void => {
    const [lo, hi] = bounds();
    opts.set(clampSize(v, lo, hi));
    refresh();
  };

  const coord = (e: PointerEvent): number => (opts.axis === "x" ? e.clientX : e.clientY);

  const release = (id: number): void => {
    try {
      handle.releasePointerCapture(id);
    } catch {
      /* capture already gone */
    }
  };

  const stop = (): void => {
    if (!drag) return;
    const id = drag.id;
    drag = null;
    release(id);
  };

  const end = (e: PointerEvent): void => {
    if (drag && e.pointerId === drag.id) stop();
  };

  const onDown = (e: PointerEvent): void => {
    if (e.button) return;
    if (drag && e.pointerId !== drag.id) return;
    drag = { id: e.pointerId, origin: coord(e), start: opts.get() };
    try {
      handle.setPointerCapture(e.pointerId);
    } catch {
      /* synthetic or already-released pointer */
    }
    refresh();
  };

  const onMove = (e: PointerEvent): void => {
    if (!drag || e.pointerId !== drag.id) return;
    if (e.buttons === 0) {
      stop();
      return;
    }
    apply(drag.start + sign * (coord(e) - drag.origin));
  };

  const onKey = (e: KeyboardEvent): void => {
    const back = opts.axis === "x" ? "ArrowLeft" : "ArrowUp";
    const fwd = opts.axis === "x" ? "ArrowRight" : "ArrowDown";
    const amount = step * (e.shiftKey ? 4 : 1);
    if (e.key === back) apply(opts.get() - sign * amount);
    else if (e.key === fwd) apply(opts.get() + sign * amount);
    else if (e.key === "Home") apply(bounds()[0]);
    else if (e.key === "End") apply(bounds()[1]);
    else return;
    e.preventDefault();
    e.stopPropagation();
  };

  const onDouble = (): void => {
    apply(typeof opts.initial === "function" ? opts.initial() : opts.initial);
  };

  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-orientation", opts.axis === "x" ? "vertical" : "horizontal");
  handle.tabIndex = 0;
  refresh();

  handle.addEventListener("pointerdown", onDown);
  handle.addEventListener("pointermove", onMove);
  handle.addEventListener("pointerup", end);
  handle.addEventListener("pointercancel", end);
  handle.addEventListener("lostpointercapture", end);
  handle.addEventListener("keydown", onKey);
  handle.addEventListener("dblclick", onDouble);
  handle.addEventListener("focus", refresh);
  handle.addEventListener("pointerenter", refresh);

  const dispose = (): void => {
    if (disposed) return;
    disposed = true;
    stop();
    handle.removeEventListener("pointerdown", onDown);
    handle.removeEventListener("pointermove", onMove);
    handle.removeEventListener("pointerup", end);
    handle.removeEventListener("pointercancel", end);
    handle.removeEventListener("lostpointercapture", end);
    handle.removeEventListener("keydown", onKey);
    handle.removeEventListener("dblclick", onDouble);
    handle.removeEventListener("focus", refresh);
    handle.removeEventListener("pointerenter", refresh);
  };
  return Object.assign(dispose, { reclamp, refresh });
}
