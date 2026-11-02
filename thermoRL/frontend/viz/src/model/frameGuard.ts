export function guardedFrame(
  draw: (now: number) => void,
  rearm: () => void,
  onError: (e: unknown) => void,
): (now: number) => void {
  const reported = new Set<string>();
  return (now) => {
    rearm();
    try {
      draw(now);
      reported.clear();
    } catch (e) {
      const key = e instanceof Error ? e.message : String(e);
      if (reported.has(key)) return;
      reported.add(key);
      onError(e);
    }
  };
}
