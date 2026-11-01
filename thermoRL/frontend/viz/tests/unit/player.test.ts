import { expect, test, vi } from "vitest";
import { Player, SPEEDS } from "../../src/replay/player";

test("defaults and speeds", () => {
  const p = new Player(100);
  expect(p.tick).toBe(0);
  expect(p.playing).toBe(false);
  expect(p.speed).toBe(10);
  expect([...SPEEDS]).toEqual([1, 2, 5, 10, 30, 60]);
});

test("advance accumulates whole ticks and keeps the remainder", () => {
  const p = new Player(100);
  expect(p.advance(100)).toBe(true);
  expect(p.tick).toBe(1);
  expect(p.advance(250)).toBe(true);
  expect(p.advance(250)).toBe(true);
  expect(p.tick).toBe(6);
  expect(p.advance(50)).toBe(false);
  expect(p.tick).toBe(6);
  expect(p.advance(50)).toBe(true);
  expect(p.tick).toBe(7);
});

test("advance honours speed", () => {
  const p = new Player(1000);
  p.speed = 60;
  p.advance(1000);
  expect(p.tick).toBe(60);
});

test("seek clamps to the tick range", () => {
  const p = new Player(100);
  p.seek(-3);
  expect(p.tick).toBe(0);
  p.seek(1e9);
  expect(p.tick).toBe(99);
  p.seek(42);
  expect(p.tick).toBe(42);
});

test("step moves relatively and clamps", () => {
  const p = new Player(100);
  p.seek(30);
  p.step(6);
  expect(p.tick).toBe(36);
  p.seek(30);
  p.step(-60);
  expect(p.tick).toBe(0);
  p.step(1e9);
  expect(p.tick).toBe(99);
});

test("playing past the end stops at the last tick", () => {
  const p = new Player(10);
  p.playing = true;
  p.seek(8);
  expect(p.advance(5000)).toBe(true);
  expect(p.tick).toBe(9);
  expect(p.playing).toBe(false);
  expect(p.advance(1000)).toBe(false);
  expect(p.tick).toBe(9);
});

test("remainder does not carry into a restart after reaching the end", () => {
  const p = new Player(10);
  p.playing = true;
  p.seek(8);
  p.advance(250);
  expect(p.tick).toBe(9);
  expect(p.playing).toBe(false);
  p.seek(0);
  p.playing = true;
  p.advance(50);
  expect(p.tick).toBe(0);
});

test("onChange fires once per actual change", () => {
  const p = new Player(100);
  const fn = vi.fn();
  p.onChange(fn);
  p.seek(0);
  p.step(0);
  p.step(-1);
  p.advance(50);
  expect(fn).not.toHaveBeenCalled();
  p.seek(5);
  expect(fn).toHaveBeenCalledTimes(1);
  expect(fn).toHaveBeenLastCalledWith(5);
  p.seek(5);
  expect(fn).toHaveBeenCalledTimes(1);
  p.step(2);
  expect(fn).toHaveBeenCalledTimes(2);
  expect(fn).toHaveBeenLastCalledWith(7);
  p.advance(300);
  expect(fn).toHaveBeenCalledTimes(3);
  expect(fn).toHaveBeenLastCalledWith(10);
  p.seek(1e9);
  p.seek(1e9);
  expect(fn).toHaveBeenCalledTimes(4);
});

test("onChange returns an unsubscribe function", () => {
  const p = new Player(100);
  const fn = vi.fn();
  const off = p.onChange(fn);
  p.seek(3);
  off();
  p.seek(4);
  expect(fn).toHaveBeenCalledTimes(1);
});
