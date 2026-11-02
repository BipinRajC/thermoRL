export interface SplitterOptions {
  axis: "x" | "y";
  get(): number;
  set(px: number): void;
  min(): number;
  max(): number;
  initial: number | (() => number);
  step?: number;
  invert?: boolean;
}

export function clampSize(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(v, max));
}

const DEFAULT_STEP = 16;

export function attachSplitter(handle: HTMLElement, opts: SplitterOptions): () => void {
  const step = opts.step ?? DEFAULT_STEP;
  const sign = opts.invert ? -1 : 1;
  let drag: { id: number; origin: number; start: number } | null = null;

  const bounds = (): [number, number] => [opts.min(), opts.max()];

  const refresh = (): void => {
    const [lo, hi] = bounds();
    handle.setAttribute("aria-valuenow", String(Math.round(opts.get())));
    handle.setAttribute("aria-valuemin", String(Math.round(lo)));
    handle.setAttribute("aria-valuemax", String(Math.round(hi)));
  };

  const apply = (v: number): void => {
    const [lo, hi] = bounds();
    opts.set(clampSize(v, lo, hi));
    refresh();
  };

  const coord = (e: PointerEvent): number => (opts.axis === "x" ? e.clientX : e.clientY);

  const end = (e: PointerEvent): void => {
    if (!drag || e.pointerId !== drag.id) return;
    const id = drag.id;
    drag = null;
    try {
      handle.releasePointerCapture(id);
    } catch {
      /* capture already gone */
    }
  };

  const onDown = (e: PointerEvent): void => {
    if (e.button) return;
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

  return () => {
    handle.removeEventListener("pointerdown", onDown);
    handle.removeEventListener("pointermove", onMove);
    handle.removeEventListener("pointerup", end);
    handle.removeEventListener("pointercancel", end);
    handle.removeEventListener("lostpointercapture", end);
    handle.removeEventListener("keydown", onKey);
    handle.removeEventListener("dblclick", onDouble);
    handle.removeEventListener("focus", refresh);
    drag = null;
  };
}
