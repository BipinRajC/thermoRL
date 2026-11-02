# Task 1.5 matched-load FMU diagnostic

Run from `thermoRL/thermorl-v2`:

```bash
MPLCONFIGDIR=/tmp/matplotlib-thermorl2 .venv/bin/python artifacts/diagnostics/task_1_5_matched_step_20s/run_matched_step.py
```

The script warms all 44 racks at 10.86 kW for up to 7200 s using 20 s steps, resets to that snapshot, then applies 40 kW to rack 1 while holding racks 2–44 at 10.86 kW for 3600 s. Warm-up used the full 7200 s. Ambient inputs are 290 K; the Lassen coupling multiplies rack power by 0.945, giving FMU heat-flow inputs of 37,800 W for rack 1 and 10,262.7 W for each other rack. The [provenance and metrics](provenance_and_metrics.json) record the code and FMU SHA-256 values, exact configuration, versions, and the CSV hash. The [series](temperature_series.csv) has time zero and every 20 s through 3600 s for all 44 rack coolant temperatures and CDU 1's primary supply and return temperatures. The [plot](temperature_trajectory.png) shows the selected trajectories.

| Measurement | Original Task 1.5 test: 40/10.0 kW | Matched load: 40/10.86 kW |
| --- | ---: | ---: |
| Rack 1 coolant at snapshot | 29.655666 °C | 29.655666 °C |
| Rack 1 coolant at 3600 s | 40.120176 °C | 40.135423 °C |
| Rack 1 rise by 3600 s | 10.464509 °C | 10.479756 °C |
| First 63% crossing, elapsed | 1260 s | 1280 s |
| First 63% crossing, test's zero-based index | 1240 s | 1260 s |
| Rack 2 change by 3600 s | −1.296349 °C | −0.884990 °C |
| Rack 44 change by 3600 s | −1.296349 °C | −0.884990 °C |

The original-run measurements above came from the prior Task 1.5 diagnostic recorded in `HANDOFF.md`; the fresh `tests/fmu/test_fmu_backend.py` run reproduced its **1240 s** failing assertion (3 passed, 1 failed). Original-run primary supply was not recorded. The matched run's CDU 1 primary supply started at **18.847383 °C**, reached **18.909586 °C at 2920 s**, and ended at **18.688557 °C**. At 0, 600, 1200, 1800, 2400, and 3600 s, its values were 18.847383, 18.804135, 18.772643, 18.749138, 18.730120, and 18.688557 °C, respectively. Rack 1 coolant peaked at **40.561402 °C at 2760 s**, so this trajectory is not a simple monotonic first-order step response.

A second execution in a fresh process produced the same CSV SHA-256, `2f2b1f3e87f6908a48cf34e9422befe3db32591016c054b621682071f59158df`.

Holding neighboring loads at their warm-up value reduced their observed 3600 s change by about 0.411 °C relative to the original test, but they still exceeded the test's 0.5 °C locality bound. The 63% crossing stayed outside the test's 500–1000 s bound. These observations do not establish the source of the remaining neighbor change or explain the difference from the design spec's earlier probe. That probe used 15 s steps, a 10 kW background, and a step at 1800 s on a cold-start trajectory; it reported about 34.2→40.4 °C and a roughly 750 s crossing. Those protocols are not directly comparable.

**Decision gate:** Task 1.5 remains uncommitted. No load, threshold, scientific assumption, or test assertion was changed. A research/design decision is needed before revising the acceptance protocol or proceeding to Task 1.6.
