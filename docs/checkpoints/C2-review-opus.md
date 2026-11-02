# C2 Independent Review — First Real-FMU Closed-Loop Slice (E10)

**Reviewer:** Claude (Opus), independent technical and scientific reviewer. **Date:** 2026-10-29.

**Scope**

| Item | Value |
|---|---|
| Reviewed SHA | `b6fb88f8c65608f67392dbf6d9dcb6b673ea3562` (`origin/feat/parasparam-demo` at fetch; equals the expected tip; no further commits) |
| Baseline | `5b2c587` (C2 preflight review) |
| Commits reviewed | `9259e15`, `e1357f6`, `0c32cf5`, `297bc4c`, `b6fb88f` (55 files, +21,768/−4) |
| Coverage | Every changed implementation and test file; all raw E10 ledgers for 3 runs; the SHA-keyed workload and its metadata |

**Method**
- Independent offline analysis of the committed artifacts, plus a parallel code-compliance audit.
- Tests were re-run in a Mac scratch venv. No FMU execution, RAPS simulation or new experiment was performed.

**Labels:** **FACT** = verified directly · **DERIVED** = calculated independently · **INFERENCE** = supported interpretation · **UNRESOLVED** = not established.

## 0. Verdict: **ACCEPT C2 WITH CONDITIONS**

**What C2 establishes:**
- The first real Summit-FMU closed loop runs correctly, deterministically and with complete provenance.
- RAPS exact-node placement → rack power → FMU → published thermal view → next placement all work.
- All six pre-registered invariants pass. I reproduced each one independently from the raw ledgers.
- R3, R4 and all Task 9 conditions are met.
- Both policies were executed correctly: a re-derivation from the logged contexts matches every decision, apart from rounding-induced ties (§3.2).

**What C2 does not establish:**
- Any policy ranking.
- Any benefit of thermal awareness.
- Any mechanism for the temperature ordering seen in E10. E10 is mechanics evidence only.

**Blockers**

| Before | Blocker |
|---|---|
| Tasks 10–11 | None. Required handling of the ledgers is listed in §8. |
| Task 12 launch | **B1** — `g4_synthetic.yaml` has no per-seed workloads, so the runner would raise. |
| Task 12 launch | **B2** — workload horizon is not checked against episode horizon. |
| Task 12 launch | **B3** — no listing/failed-run handling for runs that exceed 25 MB or fail. |
| Task 12 launch | **Two decisions for Bipin:** S1 (G4 secondary metrics) and S2 (time-axis statement). |

## 1. Independently reproduced numbers

All values below are DERIVED from the committed parquet and JSONL files and match Sol's report exactly unless noted.

**Invariants**

| Check | Result |
|---|---|
| Inv 1 — IT kW | Max \|IT kW packing − power_balance\| per tick = **1.818989e-12 kW**, on an identical 720-tick index |
| Inv 1 — start times | All **1514** job start times identical |
| Inv 2 — allocation | Lifecycle replay of `job_events.jsonl` (1514 starts, 1030 completions per run): **0** duplicate, double-allocation or bad-free errors; node reuse after completion exercised (5273 reuse events packing, 4181 power_balance); every decision has exactly `nodes_required` distinct nodes; the pre-action `free` context covered every chosen rack's count |
| Inv 3 — determinism | Packing `decisions.jsonl` SHA `56abb6c1…3bec` on both executions; `intervals.parquet` values equal (bytes also equal) |
| Inv 4 — power reconciliation | Max \|Σ rack kW − `it_kw_total`\| = **1.82e-12 kW** in all three runs |
| Inv 5 — FMU stepping | 720 ticks on a 10 s grid, endpoints 10…7200; 185,040 rows = 720 × 257; manifests record `fmu_steps = 720` and `backend_elapsed_s = 7200.0` |
| Inv 6 — ledgers | 1514 = 1514 canonical/timing rows; exact `(decision_index, job_id, t_s)` join; timing keys exactly `{decision_index, job_id, latency_ns, t_s}` with integer `latency_ns`; 14 canonical keys with `latency_us` always null; median latency ≈ 0.57 ms |

**Workload**
- SHA `65668ff9…c29a`; 1515 offered jobs.
- The single job not started is id 1514, `submit_time = 7199.60173086255`. Admission at ⌈submit⌉ = 7200 falls outside the episode. **The explanation is confirmed.**
- `expected_run_time` is int64 in [300, 14400] and `time_limit = ⌈1.5R⌉` for every job.

**Descriptive metrics** (window 3600 < t ≤ 7200, 360 ticks) — all match Sol's values:

| Metric | packing | power_balance |
|---|---:|---:|
| Mean max (°C) | 53.445129 | 54.115585 |
| p99 max (°C) | 55.579580 | 55.849403 |
| Mean rack (°C) | 43.738314 | 43.665185 |
| Raw max (°C) | 55.609175 | 55.872785 |
| Utilisation | 0.544679 | 0.544679 |
| THI fraction | 0.445233 | 0.287905 |

- No samples above 70 °C.
- Minimum episode pump power 4.131 kW.
- No warm-up or initialisation rows.

**Source hashes (FACT, code audit)**
- All 33 recorded hashes match the execution commit `0c32cf5` in all three run manifests.
- Recorded state is dirty only from the pre-existing `docs/prompt.md` deletion and the concurrently created rerun directory.
- The executed code was committed in `e1357f6`. Commit `297bc4c` contains artifacts only.

**Tests:** 78 unit + 26 integration passed in the Mac scratch venv. The Arch figure of 8 FMU passed + 1 strict historical XFAIL is not re-run here. The historical test body is unchanged.

**Runtime projection:** the arithmetic is reproduced. For each run, projected cost = (total − episode) + 3 × episode:

| Run | Projected 6 h cost |
|---|---:|
| packing | 1009.6 s |
| power_balance | 839.1 s |

Five waves give a matrix of 4196–5048 s (see §9).

## 2. Compliance: R3, R4, Task 9 conditions (FACT unless stated)

**R3 (1–6) — met.**
- Canonical rows: 14 keys, `latency_us = null`, asserted when written (`runner.py:44`).
- The timing ledger has exactly the four keys, with `latency_ns` as an unrounded integer. Both ledgers use `sort_keys`.
- The span starts after the queue sort and head-of-line check (`scheduler.py:59`) and ends before row formatting and I/O (`:79`).
- An end-of-run count-and-join assertion is in place (`runner.py:56-62`).
- The manifest records the span text and both SHAs and counts.
- Invariant 3 compares full `decisions.jsonl` bytes and interval values only. No code reads `latency_us`.
- *Minor (N3):* the span also includes `running.append`/`queue.remove` and the placement assertions, which the span text does not name.

**R4 (a–f) — met.**
- One helper, `represented_runtimes`, clips then ceils, and is shared by the Monte Carlo estimate and the jobs.
- Integer dtype and bounds are tested.
- `meta.json` holds: the spec, representation text, draw order, `mc_samples`, `mc_expected_node_seconds`, arrival rate, generator SHA, and package versions.
- The 301–310 s fixture completes across Summit ticks.
- Traces are Python scalars.
- Workloads are keyed by SHA with overwrite protection.
- The code's single RNG draw order matches the declaration.
- Submit times are continuous; there is no other rounding or truncation.

**Task 9 (i–vi) — met.**
- (i) Exactly `{a_c, b_c_per_kw, tau_s, horizon_s}` (no `r2`), recorded in the manifest.
- (ii) An independent `counted_step` wrapper, a per-step `time_s == t` assertion, and final assertions 720 = 720 and `time_s = 7200`.
- (iii) The initial view is at 0.0, with float timestamps; `pump_kw` comes from `W_flow_CDUP_kW`, with shapes validated.
- (iv) `free` comes from `geometry.free_per_rack(resource_manager.available_nodes)`.
- (v) Committed kW is reset only at the power tick, and this is documented.
- (vi) Runs are 16.8 / 18.9 / 16.8 MB.
- Import boundaries and protected files (FMU backend, `primary.yaml`, G1 summary, historical test, `sim-raps/`, `models/`, `docs/prompt.md`) are unchanged.

**Thermal double:** test-only, used only with pytest `tmp_path`. E10 artifacts come from CLI subprocesses running the real FMU (real `fmu.T_prim_*` globals, fmpy Linux environment). No double output appears in the evidence.

## 3. Findings (ranked)

| ID | Sev. | Finding | Evidence | Blocks | Smallest correction |
|---|---|---|---|---|---|
| **B1** | **blocker** | `g4_synthetic.yaml` has no workload path/SHA. The runner asserts that the workload's `attrs.seed` equals the run seed, so seeds 1–3 cannot share one file. | FACT `g4_synthetic.yaml:6-8`, `runner.py:86-89` | **Task 12 launch** | Generate three 6 h workloads (seeds 1, 2, 3) in the locked Arch environment. Add `workload.by_seed: {s: {path, sha256}}` and select by seed. Record them in the E11 pre-registration before any run. |
| **B2** | major | `--horizon-h` changes the episode but not the workload, and nothing checks that the workload horizon equals the episode horizon. A 6 h run could silently use a 2 h workload. | FACT `run.py:224-225`, `runner.py:86-89,232` | **Task 12 launch** | Assert `sidecar["horizon_s"] == horizon_s` before running. |
| **B3** | major | (a) `runs/` is gitignored and 6 h Summit runs will be about 40–50 MB each (about 8.7 KB per decision row × ~4.6k decisions), so every E11 run exceeds 25 MB and no tool lists ignored run files by path and SHA. (b) A failed run leaves a directory containing only `failure.json`, which `run_matrix` can neither skip nor retry without overwriting. | FACT `.gitignore:41`, `runner.py:96,209-211`; DERIVED sizes | **Task 12 launch** | (a) `run_matrix`/`report` writes and commits a `{relative_path: {bytes, sha256}}` listing for every run file, plus `results/` summaries and plots. (b) A failed run directory is moved, never overwritten, to `provenance/failed_<utc>/` before at most one retry. Both events are recorded. |
| **M1** | major | Re-deriving a run's own decisions from its *logged* context does not always reproduce them: power_balance mismatches 7–8 of 1514 (~0.5 %), packing 0. Logged `committed_kw` is rounded to 6 decimals, and ties that live float noise decided become index ties. | DERIVED (two independent rescoring scripts); FACT `scheduler.py:83-85` | **Task 10 design** | Compute disagreement as *scorer A vs scorer B, both re-applied to the same logged (rounded) context*, never against the logged rack. Report each policy's self-reproduction rate as a validity diagnostic. Reconstruct per-rack free-node lists with distinct ids. Keep the schema. |
| **M2** | major (interpretation) | The pre-registered primary metric, time-averaged max-rack, was set in E10 by a single rare event in both policies. Job 184 (32 nodes, all at maximum CPU and GPU) fills one whole rack at peak 49.32 kW from t = 920 under *both* policies. Only 7 of 206 jobs of ≥ 16 nodes are full-power. The argmax rack never changes through the window (rack 55 under packing, rack 181 under power_balance). | DERIVED §7 | Before Task 12 (decision S1) | Keep the frozen primary metric and the G4 rule unchanged. **Pre-register additional descriptive secondary metrics** (S1) and a max-rack attribution diagnostic before any E11 result. |
| **M3** | major (interpretation) | Identical own-rack power, different temperature. The hot racks in the two policies have **byte-identical own-power trajectories** and identical total IT power. Their coolant temperatures still differ by up to **0.95 °C** (at t = 4800 s), and by 0.67 °C on the window mean. Rack temperature therefore depends on how the *other* load is distributed, not only on own and total power. | DERIVED §7 | Neither (interpretation) | State it as an observation. The mechanism is UNRESOLVED. No new characterisation experiment is required. |
| **T1** | moderate (protocol clarity) | The thermal view is published at FMU time t+Δ *before* the RAPS seconds t+1 … t+9 execute. 91.3 % of decisions see a view stamped 1–9 s after the decision time. | DERIVED §6 | Before Task 12 (statement S2) | Pre-registration statement only (§6). No code change. |
| N1 | minor | An interval row mixes RAPS-time-t inputs (`kw`, `free`, `n_running`, `n_queued`, `it_kw_total`) with endpoint-t+Δ outputs (`t_c`, `pump_kw`). | FACT `runner.py:192-195`; DERIVED (job 0 at t = 6 appears in the row labelled 20) | Task 10 docs | Document in metric docstrings. IT energy = Σ kW·Δ is exact. Pump energy is a right-endpoint rectangle. |
| N2 | minor | Window boundary: E10 uses `t_s > 3600` (correct for endpoint labels). The plan's Task 10 says `≥`. | FACT `run.py:58` | Task 10 | Use strict `>` and document it. |
| N3 | minor | The latency span text omits `running.append`, `queue.remove` and the assertions. | FACT `scheduler.py:59-79` | none | Text-only update before E11. |
| N4 | minor | `workload_path` is relative to `thermorl-v2`. | FACT `run.py:50` | Task 10 | `load_run` resolves it against the project root. |
| N5 | info | Parquet bytes embed pandas attrs (versions, generator SHA). Regenerating the same data in a different environment gives a different SHA. | DERIVED | Task 12 pre-registration | Generate the E11 workloads only in the locked Arch environment. A cross-environment SHA difference is not a data change. |
| N6 | info | `fmu_s` includes warm-up and has no scope text. `write_manifest` always writes `backend: "fmu"`, including in the test double's temporary manifest. | FACT | none | Add `fmu_s_scope`. Optionally pass `backend` explicitly. |
| N7 | info | `t_hot_c` = 63.30 °C was never reached (raw max 55.87 °C), so hot rack-seconds will likely be 0 in G4. THI is *not* saturated in this window (0.29–0.45). | DERIVED | none | Report as observed. These are not discriminating metrics here. |
| N8 | info | E10 never had a queue at a power tick, so head-of-line blocking at scale is first exercised in E11. | FACT (code audit) | none | Invariant checks in E11 cover it. |

## 4. Six-invariant assessment

All six **PASS**, as independently reproduced in §1.

The invariants are mechanics guarantees:
- policies differ only in placement;
- allocation is exact;
- the system is deterministic;
- power is conserved;
- FMU stepping is correct;
- provenance is complete.

They say nothing about thermal benefit.

## 5. R3/R4/T9 compliance

Fully met (§2), with the minor documentation items N3 and N6.

## 6. Time-axis assessment (T1)

**Sequence** (FACT, `runner.py:177-201`; RAPS `engine.py:908-938`):
1. At RAPS second t, RAPS completes jobs, enqueues arrivals, and runs the scheduler (which sees the last published view).
2. If t is a power tick, RAPS computes `power_df(t)`, which includes the jobs placed at t, and then yields.
3. The runner reconciles power, resets committed kW, and steps the FMU over (t, t+Δ] with power held at P(t).
4. It publishes the endpoint view stamped t+Δ and writes the interval row labelled t+Δ, all before the generator resumes.

**Consequences** (DERIVED):
- Decisions at a tick second see a view stamped exactly at their own time: `t_obs_s − t_s = 0` for 132 decisions.
- Decisions at t+1 … t+9 see the view stamped t+Δ: `t_obs_s − t_s` ∈ [1, 9] for 1382 of 1514 (91.3 %).
- The view is never older than the decision.
- **There is no leakage of later decisions.** The t+Δ state is a deterministic function of the plant state at t and P(t), and P(t) already includes every placement made at or before t. A placement at s ∈ (t, t+Δ) first affects the FMU over (t+Δ, t+2Δ]. The view is a ≤ 9 s constant-power-hold forecast from the true plant, identical for every policy.
- **Magnitude:** the largest per-rack 10 s change is 0.31 °C; the p99 is 0.057 °C.

**Contract.** This matches spec §3.2 literally: step and observe at each tick; calls in (t, t+Δ] see the last view. The labels are accurate as FMU endpoints.

**Validity by policy:**
- **E10 policies:** irrelevant, because packing and power_balance do not read temperature.
- **G4 thermal policies:** acceptable as a uniform, documented coupling semantics. Thermal policies receive at most a 9 s true-plant hold-power forecast — slightly more than a lagged sensor would provide, and no information about future decisions.

**Required before G4 (S2):** a pre-registration statement, roughly: "published views are the FMU endpoint of the interval driven by P(t); decisions in (t, t+Δ) observe that endpoint (≤ 9 s hold-power forecast; max observed 10 s change 0.31 °C, p99 0.057 °C in E10); no future-decision information." Do not change the code. A causally delayed publication variant would be a protocol change requiring its own decision, and is not recommended given the magnitudes.

## 7. The unexpected temperature ordering

**Ruled out as analysis or implementation errors** (DERIVED / FACT):
- **Score signs and execution.** Both policies were re-derived from the logged contexts. Packing matches 1514/1514 (scores `−index`, lowest index that fits). Power_balance matches except for exact ties at 6-decimal rounding (M1); the live code ranks on unrounded values. 1457 single-rack and 57 spanning decisions in each.
- **Pre-action context.** The logged `free` counts are pre-assignment, and every chosen rack had enough free nodes.
- **Committed power.** Updated per placement and reset at ticks, as approved.
- **Window and aggregation.** Recomputed independently; identical results.
- **Input power.** IT kW is identical across policies, and per-rack sums reconcile.

**Power_balance does spread power** (DERIVED, window means): the across-rack std of time-averaged kW is **5.38** (power_balance) vs **9.17** (packing), and 37 vs 92 racks average above 30 kW.

**Why the max metric does not reflect this** (DERIVED):
- **The argmax is set by one rare event in both runs.** Job 184 (32 nodes, all at maximum CPU and GPU, `job_kw` 60.59) starts at t = 920 and spans two racks under the frozen rule (fill the best-scoring rack fully, then the next). Under both policies it saturates one entire rack at peak 49.32 kW for the rest of the episode: rack 55 under packing, rack 181 under power_balance. That rack is the argmax at every tick of the window in both runs.
- **Same own power, different temperature.** The two hot racks' per-tick kW series are *byte-identical*, and total IT kW is identical. Their coolant temperatures still differ, by −0.04 °C at t = 930, +0.58 °C at 3600 s, +0.95 °C at 4800 s and +0.26 °C at 7200 s. The 0.67 °C gap in the mean-max metric is this difference. It is not a difference in the policies' treatment of that rack.

**Observations (DERIVED):**
1. The pre-registered primary metric is, in this run, the temperature of the rack hosting a rare full-power large job. Such jobs saturate a rack under any policy because of the frozen spanning rule.
2. On the Summit twin, a rack's temperature depends on the placement of the *other* load, even at identical own and total power.

**UNRESOLVED:** the physical mechanism of (2). Shared primary-loop or hydraulic redistribution is a plausible hypothesis, not established; the ledgers carry no per-CDU primary diagnostics. Whether the effect is systematic or episode-specific is also unknown.

**Do not:** tune the workload, the policy weights or the spanning rule; or treat E10 as a ranking.

**Smallest necessary action:** no new experiment. Keep the primary metric and G4 rule frozen. Pre-register additional descriptive secondary metrics (S1) so that G4 also reports distributional effects and attributes the max-rack value. Interpret G4 with M2/M3 explicitly in mind. With three seeds, the primary metric may be dominated by where the few full-power large jobs land; that variance must be reported, not tuned away.

## 8. Required corrections vs non-blocking

**Before or within Tasks 10–11** (they may proceed now):
- **M1** disagreement method and self-reproduction diagnostic;
- **N1** row-semantics documentation;
- **N2** strict window;
- **N4** path resolution;
- **N7** report non-discriminating metrics as observed;
- **S1** secondary metrics, if approved;
- max-rack attribution;
- latency metrics read only from the timing ledger, with a missing ledger producing a missing metric;
- wait = (integer start) − (continuous submit), with a stated censoring rule (jobs not started by the horizon are censored and counted separately; this is identical across policies);
- Task 11 plots generalised from the hard-coded 2 h axis.

**Before the Task 12 launch:**
- **B1, B2, B3**;
- **S2** time-axis statement;
- **N3** and N6 text updates;
- the E11 pre-registration committed (README, config and three workload SHAs) before any run.

**Non-blocking limitations (carried):**
- G1 parameters are frozen heuristics, not validated predictors.
- The warm-up is capped, not settled.
- The what-if is dropped.
- Benefit beyond power balancing is untested.
- 45 °C is a reference value, not a validated safety limit.
- Coolant above 70 °C is reported, not a stop.
- M3 coupling is an observed model property with an unresolved mechanism.

## 9. Runtime and worker recommendation

**Projection audit** (DERIVED): the formula and arithmetic are correct, but the projection is likely optimistic:
- Episode FMU cost is **policy-dependent** (234 s packing vs 177 s power_balance per 2 h, +32 %).
- The 2 h episodes include a ~40-minute ramp from an empty machine. 6 h episodes run mostly at steady load.
- Three of the five policies are untimed.
- Serialisation grows to ≈ 4.6k decisions per run.
- The concurrency contention seen in C1 (105 vs 146 s per simulated hour) may recur.

**Recommendation:**
- Keep **3 workers**, the configuration tested in E10.
- Budget **1.5–2.5 h** of wall time for E11.
- Record the actual first-wave timings in the E11 README.
- Raising the worker count to 4 is an operational choice, provided the D2-style isolation is not required for the matrix. Running fewer workers does not affect results.

## 10. Bounded next assignment

1. **Tasks 10–11 now:**
   - metrics and report on the E10 ledgers as test data;
   - M1/N1/N2/N4 handling;
   - S1 metrics and max-rack attribution, if Bipin approves.
2. **Task 12 preparation:**
   - B1–B3, B2 assertion, N3/N6 texts;
   - three 6 h workloads;
   - E11 pre-registration (frozen G4 protocol + S1 + S2 statements), committed before running.
3. **Task 12 execution:**
   - the frozen nominal G4 matrix: 5 policies × seeds {1, 2, 3}, ρ = 0.6, 6 h, 3 workers;
   - invariant checks across all policies per seed;
   - the report.
4. **Stop at C3.**

**Frozen:**
- ρ, seeds, horizon, warm-up;
- G1 parameters and `primary.yaml`;
- policy definitions, the spanning rule, the primary metric and the 0.5 °C rule;
- FMU selection.

**Not authorised:** Alibaba (Tasks 13–14), viz (Task 15), what-if, extra experiments, RAPS patches.

The copyable message for Sol is in the final reply that accompanies this review (also below).

```
Sol — C2 independent review complete (docs/checkpoints/C2-review-opus.md; reviewed b6fb88f). Verdict: ACCEPT C2 WITH CONDITIONS. All six E10 invariants and R3/R4/T9 conditions independently verified. E10 is mechanics evidence only.

Bipin-approved decisions (recorded by relaying this message):
S1 — G4 secondary metrics (pre-register before any E11 run; primary metric and 0.5 °C G4 rule stay frozen): over 3600 < t_s <= 21600, report per run (a) rack_t_std_mean_c = time-mean of across-rack population std of t_c; (b) top_decile_mean_c = time-mean of the mean of the hottest ceil(0.1*n_racks)=26 racks' t_c; (c) rack_kw_std_mean = time-mean of across-rack std of kw; plus (d) max-rack attribution: per tick argmax rack, its share of window ticks, and the job ids resident on it (from job_events). Descriptive only; no decision rule changes.
S2 — Time-axis statement (no code change): published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies. Put verbatim in the E11 preregistration and C3 limitations.

Required corrections:
- Task 10: disagreement = scorer A vs scorer B both re-applied to the same logged (6-decimal) context, never vs the logged rack; also report each policy's self-reproduction rate (E10 power_balance ≈ 99.5% due to rounding ties). Reconstruct per-rack free-node lists with distinct ids. Interval rows: kw/free/n_running/n_queued/it_kw_total are RAPS-t inputs, t_c/pump_kw are t+Δ endpoints — document; IT energy = Σ kw·Δ; pump energy right-endpoint. Windows use strict t_s > eval_start. Resolve workload_path against the thermorl-v2 project root. Latency metrics only from provenance/decision_latency.jsonl (missing ⇒ missing). Waits = integer start t_s − continuous submit_time; jobs not started by the horizon are censored and reported separately. Report hot rack-seconds and THI fraction as observed (t_hot 63.30 °C not reached in E10).
- Task 11: generalise plots beyond the hard-coded 2 h axis.
- Task 12 launch blockers: (B1) generate three 6 h workloads (seeds 1,2,3) with --prepare-workload in the locked Arch environment; add workload.by_seed {s: {path, sha256}} and select by seed; (B2) assert workload sidecar horizon_s == episode horizon_s; (B3) a committed listing {relative_path: {bytes, sha256}} for every run file (runs >25 MB stay gitignored), and failed run dirs moved to provenance/failed_<utc>/ (never overwritten) before at most one retry, both recorded. Also: extend LATENCY_SPAN text to name running.append/queue.remove/assertions; add fmu_s_scope.

Authorized, in order:
1. Tasks 10–11 (metrics incl. S1 + attribution, plots, report) tested on the E10 ledgers; commit.
2. Task 12 preparation (B1–B3 + texts); generate and SHA-record three 6 h workloads; preregister E11 (README + config with frozen G4 protocol: 5 policies × seeds 1–3, rho 0.6, 6 h, nominal, 7200 s capped warm-up; S1; S2; invariants 1–6 per seed across all five policies; primary rule unchanged); commit BEFORE any E11 run.
3. Launch the E11 matrix with 3 workers (one FMU per process); record first-wave timings; run report; verify invariants per seed.
4. Write docs/checkpoints/C3-g4-synthetic.md (metrics table, decision.json outcome, per-seed gaps, S1 metrics, attribution, disagreement + self-reproduction, invariants, runtimes, limitations incl. M2/M3/S2), commit, push, STOP at C3.

Frozen: rho, seeds, horizon, warm-up, G1 params, primary.yaml, policy definitions, spanning rule, primary metric, 0.5 °C rule, FMU selection. Not authorized: Tasks 13–16, Alibaba, viz, what-if, extra experiments, RAPS patches. Stop conditions unchanged (non-finite coolant/FMU error, invariant failure, frozen-item change, RAPS patch need, unexplained test failure); >70 °C is reported, not a stop. Do not touch docs/prompt.md.
```
