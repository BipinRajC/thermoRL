# C2 preflight representation decisions — pending approval

**Status: proposed, not approved. No E10 experiment or workload has been produced.** D1/D2 are approved and implemented separately. The isolated Summit bench passed D2; these questions do not change that result or the selected system.

The current assignment requires escalation for ambiguity affecting metrics or workload semantics. The following two concrete representations need a decision before E10 preregistration and execution. No thermal model, policy, input-power reference, G1 parameter, acceptance threshold, seed, utilisation, horizon, warm-up duration or historical test has been changed to resolve them.

## R3 — measured latency versus byte-identical decision logs

The frozen decision-row schema contains `latency_us`. The scheduler currently measures it using `perf_counter_ns()`. Such wall-clock timings vary across fresh executions even when every decision is identical. E10 simultaneously requires a byte-identical full `decisions.jsonl`. Arrays rounded to six decimals do not remove timing variation.

**Proposed decision:** keep every required decision key, but write `latency_us: null` in the deterministic decision ledger. Preserve actual measured per-decision latency in a separate `provenance/decision_latency.jsonl`, keyed by decision index, job id and simulation time. Keep the full-file byte-identity invariant unchanged. Subsequent latency metrics use the measured timing ledger; null never means zero cost.

The scheduler's current allocation sink still receives real measured latency. The proposed separation would occur at the future runner's persistent logging boundary. It has not been applied or tested against an E10 run. If measured latency must remain inside the canonical decision rows instead, the determinism requirement needs a different explicit decision; it will not be weakened silently.

## R4 — continuous sampled durations versus the integer-second engine

**FACT (narrow integration fixture):** a full-rack job starting at t=25, with `expected_run_time=4.5` s and a sufficiently large time limit, raises RAPS's `Job should have ended in replay!` at t=30. RAPS completion detection consults the preceding second's `current_run_time`, while the power tick updates it and checks for overrun. The required integer-duration arrival fixture (600 s runtime) still schedules at 25 and first becomes hot at 30.

Evidence: `tests/integration/test_timing_semantics.py::test_fractional_runtime_crossing_power_tick_raises`. This fixture uses no FMU and ran only after the isolated bench exited. No `sim-raps/` edit is proposed.

**Proposed decision:** after sampling the frozen lognormal distribution and clipping to [300,14400] s, represent runtime as `ceil(runtime)` integer seconds. Apply the same representation in the one-million-sample Monte Carlo estimate. Preserve median=1800 s, sigma=0.8, clip bounds, node/CPU/GPU distributions, utilisation target, Poisson construction, seed and `time_limit=ceil(1.5*represented_runtime)`. Record the quantization and RNG draw order in workload metadata and the E10 preregistration before any run.

The complete proposed Task 8 implementation/tests are preserved as [a draft patch](2026-10-27-c2-runtime-representation-draft.patch), not installed in the runtime package. The draft's unit and job-field tests passed in scratch verification. It has not generated any E10 cached workload or supplied jobs to a closed-loop experiment. Applying it requires approval of the representation above. `git apply --check` passed.

## Requested steering

1. Approve null canonical latency plus the separate measured timing ledger, or specify the intended alternative.
2. Approve the explicit integer-second runtime representation, or specify the intended alternative.

After those decisions are recorded, finish Task 8, preregister E10 with exact input/logging conventions, implement Task 9, and execute the same prescribed packing/power_balance paired mechanics gate. No additional research experiment is a prerequisite.
