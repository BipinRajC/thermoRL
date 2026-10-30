# C3 prelaunch status — awaiting determinism evidence-scope decision

**Date:** 2026-10-30. **Branch:** `feat/parasparam-demo`. This is a prelaunch status, not CHECKPOINT C3 and not a G4 result. No E11 FMU process has been started.

## Completed

- `50ffa30`: Task 10, strict-window ledger metrics, S1 distribution metrics, mixed interval/energy semantics, censoring, timing-ledger latency, rounded-context counterfactuals and separate self-reproduction, driving-tick max-rack residency. Records Bipin's relayed S1/S2 and launch conditions in the plan addendum.
- `3616c78`: Task 11, horizon-aware plots/animations and report, frozen half-degree-in-every-seed G4 rule; tested on existing E10 ledgers. Added G2 figure from existing raw data.
- `c0cced6`: Task 12 preparation, per-seed workload selection, mandatory sidecar horizon check before backend instantiation, immutable file inventory, archived failures, explicit/capped reviewed retry support (no automatic retry), complete latency/FMU scope text, exact executed-vs-preregistered configuration checks.
- Independent read-only implementation review found four engineering issues; all were corrected with regression coverage and rechecked. No outstanding implementation blocker was reported.

## Verification

`uv run pytest tests/unit tests/integration -q`: **124 passed**. Tests use existing E10/G2 ledgers and temporary orchestration fixtures; they launch no real FMU. The historical physical-response test, FMU backend semantics, policies, primary config, G1 parameters, workload generator, RAPS and models are unchanged. No new full FMU-suite execution is claimed.

Three authorized workloads generated with `uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_synthetic.yaml --seed <s> --prepare-workload`, in the locked Arch Python 3.12 environment:

| Seed | Offered jobs | SHA-256 |
|---|---:|---|
| 1 | 4589 | `c9bd815fe21806930edf225f6e3c443fcb4e8b49e905edb985190f77de967c27` |
| 2 | 4688 | `d2a64253d18fc92ee3c6bb42eec3189e5cc5ffd50743e3c71fc1dc4b88100b91` |
| 3 | 4660 | `7e06a12548f70d5b6fbd8d3edeacbccaafbe8486dfdea48caa5533696692aa0d` |

All sidecars record 21600 s, rho 0.6, Summit 4626 nodes and 6 GPUs/node, unchanged generator-source hash, representation/MC/RNG provenance and package versions. Parquet SHA verification passes. They are referenced by `workload.by_seed` in `g4_synthetic.yaml`.

## Required clarification before final preregistration/launch

The assignment simultaneously requests exactly the frozen 5-policy × 3-seed matrix, all six invariants per seed, and no extra experiments. Invariant 3 is full-file decision byte identity plus interval-value identity across repeated executions of the same configuration/policy/seed. A matrix containing each configuration only once cannot directly remeasure it. The accepted E10 packing rerun already provides direct two-hour seed-1 evidence.

An asynchronous question is pending with Bipin:

1. Keep exactly **15 E11 runs**, explicitly cite **inherited E10 determinism evidence**, and state that E11 six-hour determinism was not independently rerun; or
2. Authorize **three additional packing determinism reruns**, one per E11 seed, preserving outputs under provenance. This tests the E11 configuration for packing; it still does not constitute a repeated execution of every policy.

Neither choice changes the frozen G4 metric, half-degree rule, policies, workload methodology, rho, seeds, horizon, warm-up, G1 or FMU. The choice controls evidence scope and authorized run count, so it must be recorded before E11 is committed as preregistered. The current report supports a labelled evidence record but no evidence choice has been made.

## Next step after the decision

Finish and commit E11 README/config (S1, S2 verbatim, all six invariants and exact evidence scopes, immutable workload SHAs, metrics, commands). Launch the authorized matrix with three workers; report first-wave timings and per-seed invariants. Generate the frozen G4 report and C3, push and stop. No Task 13–16, new policy, new research experiment, tuning or RAPS patch is authorized.

Existing local `docs/prompt.md` deletion and untracked `docs/prompt-opus5-5-C2.md` are preserved and excluded from these commits.
