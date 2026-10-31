# ThermoRL post-C6 handoff: backend completion, rename regressions and frontend integration

**Prepared:** 2026-10-31T13:40:21.263999+00:00. **For:** Opus 5.5 independent review, then a Bipin-approved Sonnet 5.5 implementation handoff. **Repository:** `/home/bipin/thermoRL`. **Branch:** `feat/parasparam-demo`. **Audited HEAD:** `c09f735ddde82d0acaf54f2f0900a2563c3915ee` (`c09f735`). This document’s own commit adds reporting/waiver bookkeeping, not an implementation fix.

## 1. Read this first

The scientific backend is complete for the agreed experiment/demo scope. The RAPS→Summit FMU feedback loop, five policies, frozen workloads, both G4 matrices, metrics, provenance and scoped repeat evidence exist. No major physics/scheduling research component is missing for a replay demo.

**The current renamed checkout is not yet integration-ready.** A post-rename bounded test run returned **195 passed, 1 failed in 35.43 s**. A direct read-only workload-loader check also failed on the removed `thermorl-v2` path, before FMU initialization. Source hashing still searches the removed directory and finds zero application modules. These are concrete path/layout regressions, not new scientific outcomes.

The cleanup dropped **81 previously tracked files** from the current Git tree. Every one still exists locally under the mapped new path with identical bytes. This is a version-control portability issue, not evidence that the local raw data was lost. Author intent for each deletion should be confirmed; broad `*.md`, `*.log` and `runs/` ignore rules explain why moved evidence/docs did not automatically get re-added.

The existing Three.js frontend is a useful reusable replay shell, but its legacy data model is incompatible with the validated backend. The main missing backend integration feature is a **read-only export adapter**. A live simulation-control API is absent and is a separate, larger choice; it is not necessary for an interactive replay of existing FMU results.

**Latest user decisions:** backup is explicitly skipped; frontend changes may be substantial if needed for a good demo; first perform an Opus review, then scope Sonnet frontend work. This pass does not repair source code, re-run physics, implement a viewer or authorize new experiments.

## 2. Canonical paths and history

| Before cleanup | Current local path |
|---|---|
| `thermoRL/thermorl-v2/` | `thermoRL/backend/` |
| `thermoRL/thermoRL-new/` | `thermoRL/frontend/` |
| old Three.js source | `thermoRL/frontend/viz/` |
| experiment artifacts | `thermoRL/backend/experiments/` |

Many historical documents, manifests, inventories and source-SHA maps intentionally record the old paths. Historical source identities can still be read with `git show <recorded-SHA>:<old-path>`. Do not rewrite immutable experiment records to pretend they ran under the new folder names. Current runtime path resolution, documentation navigation and new integration exports need an explicit, documented mapping.

The frontend directory also contains the **old Python simulator/policies/stages**, not only browser code. The accepted FMU backend is `thermoRL/backend/thermorl2`. Do not silently reconnect the viewer to the legacy RC/THI simulation or run its bundle generator as a substitute for exporting FMU evidence.

## 3. Recent commit trail

| Commit | What it delivered |
|---|---|
| `18dfea1` | Original E12 launch engineering: bounded seed checks, queueing coverage, C′ adapter and provenance. |
| `f7cde7b` | Recorded the bounded interpretation of the user’s operational resume instruction. |
| `e0e1522` | Recovery-only orchestration/accounting; preserved interrupted attempts and froze recovery source. |
| `b96a43b` | Completed E12: 15 selected primary results, preserved interruptions, exact TP seed 1 C′, metrics, figures, inventories and C4. |
| `bd5dedc` | Opus independent C4 review: accept with conditions C1–C3. |
| `ce9d912` | Verbatim approved post-C4 decisions; recovery ratification, D7(b), deferred replay and frozen science. |
| `202b9ec` | C5 note: G3 weak lever; G5/E13 not run; no alternative lever. |
| `1678d0a` | Non-frozen E12 current-status pointer, INDEX and frozen-section check. |
| `06032b4` | Presentation-only renderer and seven fixture test cases; final code candidate used by D7. |
| `35916c5` | Eight labelled E11/E12 assets plus pre-render TP checks, inventories and render records. |
| `878cca0` | Results note, runbook, asset→claim map and raw-preservation verification; backup still pending at that time. |
| `9abeb11` | Successful same-Arch D7 clone, 196 tests, 22 hashes, one Summit smoke; preserved setup failures. |
| `b3bd5ac` | C6 packaging checkpoint and final scope/content checks; backup pending at that historical checkpoint. |
| `c09f735` | Bipin’s backend/frontend directory rename and cleanup. Package bytes retained, but path and tracking issues identified in this report. |

Earlier context: C1 selected Summit by a three-FMU gate and froze G1; C2/E10 validated the loop; C3/E11 completed the synthetic matrix and its independent review; Task 13 prepared the default-only Alibaba mapping and three immutable workloads. The detailed source of truth remains the dated plan addenda, checkpoint reviews and experiment records.

## 4. What is complete on the backend

| Capability | Evidence/status |
|---|---|
| System selection | X01: Summit selected mechanically, no winner-changing tie-break; Lassen runner-up. G2 packed−spread Δ: Lassen 2.036320 °C, Summit 6.234889 °C, Marconi100 0.054797 °C. |
| Frozen predictor | G1: a=27.9753857271229 °C; b=0.8052450824355937 °C/kW; tau=4050 s; H=600 s; t_hot=63.30492211035258 °C. A finite-horizon heuristic, not a validated predictor. |
| Room-air lever disposition | G3 NOT_USABLE: affected 0.538986 °C<1 °C, unaffected 0.101837 °C; 62 candidates listed, none applied; no G5/E13 or alternative lever. |
| Closed loop | Actual RAPS jobs on exact nodes → loss-inclusive rack power → Summit FMU → thermal publications for subsequent placement decisions. |
| Policies | packing, node_balance, power_balance, coolest_rack, thermal_predictive; frozen definitions and spanning/queueing rules. |
| Experiments | E10 mechanics; E11 synthetic 5×3; E12 Alibaba-derived 5×3 plus the one planned repeat and preserved interruptions. |
| Safety of interpretation | Six acceptance gates, full provenance, immutable workloads/configs, separate timing ledger, strict window and frozen outcome rules. No hardware/safety assurance implied. |
| Offline outputs | Parquet interval trajectories, canonical decisions, job events, thermal publications, metrics CSV/JSON, attribution, timing/provenance, labelled PNG/GIF assets. |
| Historical acceptance | D7 candidate 06032b4:196 non-FMU tests, 22 pinned hashes, one finite Summit smoke. This precedes the cleanup and is not current-HEAD acceptance. |
| Current local data |15 completed primary manifests per E11/E12;4 demo assets per experiment. This pass verified 230 raw inventory entries and 12 frozen README sections at the new local paths. |

The module/config comparison checked all **43 tracked files under the backend package at b3bd5ac**, mapped to their new paths. **All 43 are byte-identical.** The move preserved implementation bytes, including stale hardcoded path literals; unchanged code therefore does not imply unchanged behavior after relocation.

## 5. Scientific outcomes that must remain unchanged

Primary metric: time-mean maximum rack coolant over **3600<t_s≤21600**, 1800 endpoints. PB−TP must be ≥0.5 °C in **every** seed at full precision. Both experiments concluded **“no material value on the homogeneous twin”; value_beyond_power=false**.

| Experiment | Seed | Packing °C | Node balance °C | Power balance °C | Coolest rack °C | TP °C | PB−TP °C (full precision) | Packing−TP °C (full precision) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E11 | 1 | 54.070216 | 53.883515 | 54.330429 | 53.534760 | 53.987934 | 0.3424946761284602 | 0.08228175899471069 |
| E11 | 2 | 54.177058 | 54.094552 | 54.137678 | 54.123498 | 54.284869 | -0.14719002809689385 | -0.10781088891907586 |
| E11 | 3 | 54.122798 | 53.559813 | 53.775784 | 53.780430 | 53.846649 | -0.07086450347454587 | 0.27614954556487703 |
| E12 | 1 | 41.410869 | 41.256919 | 41.235138 | 41.164820 | 41.057548 | 0.17758993078025043 | 0.35332112789507875 |
| E12 | 2 | 41.345775 | 40.969726 | 40.981985 | 41.239750 | 40.904721 | 0.07726484193952388 | 0.441054417333838 |
| E12 | 3 | 41.308922 | 41.128894 | 40.994658 | 41.095216 | 40.885867 | 0.10879156917675914 | 0.42305513292543395 |

E11: **packing ≈ TP on the primary metric**; no consistent primary ordering. TP had lower temperature std and hottest 26 mean than PB, while coolest_rack was lowest on those S1 metrics. PB had the lowest rack-power std; spread and p99 were mixed. S1 is descriptive, not an alternative success rule.

Use this exact E12 wording:

> In E12 (small, low-density, bursty Alibaba-derived jobs), thermal_predictive had the lowest and packing the highest time-mean max-rack coolant temperature in all three seeds (PB−TP 0.08–0.18 °C; packing−TP 0.35–0.44 °C). This is below the preregistered 0.5 °C materiality threshold, rests on about two independent workload conditions (seed 3 ≈ seed 2 shifted 33 s), and is descriptive only.

E12 S1: TP lowest on temperature std, hottest 26 mean and spread in all seeds; PB lowest on rack-power std; p99 policy rankings mixed. High counterfactual disagreement alongside small G4 differences does not prove a mechanism or material benefit.

E12 operating quantities remain separate: nominal construction rho 0.6; offered window utilisation 0.485766/0.454619/0.456625 with about 23 min dense +80 min quiet per 1.74 h cycle; realised 0.485618/0.454570/0.456569. Mean waits 8.62/6.00/6.13 s; peak queues 694/564/577; zero censoring. Starts/waits are policy-identical by construction. Seed 3 follows seed 2 after 162 leading pods with a 33.0366 s shift: about two conditions, not three independent replications.

### Invariants and reproducibility

All six historical acceptance gates passed under their approved scopes: IT power/start identity; exact distinct free-node allocation/lifecycle; scoped deterministic evidence; rack-power reconciliation; independent step/clock counts; valid manifests and joined ledgers. Invariant 3 is not a universal direct-repeat checkbox.

- E10: packing seed 1, 2 h fresh-process canonical-byte/exact-interval repeat.
- E11: seed 1 packing/PB2 h exact prefixes against E10; all E11 statuses inherited_not_remeasured; no independent6 h E11 repeat.
- E12: TP seed 1, 6 h fresh-process canonical-byte/exact-interval C′, same machine/environment/SHA. Other 14 configurations inherited and unrepeated; no A′ fallback.
- D7: same-Arch clean-clone code candidate `06032b45ee650e235d5b2b69a5eb5d012a2732e8`, 196 tests in 39.99 s, 22 pinned hashes, exactly one finite Summit smoke, 257 units, 600 s capped warm-up. It is not a matrix repeat or cross-machine portability proof.

No new FMU instance was executed in this reporting pass. The new 195/1 result below supersedes treating the old 196/0 result as evidence about current HEAD.

### Recovery and resource accounting

E12 total **19 attempts =15 selected successes +3 preserved interrupted primaries +1 planned repeat**. Four original successes retained; three partial attempts archived and restarted once; eight previously unstarted configurations run once. Original SHA 18dfea1; recovery SHA e0e1522; only orchestration/accounting changed across those launch generations. C1 ratification is in the post-C4 plan addendum. The original interruption is **Bipin-reported memory pressure**, controller SIGTERM143; the queried journal supplied no corroborating entries. Earlier session-lifetime inference is superseded.

E11 controller wall 4746.698 s. E12 recovery controller 5033.357 s; primary start-to-final-completion span 9565.744 s **including downtime**; about 1850 s downtime is derived from the approximate original termination time, not directly measured. Guarded TP repeat 1479.362 s includes subprocess + validation. E12 simulation RSS 1.63–1.99 GiB, primary service peak 6.925 GiB; report 458.676 s after imports, own peak 4.979 GiB. These scopes are not interchangeable.

## 6. What post-C4 packaging delivered

- A dated, verbatim ratification/decision addendum before other packaging work.
- C5 non-execution note, not a new E13 experiment.
- Results note with G2/G1/G3/G4 tables, S1 specifics, exact E12 ordering, input SHA appendix, scoped reproducibility, verbatim spec§8 + D8, S2 and Opus’s allowed/unsupported claims table.
- Runbook separating executed history from future reproduction, including durable service usage, sources/timing scopes, setup resources and immutable workloads.
- `DEMO.md` asset→allowed-claim/forbidden-use map and a conservative narrative.
- A presentation-only renderer plus 7 fixture cases. Targeted renderer/plot tests: 12 passed in 7.98 s.
- Eight new labelled seed 1 copies: heatmaps, time series and two comparison GIFs for each experiment. Originals untouched; all new assets below 25 MB.
- D7(b), with setup failures retained rather than hidden. Initial setup controller exited 143 before output collection; a later `/tmp` setup failed on quota copying Torch, before tests/smoke. An on-disk clone passed with unchanged lock/tests/inputs. One smoke total, no automatic retry.
- Preservation checks: 1204 original protected files and 230 raw inventory entries verified before cleanup; this pass reverified all 230 at their new local paths. Historical C4 execution documents remain important pinned records.

Labelled scales: E11 **39.252402–56.233641 °C**, E12 **38.702230–42.413286 °C**. Never juxtapose them without stating the ranges. Each asset includes experiment/workload/system/seed, strict evaluation-window context, scale note and negative-G4 caption. E12 labels correlation. First 3 TP distinct-six-decimal counts: E11 [1, 3, 3]→neutral early caption; E12 [1, 1, 1]→the user-approved tie-breaking caption. These are logged-precision checks, not full-precision equality or causal evidence.

After cleanup, these files are physically under `thermoRL/backend/`. Some Markdown/log files are not tracked at their new paths (§7), so links from older checkpoints and a fresh clone may not currently reproduce the packaged navigation.

## 7. Current backend blockers and engineering gaps

### B1 — stale workload root (confirmed blocker for new runs / current wiring test)

`thermoRL/backend/thermorl2/raps_adapter/runner.py:54` prepends `repo_root()/"thermoRL/thermorl-v2"` to relative workload paths. The old directory no longer exists. Direct `load_episode_workload` inspection raised FileNotFoundError before any FMU initialization, although the pinned Parquet exists under `backend/experiments/summit/_workloads/`.

Post-rename command, existing Python3.12.14 environment:

```bash
# cwd: thermoRL/backend; non-FMU tier only
.venv/bin/python -m pytest tests/unit tests/integration -q
```

**Result: 195 passed, 1 failed in 35.43 s.** Failure: `tests/integration/test_runner_contract.py::test_runner_wiring_counts_steps_and_records_completion_reuse`. Its temporary fixture path is also forced through the removed prefix. This is not a missing ignored dataset and not a new thermal/mechanics result. Imports from the backend working directory resolve to the moved backend package; a traceback may retain the historical test filename from moved caches. No fix was applied.

### B2 — empty application source map after rename (confirmed provenance defect)

`runner.py:129`, `experiments/bench.py:47` and `experiments/probes.py:197` still walk the old `thermoRL/thermorl-v2/thermorl2` path. It yields **0 application Python files**, while 39 exist under the current backend package. RAPS entries are collected separately; a future manifest could therefore omit the application source provenance without a useful file-not-found error. Repair and test path discovery before authorizing another run.

### B3 — tracking/ignore regression (confirmed portability gap)

Cleanup commit c09f735 contains **596 renames and 81 deletions**. All 81 deleted tracked files have local mapped equivalents with identical bytes: 29 Markdown, 39 logs, 8 JSONL, 2 Parquet, 2 JSON and 1 extensionless file. Representative untracked current files:

- `thermoRL/backend/README.md`
- `thermoRL/backend/experiments/DEMO.md` and `INDEX.md`
- E11/E12 and other experiment READMEs
- Previously committed E10 small-run evidence and console logs

`thermoRL/.gitignore` ignores `*.md`, the root ignores `*.log` and `runs/`. Review cleanup intent and retain the approved portable scientific record. **Do not force-add the whole backend:** that would risk committing ignored multi-GB E11/E12 raw data. The companion evidence JSON enumerates all 81 candidates and hashes for scoped decisions.

### B4 — paths/environment/documentation need relocation validation

Historical source/manifest paths are old by design; current executable paths and navigation must work under the new layout. The moved venv’s editable `.pth` still contains the old package root. Imports from backend cwd succeed via the current directory, so this is not proof of total import failure; installation/console use from elsewhere needs a frozen environment refresh and validation. Many checkpoint/runbook links still target `thermorl-v2`; the frontend’s legacy instructions still say `thermoRL-new`.

Do not change accepted configs/workloads, historical manifests, source hashes or equality rules merely to conceal path errors. Use relocation-safe current helpers and explicit mapping for historical evidence. Historical D7 passed at 06032b4; current c09f735 needs its own bounded post-repair acceptance. A new FMU smoke would require explicit authorization; no such rerun is assumed in this handoff.

### B5 — frontend replay export is missing

Backend `core.metrics.load_run` resolves existing run/workload data relative to its current package root. The saved ledgers contain the data needed for export, but there is no FMU-to-browser bundle exporter/validated presentation contract yet. There is also no HTTP job-control service in the inspected backend. Neither absence means the simulation engine must be rebuilt.

## 8. Existing frontend: reusable shell, different model

**Source audit only.** No new frontend build, browser/WebGL validation or legacy bundle regeneration was performed in this pass. Source: `thermoRL/frontend/viz/`; Vite + TypeScript + Three.js. Existing built files/legacy bundle are present; `viz/node_modules` was absent when checked.

Reusable pieces: split-screen WebGL rendering, instanced rack meshes, camera fitting, playback/pause/step/scrub controls, static JSONL/inline loading and a decision drawer. `main.ts` reads `window.THERMORL_DATA` or static files; it does not connect to a running simulation server.

The current demo fixture is **24 frames per policy, 0–460 s**, comparing `round_robin` with `thi_lookahead`, with 3 zones (Air/D2C/Immersion) ×16 racks. It is explicitly a constructed wiring fixture, not E11/E12 FMU evidence. The current HTML hardcodes RAMP/24 jobs and old policy names. The legacy `make_demo_bundle.py` executes the old simulator; **do not run it to integrate the FMU backend**. Its bundler can overwrite destinations; do not reuse that behavior for immutable experiment outputs.

| Old viewer assumption | Validated backend reality / required change |
|---|---|
| Three cooling technologies, 48 racks | Homogeneous Summit, 257 racks/4626 nodes. Parameterize geometry; label any layout schematic. |
| THI-baked red/green colours and percentile scale | Actual modeled coolant°C with explicit common within-experiment scale; E11/E12 scales differ. |
| RR versus THI-Lookahead | Packing/PB versus frozen thermal_predictive; use exact policy IDs and negative G4 outcome. |
| PUE, carbon, SLO/emergency counters, dual λ prices | Not supported by this accepted experiment contract. Remove or genuinely mark unavailable; never fabricate zeros or transplant legacy results. |
| Zone-based actions, counterfactual THI/regret | Actual node/rack placements and logged score context. No invented causal explanation or unsupported counterfactual outcomes. |
| Short fixture frames synchronized by index | Six-hour 10 s grids, timestamps and strict1 h evaluation start; validate exact pair alignment, not silent clamping. |

**Source-derived geometry issue:** `scene/racks.ts` allocates 16 rack instances per zone with 4 columns, but `rowZ` supplies only 2 rows; rows 2/3 both fall back to z=0. This gives 12 unique default (x,z) positions for 16 racks per zone. Browser appearance was not checked, but the source-coordinate duplication should be reviewed during the geometry rewrite.

The current Why drawer can be reused structurally, but must display actual logged choices/scores and explicitly six-decimal context where appropriate. Rescoring near-ties does not exactly reconstruct all live choices. The browser should render recorded values, not run replacement RC/THI/PUE physics.

## 9. Recommended integration shape — proposal for Opus, not implementation authorization

```text
Existing immutable FMU run outputs
  → read-only exporter + validated replay contract (missing)
  → compact versioned replay bundle
  → adapted TypeScript loader/schema and257-rack schematic
  → synchronized policy comparison, metrics, timeline and logged-decision inspection
```

Start with recorded E11/E12 seed 1 PB-vs-TP and packing-vs-TP comparisons. Playback is interactive, while its source is honestly labelled precomputed FMU evidence. No new matrix is needed. Existing episode runs take roughly 20–28 min per 6 h E12 configuration, so a live six-hour simulation is not necessary for an on-stage walkthrough.

A proposed minimal bundle should identify experiment/system/workload/policy/seed, original launch SHA, source/input hashes, evaluation window, modelled-temperature units and colour range. It should carry timestamped per-rack temperatures/power/occupancy, selected real job events, frozen summary/decision numbers, and stable references to actual decisions. Current canonical decision rows have no legacy `decision_id`; an exporter may create stable presentation IDs from run identity + decision index without editing the originals.

Avoid inlining every full decision context: E12 canonical JSONL is roughly 200 MB per run. Opus should choose a compact event/decision-detail strategy and explicit size budget. Preserve exact time alignment and the mixed interval semantics; do not substitute defaults or recompute headline metrics in JavaScript. Require exporter tests against recorded data and no-overwrite behavior.

For a browser that starts/controls new simulations, separately design job submission/status/result endpoints, background processes, progress/errors, lifecycle and one-FMU-per-process handling. This is a larger optional product layer, not required for static replay. Do not choose it merely because the directory is named backend.

## 10. Honest readiness and remaining work

| Area | Assessment |
|---|---|
| Scientific/backend engine and planned evaluations | Complete within the approved scope; no major physics/scheduler/research component missing for replay. |
| Current renamed executable/portable package | **Blocked pending B1–B4.** Historical acceptance remains valid at recorded SHAs, but current wiring fails. |
| Replay adapter/data contract | Not implemented; bounded backend integration work. |
| Existing frontend shell | Useful starting point; incompatible scientific domain/schema, plus geometry issue. Runtime/build not newly validated. |
| Live simulation-control API | Not implemented; only needed if Bipin explicitly chooses live browser-controlled runs. |
| Backup | **Waived by Bipin**, not completed; not a remaining demo blocker. Data remains local on Arch. |

The earlier estimate of roughly 1–2 focused working days for backend relocation cleanup + replay export + validation was an engineering estimate, not a promise or measured completion percentage. Opus should revise it after reviewing the actual required contract, payload size and tracking repairs. Frontend work is additional; do not claim end-to-end demo readiness from backend completion alone.

Suggested sequence for the Sonnet brief after Opus review: (1)repair relocation/tracking without scientific changes; (2)bounded tests pass and source-discovery tests cover the move; (3)define/export a minimal trustworthy bundle; (4)adapt the Three.js viewer to the actual system/data/claims; (5)browser/build/interaction/size checks; (6)package and rehearse a complete walkthrough. Backend and exporter changes should be separate scoped commits from frontend presentation work.

## 11. What Opus should verify and decide

1. Audit the recent work and original conditions against the actual code/records; distinguish historical C6/D7 success from current post-rename 195/1.
2. Validate B1–B4, classify the 81 deletions as intentional retirement versus missing tracking, and prescribe the smallest fixes. Do not erase user-owned local deletions.
3. Confirm raw 230-file and frozen 12-section verification, accepted negative outcomes and repeat scopes. On a machine without ignored raw data, label verification limits rather than claiming full raw recomputation.
4. Review the labelled figures/GIFs, results note and exact allowed-claims narrative. Treat old backup-pending language as superseded by the user waiver.
5. Choose replay-first versus live-control architecture explicitly. State why any server/API would be needed rather than assuming one.
6. Produce an implementation-ready **Sonnet 5.5** brief: exact files/contract/layout/payload limits, tasks, tests, checkpoints, priorities and acceptance criteria. Keep frontend work subordinate to real FMU evidence and frozen conclusions.
7. Identify what needs a new Bipin decision. Do not authorize new scientific runs, policy changes, RL/surrogates, a new cooling lever or unscoped research.

## 12. Navigation and audit limits

- Prior acceptance/reviews: `docs/checkpoints/C1-*`, `C2-*`, `C3-*`, `C4-review-opus.md`, `C4-g4-alibaba.md`, `C5-whatif.md`, `C6-final-packaging.md`.
- Packaging/results: `docs/results/2026-11-parasparam-demo-results.md`, `runbook.md`, `d7_fresh_clone_check.json`, `demo_asset_verification.json`, `packaging_source_verification.json`, `final_packaging_checks.json`.
- Current physical artifacts: `thermoRL/backend/experiments/summit/E11_g4_synthetic/` and `E12_g4_alibaba/`.
- Frontend: `thermoRL/frontend/viz/src/{main.ts,schema/vizevent.ts,replay/player.ts,scene/racks.ts}`, `viz/index.html`, legacy stage files and `DEMO_AND_TEST.md`.
- [Companion current-state evidence](2026-10-31-post-c6-review-evidence.json): the complete 81-file mapping, 43-file package comparison, 230 raw hash checks, 12 frozen section checks and exact current test failure.

This reporting pass ran the bounded non-FMU tier once, read-only loader/path checks, source/file tracking comparisons and raw/frozen hash verification. It did **not** run any new FMU, matrix, report CLI, legacy simulation, frontend build/browser session, backend repair or frontend implementation. Existing unrelated local deletions were left alone. All current findings are source/record-derived unless explicitly labelled inference/proposal.
