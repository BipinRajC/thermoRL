import type { VizFrame } from "../schema/vizevent";

export class Player {
  frames: VizFrame[];
  index = 0;
  playing = true;
  acc = 0;
  msPerFrame = 80;

  constructor(frames: VizFrame[]) {
    this.frames = frames;
  }

  get current(): VizFrame {
    return this.frames[this.index] ?? this.frames[0];
  }

  get last(): number {
    return Math.max(this.frames.length - 1, 0);
  }

  step(dir: number): void {
    this.index = Math.min(this.last, Math.max(0, this.index + dir));
  }

  jump(i: number): void {
    this.index = Math.min(this.last, Math.max(0, i));
  }

  tick(dtMs: number): boolean {
    if (!this.playing || this.frames.length === 0) return false;
    this.acc += dtMs;
    if (this.acc < this.msPerFrame) return false;
    this.acc = 0;
    if (this.index < this.last) {
      this.index += 1;
      return true;
    }
    this.playing = false;
    return false;
  }
}
