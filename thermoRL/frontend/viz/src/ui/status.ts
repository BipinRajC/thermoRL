import { ReplayError } from "../data/loader";
import { COPY } from "./copy";

const shortFile = (file: string) => {
  const i = file.indexOf("runs/");
  return i >= 0 ? file.slice(i + "runs/".length) : file;
};

export class Status {
  constructor(private readonly el: HTMLElement) {}

  loading(file?: string, done = 0, total = 0): void {
    this.reset("loading");
    this.el.append(this.line(file && total > 0 ? COPY.loadingFile(shortFile(file), done, total) : COPY.loading));
    this.el.setAttribute("role", "status");
    this.el.hidden = false;
  }

  hide(): void {
    this.reset("");
    this.el.hidden = true;
  }

  error(e: unknown): void {
    this.reset("error");
    this.el.setAttribute("role", "alert");
    const title = document.createElement("h2");
    title.textContent = COPY.errorTitle;
    this.el.append(title);
    if (e instanceof ReplayError) {
      this.el.append(this.line(`kind: ${e.kind}`, "status-kind"));
      if (e.file) this.el.append(this.line(`file: ${e.file}`, "status-file"));
      this.el.append(this.line(e.message, "status-message"));
      const hint = document.createElement("p");
      hint.className = "status-hint";
      const parts = COPY.syncHint.split("`");
      parts.forEach((part, i) => {
        if (i % 2) {
          const code = document.createElement("code");
          code.textContent = part;
          hint.append(code);
        } else {
          hint.append(part);
        }
      });
      this.el.append(hint);
    } else {
      this.el.append(this.line(e instanceof Error ? e.message : String(e), "status-message"));
    }
    this.el.hidden = false;
  }

  private reset(kind: string): void {
    this.el.replaceChildren();
    this.el.className = kind ? `status status-${kind}` : "status";
    this.el.removeAttribute("role");
  }

  private line(text: string, cls = ""): HTMLElement {
    const p = document.createElement("p");
    if (cls) p.className = cls;
    p.textContent = text;
    return p;
  }
}
