import type { Catalog } from "../schema/replay";
import { SPEEDS, type Player } from "../replay/player";
import { formatClock, tickToTs, tsToTick, windowLabel } from "../model/time";
import { COPY } from "./copy";

export const STEP_BUTTONS = [
  { label: "−10 min", seconds: -600 },
  { label: "−1 min", seconds: -60 },
  { label: "−1 tick", seconds: -1, tick: true },
  { label: "+1 tick", seconds: 1, tick: true },
  { label: "+1 min", seconds: 60 },
  { label: "+10 min", seconds: 600 },
] as const;

export const stepTicks = (b: (typeof STEP_BUTTONS)[number], cat: Catalog): number =>
  "tick" in b ? Math.sign(b.seconds) : b.seconds / cat.time.tick_s;

export const evalStartTick = (cat: Catalog): number =>
  tsToTick(cat.time.eval_start_exclusive_s + cat.time.tick_s, cat.time.n_ticks);

export const clockText = (k: number, cat: Catalog): string => {
  const t = tickToTs(k);
  return `${formatClock(t)} · tick ${k}/${cat.time.n_ticks} · ${windowLabel(t, cat)}`;
};

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, props: Record<string, string> = {}): HTMLElementTagNameMap[K] =>
  Object.assign(document.createElement(tag), props);

export class Controls {
  private player: Player | null = null;
  private cat: Catalog | null = null;
  private off: (() => void) | null = null;
  private readonly play = el("button", { type: "button", id: "btn-play", textContent: COPY.controls.play });
  private readonly steps = STEP_BUTTONS.map((b) => ({ b, node: el("button", { type: "button", textContent: b.label }) }));
  private readonly jump = el("button", { type: "button", id: "btn-jump-eval", textContent: COPY.controls.jumpToEval });
  private readonly speed = el("select", { id: "sel-speed" });
  private readonly scrub = el("input", { type: "range", id: "scrubber", min: "0", max: "0", step: "1", value: "0" });
  private readonly clock = el("div", { id: "clock" });

  constructor(root: HTMLElement) {
    for (const s of SPEEDS) this.speed.append(el("option", { value: String(s), textContent: COPY.controls.speedOption(s) }));
    this.speed.value = "10";
    this.clock.setAttribute("aria-live", "off");
    const buttons = el("div", { className: "control-buttons" });
    this.speed.setAttribute("aria-label", COPY.controls.speed);
    this.scrub.setAttribute("aria-label", COPY.controls.scrubber);
    buttons.append(this.play, ...this.steps.map((s) => s.node), this.jump, this.speed);
    root.append(buttons, this.scrub, this.clock);

    this.play.addEventListener("click", () => this.togglePlay());
    for (const { b, node } of this.steps) {
      node.addEventListener("click", () => this.cat && this.player?.step(stepTicks(b, this.cat)));
    }
    this.jump.addEventListener("click", () => this.cat && this.player?.seek(evalStartTick(this.cat)));
    this.speed.addEventListener("change", () => {
      if (this.player) this.player.speed = Number(this.speed.value);
    });
    this.scrub.addEventListener("input", () => this.player?.seek(this.scrub.valueAsNumber));
    this.setEnabled(false);
  }

  bind(player: Player | null, cat: Catalog | null): void {
    this.off?.();
    this.off = null;
    this.player = player;
    this.cat = cat;
    this.setEnabled(Boolean(player && cat));
    if (!player || !cat) {
      this.clock.textContent = "";
      return;
    }
    player.speed = Number(this.speed.value);
    this.scrub.max = String(player.nTicks - 1);
    this.off = player.onChange(() => this.refreshTime());
    this.refreshTime();
    this.refresh();
  }

  togglePlay(): void {
    const p = this.player;
    if (!p) return;
    if (p.playing) {
      p.playing = false;
    } else {
      if (p.tick >= p.nTicks - 1) p.seek(0);
      p.playing = true;
    }
    this.refresh();
  }

  refresh(): void {
    const playing = Boolean(this.player?.playing);
    const text = playing ? COPY.controls.pause : COPY.controls.play;
    if (this.play.textContent === text) return;
    this.play.textContent = text;
    this.play.setAttribute("aria-pressed", String(playing));
  }

  private refreshTime(): void {
    if (!this.player || !this.cat) return;
    const k = this.player.tick;
    this.scrub.value = String(k);
    this.clock.textContent = clockText(k, this.cat);
  }

  private setEnabled(on: boolean): void {
    for (const n of [this.play, this.jump, this.speed, this.scrub, ...this.steps.map((s) => s.node)]) n.disabled = !on;
  }
}

export function installKeyboard(getControls: () => Controls, getPlayer: () => Player | null, getCat: () => Catalog | null): () => void {
  const onKey = (e: KeyboardEvent) => {
    const t = e.target as HTMLElement | null;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (t && /^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(t.tagName)) return;
    if (e.key !== " " && t?.closest?.('[role="separator"]')) return;
    const player = getPlayer();
    const cat = getCat();
    if (!player || !cat) return;
    if (e.key === " ") {
      e.preventDefault();
      getControls().togglePlay();
    } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      const dir = e.key === "ArrowLeft" ? -1 : 1;
      player.step(dir * (e.shiftKey ? 60 / cat.time.tick_s : 1));
    }
  };
  window.addEventListener("keydown", onKey);
  return () => window.removeEventListener("keydown", onKey);
}
