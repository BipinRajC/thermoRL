import { COPY } from "./copy";

export function renderFallback(el: HTMLElement, experimentId: string): void {
  el.replaceChildren();
  const note = document.createElement("p");
  note.className = "fallback-note";
  note.textContent = COPY.webglFallback;
  const list = document.createElement("ul");
  for (const { file, caption } of COPY.fallbackFigures) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `fallback/${encodeURIComponent(experimentId)}/${file}`;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = caption;
    li.append(a);
    list.append(li);
  }
  el.append(note, list);
  el.hidden = false;
}

export function hideFallback(el: HTMLElement): void {
  el.replaceChildren();
  el.hidden = true;
}
