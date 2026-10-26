# C1 — FMU selection and physics

**Date:** 2026-10-27. **Status: Tasks 1–4 complete; mandatory CHECKPOINT C1 stop for review.** Primary: **summit**. No Task 5 or later implementation has begun.

## Commits and provenance

Branch `feat/parasparam-demo` was created from the clean, current `feat/thermorl2-phase0-env` at `439cae9ef559b2d05e8ba1b317419aaffb04194e`.

| Work | Commit |
|---|---|
| Task 1: approved option-B backend closure, environment, scaffold | `a7a0c1a` |
| Task 2: system/power/ambient/provenance helpers, smoke | `554af93` |
| E02/X01 preregistration and approved timing clarification | `c6e127a` |
| Tested immutable probe/selection implementation | `41c6585` |
| Task 3: three-FMU screen and selection evidence | `2d14161` |
| G1/G3 preregistration on selected primary | `6f88579` |
| Task 4: primary physics results and frozen config | `2bd9b96` |

The G2 probes executed implementation `41c658563eb4a51b7a30f0d2b1650e95130e66f2`. G1/G3 executed at preregistration commit `6f88579`, with the same source hashes. Manifests record exact git SHA/dirty flags, every implementation-file hash, environment, FMU/workload/config hashes, backend=fmu, policy/seed (not applicable) and timings. Concurrent artifact writes can make `dirty=true`; this is preserved, and source hashes were independently verified. All probes ran on Linux x86-64 / Python 3.12.14, one FMU per process, after SHA verification.

## X01: mechanical primary selection

| System | Δ °C | Class | C_s min / 6 h | Sane | Eligible |
|---|---:|---|---:|---|---|
| lassen | 2.036319592756 | GO | 0.304157671949 | True | True |
| summit | 6.234888984342 | GO | 21.912337247551 | True | True |
| marconi100 | 0.054796806701 | STOP | 0.394916788800 | True | True |

**Primary: summit; runner-up: lassen; tie-break applied: False.** Summit has the largest Δ; its 80% threshold is 4.987911187473 °C, above Lassen's Δ. Ranking: summit → lassen → marconi100. The chosen class is GO, so the X01 STOP condition does not trigger. Marconi100's individual STOP is retained as a negative result.

C_s uses the original measured FMU-only cost and the frozen 1.5 RAPS-overhead assumption. The actual Task 5 idle engine/FMU cost guard is still pending.

Experiment READMEs: [X01](../../thermoRL/thermorl-v2/experiments/cross_system/X01_fmu_selection/README.md), [Lassen E02](../../thermoRL/thermorl-v2/experiments/lassen/E02_g2_packed_vs_spread/README.md), [Summit E02](../../thermoRL/thermorl-v2/experiments/summit/E02_g2_packed_vs_spread/README.md), [Marconi100 E02](../../thermoRL/thermorl-v2/experiments/marconi100/E02_g2_packed_vs_spread/README.md). [Cross-system figure](../../thermoRL/thermorl-v2/experiments/cross_system/X01_fmu_selection/plots/g2_cross_system.png).

## G1: five-level uniform-load characterization

Initial snapshot mean coolant is 39.028228453615 °C. Every branch restored the same saved state, with exact equality of coolant, extras and globals checked before stepping. The 7200 s warm-up is capped/preconditioned, **not settled**. Final-window averages are fixed-horizon operating proxies, not certificates of equilibrium.

Holding the same idle power after that snapshot still increases the final-window mean by **1.013306769687 °C** over the subsequent 3 h. Higher-load traces are also still evolving at the endpoint; the prescribed fit and empirical crossings retain that finite-horizon limitation.

| f | Rack kW | Final mean °C | Min rack mean °C | Max rack mean °C | Signed final change °C | First t63 s |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 13.201714286 | 40.041535223 | 40.041535216 | 40.041535231 | 1.013306770 | 4930.0 |
| 0.25 | 21.721867347 | 44.058848114 | 44.058848112 | 44.058848115 | 5.030619660 | 3550.0 |
| 0.5 | 30.242020408 | 51.579892033 | 51.579892032 | 51.579892034 | 12.551663579 | 4050.0 |
| 0.75 | 38.762173469 | 59.165656596 | 59.165656596 | 59.165656596 | 20.137428142 | 4130.0 |
| 1 | 47.282326531 | 66.792187753 | 66.792187753 | 66.792187754 | 27.763959299 | 4170.0 |

- Linear fit: **a = 27.975385727123 °C**, **b = 0.805245082436 °C/kW**, **R² = 0.989167647689**.
- Frozen empirical **tau_s = 4050.0 s**: median first t63 over f=.25/.5/.75. It is protocol-specific, not a reinstated 500–1000 s acceptance bound or proof of first-order dynamics.
- Frozen **t_hot_c = 63.304922110353 °C**, the fit at f=.9.
- **40 °C reached: True; 45 °C reached: True**. The 45 °C assumption was retained.
- f=1 final-window rack-mean spread: **8.98012331163e-10 °C**.

[Summit E01 README](../../thermoRL/thermorl-v2/experiments/summit/E01_g1_uniform/README.md), [summary](../../thermoRL/thermorl-v2/experiments/summit/E01_g1_uniform/results/summary.json), [trajectories and fit](../../thermoRL/thermorl-v2/experiments/summit/E01_g1_uniform/plots/g1_trajectories.png). `thermorl2/experiments/configs/primary.yaml` points to this immutable summary and preserves H=600 s.

## G3: room-air lever decision

**NOT_USABLE**: affected final-30-min paired mean **0.538986028132 °C**, below 1.0 °C; unaffected mean **0.101837403880 °C**. Sanity passed. This is a simulated **what-if (not observed summit behaviour)**.

The specified room-air what-if is dropped. The [full list of 62 candidate CDU parameters](../../thermoRL/thermorl-v2/experiments/summit/E03_g3_room_air/results/candidate_cdu_parameters.txt) is preserved and independently checked against the exact causality/variability/name filters. **None were applied.** No substitute lever, parameter tuning or additional experiment was introduced.

[Summit E03 README](../../thermoRL/thermorl-v2/experiments/summit/E03_g3_room_air/README.md), [summary](../../thermoRL/thermorl-v2/experiments/summit/E03_g3_room_air/results/summary.json), [paired trajectories](../../thermoRL/thermorl-v2/experiments/summit/E03_g3_room_air/plots/g3_trajectories.png).

## Reproducibility and independent audits

- Lassen's retained independent rerun has byte-identical scientific-summary and thermal-series files. Warm-up, CDU/global ledger, branch-root observations and input bytes are also identical. Full summaries differ in measured timing fields, as explicitly approved before preregistration. X01 uses the original cost, never the faster rerun's cost. [Comparison](../../thermoRL/thermorl-v2/experiments/lassen/E02_g2_packed_vs_spread/provenance/rerun_1.json), [full thermal audit](../../thermoRL/thermorl-v2/experiments/lassen/E02_g2_packed_vs_spread/provenance/rerun_1_full_thermal_audit.json).
- Independent G2 audits reproduce all reported primary numbers, time grids and power sums. The largest total-power summation error is 7.28e-12 kW; summary recomputation differences are <=7.11e-15 °C. No threshold was widened.
- Summit G3's control exactly reproduces original Summit G2 spread, and their warm-up ledgers are byte-identical. This reuses existing executions, with no extra characterization run. [Audit](../../thermoRL/thermorl-v2/experiments/summit/E03_g3_room_air/provenance/independent_ledger_audit.json).
- G1's independent audit and warm-up/control comparison are recorded in its [provenance](../../thermoRL/thermorl-v2/experiments/summit/E01_g1_uniform/provenance/).
- Experiment configs and preregistered scientific sections were checked against their introducing commits. Raw results were never overwritten; the Lassen rerun is retained separately. Artifact/run directories are below 25 MB.

## Wall times (measured, seconds)

| Probe | FMU calls | Total wall |
|---|---:|---:|
| Lassen G2 | 16.221742504 | 18.217527883 |
| Marconi100 G2 | 21.062228736 | 22.922057085 |
| Summit G2 | 1168.657986536 | 1172.611832356 |
| Lassen G2 rerun | 15.575868315 | 17.419459398 |
| Summit G1 | 1784.156832484 | 1792.660297044 |
| Summit G3 | 1193.584842169 | 1201.512794927 |

RAPS engine runtime and scheduling latency are not applicable: these are FMU-only probes using RAPS configuration/power helpers. G2 was three parallel processes; G1/G3 were two parallel processes. Timings are machine- and workload-specific, including co-scheduling effects; they do not replace Task 5's engine bench.

## Tests and preserved historical failure

- Task 1 baseline: **19 passed**; option-B FMU gate/lifecycle suite: **4 passed, 1 xfailed**.
- Task 2 prescribed combined verification: **33 passed**; unit/integration including RAPS coupling regression: **31 passed**.
- New vector, classification, selection, signed-crossing and paired-metric tests were written and observed failing before implementation. Subsequent unit/integration: **55 passed in 1.75 s**.
- Final full-suite verification: **62 passed, 1 xfailed in 130.38 s**.
- Historical physical-response test retains its complete body and 500–1000 s bound under `xfail(strict=True)`; the unresolved physical premise has not become a passing physical test. Option B verifies direct/backend agreement and matching restore deviations, preserving the measured **0.000143434446 °C** restore limitation.

## Exact experiment commands

Run from `thermoRL/thermorl-v2` with Python 3.12 via uv. The three G2 commands were launched concurrently as separate processes:

```bash
uv run python -m thermorl2.experiments.probes g2 --system lassen --out experiments/lassen/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.probes g2 --system marconi100 --out experiments/marconi100/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.probes g2 --system summit --out experiments/summit/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.probes g2 --system lassen --out experiments/lassen/E02_g2_packed_vs_spread/provenance/rerun_1_data --verify-against experiments/lassen/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.select_fmu --out experiments/cross_system/X01_fmu_selection experiments/lassen/E02_g2_packed_vs_spread/results/summary.json experiments/summit/E02_g2_packed_vs_spread/results/summary.json experiments/marconi100/E02_g2_packed_vs_spread/results/summary.json
# These two ran as separate parallel processes after G1/G3 preregistration:
uv run python -m thermorl2.experiments.probes g1 --system summit --out experiments/summit/E01_g1_uniform
uv run python -m thermorl2.experiments.probes g3 --system summit --out experiments/summit/E03_g3_room_air
```

Environment and verification commands:

```bash
# Repo root, on feat/thermorl2-phase0-env:
git pull --ff-only
git checkout -b feat/parasparam-demo
sha256sum models/POWER9CSM/fmus/lassen.fmu models/POWER9CSM/fmus/summit.fmu models/POWER9CSM/fmus/marconi100.fmu
# From thermoRL/thermorl-v2:
uv lock
uv sync
uv run pytest tests/unit tests/integration -q
uv run pytest tests/fmu -v
uv run pytest tests/fmu -v --basetemp=/tmp/thermorl2-c1-option-b-20261027
uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v -s
uv run pytest tests/unit/test_probe_vectors.py tests/unit/test_select_fmu.py -v
uv run pytest tests/unit/test_probe_metrics.py -v
uv run pytest tests/unit/test_probe_vectors.py tests/unit/test_select_fmu.py tests/unit/test_probe_metrics.py -v
uv run pytest tests/unit/test_select_fmu.py::test_negative_contrast_still_selects_stop_candidate -q
uv run pytest tests/unit tests/integration -q
uv run pytest -q
```

The initial missing-module red runs and the two explained implementation/test mistakes were retained in the work history. uv initially required execution approval for its read-only sandbox cache path; prescribed runs then succeeded with approval.

## Anomalies and interpretation

- **FACT:** Task 3 originally combined full-summary byte identity with measured timings. Bipin approved the deterministic-content comparison before any G2 execution; `c6e127a` records that clarification. Full-summary byte identity is explicitly false; both full summaries are preserved.
- **FACT:** An extra Task 2 test assumed positive switch overhead, while Summit sets switch power to zero. That unsupported test assumption was corrected. A new packed-vector test caught a 7.1e-15 kW floating reconstruction overshoot; full racks are assigned the exact peak bound. A negative-result selection test caught an empty tie pool; the candidate is now always retained. No experimental threshold was changed.
- **FACT:** Summit's sampled G2 peak is 61.087591 °C; all three G2 sanity checks passed. Lassen's earlier near-40 °C behavior does not transfer numerically to Summit. G1 operating values and the fixed 45 °C comparison are reported above without tuning.
- **FACT:** G3 misses its threshold and the what-if is dropped. Its modest unaffected response is reported, without a strong spatial-coupling claim.
- **INFERENCE:** Summit offers the stronger measured packing contrast under the frozen protocol. This supports the selected demo regime, while benefit beyond power balancing remains untested. G1's finite-horizon fit does not prove universal first-order dynamics, and no history or RL benefit is claimed.

## Stop and proposed next step

**Mandatory C1 stop for steering.** Review X01, the Summit operating range/fit and the NOT_USABLE G3 decision. If approved, execute Task 5 as written: engine factory, power/timing tests and the primary's measured cost bench, including its post-selection guard and horizon rule. Then pursue the existing vertical slice. No further history, predictor-selection or placement experiment is a prerequisite. No `sim-raps/` or `docs/prompt.md` changes, FMU tuning, acceptance-bound tuning, scheduler implementation or RL work occurred in this assignment.
