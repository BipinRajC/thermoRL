# C2 preflight stop — Task 5 guard passed; two representation decisions pending

**Date:** 2026-10-27. **Status: stopped before E10; CHECKPOINT C2 has not been reached.** No E10 workload, run, heatmap, invariant result or policy-comparison result has been produced. Tasks 5–7 and the isolated bench are complete. Task 8 is a reviewable draft proposal; Task 9 has not started.

## Completed commits

Starting point: `4f13f44`, merged PR #1, on `feat/parasparam-demo`. The retired branch was not used.

| Work | Commit |
|---|---|
| Step A: verbatim approved D1/D2 in plan; D2 post-result note in X01 | `425b51b` |
| Task 5: engine factory, D1 reference helper, timing/reconciliation tests, bench | `7695c34` |
| Task 6: pure placement and five frozen scorers | `cf1d522` |
| Isolated bench result and D2 guard | `2a2616f` |
| Task 7: scheduler, committed power, decision rows; permitted N1/N3 coverage | `baf24fb` |

The workload-rounding proposal has not been applied to the runtime package. Its complete source/tests are preserved in the [draft patch](../superpowers/proposals/2026-10-27-c2-runtime-representation-draft.patch); `git apply --check` passed. Scratch verification of that draft passed, including identical generated frames/parquet hashes, offered-load bounds and job-field roundtripping. This is not an approved or executed E10 workload.

## Task 5 isolated cost bench

Exact command from `thermoRL/thermorl-v2`:

```bash
uv run python -m thermorl2.experiments.bench --system summit --hours 6
```

Before launch, a process scan found no other simulation process. The single simulation worker ran alone; only editing and non-FMU unit tests were performed concurrently. Real-engine integration tests and the FMU regression suite ran only after the benchmark worker exited. A lightweight parent measured that worker's entire process lifetime, including imports, initialization, warm-up, the episode and shutdown.

[Raw bench JSON](../../thermoRL/thermorl-v2/experiments/summit/_bench/task5_bench_20261026T224138_640592Z.json), [environment](../../thermoRL/thermorl-v2/experiments/summit/_bench/environment.txt), [system card](../../thermoRL/thermorl-v2/experiments/summit/SYSTEM.md).

```json
{
  "system": "summit",
  "total_s": 912.5393135249997,
  "raps_s": 3.9649237830744823,
  "fmu_s": 902.9637261998796,
  "episode_fmu_s": 579.4736320299344,
  "instantiation_s": 7.787814560000697,
  "warmup_wall_s": 316.12243659999876,
  "warmup_instantiation_s": 323.91025115999946,
  "warmup_used_s": 7200.0,
  "power_tick_s": 10,
  "power_ticks": 2160,
  "fmu_steps": 2160,
  "switch_required": false,
  "horizon_h": 6,
  "twice_total_s_information_only": 1825.0786270499993,
  "twice_after_warmup_instantiation_s_information_only": 1177.2581247300004
}
```

**D2 PASS: total_s = 912.539 s (15.209 min) <=2700 s. Keep Summit.** The doubled quantities are information only. The unchanged horizon rule gives **6 h**, because `4*total_s >300`. No system switch or C1 rerun occurred.

Every recorded source hash was checked against the worker's immutable start commit `7695c34e5dcd2ad670c22c9bc7e83796b7718014`. Later permitted edits are not misrepresented as the benchmark's executed source. The raw manifest preserves full `git_status_porcelain`: the only dirty path at worker start was the pre-existing ` D docs/prompt.md`.

### D1 rack-power references

| Reference | Idle kW/rack | Peak kW/rack |
|---|---:|---:|
| C1 probes, loss-exclusive | 13.201714285714 | 47.282326530612 |
| RAPS own rack calculation, loss-inclusive | 13.822619047619 | 49.323256802721 |

The new `raps_rack_kw` helper calls `PowerManager.compute_rack_power` on a uniform node state; no rectifier formula was reimplemented. Task 5 compares the actual idle mean to that loss-inclusive reference at the unchanged 0.05 kW tolerance, and exact sums at 1e-6 kW. Those checks pass. Lassen's reference matches its lossless probe bounds exactly. G1, `primary.yaml`, `rack_power_bounds` and `job_increment_kw` remain frozen; the roughly 4% between-tick increment understatement is documented in the system card.

## Verification and exact commands

From `thermoRL/thermorl-v2`:

```bash
uv run pytest tests/integration/test_engine_factory.py tests/integration/test_timing_semantics.py -v
uv run pytest tests/unit/test_bench.py -q
uv run pytest tests/integration/test_engine_factory.py tests/integration/test_timing_semantics.py tests/unit/test_bench.py -v
uv run pytest tests/unit/test_placement.py tests/unit/test_scorers.py -v
uv run pytest tests/unit/test_scheduler_unit.py -v
uv run pytest tests/unit/test_synthetic.py -v
uv run pytest tests/unit/test_coupling.py::test_per_unit_air_temperature_missing_input_key_raises -q
uv run pytest tests/unit/test_coupling.py tests/unit/test_probe_metrics.py -q
# After the isolated bench ended:
uv run pytest tests/unit tests/integration -q
uv run pytest tests/fmu -v
uv run pytest tests/integration/test_timing_semantics.py -v
# After preserving the unapproved Task 8 code as a proposal patch:
uv run pytest tests/unit tests/integration -q
uv run pytest tests/unit -q
uv run pytest tests/integration -q
```

Expected missing-module red runs preceded the new Task 5/6/7/8 implementations. The N1 missing-key test first failed with DID NOT RAISE, then passed after the permitted correction. The draft-only synthetic test command refers to scratch verification before the draft was moved into the proposal patch, not to a test in the committed active suite.

| Verification | Outcome |
|---|---|
| Task 5 focused tests, including D1/D2 | 12 passed |
| Task 6 placement/scorer tests | 8 passed |
| Task 7 allocation-port unit tests | 4 passed; real-engine scheduler tests also pass |
| Active unit suite | **66 passed in 2.18 s** |
| Active integration suite | **22 passed in 3.02 s** |
| Active combined unit/integration | **88 passed in 3.29 s** |
| Current FMU regression tier | **7 passed, 1 xfailed in 130.28 s** |
| Fractional-runtime fixture with exact t=30 assertion | 1 passed |

The FMU regression count excludes the unimplemented vertical-slice test. The historical Task 1.5 test retains its unchanged body and strict XFAIL. Production import boundaries, the FMU backend, frozen G1/primary configuration and protected source directories are unchanged except for the expressly allowed N1 coupling check. No `sim-raps/` or FMU/model patch was made.

Task 5 confirms 12 power ticks in 120 s, stale-but-non-None `power_df` between ticks (references retained for id checking), schedule time 25 and first hot tick **30**, exact rack sum reconciliation, and the required time-limit exception. Task 7 confirms FCFS head-of-line blocking, exact distinct free nodes, REPLAY allocation, policy attributes surviving priming, committed-power updates, power_balance spreading and coolest_rack herding in the mandated short fixtures. These are mechanics tests, not policy-comparison experiments.

## Why execution stops before E10

The current assignment §8 requires escalation for ambiguity affecting metrics or workload semantics. Two concrete decisions remain open; neither is silently resolved by changing an invariant or a workload representation:

1. **Measured `latency_us` versus byte-identical decision files.** The exact decision schema includes real wall-clock latency, which varies. Proposed: retain `latency_us: null` in the canonical decision ledger and store actual per-decision timings in a separate provenance ledger. Keep the byte-identity invariant intact.
2. **Fractional lognormal durations versus RAPS completion ordering.** A narrow fixture confirms the mismatch at t=30 for a job starting at 25 with runtime 4.5 s, while the required integer-duration timing fixture passes. Proposed: explicitly ceil clipped durations to the 1 s engine resolution, identically in Monte Carlo and generated jobs, and document this before E10 preregistration. No RAPS patch or runtime workaround is applied.

Full evidence and requested decisions: [C2 representation clarification proposal](../superpowers/proposals/2026-10-27-c2-reproducibility-clarifications.md). The prepared Task 8 source/tests are reviewable as a patch rather than an unapproved active implementation.

## E10 / C2 status

All six E10 invariants are **NOT RUN**, not PASS or FAIL. No E10 summary, workload cache, policy run, heatmap, thermal metric or realised-utilisation number has been fabricated. No G4 matrix projection from E10 measurements is available yet. No workload powers, thermal assumptions, controller definitions, horizon, seed, utilisation target, acceptance thresholds or historical assertions were changed to obtain a result.

## Anomalies (FACT / INFERENCE)

- **FACT:** The idle benchmark completed with finite checked outputs and maximum episode coolant 40.182142 °C. This is an idle bench result, not E10.
- **FACT:** RAPS emitted its existing missing-Summit-dataloader warning at engine construction. It subsequently ran the injected empty workload with cooling/UI/file output disabled and completed all 2160 ticks. No patch was needed.
- **FACT:** The user-owned `docs/prompt.md` deletion existed before sync and remains unstaged and untouched. Full porcelain status is preserved, not explained away as only generated artifacts.
- **FACT:** The fractional-runtime failure is reproduced at the expected power tick. No experiment was used to tune a duration law.
- **INFERENCE:** Explicitly separating measured latency and explicitly declaring second-resolution runtimes are sufficient, bounded representation decisions for proceeding. Approval is required; no additional thermal characterization, history, predictor-selection, placement or RL experiment is proposed.

## Next step after steering

Record the two decisions, finish Task 8 under the approved representation, preregister E10, and implement Task 9 using fresh subprocesses and the unchanged six-invariant gate. Then produce and review actual C2 evidence. No Task 10–12 or other experimental phase has begun.
