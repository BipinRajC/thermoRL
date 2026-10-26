# C2 Preflight Review: Tasks 5–7, Isolated Bench, and Decisions on R3/R4

- **Reviewer:** Claude (Opus), independent technical and scientific reviewer
- **Date:** 2026-10-27
- **Reviewed SHA:** `037b1dd6d67003141a1ae1930edc57e2e5eb9d1a` (`origin/feat/parasparam-demo` at fetch; equals the expected tip; no further commits)
- **Baseline:** `4f13f44` (merge of PR #1, C1)
- **Scope:** all six commits `425b51b`, `7695c34`, `cf1d522`, `2a2616f`, `baf24fb`, `037b1dd` — 25 files, +1571/−6. Every changed source and test file was read, and the unapplied Task 8 patch was read in full.

**Labels:**
- **FACT:** verified directly.
- **DERIVED:** calculated independently.
- **INFERENCE:** a supported interpretation.
- **UNRESOLVED:** not established.

## 0. Verdict

| Item | Decision |
|---|---|
| Tasks 5–7 implementation | **Accepted.** No blocker. Minor findings in §4. |
| D1 compliance | **Compliant.** |
| D2 isolated bench | **Verified PASS** (912.54 s ≤ 2700 s). Summit retained; horizon 6 h. |
| **R3** latency vs byte-identical decisions | **APPROVE WITH CONDITIONS** (§2) |
| **R4** integer-second runtime representation | **APPROVE WITH CONDITIONS** (§3) |
| Remaining blockers | **None**, once the conditions are applied inside Task 8 and Task 9 |

The approved meanings are recorded verbatim in a dated addendum to the plan: "Approved C2 preflight representation decisions (2026-10-27)". No earlier record or frozen section was altered.

## 1. Independently verified evidence

### 1.1 D1 — Summit rack-power reconciliation

- **FACT:** `raps_rack_kw` (`power_model.py:28-34`) builds `PowerManager(**cfg)`, fills `power_state` through RAPS's own `power_func`, and calls `compute_rack_power()`. The loss formula is not hand-coded.
- **DERIVED (scratch RAPS, no FMU):**

  | System | Idle kW/rack | Peak kW/rack |
  |---|---:|---:|
  | Summit | 13.822619047619 | 49.323256802721 |
  | Lassen | 10.85768 | 34.42868 |
  | Marconi100 | 12.3652 | 38.5552 |

  Lassen and Marconi100 equal their lossless `rack_power_bounds`.
- **FACT:** Tolerances are unchanged: idle within 0.05 kW, Σ reconciliation to 1e-6 kW.
- **FACT:** Nothing frozen changed. `git diff 4f13f44..HEAD` is empty for `thermal/`, `experiments/configs/` (`primary.yaml`), `tests/fmu/` (historical XFAIL body), all `experiments/*/E0*` (G1 summary), `probes.py`, `select_fmu.py`, `sim-raps/`, `models/` and `docs/prompt.md`. No C1 experiment was re-run.
- **DERIVED:** The Summit per-rack full-load increment is 34.08 kW via `job_increment_kw` and 35.50 kW in RAPS. This is the documented ~4 % understatement.
- **FACT:** D1/D2 are recorded verbatim in plan commit `425b51b`, with the D2 post-result note in the X01 README.

### 1.2 D2 — isolated bench (`experiments/summit/_bench/task5_bench_20261026T224138_640592Z.json`)

**Raw values (all FACT):**

| Field | Value |
|---|---|
| `total_s` | 912.5393135249997 |
| `raps_s` | 3.9649237830744823 |
| `fmu_s` | 902.9637261998796 |
| `warmup_instantiation_s` | 323.91025115999946 |
| `instantiation_s` | 7.788 |
| `warmup_wall_s` | 316.122 |
| `episode_wall_s` | 586.387 |
| `power_ticks` / `fmu_steps` | 2160 / 2160 |
| `switch_required` | false |
| `horizon_h` | 6 |

**DERIVED:**
- The UTC start (22:41:38.64) and finish (22:56:51.18) differ by exactly 912.54 s.
- The components sum to 910.3 s, which leaves about 2 s for interpreter start-up.
- **Guard: 912.54 ≤ 2700 → PASS.**
- Horizon: 4 × total > 300, so 6 h.
- The doubled quantities 1825.08 and 1177.26 are arithmetically correct and are information only.

**FACT, timing boundary:** `bench.py:126-136` starts `perf_counter` in a parent before `Popen` of a single worker and stops it after `wait()`. `total_s` therefore covers imports, hashing, engine build, FMU instantiation, the forced 7200 s warm-up (asserted), 6 h at 10 s, `close` and exit.

**FACT, provenance:**
- The executed commit is `7695c34`.
- All 22 recorded `source_sha256` values match `git show 7695c34:<path>`.
- `bench.py` is unchanged after `7695c34`.
- The only dirty path at start was the pre-existing ` D docs/prompt.md`.
- `environment.txt` matches the JSON.

**UNRESOLVED (minor):** Isolation from concurrent simulations is asserted in the report but not captured as an artifact (no saved process scan). Commit timings are consistent with the claim.

**Caveat (FACT):** `fmu_steps` is copied from `power_ticks`, so it is not an independent count. This does not change the bench result. Task 9 must count FMU steps independently (condition T9-ii).

### 1.3 Tasks 5–7 mechanics

**Engine factory (FACT, `engine_factory.py`):**
- Config: `cooling: False`, `output: "none"`, `noui: True`, `scheduler: "default"`, `policy: "fcfs"`, `time_delta = POWER_UPDATE_FREQ` s.
- `time_unit` is inferred as 1 s and pinned by the Δ assertion.
- `timestep_start == 0` is asserted.
- `engine.jobs` and `total_initial_jobs` are set; the generator is not primed.
- `is_power_tick` uses `t % Δ == 0`.
- Flattening is CDU-major. **DERIVED:** rack 0 and the last rack light the matching `power_df` indices on all three systems.

**Timing (FACT, tests):**
- 12 power ticks per 2 min on Summit.
- `power_df` is stale but non-None between ticks; there are exactly 12 distinct objects, with references held.
- A job arriving at t = 25 is scheduled at 25 and first appears hot at t = 30.
- An overrun raises.
- **DERIVED:** RAPS order within one second is completions → schedule → power tick → yield. `power_df(t)` therefore includes jobs placed at t, and the post-yield `on_power_tick` reset does not double count.

**Placement (FACT, `placement.py`):**
- Racks are ordered by `lexsort((index, −score))`, so ties go to the lower index.
- A single rack is used when it can hold the job; otherwise placement spans racks in score order.
- Nodes within a rack are the lowest ids, sorted, so set iteration order cannot leak in.
- Insufficient, duplicate or zero requests raise.

**Scorers (FACT, `scorers.py`):** The five formulas match spec §3.3. `ThermalPredictive` uses w = 1 − e^(−H/τ). Note that no code yet loads the frozen G1 parameters (condition T9-i).

**Scheduler (FACT, `scheduler.py`):**
- FCFS by `(submit_time, id)`, with head-of-line `break` and no backfill.
- `check_available_nodes` is never called.
- Placement uses REPLAY exact nodes, with distinct-and-free assertions.
- The per-rack committed increment is applied after every placement.
- The context (free counts, committed kW, `t_c`, scores) is snapshotted before mutation.
- Exactly the 14 schema keys are written, with 6-decimal rounding.
- Scalar-or-mean trace interpretation is used.
- `policy` and `bfpolicy` are plain attributes and survive priming.
- Scheduling fails fast if no `ThermalView` has been published.

**DERIVED (F11 in the code audit):** RAPS's rectifier loss is affine, (P + 17)/0.96, and Summit has no missing racks. Total IT kW is therefore independent of placement, apart from floating-point summation order. Invariant 1 is achievable on Summit despite D1.

**Import boundaries (FACT):** `raps` is imported only in `raps_adapter/{engine_factory, power_model, scheduler}.py`, `fmpy` only in `thermal/fmu_backend.py`, and `core/` imports neither (nor `torch`).

**Tests (DERIVED, re-run in a Mac scratch venv; no FMU):** **66 unit + 22 integration = 88 passed.** These match Sol's counts. The 7 FMU tests passing plus 1 strict historical XFAIL on Arch were not re-run here, because FMUs cannot run on macOS.

**Scope (FACT):**
- Only the authorised cleanups N1 (missing per-unit `T_Air` key raises), N3 (asymmetric max-rack fixture and length-mismatch test) and N5 are present.
- The N3 change replaces the old weak assertion rather than adding a new test. That is acceptable.
- Pin-only test `test_fractional_runtime_crossing_power_tick_raises` was added in `037b1dd`.
- No unrelated changes were found.

**Fixtures vs E10 (INFERENCE):** The scheduler and timing tests are short mechanics fixtures. They do **not** validate E10 invariants 1–6 at scale, which remain **NOT RUN**.

## 2. R3 — latency logging versus exact reproducibility: **APPROVE WITH CONDITIONS**

**Problem (FACT):** `scheduler.py:81` writes measured `perf_counter_ns` latency into the canonical decision row. Spec §7.3 and plan Task 9 require byte-identical `decisions.jsonl` on rerun. Both requirements cannot hold together.

**Assessment.** The proposal:
- keeps the complete schema;
- keeps the measurement, unrounded and integer, in a joinable ledger;
- keeps the strict byte-identity invariant;
- refuses to treat `null` as zero.

It does not fabricate deterministic timings and does not weaken any comparison. The only thing removed from the byte comparison is a quantity that is by nature non-reproducible.

**Rejected alternatives:**
- Excluding `latency_us` from the comparison would weaken the invariant's definition.
- Rounding latency to a coarse grid would still vary between runs and would lose information.

**Conditions (recorded verbatim in the plan addendum):**
1. `decisions.jsonl` keeps all 14 keys, with `latency_us` always JSON `null`.
2. Measured timings go to `runs/<policy>_seed<s>/provenance/decision_latency.jsonl`, in the same order, with `sort_keys`. Each line has exactly `decision_index`, `job_id`, `t_s` and `latency_ns` (integer, unrounded).
3. **Span definition:** context build → scoring → `place` → RAPS `assign_nodes_to_job` → committed update. It excludes the queue sort and I/O. The manifest records the span text and both ledgers' SHA-256 and row counts.
4. At end of run, the runner asserts equal row counts and an exact `(decision_index, job_id, t_s)` join. A unit test covers the split and the join.
5. Invariant 3 is unchanged in meaning: byte-identical `decisions.jsonl` plus identical `intervals.parquet` values. The timing ledger is excluded from byte comparison.
6. Latency metrics come only from the timing ledger. If that ledger is missing, the metric is missing.

**Implementation location:** Sol chooses where to split, either in the runner's sink or in the scheduler. The schema and tests above are required either way.

## 3. R4 — integer-second runtime representation: **APPROVE WITH CONDITIONS**

### 3.1 Root cause (independently verified in `sim-raps/raps/engine.py`)

- **FACT:** At second t:
  1. `prepare_timestep` (`:483`) completes jobs whose `current_run_time ≥ expected_run_time`. `current_run_time` is the integer value set by the previous second's `complete_timestep` (`:584-587`), i.e. `t − 1 − start`.
  2. On a power tick, `tick()` sets `current_run_time = t − start` (`:640`) and raises "Job should have ended in replay!" if it is `> expected_run_time` (`:655-657`).
- **DERIVED:**
  - For an integer runtime R, the last tick sees exactly R, which does not satisfy `> R`, and completion happens at start + R + 1. It never raises.
  - For a non-integer R, a power tick at start + ⌈R⌉ always raises. On Summit (Δ = 10 s) that is a 1-in-10 chance per job, so thousands of jobs make a crash essentially certain.
- The reproducer `test_fractional_runtime_crossing_power_tick_raises` (start 25, R = 4.5, tick at 30) demonstrates exactly this.
- **Ceil to integer seconds removes the cause.** No RAPS patch is needed.
- **DERIVED:** Fractional `submit_time` is harmless. RAPS admits a job at the first integer second ≥ `submit_time` (`:461`), and `start_time` is an integer.

### 3.2 Review of the unapplied Task 8 patch (all FACT, from the patch text)

- **RNG:** a single `default_rng(seed)`. Draw order is the 1e6 Monte Carlo node sizes, then the 1e6 Monte Carlo durations, then per job: inter-arrival, nodes, duration, CPU, GPU.
- **Frozen values preserved:**
  - node sizes and weights;
  - lognormal median 1800 (via `log(median)`), σ 0.8, clip [300, 14400];
  - CPU choices;
  - GPU uniform over 0..`gpus_per_node`;
  - ρ = 0.6.
- **Poisson construction:** exponential inter-arrivals at rate = ρ · n / E[nodes · runtime], with the expectation estimated from the **identically represented** Monte Carlo. Arrivals are cut off at the horizon.
- **Runtime bounds:** ceil is applied after clipping, so represented runtimes are integers in [300, 14400]. There is no other truncation. `time_limit = ceil(1.5 · R)` is never below R, and this is asserted.
- **Determinism and storage:**
  - The same seed gives an identical frame and parquet SHA (tested in scratch).
  - `write_workload` refuses to overwrite different content (`xb` mode), and the sidecar SHA is checked.
- **`jobs_from_frame`:**
  - resets `Job._id_counter`;
  - asserts `time_limit ≥ expected_run_time`;
  - casts to Python `int`/`float`, which matters because RAPS rejects `np.int64` traces;
  - round-trips fields (tested).
- **Caveat (INFERENCE):** Parquet bytes depend on the pandas and pyarrow versions. That is acceptable under SHA keying, provided the versions are recorded (condition c).

### 3.3 Bounded effect (do not describe as "no change")

The continuous distribution remains the specified lognormal. The executed durations are its discretisation:
- Each duration increases by less than 1 s, about 0.5 s on average. That is at most 0.33 % for a 300 s job and about 0.02 % of the mean runtime.
- Because the Monte Carlo uses the same representation, the arrival rate targets ρ for the executed durations.
- RAPS completion bookkeeping adds one further second of occupancy per job (start + R + 1). This is identical across policies.

### 3.4 Conditions

These are recorded verbatim in the plan addendum, items a–f:
- **(a)** One helper produces represented runtimes for both the Monte Carlo and the jobs.
- **(b)** A test asserts integer dtype and bounds for `expected_run_time` and `time_limit`.
- **(c)** `meta.json` records:
  - the spec parameters;
  - the representation text and draw order;
  - `mc_samples`, `mc_expected_node_seconds`, arrival rate;
  - the generator source SHA-256;
  - numpy, pandas and pyarrow versions.
- **(d)** An integration fixture with integer runtimes (for example 301–310 s on Summit at Δ = 10) completes across power ticks without exception.
- **(e)** Traces are passed as Python scalars.
- **(f)** Overwrite protection is kept and caching is keyed by SHA-256.
- **E10 pre-registration** must also state that submit times are continuous and admitted at ⌈submit⌉.

## 4. Findings

| ID | Sev. | Area | Evidence | Blocks | Smallest correction |
|---|---|---|---|---|---|
| P1 | **major** | `latency_us` vs byte identity | FACT `scheduler.py:81`; spec §7.3 | Task 9 | Resolved by R3 conditions |
| P2 | **major** | Fractional runtime vs RAPS completion order | FACT/DERIVED §3.1 | Task 8 | Resolved by R4 conditions |
| P3 | minor | No code loads frozen G1 parameters into `ThermalPredictive`; the summary's `fit` contains `r2`, so passing `**fit` would fail with a TypeError | FACT `scorers.py:57-79`, `primary.yaml` | Task 9 | T9-i: build `{a_c, b_c_per_kw, tau_s, horizon_s}` explicitly and record it in the manifest |
| P4 | minor | Bench `fmu_steps` = `power_ticks` (not independent) | FACT `bench.py:91,106` | Task 9 (invariant 5) | T9-ii: count `backend.step` calls independently and assert `backend.time_s == horizon_s` |
| P5 | minor | `t_obs_s` written uncast (int 0 vs float); `pump_kw` shape not validated | FACT `scheduler.py:81`, `ThermalView` | Task 9 | T9-iii: publish the initial view at 0.0 (episode-relative), all floats, `pump_kw` from `extras["W_flow_CDUP_kW"]` with shape validated |
| P6 | minor | Summit decision rows are ≈ 8.8 KB. E10 2 h ≈ 13 MB per run (fits); 6 h G4 ≈ 40 MB per run | DERIVED | Task 12 sizing | T9-vi: apply the existing gitignore + SHA rule; no schema change |
| P7 | minor | Rack-count test compares legacy config with itself, so it is tautological | FACT `test_engine_factory.py:19` | none | Optional: compare against `RackGeometry.from_legacy_config(cfg).n_racks` and the spec §3.1 constants |
| P8 | minor | No test has a job that fits the system but not the current free nodes at the head of the queue; no test reuses nodes after completion. Scratch runs of both pass. | FACT tests; DERIVED scratch | none | Optional fixture; the E10 run itself exercises both |
| P9 | info | Committed kW is not reduced between ticks when jobs complete; corrected at the next tick (≤ Δ − 1 s stale) | FACT `scheduler.py:41,74` | none | T9-v: document in E10 (spec-literal; identical across policies) |
| P10 | info | `Packing` scores serialise rack 0 as `-0.0` | FACT `scorers.py:30` | none | Optional `+0.0`; deterministic either way |
| P11 | info | Bench isolation is not captured as an artifact | UNRESOLVED | none | Future benches save the process scan |
| P12 | info | The herd test uses uniform `t_c`, so it is effectively a tie-break test | FACT test | none | Acceptable for mechanics. Herding under real thermal state is an E11/G4 interpretation question. |

## 5. Required versus non-blocking

**Required, within the authorised work:**
- R3 conditions 1–6;
- R4 conditions a–f, plus the E10 pre-registration statements;
- Task 9 conditions i–vi.

**Non-blocking:** P7, P8, P10, P11, P12. P8 is recommended but optional.

**Carried interpretation limits (unchanged from C1):**
- The G1 parameters are frozen heuristic parameters, not validated steady-state predictors.
- The warm-up is capped, not settled.
- The room-air what-if is dropped.
- Benefit beyond power balancing is untested.
- Closed-loop coolant above 70 °C is reported, not a stop. Non-finite coolant or FMU errors remain stops.
- Packing-versus-power_balance numbers in E10 are mechanics evidence only, not a G4 result.

## 6. Bounded authorisation for Sol

**Authorised** (fixed E10 configuration: Summit, `packing` and `power_balance` only, seed 1, ρ = 0.6, nominal ambient, 7200 s capped warm-up, 2 h episode, one OS process per run, 720 FMU steps per run):
1. Apply the reviewed Task 8 patch with R4 conditions a–f. Verify, then commit Task 8.
2. Implement Task 9 with R3 conditions 1–6 and T9 conditions i–vi.
3. Generate the E10 workload deterministically and record its SHA-256. Pre-register E10 (README + `config.yaml`) stating the R3/R4 representations, the six invariants and the decision rule. Commit before any run.
4. Run `packing`, `power_balance` and the `packing` determinism rerun. Verify all six invariants. Produce the shared-scale heatmaps and the E10 results.
5. Write, commit and push `docs/checkpoints/C2-vertical-slice.md`. **Stop at C2.**

**Not authorised:** Tasks 10–12, any policy-comparison matrix, other policies, ρ/seed/horizon changes, G1 refit, FMU-selection changes, RAPS patches, or any new experiment.

## 7. Message for Bipin to paste to Sol

See the final section of this review's chat reply (identical text). It is reproduced here for the record:

```
Sol — C2 preflight review is complete (docs/checkpoints/C2-preflight-review-opus.md, reviewed SHA 037b1dd). Pull feat/parasparam-demo first; the plan now has a dated addendum "Approved C2 preflight representation decisions (2026-10-27)". Read it and the review before coding.

Decisions:
- R3 (latency vs byte-identical decisions): APPROVED WITH CONDITIONS. Canonical decisions.jsonl keeps all 14 keys with latency_us = null; measured timings go to runs/<policy>_seed<s>/provenance/decision_latency.jsonl (decision_index, job_id, t_s, latency_ns as unrounded int; same order; sort_keys). Manifest records the latency span text and both ledgers' SHA-256 and row counts. Runner asserts equal counts and an exact (decision_index, job_id, t_s) join; add a unit test. Invariant 3 stays full-file byte identity of decisions.jsonl plus identical intervals values; the timing ledger is excluded from byte comparison; null is never zero.
- R4 (integer-second runtimes): APPROVED WITH CONDITIONS. Root cause verified in RAPS engine ordering. Apply the reviewed Task 8 patch with: (a) one shared helper for represented runtimes used by both Monte Carlo and jobs; (b) test that expected_run_time/time_limit are integer dtype within [300,14400] / ceil(1.5R); (c) meta.json records spec params, representation text, RNG draw order, mc_samples, mc_expected_node_seconds, arrival rate, generator source SHA-256, numpy/pandas/pyarrow versions; (d) integration fixture with integer runtimes (e.g. 301–310 s, Summit Δ=10) completing across power ticks without exception; (e) Python scalar traces; (f) keep overwrite protection and SHA keying. State in E10 preregistration that submit times are continuous and admitted at ceil(submit), and the bounded quantization effect (<1 s per job, +1 s RAPS completion bookkeeping, identical across policies).

Task 9 conditions: (i) build thermal_predictive params from primary.yaml as {a_c, b_c_per_kw from fit, tau_s top-level, horizon_s from yaml}, record in manifest (do not pass r2); (ii) count backend.step calls independently and assert backend.time_s == horizon_s (invariant 5); (iii) publish initial ThermalView after warm-up with t_obs_s = 0.0 episode-relative, all t_obs_s float, pump_kw from extras["W_flow_CDUP_kW"] with shape validation; (iv) interval free counts from geometry.free_per_rack(resource_manager.available_nodes); (v) document that committed kW is corrected only at the next power tick after completions; (vi) if a run dir exceeds 25 MB apply gitignore + SHA rule (no schema change).

Authorized now, in order:
1. Apply the Task 8 patch with conditions (a)–(f); verify; commit Task 8.
2. Implement Task 9 with R3 and T9 conditions; tests green (unit, integration, fmu incl. vertical-slice test using separate subprocesses; historical XFAIL unchanged).
3. Generate the E10 workload (Summit, seed 1, rho 0.6, 2 h), record its SHA-256, preregister E10 (README + config.yaml with R3/R4 representations, six invariants, PASS iff all hold), commit before running.
4. Run packing, power_balance, and a packing determinism rerun — one OS process each, 7200 s capped warm-up, 720 FMU steps per run, nominal ambient. Verify all six invariants; produce shared-scale heatmaps and results/summary.json (mechanics evidence only, not a G4 comparison).
5. Write docs/checkpoints/C2-vertical-slice.md, commit, push feat/parasparam-demo, and STOP at C2.

Not authorized: Tasks 10–12, any comparison matrix, other policies, changes to rho/seed/horizon/warm-up, G1 refit, FMU selection, RAPS patches, new experiments. Stop conditions from the Phase 2 assignment §7 still apply (non-finite coolant/FMU error, invariant failure, timing mismatch, frozen-item change, RAPS patch need, unexplained test failure). Coolant >70 °C is reported, not a stop. Do not touch docs/prompt.md.
```
