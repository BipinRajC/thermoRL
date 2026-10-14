# Task 1.5 thermal-system characterization gate

**Status:** Research characterization, 2026-09-29. The original Task 1.5 acceptance test is retained as a historical/specification test; its last recorded run failed the unchanged 500–1000 s assertion (1240 s by its zero-based calculation). This report does not designate a replacement criterion or mark Task 1.5 as passed.

## Evidence from the completed probes

The [original §3.2 probe](exact_spec_probe_15s/provenance_and_metrics.json) ran from cold start: 10 kW per rack, then rack 1 at 40 kW from simulation time 1800 s, 15 s communication steps. The [matched step](../task_1_5_matched_step_20s/provenance_and_metrics.json) and [no-step control](matched_no_step_control_20s/provenance_and_metrics.json) each began from an identical 7200 s, 10.86 kW-per-rack warmed snapshot, then ran for 3600 s at 20 s steps. The matched step changed only rack 1 to 40 kW. All used 290 K air/external inputs and the Lassen 0.945 rack-power-to-FMU-heat-flow factor. The [paired difference series](matched_minus_control_series.csv) subtracts control from matched step at each 20 s sample; their recorded initial observations are identical.

| Measurement | Original §3.2 cold-start probe | Warmed matched step | Warmed no-step control |
| --- | ---: | ---: | ---: |
| Rack 1 coolant at intervention | 34.146521 °C at 1800 s | 29.655666 °C at reset | 29.655666 °C at reset |
| Rack 1 coolant at end | 39.974620 °C at 7200 s | 40.135423 °C at 3600 s | 28.747409 °C at 3600 s |
| Rack 1 raw change | +5.828099 °C | +10.479756 °C | −0.908258 °C |
| Rack 1 peak | 40.587650 °C at 3495 s | 40.561402 °C at 2760 s | 29.655666 °C at reset |
| Raw end-referenced 63.2% crossing, measured from intervention | 750 s, at simulation time 2550 s | 1280 s elapsed; 1260 s by test index | Not applicable |
| Rack 2 / rack 44 raw end change | about −4.997577 °C each | about −0.884990 °C each | about −0.908258 °C each |
| CDU 1 primary supply, start → end | 19.812265 → 18.820754 °C from 1800 s | 18.847383 → 18.688557 °C | 18.847383 → 18.663262 °C |
| CDU 1 primary return, start → end | 27.718086 → 26.816233 °C from 1800 s | see paired comparison | 24.485321 → 23.853766 °C |

At FMU initialization, the cold probe's **all 44 rack coolant and CDU primary supply/return temperatures were 30.000000 °C**; all rack coolant temperatures were near 34.146521 °C immediately before its step. Full initial arrays and all rack/CDU trajectories are in the linked provenance and [cold series](exact_spec_probe_15s/temperature_series.csv), [matched series](../task_1_5_matched_step_20s/temperature_series.csv), and [control series](matched_no_step_control_20s/temperature_series.csv).

The [controlled comparison](matched_minus_control.json) shows a **+11.388014 °C** rack 1 difference at 3600 s, peaking at **+11.674862 °C at 2780 s**. Racks 2 and 44 differ by only **+0.023268 °C** at 3600 s; CDU 1 primary return differs by **+4.084305 °C** at 3600 s, with a **+5.135857 °C** maximum difference at 2640 s. CDU 1 primary supply differs by **+0.025296 °C** at 3600 s and reaches **+0.223623 °C** at 2920 s. The [difference plot](matched_minus_control.png) retains the shapes and timing. The warmed result supports a strong local rack response and a substantial CDU return response, with a small incremental neighboring-rack coolant response under this protocol. The full neighboring-rack decline is mostly present in the no-step control. The cold probe lacks a matched cold no-step control, so its neighboring-rack decline has no causal attribution here.

### Stationarity and reproducibility

With no perturbation after the 7200 s warm-up, rack coolant fell **0.908258 °C** over the following hour; CDU 1 primary supply fell **0.184122 °C** and return fell **0.631555 °C**. Rack coolant fell at an average **0.022651 K/min during the first five minutes** of that control, and **0.009379 K/min during the last five minutes**. The snapshot is therefore not stationary over the observed hour. This is a measurement of this warm-up protocol, not a judgment that the FMU or the original bound is wrong.

The cold probe and no-step control produced byte-identical CSV and PNG artifacts on repeated fresh-process executions; the earlier matched step's CSV also repeated byte-identically. CSV SHA-256: cold probe `b30ff160afc62f830d6550319b119ecf3bc3caed16ff97de1da1ab40903d92bb`; matched step `2f2b1f3e87f6908a48cf34e9422befe3db32591016c054b621682071f59158df`; control `a44302aa835556104e593e2e40cbf9ffa23332c8da4c2abf5609162f0171991a`. FMU SHA-256: `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`. The provenance JSON files contain exact inputs, code/config/spec hashes, library versions, and timestamps; the backend and original test source hashes remain unchanged.

## What remains unresolved

- **State dependence:** The cold and warmed responses differ, but background power, communication interval, observation horizon, and initial plant state differ together. These data do not isolate the effect of state.
- **History beyond current observation:** Different initial rack temperature and CDU state could explain different responses. No matched-current-observation histories have been tested, and no scheduling advantage has been measured.
- **Spatial scope:** Only one rack perturbation in one FMU configuration has a paired no-step control. The warmed incremental neighbor response is small; other states, loads, and placements remain uncharacterized.
- **Acceptance and scheduler observation:** A single 63% crossing omits drift, overshoot, and CDU behavior. The original bound remains recorded; whether to retain, replace, or separate it is a later research/design decision. No derivative, history, or CDU observation field is justified for the scheduler yet.

## Proposed state-dependent response experiment — design only

1. **Hold the protocol fixed.** Use the same Lassen FMU/hash, 290 K ambient, 20 s communication interval, all racks at 10.86 kW background, rack 1 stepped from 10.86 to 40 kW, and 3600 s post-intervention horizon in both states. This is a new controlled characterization protocol; it does not alter the historical §3.2 probe or Task 1.5 test.
2. **Prepare two states under that common background.** State A is evolving after 1800 s from cold start; State B is the 7200 s warmed state. Save the complete FMU state and communication time at each point. Record all 44 rack coolant temperatures, all 44 CDU primary supply/return temperatures, global primary flow, and current power vector. Verify that the measured states are distinct before interpreting a response difference.
3. **Pair each state with its own control.** From each saved state, run the 40 kW rack 1 step and an all-10.86 kW no-step control, restoring the *same* state before each branch. Keep all other inputs and duration identical. Check that every recorded observation at branch time matches exactly within each pair. Respect the FMU's one-instance-per-process restriction; repeat complete paired runs in fresh processes and compare series hashes.
4. **Compare trajectories, not only endpoints.** For each state and variable, compute `step(t) − control(t)` for rack coolant and CDU primary supply/return. Preserve every time sample. Report final and peak increments, time to peak, first 63.2% crossing relative to the final increment *and* relative to the peak when positive, overshoot/oscillation, and neighbor differences. Define these metrics before running; use no pass bound selected from the outcome. Compare the two paired response curves and report the size and timing of their differences alongside repeated-run numerical variation.
5. **Test the separate history question only after that comparison.** Two states with different current temperatures cannot establish that *history* adds information. Prepare rising and falling thermal histories that reach closely matched instantaneous rack coolant temperature and current power, select matches without inspecting their future responses, then run the same paired step/control branches. Record CDU state and temperature derivative at each branch. If responses differ, test whether current CDU/derivative observations explain the difference before considering longer history. If sufficiently matched states cannot be found, report that this question remains unidentified rather than adding history features by assumption.

The first four steps test state dependence; the fifth is a proposed follow-on identification experiment, not a claim of history relevance. Scheduler observation fields should be chosen only after these measurements show which current or historical signals predict the controlled response. The ParasParam closed-loop demo can then expose the validated trajectories with matched baselines and complete ledgers, without assuming a fixed first-order response. No RL or controller comparison is part of this gate.

**No acceptance criterion, FMU/backend semantic, test assertion, workload power, or thermal assumption was changed. No new experiment in this proposed design has been run. Task 1.6 remains stopped pending review of this characterization and a later A/B/C acceptance-test decision.**
