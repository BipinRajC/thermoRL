# C3 Prelaunch Review — Tasks 10–12 Preparation, E11 Workloads, Determinism Scope

**Reviewer:** Claude (Opus), independent technical and scientific reviewer. **Date:** 2026-10-30.

**Reviewed SHA:** `552e9b866d6e95020fec6e46e4f590ef1e686dd8`. This is `feat/parasparam-demo` as pulled by Bipin; it matches the expected tip, and there are no later commits.

**Scope**
- Baseline: my C2 review, `ee32212`.
- Commits reviewed: `50ffa30`, `3616c78`, `c0cced6`, `552e9b8` (20 files, +1335/−10).
- Coverage: every changed implementation, test and config file; the three workload parquets and their sidecars; the E10 raw ledgers, used to recompute values independently.
- I also used a parallel read-only code audit.
- Nothing was executed against FMUs or RAPS simulations, and run.py / run_matrix.py were not run against real experiment directories.

**Status:** no E11 simulation has started, no E11 result exists, and C3 has not been reached.

**Labels:** FACT = verified directly · DERIVED = calculated independently · INFERENCE = supported interpretation · UNRESOLVED = not established.

## 0. Verdict: **READY AFTER SPECIFIC FIXES + BIPIN'S SCOPE DECISION**

The Task 10 metrics, the three workloads, and the B1/B2 safeguards are correct. I verified them independently.

E11 should not be preregistered or launched until four things happen:
- **R1** — the report entry point cannot run against the preregistered config (major).
- **R2** — invariant 3 is a single global flag that cannot express the evidence scope honestly (major).
- **R3/R4** — two cheap launch-safety fixes to the failure and retry handling (major).
- **Bipin decides the determinism-evidence scope (§8).**

None of these touches the frozen protocol.

## 1. Independently verified numbers and tests

### 1.1 Task 10 metrics, recomputed on E10 (DERIVED)

I ran Sol's `core/metrics.py` on the committed E10 ledgers in a fresh scratch venv (numpy 2.5.4, pandas 3.1.0). I then compared the output against my own independent recomputation and against my C2 numbers.

**Metrics carried over from C2 (packing / power_balance):**

| Metric | packing | power_balance |
|---|---:|---:|
| `maxrack_mean_c` | 53.445129 | 54.115585 |
| `maxrack_p99_c` | 55.579580 | 55.849403 |
| `mean_rack_c` | 43.738314 | 43.665185 |
| `thi_t_below_0p1_frac` | 0.445233 | 0.287905 |

`raw_max_c` and the E10 invariants also match C2 exactly. `invariants()` returns IT-kW identical (1.82e-12), starts identical, and FMU steps correct.

**S1 metrics.** Sol's values equal my independent per-tick computation to the printed precision:

| Metric | packing | power_balance |
|---|---:|---:|
| `rack_t_std_mean_c` (ddof=0) | 3.276511 | 2.303864 |
| `top_decile_mean_c` (26 racks) | 49.270481 | 48.900406 |
| `rack_kw_std_mean` | 10.075766 | 7.562692 |

**Other metrics:**
- Hot rack-seconds = 0 (t_hot = 63.30 °C was not reached).
- IT energy is identical in both runs (11394.99 kWh). Pump energy is 2130.52 / 2130.36 kWh, with warm-up excluded.
- Waits: mean 0.51 s and p95 0.95 s, identical across policies by construction. One job is censored.

**Self-reproduction.** power_balance = **0.994716** (8 of 1514 decisions differ, all from 6-decimal rounding ties). packing = **1.0**.

**Counterfactual disagreement** (both scorers re-applied to the same logged context; descriptive only, no inference):
- power_balance vs thermal_predictive, on the power_balance contexts: **0.788**.
- packing vs power_balance: **0.9815** on the power_balance contexts and **0.8864** on the packing contexts.

**Max-rack attribution** reproduces the C2 finding: rack 55 (packing) and rack 181 (power_balance) for 100 % of window ticks, with job 184 resident at every tick.

**Robustness (code audit, DERIVED):**
- Shuffling the interval rows changes no metric (differences ≤ 4.5e-13).
- Argmax ties resolve to the lower rack index.
- A node completed and reused within the same tick is handled correctly.

### 1.2 Tests

| Source | Result |
|---|---|
| Reported on Arch | 97 unit + 27 integration = 124 passed |
| Re-run in a scratch venv built from the project lock (code audit) | **124 passed** from `thermorl-v2`, and also from the repo root; repository status unchanged |

No FMU or vertical-slice test was run on the Mac.

## 2. Findings (ranked)

### Critical
None.

### Major — must be fixed before the E11 preregistration commit and launch

| ID | Finding | Evidence | Consequence | Smallest correction | Blocks launch |
|---|---|---|---|---|---|
| **R1** | `report.main` reads `cfg['t_hot_c']`, `cfg['grid']` and `cfg['determinism_evidence']`. None of these exists in `g4_synthetic.yaml` or `primary.yaml`. Separately, `validate_expected` requires each run's executed config to equal `E11/config.yaml` exactly. | FACT `report.py:220-227`, `report.py:117-124`; grep of configs finds none of the keys; `main()` has no test | Followed literally, the plan fails: the report either raises KeyError or marks every run INVALID (invariant 6 false). Embedding the evidence in the run config is not possible either, because evidence produced *after* launch (§8 Option C) cannot be part of a preregistered run-config hash. | Read `t_hot_c` from the G1 summary that the config already pins (`thermal_predictive.from`, `g1_sha256`). Read `grid` from `get_system(system).grid`. Pass the determinism evidence as a **separate, SHA-recorded evidence file outside the run config**. Make `E11/config.yaml` a byte-identical copy of the launch config. Add a fixture test for `report.main()`. | **Yes** |
| **R2** | Invariant 3 is a single global boolean taken from one evidence dict and applied to every seed. | FACT `report.py:153-162` | With inherited evidence, E11 seeds 1–3 would be shown as "determinism verified" when nothing was re-measured. That mislabels the evidence. | Make it a per-seed record holding `status` ∈ {`verified_E11`, `inherited_not_remeasured`, `failed`} plus a list of evidence items, each with `kind`, `scope`, `result` and `ref`. The G4 gate accepts exactly the scope Bipin approved (§8) and treats any measured failure as INVALID. | **Yes** (needed to record the scope decision honestly) |
| **R3** | Pre-flight checks (run directory already exists; a prior attempt exists without `--retry-failed`) run only when each job is taken from the queue. When one fails mid-matrix, the error handler terminates and archives healthy in-flight runs, and each killed run uses up its single retry. | FACT `run_matrix.py:111-119,162-173`; DERIVED (scratch reproduction: a healthy `power_balance` was killed, exit −15) | A resume after any failure can destroy valid runs and their retry budget. | Validate every job (directory absent, retry eligibility) before launching any process. On a non-scientific failure, stop launching new jobs and let in-flight runs finish. | **Yes** (cheap; B3 intent) |
| **R4** | `--retry-failed` reruns any once-failed run whatever the cause: an FMU error, non-finite coolant, a step/clock assertion, a validation failure, or collateral termination. `failure_archived` and `matrix_stopped` record no reason. "Scientific stops take precedence" appears only in a docstring. | FACT `run_matrix.py:94-100,116-119,174,187` | The approved B3 condition is not enforced and the audit trail is incomplete. | Record `failure_kind` and `message` for every archive and stop. Refuse a retry when the failure kind is a scientific stop (FMU error, non-finite coolant, step/clock or invariant/validation failure) unless an override reviewed by Bipin is recorded. State this rule in the E11 README. | **Yes** (cheap; approved B3 condition) |

### Minor — should fix before launch; none blocks alone

| ID | Finding | Evidence | Correction |
|---|---|---|---|
| R5 | If every run already exists, `main` exits 0 before the seed cross-policy checks and without writing an inventory. | FACT `run_matrix.py:216-222` | Run the seed checks and write the inventory on every exit path. (The report still catches failures.) |
| R6 | SIGTERM/SIGHUP are not handled: children can be orphaned and partial directories are not recorded. Ctrl-C works. | FACT `run_matrix.py:162` | Install a signal handler that raises KeyboardInterrupt; start children in their own process group. |
| R7 | `provenance/failed_*/` is not gitignored, so a failed run over 25 MB could be committed. Console logs are not in the inventory. | FACT `.gitignore`; `git check-ignore` | Ignore `failed_*/`. Add the logs and `matrix_events.jsonl` to the inventory. |
| R8 | The parent process uses cwd-relative paths. | FACT `run_matrix.py:193,203-205` | Document that it runs from `thermorl-v2`, or anchor paths to PROJECT. |
| R9 | `--workers` defaults to `min(6, cpu−2)`, not the approved 3. | FACT `run_matrix.py:186` | Use `--workers 3` explicitly in the preregistered command. |
| R10 | `g4_decision` does not itself enforce completeness of all 3 seeds × 5 policies; only `build_report` does. | FACT `report.py:34-46` | Assert completeness inside `g4_decision`. |
| R11 | The `build_report(g4=True)` path is untested in the repo, and assertion messages are empty. | FACT tests | Add a test and assertion messages. |
| R12 | Safety checks use bare `assert`, so `python -O` disables them. | FACT `runner.py:95-106`, `report.py`, `run_matrix.py` | Refuse to run when `sys.flags.optimize` is set, or raise explicitly. |
| R13 | A missing `job_events.jsonl` becomes empty residency instead of "missing". The file is not hashed in the manifest. | FACT `metrics.py:52`; `runner.py:246-268` | Require the file for G4 and record its SHA. |
| R14 | `fmu_s_scope` slightly overstates what is timed: the FMU2Slave constructor and unzip-directory removal are untimed. | FACT `fmu_backend.py` | Adjust the wording. |
| R15 | Two undocumented conventions: p99 uses linear interpolation, and `jobs_censored` includes jobs submitted after 21599 s. | FACT `metrics.py:94,101` | Document both. |
| R16 | `by_seed` pins parquet SHAs but not sidecar SHAs. | FACT config | Optional `meta_sha256`. |

## 3. Task 10–11 compliance and missing coverage

**Task 10 (`core/metrics.py`): compliant (FACT/DERIVED).**
- Strict window: `eval_start < t_s ≤ horizon`.
- Time-mean of per-tick maxima; p99 of per-tick maxima (linear interpolation); spread = mean over ticks of (max − min).
- THI uses per-rack `t_idle_c`, indexed by rack id regardless of row order.
- S1: population std (ddof=0) per tick, then time-mean. The hottest ⌈0.1·257⌉ = 26 racks are selected per tick.
- IT energy is the held-input sum kW·Δ; pump energy is a right-endpoint sum; warm-up is excluded.
- Waits = integer start − continuous submit, asserted ≥ 0. Censored jobs are counted separately and never given a zero wait.
- Latency comes only from the timing ledger: if the ledger is missing, so is the metric; an exact join is asserted, nanoseconds are integers, and `null` is never read as zero.
- Disagreement re-applies both scorers to the same rounded context, with globally distinct reconstructed node IDs. Self-reproduction is reported separately.
- Attribution: argmax ties go to the lower index. Residency is taken at the driving RAPS tick (t_s − Δ) with completions applied before starts, and node reuse is correct.

**Correct is not the same as discriminating.** On E10:
- hot rack-seconds = 0;
- waits are identical by construction;
- `maxrack_mean_c` is dominated by a single resident job (C2 M2).

These limitations must be stated; they are not defects.

**Task 11 (`plots.py`, `report.py`): compliant, apart from R1, R2, R10 and R11.**
- Axes use the actual horizon. Heatmaps share a colour scale.
- G4 requires all 3 seeds × 5 policies (through `build_report`), all invariant flags `is True`, and gap ≥ 0.5 °C in every seed on `maxrack_mean_c` only. Secondary metrics are excluded from the decision.
- Executed configs are checked against the expected preregistered config: hash and equality after per-seed resolution, system, FMU SHA, workload SHA and path, warm-up, and horizon.
- An invariant failure writes "INVALID" and raises.
- Outputs are created exclusively and never overwrite.
- E10 is labelled "ledger analysis; no G4 decision".

**Missing or superficial coverage:** `report.main` (R1); the G4 path (R11); the positive skip path; the seed cross-policy check; interruption handling; R3. The argmax-tie, same-tick-reuse and row-order cases are verified in scratch but not unit-tested.

## 4. B1 / B2 / B3 and provenance

- **B1 — met (FACT).** `config_for_seed` deep-copies the shared config and does not mutate it (tested). The path and SHA reach both the execution and the manifest (relative path; tested).
- **B2 — met (FACT).** The sidecar `horizon_s` is asserted equal to the episode horizon (`runner.py:103-104`) before the run directory or FMU exists (tested with a forbidden backend). `--horizon-h` cannot bypass it, except via `python -O` (R12).
- **B3 — partially met.**
  - Met: every run file is inventoried as `{bytes, sha256}`; `runs/` is ignored but locatable; failed runs are archived to unique `failed_<utc>` directories, never overwritten; at most two attempts, both recorded; a run that fails post-run validation is archived; Ctrl-C archives runs; skipping requires a matching config hash and intact ledger SHAs.
  - **Gaps:** R3, R4 (major); R5, R6, R7 (minor).
- **Other launch corrections — met.**
  - `LATENCY_SPAN` now names the assertions, `running.append` and `queue.remove`, and the span text matches the code.
  - `fmu_s_scope` is present (wording: R14).
  - Workload paths resolve from the project root in both runner and metrics.
  - Import boundaries are intact.
  - `git diff ee32212..552e9b8` is empty for: `fmu_backend.py`, `primary.yaml`, G1 results, `tests/fmu`, scorers, placement, the workload generator, `sim-raps/`, `models/`, E10 artifacts.
- **Sol's four internal-review fixes (UNRESOLVED identities; plausible mapping DERIVED from the tests added in `c0cced6`), all present and tested:**
  1. Executed config checked against the preregistered config.
  2. Archiving of runs that fail post-run validation.
  3. No automatic retry; capped reviewed retry; immutable evidence.
  4. All-matching skip without overwriting.

## 5. Workload audit (FACT / DERIVED, committed bytes inspected directly)

| Seed | Offered jobs | Parquet SHA-256 (recomputed) | Offered utilisation in (3600, 21600] | Full-power jobs of ≥ 16 nodes |
|---|---:|---|---:|---:|
| 1 | 4589 | `c9bd815f…de967c27` ✓ | 0.568 | 20 of 615 |
| 2 | 4688 | `d2a64253…88100b91` ✓ | 0.575 | 10 of 603 |
| 3 | 4660 | `7e06a125…696692aa0d` ✓ | 0.576 | 18 of 626 |

**Sidecars (all three):**
- horizon 21600 s, ρ 0.6, Summit, 4626 nodes, 6 GPUs per node;
- the frozen spec parameters;
- generator source SHA `0e63550e…3335` — identical to the E10 workload, so the generator is unchanged;
- representation text, RNG draw order, 1e6 Monte Carlo samples with the expectation and arrival rate;
- locked numpy 2.5.3 / pandas 3.0.6 / pyarrow 25.0.1 — identical to E10.

**Data checks:**
- `expected_run_time` is int64 in [300, 14400], and `time_limit = ⌈1.5R⌉` for every row.
- Submit times are continuous (all non-integer), sorted, and inside the horizon.
- IDs are 0..n−1.
- `by_seed` references each parquet by SHA.

**Prefix property (DERIVED, important for §8).** The E10 workload (1515 jobs, 2 h) is **identical to the first 1515 rows** of the E11 seed-1 workload. The next arrival is at 7201.34 s.

Between E10's execution commit `0c32cf5` and `552e9b8`, the decision path is unchanged. The runner diff only adds per-seed config resolution, path anchoring, the horizon assertion and manifest text, and the scheduler diff is the latency-span text only. So **E11 seed-1 packing and power_balance must reproduce E10's decisions for t_s < 7200 and its interval values for t_s ≤ 7200, byte-for-byte.** This is a cost-free cross-execution determinism check.

No workload tuning was performed or is recommended.

## 6. Carried scientific limitations (unchanged; must appear in the E11 preregistration and C3)

- **M2.** The primary max-rack metric can be dominated by a rare, long-running, full-power large job that saturates a rack under the frozen spanning rule. Each seed has 10–20 such jobs; in E10, one job (184) set the argmax for the whole window under both policies.
- **M3.** Identical own-rack and total power gave different coolant trajectories under different placements of the other load. The mechanism is unresolved.
- **S1.** The S1 metrics are descriptive only and must not replace an unfavourable primary result.
- **S2, verbatim:** "published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies."
- **Model and protocol limits:**
  - capped, evolving warm-up;
  - G1 parameters are frozen heuristics, not validated predictors;
  - 45 °C is a reference value, not a safety limit;
  - three seeds;
  - hot rack-seconds are expected to be about 0;
  - waits are identical across policies by construction;
  - no PUE, carbon, lifetime or RL claims;
  - coolant above 70 °C is reported, not an automatic stop.
- **E10 descriptive values point in different directions.** power_balance has a lower rack-temperature std and a lower top-decile mean than packing, but a higher max-rack. **No inference is drawn**, and none should be.

## 7. Runtime (INFERENCE)

| Plan | Waves at 3 workers | Estimated wall time |
|---|---:|---|
| 15 runs | 5 | ~1.5–2.5 h (C2 estimate; costs are policy-dependent and three policies are untimed) |
| 16 runs (Option C, §8) | 6 | adds ~15–20 min |

The optional real-path smoke (§10, step 3) adds about 10 min.

## 8. Determinism evidence scope — recommendation

**What the authorisation covers.**
- **Task 9/E10** owned reproducibility validation, through the same-config rerun.
- **Task 12** owns policy evaluation. The approved addendum (2026-10-30) explicitly says "execute the 15-run, three-worker frozen matrix".
- **Plan Task 17 Step 4** already schedules "re-run one E11 run … confirm its `decisions.jsonl` is byte-identical".

So a single E11 rerun is already planned work, not a new experiment.

**Assessment of the options:**
- **A — exactly 15 runs, inherited E10 evidence.** Within the existing authorisation. Honest if labelled correctly. Leaves the 6 h horizon and the temperature-reading policies with no repeated execution.
- **B — 3 packing reruns.** Low marginal value. Packing never reads FMU outputs, so its decisions cannot reveal FMU-output nondeterminism feeding back into placement, and the prefix check below already covers packing at zero cost. **Not recommended.**
- **C — recommended:**
  - **Exactly 15 matrix runs**, plus:
  - **(i) A zero-cost prefix check**, enabled by §5. E11 seed-1 `packing` and `power_balance` must reproduce E10 byte-for-byte: decisions for t_s < 7200 (canonical line bytes, same order) and interval values for t_s ≤ 7200. A mismatch means unexpected nondeterminism or horizon dependence: stop and report before any G4 interpretation.
  - **(ii) One E11 rerun of `thermal_predictive`, seed 1, full 6 h**, stored under `provenance/rerun_1_thermal_predictive_seed1/`. This brings Task 17 Step 4 forward. thermal_predictive is the policy under test, and its decisions consume FMU temperatures, so this is the single most informative repeated execution. Cost: one run, about 15–20 min.
  - **Option A (15 runs + prefix check, no rerun)** is the minimal acceptable alternative.

**Bipin decides between C and A.**

**Exact wording.**

*E11 preregistration, Option C:*
> "Invariant 3 evidence scope (fixed before launch): (a) inherited — E10 packing seed 1, 2 h, same-config fresh-process rerun, byte-identical decisions and identical intervals (`experiments/summit/E10_c2_vertical_slice/provenance/rerun_1.json`); (b) E11 prefix reproduction — E11 seed-1 packing and power_balance must reproduce E10's canonical decision lines for t_s < 7200 byte-for-byte and interval values for t_s ≤ 7200 exactly (E10 workload is the exact prefix of the E11 seed-1 workload; decision path unchanged since 0c32cf5); (c) E11 direct rerun — thermal_predictive seed 1, full 6 h, fresh process, byte-identical decisions and identical interval values required. No other E11 policy/seed combination is independently repeated; for those, determinism is inherited, not re-measured. Any failure of (b) or (c) invalidates the G4 conclusion pending review."

*E11 preregistration, Option A:* use (a) and (b) only, and replace (c) with:
> "No full 6 h E11 configuration is independently repeated."

*`invariants.json`, per seed* (R2 schema):
```json
"3_determinism": {
  "status": "verified_E11 | inherited_not_remeasured | failed",
  "evidence": [
    {"kind": "inherited_E10", "scope": "packing seed1 2h same-config rerun", "result": true, "ref": ".../E10.../provenance/rerun_1.json"},
    {"kind": "E11_prefix_vs_E10", "scope": "seed1 packing+power_balance; decisions t_s<7200 bytes; intervals t_s<=7200 values", "result": true, "ref": "..."},
    {"kind": "E11_rerun", "scope": "thermal_predictive seed1 6h", "result": true, "ref": "..."}
  ]
}
```

| Seed | Option C status | Evidence items |
|---|---|---|
| 1 | `verified_E11` | all three |
| 2 | `inherited_not_remeasured` | `inherited_E10` |
| 3 | `inherited_not_remeasured` | `inherited_E10` |

*C3:*
> "Determinism: directly re-measured in E11 only for thermal_predictive seed 1 (6 h) [Option C] and for seed-1 packing/power_balance over the first 2 h prefix against E10; all other E11 policy/seed configurations rely on inherited E10 evidence and were not independently repeated."

## 9. E11 preregistration readiness

**Not ready yet.** The preregistration commit must contain all of the following:
- **Fixes:** R1, R2, R3, R4.
- **Frozen protocol:** 5 policies × seeds 1–3; ρ 0.6; 6 h; nominal; 7200 s capped warm-up; window (3600, 21600]; the primary metric; the 0.5 °C every-seed rule; the "no material value on the homogeneous twin" outcome text.
- **Analysis content:** S1 as descriptive only, S2 verbatim, M2/M3, the §6 limitations, the determinism scope (§8 wording), the six invariants per seed, the `t_hot_c` source (G1 summary), censoring, and the retry/failure rule (R4).
- **Inputs:** the workload SHAs.
- **Commands:**
  - run from `thermorl-v2`;
  - `run_matrix --config <launch config> --workers 3`;
  - `E11/config.yaml` byte-identical to the launch config;
  - the report command and its evidence-file argument.

## 10. Bounded next assignment for Sol

1. Fix R1–R4. Optionally R5–R16 (recommended: R7, R9, R10, R11, R12, R13). Write the tests; commit.
2. Write and commit the E11 preregistration (§9), using the scope Bipin chose.
3. **Optional, recommended:** run the plan's Task 12 Step 1 real-path smoke — `smoke_2h`, packing + power_balance, seed 1, 3 workers — into a non-evidence scratch directory outside `experiments/`, not committed. Its decisions must equal E10 byte-for-byte; record that as an engineering check only.
4. Launch E11 from `thermorl-v2` with `--workers 3`: 15 runs, plus the single thermal_predictive seed-1 rerun if Option C. Record first-wave timings. Generate the report with the separate evidence file.
5. Write C3. Commit, push, **stop**.

**Frozen:** policies, spanning rule, thresholds, G1 parameters, `primary.yaml`, workload methodology and the three workloads, FMU selection, primary metric, success rule, ρ, seeds, horizon, warm-up.

**Not authorised:** Tasks 13–16, Alibaba, what-if, scheduler redesign, new characterisation, predictor selection, RL, or any additional run beyond the chosen scope.
