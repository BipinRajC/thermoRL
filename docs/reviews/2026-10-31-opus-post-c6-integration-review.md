# Opus Post-C6 Integration Review — Backend, Experiments, Packaging, Assets, Frontend Readiness

**Reviewer:** Claude (Opus), the independent reviewer and integration architect. **Date:** 2026-10-31.

**Reviewed:**
- `origin/feat/parasparam-demo` at **`beafb51`**.
- `e808275` (handoff docs plus the backup-waiver addendum).
- `c09f735` (the audited rename snapshot).
- `beafb51` itself: Bipin's "chore: minor cleanup", which deletes the root `CLAUDE.md`, `HANDOFF.md`, `docs/prompt.md` and `docs/repository-notes.md`. It touches no backend, frontend or experiment file. These were user-owned deletions, and I treat them as intentional.

**Environment:** the Mac, macOS arm64. The working tree is clean apart from ignored files.

**Commands run:**
- `git` log, diff, `ls-files`, `check-ignore` and `show`.
- A Python read-only audit of the evidence JSON, asset inventories and hashes.
- A scratch venv: `UV_PROJECT_ENVIRONMENT=<scratch> uv sync --frozen` from `thermoRL/backend`, followed by `uv run pytest tests/unit tests/integration -q`.
- A scratch copy of `thermoRL/frontend/viz`: `npm ci && npm run build`. The output stayed in scratch; the original `viz/` and legacy bundle were untouched.
- Extraction of GIF frames into scratch.

**Not run:** any FMU, smoke test, `run.py`, `run_matrix`, report CLI, legacy simulator, `make_demo_bundle.py`, browser session or WebGL check.

**Evidence limits:**
- The raw ignored E11/E12 ledgers are only on Arch. The 81 de-tracked files are **absent on the Mac at both their old and new paths**: git removed the old paths, and the new paths were never committed.
- The 230-entry raw re-verification and the 12 frozen-section checks on Arch are **SOL-REPORTED**. I verified frozen-section integrity from git history (`b3bd5ac`) and in my earlier C4 review.

**Labels:** FACT, DERIVED, INFERENCE, HYPOTHESIS, UNRESOLVED, SOL-REPORTED.

---

## 0. Verdict

| Dimension | Verdict | Basis |
|---|---|---|
| **Scientific completion** | **COMPLETE within the approved scope.** No further simulation is required. | Both G4 outcomes are frozen and unchanged (`decision.json`: `value_beyond_power=false` for E11 and E12). All 596 moves are `R100` (byte-identical renames). The demo-asset hashes match their inventories. Results-note numbers trace to committed artifacts. |
| **Backend operability at current HEAD** | **NOT READY (blocked).** | B1: stale workload root, which fails the runner wiring path. B3: empty application source map for future runs. B4: stale editable environment. |
| **Portability and auditability at current HEAD** | **NOT READY (blocked).** | B2: 81 tracked files dropped. They include both **preregistered experiment READMEs**, `INDEX.md`, `DEMO.md`, the backend README and the **E10 inherited-evidence ledgers**. A clean checkout fails **4 additional tests** (DERIVED on the Mac). |
| **Demo readiness — fallback assets** | **READY with one gap.** The eight labelled PNG/GIF assets are correct and hash-verified. | `DEMO.md`, the asset→claim map, is not in the git tree (B2). |
| **Demo readiness — interactive replay** | **NOT STARTED.** A clear and feasible path exists (replay-first). | No exporter or data contract exists. The frontend shell builds, but its domain model is incompatible. |

**Readiness in one sentence:** the science is done and the static demo assets are good. Before anything else, the repository needs a ~half-day relocation and tracking repair. An interactive FMU-replay demo is then roughly 4–5 focused days of bounded engineering, with **no new simulation**.

---

## 1. Historical validation vs current readiness (kept distinct)

| Claim | Status |
|---|---|
| D7 at code candidate `06032b4`: 196 non-FMU tests, 22 pinned hashes, 1 finite Summit smoke | **Historical, valid at that SHA** (C6, `d7_fresh_clone_check.json`). It says nothing about current HEAD. |
| Post-rename on Arch: **195 passed, 1 failed** (`test_runner_contract.py::test_runner_wiring_counts_steps_and_records_completion_reuse`) | SOL-REPORTED. The cause matches the source I inspected (`runner.py:54`). |
| **Post-rename clean checkout (Mac, `beafb51`): 192 passed, 4 failed** (54.36 s) | **DERIVED here.** Failures: `test_e11_review_fixes::test_g4_requires_job_event_file`, `test_metrics::test_e10_ledgers_reproduce_reviewed_metrics_and_rounding_diagnostic`, `test_plots_smoke::test_e10_reporting_uses_ledgers_without_overwriting_e10`, `test_plots_smoke::test_expected_preregistration_rejects_self_consistent_wrong_config`. All four fail with `FileNotFoundError` on the **untracked E10 run ledgers**. |
| The runner-contract test **passed** on the Mac | **An artefact, not health.** The relative path is resolved through `repo_root()/'thermoRL/thermorl-v2'/<../../…>`. On my Mac a leftover ignored `thermoRL/thermorl-v2/` directory (only `__pycache__`) exists, so the `..` traversal succeeds. On Arch the directory is gone and it fails. **A true fresh clone is expected to show ≈ 191 passed, 5 failed** (INFERENCE: B1 + B2 combined). |

So **"195/1" understates the defect.** Arch still holds the untracked copies locally, which masks the B2 test failures.

---

## 2. Findings, by severity

### High — blocks a clean, portable, operable HEAD

| ID | Finding | Evidence | Consequence | Smallest correction |
|---|---|---|---|---|
| **B1** | Stale workload root | `thermoRL/backend/thermorl2/raps_adapter/runner.py:54`: `if not path.is_absolute(): path=repo_root()/'thermoRL/thermorl-v2'/path`. `core/metrics.py:22` and `experiments/run.py:20` already use a relocation-safe `PROJECT = Path(__file__).resolve().parents[2]`. | Any new run, the runner wiring test, and any workload load through the runner all fail. Behaviour depends on whether the old directory exists (B1 is masked on the Mac). | Replace it with `PROJECT/path`, where `PROJECT` is the package root (same definition as `core.metrics`). Keep `manifest['workload_path']` relative and unchanged. Add a test that **creates no old directory** and asserts resolution under `thermoRL/backend`. |
| **B2** | 81 tracked files dropped by `c09f735`. Byte-identical copies exist only locally on Arch. | FACT: `git diff -M --name-status b3bd5ac c09f735` gives **596 R100 + 81 D**. Causes: `thermoRL/.gitignore:2-3` (`*.md`, `docs/*`), root `.gitignore:33` (`*.log`) and `:41` (`runs/`). Moving a tracked file is an *add* at the new path, so the ignore rules apply to it. Dropped: 29 `.md` (**E11/E12 READMEs containing the hashed preregistration sections**, `INDEX.md`, `DEMO.md`, the backend README, X01/E00/E01/E02/E03/E10 READMEs, SYSTEM files, templates, Task 1.5 diagnostic READMEs); 39 logs; the E10 run ledgers (2 parquet, 8 jsonl, 2 json, `.gitkeep`); 2 `metrics.md`. | The preregistration record, the asset→claim map and the experiment index are **absent from the current tree**. E10 inherited-determinism evidence, referenced by E11/E12 `determinism_evidence.json` and by tests, is absent. A clean clone fails 4 tests. Links from C6, the results note and the runbook break. | **Retain all 81** (recommended; no evidence of intent to retire any). Re-add **exactly** the mapped list from `post-c6-review-evidence.json` with `git add -f -- <path…>`, after re-verifying each file's SHA-256 against `historical_sha256`. Never `git add -A`, and never force-add a directory. Separately, decide whether to narrow `thermoRL/.gitignore` (D-B). |
| **B3** | Empty application source map for future runs | `runner.py:128-129`, `experiments/bench.py:46-47` and `experiments/probes.py:196-197` walk `repo_root()/"thermoRL/thermorl-v2/thermorl2"`, which yields 0 files. | Future manifests would silently omit application provenance. The C′ comparator's equality of `source_sha256` could then pass vacuously on the application part. | Use `PROJECT/'thermorl2'` with keys relative to `repo_root()`, so keys become `thermoRL/backend/thermorl2/...`. Add a test asserting ≥ 39 entries and that the key set equals the actual package files. Historical manifests keep their old keys; document the mapping and never rewrite them. |

### Medium

| ID | Finding | Evidence | Correction |
|---|---|---|---|
| B4 | The moved Arch `.venv` still has an editable `.pth` pointing to the old root. Imports from the backend directory work only because of the cwd. | SOL-REPORTED; consistent with the move. | `uv sync --frozen` from `thermoRL/backend` (no lock change), then `python -c "import thermorl2, raps; print(thermorl2.__file__)"` from **outside** the backend directory. |
| D1 | The navigation documents point to old paths: results note (2 links), runbook (13), C6 (4), C5 (1). The results note and `DEMO.md` still say the backup is "pending". | FACT, by grep. The backup waiver is in the plan addendum (`e808275`). | Add a dated **path-mapping note** (`thermorl-v2 → backend`, `thermoRL-new → frontend`). Update **only living navigation documents** (results note, runbook, `DEMO.md`, backend README, `INDEX.md`): new links plus a "backup waived (2026-10-31)" line. Leave checkpoints and experiment records historical. |
| D2 | `tests/unit/test_e11_review_fixes.py:107` checks the ignore rule on an old `thermorl-v2` path. It passes only because `**/provenance/failed_*/` is location-independent. | FACT | Point it at the new path. |
| D3 | Frontend documentation (`DEMO_AND_TEST.md`, referenced by the handoff) is also untracked (`*.md` rule). | `git ls-files thermoRL/frontend` contains no `.md` | Same handling as B2 if it is to be kept. |

### Low and cosmetic (assets)

| ID | Finding | Correction |
|---|---|---|
| A1 | The E11 early-frame caption "logged initial rack temperatures differ" is imprecise. The first logged TP decision had **one** distinct six-decimal value (`[1,3,3]`), i.e. identical for decision 0, differing from decision 1 onward. | Optional caption tweak in a later re-render: "decision 0: identical at logged precision; decisions 1–2 differ". Never overwrite; any new copy gets a new name. |
| A2 | The "Early-frame TP scatter" caption also appears on static heatmaps and time series, where there is no scatter. Large blank areas in the GIF layout. GIF sizes are 17–21 MB. | Cosmetic. They are superseded by the replay viewer if built. |

### Frontend (source audit plus a scratch build)

| ID | Finding | Evidence |
|---|---|---|
| F1 | **Geometry defect confirmed in source.** `scene/racks.ts:6-7,274,282,317`: `COLS=4, ROWS=4` but `rowZ=[+0.725,−0.725]`, so rows 2 and 3 resolve to `z=0` and overlap exactly. That gives 12 unique (x,z) positions for 16 racks per zone. | FACT (source). Browser rendering not checked. |
| F2 | The domain model is incompatible: 3 zones × 16 racks, THI colours, `round_robin` vs `thi_lookahead`, PUE/carbon/SLO/emergency/λ fields (`schema/vizevent.ts:1-51`; `main.ts:71-155`; `index.html:6-59`). | FACT |
| F3 | The build works. In scratch, `npm ci && npm run build` succeeded (Vite 6.4.3, `tsc` clean) and reproduced the legacy asset hashes (`index-B-gtpkTt.js`, `index-BxkZm3H2.css`). Warnings: the `<script src="./bundle-data.js">` tag is not a module. `vite.config.ts` has `emptyOutDir: true` and a non-existent `publicDir: "public"`. | DERIVED |
| F4 | The legacy Python simulator, stages and policies live in `thermoRL/frontend/thermorl/`. The legacy bundle is `thermoRL/frontend/artifacts/bundles/demo_ramp/` (24 frames, 0–460 s, a constructed fixture). | FACT. These must not be reconnected or run. |

---

## 3. Science and results: re-verified (unchanged)

- **Frozen outcomes:** both `decision.json` files have `value_beyond_power=false` and "no material value on the homogeneous twin".
  - E11 PB−TP: +0.342, −0.147, −0.071 °C.
  - E12 PB−TP: +0.178, +0.077, +0.109 °C.

  I recomputed these from the per-tick series in my C4 review. The files are R100-identical since then.
- **The results note** (`docs/results/2026-11-parasparam-demo-results.md`) is accurate:
  - the E11 table and "packing ≈ TP" are scoped to E11;
  - the E12 descriptive-ordering sentence is exact, with the "about two conditions" caveat;
  - the S1 statements are metric-specific and match `metrics.csv`;
  - the three utilisation quantities are kept distinct;
  - reproducibility is scoped exactly (E10 packing 2 h; E11 seed-1 packing/PB 2 h prefixes; E12 TP seed 1 6 h; D7 same-machine);
  - spec §8 is quoted verbatim, followed by the D8 correction; S2 is verbatim;
  - M2 is E11-only and M3 is unresolved; the strict XFAIL is stated;
  - the forbidden claims are absent.

  **Only staleness:** old links and "backup pending" (D1).
- **Assets, checked by opening them:**
  - The labelled E11/E12 heatmaps and time series carry the experiment, workload, system, seed, E12's correlation caveat, the colour range with the "scales differ" note, a dashed **1 h "evaluation window starts" marker**, and the negative-G4 caption.
  - GIF frames 0, 100, 121, 360 and 719 show "before evaluation window (t ≤ 1 h)" / "evaluation window (1 h < t ≤ 6 h)" states, the shared within-experiment scale, cyan recent-placement rings and the early-frame caption (the E12 tie-breaking caption is consistent with the `[1,1,1]` check).
  - All 8 SHA-256 hashes match `provenance/demo_asset_inventory.json` (DERIVED).
  - The visuals agree with the numbers. None suggests a positive G4 headline. C4 conditions C1–C3 are satisfied.
- **Recovery, C′ and resource scopes:** unchanged since my C4 review (accepted). The backup is **waived**, not completed (plan addendum `e808275`; `raw_backup_record.json` `status: skipped_by_user`). It is not a blocker.

**Allowed and forbidden claims:** unchanged, as in the results note's Appendix C (my C4 §9).
- **Allowed:** an FMU-backed closed loop with six invariants; two negative G4 results (largest PB−TP 0.34 / 0.18 °C, against 0.5); E12's descriptive ordering with its caveats; metric-specific redistribution at identical power; G3 NOT_USABLE; exactly scoped reproducibility.
- **Forbidden:** "thermal-aware placement works/removes hotspots"; significance; generalising across regimes; whole-matrix or cross-machine reproducibility; hardware, safety, PUE, energy savings, carbon, lifetime, RL, surrogate, heterogeneous-zone or mechanism claims; "weak rack-to-rack coupling" without D8.

**New for the interactive demo:**
- Every interactive view must show the frozen outcome and the materiality rule.
- It must never compute or display a "winner" or a savings number.
- It must label temperatures "modelled coolant °C".
- It must never use the legacy THI, PUE or λ visuals.

---

## 4. Integration architecture decision

**Replay-first.** I found no concrete need for browser-controlled live runs:
- runs take about 20–28 min per 6 h configuration;
- the FMUs are Linux-only, while the demo laptop is a Mac;
- one FMU per process plus memory constraints apply;
- any new run would be a *new* execution needing scientific authorisation.

A live job API (submission, status, lifecycle, one-FMU-per-process supervision) is a separate product layer. **Not recommended for this demo.**

```text
immutable FMU ledgers (Arch, ignored)          committed, small, hashed
runs/<policy>_seed1/{intervals.parquet,   →   exporter (backend, read-only)   →   exports/replay_v1/ (≈ 6 × ~7 MB)
 decisions.jsonl, job_events.jsonl,                                                │ sync (sha-checked copy)
 manifest.json} + results/*.json/csv                                               ▼
                                                                         frontend/viz/public/replay/ (ignored)
                                                                                   ▼
                                                                Three.js 257-rack schematic replay (Mac or any browser)
```

- The exporter runs **once on Arch**, where the raw ledgers live. Its outputs are committed (each file under 25 MB), so the Mac can present without the raw data.
- The browser renders recorded values only. There is **no physics in JavaScript**, and headline metrics are **never** recomputed client-side; they come verbatim from the frozen `metrics.csv` and `decision.json`.

**Payload (DERIVED estimate):** per run, 2160 ticks × 257 racks:
- `t_c` float32 ≈ 2.2 MB;
- `kw` float32 ≈ 2.2 MB;
- free nodes uint8 ≈ 0.56 MB;
- per-tick scalars ≈ 0.1 MB;
- events ≈ 0.3–0.8 MB;
- top-8 decision context ≈ 2–3 MB.

That is **≈ 7–9 MB per run**, and about 50 MB for six seed-1 runs (E11 and E12 × packing, PB, TP). Full decision contexts (≈ 200 MB per E12 run) are **never** shipped.

---

## 5. Complete, blocked, optional; remaining-work estimate

| Item | Status |
|---|---|
| Science (C1–C5, E10–E12, results note, labelled assets, D7 historical) | **Complete** |
| Relocation and tracking repair (B1–B4, D1–D3) | **Blocked → required, ~0.5 day** |
| Post-repair acceptance: non-FMU tier in a clean clone on Arch, expecting all pass | **Required, ~0.25 day** |
| Optional single Summit FMU smoke after the repair (backend "operable for future runs") | Optional; needs a Bipin decision (D-C). Not needed for replay. |
| Replay exporter, v1 contract and tests (Arch) | Required for an interactive demo, **~1–1.5 days** |
| Frontend adaptation (schema, 257-rack schematic, panels, timeline, Why drawer, summary) | Required for an interactive demo, **~2–2.5 days** |
| Build, browser, interaction and payload checks; packaging; rehearsal | **~0.5–1 day** |
| Live simulation API | Not recommended; out of scope |
| Backup | **Waived** (not a gate) |

**Grounded total:** about **4.5–5.5 focused days** to an interactive, truthful replay demo. About 0.75 day is enough for a repaired repository presenting the existing labelled assets.

---

## 6. Decisions for Bipin

- **D-A (recommended: retain all 81).** Re-track all 81 dropped files, or name any to retire explicitly. The Task 1.5 diagnostic READMEs and templates are historical, but cheap and referenced.
- **D-B.** How to stop recurrence. Options:
  - **(i)** force-add the verified explicit list only, leaving the ignore rules as they are (recommended now);
  - **(ii)** also narrow `thermoRL/.gitignore` (`*.md`, `docs/*`). That rule likely exists for local context files; only you know its intent.
- **D-C.** After the repair, run one Summit FMU smoke from a clean clone (same as D7), or accept non-FMU acceptance only. **Recommendation:** non-FMU only for the replay demo; smoke only if you want "backend operable for new runs" claimed.
- **D-D.** Approve the **replay-first** architecture and reject a live API for this demo (recommended).
- **D-E.** Commit the replay exports (≈ 50 MB total, every file under 25 MB) so the Mac can present. **Recommended.** The alternative keeps them on Arch only.
- **D-F.** Initial comparisons, all seed 1:
  1. E12 PB vs TP (headline);
  2. E12 packing vs TP;
  3. E11 PB vs TP;
  4. E11 packing vs TP.
- **D-G.** Legacy frontend simulator and the `demo_ramp` bundle: keep them untouched and label them legacy (recommended), or remove them in a separate, explicit commit.
- **D-H.** Execution split. Part A (repair plus exporter) must run on **Arch**, where the raw ledgers live. Part B (frontend) can run anywhere once the exports are committed.

---

## 7. Recommendation to Bipin

1. Approve **D-A, D-B(i), D-D, D-E, D-F, D-G (keep, label legacy) and D-H**. Choose D-C (I recommend non-FMU only).
2. Have Sonnet execute **Part A** of the brief first: repair, re-track, and run the clean-clone acceptance. Stop for a short check of the green test tier.
3. Then the exporter, then the frontend.
4. Keep the labelled GIFs and figures as the fallback throughout.

**No new simulation, policy, metric, threshold or science change is needed or authorised.**
