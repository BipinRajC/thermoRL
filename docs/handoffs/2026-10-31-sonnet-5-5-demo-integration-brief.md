# Sonnet 5.5 Brief — ThermoRL Demo Integration (Repository Repair → FMU Replay Export → Frontend)

**Status:** ready to execute **only after Bipin approves** the decisions in `docs/reviews/2026-10-31-opus-post-c6-integration-review.md` §6. Where a decision is not yet approved, follow the default marked **[default]** and say so in your report.

**Author:** Opus (independent reviewer and integration architect), 2026-10-31. **Base:** `feat/parasparam-demo` at `beafb51` or later.

> **Progress update (2026-10-31, done on the Mac by Opus at Bipin's request):**
> - **A1 is DONE** in commit `a5d3824`. `project_root()` lives in `systems.py` and `application_source_hashes()` in `provenance.py`; the runner, bench and probes use them. `tests/unit/test_relocation.py` was added and the stale path in `test_e11_review_fixes.py:107` was fixed. Non-FMU tier on the Mac: 196 passed, 4 failed. All 4 failures are the E10-ledger tests, which pass only after A2 re-tracks those files.
> - **A3 is PARTLY DONE:** `docs/results/path_mapping.md` was added, and the runbook and results-note links and backup wording were updated. **Still to do on Arch, after A2:** the `DEMO.md`, `INDEX.md` and backend README link/backup updates (those files are absent from git until A2), and `uv sync --frozen`.
> - **A2 tool ready:** `docs/handoffs/scripts/retrack_dropped_files.py`. Run it as a dry run first, then `--apply`. It hash-verifies every file, refuses E11/E12 raw `runs/`, stages paths one at a time and writes `docs/results/post_rename_retrack_check.json`. It never commits.
> - **Next on Arch:** A2 → the rest of A3 → A4 (fresh on-disk clone; expect all ≈ 200 tests to pass) → **CK-A STOP**.

**You have no prior conversation context.** Everything you need is in this brief and the files it names.

---

## 0. What this project is and what you must not change

ThermoRL couples ExaDigiT RAPS (job scheduling, exact-node placement, rack power) to ORNL's POWER9 Modelica cooling FMU for **Summit** (257 racks, 18 nodes each, 4626 nodes, 10 s ticks). It compared five frozen placement policies: `packing`, `node_balance`, `power_balance`, `coolest_rack` and `thermal_predictive`. There were two preregistered matrices, each 5 policies × 3 seeds × 6 h:
- **E11** (synthetic workload);
- **E12** (Alibaba-derived workload).

**Frozen outcomes (never alter or reinterpret):**
- **Both experiments: "no material value on the homogeneous twin"; `value_beyond_power=false`.** The rule: `power_balance` minus `thermal_predictive` time-mean max-rack coolant over the window 3600 < t_s ≤ 21600 must be ≥ 0.5 °C in **every** seed.
  - E11 PB−TP: +0.342, −0.147, −0.071 °C.
  - E12 PB−TP: +0.178, +0.077, +0.109 °C.
- **E11 only:** "packing ≈ TP on the primary metric".
- **E12, use this exact wording:**
  > In E12 (small, low-density, bursty Alibaba-derived jobs), thermal_predictive had the lowest and packing the highest time-mean max-rack coolant temperature in all three seeds (PB−TP 0.08–0.18 °C; packing−TP 0.35–0.44 °C). This is below the preregistered 0.5 °C materiality threshold, rests on about two independent workload conditions (seed 3 ≈ seed 2 shifted 33 s), and is descriptive only.
- **Reproducibility scope, exactly:**
  - E10 packing seed 1, 2 h fresh-process repeat;
  - E11 seed-1 packing/PB 2 h prefixes;
  - E12 TP seed 1, 6 h byte-identical repeat;
  - D7: a same-machine clone, tests and one smoke.

  Nothing else was repeated.
- **S2, verbatim** (show it in the viewer's "About this data" panel):
  > published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.
- **Forbidden claims anywhere** (UI, captions, docs, commit messages):
  - "thermal-aware placement works", "removes hotspots", or any °C saving as a benefit;
  - significance, or any policy "winner";
  - whole-matrix or cross-machine reproducibility;
  - hardware or real Summit temperatures, safety limits;
  - PUE, energy or cooling-power savings, carbon, lifetime;
  - RL, surrogate or heterogeneous-zone results;
  - any identified physical mechanism.

  Temperatures are **modelled coolant °C**. 45 °C is a reference value only.

**Never:**
- run a new simulation, FMU, `run.py`, `run_matrix`, the report CLI, `make_demo_bundle.py` or the legacy simulator in `thermoRL/frontend/thermorl/`;
- change policies, scheduler, metrics, thresholds, workloads, seeds, ρ, horizon, warm-up, G1, FMU, configs or RAPS (`sim-raps/`);
- modify, regenerate or overwrite any existing experiment artifact: results, plots, provenance, manifests, inventories, READMEs' frozen sections, `C4-execution-*` documents;
- use `git add -A`, force-add a directory, or commit any file under a `runs/` directory other than the 13 E10 files listed in A2;
- push to any branch other than `feat/parasparam-demo`, or open a PR.

**Escalate (STOP and report)** if:
- anything requires a new run, a science change, or editing a frozen artifact;
- a hash or metric check fails;
- raw ledgers are missing;
- a size budget would be exceeded;
- a test fails for a reason you cannot fix without touching frozen code or data.

---

## Layout and key facts

| Thing | Path |
|---|---|
| Backend package root (`PROJECT`) | `thermoRL/backend/` (package `thermorl2/`, `tests/`, `experiments/`, `pyproject.toml`, `uv.lock`) |
| Frontend viewer | `thermoRL/frontend/viz/` (Vite 6 + TypeScript + Three.js 0.170) |
| Legacy frontend simulator and fixture | `thermoRL/frontend/thermorl/`, `thermoRL/frontend/artifacts/bundles/demo_ramp/` (**legacy; do not run or reconnect**) |
| E11 / E12 | `thermoRL/backend/experiments/summit/E11_g4_synthetic/`, `.../E12_g4_alibaba/` |
| Raw run ledgers (gitignored; on Arch only) | `<EID>/runs/<policy>_seed<s>/{manifest.json,intervals.parquet,decisions.jsonl,provenance/{job_events.jsonl,thermal_publications.jsonl,decision_latency.jsonl}}` |
| Frozen summaries (tracked) | `<EID>/results/{decision.json,metrics.csv,summary.json,invariants.json}` |
| Labelled fallback assets (tracked) | `<EID>/plots/demo/*.png|*.gif` (+ `provenance/demo_asset_inventory.json`) |
| Historical paths | Records before `c09f735` say `thermoRL/thermorl-v2/` (= backend) and `thermoRL/thermoRL-new/` (= frontend). **Do not rewrite them.** |

**Ledger semantics** (from the source; do not "fix"):
- **`intervals.parquet`:** one row per (t_s, rack). t_s = 10, 20, …, 21600 (2160 endpoints). Columns: `t_s, rack, kw, t_c, pump_kw, free, it_kw_total, n_running, n_queued, scenario_active`.
  - `kw`, `free`, `it_kw_total`, `n_running` and `n_queued` are **RAPS inputs at t_s − 10**, held over (t_s − 10, t_s].
  - `t_c` and `pump_kw` are **FMU endpoint outputs at t_s**.
- **`decisions.jsonl`:** one line per placement, in `decision_index` order. 14 keys: `t_s` (integer RAPS second), `job_id`, `nodes_required`, `policy`, `rule` (`single`/`span`), `racks` (chosen, ordered), `nodes`, `job_kw`, `scores` (257, logged at 6 d.p., higher is better), `t_c` (257, 6 d.p.), `committed_kw` (257), `free` (257), `t_obs_s`, `latency_us` (always null).
  - Logged context is **six-decimal**. About 5 % of TP and about 10 % of coolest_rack live choices were decided by margins below logging precision. Never claim exact reconstruction.
- **`job_events.jsonl`:** `{event:"start", decision_index, job_id, nodes, t_s}` and `{event:"complete", job_id, nodes, t_s}`. rack = node // 18.
- **Schematic grid:** 13 rows × 20 columns, 257 cells used, 3 empty, `origin='lower'`, rack r at (row = r // 20, col = r % 20). This is the same schematic as the existing GIFs. **It is not a floor plan.**
- **Colour scales:** within-experiment and shared across all five seed-1 policies (from `demo_asset_inventory.json` / C6):
  - E11 **39.252402–56.233641 °C**;
  - E12 **38.702230–42.413286 °C**.

  Never pair the two experiments in one view.

---

# PART A — Backend repair and replay export (must run on **Arch**: `/home/bipin/thermoRL`)

### A0. Sync and preflight
`git fetch && git checkout feat/parasparam-demo && git pull --ff-only`. Record HEAD.

Confirm on Arch that these exist locally:
- all 81 untracked mapped files listed in `docs/handoffs/2026-10-31-post-c6-review-evidence.json` → `dropped_tracked_files[*].current_local_path`;
- the E11/E12 `runs/` ledgers.

If any is missing, STOP.

### A1. Relocation fixes (one commit: `fix(backend): relocation-safe workload and source paths`)
1. **`thermorl2/raps_adapter/runner.py:54`:** replace `repo_root()/'thermoRL/thermorl-v2'/path` with `PROJECT/path`, where `PROJECT = Path(__file__).resolve().parents[2]` (identical to `core/metrics.py:22`).
   - Keep `manifest['workload_path']` exactly as configured (relative).
2. **Source maps:** at `runner.py:128-129`, `experiments/bench.py:46-47` and `experiments/probes.py:196-197`, replace `repo_root() / "thermoRL/thermorl-v2/thermorl2"` with `PROJECT / "thermorl2"`.
   - Keys stay `relative_to(repo_root())`, which now yields `thermoRL/backend/thermorl2/...`.
   - Put `PROJECT` in one shared helper (for example in `systems.py` or `provenance.py`) and reuse it. No other behaviour change.
3. **`tests/unit/test_e11_review_fixes.py:107`:** update the path to `thermoRL/backend/...`.
4. **New tests** (`tests/unit/test_relocation.py`):
   - (a) workload resolution from a relative path under `thermoRL/backend` works **while asserting that `repo_root()/'thermoRL/thermorl-v2'` does not exist** (skip the assertion if it does, and record that);
   - (b) the runner, bench and probes source collectors each return ≥ 39 `thermorl2/*.py` entries whose keys start with `thermoRL/backend/thermorl2/`;
   - (c) `grep` finds no `thermorl-v2` literal in `thermorl2/**/*.py` (comments that cite history are allowed only in `core/kernels/*` headers, which mention `thermoRL-new`).
5. Do **not** touch historical manifests, inventories, evidence or E12 comparison logic.

### A2. Re-track the 81 dropped files (one commit: `chore(repo): re-track files dropped by directory rename`)
- **[default D-A: retain all 81]**
- Write a small one-off script (not committed, or committed under `docs/handoffs/scripts/` if useful). For every entry in `dropped_tracked_files`, it must:
  - assert `sha256(current_local_path) == historical_sha256` and `== current_sha256`;
  - assert the path is not under E11/E12 `runs/`;
  - then run `git add -f -- <current_local_path>` **one path at a time**.
- Expect exactly 81 staged additions. `git diff --cached --stat` must list only those paths. The only `runs/` files allowed are the 13 E10 files under `E10_c2_vertical_slice/runs/`.
- **[default D-B(i)]** Do **not** change `.gitignore` rules unless Bipin approved D-B(ii).
- Verify with `git ls-files` that `thermoRL/backend/experiments/summit/E1{1,2}_*/README.md`, `experiments/INDEX.md`, `experiments/DEMO.md` and `thermoRL/backend/README.md` are tracked.
- Re-verify the 12 frozen README sections against each experiment's `provenance/preregistration.json` / frozen-section records. Record this in `docs/results/post_rename_repair_check.json` (new file, `open('x')`).

### A3. Environment and navigation (one commit: `docs(repo): post-rename path mapping and living-doc links`)
1. `uv sync --frozen` from `thermoRL/backend`, with no lock change. Verify `python -c "import thermorl2,raps;print(thermorl2.__file__)"` **from the repository root**, not the backend directory, and that it resolves to `thermoRL/backend/thermorl2`.
2. Create `docs/results/path_mapping.md`: `thermorl-v2 → backend`, `thermoRL-new → frontend`, rename commit `c09f735`, and the rule that historical records keep their old paths.
3. Update **only living navigation documents**:
   - `docs/results/2026-11-parasparam-demo-results.md` (links; replace "Raw backup remains pending…" with "Raw backup waived by Bipin on 2026-10-31; raw ledgers remain local on Arch");
   - `docs/results/runbook.md` (links, commands, cwd);
   - `thermoRL/backend/experiments/DEMO.md` (links; the same backup line);
   - `thermoRL/backend/README.md`;
   - `thermoRL/backend/experiments/INDEX.md`.
4. **Do not edit** checkpoints `C1`–`C6`, reviews, handoffs or experiment READMEs' frozen sections.

### A4. Acceptance CK-A (STOP point)
- Fresh **on-disk** clone of the pushed HEAD (for example `~/thermorl-postrename-clone`; not `/tmp`, which hit a quota before):
  - `uv sync --frozen`;
  - `uv run pytest tests/unit tests/integration -q`.
  - **Required: all pass**, about 199 including the new tests.
- Also run the same tier in the working repo.
- **[default D-C: no FMU smoke]** Only if Bipin approved D-C: exactly one `uv run python -m thermorl2.experiments.fmu_smoke --system summit` in the clone.
- Record SHA, commands, counts, wall time and any smoke JSON in `docs/results/post_rename_acceptance.json`.
- Push. **STOP and report to Bipin** before A5. Include the test counts and the staged/committed path list.

### A5. Replay exporter (after the CK-A go-ahead)
**File:** `thermoRL/backend/thermorl2/experiments/replay_export.py`, CLI `python -m thermorl2.experiments.replay_export --experiment-dir experiments/summit/<EID> --policies packing,power_balance,thermal_predictive --seed 1`.

**Rules:**
- **Read-only** with respect to every existing file.
- **Stream** `decisions.jsonl` line by line. Do not use `core.metrics.load_run` for decisions: E12 files are about 200 MB, and parsing them whole costs about 600 MB of RAM.
- `pandas.read_parquet` with explicit columns for intervals.
- Write with `open('x')` into a **new** directory `experiments/summit/<EID>/exports/replay_v1/`. Refuse if it exists.
- No FMU, RAPS or scorer imports. The exporter must not rescore anything.

**Output layout:**
```
exports/replay_v1/
  catalog.json                         # experiment-level index (schema below)
  frozen_outcome.json                  # verbatim copy of results/decision.json + full metrics.csv rows as parsed numbers + source SHA-256s
  runs/<policy>_seed1/
    run.json                           # metadata, file index (bytes, sha256, dtype, shape), summaries
    rack_tc.f32                        # float32 LE, shape [2160][257], modelled coolant °C at endpoint t_s
    rack_kw.f32                        # float32 LE, shape [2160][257], RAPS input rack kW held over (t_s-10, t_s]
    rack_free.u8                       # uint8, shape [2160][257], free nodes (RAPS input at t_s-10), 0..18
    tick.f64                           # float64 LE, shape [2160][8]: t_s, it_kw_total, n_running, n_queued,
                                       #   maxrack_c, minrack_c, argmax_rack (lower index on ties), pump_kw_sum
    events.json                        # columnar: kind[0=start,1=complete], raps_t_s[int], job_id[int],
                                       #   decision_index[int|-1], rack_offsets[int], racks[int] (node//18, unique, sorted)
    decisions.bin + decisions.json     # see "Decision context" below
```

**`catalog.json` (version `"thermorl.replay.v1"`):**
```json
{
  "schema": "thermorl.replay.v1",
  "experiment": "E12_g4_alibaba", "workload_label": "Alibaba-derived", "system": "summit",
  "fmu_sha256": "0a6ca377…9233", "scenario": "nominal (290 K)",
  "seeds_in_experiment": [1,2,3], "seed_exported": 1,
  "seed_note": "seed 1 of 3; E12 seeds 2/3 are correlated (seed 3 ≈ seed 2 shifted 33 s)",   // E11: "seed 1 of 3"
  "policies": ["packing","power_balance","thermal_predictive"],
  "comparisons": [{"id":"pb_vs_tp","left":"power_balance","right":"thermal_predictive","default":true},
                  {"id":"packing_vs_tp","left":"packing","right":"thermal_predictive"}],
  "grid": {"rows":13,"cols":20,"n_racks":257,"mapping":"row=r//20, col=r%20, origin lower","schematic_not_floor_plan":true},
  "time": {"tick_s":10,"n_ticks":2160,"first_t_s":10,"last_t_s":21600,
           "evaluation_window":{"start_exclusive_s":3600,"end_inclusive_s":21600},
           "interval_semantics":"kw/free/it_kw_total/n_running/n_queued are RAPS inputs at t_s-10 held over (t_s-10,t_s]; t_c/pump_kw are FMU endpoint outputs at t_s",
           "s2_statement":"<verbatim S2>"},
  "colour_scale_c": {"min": 38.70223, "max": 42.413286, "scope":"all five seed-1 policies of this experiment; E11 and E12 scales differ"},
  "launch_shas": ["18dfea1…","e0e1522…"], "export_source_sha": "<HEAD at export>",
  "frozen_outcome_ref": "frozen_outcome.json",
  "unavailable_fields": ["PUE","carbon","SLO","emergency","dual_prices","THI_counterfactual","regret","energy_savings"],
  "claims": {"headline":"no material value on the homogeneous twin","rule":"PB−TP ≥ 0.5 °C in every seed (time-mean max-rack, 3600<t_s≤21600)","descriptive_only":true}
}
```

**The colour scale** must equal the recorded demo scale. Recompute min/max over the five seed-1 `intervals.parquet` files and assert agreement with the inventory/C6 values to within 1e-6. On mismatch, STOP.

**`run.json`** must carry:
- `policy`, `seed`, `run_id` (`<EID>:<policy>_seed1`), `launch_sha` (`manifest.git.sha`), `selected_attempt` (E12, from `results/matrix_runtime.json`);
- `manifest_sha256`, and the source ledger SHAs (`decisions_sha256`, `intervals_sha256`, `job_events_sha256`), copied from the manifest **and re-hashed** to confirm;
- `n_decisions` (equal to `manifest.decision_rows`), `jobs_started`;
- `metrics` (that run's `metrics.csv` row, parsed);
- `files` (name → bytes, sha256, dtype, shape);
- `c_prime_status` (from `determinism_evidence.json`: `verified_E12` for E12 TP seed 1 only; otherwise `inherited_not_remeasured`).

**Decision context (bounded; no full 257-vectors):** for each decision, in `decision_index` order, `decisions.json` holds columnar arrays:
- `decision_index`, `raps_t_s`, `job_id`, `nodes_required`, `rule`, `job_kw`, `t_obs_s`;
- `chosen_rack_offsets`, `chosen_racks`;
- `n_ties_at_logged_best` (count of racks whose **logged** score equals the max logged score);
- `chosen_is_logged_best` (bool).

`decisions.bin` holds, per decision, the **top K = 8 racks by logged score** (descending; ties broken by lower rack index, matching the placement rule), plus any chosen rack not already among them, padded to 10 rows. Each row is `[rack:u16, score:f32, t_c:f32, committed_kw:f32, free:u8]`, with a fixed record size documented in `run.json`. Values are the **logged six-decimal values**, cast to f32 for display.

Include the precision note verbatim in `run.json`:
> "Logged six-decimal context. Live decisions used full precision; near-ties below logging precision are common for temperature-reading policies (E11 self-reproduction ≈ 95 % TP, ≈ 90 % coolest_rack). This view does not reconstruct or rescore decisions."

**Pulse/display rule (same as the existing GIFs):** frame endpoint T shows the starts with `T_prev < raps_t_s ≤ T`, where T_prev is the previously displayed tick. A placement's power first appears in the `kw` of the row labelled `10·ceil(raps_t_s/10)+10` (document this; do not change the data).

**Size budget:**
- every file under 25 MB;
- each `run.json` + arrays under about 12 MB;
- the whole `replay_v1` under 40 MB per experiment.

If the budget is exceeded, reduce K first. Do **not** downsample the time grid without an explicit Bipin decision. If still exceeded, STOP.

### A6. Exporter tests
- **Unit (fixtures; run in the default tier):** a tiny 3-rack × 4-tick synthetic run directory built in `tmp_path`. Check:
  - shapes, dtypes and byte lengths;
  - the t_s grid;
  - interval-semantics labels;
  - the top-K tie ordering;
  - `chosen_is_logged_best` and `n_ties`;
  - event rack mapping (node // 18);
  - the pulse-rule helper;
  - no overwrite;
  - sha256 entries match the file bytes;
  - `unavailable_fields` present;
  - no rescoring imports (static check that the module does not import `core.scorers`/`placement`).
- **Real-data checks** (`tests/integration/test_replay_export_real.py`, `skipif` raw ledgers are absent; record when skipped). For each exported run:
  - `mean(tick.maxrack_c over 3600 < t_s ≤ 21600) == metrics.csv maxrack_mean_c` within **1e-9** (float64 path);
  - `float32 rack_tc` vs the parquet maximum absolute error ≤ 5e-6 °C;
  - `it_kw_total` identical across the exported policies within 1e-6 kW;
  - decision count equals `manifest.decision_rows`;
  - event start count equals the decision count;
  - colour-scale agreement;
  - source ledger SHAs equal the manifest values.
- Run the default tier (all pass), and the real-data test on Arch.

### A7. Produce and commit exports (CK-B)
- **[default D-F]** Export E12 and E11, seed 1, policies `packing`, `power_balance`, `thermal_predictive`. That is 6 runs and 2 catalogs.
- **[default D-E: commit exports]** Commit them (`artifacts(replay): replay_v1 exports for E11/E12 seed 1`) after checking each file is under 25 MB. Never commit raw ledgers.
- Write `docs/results/replay_export_record.json`: command, HEAD, wall time, own peak RSS, file inventory, all A6 check results.
- Push. **STOP (CK-B)** with a short report. The contract can then be reviewed before frontend work.

---

# PART B — Frontend replay viewer (any machine; Node ≥ 20)

Work in `thermoRL/frontend/viz/`. Keep it a static Vite app with no server.

### B0. Data sync
- Add `scripts/sync-replay.mjs`. It copies `thermoRL/backend/experiments/summit/{E11_g4_synthetic,E12_g4_alibaba}/exports/replay_v1/**` into `viz/public/replay/<EID>/`, verifying each sha256 against `run.json`/`catalog.json`.
- Add `public/replay/` to `viz/.gitignore`.
- Set `publicDir: "public"` (create the directory with a `.gitkeep`). Keep `emptyOutDir` limited to `dist/` (already ignored).
- `npm run dev` and `npm run build` run the sync first.

### B1. Replace the data model
- **Delete** the legacy types and fields from the viewer path. These are zones, THI, PUE, carbon, SLO, emergency, λ/dual prices, regime, `round_robin`/`thi_lookahead`, `frames_rr`/`frames_thermorl`, the `bundle-data.js` script tag and the `ledger_thermorl` loader.
- Do **not** delete `thermoRL/frontend/thermorl/**` or `artifacts/bundles/demo_ramp/**`. **[default D-G]** Add `thermoRL/frontend/LEGACY.md` (force-add, since `*.md` is ignored): "legacy three-zone simulator and constructed fixture; not FMU evidence; not used by the viewer".
- New `src/schema/replay.ts` mirrors `thermorl.replay.v1` exactly. Any field listed in `unavailable_fields` must **not** have a UI element at all. Never render placeholder zeros.
- New `src/data/loader.ts`:
  - fetch `catalog.json`, `frozen_outcome.json` and the two runs' `run.json`;
  - fetch the binaries as `ArrayBuffer`, **verify sha256 with `crypto.subtle.digest`** and byte length;
  - build typed-array views.

  Loading states: per-file progress; an error state naming the file (missing, size or hash mismatch, schema version mismatch); no partial rendering after an integrity failure.

### B2. Scene: 257-rack schematic
- Rewrite `src/scene/racks.ts` as a parameterised grid from `catalog.grid` (13 × 20, origin lower; 3 empty cells drawn as outlines). This **fixes the old `rowZ` duplication** by construction.
- Use an `InstancedMesh` of 257 low boxes (or flat tiles) with an orthographic camera, fitted to the viewport.
- **Colour:** modelled coolant °C mapped through a fixed **inferno-like** ramp (same family as the figures) using `catalog.colour_scale_c`. Show a numeric legend with min/max and the label "Modelled coolant °C; scale fixed per experiment".
- **Optional overlay toggle:** rack kW or occupancy (18 − free). Label it "RAPS input over the interval ending at t".
- **Placement pulses:** a ring or outline on racks with starts satisfying the pulse rule. Caption: "recent placements (not a cooling effect)".
- **Hover tooltip:** rack id, `t_c` (2 d.p. displayed), kW (1 d.p.), free nodes, the interval-semantics note.
- **Click:** pin the rack and show a small sparkline of its `t_c` and kW across the episode, both runs overlaid, with the evaluation window shaded.
- Two synchronised panels (left and right policy), same scale, same tick index. Assert that the two runs' t_s grids are identical, or show an error. Never clamp silently.

### B3. Player, timeline and panels
- **Player:** an index over 2160 ticks; speeds 1/2/5/10/30 ticks per second; play, pause, step ±1 tick, ±1 min, ±10 min; scrubber with the **1 h evaluation-window boundary marked**; keyboard (space, arrows, Shift+arrows); a clock showing `t = hh:mm:ss (tick k/2160)` and "before evaluation window" / "evaluation window".
- **Timeline strip** (canvas or SVG): per-tick `maxrack_c` and spread (max − min) for both runs, with the evaluation window shaded and a cursor. This is the *recorded* time series, not a metric.
- **Header identity:**
  - experiment and workload label;
  - "Summit POWER9 FMU (modelled), nominal";
  - `seed_note`;
  - left and right policy IDs exactly as written (`power_balance`, `thermal_predictive`, …);
  - E12 "C′ verified (6 h repeat)" badge **only on TP seed 1**, with a tooltip giving the exact scope. Other runs read "not directly repeated".
- **Frozen outcome card** (from `frozen_outcome.json`, verbatim numbers, full precision available on hover):
  - the decision text;
  - the rule;
  - per-seed PB−TP and packing−TP for **all three seeds**;
  - the five-policy `maxrack_mean_c` table for all seeds;
  - E11 shows "packing ≈ TP on the primary metric (E11 only)"; E12 shows the exact descriptive-ordering sentence;
  - footer: "The preregistered rule decides; this viewer is descriptive."
  - **No** derived "winner", delta badge or percentage.
- **"Why this rack?" drawer:**
  - lists the decisions in the current frame's pulse interval for the selected side;
  - shows job id, nodes, rule, chosen racks;
  - shows the top-K logged candidates table (rack, logged score, `t_c`, committed kW, free), with chosen rows highlighted;
  - shows "ties at logged precision: n" and whether the chosen rack is the logged best;
  - always shows the precision note verbatim;
  - links "Show all decisions in this interval".
- **"About this data" panel:**
  - S2 verbatim;
  - interval semantics;
  - capped, unsettled warm-up; G1 is a heuristic;
  - modelled, not hardware;
  - the reproducibility scope sentence;
  - the forbidden-claims reminder;
  - links to the results note and `DEMO.md`.
- **Comparison selector:** only pairs within one experiment, from `catalog.comparisons`. Default: E12 `pb_vs_tp`. An experiment switch reloads everything, including the scale. Never mix E11 and E12 scales in one view.
- **Fallback:** if WebGL is unavailable, show a message and links to the labelled GIFs/PNGs.

### B4. Frontend tests and checks
- Add `vitest` (dev dependency). Unit tests for:
  - loader integrity (bad sha or size → error);
  - schema-version mismatch;
  - pulse-rule mapping;
  - colour-scale mapping at the endpoints and clamping display (out-of-range values flagged, not hidden);
  - comparison pairing constraint;
  - absence of any UI binding for `unavailable_fields`.
- **Playwright** smoke (Chromium, headless; dev dependency) against `vite preview`:
  - the page loads the default comparison;
  - step to t = 3610 s, then the window label changes;
  - open the Why drawer at a tick with placements and see rows;
  - switch to E11 and see the legend range change;
  - capture screenshots to `viz/test-artifacts/` (ignored).
- `npm run build` must pass `tsc --noEmit` with no type errors.
- **Record:** bundle sizes, initial load time on the presenting Mac (Chrome), steady frame rate during playback (target ≥ 50 fps at 5 ticks/s), and JS heap after load (target under 400 MB).

### B5. Packaging and walkthrough (CK-C, final STOP)
- `thermoRL/frontend/viz/README_DEMO.md` (force-add): how to run (`npm ci && npm run dev`, or `npm run build && npm run preview`), the data provenance chain, the scripted 5-minute walkthrough below, and the GIF fallback.
- Update `thermoRL/backend/experiments/DEMO.md` with a "Replay viewer" row: the asset, what it shows, the allowed claim, "must not be used for", and source.
- Write `docs/results/demo_replay_check.json`: commands, versions, test counts, sizes, performance numbers, screenshots list.
- Push. **STOP for Bipin and Opus review.**

**Walkthrough** (the viewer must support each step):
1. Open E12, `pb_vs_tp`. Read the header and the frozen outcome card.
2. Play the burst at about 2–3 h. Pause and open the Why drawer: actual placements, logged context and precision note.
3. Scrub the window boundary at 1 h. Show the timeline and evaluation shading.
4. Switch to `packing_vs_tp`: spatial concentration under packing at identical IT power.
5. Switch to E11: a different regime and scale; packing ≈ TP on the primary metric.
6. "About this data": limits and reproducibility scope.

---

## Commits (scoped; never mix backend and frontend in one commit)
1. `fix(backend): relocation-safe workload and source paths` (A1)
2. `chore(repo): re-track files dropped by directory rename` (A2; exactly 81 paths)
3. `docs(repo): post-rename path mapping and living-doc links` (A3)
4. `docs(results): post-rename acceptance` (A4) → **CK-A STOP**
5. `feat(backend): read-only replay_v1 exporter with tests` (A5–A6)
6. `artifacts(replay): replay_v1 exports for E11/E12 seed 1` (A7) → **CK-B STOP**
7. `feat(frontend): replay_v1 loader and 257-rack schematic` (B0–B2)
8. `feat(frontend): timeline, frozen-outcome card, why drawer, about panel` (B3)
9. `test(frontend): vitest and playwright smoke` (B4)
10. `docs(demo): replay walkthrough and asset map` (B5) → **CK-C STOP**

Each commit message states "no new simulation; no change to accepted science".

## Acceptance criteria (all required)
- **Backend:**
  - non-FMU tier fully green in the working repo **and** in a fresh on-disk clone;
  - no `thermorl-v2` literal in executable paths;
  - source collectors return the package files;
  - exactly 81 files re-tracked, SHA-identical;
  - no E11/E12 raw `runs/` file tracked;
  - frozen README sections verified;
  - no experiment artifact modified (`git diff --stat` between `beafb51` and the final HEAD shows only the allowed paths).
- **Exporter:**
  - every A6 check passes on real data, including **maxrack mean agreement with `metrics.csv` within 1e-9** and colour-scale agreement;
  - file hashes recorded;
  - size budget met;
  - no rescoring.
- **Viewer:**
  - loads only verified `replay_v1` data;
  - shows experiment, workload, seed and policy identity, the 257-rack schematic, modelled °C with a fixed legend, the strict window, real placement events and the frozen outcome with all three seeds' gaps;
  - logged decision details carry the precision caveat;
  - no PUE/carbon/SLO/emergency/λ/THI/zone UI;
  - no computed winners or savings;
  - fallback to the GIFs;
  - tests pass; build passes; the walkthrough is reproducible.
- **Wording:** every visible string complies with the frozen claims and forbidden list in §0.
