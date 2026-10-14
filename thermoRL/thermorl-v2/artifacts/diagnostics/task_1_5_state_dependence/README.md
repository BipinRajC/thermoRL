# State-dependent Lassen response: paired research experiment

**Research question:** Does the same rack-power perturbation produce materially different *control-subtracted* thermal responses from different current FMU plant states? This experiment tests state dependence only. It does not test whether recent history adds information beyond current observables, whether scheduling improves, or whether the original Task 1.5 acceptance bound should change.

## Protocol and paired design

One Lassen FMU instance runs at **10.86 kW per rack** from cold initialization. Its complete state is saved at **1800 s** (State A, evolving) and **7200 s** (State B, warmed). At each saved state, the FMU is restored separately for a 3600 s **no-step control** (all racks 10.86 kW) and a **step branch** (rack 1 at 40 kW, other racks 10.86 kW). Every branch uses 20 s communication steps and 290 K air/external inputs. Rack 1's electrical-power increment is 29.14 kW; the FMU heat input changes from **10,262.7 W to 37,800 W** through the unchanged 0.945 Lassen coupling. The branch-time observations, FMU time, and input powers are exactly equal within each pair.

The complete [preconditioning ledger](run_01/preconditioning.csv) and four [branch ledgers](run_01/) record all 44 rack coolant temperatures, all 44 CDU primary supply/return temperatures, datacenter primary flow, all 44 rack powers, and all 44 FMU heat inputs at time zero and every 20 s. At each post-zero row, power and heat columns are the inputs used for the preceding 20 s interval; at time zero they show the background input before branching. Each `step_minus_control.csv` records the 44-rack and CDU paired difference; [B minus A](run_01/B_minus_A_response.csv) compares those paired responses at the same elapsed time. The [paired-response plot](run_01/paired_response.png) and [absolute-temperature plot](run_01/absolute_trajectories.png) show both views. The [run 1 provenance](run_01/provenance_and_metrics.json) contains complete initial arrays, exact input vectors, source/config/FMU hashes, versions, metrics, and file hashes; [run 2](run_02/provenance_and_metrics.json) is a fresh-process repeat.

| Paired ledgers | State A | State B |
| --- | --- | --- |
| Step | [A step](run_01/A_evolving_step.csv) | [B step](run_01/B_warmed_step.csv) |
| No-step control | [A control](run_01/A_evolving_control.csv) | [B control](run_01/B_warmed_control.csv) |
| Step − control | [A response](run_01/A_evolving_step_minus_control.csv) | [B response](run_01/B_warmed_step_minus_control.csv) |

## Measured response

| Measurement | State A: evolving at 1800 s | State B: warmed at 7200 s |
| --- | ---: | ---: |
| Initial rack 1 coolant | 34.413986 °C | 29.655666 °C |
| Initial CDU 1 primary supply / return | 19.832093 / 27.833454 °C | 18.847383 / 24.485321 °C |
| No-step rack 1 coolant at +3600 s | 30.564269 °C | 28.747409 °C |
| Step rack 1 coolant at +3600 s | 40.306416 °C | 40.135423 °C |
| **Rack 1 step − control at +3600 s** | **+9.742147 °C** | **+11.388014 °C** |
| Rack 1 paired peak / time | +9.742147 °C at 3600 s, still rising | +11.674862 °C at 2780 s |
| Raw step-branch rack 1 peak / time | 40.590868 °C at 1640 s | 40.561402 °C at 2760 s |
| First 63.2% crossing of *final paired increment* | 1060 s | 1300 s |
| First 63.2% crossing of *paired peak increment* | 1060 s | 1360 s |
| CDU 1 primary supply paired peak / time | +0.204934 °C at 1780 s | +0.223623 °C at 2920 s |
| CDU 1 primary return paired maximum / time | +3.150219 °C at 3600 s | +5.135857 °C at 2640 s |
| CDU 1 primary return paired minimum / time | −3.272503 °C at 1840 s | −1.015073 °C at 2940 s |
| Neighbor rack 2 paired increment at +3600 s | +0.031616 °C | +0.023268 °C |

The full curves are not first-order monotonic responses. State A's rack 1 paired curve reaches a local +8.407206 °C at 1680 s, dips to +8.016564 °C at 2020 s, then rises again; its maximum within the horizon is at the final sample, so the eventual peak is unknown. State B peaks at +11.674862 °C at 2780 s, dips to +11.004648 °C at 3220 s, and ends at +11.388014 °C. The peak-minus-final paired increment is **0.286848 °C** for B. In the *absolute step branches*, rack 1 peaks at nearly the same temperature in A and B, but **1120 s apart**. Reporting both raw and control-subtracted trajectories is therefore necessary.

At each elapsed time, **B response minus A response** reaches a largest absolute rack 1 difference of **2.317725 °C at 2560 s**; its end difference is **+1.645867 °C**, and its time-averaged absolute difference is **1.012915 °C**. CDU 1 primary return paired responses differ by up to **7.045611 °C at 1840 s**, reflecting different response timing and oscillation. CDU 1 primary supply paired responses differ by up to **0.189701 °C**. All 43 non-target rack coolant increments remain small: their end ranges are **+0.031615684 to +0.031615688 °C** in A and **+0.023267993 to +0.023267998 °C** in B. These measurements do not support a claim of strong rack-to-rack coolant coupling under this protocol.

**Ledger metric definition:** `mean_abs_over_3600s = 1.012915167 °C` is `trapezoid(|B−A|, time) / 3600 s`, a time-weighted mean with half-weight endpoints. The arithmetic mean of the 181 equally spaced stored samples is `1.011865545 °C`. Both calculations use the same `B_minus_A_response.csv`; the small difference is endpoint weighting, not a data or trajectory discrepancy. The saved ledger and metric were left unchanged.

## Reproducibility and interpretation

The independent [repeat verification](repeat_verification.json) checked 362 paired time rows per run, exact branch-time equality, powers and FMU heat inputs, all paired/cross-state differences, recorded hashes, and unchanged backend/test/FMU hashes. **All eight CSV ledgers and both plots are byte-identical between the two fresh-process runs; maximum repeated-run thermal difference is 0 °C at serialized precision.** The FMU SHA-256 is `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`; experiment-script and input file hashes are in the provenance.

**Result for the tested states:** The same power perturbation yields clearly different controlled rack and CDU trajectories from the evolving and warmed plant states, with differences far above the observed repeat variation. This establishes state-dependent response for this pair of FMU states and protocol. It does **not** identify which current variable or hidden plant state accounts for the difference, establish history dependence, show a scheduling advantage, or generalize across loads and placements. In particular, the two initial states differ in rack coolant, CDU supply/return, and other FMU state. The history-matching experiment remains separate and has not been run.

These ledgers can inform a later ParasParam closed-loop demonstration, but this diagnostic has **no RAPS jobs or scheduler decisions**. Observation design should follow evidence about what predicts the controlled response, then be tested for scheduling benefit before considering a learned policy.

**Stop gate:** The original §3.2 protocol, Task 1.5 test and 500–1000 s bound, FMU, backend semantics, and workload powers were not changed. The historical Task 1.5 failure remains recorded. No Task 1.6 work or history-matching experiment was started. Review this result before deciding what to characterize next or how to treat Task 1.5 acceptance.

### Reproduce

From `thermoRL/thermorl-v2`, in two separate OS processes:

```bash
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_state_dependence/run_state_dependence.py run_01
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_state_dependence/run_state_dependence.py run_02
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_state_dependence/verify_runs.py
```
