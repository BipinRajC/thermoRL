# C4 Prelaunch Review — Task 13 Alibaba-Derived Workload, D5 Loader, E12 Preregistration

**Reviewer:** Claude (Opus), the independent technical and scientific reviewer. **Date:** 2026-10-30.

**Reviewed SHA:** `8908c2a98e5455f45b0c54106a29c4d8a15e8aa6`, the tip of `origin/feat/parasparam-demo` and the expected tip.
- Delta: `1ec6dd5..8908c2a`, which is `75363ee`, `20ff68f`, `ababba8` and `8908c2a` (27 files, +1673/−38).
- My local branch also carries Bipin's unpushed handoff commit, rebased on top. It is documentation only and outside the review scope.

**Labels:**
- FACT: checked directly.
- DERIVED: I calculated it myself.
- INFERENCE: a supported interpretation.
- HYPOTHESIS: plausible but not tested.
- UNRESOLVED: not established.

**Boundary:** Nothing was run against an FMU or RAPS on the Mac. I ran only `tests/unit` in a scratch venv built from the lock. No workload files were regenerated into the repository.

---

## 0. Verdict: **ACCEPT PREPARATION WITH SPECIFIC CONDITIONS — execution needs one Bipin regime decision, the C′ adapter, and one memory fix**

**Task 13 implements D2–D4 exactly.**
- I rebuilt all three workloads independently from the raw CSV, without importing `alibaba.py`. Every job matches bit for bit: submit times, nodes, CPU, GPU, runtime, limit and IDs.
- The D5 loader is metric-neutral by construction. I verified this from the code; I could not re-run the E11 byte proof here, because the raw ledgers are not on the Mac.
- The preregistration came before any run, and protected paths are unchanged.

**The utilisation shortfall is not a generator bug** (§4). It follows from the approved construction:
- an empty start;
- uncompressed, heavy-tailed durations, where 34 % of node-seconds come from jobs capped at 6 h;
- rotation.

A perfectly steady arrival stream at ρ = 0.6 would still average **0.483** over the window.

**My own analysis found a more material property than the mean utilisation, and C4 does not report it** (§4.3).
- The source creation times are extremely concentrated: 99 % of eligible pods were created in the last ≈ 33 of 149 days.
- So the approved cyclic construction produces a **periodic burst regime**. Hourly arrivals run, for example, 3278 / 6195 / **11** / 6193 / **21** / 6187.
- Offered utilisation swings from **0.02–0.09** up to **1.12–1.15**, and demand exceeds machine capacity for 2.3–2.9 % of the window.
- **Seeds 2 and 3 are near-duplicates.** Seed 3 is seed 2 shifted by 33.04 s, with 162 extra pods at the front.

This is a faithful consequence of D4, which I proposed at C3 without examining the creation-time distribution. Bipin approved D4 without this information. **Execution should therefore wait for Bipin to explicitly accept, or revise, this characterised regime** (decision E-A). My recommendation is to **proceed untuned** with mandatory reframing (§4.5).

**Before execution:**
- the E12 C′ evidence adapter (§6);
- a lightweight `run_matrix` seed check, because the current one loads five full E12 runs into the parent process (F2, §5);
- a pre-run regime record (§4.5).

---

## 1. What I verified independently

| Item | Method | Result |
|---|---|---|
| Source CSV | DERIVED: SHA of the Mac copy | `1ee7ed79…34a8`, equal to the sidecar's `source_sha256`. The Arch checksums (26/26) are Sol-reported. |
| Eligible population | DERIVED from raw | 6203 pods: Running 4149, Failed 1869, Succeeded 185. Runtime min/median/max 4 / 723 / 12537496 s, all integer. Floored 2033 (32.774464 %), capped 266 (4.288248 %). |
| Arrival constants | DERIVED | Mean original inter-arrival 2080.258143 s; E[nodes×R] 2797.852652; target 1.008017 s; scale 2063.712861; 3.454491 cycles. |
| Workloads s1–s3 | DERIVED: my own generator (sorting, gaps, offset from `default_rng(seed).integers(6203)`, sequential float accumulation, cutoff below 21600) | **Exact array equality** with the committed parquets for all 7 columns. Offsets 2935 / 5195 / 5033; jobs 21885 / 19627 / 19789; `attrs.seed` correct. |
| Offered utilisation, window (3600, 21600] | DERIVED | 0.485766 / 0.454619 / 0.456625, the same as C4. Including `ceil` admission and RAPS's +1 s raises this by only ≈ +0.0002. |
| Variant statistics | DERIVED with the repo's `node_power_kw` | Default runnable 0.319982 kW/node (6247 nodes); default resource-only 0.316042; multigpu50 resource-only 0.476608. Node weights and share ≥ 2 GPUs match `variant_choice.json`. Selection is `default` by D2, not by statistics. |
| Generator and report hashes | FACT | `alibaba.py` = `39665ab9…` (sidecar and preregistration); `report.py` = `b556b048…` (D5 proof and preregistration). |
| Protected paths | FACT: `git diff 1ec6dd5..8908c2a` | Empty for `sim-raps/`, `models/`, `core/`, `thermal/`, `primary.yaml`, `g4_synthetic.yaml`, `scheduler.py`, `jobs.py`, the E11 and E01 directories, `uv.lock`, `tests/fmu` and `.gitignore`. |
| Unit tests | DERIVED on the Mac | **126 passed.** The 27 integration tests were not run here; Sol reports 153 in total. |
| D5 E11 byte identity | **Not reproduced.** The E11 raw ledgers are absent here. | Reported by Sol (`report_loading_verification.json`). Neutrality was checked in code (§5). |

---

## 2. Task 13 against D2–D4 (FACT from code unless stated)

- **D2.** `choose_variant` (`alibaba.py:118-144`):
  - fixes `default`;
  - marks `multigpu50` as `simulation_eligible: false` with its missing fields listed;
  - computes resource-only statistics separately from the default runnable population;
  - writes with `open('x')`.

  `load_pods` rejects files without timing fields (tested), so no timing join and no imputation are possible.
- **D3.**
  - The filter is `pod_phase != Pending & num_gpu > 0` (`:56`), which keeps Failed and Running pods.
  - Runtime is deletion − creation (`:57`), clipped to [300, H].
  - The integer **assertion** (`:92`) does not round.
  - `limit = ceil(1.5R)` (`:172`).
  - The runner re-checks integer dtype, bounds and limits for the Alibaba kind (`runner.py:47-69`).
- **D4.**
  - Stable sort on (creation_time, source_row) (`:153`).
  - Incoming gaps `[mean, diff]` (`:161`).
  - Exact population E[nodes×R] over clipped runtimes (`:162`); target and scale as approved (`:163-164`).
  - One offset (`:165`), gap/scale accumulation, and `>= horizon` termination (`:166-175`).
  - Lineage: job i is ordered pod (offset + i) mod 6203, with the ordered-row hash recorded.
  - **Gap direction, offset alignment, the wrap at index 0, zero gaps and row ties are correct**, as my exact reconstruction confirms.
- **Mapping.** `nodes = max(1, ceil(g/6))`, `gpu = min(6, …)`, `cpu = min(2, cpu_milli/1000/20/nodes)`. The assumption of 20 cores per socket is recorded.
- **Synthetic path preserved.**
  - The synthetic branch of `prepare_workload` is unchanged.
  - `load_episode_workload` keeps the SHA, horizon and seed checks.
  - `meta_sha256` is checked only where it is configured, which is not the case in E11.

  INFERENCE: E11 behaviour is unchanged. However, `runner.py`'s source hash now differs from `6ee93c4`, which matters for any future E11 rerun (D7).
- **Sidecars** record: horizon, seed, kind, variant, phase mixes, clip statistics, offset, passes, wrap events, ordered-row hash, generator SHA, versions, the representation, and the RNG and lineage rules.
- **A2–A4 are explicit** in the README: units and lifecycle-as-runtime, clipping, arrival-only compression and the artificial wrap, correlated rotations, the static mapping, ≈ 99.3 % 1-node jobs (maximum 2), low density, and possibly weak contrast. The **burst structure and seed near-duplication are missing** (F1).

---

## 3. Descriptive population statistics

The three populations are labelled correctly and are not presented as a performance comparison. Their scope:
- the values are static RAPS-model increments above idle, loss-exclusive, with network at 0;
- they are not measured power;
- multigpu50's phase and timing are unknown.

---

## 4. The utilisation shortfall and the arrival regime

### 4.1 The mean shortfall comes from the construction, not a defect (DERIVED)

- With a **stationary** arrival rate at the exact target and the same clipped durations, an empty-start M/G/∞ projection averages **0.483** over (3600, 21600].
- 75.7 % of node-seconds belong to jobs with R ≥ 1 h, and **34.4 %** to jobs capped at 21600 s. Load therefore keeps rising until the horizon, and ρ = 0.6 is reached only asymptotically.
- The E11 synthetic workloads, built by the same offered-utilisation calculation, reach 0.568–0.576, because their runtimes have a lighter tail and a 14400 s cap.
- The spread between seeds (0.455 vs 0.486) comes from where each rotation lands within the bursts.

### 4.2 The utilisation calculation is correct (DERIVED)
It sums node × overlap of [submit, submit + R) with the window, divided by 4626 × 18000. An FCFS emulation that respects capacity (with `ceil` admission and +1 s, approximating RAPS; HYPOTHESIS-level) gives **realised ≈ offered**: 0.4857 / 0.4547 / 0.4567.

### 4.3 The material finding: periodic overload bursts and near-duplicate seeds (DERIVED)

- **Source creation times:**
  - only 3 pods fall in the first 30 days, and the 1 % quantile is at day 115.8;
  - the 20 largest gaps cover **77 %** of the 149-day span;
  - pods in the sparse early segment are disproportionately long-running.

  The 149-day timeline therefore compresses into a cycle of about 1.74 h: about 23 minutes of dense arrivals at roughly 4.4× the mean rate, then about 80 minutes of near silence.

- **Prepared workloads:**

  | Seed | Arrivals per hour | Hourly mean offered utilisation | Window min / max | Fraction of window > 1.0 |
  |---|---|---|---|---|
  | 1 | 3278, 6195, 11, 6193, 21, 6187 | 0.25, 0.33, 0.41, 0.57, 0.41, 0.71 | 0.09 / 1.15 | 0.029 |
  | 2 | 1021, 6193, 12, 6195, 2178, 4028 | 0.06, 0.34, 0.30, 0.58, 0.37, 0.69 | 0.02 / 1.12 | 0.024 |
  | 3 | (≈ seed 2) | 0.07, 0.34, 0.30, 0.58, 0.37, 0.69 | 0.02 / 1.13 | 0.023 |

  The near-silent hours consist almost entirely of 21600 s jobs.

- **Seed 3 equals seed 2 delayed by 33.04 s, plus 162 leading pods.** All 19627 remaining jobs are identical, with a constant shift. The rotations are independent in name only; there are effectively **two workload conditions plus one near-replicate**.

- **FCFS emulation (HYPOTHESIS, approximating RAPS):**
  - no censoring;
  - mean waits 6–9 s, with 4.7–5.9 % of jobs waiting more than 1 s and a maximum of about 4–5 min;
  - start times stay policy-independent, so invariant 1 is unaffected.

- **Power density (DERIVED):**
  - mean modelled load above idle in the window is **≈ 2.7–2.9 kW per rack**, against ≈ 10.1–10.4 kW in E11;
  - the maximum is 4 GPUs per node;
  - no job fills a rack.

### 4.4 Is this still a meaningful external-validity question? (INFERENCE)

**Yes, but a narrower one than the "Alibaba-derived" label suggests.** E12 can answer:

> Under the frozen protocol, does `thermal_predictive` beat `power_balance` by ≥ 0.5 °C in every seed when the load consists of small (1–2-node), low-power jobs whose arrivals alternate between capacity-saturating bursts and near-idle periods?

Ways in which it is informative:
- M2's forced rack-filling jobs are absent, so placement controls nearly all of the power distribution;
- the resource mix is real.

Ways in which it is limited:
- thermal contrast is low, so the absolute 0.5 °C threshold is relatively stricter;
- the burst/idle periodicity is an artefact of compressing a snapshot-like trace (HYPOTHESIS about the trace semantics; UNRESOLVED);
- during saturated bursts, every policy is constrained to nearly the same occupancy;
- only about two workload conditions are independent.

**Stated before any run:**
- a negative E12 is weak evidence about high-density regimes and does not "confirm" E11;
- a positive E12 would apply to this regime only, and would warrant caution because seeds 2 and 3 are correlated.

### 4.5 Recommendation: proceed untuned, after an explicit Bipin decision

**E-A (new decision, not approved).** Options:

| Option | Effect | Assessment |
|---|---|---|
| **P (recommended): proceed as preregistered** | Execute the existing SHA-pinned workloads. | Correct implementation and no outcome exposure. Any revision would add a new, arbitrary choice (window cut, gap cap, seed spacing). Low cost. The narrower question is legitimate if it is labelled honestly. |
| R1: revise the arrival construction (for example, drop the sparse lead-in or cap gaps) | New workloads, SHAs and preregistration | Not outcome-informed, so it would be legitimate, but the threshold choice is arbitrary and yields another construction to defend. Not recommended. |
| R2: respace seed offsets deterministically | Removes the seed-2/3 duplication | A seed-rule change needing a new preregistration. Not recommended; document the correlation instead. |
| S: skip E12 and record the Task 13 finding | No external-validity run | Gives up the preplanned evaluation for little saving. |

**Conditions if P is chosen.** Before any run, Sol commits a **descriptive pre-run regime record**:
- `results/workload_regime.json`: hourly arrivals and offered utilisation, window minimum/maximum, fraction above 1.0, the creation-time concentration, the seed-2/3 shift identity, and the mean load above idle per rack;
- a new README section, "Prelaunch review addendum", that leaves the hashed frozen sections untouched.

Reporting uses three distinct quantities:
1. **Nominal ρ = 0.6:** an input; the long-run cycle average of the construction.
2. **Offered window utilisation:** a workload property computed before the run, 0.455–0.486, together with its burst profile.
3. **Realised utilisation:** an outcome from RAPS ledgers (`realised_node_utilisation_mean`), plus waits and censoring. These are non-zero now but still identical across policies by construction.

Never write "ρ = 0.6 operation" without the other two.

---

## 5. D5 loader assessment

**Correct and metric-neutral by construction** (FACT, `report.py:250-330`):
- `_collect_seed` holds at most the 5 `Run` objects of one seed and returns only checks, row dicts, diagnostic floats and attribution dicts. No `Run` or DataFrame escapes, which the weakref test confirms (`test_report_loading.py`).
- Seeds are processed sequentially. The seed-1 group is reloaded for plotting **after** the last group has been released.
- Metric functions, window, row order (seeds outer, policies inner, following the config), CSV writer, invariant checks, completeness assertions (15 distinct, 5 per seed) and the seed gate are unchanged. The old `build_report` API is retained.
- The CLI (`main`) uses the bounded loader. Paths come only from `runs/`, so the C′ repeat **cannot** enter primary aggregation.
- The D5 byte proof exercised the `metrics_only` path. The full path's diagnostics, attribution and plots use the same functions, but they are not byte-verified on real data. Acceptable.

**Memory risk (INFERENCE).**
- Estimated peak for the full-path report is one seed's payload (≈ 3.0–3.4 GiB) plus parsing and counterfactual transients plus the seed-1 reload. Plausibly **≈ 4–6 GiB**, against 6.3 GiB available in Sol's snapshot (15.3 GiB total, 16 GiB swap).
- Run the report after all simulations finish, and record its `ru_maxrss` as provenance.
- These figures are estimates, not measurements.

**F2: an uncovered memory path (major engineering).**
- `run_matrix.seed_check` (`run_matrix.py:255-262`) calls `load_run` on **all five full runs of a seed in the parent process**, about 3.3+ GiB for E12, **while worker simulations are still running**.
- `_verify_run` also loads each full run in the parent.
- Any exception in `seed_check`, including `MemoryError`, is recorded as **`invariant_failure`** (`run_matrix.py:193-195`). That is a scientific stop: it terminates and archives healthy in-flight runs, and blocks their retry without an override.

The smallest fix is a metric-neutral lightweight seed check. Per run, load `intervals.parquet` (`it_kw_total` per tick) and stream `decisions.jsonl` keeping only `(job_id, t_s)`, then compare exactly as `invariants()` does. Add a test showing equivalence with `invariants()` on fixtures, plus a check against an E11 committed run pair on Arch. Optionally, classify `MemoryError` as non-scientific.

---

## 6. C′ evidence adapter: the exact remaining work (engineering prerequisite)

The current `evidence.py` and `approved_determinism` (`report.py:174-185`) only accept E11 kinds (`inherited_E10`, `E11_prefix_vs_E10`). If invoked on E12 they would mark every seed INVALID, or mislabel evidence. Minimum implementation:

1. **Rerun execution guard.**
   - Run the rerun as **one fresh process after the 15-run matrix completes**, via `run.py --run-dir experiments/summit/E12_g4_alibaba/provenance/rerun_1/runs/thermal_predictive_seed1`. The runner already refuses an existing directory (`runner.py:132`).
   - Write the console log to `provenance/rerun_1/console_thermal_predictive_seed1.log`. `*.log` is globally ignored, so force-add it, as E11's logs were.
   - Append a journal record.
   - Write `provenance/rerun_1/run_files.json` (path, bytes and SHA for every rerun file) and a byte-identical manifest mirror. **Never write to `results/run_files.json`.**
   - No retry. A crash means G4 is **pending review**, never A′.
2. **Comparison** (new function, for example `evidence.compare_full_rerun`):
   - Preconditions, all exact: both runs pass `manifest_valid(require_job_events=True)` and `validate_expected`; equal `config_sha256`, `workload_sha256`, `meta_sha256`, FMU SHA, `source_sha256` map, `git.sha` and `environment`; `warmup_used_s` 7200; 2160 steps; 21600 s.
   - **Gate:** full-file byte equality of `decisions.jsonl`, and `assert_frame_equal(check_exact=True)` over the complete `intervals.parquet`.
   - Record as information only: interval file-byte equality, and equality of `job_events` and `thermal_publications` bytes.
   - The timing ledger is excluded from comparison, but its join and hash validity is still checked through `manifest_valid`.
3. **Evidence file:**
   - `provenance/determinism_evidence.json` plus its `.sha256` seal, written with `open('x')`.
   - `scope_id: E12_C_prime_2026_10_30` and a per-configuration record for all 15 configurations:
     - `thermal_predictive_seed1`: `verified_E12` with item `{kind: E12_full_rerun_6h, result, ref}`, or `failed`;
     - the other 14: `inherited_not_remeasured` with `{kind: inherited_E10, …}`.
   - `references_sha256` for every compared file and for E10 `rerun_1.json`.
   - `fallback_to_A_prime: false`.
4. **Gate dispatch.** Make `seed_gate`/`approved_determinism` dispatch on the evidence `scope_id`.
   - The E12 gate accepts **only** the exact C′ pattern: TP seed 1 `verified_E12` with `result is True`, and the other 14 inherited.
   - It rejects any other configuration marked verified, TP seed 1 marked inherited (the A′ fallback), any `failed`, or a missing record.
   - The E11 path stays unchanged.
5. **Tests:**
   - identical pair → verified;
   - a one-byte decision change → failed → report INVALID;
   - an interval value change → failed;
   - timing-ledger-only differences → verified;
   - a precondition mismatch (config, source, workload or git) → refused;
   - the A′-fallback record is rejected;
   - the committed E11 evidence still passes the E11 gate;
   - the rerun directory is excluded from 15-run aggregation;
   - no overwrite of the evidence file or the rerun inventory.

---

## 7. Findings (ranked)

### Critical
None. Nothing has run, and the generator is correct.

### Major

| ID | Finding | Evidence | Consequence | Minimal correction | Blocks execution? |
|---|---|---|---|---|---|
| **F1** | Periodic burst/overload regime and near-duplicate seeds 2/3. Not reported in C4 or the README. | §4.3, DERIVED from committed parquets and raw CSV | Changes what E12 can answer; effective replication is about 2 conditions. | Bipin decision E-A; pre-run regime record and reframing (§4.5). No workload change. | **Yes, until E-A is decided** |
| **F2** | `seed_check` and `_verify_run` load full E12 runs in the parent during simulation; a `MemoryError` would be classified as `invariant_failure`. | `run_matrix.py:193-195, 255-262` | A spurious scientific stop could kill healthy runs. | Lightweight seed check (§5), tested. | **Yes** (cheap) |
| **F3** | The C′ adapter is absent; the E11 gate would INVALIDATE or mislabel E12. | `evidence.py`; `report.py:174-185` | E12 cannot be reported. | §6 | **Yes** (acknowledged by Sol) |

### Minor

| ID | Finding | Correction |
|---|---|---|
| F4 | `*.log` is gitignored globally (`.gitignore:33`). Rerun and console logs need force-add or inventory-only treatment. | State the handling in the adapter step. |
| F5 | `runner.py` source hash changed. A future E11 Task-17 rerun cannot claim identical source hashes to `6ee93c4`, only decision-path equivalence. | Note it for D7. |
| F6 | The CPU cap (`min(2, …)`) binds for about 0.4 % (default) and 4.3 % (multigpu50) of pods, and this is not recorded in the sidecar. | Add it to the regime record (descriptive). |
| F7 | The D5 proof covers `metrics_only`; full-path diagnostics are unverified on real data. | Acceptable; record report `ru_maxrss`. |
| F8 | Run memory per worker: `DecisionLedgers.finalize` re-reads about 600 MB of decisions per E12 run. | Monitor; three workers stay within the plan. |

---

## 8. Launch blockers vs optional work

- **Blockers:**
  1. Bipin decides E-A (and E-B: keep the seeds as preregistered, recommended).
  2. The C′ adapter and tests (F3).
  3. The lightweight seed check (F2).
  4. The pre-run regime record (F1 conditions).
- **Optional:** F4–F8; the deferred items R5/R6; a `MemoryError` reclassification.

---

## 9. Smallest defensible next assignment

Once E-A = P and E-B = keep:
1. Commit the regime record and README addendum (descriptive, pre-run).
2. Implement the lightweight seed check and the C′ adapter, test-first, with the §6 tests; commit before any run.
3. Run exactly 15 primary runs with `--workers 3`; record the first wave.
4. Run exactly one fresh-process TP seed-1 rerun alone afterwards, with its own inventory.
5. Write the evidence file and seal, then the report (record peak RSS).
6. Write C4 with the §4.5 three-level utilisation wording, the burst-regime and seed-correlation limitations, M2 not assumed, M3 unresolved, S2 verbatim, and the C3 conditions carried forward. Commit, push, STOP.

No other runs, no retries without a reviewed override, and no Task 15–17 work.

---

## 10. Evidence ledger

| Claim | Evidence | Status | Scope / limits | Next evidence |
|---|---|---|---|---|
| Workloads implement D2–D4 exactly | Independent rebuild, bit-exact | DERIVED | Mac CSV copy (SHA equal) | — |
| Window offered utilisation 0.455–0.486 | Recomputed | DERIVED | Offered, not realised | Realised from E12 ledgers |
| The shortfall comes from the construction, not a bug | Stationary-rate projection 0.483; tail decomposition | DERIVED / INFERENCE | — | — |
| Periodic overload bursts; seed 3 ≈ seed 2 + 33 s | Hourly profiles; exact shifted identity | DERIVED | Trace semantics UNRESOLVED | Realised waits/utilisation from E12 |
| Waits are small and censoring absent | FCFS emulation | HYPOTHESIS | Approximates RAPS | E12 ledgers |
| Low thermal load (≈ 2.8 vs ≈ 10 kW/rack above idle) | Model increments × overlap | DERIVED (modelled) | Static mapping | E12 S1 |
| D5 loader is metric-neutral | Code; weakref test; Sol's E11 byte proof | FACT (code) / Sol-reported (proof) | `metrics_only` path | Report `ru_maxrss` |
| `seed_check` memory risk | Code path | FACT (code) / INFERENCE (size) | — | Fix F2 |
| C′ scope preregistered correctly | `determinism_scope.json`, README | FACT | Adapter absent | §6 tests |
| C3 outcome and conditions carried | README, C4 | FACT | — | — |
