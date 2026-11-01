export const SPEEDS = [1, 2, 5, 10, 30, 60] as const;

export class Player {
  tick = 0;
  playing = false;
  speed = 10;
  private acc = 0;
  private listeners = new Set<(k: number) => void>();

  constructor(readonly nTicks: number) {}

  private moveTo(k: number): boolean {
    const next = Math.min(this.nTicks - 1, Math.max(0, Math.trunc(k)));
    if (next === this.tick) return false;
    this.tick = next;
    for (const fn of this.listeners) fn(next);
    return true;
  }

  advance(dtMs: number): boolean {
    this.acc += (dtMs * this.speed) / 1000;
    const whole = Math.floor(this.acc);
    this.acc -= whole;
    const changed = this.moveTo(this.tick + whole);
    if (this.tick >= this.nTicks - 1) {
      this.playing = false;
      this.acc = 0;
    }
    return changed;
  }

  seek(k: number): void {
    this.moveTo(k);
  }

  step(dk: number): void {
    this.moveTo(this.tick + dk);
  }

  onChange(fn: (k: number) => void): () => void {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  }
}
