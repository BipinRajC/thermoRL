import { beforeEach, describe, expect, test } from "vitest";
import { attachSplitter, clampSize } from "../../src/ui/splitter";

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

function attach(extra: Partial<Opts> = {}): () => void {
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

function pointer(type: string, clientX: number, clientY = 0, id = 1): void {
  const ev = new Event(type, { bubbles: true, cancelable: true }) as Event & Record<string, unknown>;
  ev.clientX = clientX;
  ev.clientY = clientY;
  ev.pointerId = id;
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
