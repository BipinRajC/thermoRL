import * as THREE from "three";
import { Player } from "./replay/player";
import { RackPanel } from "./scene/racks";
import type { BundleMetrics, VizFrame } from "./schema/vizevent";

type LedgerRowLite = {
  decision_id: string;
  job_id: string;
  action: string;
  reason_code: string;
  reason_text: string;
  chosen_zone: number | null;
  chosen_rack: number | null;
  candidates: Array<{
    zone_id: number;
    feasible: boolean;
    thi_before: number;
    thi_after_pred: number | null;
    lookahead_score: number | null;
    infeasible_reason: string | null;
  }>;
  outcome: {
    thi_actual_h: number[];
    thi_predicted_h: number[];
    regret_vs_best_counterfactual: number;
  } | null;
};

const ZONE_NAMES = ["Z1 Air", "Z2 D2C", "Z3 Immersion"];

function escapeHtml(value: unknown): string {
  return String(value ?? "—")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fixed(value: number | null | undefined, digits = 3): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

declare global {
  interface Window {
    THERMORL_DATA?: {
      frames_rr: VizFrame[];
      frames_thermorl: VizFrame[];
      ledger_thermorl: LedgerRowLite[];
      metrics: BundleMetrics;
    };
  }
}

async function loadJsonl<T>(url: string): Promise<T[]> {
  const text = await fetch(url).then((r) => {
    if (!r.ok) throw new Error(`failed ${url}`);
    return r.text();
  });
  return text
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as T);
}

function setText(id: string, value: string): void {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function paintMetrics(left: VizFrame, right: VizFrame): void {
  setText("regime", `Regime: ${right.regime}`);
  setText(
    "m-viol",
    `${left.metrics.violations_per_1k_jobs.toFixed(1)} / ${right.metrics.violations_per_1k_jobs.toFixed(1)}`,
  );
  setText(
    "m-emerg",
    `${left.metrics.emergency_events_per_1k_jobs.toFixed(1)} / ${right.metrics.emergency_events_per_1k_jobs.toFixed(1)}`,
  );
  setText("m-jobs", `${left.metrics.jobs_completed} / ${right.metrics.jobs_completed}`);
  setText("m-wait", `${left.metrics.mean_wait_s.toFixed(1)} / ${right.metrics.mean_wait_s.toFixed(1)}`);
  setText(
    "m-slo",
    `${left.metrics.slo_compliance.toFixed(2)} / ${right.metrics.slo_compliance.toFixed(2)}`,
  );
  setText("m-offered", right.metrics.offered_demand_ratio.toFixed(2));
  setText(
    "m-load",
    `${left.metrics.physical_facility_load_kw.toFixed(0)} / ${right.metrics.physical_facility_load_kw.toFixed(0)}`,
  );
}

function showWhy(row: LedgerRowLite | undefined): void {
  const box = document.getElementById("why");
  const body = document.getElementById("why-body");
  const raw = document.getElementById("why-raw");
  if (!box || !body) return;
  if (!row) {
    body.innerHTML = '<div class="why-reason">No ledger row for this frame. Step to a placement event to inspect a real decision.</div>';
    if (raw) raw.textContent = "";
    return;
  }
  const candidates = row.candidates
    .map((candidate) => {
      const status = candidate.feasible ? "FEASIBLE" : `INELIGIBLE · ${candidate.infeasible_reason ?? "constraint"}`;
      return `<div class="candidate ${candidate.feasible ? "" : "ineligible"}">
        <strong>${escapeHtml(ZONE_NAMES[candidate.zone_id] ?? `Zone ${candidate.zone_id}`)}</strong>
        <span>${escapeHtml(status)}</span><br>
        <span>THI before ${fixed(candidate.thi_before)}</span><br>
        <span>THI predicted ${fixed(candidate.thi_after_pred)}</span><br>
        <span>score ${fixed(candidate.lookahead_score)}</span>
      </div>`;
    })
    .join("");
  const outcome = row.outcome
    ? `Outcome: actual ${row.outcome.thi_actual_h.map((value) => fixed(value)).join(" / ")} · predicted ${row.outcome.thi_predicted_h.map((value) => fixed(value)).join(" / ")} · regret ${fixed(row.outcome.regret_vs_best_counterfactual)}`
    : "Outcome is not available for this decision.";
  body.innerHTML = `
    <div class="why-summary">
      <div class="why-card"><span>Job</span><strong>${escapeHtml(row.job_id)}</strong></div>
      <div class="why-card"><span>Action</span><strong>${escapeHtml(row.action)}</strong></div>
      <div class="why-card"><span>Target</span><strong>${escapeHtml(`${ZONE_NAMES[row.chosen_zone ?? -1] ?? "—"} · rack ${row.chosen_rack ?? "—"}`)}</strong></div>
      <div class="why-card"><span>Decision</span><strong>${escapeHtml(row.decision_id.split("::").at(-1))}</strong></div>
    </div>
    <div class="why-reason"><strong>${escapeHtml(row.reason_code)}</strong><br>“${escapeHtml(row.reason_text)}”<br><small>${escapeHtml(outcome)}</small></div>
    <div class="candidate-grid">${candidates}</div>`;
  if (raw) {
    raw.textContent = JSON.stringify(
      {
        decision_id: row.decision_id,
        job_id: row.job_id,
        action: row.action,
        reason_code: row.reason_code,
        reason_text: row.reason_text,
        chosen_zone: row.chosen_zone,
        chosen_rack: row.chosen_rack,
        candidates: row.candidates,
        outcome: row.outcome,
      },
      null,
      2,
    );
  }
}

function showAdvanced(frame: VizFrame): void {
  const body = document.getElementById("adv-body");
  if (!body) return;
  const labels = ["THI · Air", "THI · D2C", "THI · Immersion", "Throughput", "SLO"];
  const values = frame.advanced.lambdas ?? [];
  body.innerHTML = `<div class="lambda-grid">${labels
    .map((label, index) => `<div class="lambda-card"><span>${label}</span><strong>${fixed(values[index] ?? 0, 4)}</strong></div>`)
    .join("")}</div><div class="lambda-note">Frame-backed dual values. Zeros mean this short wiring replay has not yet priced the constraint.</div>`;
}

function setScissorForElement(
  renderer: THREE.WebGLRenderer,
  el: HTMLElement,
): { width: number; height: number } {
  const canvas = renderer.domElement;
  const canvasRect = canvas.getBoundingClientRect();
  const rect = el.getBoundingClientRect();
  const left = rect.left - canvasRect.left;
  const bottom = canvasRect.bottom - rect.bottom;
  const width = rect.width;
  const height = rect.height;
  renderer.setViewport(left, bottom, width, height);
  renderer.setScissor(left, bottom, width, height);
  return { width, height };
}

async function main(): Promise<void> {
  const inline = window.THERMORL_DATA;
  const [framesRr, framesTh, metrics, ledgerTh] = inline
    ? [inline.frames_rr, inline.frames_thermorl, inline.metrics, inline.ledger_thermorl]
    : await Promise.all([
        loadJsonl<VizFrame>("./frames_rr.jsonl"),
        loadJsonl<VizFrame>("./frames_thermorl.jsonl"),
        fetch("./metrics.json").then((r) => r.json() as Promise<BundleMetrics>),
        loadJsonl<LedgerRowLite>("./ledger_thermorl.jsonl"),
      ]);

  const player = new Player(framesTh);
  const left = new RackPanel();
  const right = new RackPanel();
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    preserveDrawingBuffer: true,
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x0b0d12, 1);
  renderer.autoClear = false;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const canvas = renderer.domElement;
  canvas.id = "gl";
  document.body.prepend(canvas);

  const viewRr = document.getElementById("view-rr")!;
  const viewTh = document.getElementById("view-th")!;
  const scrub = document.getElementById("scrub") as HTMLInputElement;
  scrub.max = String(player.last);

  const byDecision = new Map(ledgerTh.map((r) => [r.decision_id, r]));

  function resize(): void {
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
  }

  function renderViews(nowMs: number): void {
    const rr = framesRr[Math.min(player.index, framesRr.length - 1)] ?? framesRr[0];
    const th = player.current;
    left.apply(rr, metrics.thi_p10, metrics.thi_p90, nowMs);
    right.apply(th, metrics.thi_p10, metrics.thi_p90, nowMs);
    paintMetrics(rr, th);
    setText("clock", `t=${th.t}  ${th.sim_time_s.toFixed(0)}s`);
    scrub.value = String(player.index);

    renderer.setScissorTest(false);
    renderer.clear(true, true, true);
    renderer.setScissorTest(true);
    for (const [el, panel] of [
      [viewRr, left],
      [viewTh, right],
    ] as const) {
      const { width, height } = setScissorForElement(renderer, el);
      if (width < 2 || height < 2) continue;
      panel.fitAspect(width / height);
      renderer.clearDepth();
      renderer.render(panel.scene, panel.camera);
    }
  }

  document.getElementById("btn-play")!.onclick = () => {
    player.playing = true;
  };
  document.getElementById("btn-pause")!.onclick = () => {
    player.playing = false;
  };
  document.getElementById("btn-back")!.onclick = () => {
    player.playing = false;
    player.step(-1);
    renderViews(performance.now());
  };
  document.getElementById("btn-fwd")!.onclick = () => {
    player.playing = false;
    player.step(1);
    renderViews(performance.now());
  };
  scrub.oninput = () => {
    player.playing = false;
    player.jump(Number(scrub.value));
    renderViews(performance.now());
  };
  document.getElementById("btn-why")!.onclick = () => {
    const box = document.getElementById("why")!;
    box.hidden = !box.hidden;
    const ev = player.current.events.find((e) => e.decision_id);
    showWhy(ev?.decision_id ? byDecision.get(ev.decision_id) : undefined);
  };
  document.getElementById("btn-adv")!.onclick = () => {
    const box = document.getElementById("advanced")!;
    box.hidden = !box.hidden;
    showAdvanced(player.current);
  };

  let last = performance.now();
  const loop = (now: number) => {
    player.tick(now - last);
    last = now;
    renderViews(now);
    requestAnimationFrame(loop);
  };
  resize();
  window.addEventListener("resize", () => {
    resize();
    renderViews(performance.now());
  });
  requestAnimationFrame(loop);
}

main().catch((err) => {
  document.body.textContent = String(err);
});
