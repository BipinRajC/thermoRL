# C2 — First real-FMU closed-loop vertical slice

**Date:** 2026-10-27. **Status: CHECKPOINT C2 reached; E10 PASS; mandatory stop for review.** Summit remains primary. No Tasks 10–12, comparison matrix, additional policy experiment, what-if, refit, selection change or RL work has begun.

## Commits and executed sources

All work is on `feat/parasparam-demo`; the retired branch was not used.

| Work | Commit |
|---|---|
| Approved D1/D2 recorded verbatim | `425b51b` |
| Task 5 engine factory, D1 helper and timing tests | `7695c34` |
| Task 6 pure placement and five frozen scorers | `cf1d522` |
| Isolated Task 5 bench / D2 outcome | `2a2616f` |
| Task 7 scheduler, committed power, allowed N1/N3/N5 coverage | `baf24fb` |
| Preflight review and approved R3/R4/T9 decisions | `5b2c587` |
| Task 8 with all R4 conditions | `9259e15` |
| Task 9 unit/integration-tested implementation anchor | `e1357f6` |
| E10 immutable workload and preregistration, before real-FMU runs | `0c32cf5` |
| Task 9 completed real-FMU result and artifacts | `297bc4c` |

Every real E10 run records execution SHA `0c32cf5` and source-file hashes independently verified against that commit. The E10 Question, Rule, Configuration, Method, Metrics and Limitations and exact config bytes remain unchanged from preregistration. [Audit](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/provenance/preregistration_audit.json). All FMU SHA checks preceded instantiation, and every policy run and rerun owned its FMU in a separate OS process. G1, `primary.yaml`, the FMU/backend, RAPS source and historical test body are unchanged.

## Task 5 bench, D1 and D2

Exact command from `thermoRL/thermorl-v2`:

```bash
uv run python -m thermorl2.experiments.bench --system summit --hours 6
```

[Full raw bench JSON](../../thermoRL/thermorl-v2/experiments/summit/_bench/task5_bench_20261026T224138_640592Z.json), [environment](../../thermoRL/thermorl-v2/experiments/summit/_bench/environment.txt), [system card](../../thermoRL/thermorl-v2/experiments/summit/SYSTEM.md). One isolated simulation worker was measured from process launch to exit, including imports, instantiation, full capped 7200 s warm-up, 6 h idle episode and shutdown. A lightweight timing parent ran no simulation. Only editing and non-FMU unit tests ran meanwhile; real-engine integration and FMU tests ran after it exited.

Bench operational JSON (full source/input provenance is in the linked raw file):

```json
{
  "fmu_s": 902.9637261998796,
  "fmu_steps": 2160,
  "horizon_h": 6,
  "instantiation_s": 7.787814560000697,
  "power_ticks": 2160,
  "raps_s": 3.9649237830744823,
  "switch_required": false,
  "total_s": 912.5393135249997,
  "twice_after_warmup_instantiation_s_information_only": 1177.2581247300004,
  "twice_total_s_information_only": 1825.0786270499993,
  "warmup_instantiation_s": 323.91025115999946,
  "warmup_used_s": 7200.0,
  "warmup_wall_s": 316.12243659999876
}
```

**D2 PASS: 912.539313525 s (15.209 min) <=2700 s.** Summit retained. The doubled values are information only. Horizon remains **6 h** because `4*total_s >300`. No guard-triggered switch or C1 rerun occurred.

| D1 reference, kW/rack | Idle | Peak |
|---|---:|---:|
| C1 probe, loss-exclusive | 13.201714285714 | 47.282326530612 |
| Actual RAPS rack power, loss-inclusive | 13.822619047619 | 49.323256802721 |

`raps_rack_kw` calls RAPS's own power code; no loss formula was reimplemented. The actual power_df values feed the FMU and the idle warm-up. The roughly 4% understatement of between-tick `job_increment_kw` remains frozen and documented. G1 still maps FMU-input kW to coolant; it was not refit.

## Test results

| Gate | Exact result |
|---|---|
| Task 8 focused conditions, including integer completion fixture | 7 passed |
| Full non-FMU suite before E10 | 104 passed in 3.58 s |
| Final unit suite | **78 passed in 2.36 s** |
| Final integration suite | **26 passed in 2.55 s** |
| Full FMU tier, including actual three-process vertical slice | **8 passed, 1 xfailed in 646.94 s** |

The historical Task 1.5 physical-response test is still strict XFAIL with its unchanged body and 500–1000 s bound. It has not become a passing physical test. The expected missing-helper/CLI and required R3/T9-condition red tests preceded implementation. A separate engineering fixture used real RAPS and a test-only thermal double in pytest's temp directory; none of its outputs were used as E10 evidence. All published E10 outputs came from the real SHA-pinned Summit FMU.

Exact verification/production commands, run from `thermoRL/thermorl-v2`:

```bash
uv run pytest tests/unit/test_synthetic.py tests/integration/test_jobs.py -v
uv run pytest tests/unit/test_runner_support.py tests/unit/test_scheduler_unit.py -v
uv run pytest tests/integration/test_runner_contract.py -v
uv run pytest tests/unit tests/integration -q
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --seed 1 --prepare-workload
# Workload SHA/config and E10 protocol committed at 0c32cf5 before this command:
THERMORL2_E10_ROOT=experiments/summit/E10_c2_vertical_slice uv run pytest tests/fmu -v
uv run pytest tests/unit -q
uv run pytest tests/integration -q
```

The vertical-slice test launched the following three CLI subprocesses concurrently, with no second experiment set or automatic retry:

```bash
python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --policy packing --seed 1 --run-dir experiments/summit/E10_c2_vertical_slice/runs/packing_seed1
python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --policy power_balance --seed 1 --run-dir experiments/summit/E10_c2_vertical_slice/runs/power_balance_seed1
python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --policy packing --seed 1 --run-dir experiments/summit/E10_c2_vertical_slice/provenance/rerun_1_packing_seed1
```

## E10 six-invariant gate

| Invariant | Result | Evidence |
|---|---|---|
| 1_it_kw_and_start_times_identical | PASS | Maximum IT-kW difference 1.818989403546e-12; all 1514 job starts identical. |
| 2_exact_distinct_free_nodes | PASS | Independent lifecycle replay verifies requested node count, distinctness, free state and reuse across 1514 starts / 1030 completions per run. |
| 3_decisions_byte_identical_and_interval_values_identical | PASS | Packing canonical decision bytes identical; all interval values identical. Interval file bytes also match (information only). Actual measured timing ledger excluded. |
| 4_rack_power_sums_reconcile | PASS | Largest per-tick reconciliation error 1.818989403546e-12 kW; tolerance 1e-6. |
| 5_independent_step_count_and_clock | PASS | 720 power ticks, independently counted backend.step calls=720, backend.time_s=7200.0; 185040 rows per run on endpoints 10..7200. |
| 6_manifests_and_joinable_ledgers_complete | PASS | Required fields, hashes, full porcelain, frozen parameter dict, power references, environments, span, 1514 rows in each decision/timing ledger and exact joins verified. |

**Decision: PASS (6/6).** [E10 README](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/README.md), [summary](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/results/summary.json), [invariants](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/results/invariants.json), [independent audit](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/provenance/independent_audit.json), [rerun evidence](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/provenance/rerun_1.json).

The canonical packing decision SHA is `56abb6c14d4db49b3caac8aa68fd8531868902e3c2d988eb537c9c622d383bec` on both executions. Runtime measurements remain genuine and separate; null latency is never zero.

## E10 key numbers — mechanics evidence only

All runs: Summit, seed 1, rho=.6, nominal 290 K, 7200 s capped warm-up and 2 h episode. The workload has 1515 offered jobs and SHA `65668ff9e11cad523bf2c26541e0982e1e14e79d26b88bf7f9fd791c7d3fc29a`. [Parquet](../../thermoRL/thermorl-v2/experiments/summit/_workloads/65668ff9e11cad523bf2c26541e0982e1e14e79d26b88bf7f9fd791c7d3fc29a.parquet), [full generation metadata](../../thermoRL/thermorl-v2/experiments/summit/_workloads/65668ff9e11cad523bf2c26541e0982e1e14e79d26b88bf7f9fd791c7d3fc29a.parquet.meta.json).

Temperature means/p99 and sampled utilisation use **3600 < t_s <=7200** (360 right-endpoint samples). P99 uses linear percentile. Raw maximum uses all 720 episode samples, with no initialization/warm-up samples.

| Run | Mean max °C | P99 max °C | Mean rack °C | Raw max °C | Mean sampled node util | Jobs started | RAPS s | FMU s | Total s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| packing | 53.445128703 | 55.579580360 | 43.738313657 | 55.609174587 | 0.544679229 | 1514 | 4.224714 | 532.739100 | 540.665581 |
| power_balance | 54.115585107 | 55.849402767 | 43.665184613 | 55.872785112 | 0.544679229 | 1514 | 3.968780 | 476.589654 | 484.213451 |
| packing_rerun | 53.445128703 | 55.579580360 | 43.738313657 | 55.609174587 | 0.544679229 | 1514 | 4.182109 | 530.507808 | 538.399463 |

The rerun is a determinism check, not a third policy. RAPS time excludes scheduler callback wall time (also recorded); measured decision latency covers the approved inner span and excludes sort/row-format/I/O. FMU API time includes initialization/warm-up. Total_s covers EpisodeRunner.run through ledger serialization, excluding interpreter imports; all scopes are recorded in the manifests. These timing scopes are not confused with the process-lifetime D2 guard.

## Shared-scale heatmaps

![E10 shared-scale rack-time coolant heatmaps](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/plots/heatmaps.png)

Both panels share the same colour range and episode axis; warm-up is excluded. Packing concentrates heat on lower rack indices. Power_balance distributes the occupied/hot regions across the plant, but the anticipated thermally flat panel is not observed.

## R3/R4, time axis and provenance

- Canonical decisions retain exactly 14 keys with `latency_us=null`. Actual unrounded integer nanoseconds are in each run's `provenance/decision_latency.jsonl`, in the same order, with exactly the four approved keys. The runner asserts equal counts and exact `(decision_index,job_id,t_s)` joins. Manifest span and both SHA-256/row-count pairs are independently verified.
- One shared R4 helper clips the fixed lognormal then ceils to integer seconds for both MC and actual jobs. Integer dtype/bounds, `ceil(1.5*R)` limits, Python scalar traces, overwrite protection and completion across Summit power ticks are tested. Metadata records the full spec, representation, draw order, one-million-sample expectation/rate, generator source SHA and numpy/pandas/pyarrow versions. Submit times remain continuous and are admitted at ceil(submit). The <1 s quantization and extra 1 s completion bookkeeping are explicit and identical across policies.
- G1 parameters are loaded explicitly as exactly a_c, b_c_per_kw, tau_s and H=600, without r2. Each manifest records them. They remain frozen heuristic parameters, not validated steady-state predictors. No thermal-aware policy was run here.
- The initial post-warm-up ThermalView is at 0.0, and all subsequent observation timestamps are floats. Under the prescribed coupling sequence, a RAPS power tick t advances the FMU over (t,t+10], then publishes its endpoint view before the RAPS generator resumes. Interval t_s and t_obs_s label that FMU endpoint. The [publication ledger](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/runs/packing_seed1/provenance/thermal_publications.jsonl) pairs both clocks. Free counts come from the actual resource manager at the power tick; no within-tick thermal interpolation is claimed.
- Completion does not immediately subtract committed power between ticks. The next power tick corrects it, as specified and preregistered.
- Run sizes are 16772825 / 18909997 / 16772717 bytes, all below 25 MB; all are committed. No schema reduction or ignore exception was needed. Source hashes match execution commit 0c32cf5, and input/source files were not changed during runs. Full porcelain includes the pre-existing user-owned docs/prompt.md deletion and concurrent output files; it is preserved, not attributed solely to artifacts.

## Anomalies — FACT / INFERENCE

- **FACT:** Power_balance's final-hour mean maximum is **0.670456403867 °C higher** than packing's (54.115585 vs 53.445129). Its raw maximum is also slightly higher. The expected flatter thermal picture is not observed. No workload, seed, horizon, parameter or policy was adjusted to reverse this ordering.
- **INFERENCE:** This fixed two-hour, seed-1 mechanics run cannot establish a G4 policy ranking or an advantage beyond power balancing. The cause of the temperature ordering is not established here; no new experiment was run to explain it. Review the actual visual and operating regime before authorizing the matrix.
- **FACT:** All three runs have **zero samples above 70 °C and no affected racks**; largest raw value is 55.872785112 °C. No non-finite coolant or FMU error occurred.
- **FACT:** Every interval begins after warm-up; the known cold-initialization pump artifact (~−92.4 kW) is excluded. No episode pump sample is negative; minimum is 4.131024602 kW.
- **FACT:** Temperature-only THI fraction below .10 is 0.445233463035 for packing and 0.287905317769 for power_balance in this window. The outcome is not fully saturated here. T_max=45 °C remains a comparison reference, not a validated hardware safety limit.
- **FACT:** The one offered job not started is id=1514, submit=7199.60173086255; admission=7200 is outside the RAPS episode. Both policies have identical starts. Progress log counts are sampled at power ticks; final counts also include starts after the last tick at 7190 and before episode end.
- **FACT:** RAPS's existing missing-Summit-dataloader warning appears at construction, but the approved synthetic workload is injected and all required ticks complete. No RAPS patch was needed. The user-owned docs/prompt.md deletion remains unstaged and untouched.

## Projected G4 synthetic matrix runtime — information only

**Proposed workers: 3**, matching the successfully tested three-process E10 orchestration. No matrix has run.

[Projection and source-manifest hashes](../../thermoRL/thermorl-v2/experiments/summit/E10_c2_vertical_slice/results/runtime_projection.json). For each observed actor:

`projected_6h = (total_s - episode_wall_s) + 3*episode_wall_s`

Keep initialization/warm-up once, scale episode wall time from 2 h to 6 h, then use five waves for 15 runs at three workers. Projected per-run six-hour cost is **839.114–1009.616 s (13.985–16.827 min)**. Matrix wall projection is **4195.572–5048.080 s (69.926–84.135 min)**.

This assumes the same concurrency and linear episode cost. The other three policies, six-hour workload, later thermal regime, serialization growth and scheduling imbalance are not measured. It is a timing extrapolation, not a measured matrix runtime or a performance conclusion. The approved G4 horizon remains 6 h.

## Stop and proposed next step

**Mandatory CHECKPOINT C2 stop.** Review the six-invariant PASS, shared-scale image, unexpected temperature ordering, provenance and timing projection. The proposed next assignment is **Tasks 10–12 → C3**, only after steering. No policy matrix, additional experiment, what-if, alternate system, G1 refit, threshold/input tuning, RAPS patch, or RL work was performed. No further work proceeds on this turn beyond committing and pushing this checkpoint.
