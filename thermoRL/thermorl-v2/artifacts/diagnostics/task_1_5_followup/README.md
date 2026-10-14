# Task 1.5 diagnostic follow-up: original probe and no-step control

These runs characterize the existing Lassen FMU response. They do not change the Task 1.5 backend, test, acceptance bounds, workload powers, or thermal assumptions.

## Protocol and reproduction

Run from `thermoRL/thermorl-v2`, one fresh OS process per command:

```bash
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_followup/run_probes.py exact
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_followup/run_probes.py control
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_followup/compare_matched_control.py
```

The **original §3.2 probe** starts from a new FMU instance at simulation time zero, applies 10 kW to all 44 racks at 15 s steps, then changes rack 1 to 40 kW starting at 1800 s while keeping the other 43 racks at 10 kW. Total simulation time is 7200 s. The original reconnaissance explicitly says that rack kW is multiplied by the Lassen 0.945 cooling efficiency, so the FMU receives 9450 W per rack before the step and 37,800 W for rack 1 after it. Air and external temperature inputs are 290 K. The time-zero sample is an initialization sample; the 1800 s sample is immediately **before** the first 40 kW interval.

The **no-step control** uses the same 7200 s, 20 s, 10.86 kW warm-up and snapshot reset as the earlier [matched step](../task_1_5_matched_step_20s/README.md). It then keeps every rack at 10.86 kW for 3600 s at 20 s steps. The FMU receives 10,262.7 W per rack. The control's time-zero coolant values and CDU 1 primary supply/return values are exactly equal to the matched step's time-zero values in the saved CSVs.

Each [exact-probe series](exact_spec_probe_15s/temperature_series.csv) and [control series](matched_no_step_control_20s/temperature_series.csv) records **all 44 rack coolant temperatures, all 44 CDU primary supply and return temperatures, and the datacenter primary flow** at every communication point. Full initial arrays, input vectors, code/config/spec/FMU hashes, versions, timestamps, and extrema are in their respective [exact-probe provenance](exact_spec_probe_15s/provenance_and_metrics.json) and [control provenance](matched_no_step_control_20s/provenance_and_metrics.json). The [exact-probe plot](exact_spec_probe_15s/temperature_trajectory.png) and [control plot](matched_no_step_control_20s/temperature_trajectory.png) show selected traces.

## Original §3.2 probe results

At time zero, **all 44 rack coolant temperatures and all CDU primary supply/return temperatures were 30.000000 °C**. Immediately before the step at 1800 s, rack coolant was 34.146521 °C across all racks (range 34.1465213817–34.1465213919 °C). CDU 1 primary supply and return were 19.812265 and 27.718086 °C.

| Measurement | Value |
| --- | ---: |
| Rack 1 coolant at 1800 s → 7200 s | 34.146521 → 39.974620 °C |
| Rack 1 7200 s rise from pre-step | +5.828099 °C |
| Rack 1 first 63.2% crossing of that rise | **750 s after step; simulation time 2550 s** |
| Rack 1 post-step peak | 40.587650 °C at simulation time 3495 s |
| Rack 2 and rack 44 coolant at 7200 s | 29.148944 °C each, about −4.997577 °C from 1800 s |
| CDU 1 primary supply at 1800 s → 7200 s | 19.812265 → 18.820754 °C |
| CDU 1 primary return at 1800 s → 7200 s | 27.718086 → 26.816233 °C |
| CDU 1 primary return post-step peak/minimum | 29.424189 °C at 3360 s / 22.840931 °C at 3690 s |

The measured 750 s crossing reproduces the earlier probe's reported crossing under its cold-start protocol. The rack 1 trajectory is oscillatory after its 3495 s peak. The large neighboring-rack declines occur during ongoing cold-start evolution; this experiment has no matching cold-start no-step control, so they are **not attributed to rack 1's perturbation**.

## Warmed no-step control results

At snapshot reset, all rack coolant temperatures were between **29.6556664031 and 29.6556664078 °C**. CDU primary supply across all CDUs was 18.8473833337–18.8473833348 °C and primary return was 24.4853209946–24.4853209974 °C. Warm-up used the full 7200 s cap.

| Measurement | Time zero | 3600 s | Change |
| --- | ---: | ---: | ---: |
| Rack 1 coolant | 29.655666 °C | 28.747409 °C | −0.908258 °C |
| Rack 2 coolant | 29.655666 °C | 28.747409 °C | −0.908258 °C |
| Rack 44 coolant | 29.655666 °C | 28.747409 °C | −0.908258 °C |
| CDU 1 primary supply | 18.847383 °C | 18.663262 °C | −0.184122 °C |
| CDU 1 primary return | 24.485321 °C | 23.853766 °C | −0.631555 °C |

All listed control trajectories peak at time zero and reach their minima at 3600 s. A 63% perturbation crossing does not apply because no rack power was changed. The subsequent 0.908 °C coolant decline shows that the 7200 s snapshot was not stationary over the next hour.

## Paired comparison with the earlier matched step

The [difference series](matched_minus_control_series.csv), [difference plot](matched_minus_control.png), and [comparison metrics](matched_minus_control.json) subtract the no-step control from the earlier 40/10.86 kW matched step at each aligned 20 s sample. All 44 coolant and the common CDU 1 primary measurements match exactly at time zero.

| Difference: matched step minus no-step control | At 3600 s | Largest absolute difference and time |
| --- | ---: | ---: |
| Rack 1 coolant | +11.388014 °C | 11.674862 °C at 2780 s |
| Rack 2 coolant | +0.023268 °C | 0.023268 °C at 3600 s |
| Rack 44 coolant | +0.023268 °C | 0.023268 °C at 3600 s |
| CDU 1 primary supply | +0.025296 °C | 0.223623 °C at 2920 s |
| CDU 1 primary return | +4.084305 °C | 5.135857 °C at 2640 s |

All racks 2–44 have a 3600 s step-minus-control difference between +0.023267991 and +0.023267996 °C. The control accounts for about 0.908 °C of the matched step's roughly 0.885 °C neighboring-rack decline; the incremental difference associated with the rack 1 power change is about +0.023 °C under this warmed protocol. This controlled comparison does **not** justify treating the full neighboring-rack decline, or the cold-start probe's neighboring-rack decline, as thermal coupling from rack 1.

## Reproducibility and stop gate

Each probe was run at least twice in fresh processes. The exact probe's CSV SHA-256 remained `b30ff160afc62f830d6550319b119ecf3bc3caed16ff97de1da1ab40903d92bb`; the control's remained `a44302aa835556104e593e2e40cbf9ffa23332c8da4c2abf5609162f0171991a`. Their PNG hashes also matched across runs. The FMU SHA-256 is `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`. Both runs used repository commit `3ebcdd7ba775c251ae8e9fb633588a2f01bc6b46` with the Task 1.5 backend still untracked; the provenance JSONs hash that source directly. The paired comparison is derived from those saved CSVs.

**Task 1.5 remains at its original failing gate.** No acceptance threshold, test assertion, implementation semantic, load, or thermal assumption was changed. No Task 1.5 commit or Task 1.6 work was made. The next step is a research/design decision.
