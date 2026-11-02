import { beforeEach, describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { attachSplitter, clampSize, DRAWER_MAX_SHARE, DRAWER_MIN_PX, drawerMax, HANDLE_PX, panelMin, STAGE_MIN_PX, type SplitterHandle } from "../../src/ui/splitter";

type Opts = Parameters<typeof attachSplitter>[1];

let handle: HTMLElement;
let value: number;
let setCalls: number[];

beforeEach(() => {
  document.body.innerHTML = "";
  handle = document.createElement("div");
  document.body.append(handle);
  (handle as unknown as { setPointerCapture: (id: number) => void }).setPointerCapture = () => {};
  (handle as unknown as { releasePointerCapture: (id: number) => void }).releasePointerCapture = () => {};
  value = 200;
  setCalls = [];
});

function attach(extra: Partial<Opts> = {}): SplitterHandle {
  return attachSplitter(handle, {
    axis: "x",
    get: () => value,
    set: (px) => {
      value = px;
      setCalls.push(px);
    },
    min: () => 100,
    max: () => 500,
    initial: 250,
    ...extra,
  });
}

function pointer(type: string, clientX: number, clientY = 0, id = 1, buttons?: number): void {
  const ev = new Event(type, { bubbles: true, cancelable: true }) as Event & Record<string, unknown>;
  ev.clientX = clientX;
  ev.clientY = clientY;
  ev.pointerId = id;
  if (buttons !== undefined) ev.buttons = buttons;
  handle.dispatchEvent(ev);
}

function key(k: string, shiftKey = false): KeyboardEvent {
  const ev = new KeyboardEvent("keydown", { key: k, shiftKey, bubbles: true, cancelable: true });
  handle.dispatchEvent(ev);
  return ev;
}

describe("clampSize", () => {
  test("clamps to min and max and passes values in range", () => {
    expect(clampSize(50, 100, 500)).toBe(100);
    expect(clampSize(900, 100, 500)).toBe(500);
    expect(clampSize(300, 100, 500)).toBe(300);
    expect(clampSize(100, 100, 500)).toBe(100);
    expect(clampSize(500, 100, 500)).toBe(500);
  });

  test("min wins when the range is inverted", () => {
    expect(clampSize(50, 300, 200)).toBe(300);
    expect(clampSize(900, 300, 200)).toBe(300);
  });
});

describe("attributes", () => {
  test("handle is a focusable separator with aria values", () => {
    attach();
    expect(handle.getAttribute("role")).toBe("separator");
    expect(handle.tabIndex).toBe(0);
    expect(handle.getAttribute("aria-orientation")).toBe("vertical");
    expect(handle.getAttribute("aria-valuenow")).toBe("200");
    expect(handle.getAttribute("aria-valuemin")).toBe("100");
    expect(handle.getAttribute("aria-valuemax")).toBe("500");
  });

  test("a y-axis handle is horizontal", () => {
    attach({ axis: "y" });
    expect(handle.getAttribute("aria-orientation")).toBe("horizontal");
  });
});

describe("pointer drag", () => {
  test("moves the value by the delta from the value at pointerdown", () => {
    attach();
    pointer("pointerdown", 1000);
    pointer("pointermove", 1040);
    expect(value).toBe(240);
    pointer("pointermove", 970);
    expect(value).toBe(170);
    expect(handle.getAttribute("aria-valuenow")).toBe("170");
  });

  test("clamps at min and max", () => {
    attach();
    pointer("pointerdown", 1000);
    pointer("pointermove", 5000);
    expect(value).toBe(500);
    pointer("pointermove", -5000);
    expect(value).toBe(100);
  });

  test("y axis uses clientY", () => {
    attach({ axis: "y" });
    pointer("pointerdown", 0, 400);
    pointer("pointermove", 0, 430);
    expect(value).toBe(230);
  });

  test("invert flips the direction", () => {
    attach({ invert: true });
    pointer("pointerdown", 1000);
    pointer("pointermove", 1040);
    expect(value).toBe(160);
    pointer("pointermove", 900);
    expect(value).toBe(300);
  });

  test("ignores moves without a drag", () => {
    attach();
    pointer("pointermove", 1040);
    expect(setCalls).toEqual([]);
  });

  test("pointerup ends the drag", () => {
    attach();
    pointer("pointerdown", 1000);
    pointer("pointermove", 1010);
    pointer("pointerup", 1010);
    setCalls.length = 0;
    pointer("pointermove", 1100);
    expect(setCalls).toEqual([]);
  });

  test("the handle is blurred when a pointer drag ends, so global shortcuts keep working", () => {
    attach();
    handle.focus();
    expect(document.activeElement).toBe(handle);
    pointer("pointerdown", 1000);
    pointer("pointermove", 1010);
    pointer("pointerup", 1010);
    expect(document.activeElement).not.toBe(handle);
  });

  test("the handle is blurred after a pointercancel and a click without movement", () => {
    attach();
    handle.focus();
    pointer("pointerdown", 1000);
    pointer("pointercancel", 1000);
    expect(document.activeElement).not.toBe(handle);
    handle.focus();
    pointer("pointerdown", 1000);
    pointer("pointerup", 1000);
    expect(document.activeElement).not.toBe(handle);
  });

  test("keyboard use keeps the focus on the handle", () => {
    attach();
    handle.focus();
    key("ArrowLeft");
    key("Home");
    expect(document.activeElement).toBe(handle);
  });

  test("pointercancel ends the drag", () => {
    attach();
    pointer("pointerdown", 1000);
    pointer("pointercancel", 1000);
    pointer("pointermove", 1100);
    expect(setCalls).toEqual([]);
  });

  test("lostpointercapture ends the drag", () => {
    attach();
    pointer("pointerdown", 1000);
    pointer("lostpointercapture", 1000);
    pointer("pointermove", 1100);
    expect(setCalls).toEqual([]);
  });

  test("a second drag starts from the current value", () => {
    attach();
    pointer("pointerdown", 1000);
    pointer("pointermove", 1050);
    pointer("pointerup", 1050);
    pointer("pointerdown", 300);
    pointer("pointermove", 310);
    expect(value).toBe(260);
  });

  test("captures the pointer on pointerdown and releases on end", () => {
    const seen: string[] = [];
    (handle as unknown as { setPointerCapture: (id: number) => void }).setPointerCapture = (id) => seen.push(`set${id}`);
    (handle as unknown as { releasePointerCapture: (id: number) => void }).releasePointerCapture = (id) => seen.push(`rel${id}`);
    attach();
    pointer("pointerdown", 0, 0, 7);
    pointer("pointerup", 0, 0, 7);
    expect(seen).toEqual(["set7", "rel7"]);
  });

  test("a throwing setPointerCapture does not break the drag", () => {
    (handle as unknown as { setPointerCapture: () => void }).setPointerCapture = () => {
      throw new Error("no such pointer");
    };
    attach();
    pointer("pointerdown", 1000);
    pointer("pointermove", 1020);
    expect(value).toBe(220);
  });

  test("moves of another pointer are ignored", () => {
    attach();
    pointer("pointerdown", 1000, 0, 1);
    pointer("pointermove", 1100, 0, 2);
    expect(setCalls).toEqual([]);
  });
});

describe("keyboard", () => {
  test("arrows move by the default 16 px step", () => {
    attach();
    key("ArrowRight");
    expect(value).toBe(216);
    key("ArrowLeft");
    key("ArrowLeft");
    expect(value).toBe(184);
  });

  test("a custom step is honoured and Shift is four times larger", () => {
    attach({ step: 10 });
    key("ArrowRight");
    expect(value).toBe(210);
    key("ArrowRight", true);
    expect(value).toBe(250);
  });

  test("keys are clamped", () => {
    attach();
    value = 495;
    key("ArrowRight");
    expect(value).toBe(500);
    value = 105;
    key("ArrowLeft", true);
    expect(value).toBe(100);
  });

  test("Home and End jump to min and max", () => {
    attach();
    key("End");
    expect(value).toBe(500);
    expect(handle.getAttribute("aria-valuenow")).toBe("500");
    key("Home");
    expect(value).toBe(100);
  });

  test("y axis uses Up and Down; x axis ignores them", () => {
    attach({ axis: "y" });
    key("ArrowDown");
    expect(value).toBe(216);
    key("ArrowUp");
    expect(value).toBe(200);
    key("ArrowRight");
    expect(value).toBe(200);
  });

  test("x axis ignores Up and Down", () => {
    attach();
    key("ArrowUp");
    key("ArrowDown");
    expect(setCalls).toEqual([]);
  });

  test("invert flips arrow direction so the handle moves the way the arrow points", () => {
    attach({ invert: true });
    key("ArrowLeft");
    expect(value).toBe(216);
    key("ArrowRight");
    expect(value).toBe(200);
  });

  test("handled keys are default-prevented and other keys are not", () => {
    attach();
    expect(key("ArrowRight").defaultPrevented).toBe(true);
    expect(key("Home").defaultPrevented).toBe(true);
    expect(key("a").defaultPrevented).toBe(false);
    expect(key("Tab").defaultPrevented).toBe(false);
  });
});

describe("double click", () => {
  test("resets to the initial value", () => {
    attach();
    value = 400;
    handle.dispatchEvent(new Event("dblclick", { bubbles: true }));
    expect(value).toBe(250);
    expect(handle.getAttribute("aria-valuenow")).toBe("250");
  });

  test("initial may be a function evaluated at reset time", () => {
    let want = 250;
    attach({ initial: () => want });
    want = 321;
    handle.dispatchEvent(new Event("dblclick", { bubbles: true }));
    expect(value).toBe(321);
  });
});

describe("dispose", () => {
  test("removes every listener", () => {
    const dispose = attach();
    pointer("pointerdown", 1000);
    dispose();
    setCalls.length = 0;
    pointer("pointermove", 1100);
    key("ArrowRight");
    key("End");
    handle.dispatchEvent(new Event("dblclick", { bubbles: true }));
    pointer("pointerdown", 0);
    pointer("pointermove", 50);
    expect(setCalls).toEqual([]);
  });

  test("is idempotent", () => {
    const dispose = attach();
    dispose();
    expect(() => dispose()).not.toThrow();
  });
});

describe("key events stay on the handle", () => {
  test("handled keys stop propagating; unhandled keys still bubble", () => {
    attach();
    const seen: string[] = [];
    const onKey = (e: KeyboardEvent): void => void seen.push(e.key);
    document.body.addEventListener("keydown", onKey);
    window.addEventListener("keydown", onKey);
    for (const k of ["ArrowLeft", "ArrowRight", "Home", "End"]) key(k);
    expect(seen).toEqual([]);
    key("a");
    key(" ");
    expect(seen).toEqual(["a", "a", " ", " "]);
    document.body.removeEventListener("keydown", onKey);
    window.removeEventListener("keydown", onKey);
  });

  test("keys for the other axis keep bubbling", () => {
    attach();
    const seen: string[] = [];
    const onKey = (e: KeyboardEvent): void => void seen.push(e.key);
    document.body.addEventListener("keydown", onKey);
    key("ArrowUp");
    expect(seen).toEqual(["ArrowUp"]);
    document.body.removeEventListener("keydown", onKey);
  });
});

describe("drag robustness", () => {
  test("a move with no button pressed ends the drag even if capture failed", () => {
    (handle as unknown as { setPointerCapture: () => void }).setPointerCapture = () => {
      throw new Error("no such pointer");
    };
    attach();
    pointer("pointerdown", 1000, 0, 1, 1);
    pointer("pointermove", 1020, 0, 1, 1);
    expect(value).toBe(220);
    pointer("pointermove", 1100, 0, 1, 0);
    expect(value).toBe(220);
    pointer("pointermove", 1200, 0, 1, 1);
    expect(value).toBe(220);
  });

  test("a second pointer's pointerdown is ignored while dragging", () => {
    attach();
    pointer("pointerdown", 1000, 0, 1);
    pointer("pointerdown", 2000, 0, 2);
    pointer("pointermove", 1040, 0, 1);
    expect(value).toBe(240);
    pointer("pointermove", 2100, 0, 2);
    expect(value).toBe(240);
    pointer("pointerup", 2100, 0, 2);
    pointer("pointermove", 1060, 0, 1);
    expect(value).toBe(260);
  });

  test("a second pointer cannot capture, release or restart the drag", () => {
    const seen: string[] = [];
    (handle as unknown as { setPointerCapture: (id: number) => void }).setPointerCapture = (id) => seen.push(`set${id}`);
    attach();
    pointer("pointerdown", 1000, 0, 1);
    pointer("pointerdown", 2000, 0, 2);
    expect(seen).toEqual(["set1"]);
  });

  test("dispose in the middle of a drag releases the pointer capture", () => {
    const seen: string[] = [];
    (handle as unknown as { releasePointerCapture: (id: number) => void }).releasePointerCapture = (id) => seen.push(`rel${id}`);
    const dispose = attach();
    pointer("pointerdown", 1000, 0, 5);
    dispose();
    expect(seen).toEqual(["rel5"]);
  });

  test("dispose without a drag releases nothing", () => {
    const seen: string[] = [];
    (handle as unknown as { releasePointerCapture: (id: number) => void }).releasePointerCapture = (id) => seen.push(`rel${id}`);
    attach()();
    expect(seen).toEqual([]);
  });
});

describe("reclamp", () => {
  test("pulls an out-of-range value back inside and refreshes aria", () => {
    const s = attach();
    value = 700;
    s.reclamp();
    expect(value).toBe(500);
    expect(handle.getAttribute("aria-valuenow")).toBe("500");
    value = 40;
    s.reclamp();
    expect(value).toBe(100);
  });

  test("does not call set when the value is already in range", () => {
    const s = attach();
    s.reclamp();
    expect(setCalls).toEqual([]);
  });

  test("follows shrinking bounds", () => {
    let hi = 500;
    const s = attach({ max: () => hi });
    value = 400;
    hi = 300;
    s.reclamp();
    expect(value).toBe(300);
    expect(handle.getAttribute("aria-valuemax")).toBe("300");
  });

  test("a size of zero (not laid out / hidden) is left alone", () => {
    const s = attach();
    value = 0;
    s.reclamp();
    expect(setCalls).toEqual([]);
  });

  test("is still a plain dispose function", () => {
    const s = attach();
    expect(typeof s).toBe("function");
    s();
    value = 700;
    s.reclamp();
    expect(setCalls).toEqual([]);
  });
});

describe("aria-valuetext", () => {
  test("is a percentage of the total when a total is given", () => {
    attach({ total: () => 800 });
    expect(handle.getAttribute("aria-valuetext")).toBe("25%");
    key("End");
    expect(handle.getAttribute("aria-valuetext")).toBe("63%");
  });

  test("is absent without a total", () => {
    attach();
    expect(handle.hasAttribute("aria-valuetext")).toBe(false);
  });

  test("refresh() re-reads the current size", () => {
    const s = attach();
    value = 321;
    s.refresh();
    expect(handle.getAttribute("aria-valuenow")).toBe("321");
  });

  test("pointerenter refreshes stale values", () => {
    attach();
    value = 333;
    handle.dispatchEvent(new Event("pointerenter"));
    expect(handle.getAttribute("aria-valuenow")).toBe("333");
  });
});

describe("drawerMax", () => {
  test("keeps STAGE_MIN_PX for the stage, capped at 70% and floored at the drawer minimum", () => {
    expect(STAGE_MIN_PX).toBe(640);
    expect(DRAWER_MIN_PX).toBe(300);
    expect(DRAWER_MAX_SHARE).toBe(0.7);
    expect(HANDLE_PX).toBe(8);
    expect(drawerMax(1440)).toBe(792);
    expect(drawerMax(1000)).toBe(352);
    expect(drawerMax(800)).toBe(300);
    expect(drawerMax(0)).toBe(300);
  });

  test("the stage (body minus drawer minus handle) is never below STAGE_MIN_PX once the floor does not apply", () => {
    for (const body of [960, 1000, 1280, 1440, 1920]) expect(body - drawerMax(body) - HANDLE_PX).toBeGreaterThanOrEqual(STAGE_MIN_PX);
  });

  test("uses the 70% share on very wide windows", () => {
    expect(drawerMax(4000)).toBe(2800);
    expect(drawerMax(2000)).toBe(1352);
  });

  test("CSS fallback values match the exported constants", () => {
    const css = readFileSync("src/style.css", "utf8");
    expect(css).toContain(`max-width: max(var(--drawer-min, ${DRAWER_MIN_PX}px), min(${DRAWER_MAX_SHARE * 100}%, calc(100% - var(--stage-min, ${STAGE_MIN_PX}px) - var(--splitter-w, ${HANDLE_PX}px))))`);
  });
});

describe("panelMin", () => {
  test("keeps at least a 120 px grid beside the 132 px legend, never more than half", () => {
    expect(panelMin(610)).toBeGreaterThanOrEqual(132 + 8 + 120);
    expect(panelMin(920)).toBeGreaterThanOrEqual(132 + 8 + 120);
    expect(panelMin(400)).toBe(200);
    expect(panelMin(2000)).toBe(400);
  });
});
