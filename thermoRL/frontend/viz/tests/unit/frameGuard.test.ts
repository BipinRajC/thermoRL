import { expect, test, vi } from "vitest";
import { guardedFrame } from "../../src/model/frameGuard";
import { Status } from "../../src/ui/status";

test("re-arms before drawing, so a throwing draw cannot stop the loop", () => {
  const order: string[] = [];
  const frame = guardedFrame(
    () => {
      order.push("draw");
      throw new RangeError("Offset is outside the bounds of the DataView");
    },
    () => order.push("rearm"),
    () => order.push("error"),
  );
  expect(() => frame(0)).not.toThrow();
  expect(order).toEqual(["rearm", "draw", "error"]);
});

test("reports once per distinct error message", () => {
  let n = 0;
  const messages = ["a", "a", "a", "b", "a", "b"];
  const onError = vi.fn();
  const rearm = vi.fn();
  const frame = guardedFrame(() => {
    throw new RangeError(messages[n++]);
  }, rearm, onError);
  for (let i = 0; i < messages.length; i++) frame(i);
  expect(rearm).toHaveBeenCalledTimes(6);
  expect(onError.mock.calls.map(([e]) => (e as Error).message)).toEqual(["a", "b"]);
});

test("a successful frame resets the report memory", () => {
  let fail = true;
  const onError = vi.fn();
  const frame = guardedFrame(() => {
    if (fail) throw new Error("x");
  }, () => {}, onError);
  frame(0);
  frame(1);
  fail = false;
  frame(2);
  fail = true;
  frame(3);
  expect(onError).toHaveBeenCalledTimes(2);
});

test("non-Error throws are reported too", () => {
  const onError = vi.fn();
  const frame = guardedFrame(() => {
    throw "boom";
  }, () => {}, onError);
  frame(0);
  frame(1);
  expect(onError).toHaveBeenCalledTimes(1);
  expect(onError).toHaveBeenCalledWith("boom");
});

test("the status error panel shows the exception message", () => {
  const el = document.createElement("div");
  const status = new Status(el);
  const frame = guardedFrame(() => {
    throw new RangeError("Offset is outside the bounds of the DataView");
  }, () => {}, (e) => status.error(e));
  frame(0);
  expect(el.hidden).toBe(false);
  expect(el.getAttribute("role")).toBe("alert");
  expect(el.textContent).toContain("Offset is outside the bounds of the DataView");
});
