# C1 Independent Review: FMU Selection and Physics Characterization

- **Reviewer:** Claude (Opus), independent technical and scientific review.
- **Date:** 2026-10-27.
- **Reviewed SHA:** `f77b14924b6c8debb1d1b1d5166710dfe16bed8a`. This is the `origin/feat/parasparam-demo` tip at fetch time and equals the expected C1 tip; the remote had not advanced.
- **Baseline:** `439cae9ef559b2d05e8ba1b317419aaffb04194e`.
- **Commits reviewed:** all 9 between baseline and reviewed SHA: `a7a0c1a`, `554af93`, `db56190`, `c6e127a`, `41c6585`, `2d14161`, `6f88579`, `2bd9b96`, `f77b149`. That is 142 files, +23,444/−9.

**Labels:**
- **FACT:** checked directly.
- **DERIVED:** I calculated it independently from committed raw artifacts.
- **INFERENCE:** a supported interpretation.
- **UNRESOLVED:** not established.

## 0. Verdict

**C1 is correct and merge-ready. Nothing in the C1 deliverables blocks merging.**

**DERIVED:** Every reported primary number reproduces exactly from the raw parquet series, independently of Sol's audit files. This covers:
- three G2 Δ values and their classes;
- the X01 selection, runner-up and 80 % tie threshold;
- G1 levels, t63 values, fit, τ and `t_hot_c`;
- G3 deltas.

**FACT:** Preregistration preceded every results commit, and no frozen section changed afterwards. Source hashes match the executed commits.

**Two items must be resolved by explicit steering before Task 5 starts.** Neither is a defect in C1's experiments. Both are test-specification issues that the Summit selection exposed:

- **R1 — Summit rack-power definition.**
  - **FACT:** RAPS applies Summit rectifier losses that `rack_power_bounds` (spec §3.1) omits. RAPS idle is 13.823 kW against the probe's 13.202 kW, and peak is 49.323 kW against 47.282 kW.
  - The plan's Task 5 `test_idle_power_reconciles` asserts `|mean − idle_kw| < 0.05` and will therefore fail on Summit, which is a stop condition.
- **R2 — cost-guard formula.**
  - The plan's guard is `total_s × 2 > 45 × 60`.
  - The spec's and the preregistered X01 rule's wording is "measures more than 45 min per 6 h run", with no ×2.
  - Neither text says whether the warm-up is counted.
  - For Summit, the choice of reading could plausibly decide whether we switch to Lassen.

**Recommendation:** merge C1; make the R1 and R2 decisions (§6); then authorise Task 5. Interpretation items I1–I6 should be carried into C2/C3 reporting. They do not block engineering.

---

## 1. Independently verified results

**Method.** I wrote scratch scripts against the committed `series.parquet`, `warmup.parquet` and `summary.json` files, outside the repo, without executing any FMU. Separately, a sub-reviewer re-ran 48 unit and 7 integration tests (55 passed) in a scratch Python 3.12 environment on the Mac, and ran one 30 s idle Summit RAPS engine to check power accounting.

### 1.1 G2 and X01

Δ is the mean over the window of the per-sample cross-rack maximum, packed minus spread. The window is `9000 < t ≤ 10800`, using right-endpoint samples: 90 samples at Δt = 20 s, or 180 at Δt = 10 s.

| System | Recomputed Δ °C | Reported | Class | Alt. Δ (max of rack means) | Packed vector check | C_s (min / 6 h) |
|---|---:|---:|---|---:|---|---:|
| lassen | 2.036319592756 | identical | GO | 2.036289 | 26 full + 1 partial (20.286 kW), total = 44·P(0.6) exactly | 0.304157671949 |
| summit | 6.234888984342 | identical | GO | 6.234889 | 154 full + 1 partial (20.018 kW), total exact | 21.912337247551 |
| marconi100 | 0.054796806701 | identical | STOP | 0.054651 | 29 full + 1 partial (22.841 kW), total exact | 0.394916788800 |

**DERIVED:**
- **Eligibility.** All three systems are eligible: sane, and C_s ≤ 30.
- **Candidate.** Summit. Its 80 % threshold is 4.987911187473 °C, and Lassen's 2.036 °C is below it, so the tie pool is {summit} and no tie-break applies.
- **Primary and runner-up.** Primary is **summit**. Runner-up is **lassen**, under both the rule re-applied to the remainder and plain Δ order.
- **Marconi100.** Its STOP is per-system only. The selected class is GO, so the X01 STOP condition does not fire.
- **Robustness.** The alternative max-rack definition gives the same classes, so the result does not depend on that definitional choice.

### 1.2 Lassen reproducibility (approved clarification)

**DERIVED (SHA-256 comparison):** The rerun is byte-identical to the original in:
- `scientific_summary.json`, `series.parquet`, `warmup.parquet`, `globals.parquet`;
- `input_sequence.json`, `branch_initial_observations.json`.

The full `summary.json` files differ **only** in `fmu_s_per_sim_h` and `projected_closed_loop_min_6h`. `scientific_summary.json` excludes exactly those two keys and adds none.

**FACT:**
- The clarification text was committed in `c6e127a` (02:10), before the G2 results commit `2d14161` (02:39).
- X01 uses the original-run costs.
- No other difference is hidden.
- UNRESOLVED (minor): the approval itself happened in conversation.

### 1.3 Summit G1 (all five levels)

Window `9900 < t ≤ 10800` (90 samples). Each rack is time-averaged first; mean, min and max are then taken across racks.

| f | Rack kW (FMU input) | Final mean °C | t63 s | Slope over last 15 min (K/min) |
|---|---:|---:|---:|---:|
| 0 | 13.201714 | 40.041535 | 4930 | +0.0029 |
| 0.25 | 21.721867 | 44.058848 | 3550 | +0.0091 |
| 0.5 | 30.242020 | 51.579892 | 4050 | +0.0256 |
| 0.75 | 38.762173 | 59.165657 | 4130 | +0.0418 |
| 1 | 47.282327 | 66.792188 | 4170 | +0.0581 |

**DERIVED:**
- Fit: a = 27.975385727123, b = 0.805245082436, R² = 0.989167647689. All three match.
- `tau_s` = median(3550, 4050, 4130) = **4050 s**. Matches.
- `t_hot_c` = 63.304922110353. Matches.
- Raw maximum is 67.213 °C, so both the 40 °C and 45 °C reach flags are true.
- Initial snapshot mean is 39.028228 °C. Rack spread at f = 1 is about 9e-10 °C, so the racks behave identically numerically.
- **Fit residuals** (observed − fit) are +1.436, −1.408, −0.748, −0.023 and +0.743 °C: convex and structured (see I2).

### 1.4 Summit G3

**DERIVED:**
- Affected racks are 192–256 (65 racks, `T_Air` = 308.15 K). The other 192 racks are at 290 K.
- Rack power is identical in both branches.
- Paired final-30-min difference: affected **+0.538986028132 °C** (per-rack range ±1e-9); unaffected **+0.101837403880 °C**.
- Decision **NOT_USABLE** under the frozen ≥ 1.0 °C rule. Correct.
- The G3 control equals the G2 spread branch exactly (max |Δ| = 0).
- The warm-up ledgers of G1, G2 and G3 are byte-identical.

### 1.5 Data hygiene

**DERIVED:**
- `pump_kw` = −92.42 kW appears only at warm-up t = 0, the initialization sample, in all three systems. No experiment-series sample is negative (minimum ≈ 4.08–4.13 kW).
- Every branch root re-reports the idle snapshot power at t = 0. Per-branch power is constant from t > 0 onwards.

---

## 2. Implementation conformance

These checks are FACT unless marked otherwise.

- **FMU backend.** `thermal/fmu_backend.py` is unchanged from the baseline (empty diff). Snapshot and offset semantics are as before: branch communication points are 7200 + `time_s`, and K → °C is −273.15.
- **Per-unit `T_Air` mapping** (`core/state.py:12`, `raps_adapter/coupling.py:37-49`):
  - Element i (1-based) maps to `computeBlock_{i}`, consistent with the power and observation indexing.
  - `T_ext` is unaffected.
  - A length mismatch raises an error.
  - The unit test pins index 33 → `computeBlock_34`.
- **System registry** (`raps_adapter/systems.py`) matches spec §3.1 exactly: FMU SHAs, grids, and `whatif_racks` equal to the last ⌈n/4⌉.
- **Power model** (`raps_adapter/power_model.py`) implements the spec formula exactly (net_util = 0; switch power added once per rack). The spec formula itself omits RAPS rectifier losses; see R1.
- **Probes** (`experiments/probes.py`):
  - Warm-up is forced to exactly 7200 s (`settle_k_per_min = −1`, asserted).
  - `dt` is the system's `POWER_UPDATE_FREQ`, cross-checked against config.
  - There is a `reset()` before every branch, and branch-root equality is asserted.
  - Each branch takes exactly 10800/dt steps.
  - Windows use right endpoints, as preregistered.
  - Sanity covers warm-up samples and globals.
- **Selection** (`experiments/select_fmu.py`) implements spec §4.1 steps 1–5. Two robustness gaps exist (N2), neither triggered.
- **Primary config** (`experiments/configs/primary.yaml`) matches the plan exactly.
- **Import boundaries.**
  - `raps` is imported only in `raps_adapter/`.
  - `fmpy` is imported only in `thermal/fmu_backend.py`.
  - `core/` imports only numpy and the standard library.
  - `probes.py` reads `modelDescription.xml` with zipfile and ElementTree, without fmpy.
  - The direct-FMPy replay helper is test-only.
- **Tests.**
  - The historical Task 1.5 test differs only by an added `xfail(strict=True)` decorator carrying the plan's reason verbatim. Its body and 500–1000 s bound are unchanged.
  - The option-B edit removes exactly the within-process 1e-9 replay assertion. It adds backend-delta = direct-delta at `atol = 1e-6` and records restore jitter of 1.43434446e-4 °C. The direct-vs-backend 1e-6 assertions are untouched.
  - **This is not a passing physical-response test.** The original criterion remains failed and recorded.
  - **DERIVED:** 55 unit and integration tests pass on the Mac.
  - The reported Arch suite result, **62 passed, 1 xfailed**, was not re-run here (FMU tests need Linux). The artifacts it produced were independently re-derived instead.
  - **Coverage gaps (minor, N3):** no test distinguishes the two max-rack definitions, and no unit test covers probe cadence (it is checked by runtime asserts). None of the tests would have caught R1.

## 3. Experimental correctness

**Preregistration (FACT):**

| Experiment(s) | Preregistered in | Results in |
|---|---|---|
| E02 ×3 and X01 | `c6e127a` (02:10:41) | `2d14161` (02:39:52) |
| Summit E01/E03 | `6f88579` (02:40:53) | `2bd9b96` (03:14:49) |

- The probe implementation `41c6585` (02:15) came after the G2 preregistration.
- Diffing each frozen section (Question, Rule, Configuration, Method, Metrics, Limitations) and each `config.yaml` from its preregistration commit to HEAD shows **no changes**. The only changes between preregistration and results are the `Pre-registered:` header SHA line and the Status line.
- Wall times are consistent with the commit times.

**Provenance (FACT):**
- Every `source_sha256` re-hashes correctly against the commit recorded in its manifest; there are zero mismatches.
- `config_sha256`, `uv_lock_sha256` and the FMU SHAs match.
- `dirty = true` appears on lassen E02, summit E02, summit E01 and X01, and is attributed to concurrent artifact writes. That is plausible, and the source-hash check confirms it for `thermorl2/**`.
- UNRESOLVED (low risk): the hashes cannot rule out uncommitted `sim-raps` edits. However, no commit in range touches `sim-raps/` or `models/`.
- Some README wording about dirty flags is inaccurate (N4).

**Raw runs (FACT):** No raw run was overwritten. The Lassen rerun is stored separately under `provenance/rerun_1_data/`.

**Inputs (DERIVED):**
- Controls and interventions use the intended power vectors and ambient values. G2 totals equal n·P(0.6) to machine precision.
- G3 changes only `T_Air` on the 65 affected racks.

**Computation vs physics.** All of the above is recomputation. It shows the summaries faithfully reflect the FMU outputs. It does **not** validate the Summit FMU against real hardware.

## 4. Interpretation

| ID | Finding | Evidence | Consequence | Blocks |
|---|---|---|---|---|
| **I1** | **Summit shows strong facility-level coupling. Rack temperature depends on total facility load, not only on the rack's own power.** At the same own power, racks in the G2 packed branch (60 % facility load) differ substantially from G1 (uniform load): idle racks 45.09 vs 40.04 °C (+5.05); full racks 60.58 vs 66.79 °C (−6.21). Within the packed branch, the own-rack gain is (60.58 − 45.09)/34.08 ≈ **0.45 °C/kW**, against G1's uniform-load slope of 0.805 °C/kW. | DERIVED: `summit/E02…/series.parquet` packed final-window per-rack means grouped by power; G1 levels | This replaces the Lassen-era "decoupled racks" frame for Summit. The facility term is equal across policies, because total IT power is identical by construction, so it cancels in G4 comparisons. **G1's `b` mixes own-rack and facility effects** (see I3). | Neither; carry into C3 interpretation |
| **I2** | **G1's linear fit is a finite-horizon operating proxy, not a steady-state characteristic.** Residuals are structured (convex), up to 1.44 °C, which R² = 0.989 hides. Every level is still rising at 3 h (+0.058 K/min at f = 1). | DERIVED: §1.3 | `a`, `b` and `t_hot_c` are defensible as **prescribed, frozen heuristic parameters** for `thermal_predictive` and the hot-seconds metric. They are not validated predictive quantities. Do not claim predictive accuracy from them. | Neither for Task 5. For later claims: wording only. |
| **I3** | **`thermal_predictive` effectively reduces to a fixed blend of coolant temperature and committed power.** With τ = 4050 s and H = 600 s, the weight is w = 1 − e^(−600/4050) = 0.138. Within one decision, the a- and P_job-terms are common to all candidates and cancel, so ranking ∝ 0.862·T_r + 0.111·P_committed,r (°C, kW): 1 kW ≈ 0.13 °C. | DERIVED from spec §3.3 and the frozen values | The policy is mostly coolant-driven, so it may partly herd like `coolest_rack`. Because `b` mixes facility and own-rack effects (I1), the power weight is roughly 1.8× the own-rack gain. This is a property of a frozen heuristic, not a bug. The G4 decision-disagreement diagnostic will show its effect. | Neither; frozen. Interpret at C3. |
| **I4** | **The empirical τ = 4050 s is a first-crossing statistic measured against an endpoint that has not yet stopped rising.** Because the final value is underestimated, the 63 % crossing happens earlier than a true time constant would imply. τ is therefore likely an underestimate of the slow dynamics. | INFERENCE from §1.3 slopes | The label "protocol-specific, not a first-order time constant" in the E01 README is correct. Do not describe τ as a plant time constant. | Neither |
| **I5** | **Summit operates far hotter in this FMU+RAPS coupling than Lassen did.** Idle is about 39–40 °C and full load about 67 °C at 3 h, still rising. Closed-loop RAPS power will be about 4 % higher still (R1). Under packing, full racks may approach or exceed 70 °C over 6 h. | DERIVED: §1.3; F12 | This is model behaviour and must not be presented as real Summit hardware behaviour. The E02 README already states this correctly. Two consequences: (a) the 70 °C sanity band applied only to the probes; the closed loop has no preregistered sanity rule (N6). (b) **The temperature-only THI outcome metric with T_max = 45 °C will be saturated on Summit**: almost every rack-interval will be below 0.10 for every policy, so it will not discriminate. | Neither for Task 5. Decide reporting before C3 (N6). |
| **I6** | **G2 supports exactly one claim:** on this twin, under a fixed 3 h, 60 %-load protocol, packing the same total power produces a 6.23 °C higher time-averaged max-rack coolant temperature than spreading it. Thermal awareness *versus power balancing* is untested. G3 is negative (0.54 °C < 1.0), so the preregistered what-if is dropped. The 0.10 °C unaffected response is facility-level and small; it must not be presented as strong spatial coupling. | FACT / DERIVED | The demo's "beyond power balancing" question now rests only on G4 (nominal). E13/G5 will not run unless a new, explicitly approved lever is preregistered. The 62 candidate CDU parameters are a list only; using one would be new work, not an automatic follow-on. | Neither |

**On 45 °C:** the C1 and E02 texts treat 45 °C as a fixed comparison reference, not as a validated hardware safety limit. That framing is correct and should be kept.

## 5. Downstream readiness (Task 5 and later)

| ID | Item | Severity | Evidence | When it matters | Smallest correction / decision |
|---|---|---|---|---|---|
| **R1** | Summit RAPS rack power includes rectifier losses, which `rack_power_bounds` omits. RAPS `power_df` idle is 13.822619 kW, against 13.201714 kW used by the probes. Peak is 49.323257 kW against 47.282327 kW. Lassen and Marconi100 are lossless, so their values match exactly. | **Major** | FACT: `sim-raps/raps/power.py:351-361` (`compute_loss(P/4, 17, 0.96)` per rectifier); `config/summit.yaml:33-34`. Executed by the sub-reviewer with a 30 s Summit engine. | **Before Task 5.** The plan's `test_idle_power_reconciles` (\|mean − idle_kw\| < 0.05) will fail. | **Steering decision needed** (§6 D1). Recommended: the Task 5 test reconciles against RAPS itself (Σ rack kW = Σ `power_df["Sum"]`, already required) and against a *loss-inclusive* expected idle. Record both values in SUMMIT `SYSTEM.md`. The G1 fit stays valid, because it relates FMU-input kW to temperature, and `power_df` *is* the FMU input in the closed loop. Accept and document that `job_increment_kw` understates Summit's rack increment by about 4 % between power ticks: it applies equally to all candidates, so the ranking effect is negligible. |
| **R2** | The cost guard is ambiguous: the plan says `total_s × 2 > 45·60`; the spec and the preregistered X01 rule say "measures more than 45 min per 6 h run". Neither defines whether the 7200 s warm-up and initialization are included, or whether the bench must run alone. | **Major** | FACT: plan Task 5 Step 4; spec §4.1 step 6; X01 README rule | **Before Task 5's bench.** Estimate: Summit FMU-only ≈ 105–149 s per simulated hour (concurrency-dependent) → 6 h ≈ 630–900 s, or ≈ 840–1,200 s with warm-up, plus about 50 s initialization. Under the plan's ×2 reading the margin to 2,700 s is only about 10–35 %. Under the spec reading the margin is large. | **Steering decision needed** (§6 D2). Do not let the executor choose. |
| R3 | Stale `power_df` / FMU step count / 10 s cadence | Info | Sub-reviewer, executed: a 30 s Summit run gives power ticks at 0, 10 and 20 s. The plan's `t % Δ == 0` definition and `horizon/Δ` invariant are correct. ⌈25/10⌉·10 = 30 and 12 ticks per 2 min for Summit. | Task 5 | None. Keep `id()`-distinctness checks robust by holding references (N5). |
| R4 | Horizon rule | Info | 12 h requires an idle bench ≤ 75 s, which Summit cannot meet. | Task 5 | None. The horizon will be 6 h. G4's evaluation window [1 h, 6 h] is about 5τ_empirical, and states remain transient. |
| R5 | Matrix runtime on Summit | Info | Per run ≈ 2 h warm-up + 6 h at 105–149 s/h FMU, plus RAPS with 4,626 nodes. FMU cost rises with concurrency (G1 105 vs G2/G3 146–149 s/h). | C3/C4 scheduling | Expect about 1–3 h per 15-run matrix with 4–6 workers. Not a blocker. |
| R6 | Exact-node allocation, RAPS cooling/output, time limits | Info | Unchanged RAPS seams (earlier review). `output: "none"`, `cooling: false`, and `time_limit ≥ expected_run_time` are already in the plan. | Tasks 5–9 | None. |

## 6. Decisions requested before Task 5

**D1 — Summit rack-power reconciliation (R1).** I recommend these clarifications to the Task 5 tests:
- (a) Compare the idle mean against RAPS's own loss-inclusive idle. Compute it through RAPS's `PowerManager` on an idle state, or apply the loss formula explicitly as an expected value, instead of using `rack_power_bounds`.
- (b) Keep the exact Σ-reconciliation against `power_df["Sum"]`.
- (c) Document in `summit/SYSTEM.md` that probe vectors used loss-exclusive kW. For the same node utilisation, closed-loop FMU inputs will be about 4.3–4.7 % higher.
- (d) Leave `job_increment_kw` frozen and document its about 4 % between-tick understatement on Summit.

Changing the G1 or G2 protocols is not recommended, and no rerun is needed.

**D2 — Cost-guard formula (R2).** Bipin must pick one reading explicitly and record it in the plan's Task 5 and in the X01 README:
1. **Spec-literal (recommended).** Switch if one isolated, idle bench process (FMU instantiation + 7200 s warm-up + 6 h RAPS+FMU) takes more than 45 min of wall time. Report the ×2 job-load projection for information only.

   *Rationale:* the spec is authoritative, and the preregistered X01 rule quotes the spec. The ×2 factor in the plan was borrowed from the horizon rule in §3.4.
2. **Plan-literal.** Switch if 2 × (that same measured quantity) exceeds 45 min.

Either way, the bench must run alone on the machine, warm-up must be included, and the measured numbers must be recorded.

## 7. Non-blocking cleanups

These can be done alongside Task 5 or later. They are not prerequisites.

| ID | Item | Correction |
|---|---|---|
| N1 | `coupling.py:45-49` silently skips per-unit `T_Air` keys missing from `temperature_keys`. All three configs are complete today. | Raise on a missing key. |
| N2 | `select_fmu.py:47` sets `tie_break_applied = True` whenever the pool has more than one member, even when the winner is unchanged. A crashed system (no `summary.json`) aborts X01 instead of being marked ineligible. WEAK reframing is not recorded. None of these was triggered. | Use `changed_winner`; handle missing summaries; record WEAK. |
| N3 | The max-rack unit-test fixture cannot distinguish the two definitions. There is no length-mismatch test. | Use an asymmetric fixture; add a mismatch test. |
| N4 | The Marconi100 E02 and Summit E03 READMEs say "dirty=false … from concurrent outputs". X01's README does not explain its `dirty=true`. | Fix the wording. These sections are post-result. |
| N5 | Task 5 test text: `SystemSpec` has no rack-count field, so the count must be derived. `id()` reuse can defeat stale-object checks. | Derive the count from config; hold references. |
| N6 | Closed-loop sanity and THI reporting on Summit (I5). | Before C3, decide how to report: (i) any closed-loop coolant above the probes' 70 °C band, and (ii) the THI_T fraction, which is expected to saturate. Keep both frozen metrics, report them transparently, and add no new thresholds after results. |
| N7 | `pump_kw` initialization artifact (−92.4 kW at warm-up t = 0). | Make sure Task 9's intervals start after warm-up and that pump energy excludes initialization samples. Verify at C2. |

## 8. Recommendation

1. **Merge C1** into `feat/thermorl2-phase0-env` with a merge commit, preserving every preregistration and execution SHA.
2. **Before Task 5:** Bipin records D1 and D2. The cleanest place is a dated addendum to the plan, plus the X01 README's post-result notes for D2.
3. **Then authorise Task 5** as written, with the D1/D2 clarifications. This review does not authorise Task 5.
4. **Carry into C2/C3 reporting:** I1–I6. In particular, the comparison of thermal-aware placement against power balancing on Summit is untested, and the G1 parameters are prescribed heuristics, not validated predictors.
5. **No additional characterisation is required.** No rerun is needed for C1. No history, predictor-selection, placement or RL experiment is a prerequisite.
