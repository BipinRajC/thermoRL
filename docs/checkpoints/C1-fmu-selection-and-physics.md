# C1 — FMU selection and physics: preparation complete, gate pending

**Date:** 2026-10-27. **Status: C1 NOT COMPLETE; stopped before Task 3 pending a required clarification.** Tasks 1–2 are complete. G2, X01, G1 and G3 have not run. No primary FMU has been selected.

## Commits and scope

- Source branch: `feat/thermorl2-phase0-env`, `439cae9ef559b2d05e8ba1b317419aaffb04194e`; `git pull --ff-only` reported already up to date.
- Work branch: `feat/parasparam-demo`.
- Task 1: `a7a0c1a` — option-B backend closure, lock refresh, experiment scaffold and legacy index.
- Task 2: `554af93` — three-system registry, per-unit room air, power/provenance helpers and per-system smoke subprocesses.

The historical physical-response test body and 500–1000 s bound are unchanged under strict XFAIL. FMU and backend stepping semantics were unchanged. No `sim-raps/` or `docs/prompt.md` changes were made. Production import boundaries were checked with an AST scan.

## Required clarification before G2 preregistration/execution

Task 3 requires G2 `results/summary.json` to contain independently measured `fmu_s_per_sim_h` and `projected_closed_loop_min_6h` (plan lines 237–243). It also requires a rerun to confirm a **byte-identical `summary.json`** (line 273). Wall-clock measurements vary across otherwise identical executions. These requirements cannot jointly serve as a reproducibility assertion without defining how timing fields are treated.

Concrete mechanical evidence: Lassen's two smoke runs had identical reported temperatures and rack power bounds, but wall times 2.453431820000 and 2.479606414000 s. Summit's were 73.791710919000 and 69.812412241000 s. These smoke measurements are not G2 outcomes or selection costs.

**Proposed clarification, awaiting approval:** independently run Lassen G2 twice; require byte-identical canonical thermal/scientific summary content and identical thermal-series values; preserve each full summary and timing measurement without overwriting; record the comparison and excluded timing keys in `provenance/rerun_1.json`. Use the original G2 run's measured cost for X01. All thresholds, classification, workloads, ambient settings, horizons and selection rules remain frozen. Do not claim full-summary byte identity if only the deterministic projection matches.

The kickoff brief freezes preregistered items and requires stopping for a needed change. No G2 README or protocol has been silently amended, and no G2 result has been generated. This is a stop before C1 completion, not a successful C1 review.

## Verification

| Check | Exact outcome |
|---|---|
| Task 1 baseline unit/integration | 19 passed in 1.78 s |
| Original FMU suite before approved changes | 3 passed, 2 failed in 21.13 s; known restore identity failure and historical t63 = 1240 s |
| Task 1 FMU verification under option B | 4 passed, 1 xfailed in 21.01 s |
| Task 2 initial red run | 3 collection errors for missing planned modules |
| Task 2 initial implementation run | 32 passed, 1 failed in 85.10 s; extra test incorrectly assumed positive switch power on Summit |
| Corrected unit/integration, including RAPS equality regression | 31 passed in 1.43 s |
| Corrected complete Task 2 command | 33 passed in 81.14 s, including all three smoke subprocesses |

Option-B maximum temperature restore deviation: **0.00014343444621545132 °C**. Direct/backend comparisons and restore-delta comparisons retain `rtol=0, atol=1e-6`. Snapshot and warm-up duration are exactly 7200 s. This is capped preconditioning, not settled initialization.

Closure evidence: [E00 legacy index](../../thermoRL/thermorl-v2/experiments/lassen/E00_legacy_task15/README.md) and [option-B manifest](../../thermoRL/thermorl-v2/experiments/lassen/E00_legacy_task15/provenance/option_b_manifest.json).

## Task 2 measured system values (FACT)

| System | Idle rack kW | Peak rack kW | Smoke coolant min/max °C | Smoke wall s, first / repeat | Smoke outcome |
|---|---:|---:|---|---|---|
| Lassen | 10.857680000000 | 34.428680000000 | 36.609148984896 / 36.609149050257 | 2.453432 / 2.479606 | finite; 44 units |
| Summit | 13.201714285714 | 47.282326530612 | 37.540367295108 / 37.540369062942 | 73.791711 / 69.812412 | finite; 257 units |
| Marconi100 | 12.365200000000 | 38.555200000000 | 36.856428549590 / 36.856428708161 | 2.848765 / 2.889859 | finite; 49 units |

Every smoke verified the exact spec §3.1 SHA before instantiation, used 290 K ambient and 600 s capped preconditioning at its own power tick, and ran in a separate process. Details: [Lassen](../../thermoRL/thermorl-v2/experiments/lassen/SYSTEM.md), [Summit](../../thermoRL/thermorl-v2/experiments/summit/SYSTEM.md), [Marconi100](../../thermoRL/thermorl-v2/experiments/marconi100/SYSTEM.md).

## C1 experiment outcomes

| System | G2 Δ °C | Class | C_s min / 6 h | G2 sanity |
|---|---|---|---|---|
| Lassen | not run | unclassified | not measured | not evaluated |
| Summit | not run | unclassified | not measured | not evaluated |
| Marconi100 | not run | unclassified | not measured | not evaluated |

Primary, runner-up and tie-break: pending X01. G1 levels/fit/τ/t_hot/40 °C/45 °C outcomes: pending selection. G3 decision and candidate CDU parameter list: pending selection. Smoke success alone establishes neither G2 eligibility nor G2 sanity across the prescribed horizon.

## Exact commands

From repository root:

```bash
git pull --ff-only
git checkout -b feat/parasparam-demo
sha256sum models/POWER9CSM/fmus/lassen.fmu models/POWER9CSM/fmus/summit.fmu models/POWER9CSM/fmus/marconi100.fmu
```

From `thermoRL/thermorl-v2` (Python 3.12.14, Linux x86-64):

```bash
uv lock
uv sync
uv run pytest tests/unit tests/integration -q
uv run pytest tests/fmu -v
# Apply only the approved option-B test changes, then:
uv run pytest tests/fmu -v --basetemp=/tmp/thermorl2-c1-option-b-20261027
# Task 2 red run before implementation:
uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v
# Initial implementation run; identified the Summit test assumption:
uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v -s
# Correct the test assumption, then:
uv run pytest tests/unit tests/integration -q
uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v -s
```

`uv` initially failed because the sandbox made `/home/bipin/.cache/uv` read-only. The prescribed commands succeeded with execution approval. This was an environment permission issue, not a test result. FMU tests used fresh subprocesses as specified; no FMU was used on a different machine.

## Anomalies and interpretation

- **FACT:** Summit has `power_switch: 0`; the extra positive-overhead test assumption was corrected, leaving the specified idle/peak formula unchanged.
- **FACT:** repeated smoke temperatures and power bounds matched; wall times differed.
- **INFERENCE:** timing metadata must be handled explicitly in the G2 determinism assertion. No inference about G2 effect size or primary system can be made from the smoke results.

## Proposed next step

Approve or clarify the G2 reproducibility comparison above. Then execute Tasks 3–4 as planned, complete this C1 report with X01/G1/G3 evidence, push, and stop for checkpoint review. No Task 5 or later work has begun.
