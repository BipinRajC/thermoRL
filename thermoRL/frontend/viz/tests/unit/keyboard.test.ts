import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { Catalog } from "../../src/schema/replay";
import { Player } from "../../src/replay/player";
import { installKeyboard, type Controls } from "../../src/ui/controls";

const cat = { time: { tick_s: 10 } } as unknown as Catalog;

let player: Player;
let togglePlay: ReturnType<typeof vi.fn>;
let dispose: () => void;

beforeEach(() => {
  document.body.innerHTML = "";
  player = new Player(400);
  player.seek(100);
  togglePlay = vi.fn();
  dispose = installKeyboard(
    () => ({ togglePlay }) as unknown as Controls,
    () => player,
    () => cat,
  );
});

afterEach(() => dispose());

function press(target: EventTarget, key: string, shiftKey = false): KeyboardEvent {
  const ev = new KeyboardEvent("keydown", { key, shiftKey, bubbles: true, cancelable: true });
  target.dispatchEvent(ev);
  return ev;
}

test("arrows step the player and Space toggles play from the page body", () => {
  press(document.body, "ArrowRight");
  expect(player.tick).toBe(101);
  press(document.body, "ArrowLeft");
  press(document.body, "ArrowLeft");
  expect(player.tick).toBe(99);
  press(document.body, " ");
  expect(togglePlay).toHaveBeenCalledTimes(1);
});

test.each(["ArrowLeft", "ArrowRight", " "])("%s on a role=separator target does not drive playback", (k) => {
  const sep = document.createElement("div");
  sep.setAttribute("role", "separator");
  sep.tabIndex = 0;
  document.body.append(sep);
  press(sep, k);
  press(sep, k, true);
  expect(player.tick).toBe(100);
  expect(togglePlay).not.toHaveBeenCalled();
});

test("a child of a separator is also skipped", () => {
  const sep = document.createElement("div");
  sep.setAttribute("role", "separator");
  const inner = document.createElement("span");
  sep.append(inner);
  document.body.append(sep);
  press(inner, "ArrowRight");
  expect(player.tick).toBe(100);
});

test("form controls are still skipped", () => {
  const input = document.createElement("input");
  document.body.append(input);
  press(input, "ArrowRight");
  press(input, " ");
  expect(player.tick).toBe(100);
  expect(togglePlay).not.toHaveBeenCalled();
});
