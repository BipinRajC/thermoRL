# ThermoRL Replay Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy three-zone viewer in `thermoRL/frontend/viz/` with a truthful, interactive replay of the **recorded** Summit FMU runs (E11 synthetic, E12 Alibaba-derived). It shows two policies side by side on a 257-rack schematic, synchronised in time, with the frozen negative G4 outcome and logged decision context.

**Architecture:** a static Vite + TypeScript + Three.js app with no server. A sync script copies the exporter's `replay_v1` bundles into `public/replay/`. The app:
- fetches the JSON and binary files and verifies each one's SHA-256 in the browser;
- holds the arrays in typed form;
- renders two orthographic tile grids with one WebGL renderer using scissor viewports;
- draws the timeline, drawers and panels as DOM/Canvas2D.

Nothing is simulated, rescored or recomputed in the browser. Headline numbers come verbatim from `frozen_outcome.json`.

**Tech stack:**
- Node ≥ 20;
- Vite 6, TypeScript 5.6 (`strict`), Three.js 0.170 (all already in `package.json`);
- new dev dependencies: `vitest` (^3), `jsdom` (^25), `@playwright/test` (^1.48).

**Spec:**
- **Data:** `docs/superpowers/specs/2026-11-01-replay-v1-contract.md` (binding; read it first).
- **Scope, claims and constraints:** `docs/handoffs/2026-10-31-sonnet-5-5-demo-integration-brief.md`, §0, the 2026-11-01 override block, and Part B. **This plan supersedes Part B's details.**
- **Science:** `docs/results/2026-11-parasparam-demo-results.md`.

**Prerequisite for the last task only:** real exports must exist (brief A5–A7, checkpoint CK-B). Tasks 1–12 run against a **generated fixture bundle**, so they can start before the exports land.

## Global Constraints

- **Location:** work only in `thermoRL/frontend/viz/`, plus the docs listed in Task 13.
- **Never touch:**
  - `thermoRL/frontend/thermorl/**` and `thermoRL/frontend/artifacts/**` (legacy simulator and fixture: never run, import or delete);
  - anything under `thermoRL/backend/` (except reading `exports/replay_v1` and `plots/demo` in the sync script);
  - raw `runs/`.
- **No simulation of any kind.** No FMU, RAPS, `run.py`, `run_matrix` or legacy `make_demo_bundle.py`.
- **Forbidden in any visible string, file or commit message** (enforced by test in Task 9):
  - PUE, carbon, CO₂, SLO, emergency, λ / dual price, THI, regret, counterfactual outcome;
  - "energy saving(s)", "cooling savings", "removes hotspots", "hotspot removal";
  - "winner", "best policy", "significant(ly)";
  - "real Summit temperature", "hardware temperature", "safety limit".
- **Temperatures** are always labelled **"Modelled coolant °C"**.
- **Never pair E11 and E12 in one view.** Comparisons are within one experiment and one seed.
- **Colour:** `catalog.colormap.lut` (matplotlib inferno, 256 entries) over the active seed's `colour_scale_c`. The legend always prints min and max to 2 decimals.
- **Headline strings** (`headline`, `rule`, `experiment_statement`, `reproducibility_scope`, `s2`, `precision_note`, `interval_semantics`, `pulse_rule`) are rendered **verbatim** from the bundle, never retyped in source.
- **Time:** tick k ↔ `t_s = 10·(k+1)`. The evaluation window is **3600 < t_s ≤ 21600**, so t_s = 3600 is "before", and 3610 is the first "evaluation" tick.
- **No overwrite of tracked historical artifacts.** The sync script writes only to `viz/public/replay/` and `viz/public/fallback/`, both gitignored.
- **Git:**
  - new `.md` files under `thermoRL/` need `git add -f -- <file>` (`thermoRL/.gitignore` ignores `*.md`);
  - never `git add -A`; stage explicit paths;
  - every commit message ends with "No new simulation; no change to accepted science.";
  - branch `feat/parasparam-demo`; push after each task.

## Review Focus

1. **Comparing runs with different shapes or time grids:** the app must show an error naming both runs. It must never clamp or silently align. *Test: Task 2, `assertComparable` mismatch cases.*
2. **Values outside the active colour scale** (seeds 2/3, or the kW and occupancy overlays): render at the end colour, **and** the tooltip says "outside scale" and the legend shows a count of out-of-range racks in the current frame. *Test: Task 4.*
3. **The window boundary and the ends of the episode:** tick 359 (t_s 3600) is labelled "before evaluation window", tick 360 (3610) "evaluation window"; seeking below 0 or above 2159 clamps; pulses at k = 0 do not read negative times. *Tests: Tasks 3 and 5.*
4. **Burst frames with hundreds of placements in 30 s** (E12 bursts exceed 500 decisions in that window), and frames with none: the Why drawer pages (50 per page) and shows "No job starts in this 30 s window" for empty frames. *Test: Task 10.*
5. **Switching experiment, seed or comparison while a load is in flight:** stale responses must never render. The newest request wins (AbortController plus a load token). *Test: Task 7, `Store` / `loadComparison` race test.*

---

## File structure (after this plan)

```
thermoRL/frontend/viz/
  index.html                      # rewritten: app shell (no bundle-data.js)
  vite.config.ts                  # modified
  package.json / package-lock.json# modified: scripts + dev deps
  vitest.config.ts                # new
  playwright.config.ts            # new
  .gitignore                      # modified: public/replay/, public/fallback/, public/replay-fixture/, test-artifacts/
  README_DEMO.md                  # new (force-add)
  scripts/sync-replay.mjs         # new: copy+verify exports → public/replay, write index.json, copy fallback assets
  scripts/make-fixture.mjs        # new: writes a small valid bundle to public/replay-fixture/
  src/main.ts                     # rewritten: bootstrap
  src/style.css                   # rewritten
  src/schema/replay.ts            # contract types + SCHEMA + constants
  src/data/hash.ts                # sha256Hex
  src/data/loader.ts              # fetch + verify + typed arrays; ReplayError; assertComparable
  src/data/views.ts               # accessors over LoadedRun
  src/model/time.ts               # tick/time/window/pulse helpers
  src/model/colour.ts             # LUT mapping, overlays, legend stats
  src/model/store.ts              # AppState store
  src/replay/player.ts            # rewritten: tick player
  src/scene/rackGrid.ts           # 257-tile instanced grid (replaces racks.ts)
  src/scene/dualView.ts           # one renderer, two scissor viewports, picking
  src/ui/copy.ts                  # fixed UI copy (non-headline)
  src/ui/header.ts  src/ui/controls.ts  src/ui/legend.ts  src/ui/tooltip.ts
  src/ui/timeline.ts  src/ui/sparkline.ts  src/ui/outcomeCard.ts
  src/ui/aboutPanel.ts  src/ui/whyDrawer.ts  src/ui/status.ts  src/ui/fallback.ts
  tests/fixture/buildFixture.ts   # in-memory fixture builder (shared by unit tests and make-fixture)
  tests/unit/*.test.ts
  tests/e2e/smoke.spec.ts
```

**Deleted:** `src/schema/vizevent.ts` and `src/scene/racks.ts`. These are legacy viewer files and remain in git history. Do not delete anything under `thermoRL/frontend/thermorl/` or `artifacts/`.

---

### Task 1: Contract types, fixture builder, test tooling

**Files:**
- Create: `src/schema/replay.ts`, `tests/fixture/buildFixture.ts`, `scripts/make-fixture.mjs`, `vitest.config.ts`, `tests/unit/fixture.test.ts`
- Modify: `package.json` (scripts and dev dependencies), `.gitignore`

**Interfaces:**
- Produces, in `src/schema/replay.ts`:
  - `export const SCHEMA = "thermorl.replay.v1"`
  - `export type PolicyId = "packing"|"node_balance"|"power_balance"|"coolest_rack"|"thermal_predictive"`
  - `export interface IndexFile { schema: string; experiments: IndexEntry[] }`
  - `export interface IndexEntry { id: string; short: string; label: string; catalog: string; default?: boolean }`
  - `export interface Catalog`, `FrozenOutcome`, `RunMeta`, `FileEntry`, `SeedEntry`, `Comparison`, `MetricsRow`. These mirror contract §§3–5 field for field.
  - `export const TICK_COLUMNS = ["t_s","it_kw_total","n_running","n_queued","maxrack_c","minrack_c","argmax_rack","pump_kw_sum"] as const`
  - `export type TickColumn = typeof TICK_COLUMNS[number]`
- Produces, in `tests/fixture/buildFixture.ts`:
  - `buildFixture(opts?: { nTicks?: number; rows?: number; cols?: number; nRacks?: number; seeds?: number[]; decisionsPerTick?: (k: number) => number; corrupt?: { file: string } }): Promise<Map<string, Uint8Array>>`
  - Returns relative path → bytes for a complete, hash-correct tree: `index.json`, `<EXP>/catalog.json`, `frozen_outcome.json`, and `runs/*/` for one fake experiment `EFIX` with three policies.
  - **Defaults:** `nTicks = 400` (so the 3600 s boundary at tick 359 exists), a 3 × 4 grid with 11 racks (one empty cell), seeds `[1, 2]`.
  - **Values are deterministic**, e.g. `t_c = 40 + 0.01·k + 0.1·r` for the right policy and +0.2 °C for the left policy. That way the tests know exact values.
  - **Required fixture specifics** (later tasks test them; each is identical in every policy unless stated):
    - a start event at `raps_t_s = 25` whose decision is `rule: "span"` with chosen racks {2, 3};
    - one decision with `chosen_is_logged_best = false` and `n_ties_at_logged_best = 3`;
    - a **burst** of exactly 120 decisions with `raps_t_s` in (3580, 3610];
    - **no** decisions with `raps_t_s` in (1170, 1200], i.e. the window ending at tick 119;
    - the seed-1 `colour_scale_c.max` set so that **exactly 2 racks exceed it at tick 5** for the right policy;
    - the seed-2 scale differs from seed 1's;
    - `c_prime_status = "verified_E12"` on `thermal_predictive` seed 1 only.
- Produces: `scripts/make-fixture.mjs` writes `buildFixture()` output into `public/replay-fixture/` (via `tsx` or a compiled import; choose `npx tsx` and add `tsx` as a dev dependency).

- [ ] **Step 1: Add dev dependencies and scripts.** `npm i -D vitest jsdom @playwright/test tsx`. Scripts:
  - `"test": "vitest run"`
  - `"e2e": "playwright test"`
  - `"make-fixture": "tsx scripts/make-fixture.mjs"`
  - `"sync-replay": "node scripts/sync-replay.mjs"`
  - `"dev": "npm run sync-replay --if-present && vite"`
  - `"build": "tsc --noEmit && vite build"`

  `vitest.config.ts` uses `environment: "jsdom"` and `include: ["tests/unit/**/*.test.ts"]`. Add `public/replay/`, `public/replay-fixture/`, `public/fallback/` and `test-artifacts/` to `viz/.gitignore`.
- [ ] **Step 2: Write the failing test** `tests/unit/fixture.test.ts`:
  ```ts
  test("fixture is a complete, hash-correct replay_v1 tree", async () => {
    const files = await buildFixture();
    const index = JSON.parse(dec(files.get("index.json")!));
    expect(index.schema).toBe("thermorl.replay.v1");
    const cat = JSON.parse(dec(files.get("EFIX/catalog.json")!));
    expect(cat.grid).toMatchObject({ rows: 3, cols: 4, n_racks: 11 });
    expect(cat.colormap.lut).toHaveLength(256);
    const run = JSON.parse(dec(files.get("EFIX/runs/power_balance_seed1/run.json")!));
    for (const f of Object.values(run.files) as any[]) {
      const bytes = files.get(`EFIX/runs/power_balance_seed1/${f.path}`)!;
      expect(bytes.byteLength).toBe(f.bytes);
      expect(await sha256Hex(bytes)).toBe(f.sha256);   // sha256Hex from Task 2; inline node:crypto here until then
    }
  });
  ```
- [ ] **Step 3:** run `npm test`. Expected: FAIL (module not found).
- [ ] **Step 4:** implement `replay.ts` types and `buildFixture`.
  - The candidates records are 15 bytes each (`<HfffB`, little-endian), 6 rows per decision; empty rows use rack 65535.
  - The fixture's LUT is any 256 valid `#rrggbb` strings.
- [ ] **Step 5:** run `npm test`. Expected: PASS. Run `npm run make-fixture`, then `ls public/replay-fixture/EFIX/runs`. Expected: 6 run directories.
- [ ] **Step 6: Commit:** `feat(viz): replay_v1 contract types, fixture builder, test tooling`.

---

### Task 2: Hashing, loader, integrity errors

**Files:**
- Create: `src/data/hash.ts`, `src/data/loader.ts`, `tests/unit/loader.test.ts`

**Interfaces:**
- Consumes: Task 1 types and `buildFixture`.
- Produces:
  - `sha256Hex(bytes: ArrayBuffer | Uint8Array): Promise<string>` (via `crypto.subtle.digest`).
  - `class ReplayError extends Error { kind: "missing"|"schema"|"size"|"hash"|"shape"|"mismatch"|"network"; file?: string }`
  - `type Fetcher = (url: string, init?: { signal?: AbortSignal }) => Promise<Response>`
  - `loadIndex(base: string, f?: Fetcher): Promise<IndexFile>`
  - `loadExperiment(base: string, entry: IndexEntry, f?: Fetcher): Promise<{ catalog: Catalog; outcome: FrozenOutcome }>`
  - `interface LoadedRun { meta: RunMeta; tc: Float32Array; kw: Float32Array; free: Uint8Array; tick: Float64Array; events: EventsColumns; decisions: DecisionColumns; candidates: DataView }`
  - `loadRun(base: string, expDir: string, runJsonPath: string, f?: Fetcher, signal?: AbortSignal, onProgress?: (file: string, done: number, total: number) => void): Promise<LoadedRun>`
  - `assertComparable(a: LoadedRun, b: LoadedRun): void` (throws `ReplayError("mismatch")`).
  - `EventsColumns` and `DecisionColumns` are the contract §5 columnar shapes as typed arrays: `Int32Array` for integer columns, `Float64Array` for `job_kw` and `t_obs_s`, `string[]` for `rule`, `Uint8Array` for booleans.

- [ ] **Step 1: Write failing tests** (each uses a fetcher built from the fixture `Map`):
  - `loads a valid run`: `tc.length === 400*11`, `tc[0]` equals the fixture value, `decisions.raps_t_s` is non-decreasing.
  - `schema mismatch`: catalog `schema: "x"` → rejects `{kind:"schema"}`.
  - `missing file`: drop `rack_kw.f32` → `{kind:"missing", file:"…/rack_kw.f32"}`.
  - `size mismatch`: truncate `rack_tc.f32` by 4 bytes → `{kind:"size"}`.
  - `hash mismatch`: `buildFixture({corrupt:{file:"rack_tc.f32"}})` → `{kind:"hash"}`.
  - `shape mismatch`: `run.json` `files.rack_tc.shape = [399,11]` with the bytes unchanged → `{kind:"shape"}`.
  - `assertComparable` throws `mismatch` when `n_ticks` differs, when `n_racks` differs, or when `tick` t_s columns differ at any index; it passes for two policies of the same seed.
  - `abort`: an aborted signal → rejects with an `AbortError` (not a `ReplayError`).
- [ ] **Step 2:** `npm test -- loader`. Expected: FAIL.
- [ ] **Step 3:** implement. Fetch `run.json`, then each `files[*]` as an `ArrayBuffer`. Check `byteLength === bytes` (else "size"), then `sha256Hex === sha256` (else "hash"), then `shape` product × element size `=== bytes` (else "shape"). Decode JSON files after hashing. HTTP 404 → "missing"; any other failed fetch → "network".
- [ ] **Step 4:** `npm test -- loader`. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): verified replay loader`.

---

### Task 3: Time model and data views

**Files:**
- Create: `src/model/time.ts`, `src/data/views.ts`, `tests/unit/time.test.ts`, `tests/unit/views.test.ts`

**Interfaces:**
- Produces, in `time.ts`:
  - `tickToTs(k: number): number` (= 10·(k+1))
  - `tsToTick(t: number): number` (inverse, clamped to [0, nTicks−1]; t not on the grid → floor)
  - `windowState(t_s: number, cat: Catalog): "before" | "evaluation"`
  - `windowLabel(t_s, cat): string`: exactly `"before evaluation window (t ≤ 1 h)"` or `"evaluation window (1 h < t ≤ 6 h)"`
  - `formatClock(t_s: number): string` (`"hh:mm:ss"`)
  - `pulseBounds(t_s: number, cat: Catalog): [loExclusive: number, hiInclusive: number]` = `[max(−1, t_s − cat.time.pulse_window_s), t_s]`. The −1 floor makes the very first ticks include RAPS second 0.
- Produces, in `views.ts`:
  - `rackTc(run, k, r)`, `rackKw(run, k, r)`, `rackFree(run, k, r)`
  - `tickValue(run, k, col: TickColumn): number`
  - `startRacksIn(run, lo, hi): Set<number>`: racks of **start** events with lo < raps_t_s ≤ hi (binary search on `events.raps_t_s`).
  - `decisionsIn(run, lo, hi): number[]`: decision indices with lo < raps_t_s ≤ hi.
  - `interface DecisionView { index: number; rapsTs: number; jobId: number; nodes: number; rule: "single"|"span"; jobKw: number; tObs: number; chosen: number[]; nTies: number; chosenIsBest: boolean }`
  - `decisionAt(run, i): DecisionView`
  - `interface CandidateRow { rack: number; score: number; tc: number; committedKw: number; free: number; chosen: boolean }`
  - `candidatesFor(run, i): CandidateRow[]`: skips rows with rack 65535; `chosen` = rack ∈ `decisionAt(i).chosen`.

- [ ] **Step 1: Write failing tests:**
  - `windowState(3600)` → `"before"`; `windowState(3610)` → `"evaluation"`; `windowState(21600)` → `"evaluation"`.
  - `tickToTs(0) === 10`; `tickToTs(2159) === 21600`; `tsToTick(3610) === 360`; `tsToTick(-5) === 0`; `tsToTick(99999) === nTicks − 1`.
  - `formatClock(3610) === "01:00:10"`.
  - `pulseBounds(10)` → `[-1, 10]`; `pulseBounds(3610)` → `[3580, 3610]`.
  - `startRacksIn` on the fixture, with a known event at raps_t_s 25 on racks {2, 3}: included for (−1, 30], excluded for (25, 55].
  - `candidatesFor` returns ≤ 6 rows, sorted by score descending within rows 0–4, with exactly one `chosen` row in a single-rack decision; a fixture "span" decision has two chosen racks.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement. **Step 4:** run. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): time model and run views`.

---

### Task 4: Colour and overlay model

**Files:**
- Create: `src/model/colour.ts`, `tests/unit/colour.test.ts`

**Interfaces:**
- Produces:
  - `type Overlay = "tc" | "kw" | "occupied"`
  - `interface Scale { min: number; max: number; unit: string; label: string }`
  - `scaleFor(overlay: Overlay, cat: Catalog, seed: number): Scale`:
    - `"tc"` → the seed's `colour_scale_c`, label `"Modelled coolant °C"`;
    - `"kw"` → `[idle_kw, peak_kw]`, label `"Rack power kW (RAPS input over the interval ending at t)"`;
    - `"occupied"` → `[0, nodes_per_rack]`, label `"Occupied nodes (18 − free)"`.
  - `lutToRgb(lut: string[]): Float32Array` (256×3, values 0–1)
  - `mapValue(v: number, s: Scale, lut: Float32Array, out: Float32Array, offset: number): -1 | 0 | 1`: writes the RGB and returns −1, 0 or +1 for below, inside or above the scale.
  - `frameColours(run, k, overlay, scale, lut, out: Float32Array): { below: number; above: number }`

- [ ] **Step 1: Write failing tests:**
  - `mapValue(min)` gives LUT[0]; `mapValue(max)` gives LUT[255]; the midpoint gives LUT[127] or LUT[128] (rounded index `round((v−min)/(max−min)·255)`).
  - Below min → LUT[0] and returns −1; above max → LUT[255] and returns +1.
  - `frameColours` on a fixture frame with two racks forced above max reports `above === 2`.
  - `scaleFor("tc", cat, 2)` uses **seed 2's** range, not seed 1's.
  - `scaleFor("occupied")` gives max 18 and uses `18 − free`.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement. **Step 4:** run. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): colour scales and overlays`.

---

### Task 5: Tick player

**Files:**
- Modify (rewrite): `src/replay/player.ts`
- Create: `tests/unit/player.test.ts`

**Interfaces:**
- Produces:
  - `export const SPEEDS = [1, 2, 5, 10, 30, 60] as const` (ticks per second)
  - `class Player { constructor(nTicks: number); tick: number; playing: boolean; speed: number /* default 10 */; advance(dtMs: number): boolean; seek(k: number): void; step(dk: number): void; onChange(fn: (k: number) => void): () => void }`
  - `advance` accumulates `dtMs·speed/1000` ticks, moves by the whole number and keeps the remainder. It stops (`playing = false`) at `nTicks−1`. It returns true if the tick changed.

- [ ] **Step 1: Write failing tests:**
  - At speed 10, `advance(100)` gives +1 tick; `advance(250)` twice gives +5 ticks total (remainder kept).
  - `seek(-3)` gives 0; `seek(1e9)` gives `nTicks−1`.
  - `step(6)` gives +6; `step(-60)` from 30 gives 0.
  - Playing past the end stops at `nTicks−1` with `playing === false`.
  - `onChange` fires once per change and not on a no-op seek.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement. **Step 4:** run. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): tick-based replay player`.

---

### Task 6: 257-rack grid scene and dual viewports

**Files:**
- Create: `src/scene/rackGrid.ts`, `src/scene/dualView.ts`, `tests/unit/rackGrid.test.ts`
- Delete: `src/scene/racks.ts`, `src/schema/vizevent.ts`

**Interfaces:**
- Produces, in `rackGrid.ts`:
  - `cellOf(r: number, cols: number): { row: number; col: number }` (row = ⌊r/cols⌋, col = r mod cols)
  - `rackAt(xNorm: number, yNorm: number, grid: Catalog["grid"]): number | null`: normalised viewport coordinates with origin bottom-left; null for gaps, empty cells or outside.
  - `class RackGrid { constructor(grid: Catalog["grid"]); readonly group: THREE.Group; setColours(rgb: Float32Array): void; setPulses(racks: Set<number>): void; setPinned(r: number | null): void; setHover(r: number | null): void; dispose(): void }`
    - Tiles are an `InstancedMesh(PlaneGeometry)`, cell pitch 1.0 and tile size 0.88, laid flat in the x–y plane.
    - Empty cells (`rows·cols − n_racks`) get outline-only `LineSegments`.
    - Pulses are a second `InstancedMesh` of rings (`RingGeometry(0.30, 0.40)`, cyan `#22d3ee`) with visible count = |pulses|.
    - Pinned and hover use a white outline.
- Produces, in `dualView.ts`:
  - `class DualView { constructor(canvas: HTMLCanvasElement); render(left: RackGrid, right: RackGrid, leftEl: HTMLElement, rightEl: HTMLElement): void; resize(): void; static webglAvailable(): boolean }`
  - One `WebGLRenderer`, one `OrthographicCamera` per side fitted to the grid with 4 % padding, scissor per element rect (keep the scissor approach from the legacy `main.ts`).

- [ ] **Step 1: Write failing tests** (no WebGL needed; they test geometry and instance data):
  - For `{rows:13, cols:20, n_racks:257}`, all 257 `cellOf` results are unique, and `cellOf(256)` = `{row:12, col:16}`.
  - `RackGrid` instance count is 257, and the instance matrices give 257 **distinct** (x,y) positions. This is the regression test for the legacy `rowZ` duplication.
  - The empty-cell outline count is 3.
  - `rackAt` hits the centre of cell (row 0, col 0) → 0; the centre of (12, 16) → 256; (12, 17) → null (empty); the gap between tiles → null.
  - `setPulses(new Set([1, 5]))` sets the ring mesh count to 2.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement and delete the legacy files. **Step 4:** run. Expected: PASS. `npx tsc --noEmit` is clean.
- [ ] **Step 5: Commit:** `feat(viz): 257-rack schematic grid and dual viewports (replaces legacy 3-zone scene)`.

---

### Task 7: App shell, state store, selectors, loading and error states

**Files:**
- Modify (rewrite): `index.html`, `src/main.ts`, `src/style.css`
- Create: `src/model/store.ts`, `src/ui/header.ts`, `src/ui/status.ts`, `src/ui/fallback.ts`, `src/ui/copy.ts`, `tests/unit/store.test.ts`

**Interfaces:**
- Produces, in `store.ts`:
  - `interface AppState { experimentId: string; seed: number; comparisonId: string; tick: number; overlay: Overlay; pinnedRack: number | null; drawer: "outcome" | "why" | "about" | "rack" | null; whySide: "left" | "right" }`
  - `class Store { get(): AppState; set(p: Partial<AppState>): void; subscribe(fn: (s: AppState, prev: AppState) => void): () => void }`
  - `loadComparison(base: string, store: Store, cache: RunCache, f?: Fetcher): Promise<{ left: LoadedRun; right: LoadedRun } | "stale">`. It uses a monotonically increasing token and aborts the previous `AbortController`. It returns `"stale"` if superseded. It calls `assertComparable`.
  - `class RunCache { constructor(maxRuns = 6); get(id); put(id, run) }` (least recently used).
- Produces, in `copy.ts`, the non-headline fixed strings only:
  - app title `"ThermoRL — closed-loop FMU replay"`;
  - badge `"Replay of recorded runs · no live simulation"`;
  - legend unit labels (from Task 4);
  - empty-state texts;
  - the fallback text `"WebGL is unavailable. Showing the labelled pre-rendered figures instead."`.
- **Layout (index.html):**
  - **Header row:** title and badge; selects for Experiment (from `index.json`), Seed (from `catalog.seeds`) and Comparison (from `catalog.comparisons`); Overlay segmented control (`Coolant °C` | `Rack kW` | `Occupied`); buttons `Outcome`, `Why?`, `About this data`.
  - **Identity strip:** `experiment.workload_label · experiment.system_label · experiment.scenario · seed note`.
  - **Main:** two panels (`#view-left`, `#view-right`). Each has a heading with the exact policy ID and a badge (`C′ verified (6 h repeat)` only when `c_prime_status === "verified_E12"`, otherwise `not directly repeated`). The legend (Task 8) sits at the right edge.
  - **Below:** `#timeline` (Task 8) and `#controls`: play/pause, step −10 min, −1 min, −1 tick, +1 tick, +1 min, +10 min, a "Jump to evaluation start" button (tick 360), a speed select (`SPEEDS`), the scrubber, and the clock `hh:mm:ss · tick k/2160 · <windowLabel>`.
  - **Right side:** a drawer container (Tasks 9–10).
- **Query parameters:** `?data=<dir>` (default `replay`; e2e uses `replay-fixture`), `?exp=`, `?seed=`, `?cmp=`, `?t=` (seconds). State changes update the URL with `history.replaceState`, so a view can be bookmarked.
- **Status overlay (`status.ts`):**
  - while loading: per-file progress "Loading power_balance_seed1/rack_tc.f32 (3/16)";
  - on `ReplayError`: a red panel with `kind`, `file`, and the hint "Run `npm run sync-replay` (exports must exist under thermoRL/backend/experiments/summit/<EID>/exports/replay_v1)";
  - nothing renders behind an error.
- **Fallback (`fallback.ts`):** if `DualView.webglAvailable()` is false, show the PNG and GIF links from `public/fallback/<EID>/` (Task 11) with their captions.

- [ ] **Step 1: Write failing tests** (`store.test.ts`):
  - `set` merges and notifies with the previous state.
  - **Race:** start `loadComparison` for seed 1 with a fetcher that delays 50 ms, immediately start it for seed 2 with no delay. The first resolves `"stale"`, the second resolves runs whose `meta.seed === 2`, and the store renders only seed 2. **Review Focus 5.**
  - `RunCache` evicts the least recently used entry beyond 6 entries.
  - URL round-trip: `stateFromQuery("?exp=EFIX&seed=2&cmp=packing_vs_tp&t=3610")` → tick 360, seed 2.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement the store, shell, header, status and fallback. Wire `main.ts`: load index → experiment → comparison, then a render loop that calls `player.advance`, updates both `RackGrid`s via `frameColours`, applies pulses from `startRacksIn(pulseBounds(t))` per side, and calls `dualView.render`. **Step 4:** run. Expected: PASS. `npx tsc --noEmit` is clean.
- [ ] **Step 5: Manual check:**
  - `npm run make-fixture && npx vite --open "/?data=replay-fixture"`: two grids, scrubbing works, and the experiment, seed and comparison selects switch views.
  - Corrupt one fixture file by hand: the error panel names it.
- [ ] **Step 6: Commit:** `feat(viz): app shell, state store, selectors, loading/error/fallback`.

---

### Task 8: Legend, tooltip, timeline strip, pinned-rack sparkline

**Files:**
- Create: `src/ui/legend.ts`, `src/ui/tooltip.ts`, `src/ui/timeline.ts`, `src/ui/sparkline.ts`, `tests/unit/timeline.test.ts`, `tests/unit/tooltip.test.ts`

**Interfaces:**
- Consumes: Tasks 3, 4 and 7.
- Produces:
  - `renderLegend(el, scale: Scale, lut, outOfRange: { below: number; above: number }): void`. Shows the gradient, min/max to 2 decimals, the unit label, `"Scale fixed per experiment and seed; E11 and E12 scales differ"`, and, when the counts are > 0, `"n racks outside scale this frame"`.
  - `tooltipHtml(run, k, r, scale, cat): string`. Rack index (row, col); `Modelled coolant 41.23 °C`; `Rack power 21.4 kW`; `Free nodes 7 / 18`; `outside scale` when applicable; then `catalog.strings.interval_semantics` (small type).
  - `class Timeline { constructor(el: HTMLCanvasElement, cat: Catalog); setRuns(left, right, labels: [string, string]): void; setCursor(k): void; onSeek(fn: (k) => void): void; static xToTick(x: number, width: number, nTicks: number): number; static tickToX(k: number, width: number, nTicks: number): number }`.
    - Draws per-tick `maxrack_c` (solid line) and `maxrack_c − minrack_c` spread (lower sub-panel) for both runs, in two fixed colours with a legend.
    - Shades t ≤ 3600 grey, labelled "before evaluation window".
    - The y-axis is labelled "Max-rack modelled coolant °C".
    - Pre-renders the series to an offscreen canvas once per `setRuns`; `setCursor` only redraws the cursor. Clicking or dragging seeks.
  - `renderSparkline(el, left, right, r, cat): void`: the pinned rack's `t_c` across the episode for both runs (with evaluation-window shading and a cursor), plus a second small panel of `kw`. The drawer title is `"Rack r (row, col)"`.
- **Interaction:**
  - Hover over a tile shows the tooltip (via `rackAt`).
  - Click pins the rack (`store.pinnedRack`, `drawer = "rack"`), highlights that rack in both panels and opens the sparkline drawer.
  - `Esc` unpins.

- [ ] **Step 1: Write failing tests:**
  - `tooltipHtml` for a fixture value above scale contains `"outside scale"`, and contains `"Modelled coolant"` and `"interval"` (from semantics).
  - `Timeline.xToTick` maps x = 0 → 0 and x = width → nTicks−1, is monotonic, and inverts `Timeline.tickToX` (round trip within one tick).
  - The shaded region's end x equals `Timeline.tickToX(359, width, nTicks)`, i.e. t_s 3600.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement. **Step 4:** run. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): legend, tooltip, timeline and pinned-rack sparkline`.

---

### Task 9: Outcome card, About panel, forbidden-copy guard

**Files:**
- Create: `src/ui/outcomeCard.ts`, `src/ui/aboutPanel.ts`, `tests/unit/outcome.test.ts`, `tests/unit/forbiddenCopy.test.ts`

**Interfaces:**
- Produces: `renderOutcome(el, outcome: FrozenOutcome, cat: Catalog, active: { seed: number; left: PolicyId; right: PolicyId }): void`, rendering in this order:
  1. `outcome.headline`, in large type;
  2. `outcome.rule`;
  3. a per-seed table of `decision.per_seed[s].power_minus_thermal_c` and `packing_minus_thermal_c`, **all seeds**, shown to 3 decimals (full precision in the `title` attribute), with the ≥ 0.5 °C requirement noted in the column header;
  4. a five-policy × seeds table of `maxrack_mean_c` from `outcome.metrics` (3 decimals), with the active seed's column and the two active policies' rows highlighted;
  5. `outcome.experiment_statement`;
  6. the footer `"The preregistered rule decides; this viewer is descriptive."`

  No computed differences beyond what `decision.json` contains, no ranking, no colour-coding of "good/bad".
- Produces: `renderAbout(el, cat, outcome): void`, rendering:
  - S2 (`cat.strings.s2`);
  - interval semantics;
  - the pulse rule;
  - the precision note;
  - `outcome.reproducibility_scope`;
  - fixed bullets in `copy.ts`: "Warm-up is capped (7200 s), not settled"; "G1 thermal predictor parameters are a frozen heuristic"; "Temperatures are modelled by the POWER9 cooling FMU, not measured on hardware"; "45 °C is a reference value only";
  - a link to `docs/results/2026-11-parasparam-demo-results.md` (as a GitHub URL on the `feat/parasparam-demo` branch).
- The Outcome drawer is **open by default** on first load.

- [ ] **Step 1: Write failing tests:**
  - `renderOutcome` with the fixture shows `headline` verbatim and one row per seed in the gap table; the full-precision value appears in a `title` attribute; there is no element whose text matches `/winner|best|significan/i`.
  - `renderAbout` includes `cat.strings.s2` **exactly** (string equality on `textContent`).
  - `forbiddenCopy.test.ts` scans every file under `src/` and `index.html` (as text) for the forbidden list in Global Constraints (case-insensitive, word-boundary). Expected: zero hits. The only allowed exception is the internal identifier `unavailable_fields`, which may be *read* but whose values are never rendered.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement. **Step 4:** run. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): frozen-outcome card, about panel, forbidden-copy guard`.

---

### Task 10: "Why this rack?" drawer

**Files:**
- Create: `src/ui/whyDrawer.ts`, `tests/unit/whyDrawer.test.ts`

**Interfaces:**
- Consumes: `decisionsIn`, `decisionAt`, `candidatesFor` (Task 3) and `pulseBounds` (Task 3).
- Produces: `renderWhy(el, run: LoadedRun, side: "left" | "right", t_s: number, cat: Catalog, page = 0): void`.
  - **Header:** `"Job starts in the 30 s ending at hh:mm:ss — <policy> (seed s)"`; a toggle for the left/right side; the count `"n decisions"`.
  - **List:** 50 per page, with Prev/Next buttons. Each item shows job id, nodes required, rule, chosen rack(s), the logged-at time `t_obs_s`, and the RAPS start second.
  - **Expanding an item** shows the candidates table: rack | logged score | coolant °C | committed kW | free; chosen rows highlighted. Then `"Ties at logged precision: n"`. If `!chosenIsBest`, the note `"Chosen rack is not the top logged score — the live decision used full precision."`
  - `catalog.strings.precision_note` is **always** shown at the drawer top.
  - **Empty window:** `"No job starts in this 30 s window."`
  - Never compute new scores; never show other policies' hypothetical choices.

- [ ] **Step 1: Write failing tests:**
  - Fixture tick 119 (window (1170, 1200], no decisions) → the empty text.
  - Fixture tick 360 (the 120-decision burst) → page 0 shows 50 items and "Next" is enabled; page 2 shows 20.
  - An expanded item's table has ≤ 6 rows, highlighted rows equal the chosen racks, and the precision note text is present verbatim.
  - A fixture decision with `chosen_is_logged_best = false` shows the full-precision note.
- [ ] **Step 2:** run. Expected: FAIL. **Step 3:** implement. **Step 4:** run. Expected: PASS.
- [ ] **Step 5: Commit:** `feat(viz): logged decision-context drawer`.

---

### Task 11: Sync script, Vite config, fallback assets, legacy label

**Files:**
- Create: `scripts/sync-replay.mjs`, `thermoRL/frontend/LEGACY.md` (force-add)
- Modify: `vite.config.ts`

**Interfaces:**
- `node scripts/sync-replay.mjs [--source <repoRoot>]`. For each `EID` in [`E12_g4_alibaba` (default), `E11_g4_synthetic`]:
  - require `thermoRL/backend/experiments/summit/<EID>/exports/replay_v1/catalog.json`; exit code 2 with a clear message if it is absent;
  - for every `runs/*/run.json`, verify each `files[*]` byte length and SHA-256 **before** copying;
  - copy to `public/replay/<EID>/` (recreate that directory; it is gitignored);
  - write `public/replay/index.json` (contract §2);
  - copy `thermoRL/backend/experiments/summit/<EID>/plots/demo/*.{png,gif}` to `public/fallback/<EID>/` after verifying them against `provenance/demo_asset_inventory.json`;
  - print the totals (files, bytes).
- `vite.config.ts`: `base: "./"`, `publicDir: "public"`, `build.outDir: "dist"`, `emptyOutDir: true` (only `dist/`, which is gitignored). Remove nothing else.
- `LEGACY.md`: "`thermorl/`, `artifacts/bundles/demo_ramp/`, `tests/`, `config/` and `pyproject.toml` in this directory are the legacy three-zone simulator and a constructed 24-frame fixture. They are not FMU evidence, are not used by the viewer, and must not be run or reconnected. The viewer replays `replay_v1` exports of the recorded Summit FMU runs (see `viz/README_DEMO.md`)."

- [ ] **Step 1:** run `node scripts/sync-replay.mjs --source <fixture-tree>` against a test tree: write `buildFixture` output under a temp `thermoRL/backend/experiments/summit/EFIX/exports/replay_v1/` layout and pass `--experiments EFIX`. Add an `--experiments` option, defaulting to the two real IDs.
  - **Expected:** exit 0 and `public/replay/index.json` lists EFIX.
  - Corrupt one fixture file and run again. **Expected:** exit 1, naming the file, with nothing copied for that experiment.
- [ ] **Step 2:** implement until both behaviours hold. Record them in a `node:test` file `scripts/sync-replay.test.mjs`, run with `node --test scripts/`.
- [ ] **Step 3: Commit:** `feat(viz): verified sync of replay exports and fallback assets; mark legacy frontend`.

---

### Task 12: End-to-end smoke (fixture), build, performance

**Files:**
- Create: `playwright.config.ts`, `tests/e2e/smoke.spec.ts`

**Interfaces:**
- Playwright: Chromium only; `webServer: { command: "npm run make-fixture && npx vite preview --port 4173", port: 4173 }` after `vite build`. Use `baseURL` with `?data=replay-fixture`.

- [ ] **Step 1: Write `smoke.spec.ts`:**
  - the page shows `"ThermoRL — closed-loop FMU replay"` and the fixture headline;
  - the canvas exists and WebGL is available in headless Chromium;
  - step to t = 3600 s and read "before evaluation window"; step +1 and read "evaluation window";
  - open Why? at a fixture burst tick and see ≥ 1 decision row with the precision note;
  - switch the seed to 2 and the legend min/max text changes;
  - hover a tile and see a tooltip containing "Modelled coolant";
  - `document.body.innerText` does not match the forbidden regex from Task 9;
  - save screenshots to `test-artifacts/`.
- [ ] **Step 2:** `npm run build && npm run e2e`. Expected: all pass. Fix the code (not the tests) on failure.
- [ ] **Step 3:** `npm test && npx tsc --noEmit && npm run build`. Expected: clean.
- [ ] **Step 4: Commit:** `test(viz): playwright smoke on fixture bundle`.

---

### Task 13: Real-data integration and demo packaging → CK-C (requires CK-B exports)

**Files:**
- Create: `thermoRL/frontend/viz/README_DEMO.md` (force-add), `docs/results/demo_replay_check.json`
- Modify: `thermoRL/backend/experiments/DEMO.md` (add one row)

- [ ] **Step 1:** `npm run sync-replay`. **Expected:** both experiments verified; the totals printed; `public/replay/index.json` has E12 as the default.
- [ ] **Step 2: Real-data spot checks** (manual, recorded in `demo_replay_check.json`):
  - for E12 seed 1 `pb_vs_tp`: the legend reads **38.70–42.41 °C**;
  - the timeline max-rack curves match `plots/demo/timeseries_seed1.png` by eye (shape, ~42.4 °C packing peak at ~2.7 h in `packing_vs_tp`);
  - the outcome card PB−TP values read 0.178 / 0.077 / 0.109;
  - E11 seed 1: the legend reads **39.25–56.23 °C**;
  - the `C′ verified` badge appears only on E12 `thermal_predictive` seed 1.
- [ ] **Step 3:** run `npm run e2e` with an extra project `real` that loads `?data=replay` and repeats the smoke assertions on E12 seed 1. **Expected:** pass.
- [ ] **Step 4: Performance** on the presenting Mac (Chrome, `npm run build && npx vite preview`):
  - time to first render of E12 seed 1;
  - steady FPS at speed 10 and at speed 60, over 30 s (DevTools Performance);
  - JS heap after loading three comparisons.

  **Targets:** first render ≤ 5 s; ≥ 50 fps; heap ≤ 400 MB. Record the numbers; if a target is missed, report it rather than tuning the data.
- [ ] **Step 5: `README_DEMO.md`:**
  - how to run (`npm ci`, `npm run sync-replay`, `npm run dev`, or `build` + `preview`);
  - the data chain (FMU runs → raw ledgers → `replay_v1` exporter → hash-verified viewer);
  - the 5-minute walkthrough (below);
  - the fallback;
  - the forbidden claims.

  **Walkthrough:**
  1. Open E12 `pb_vs_tp` seed 1 and read the header and the outcome card.
  2. Play the 2–3 h burst; pause and open Why?.
  3. Scrub across 1 h to show the window.
  4. Switch to `packing_vs_tp` to show concentration under packing at identical power.
  5. Switch the seed to 2 to show the second independent condition.
  6. Switch to E11 to show a different regime and scale (packing ≈ TP).
  7. Open About this data.
- [ ] **Step 6: `DEMO.md` row:** asset `thermoRL/frontend/viz` (replay viewer); shows recorded E11/E12 runs, all seeds; allowed claim: placement changes the spatial distribution at identical IT power, plus the frozen negative outcome; must NOT be used for: a validated benefit, savings, live simulation, or hardware temperatures.
- [ ] **Step 7:** write `docs/results/demo_replay_check.json`: commit SHA; Node and npm versions; vitest and playwright counts; synced bytes per experiment; the spot-check results; the performance numbers; the list of screenshots.
- [ ] **Step 8: Commit:** `docs(demo): replay viewer walkthrough, asset map row, acceptance record`. Push. **STOP (CK-C)** and report: commits, test counts, sizes, performance, spot checks, and any deviations.

---

## Acceptance criteria (CK-C)

- `npm test`, `npx tsc --noEmit`, `npm run build` and `npm run e2e` (fixture and real) all pass.
- **Data integrity:** the viewer renders only hash-verified `replay_v1` data. Corrupt or missing files produce a named error, never a partial view.
- **Header:** shows the experiment, workload label, system label, scenario, seed and its note, the exact policy IDs, and a C′ badge only on E12 TP seed 1.
- **Main view:** the 257-rack schematic in modelled °C on the fixed per-seed scale, with legend values and out-of-range counts; placement rings with the pulse rule visible in About.
- **Time:** an evaluation-window label and shading that are exact at 3600 s / 3610 s.
- **Outcome card:** verbatim headline, rule and statement; all seeds' gaps; no rankings or winners.
- **Why drawer:** shows only logged context, always with the precision note.
- **Legacy removed:** no PUE, carbon, SLO, emergency, λ or THI UI anywhere (guarded by test).
- The legacy simulator and fixture are untouched and labelled. No file under `thermoRL/backend/` changed except `experiments/DEMO.md` (one row).
- The walkthrough is reproducible from `README_DEMO.md`; the performance numbers are recorded.
