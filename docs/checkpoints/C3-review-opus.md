# C3 Independent Review — E11 Frozen G4 Synthetic Matrix

**Reviewer:** Claude (Opus), the incoming independent research reviewer and planning lead. **Date:** 2026-10-30.

**Reviewed SHA:** `bf88ed8e8578b11aee990b363b6428284d2953a7`, the tip of `origin/feat/parasparam-demo` and the expected C3 tip.
- Delta reviewed: `66f7753..bf88ed8`, which is `ea3a26d` (fixes), `6ee93c4` (preregistration), `ceb2c98` (results) and `bf88ed8` (C3 report). It touches 71 files.
- My local branch has one extra commit, `4d9a3be`, which is Bipin's local, unpushed handoff document (`docs/HANDOFF-2026-10-30-opus-takeover.md`). It contains no code or evidence and is not part of the reviewed scope.

**Labels:**
- FACT: checked directly.
- DERIVED: I calculated it myself.
- INFERENCE: a supported interpretation.
- HYPOTHESIS: plausible but not tested.
- UNRESOLVED: not established.

**Execution boundary:** Nothing was run against an FMU or a RAPS simulation on the Mac. Tests were limited to `tests/unit`, in a scratch venv built with `uv sync --frozen`. No integration tests were run, because they start small RAPS engines. No artifacts were regenerated or overwritten.

---

## 0. Verdict: **ACCEPT C3 WITH CONDITIONS**

The E11 matrix ran as preregistered. The frozen G4 rule was applied correctly. The negative primary outcome holds with a wide margin:
- the largest per-seed PB−TP gap is 0.342 °C, against a 0.5 °C threshold;
- two of the three seeds have negative gaps.

I found no critical or launch-type defect.

The conditions concern **interpretation and downstream wording** (§4, §7). They block none of the next preparation work. They do bind Tasks 15–17 and any presentation:
1. The primary null extends to **default packing**: packing − TP is +0.08, −0.11 and +0.28 °C. Therefore "packing creates hotspots that thermal-aware placement removes" is **not supported** on the preregistered max-rack metric. Hotspot language may describe only the distributional metrics, with their numbers.
2. The reproducibility claim (spec §6, claim 1) must carry the exact Option-A scope. No six-hour run and no temperature-reading policy has been repeated.
3. Spec §8 says "weak rack-to-rack coupling". C1 finding I1 and the E10/E11 M3 evidence contradict this. Bipin must decide how Task 17 quotes §8 "verbatim" (§7, F6).
4. The precision limits of rounded-context reconstruction (F3) must be carried into the "why this rack?" view in Task 15.

---

## 1. Handoff orientation and what changed

**Handoff:** `docs/HANDOFF-2026-10-30-opus-takeover.md`.
- Written 2026-10-30 and committed locally as `4d9a3be`, after `bf88ed8`.
- It describes the repository state **at C3 launch**. It names no reviewed SHA of its own. The last Opus review it references is `66f7753`, which reviewed `552e9b8`.

**Where the handoff is outdated or superseded:**

| Handoff statement | Current status |
|---|---|
| "You are the implementation and execution agent" (§0) | **Superseded** by Bipin's latest instruction. Sol/Codex on Arch remains the executor; Opus reviews and plans. |
| C3 "to be produced by Sol" | Produced at `bf88ed8`. |
| R5, R6, R8, R14–R16 open (§7) | **Done:** R14 (`fmu_s_scope` wording); R15 (README documents p99 interpolation and censoring); R7, R9–R13 (FACT, `ea3a26d`). **Partly done:** R16 (`workload_meta_sha256` is in the manifests and the preregistration, but not in `by_seed`). **Open:** R5 (the all-skip path returns before seed checks and inventory, `run_matrix.py:264-266`); R6 (no SIGTERM/SIGHUP handling); R8 (documented only). None of these affected E11: there were no skips, no signals, and the matrix ran from `thermorl-v2`. |
| §9: the Task 17 Step 4 rerun is "superseded by Option A" | This is the previous session's interpretation. **No approved addendum supersedes Task 17 Step 4.** The approved addendum covers the E11 launch only. It needs a fresh Bipin decision (§9, D7). |
| "Expected honest headline… thermal-aware placement removes [hotspots]" (§1) | **Not supported** on the primary metric (§4, F1). |

---

## 2. Independent reproduction: what is verified, and how

The 15 raw run directories are absent on this Mac. They are intentionally gitignored and remain on Arch, so their absence is not a policy violation.

| Item | Method | Result |
|---|---|---|
| Primary metric, all 15 runs | **DERIVED from a committed derived file.** `results/max_rack_attribution.json` holds the per-tick argmax rack and its full-precision `t_c` for every window tick. I checked: t_s = 3610…21600 in 10 s steps, exactly 1800 per run, all strictly > 3600 and ≤ 21600; `raps_power_tick_s = t_s − 10`. | Every `maxrack_mean_c` matches `metrics.csv` to ≤ 7.1e-15 °C. The rack shares recompute exactly. |
| G4 rule | DERIVED, applied by hand at full precision | PB−TP: **+0.342495, −0.147190, −0.070865 °C**; none reaches 0.5. `value_beyond_power = false`. Matches `decision.json` and `report.py:35-49`. |
| Preregistration before the runs | FACT: git and journal | `6ee93c4` was committed 11:37:20 UTC. The first `started` event is 11:37:32 UTC (`matrix_events.jsonl`). Frozen README sections are byte-identical between `6ee93c4` and `ceb2c98` (`git diff`). `config.yaml` is byte-identical to `configs/g4_synthetic.yaml`. |
| Exactly 15 runs, no retries | FACT from the journal | 15 `started`, 15 `completed`, no `failure_archived` and no `matrix_stopped` events. Three-way concurrency is visible. Wall time: 11:37:32 → 12:56:39, which agrees with 4746.7 s. |
| Manifests | FACT: the 15 committed mirrors | Each mirror's SHA equals its `run_files.json` entry. Ledger hashes in the manifests are consistent with the inventory. Each manifest records: git `6ee93c4`, dirty (porcelain lists only unrelated document deletions, `docs/prompt-opus5-5-C2.md`, and the matrix journal); FMU `0a6ca377…9233`; workload SHA equal to `by_seed` and to the local parquet; warm-up 7200, `capped_preconditioned_not_settled`; `fmu_steps` 2160; `backend_elapsed_s` 21600; TP parameters exactly G1 (a = 27.9753857271229, b = 0.8052450824355937, τ = 4050, H = 600). They also record `job_events_sha256`, 0 samples > 70 °C, 0 negative pump samples, and a reconciliation of 0.0. |
| Source hashes | FACT, against `git show 6ee93c4:<path>` | All 38 recorded source hashes match. No decision-path change since `0c32cf5`: the `ea3a26d` runner diff only adds `require_assertions`, phase tags, failure classification, assertion messages and manifest fields. |
| Protected paths | FACT: `git diff 66f7753..bf88ed8` | Empty for `sim-raps/`, `models/`, `thermal/`, `core/`, `configs/`, `scheduler.py`, `jobs.py`, `_workloads/`, E01, E10 and `tests/fmu`. |
| Determinism-evidence files | FACT | `determinism_evidence.json` SHA equals its `.sha256` seal (`0020d8c2…`). All present references match their recorded SHAs: E10 `rerun_1.json`, the E10 seed-1 ledgers, `prefix_vs_E10.json`, and both workloads. The four E11 raw references are absent here. |
| Unit tests | DERIVED: Mac scratch venv from the lock | `pytest tests/unit` → **112 passed**. The 27 integration tests were **not run** here, because they start RAPS engines; Sol reports they pass. |
| S1 directional statements | DERIVED from the committed `metrics.csv` | Confirmed (§5). The values themselves are Sol's computation from the raw ledgers. |
| G3 NOT_USABLE (Task 16) | DERIVED from committed `E03…/series.parquet` | Affected Δ = 0.5389860 °C, unaffected Δ = 0.1018374 °C → NOT_USABLE. The candidate list has 62 entries plus a header. |

**Reported by Sol and not independently verified** (each needs the raw ledgers):
- invariants 1, 2 and 4 on the raw ledgers;
- the prefix check (`prefix_vs_E10.json`: 1514 decision rows and 185,040 interval rows, identical for both policies);
- disagreement and self-reproduction rates;
- latency;
- raw maxima, the > 70 °C counts and THI;
- `independent_audit.json`. This is Sol's own self-audit, and its script is not committed (F4).

**Smallest raw subset, if Bipin wants this closed.** It is **not needed for my verdict**, because the primary metric comes from the committed per-tick series and the margin is large.
- For an independent prefix check against the local E10 ledgers: seed-1 `packing` and `power_balance` `decisions.jsonl` plus `intervals.parquet` (about 4 files, about 110 MB).
- To recompute everything from raw: the 15 `intervals.parquet` files (about 9 MB each).

---

## 3. Primary negative result and its scope

FACT/DERIVED, `maxrack_mean_c` in °C, window 3600 < t_s ≤ 21600:

| Seed | packing | node_balance | power_balance | coolest_rack | thermal_predictive | PB−TP | packing−TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 54.0702 | 53.8835 | 54.3304 | **53.5348** | 53.9879 | +0.3425 | +0.0823 |
| 2 | 54.1771 | **54.0946** | 54.1377 | 54.1235 | 54.2849 | −0.1472 | −0.1078 |
| 3 | 54.1228 | **53.5598** | 53.7758 | 53.7804 | 53.8466 | −0.0709 | +0.2761 |

**DERIVED observations:**
- The within-seed range across all five policies is 0.19–0.80 °C.
- No policy is consistently lowest; the lowest is coolest_rack, then node_balance, then node_balance.
- thermal_predictive is never lowest.
- packing is not consistently highest.
- Per-tick PB−TP differences are large but average out. The 5th–95th percentile spans are −0.46/+1.54, −1.57/+1.58 and −0.84/+0.49 °C.
- The seed-1 mean gap of +0.34 comes from hours 3–6. Hours 1–3 contribute about 0.

**Exact supported conclusion (for wording):**
> Under the frozen E11 protocol (Summit POWER9 cooling FMU, nominal 290 K, synthetic ρ = 0.6 workload, 6 h, capped unsettled warm-up, seeds 1–3), `thermal_predictive` did not reduce time-mean max-rack coolant temperature by ≥ 0.5 °C relative to `power_balance` in every seed (gaps +0.34, −0.15, −0.07 °C). Pre-registered outcome: **no material value on the homogeneous twin.** On this metric no policy, including default packing (packing − thermal_predictive +0.08, −0.11, +0.28 °C), was consistently separated from the others.

**Scope:**
- this frozen heuristic with frozen G1 parameters;
- one synthetic workload law;
- three seeds;
- one homogeneous liquid-cooled POWER9 twin, with modelled coolant (not measured hardware);
- this window and warm-up.

**It does not show that thermal information is useless in general.** It is a valid negative result, not a mechanics failure. It does not justify tuning.

**INFERENCE: why the metric barely discriminates.**
- The per-tick maximum is usually a rack that hosts a high-power job filling most of a rack. The argmax rack draws ≥ 40 kW in 69–97 % of window ticks (DERIVED).
- The frozen rule places any job that fits within one rack, so every policy must create such a rack. Rack choice changes *which* rack this is, but on a homogeneous plant it barely changes *how hot* that rack becomes.
- Treat this as an explanation consistent with the data, not a tested mechanism (HYPOTHESIS for the causal part).

---

## 4. Interpretation conditions (what may and may not be said)

- **Allowed (spec §6):**
  - "Placement alone changes the rack thermal distribution at identical IT power and timing." Supported by S1 (§5) and invariants 1 and 4.
  - "The measured packing → thermal gap." It must be reported as ≈ 0 on the primary metric, with distributional gaps given separately.
  - "How thermal awareness compares with power balance." Use the frozen negative outcome above.
- **Not supported:**
  - "Packing creates hotspots that thermal-aware placement removes", stated about max-rack temperature.
  - Any policy ranking on the primary metric.
  - Treating `top_decile_mean_c` PB−TP (+0.54, +0.52, +0.46 °C) or `rack_t_std_mean_c` as a substitute G4 criterion.
- **Reproducibility claim** (spec §6, claim 1). Use the exact wording:
  > "Fresh-process reproducibility was verified for E10 packing seed 1 (2 h) and, by exact prefix reproduction, for E11 seed-1 packing and power_balance over the first 2 h; no 6 h E11 configuration and no temperature-reading policy was repeated."

---

## 5. S1, attribution, disagreement and precision

### 5.1 S1 metrics (DERIVED from `metrics.csv`; descriptive only)

| Metric | PB − TP (seeds 1, 2, 3) | packing − TP | Lowest policy per seed |
|---|---|---|---|
| `rack_t_std_mean_c` | +0.37, +0.32, +0.29 | +1.95, +1.99, +2.01 | coolest_rack ×3 |
| `top_decile_mean_c` | +0.54, +0.52, +0.46 | +1.26, +1.47, +1.51 | coolest_rack ×3 |
| `rack_kw_std_mean` (kW) | **−0.28, −0.42, −0.47** | +2.37, +2.63, +2.62 | power_balance ×3 |
| `spread_mean_c` | +0.49, **−0.06**, +0.06 | +1.59, +1.59, +2.26 | mixed |
| `maxrack_p99_c` | −0.02, +0.55, −0.64 | mixed | mixed |
| `mean_rack_c` | ≈ +0.008 | ≈ +0.05 | — |

**C3's S1 statement is correct as worded.** TP has lower rack-temperature std and lower hottest-decile mean than PB in all three seeds. It **must not be generalised**:
- TP's rack-**power** std is higher than PB's in every seed;
- spread and p99 are mixed.

Packing has about twice the rack-temperature std and a hottest-26 mean 1.3–1.5 °C higher than TP in every seed. That is the defensible "placement changes the distribution" finding.

TP's S1 profile is close to coolest_rack's. This is consistent with C1 I3 (TP ranks by ≈ 0.86·T + 0.11·P), so it is mostly coolant-driven (INFERENCE).

### 5.2 M2 / attribution over six hours (DERIVED from the attribution file and the workload parquets)

**The E10 pattern does not persist unchanged.**
- In seed 1, job 184 (32 nodes, CPU 2.0, 6 GPUs, R = 6884 s) is resident at the argmax for **23.4 % of window ticks under every policy**: t_s 3610–7810, while it runs at peak.
- After that, the argmax is spread over 7–15 racks per run and many jobs. These include 16-node jobs at CPU 1.5 / 6 GPUs, and 1–2-node jobs that coexist on the hottest rack.
- Window ticks whose argmax rack hosts a full-power ≥ 16-node job: 29–43 % (seed 1), 13–20 % (seed 2), 13–27 % (seed 3).
- The argmax rack is sometimes empty, at idle 13.82 kW: 0.1–6 % of ticks, highest for coolest_rack and TP (thermal lag after a job ends; INFERENCE).
- Resident fractions mean coexistence, not causal contribution.

**M2 stands as a limitation.** The max metric is governed by a few large high-power jobs and when they arrive, not by policy.

### 5.3 M3 recurs in E11

DERIVED: from t_s 3610 to 7810 in seed 1, the argmax rack under packing, node_balance, power_balance and thermal_predictive hosts job 184 at the **identical own power of 49.323 kW**:
- under node_balance, power_balance and TP, the racks (181, 181, 194) agree within 0.03 °C;
- under packing, rack 55 is **0.61 °C cooler on average, and up to 0.99 °C cooler**.

The own-power history *before* the window was not checked, because that needs the raw intervals. The direction matches E10, and also C1 I1: G2 packed full racks were cooler than uniform-load full racks.

**The mechanism remains UNRESOLVED.** No hydraulic or thermal cause is claimed, and no characterisation is requested.

### 5.4 Disagreement and self-reproduction (Sol-reported; the method was checked in code)

- `metrics.py:137-155` and `report.py:209-213` re-score **both** scorers on the same six-decimal logged context. Self-reproduction is a separate measure. Global node IDs are distinct.
- PB-vs-TP disagreement is 0.63–0.96, depending on the context source.

**F3, the precision diagnostic.** Self-reproduction is 94.8 % for TP and 90.0–90.6 % for coolest_rack. INFERENCE: about 5 % of TP live decisions, and about 10 % of coolest_rack live decisions, were decided by score margins below the 1e-6 logging precision. In other words, they were near-ties among nearly identical racks, decided by sub-micro-degree coolant differences.

Consequences:
1. A Task 15 "why this rack?" panel can show the **logged** scores and the **actual** logged racks. It must not present rescored choices as exact reconstructions.
2. Temperature-reading policies are where floating-point nondeterminism would surface first. This is a concrete reason to prefer a TP rerun for any E12 determinism evidence (§9, D6).

It does not threaten the E11 negative outcome. Two seeds have negative gaps, and run-to-run perturbation would need to push all three to ≥ +0.5 °C (INFERENCE).

---

## 6. Invariants and determinism evidence

| Inv | Status | Basis |
|---|---|---|
| 1. IT kW and start times identical | PASS (2.73e-12 kW) | Sol, from raw. Corroborated: `it_energy_kwh`, `jobs_started` and wait statistics are identical within each seed in `metrics.csv`, and the journal records `seed_cross_policy_invariants_passed` ×3. |
| 2. Exact distinct free nodes; lifecycle replay | PASS | Sol (`report.py:52-80`). The code was checked; job events are required and hashed. |
| 3. Determinism | **`inherited_not_remeasured` for all seeds** | See below. |
| 4. Power reconciliation | PASS (0.0 in every manifest) | FACT from the manifests; recomputation from raw is Sol's. |
| 5. Steps and clock | PASS: 2160 steps, 21600 s, complete grid | FACT from the manifests; the grid is corroborated by the attribution file. |
| 6. Provenance and ledgers | PASS | FACT (§2). |

**Invariant 3 is implemented exactly as approved.**
- `report.approved_determinism` (`report.py:174-185`) accepts only status `inherited_not_remeasured`, with evidence-kind lists of exactly `[inherited_E10, E11_prefix_vs_E10]` for seed 1 and `[inherited_E10]` for seeds 2–3, each with `result is True`.
- A measured prefix failure sets seed 1 to `failed` (`evidence.py:80`). `seed_gate` then writes `INVALID` and raises. Tests cover both the accept and the invalidate paths (`test_e11_evidence.py`).
- The evidence file sits outside the launch config. It is SHA-sealed, and its references are re-hashed by `report.main`.
- **INHERITED:** E10 packing seed 1, 2 h. Covers that configuration only.
- **NEW:** seed-1 packing and power_balance prefix (t_s < 7200 decisions; t_s ≤ 7200 intervals), reported as passing.
- **Not measured:** any 6 h E11 configuration, and any temperature-reading policy.

C3 and the README keep these distinct. Labelling is correct.

---

## 7. Findings (ranked)

### Critical
None.

### Major — interpretation (they bind wording, not launches)

| ID | Finding | Evidence | Consequence | Smallest fix |
|---|---|---|---|---|
| **F1** | The primary null covers packing vs TP too. No policy is consistently best on max-rack. | §3 table; `decision.json` `packing_minus_thermal_c` | The "hotspot removal" headline (handoff §1) is unsupported on the preregistered metric. | Use §3 and §4 wording in Tasks 15–17. Distributional claims only with S1 numbers. No new run. |
| **F2** | M3 recurs: identical own power at the argmax, packing's rack 0.61 °C cooler. | §5.3 | G1's own-rack model omits a non-local dependence. This plausibly limits any T/P-based heuristic (HYPOTHESIS). | State it as an observation, mechanism UNRESOLVED. No characterisation. |
| **F3** | About 5 % (TP) and about 10 % (coolest_rack) of live decisions fall below the logging precision. | §5.4; `decision_diagnostics.json` | Constrains Task 15 explanation views and motivates the E12 determinism choice. | Label views; follow D6. No schema change. |

### Minor — engineering and documentation (none blocks)

| ID | Finding | Evidence | Smallest fix |
|---|---|---|---|
| F4 | `independent_audit.json` records results, but the audit procedure (script) is not committed, so it cannot be independently re-executed. | `ceb2c98` file list | Commit the audit script with Task 17, or label it "Sol self-audit". |
| F5 | The invariant-3 key is still named `3_decisions_byte_identical_and_interval_values_identical`, but its value is a status record. A downstream table could render it as ✓. | `report.py:166` | Task 17 tables must print the `status` text. No code change is needed. |
| F6 | Spec §8 says "weak rack-to-rack coupling", which contradicts C1 I1 and M3. Task 17 requires §8 verbatim. | Spec line 310; C1 review I1; §5.3 | Bipin decides (D8). Recommendation: quote verbatim plus a dated annotation citing I1 and M3. |
| F7 | Failure classification: any `OSError` is `non_scientific_io` (retry-eligible), even in the FMU phase. A scientific stop archives healthy collateral runs under the scientific kind, which then need an override. | `runner.py:236-239`; `run_matrix.py:216-221` | Conservative and not exercised in E11. Optionally refine before E12. |
| F8 | R5 (all-skip exit skips seed checks and the inventory) and R6 (no SIGTERM handling) remain open. | `run_matrix.py:264-266` | Optional before E12. |
| F9 | Run cost is bimodal (about 570–630 s vs 1070–1160 s FMU time), independent of policy. Most likely CPU contention under 3 workers (INFERENCE). | `metrics.csv` `fmu_s` | Informational for E12 budgeting only. |

---

## 8. What blocks further work

**Nothing in C3 blocks proceeding.** The genuine blockers for the next phase are **Task 13 planning ambiguities**. They come from the dataset itself, which I inspected read-only on the Mac copy. All local checksums are OK. **Availability on Arch is unverified.**

| ID | Issue (DERIVED from `datasets/alibaba_gpu_2023/raw/`) | Why it blocks |
|---|---|---|
| **A1** | `openb_pod_list_multigpu50.csv` has **only 5 columns**: name, cpu_milli, memory_mib, num_gpu, gpu_milli. It has **no `pod_phase`, `creation_time` or `deletion_time`**. Its 8152 pods are byte-identical in resources to `default`, plus 909 extra multi-GPU pods with no timing. | The plan's `load_pods` and `derive_workload` cannot be applied to it, so `choose_variant` cannot compare two runnable variants. Joining timing by name would invent data for 909 pods. **Only `default` is spec-implementable.** |
| **A2** | Times appear to be seconds (creation 0–12.90 M ≈ 149 days; median runtime 723 s), but the units are not documented in the file. The kept set (non-Pending, GPU > 0) has 6203 pods: Running 4149, Failed 1869 (median 243 s), Succeeded 185. 33 % of runtimes fall below 300 s and are floored; 4.3 % exceed 6 h and are capped. | The spec keeps Failed pods, and Running pods' deletion semantics are unknown. These are assumptions to record, not decide silently. |
| **A3** | Rate scaling: the mean original inter-arrival is 2080 s and the target is ≈ 1.01 s. That is a **≈ 2064× compression of arrivals only** (runtimes are uncompressed), about **21,400 jobs per 6 h run**, and **≈ 3.45 cyclic passes** over the 6203 pods. | The wrap-around gap is undefined. Seeds are only rotations of one sequence, not independent draws. Burstiness is preserved only in shape. |
| **A4** | Under G = 6: 99.3 % of jobs are 1-node (max 2); mean GPU ≈ 0.86/6 and CPU ≈ 0.45/2 per node. | Expect much lower power density and no rack-filling jobs, so a weak thermal contrast. That is legitimate external-validity evidence, but it must be stated in the preregistration, never tuned. |
| **A5** | At about 8.7 KB per decision row, `decisions.jsonl` is ≈ 186 MB per run, ≈ 2.8 GB per matrix. `report.main` loads all 15 runs at once (`report.py:258`), and a Python-object estimate is ~10 GB RAM. | Feasibility risk. Measure it, or refactor non-scientifically to per-seed loading. |
| **A6** | The E11 prefix gate cannot apply to Alibaba data. | E12 needs its own determinism scope (D6). |

---

## 9. Remaining-task roadmap (Tasks 13–17)

**Decisions Bipin needs to make. These are proposals and are NOT approved.**

| ID | Decision | Recommendation |
|---|---|---|
| D1 | Accept C3 with conditions (§0, §4) | Accept. |
| D2 | Alibaba variant | Use `default` only. Record that `multigpu50` lacks the §3.4 timing fields. Report its mapped power statistics descriptively, computed before any run. This is a documented plan deviation, not a selection. |
| D3 | Runtime representation | Runtime = deletion − creation in seconds, for all non-Pending GPU pods including Failed and Running (spec-literal). Clip to [300, 21600]. Assert integer. `time_limit = ceil(1.5R)`. Record phase mix and clip fractions. |
| D4 | Arrivals | Sort by (creation_time, file row). Take the original inter-arrival sequence cyclically from a `default_rng(seed)` start offset. Make the wrap gap equal the mean original inter-arrival. Scale factor = mean original inter-arrival / target, where target = E[nodes·R]/(ρ·N), computed exactly over the mapped set. Submit = cumulative scaled gaps, keeping those < horizon. Admission stays at `ceil(submit)`. Document ~2064× compression, ~3.45 passes, and that seeds are rotations. |
| D5 | Feasibility | Before preregistration, report job counts, ledger sizes and estimated report memory. If needed, approve a metric-neutral per-seed loading refactor. Verify it on Arch by regenerating E11 metrics into a **scratch** directory and byte-comparing with the committed `metrics.csv`. |
| D6 | E12 determinism scope | **Option C′:** 15 runs plus **one** fresh-process 6 h rerun of `thermal_predictive` seed 1, requiring byte-identical decisions and identical interval values (status `verified_E12` for that configuration only; others `inherited_not_remeasured`). The minimal alternative is A′: no rerun, all statuses inherited from E10 synthetic packing, with an explicit statement that this is weak cross-workload evidence. |
| D7 | Task 17 Step 4 (fresh-run check) | Either authorise one E11 `thermal_predictive` seed-1 rerun into `provenance/rerun_1_thermal_predictive_seed1/` (≈ 10–20 min; never alters G4), or record Step 4 as not executed and use the §4 reproducibility wording. The full `uv run pytest -q` launches FMU tests on Arch and needs explicit authorisation too. |
| D8 | Spec §8 coupling wording | Quote §8 verbatim, followed by a dated annotation citing C1 I1 and M3. |

**Roadmap:**

| Phase | Content | Stop |
|---|---|---|
| **Next (proposed)** | Task 13 implementation, E12 workloads, power statistics, preregistration. **No E12 policy run.** | **C4-prelaunch** stop and review |
| Then | Task 14: E12 matrix (15 runs plus the D6 rerun, if approved), report, C4 | **C4** |
| Then | Task 15 (time-box 1 day): export from existing E11 seed-1 ledgers on Arch (no simulation). Viz copied from `thermoRL/thermoRL-new/viz/` (present). The "why this rack?" panel shows logged scores and actual racks; any rescoring is labelled "six-decimal reconstruction". The negative primary result is shown on the replay. Fallback: the existing GIFs. | — |
| Then | Task 16: C5 note only. G3 NOT_USABLE (0.538986 < 1.0 °C); 62 candidate CDU parameters listed, none applied; no G5/E13. | **C5** |
| Then | Task 17: results note (§3/§4 wording; S2 verbatim; M2/M3; §8 plus the D8 annotation); runbook separating **executed** commands from **reproduction** commands; `DEMO.md` asset → claim map; Step 4 per D7. | **Final review** |

Not prerequisites, and not authorised: history/predictor experiments, G1 refit, scheduler or spanning redesign, new characterisation, RL, surrogates, a G3 rerun or lever tuning.

---

## 10. Smallest bounded next assignment

Once D1–D6 are approved:

**Sol (Arch):**
1. Verify `datasets/alibaba_gpu_2023` with `checksums.txt`. If it is missing, stop.
2. Implement Task 13 (`alibaba.py`, `g4_alibaba.yaml`, dispatch in `runner.py` on `workload.kind`), test-first, using the D2–D4 resolutions. Tests must cover:
   - the plan fixtures;
   - the wrap rule;
   - integer runtimes;
   - `time_limit ≥ R`;
   - sorted submits in [0, horizon);
   - seed determinism;
   - offered utilisation within ±15 % of 0.6.
3. Generate seeds 1–3 workloads in the locked environment: SHA-keyed sidecars, horizon assertion, never overwrite. Commit `variant_choice.json` / power statistics (default; multigpu50 descriptive) **before** any policy run.
4. Report the D5 feasibility numbers.
5. Write the E12 README and config preregistration: frozen G4 rule, metrics, S1, S2 verbatim, M2/M3, A2–A4 assumptions, and the D6 scope.
6. Write `docs/checkpoints/C4-prelaunch-status.md`, commit, push, **STOP**. No E12 policy simulation.

---

## 11. Evidence ledger

| Claim | Evidence | Status | Scope / limits | Next discriminating evidence |
|---|---|---|---|---|
| G4: no material value beyond power | Per-tick max series → means; frozen rule | **DERIVED** (committed derived file); raw: Sol | E11 regime only (§3) | E12 (preplanned external validity) |
| Packing ≈ TP on max-rack | Same | DERIVED | Same | — |
| Placement changes the thermal distribution | S1 in `metrics.csv`; invariants 1/4 | DERIVED from derived; raw: Sol | Descriptive; not a G4 criterion | — |
| TP < PB on rack-T std and top decile, all seeds | `metrics.csv` | DERIVED | Not rack-kW std, spread or p99 | — |
| M2: max governed by few high-power jobs | Attribution + workloads | DERIVED | Coexistence, not causation | — |
| M3 recurs (0.61 °C at identical own power) | Attribution, seed 1, 3610–7810 s | DERIVED | Pre-window own-power history unchecked; mechanism UNRESOLVED | None required |
| Preregistration preceded runs; protocol unchanged | git timestamps, journal, diffs, configs | FACT | — | — |
| 15 runs, no retries | Journal | FACT | — | — |
| Inv 1/2/4 pass | `invariants.json`, journal | Sol-reported; corroborated | Raw not on Mac | Optional raw subset (§2) |
| Inv 3: inherited + seed-1 2 h prefix | Evidence files and seal; code | FACT (structure); prefix result Sol-reported | No 6 h or TP repetition | D6 / D7 rerun |
| ≈ 5 % TP / 10 % coolest_rack decisions below 1e-6 margins | Self-reproduction + code | Rates Sol-reported; interpretation INFERENCE | Logging precision | None required |
| G3 NOT_USABLE | E03 series | DERIVED | 3 h finite horizon | None (frozen) |
| `multigpu50` lacks timing fields | Local dataset (checksums OK) | FACT on the Mac copy | Arch copy unverified | Sol checksum on Arch |
