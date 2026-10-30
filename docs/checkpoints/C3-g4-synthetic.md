# C3 — Frozen G4 synthetic policy evaluation

**Date:** 2026-10-30. **Status:** CHECKPOINT C3; stop for review. **System:** Summit FMU. **Execution SHA:** `6ee93c4` (preregistration); code corrections `ea3a26d`. [E11 README](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/README.md).

## Outcome and primary metric

**FACT/DERIVED:** `value_beyond_power = false`. Frozen outcome: **no material value on the homogeneous twin**. The decision uses only maxrack_mean_c and PB−TP ≥ 0.5 °C in every seed, at full precision. Secondary metrics do not alter it.

Mean max-rack coolant (°C), strict 3600 < t_s <= 21600, 1800 endpoint samples:

| Seed | packing | node_balance | power_balance | coolest_rack | thermal_predictive |
|---|---|---|---|---|---|
| 1 | 54.070216 | 53.883515 | 54.330429 | 53.534760 | 53.987934 |
| 2 | 54.177058 | 54.094552 | 54.137678 | 54.123498 | 54.284869 |
| 3 | 54.122798 | 53.559813 | 53.775784 | 53.780430 | 53.846649 |

| Seed | power_balance − thermal_predictive (°C) | packing − thermal_predictive (°C) | ≥0.5 °C beyond power? |
|---|---|---|---|
| 1 | 0.342495 | 0.082282 | False |
| 2 | -0.147190 | -0.107811 | False |
| 3 | -0.070865 | 0.276150 | False |

Machine-readable: [decision.json](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/decision.json), [summary.json](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/summary.json), [all metrics CSV](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/metrics.csv).

## Work completed and commands

Earlier Tasks 10/11: `50ffa30`, `3616c78`. Launch preparation/workloads: `c0cced6`, `552e9b8`. Approved review fixes and inherited-scope decision: `ea3a26d`. E11 preregistration: `6ee93c4`, before any E11 process. E11 results: `ceb2c98`. This checkpoint is committed separately after execution; see git history.

Exactly 15 fresh-process FMU episodes, 5 frozen policies × seeds 1–3, rho 0.6, nominal 290 K ambient, 6 h, three workers. Each uses a 7200 s capped warm-up, not a settled state. No smoke run, repeat, retry, policy/input change or RAPS patch.

Cwd `thermoRL/thermorl-v2`:

```bash
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_synthetic.yaml --workers 3
uv run python -m thermorl2.experiments.evidence experiments/summit/E11_g4_synthetic
uv run python -m thermorl2.experiments.report experiments/summit/E11_g4_synthetic --evidence experiments/summit/E11_g4_synthetic/provenance/determinism_evidence.json
uv run pytest tests/unit tests/integration -q
```

**Tests:** 112 unit + 27 integration = **139 passed** before launch; the final non-FMU regression recheck also passed **139 tests in 17.06 s**. [Exact output](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/non_fmu_tests.txt) and [artifact verification](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/verification.json). No new full FMU pytest-suite execution is claimed; the historical strict-XFAIL test body/bounds remain unchanged. The actual E11 matrix is the real-FMU verification in this phase.

## Invariants and determinism evidence scope

| Seed | Inv 1: power+starts | Inv 2: allocation | Inv 3: evidence status | Inv 4: power sum | Inv 5: steps+clock | Inv 6: provenance | Max absolute IT difference (kW) |
|---|---|---|---|---|---|---|---|
| 1 | True | True | inherited_not_remeasured | True | True | True | 2.728e-12 |
| 2 | True | True | inherited_not_remeasured | True | True | True | 2.728e-12 |
| 3 | True | True | inherited_not_remeasured | True | True | True | 2.728e-12 |

All directly measured invariants pass. **Invariant 3 is accepted only within the approved evidence scope, not as full E11 repeatability verification.**

- INHERITED for all seeds: accepted E10 packing seed1 two-hour same-config fresh-process rerun; covers that E10 configuration only.
- NEW for seed1 only: packing and power_balance reproduce E10 canonical decision lines for t_s < 7200 byte-for-byte and interval values for t_s <= 7200 exactly. No additional run.
- Seeds 2–3 have no new determinism measurement. All statuses are inherited_not_remeasured. No six-hour E11 policy/seed is repeated, including the temperature-reading policies.

[Per-seed invariants](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/invariants.json), [new prefix result](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/prefix_vs_E10.json), [SHA-sealed evidence](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/determinism_evidence.json). Evidence is separate from launch config. The experiment config and launch config remain byte-identical; pinned inputs, frozen README sections and execution-source hashes are audited.

## S1 descriptive metrics and attribution

S1 uses the same strict window; population std per tick, hottest 26 racks per tick. These are descriptive, with no new criterion. **DERIVED:** thermal_predictive has lower rack-temperature standard deviation and lower hottest-decile mean than power_balance in all three seeds. No success decision is assigned to these secondary metrics.

| Run | Rack T std (°C) | Hottest 26 mean (°C) | Rack kW std |
|---|---|---|---|
| packing_seed1 | 3.747282 | 51.400261 | 9.622002 |
| node_balance_seed1 | 2.217128 | 50.647423 | 7.077326 |
| power_balance_seed1 | 2.175249 | 50.681093 | 6.969511 |
| coolest_rack_seed1 | 1.762447 | 49.980419 | 7.798192 |
| thermal_predictive_seed1 | 1.801660 | 50.143567 | 7.252797 |
| packing_seed2 | 3.845735 | 51.947091 | 9.770287 |
| node_balance_seed2 | 2.270340 | 50.958578 | 6.940780 |
| power_balance_seed2 | 2.173668 | 51.000379 | 6.721737 |
| coolest_rack_seed2 | 1.815888 | 50.373661 | 7.642729 |
| thermal_predictive_seed2 | 1.855072 | 50.481702 | 7.143194 |
| packing_seed3 | 3.692278 | 51.382895 | 9.484795 |
| node_balance_seed3 | 2.087067 | 50.444726 | 6.720345 |
| power_balance_seed3 | 1.977370 | 50.332038 | 6.395488 |
| coolest_rack_seed3 | 1.665736 | 49.761774 | 7.471056 |
| thermal_predictive_seed3 | 1.683078 | 49.868605 | 6.865811 |

| Run | Most frequent argmax rack | Share of window ticks | Top resident job IDs: fraction of all argmax ticks |
|---|---|---|---|
| packing_seed1 | 77 | 28.500% | 859: 25.1%, 184: 23.4%, 2229: 15.4% |
| node_balance_seed1 | 181 | 27.222% | 184: 23.4%, 590: 19.2%, 1410: 11.4% |
| power_balance_seed1 | 181 | 26.000% | 184: 23.4%, 3501: 14.7%, 1910: 9.8% |
| coolest_rack_seed1 | 151 | 24.500% | 184: 23.4%, 1745: 17.6%, 1410: 12.4% |
| thermal_predictive_seed1 | 194 | 25.500% | 184: 23.4%, 1745: 17.6%, 1266: 14.4% |
| packing_seed2 | 150 | 22.333% | 3102: 22.3%, 614: 18.4%, 2297: 16.3% |
| node_balance_seed2 | 91 | 35.889% | 614: 34.9%, 974: 18.0%, 2160: 16.3% |
| power_balance_seed2 | 46 | 37.056% | 614: 34.9%, 2160: 15.1%, 1804: 11.5% |
| coolest_rack_seed2 | 84 | 36.556% | 614: 34.9%, 3102: 20.2%, 2160: 12.6% |
| thermal_predictive_seed2 | 108 | 36.444% | 614: 34.9%, 3102: 25.9%, 2160: 15.7% |
| packing_seed3 | 86 | 32.167% | 467: 32.2%, 413: 29.9%, 992: 18.4% |
| node_balance_seed3 | 202 | 27.389% | 413: 25.3%, 3324: 17.3%, 1784: 12.2% |
| power_balance_seed3 | 189 | 27.722% | 413: 23.7%, 3324: 23.2%, 1659: 15.7% |
| coolest_rack_seed3 | 54 | 30.056% | 413: 29.1%, 1659: 16.8%, 2777: 16.3% |
| thermal_predictive_seed3 | 113 | 27.944% | 413: 26.3%, 2777: 18.1%, 3197: 13.4% |

Attribution uses endpoint argmax (ties to lower rack index), with resident jobs at the driving RAPS tick, t_s−10. Resident fractions indicate coexistence, not isolated causal contributions. Complete per-tick rack/temperature/power/job IDs and rack shares: [max_rack_attribution.json](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/max_rack_attribution.json).

## Disagreement and self-reproduction

| Run | PB vs TP disagreement | Policy self-reproduction | Latency mean/p95 (µs) |
|---|---|---|---|
| packing_seed1 | 0.751798 | 1.000000 | 620.5 / 993.7 |
| node_balance_seed1 | 0.700588 | 1.000000 | 630.4 / 1000.6 |
| power_balance_seed1 | 0.866638 | 0.991501 | 642.1 / 997.6 |
| coolest_rack_seed1 | 0.891698 | 0.904772 | 628.9 / 979.3 |
| thermal_predictive_seed1 | 0.960994 | 0.948137 | 643.2 / 1029.0 |
| packing_seed2 | 0.749147 | 1.000000 | 602.7 / 970.4 |
| node_balance_seed2 | 0.633319 | 1.000000 | 617.6 / 969.9 |
| power_balance_seed2 | 0.858788 | 0.992321 | 650.8 / 1005.3 |
| coolest_rack_seed2 | 0.880759 | 0.899744 | 627.6 / 966.5 |
| thermal_predictive_seed2 | 0.941340 | 0.948166 | 653.6 / 1043.0 |
| packing_seed3 | 0.712017 | 1.000000 | 607.2 / 956.6 |
| node_balance_seed3 | 0.682189 | 1.000000 | 620.5 / 986.0 |
| power_balance_seed3 | 0.836266 | 0.991416 | 633.0 / 1001.0 |
| coolest_rack_seed3 | 0.867597 | 0.906009 | 582.9 / 946.9 |
| thermal_predictive_seed3 | 0.943133 | 0.947854 | 564.7 / 875.2 |

Both PB and TP are reapplied to each identical six-decimal logged context. Rates are context-source dependent and are not comparisons against the live logged rack. Self-reproduction separately compares each live policy choice with its rescored rounded context; rounding ties explain why it can be below 1. Artificial free-node lists have distinct IDs. Latency comes only from the joined timing ledger; canonical null is never zero. [Diagnostics](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/decision_diagnostics.json).

**FACT/DERIVED — precision diagnostic:** rounded-context self-reproduction ranges across seeds are power_balance: 99.142%–99.232%; coolest_rack: 89.974%–90.601%; thermal_predictive: 94.785%–94.817%. These rates differ from fresh-process determinism: six-decimal logging can reverse close rankings, so the counterfactual diagnostic applies at logged precision and does not exactly reconstruct every live full-precision decision. No schema, precision or policy was changed.

## Runtime and storage

First wave (all seed1, observed three-worker operation):

| Policy (seed1) | Fresh-process wall s |
|---|---|
| packing | 655.588 |
| node_balance | 1148.211 |
| power_balance | 602.637 |

Full matrix wall time: **4746.698 s (79.11 min)**, excluding later offline report generation. Fifteen runs, three workers, no retries. The 1.5–2.5 h budget was an estimate, not a guard or decision rule.

| Run | RAPS s | FMU s | Total run s | Started / censored | Node utilisation |
|---|---|---|---|---|---|
| packing_seed1 | 23.228 | 620.031 | 653.177 | 4589 / 0 | 0.568423 |
| node_balance_seed1 | 21.882 | 1113.789 | 1145.937 | 4589 / 0 | 0.568423 |
| power_balance_seed1 | 23.300 | 566.407 | 600.054 | 4589 / 0 | 0.568423 |
| coolest_rack_seed1 | 20.634 | 1126.725 | 1157.657 | 4589 / 0 | 0.568423 |
| thermal_predictive_seed1 | 22.106 | 1150.595 | 1182.827 | 4589 / 0 | 0.568423 |
| packing_seed2 | 22.630 | 1073.627 | 1106.354 | 4688 / 0 | 0.574965 |
| node_balance_seed2 | 22.513 | 571.531 | 603.708 | 4688 / 0 | 0.574965 |
| power_balance_seed2 | 24.531 | 1089.851 | 1125.021 | 4688 / 0 | 0.574965 |
| coolest_rack_seed2 | 22.889 | 583.532 | 616.697 | 4688 / 0 | 0.574965 |
| thermal_predictive_seed2 | 24.908 | 567.632 | 602.849 | 4688 / 0 | 0.574965 |
| packing_seed3 | 22.588 | 1163.486 | 1196.265 | 4660 / 0 | 0.575933 |
| node_balance_seed3 | 21.895 | 602.170 | 634.087 | 4660 / 0 | 0.575933 |
| power_balance_seed3 | 22.805 | 1103.989 | 1137.266 | 4660 / 0 | 0.575933 |
| coolest_rack_seed3 | 20.066 | 634.296 | 663.983 | 4660 / 0 | 0.575933 |
| thermal_predictive_seed3 | 18.086 | 630.033 | 657.195 | 4660 / 0 | 0.575933 |

RAPS timing excludes scheduler callbacks; FMU timing includes timed extraction/model-description reading, initialization, warm-up, step/observe/state calls and terminate/freeInstance. Untimed constructor/directory cleanup are excluded from FMU time. Total EpisodeRunner timing includes setup/warm-up/serialization but excludes interpreter imports. First-wave process wall time includes interpreter startup; do not conflate these scopes or require them to sum exactly.

Every raw run exceeds 25 MB and remains gitignored locally at `thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/runs/`. [Every run file, console log and matrix journal: bytes + SHA-256](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/run_files.json); [run directory sizes](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/run_storage.json). Byte-identical manifest mirrors are committed under [provenance/run_manifests](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/run_manifests/). Raw ignored ledgers must be obtained separately for independent full-data review; git pull brings reports and hashes, not those raw directories.

## Figures and audit artifacts

[Shared-scale heatmaps](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/plots/heatmaps_seed1.png) · [max/spread time series](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/plots/timeseries_seed1.png) · [packing vs thermal GIF](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/plots/anim_packing_vs_thermal_predictive_seed1.gif) · [power_balance vs thermal GIF](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/plots/anim_power_balance_vs_thermal_predictive_seed1.gif).

[Independent raw-data recomputation](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/independent_audit.json) verifies 106 inventoried files and 38 execution-source files, with maximum scalar recomputation difference 7.28e-12. [Preregistration audit](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/preregistration_audit.json) confirms unchanged frozen sections; final verification also checks every pinned input, FMU SHA, import boundaries and both 720-frame GIFs. Source hashes match execution commit `6ee93c4`. Full porcelain records the unrelated user document changes and new artifact paths; they are preserved rather than included in this closeout.

## Anomalies and limitations

- **FACT:** 0 episode rack samples above 70 °C across the matrix; raw maximum 56.931960 °C. 0 negative episode pump-power samples. Warm-up/initialization rows, including the known initial negative pump artifact, are excluded.
- **DERIVED:** Hot rack-seconds across runs range 0–0 at the frozen G1-derived t_hot=63.30492211035258 °C. Report as observed; no threshold changes. Waits are identical by construction; unstarted jobs are censored, including late fractional arrivals admitted outside the horizon.
- **DERIVED:** temperature-only THI fraction below 0.10 ranges 0.578908–0.758694; no run is fully saturated at this reference. Full per-run values are in metrics.csv.
- **M2:** A rare long-running full-power large job can dominate the primary max-rack metric under the frozen spanning rule. The attribution above describes the E11 observations; the E10 example was job 184 setting the entire-window argmax. No workload or spanning tuning was performed.
- **M3:** E10 showed different coolant trajectories at identical hottest-rack own-power and total power, under different placements of the other load. Its mechanism remains unresolved; this matrix does not identify a hydraulic/thermal mechanism.
- published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.
- Capped warm-up is evolving, not settled. G1 parameters are frozen heuristics, not validated predictors. Forty-five °C is a reference, not a validated safety limit. Three seeds, one synthetic law, one homogeneous POWER9 twin; no generalization beyond this regime.
- RAPS-t kw/free/count inputs and t+Delta thermal/pump endpoints retain their documented mixed representation. IT energy is held-power integration; pump energy is right-endpoint integration; both exclude warm-up.
- Summit committed between-tick job-power estimates retain their documented roughly 4% loss understatement. The FMU receives actual loss-inclusive power. No correction/refit was made.
- No six-hour E11 determinism rerun. Counterfactual precision limitations and timing scopes are stated above. No PUE, plant-total energy, carbon, lifetime, heterogeneous-zone, RL or surrogate claims. The G3 what-if remains dropped.

**INFERENCE:** The primary result establishes only whether the frozen thermal heuristic meets the prescribed benefit rule in this tested regime. S1 and attribution describe distributional behavior; they do not overturn the primary decision or identify a causal plant mechanism.

## Stop and next step

**STOP at C3.** Independent review of E11 and this checkpoint is the next step. Tasks 13–16, Alibaba, what-if, redesign, new characterization, predictor selection and RL remain unauthorized. No additional run is requested as part of this closeout.
