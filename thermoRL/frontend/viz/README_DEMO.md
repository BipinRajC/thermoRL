# ThermoRL replay viewer — demo guide

An interactive replay of **recorded** closed-loop FMU runs (E11 synthetic workload, E12 Alibaba-derived workload), each with 3 seeds and 3 policies (`packing`, `power_balance`, `thermal_predictive`). Nothing is simulated in the browser: every value on screen is read from hash-verified export files, and the header badge says so ("Replay of recorded runs · no live simulation").

## Run it

From `thermoRL/frontend/viz`:

```bash
npm ci
npm run sync-replay      # copies + verifies the exports (read-only on the backend tree)
npm run dev              # sync (if present) + Vite dev server
```

or a production build served locally:

```bash
npm run build            # tsc --noEmit + vite build (copies public/ including the replay data)
npm run preview          # serves dist/ at http://localhost:4173
```

- `npm run sync-replay` reads `thermoRL/backend/experiments/summit/<EID>/exports/replay_v1` (`E12_g4_alibaba`, `E11_g4_synthetic`), the labelled figures under `plots/demo/`, and `provenance/demo_asset_inventory.json`. It checks every file hash and writes `public/replay/` (about 79 MiB for E12 and 52 MiB for E11) and `public/fallback/`. Both folders are generated and not committed.
- E12 is the default experiment. Deep links look like `/?data=replay&exp=E12_g4_alibaba&seed=1&cmp=pb_vs_tp&t=6950`.
- If a file is missing or its hash differs, the viewer shows an error panel naming the file and the kind of problem, and no partial view.
- Checks: `npm test` (unit), `npx tsc --noEmit`, `npm run e2e` (a `fixture` project and a `real` project against the synced exports), `npm run test:scripts`. `node scripts/perf-check.mjs --base http://localhost:4173 [--headed]` repeats the timing and frame-rate measurements recorded in `docs/results/demo_replay_check.json`.

## Data chain

1. **FMU runs.** RAPS places the workload's jobs on exact nodes; loss-inclusive rack power drives the Summit POWER9 cooling FMU; its published coolant values feed later placement decisions.
2. **Raw ledgers.** Per run: run manifest, per-interval rack records, placement decisions, job events.
3. **`replay_v1` exporter.** Converts a run into compact files (rack coolant °C, rack kW, free nodes, per-tick summary, events, decisions, top-candidates table) plus `catalog.json` and `frozen_outcome.json`, each with a SHA-256. Headline strings are copied verbatim from frozen results. The contract is `docs/superpowers/specs/2026-11-01-replay-v1-contract.md`.
4. **Sync.** `scripts/sync-replay.mjs` copies the tree read-only and re-verifies the hashes.
5. **Viewer.** The browser verifies each file again before drawing. Time maps as tick k ↔ t = 10 (k + 1) s; the evaluation window is 3600 s < t ≤ 21600 s.

## Five-minute walkthrough

1. **Open E12, `power_balance` vs `thermal_predictive`, seed 1.** Read the header (experiment, workload, system, scenario, seed note, exact policy IDs) and the Outcome card: headline, rule, the per-seed gaps (0.178 / 0.077 / 0.109 °C), the five-policy table and the experiment statement. The legend reads 38.70–42.41 °C (modelled coolant).
2. **Play the burst, then pause and open Why?** Seek to about 1 h 50 min (`&t=6600`) and press Play at 10 ticks/s. The job-start burst is at 01:55:50 (tick 694; 493 decisions in the 30 s window). Pause there and open **Why?**: pages of 50 decisions; expand one to see up to 6 logged candidate racks. The precision note stays visible: only logged six-decimal context is shown and nothing is re-scored. Keep playing to follow the temperature rise through about 3 h.
3. **Scrub across 1 h.** Use *Jump to evaluation start* and the ±1 tick buttons: the clock reads `01:00:00` as "before evaluation window" and `01:00:10` as "evaluation window". The shaded start of the timeline is the pre-window hour.
4. **Switch the comparison to `packing_vs_tp`.** Under packing the maximum is higher and more concentrated, with identical IT power in both panels (packing peak about 42.4 °C near 2.7 h in seed 1).
5. **Switch the seed to 2.** The scale changes (38.41–42.64 °C). Seed 3 is about seed 2 shifted by 33 s, so E12 has about two independent workload conditions (stated in the seed note).
6. **Switch to E11.** A different regime and scale (39.25–56.23 °C for seed 1); here packing and `thermal_predictive` are close and the gaps change sign across seeds. E11 and E12 are never shown in one view.
7. **Open About this data.** The S2 timing statement, interval semantics, pulse rule, precision note, reproducibility scope and the limits list.

Tips: hover a rack for modelled coolant and rack power; click a rack to pin it (sparklines in the drawer); the overlays *Rack kW* and *Occupied* use fixed scales; keyboard: Space, ←/→, Shift+←/→.

## Fallback

If WebGL is unavailable the viewer shows labelled pre-rendered figures instead (`public/fallback/<EID>/`: heatmaps, time series and two animations for seed 1, copied by the sync script). The same labelled figures are listed in `thermoRL/backend/experiments/DEMO.md`; use them directly if a browser is not an option.

## What may be said

- These are recorded runs of the FMU-driven closed loop, replayed; there is no live simulation.
- Temperatures are modelled coolant °C on a scale fixed per experiment and seed; the E11 and E12 scales differ.
- Placement changes the spatial distribution of rack temperatures at identical IT power and timing.
- The frozen outcome is the headline on the Outcome card: "no material value on the homogeneous twin". The preregistered rule decides; the viewer is descriptive only, and no validated benefit is claimed.
- Rings mark recent job starts; they are not a cooling effect.
- Why? shows logged context only; it does not reconstruct decisions.
- The `C′ verified (6 h repeat)` badge applies to E12 `thermal_predictive` seed 1 only; every other run reads "not directly repeated".

## Limits and S2

The About panel (button **About this data**) carries the S2 statement, the interval semantics, the pulse rule, the precision note, the reproducibility scope and the list of limits, all rendered verbatim from the export. The schematic grid is a layout of 257 racks, not a floor plan. Read the About panel before presenting any number.
