# Viewer readability and resizable layout — Implementation Plan

> **For agentic workers:** use superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** make the replay viewer (`thermoRL/frontend/viz`) cleaner and easier to read on a projector, and make every layout boundary draggable. UI-only change: no data, contract, exporter or science change.

**Approved design (Bipin, 2026-11-02):**
- **Splitters (draggable borders):** (1) between the left and right rack grids; (2) between the stage and the right drawer (drag the drawer's left edge to widen it); (3) between the stage and the timeline (timeline height). Double-click resets; keyboard arrows move a focused splitter; sizes are not persisted. Rack tiles rescale automatically because each grid refits to its panel.
- **Readability:** larger type and spacing in the drawer and panels; **plain simple words first**; technical text is **collapsible and kept short**.
- Plain-words lines are fixed viewer copy (not headline strings). The contract's verbatim strings (`s2`, `precision_note`, `interval_semantics`, `pulse_rule`, `reproducibility_scope`, headline/rule/statement) stay verbatim from the bundle and are never retyped in source.

**Rulings already made (apply them):**
- **R-A:** About keeps each existing section heading. Under each heading: a short plain-words sentence (fixed copy) visible; below it a collapsed `<details><summary>Technical detail</summary>` holding the verbatim bundle string (S2 must remain shown verbatim in About per project rules; it is simply one click away). No third level.
- **R-B:** Why? keeps the logged-precision note, but as a compact callout: a plain-words one-liner visible, the verbatim `precision_note` inside a collapsed `Technical detail`. The "Chosen rack is not the top logged score — the live decision used full precision." note and `Ties at logged precision: n` stay visible.
- **R-C:** Outcome card content/order are unchanged and stay visible (headline, rule, tables, statement, footer); only typography and a callout style for the experiment statement change. No ranking, colouring good/bad, or derived values.
- **R-D:** Keep existing CSS class names / DOM ids that unit and e2e tests use, or update those tests in the same task.

## Global Constraints

- Work only in `thermoRL/frontend/viz/` (plus `README_DEMO.md` tips). Never touch `thermoRL/frontend/thermorl/**`, `thermoRL/frontend/artifacts/**`, or anything under `thermoRL/backend/`.
- No simulation of any kind.
- **Forbidden wording** (UI, source, docs, commits; enforced by `tests/unit/forbiddenCopy.test.ts` over `src/` and `index.html`): PUE, carbon, CO₂, SLO, emergency, λ / dual price(s), THI, regret, counterfactual outcome, "energy saving(s)", "cooling savings", "removes hotspots", "hotspot removal", "winner", "best policy", "significant(ly)", "real Summit temperature", "hardware temperature", "safety limit". Temperatures are "Modelled coolant °C".
- Never pair E11 and E12 in one view.
- Git: stage explicit paths only; one commit per task; push to `origin feat/parasparam-demo`; every commit message ends with the line `No new simulation; no change to accepted science.`; new `.md` under `thermoRL/` needs `git add -f`.
- Before each commit: `npm test` and `npx tsc --noEmit` clean; before the last task also `npm run build`, `npm run e2e` (fixture + real projects; real data needs `npm run sync-replay`), `npm run test:scripts`.
- Test-first: write the failing test, run it RED, implement, run it GREEN.

## Review Focus

1. Dragging a splitter must never leave the stage unusable: min/max clamps, pointer capture released on `pointerup`/`pointercancel`, no stuck drag, no listener leaks.
2. The WebGL canvas and rack grids must stay correct after every resize (no stretched tiles, no stale scissor rects, no blank grid), including a resize while playing.
3. Hover/click picking (`rackAt` / `pointerToNorm`) must stay correct in resized panels.
4. Verbatim bundle strings remain exactly equal in `textContent` (just inside collapsed `<details>`); plain-words copy contains no forbidden wording and makes no claim stronger than the verbatim text.
5. Readability: nothing overflows horizontally at drawer width 300 px and 70 %; tables stay legible.

---

### Task 1: Draggable splitters and layout wiring

**Files:**
- Create: `src/ui/splitter.ts`, `tests/unit/splitter.test.ts`
- Modify: `index.html` (splitter elements), `src/style.css` (layout via CSS variables), `src/main.ts` (wire splitters; trigger grid refit on resize)

**Interfaces:**
- `src/ui/splitter.ts` exports `attachSplitter(handle: HTMLElement, opts: { axis: "x" | "y"; get(): number; set(px: number): void; min(): number; max(): number; initial: number; step?: number }): () => void` (returns a dispose function).
  - Pointer drag: `pointerdown` captures the pointer, `pointermove` computes `clamp(start + delta)` (for the drawer and timeline the sign is reversed — the caller's `get/set` define the quantity; the handle only reports raw pixel deltas, so provide an optional `invert?: boolean`); `pointerup`/`pointercancel`/`lostpointercapture` end the drag.
  - Keyboard (handle `tabindex=0`, `role="separator"`, `aria-orientation`): arrow keys move by `step` (default 16 px), Shift = 4× step; Home/End jump to min/max.
  - Double-click calls `set(initial)`.
  - Sets `aria-valuenow/min/max` on the handle.
  - Exports a pure helper `clampSize(v: number, min: number, max: number): number` used by tests.
- Three splitters: `#split-panels` (between `#panel-left` and `#panel-right`, adjusts the left/right fraction via CSS variables on `#panels`, min 20 % each), `#split-drawer` (drawer left edge; drawer width var `--drawer-w`, default 460 px, min 300 px, max 70 % of `#body`), `#split-timeline` (timeline height var `--timeline-h`, default 168 px, min 80, max 400).
- When the drawer is hidden its splitter is hidden. Resizing must refit the WebGL canvas/grids (see Review Focus 2): verify `main.ts`' `ResizeObserver`/`dualView.resize()` path reacts to size changes caused by the CSS variables; add an observer on `#stage` and the panels if not already covered.

- [ ] **Step 1: write failing tests** (`tests/unit/splitter.test.ts`, jsdom): clamp helper at min/max; pointer drag moves the value by the delta and clamps; `invert` flips direction; drag ends on `pointerup` and on `pointercancel` (further moves ignored); arrow keys step, Shift ×4, Home/End jump to min/max; double-click resets to `initial`; `aria-valuenow` follows; dispose removes listeners (moves after dispose do nothing). Polyfill `setPointerCapture` in the test if jsdom lacks it.
- [ ] **Step 2:** `npm test -- splitter` → RED. **Step 3:** implement splitter + CSS + wiring. **Step 4:** GREEN; `npx tsc --noEmit`; `npm test`.
- [ ] **Step 5: browser check** (throwaway headless Chromium script, not committed, against `npm run make-fixture && npx vite build && npx vite preview`, `?data=replay-fixture`): drag each splitter and confirm sizes change, tiles rescale, both grids stay drawn, the tooltip still appears on hover after a resize, playing while resizing works; record what you verified.
- [ ] **Step 6: Commit:** `feat(viz): draggable splitters for panels, drawer and timeline`.

---

### Task 2: Readability — typography, plain-words About/Why?, outcome callout

**Files:**
- Modify: `src/style.css`, `src/ui/copy.ts`, `src/ui/aboutPanel.ts`, `src/ui/whyDrawer.ts`, `src/ui/outcomeCard.ts` (class tweaks only), tests `tests/unit/about*.test.ts` / `outcome.test.ts` / `whyDrawer.test.ts` (and `tests/e2e/*.spec.ts` selectors only if needed)

**Interfaces / copy (fixed viewer text in `copy.ts`; no forbidden wording):**
- About, plain-words lines (one sentence each, shown under the existing headings):
  - Decision timing (S2): "Every policy sees the same latest temperatures from the cooling model, with at most a 9-second look-ahead that assumes power stays constant. None of them sees future placements."
  - Interval semantics: "Rack power is what the scheduler fed in during the 10 seconds before the time shown. Temperature is what the cooling model returned at the end of those 10 seconds."
  - Pulse rings: "Cyan rings mark racks that just received a job. They show where jobs landed, not a cooling effect."
  - Logged precision: "The Why? list shows numbers as logged, to six decimals. The live scheduler used full precision, so near-ties can differ. Nothing is re-scored."
  - Reproducibility: "A few runs were repeated and matched exactly (E12 thermal_predictive seed 1 for 6 h; E11 seed-1 packing and power_balance for the first 2 h). The others were not repeated."
  - The "recorded runs, no new simulation" line and the four caveat bullets stay visible as they are (restyled).
  - Under each plain line: `<details class="about-tech"><summary>Technical detail</summary><p class="about-s2|about-interval|about-pulse|about-precision|about-repro">verbatim string</p></details>` — keep the existing class on the `<p>` so `textContent` equality tests keep working. **If the E12/E11 names or numbers in the repro line could drift from `outcome.reproducibility_scope`, say so in the report** (the plain line is fixed copy; the verbatim line is authoritative).
- Why? (R-B): compact callout `.why-precision-callout`: plain line "Numbers here are the logged six-decimal values; the live decision used full precision, and nothing is re-scored." visible; `<details class="why-tech"><summary>Technical detail</summary><p class="why-precision">verbatim precision_note</p></details>`. Item rows become cleaner (job id bold, nodes and racks as inline chips, logged-at and RAPS start muted); candidate table keeps its columns and the chosen-row highlight; larger text.
- Typography: base panel/drawer text 15–16 px, line-height ≥ 1.5, drawer padding 16 px, heading hierarchy (h-title 18 px, section heading 13 px uppercase muted), tables 13–14 px, outcome statement in a left-bordered callout, `details > summary` styled as a small muted toggle with a visible focus ring. Respect existing colour tokens.
- The drawer default width is set in Task 1 (460 px); verify nothing overflows horizontally at 300 px and at 70 %.

- [ ] **Step 1: write failing tests**: About: each plain line present (exact copy strings from `COPY`), each verbatim `<p>` `textContent` still strictly equals the bundle string and is inside a closed `<details>`; every `<details>` closed by default; Why?: plain callout line visible, verbatim precision note inside a closed `<details>` with exact textContent equality, ties/not-best notes unchanged; no forbidden wording (existing guard) ; outcome statement callout class present.
- [ ] **Step 2:** run RED; **Step 3:** implement; **Step 4:** GREEN (`npm test`, `npx tsc --noEmit`). Update existing tests only where they referenced layout (never loosen assertions).
- [ ] **Step 5: browser check** (throwaway): screenshots at drawer width 300 px / default / 70 % for Outcome, About, Why? (burst tick `t=3610` on the fixture) to the gitignored `test-artifacts/`; view them and report readability observations and any overflow.
- [ ] **Step 6: Commit:** `feat(viz): plain-words About and Why? with collapsible technical detail; readable type`.

---

### Task 3: e2e coverage, README tips, full verification (→ done)

**Files:**
- Modify: `tests/e2e/smoke.spec.ts` (and `tests/e2e/real.spec.ts` if selectors for Why?/About changed), `README_DEMO.md`, `docs/results/demo_replay_check.json` (update test counts only)

- [ ] **Step 1: e2e tests (fixture project):** drag `#split-drawer` left and assert the drawer's width grows (≥ +100 px) and the grids remain visible with a non-zero canvas; drag `#split-panels` and assert the left/right panel widths change; drag `#split-timeline` and assert the height changes within clamps; double-click each resets to the default; open About and assert plain lines visible, `<details>` closed, then expand one and assert the verbatim S2 text equals the catalog's; Why? at the burst shows the callout and the collapsed technical detail. Real project: keep the existing assertions working (update selectors only if needed).
- [ ] **Step 2: README_DEMO.md:** add a short "Layout tips" line (drag borders to resize, double-click resets; Technical detail toggles) and fix any wording that no longer matches. No forbidden wording.
- [ ] **Step 3:** run `npm test`, `npx tsc --noEmit`, `npm run build`, `npm run test:scripts`, `npm run e2e` (fixture + real); update test counts in `docs/results/demo_replay_check.json` (valid JSON; edit in place).
- [ ] **Step 4: Commit:** `test(viz): e2e for splitters and collapsible detail; README layout tips`. Push.
