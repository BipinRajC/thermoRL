# E00 — Legacy Task 1.5 evidence index
**System:** lassen  **Status:** complete
**Pre-registered:** legacy protocols remain in their original directories; this is an index, not a new experiment.

## Question
What evidence already exists, and which limitations carry into the demo?

## Pre-registered decision rule
No new scientific gate. Legacy characterization artifacts are research evidence only and may never be cited as acceptance-gate satisfaction by any future task. The option-B direct-reference test is the backend correctness gate.

## Configuration
See [config.yaml](config.yaml). Original files remain under `artifacts/diagnostics/`.

## Method
Index A–H from the 2026-10-26 investigation findings §7; do not repeat the research chain.

## Metrics
Metrics and windows remain defined in each legacy README.

## Results

| ID | Original artifact | Question | Key finding |
|---|---|---|---|
| A | [task_1_5_matched_step_20s](../../../artifacts/diagnostics/task_1_5_matched_step_20s/README.md) | Does matching background power explain the historical response? | t63 1280 s elapsed; raw neighbour change confounded by drift. |
| B | [task_1_5_followup](../../../artifacts/diagnostics/task_1_5_followup/README.md) | What do the exact probe and matched control establish? | Cold-start t63 750 s; no-step drift −0.908 °C/h; neighbour increment +0.023 °C. |
| C | [task_1_5_state_dependence](../../../artifacts/diagnostics/task_1_5_state_dependence/README.md) | Does response vary with current plant state? | Paired final +9.74 vs +11.39 °C; nearly equal raw peaks. |
| D | [task_1_5_state_sufficiency](../../../artifacts/diagnostics/task_1_5_state_sufficiency/README.md) | Can current observables predict response on one path? | Raw peak 40.561–40.670 °C; coolant-only final MAE 0.23 °C; collinear states. |
| E | [task_1_5_off_trajectory](../../../artifacts/diagnostics/task_1_5_off_trajectory/README.md) | Does the frozen coolant model transfer across paths? | Final errors −0.035/+0.234/−0.144 °C; response spread 0.384 °C. |
| F | [task_1_5_state_identification](../../../artifacts/diagnostics/task_1_5_state_identification/README.md) | Which plant observables predict residual variation? | Flow LOPO MAE 0.052/0.027 °C; no causal attribution. |
| G | [task_1_5_placement_relevance](../../../artifacts/diagnostics/task_1_5_placement_relevance/README.md) | Does single-job state-aware placement lower peak? | 2/4 disagreements; aware peak higher by 0.0018/0.0016 °C; no RAPS loop. |
| H | [task_1_5_backend_replay_trial](../../../artifacts/diagnostics/task_1_5_backend_replay_trial/README.md) | Does backend execution match an independent direct FMU? | Direct/backend difference 0 on both passes; restore jitter 0.000143434 °C. |

## Plots
Retained in the linked original directories.

## Observations (FACT)
The historical response test fails its unchanged 500–1000 s bound at 1240 s by its index convention. The independent reference and backend agree on both replay passes; each access path exhibits the same restore transient.

## Interpretation (INFERENCE)
The backend can be checked independently of the assumed response-time bound. Characterization does not certify stationary initialization or scheduling benefit.

## Conclusion and decision
Option-B closure is recorded in the project README and dated closeout addendum after successful verification. The historical physical-response premise remains unresolved.

## Limitations
7200 s is capped preconditioning, not a settled state. Restore jitter is approximately 1.43e-4 °C. No strong spatial-coupling, history, RL, or scheduling-benefit claim follows.

## Provenance
See each original README for git, FMU and input hashes. Backend: fmu. New closure verification is retained in `provenance/option_b_manifest.json`.

## Demo relevance
Reuse fidelity and limitation evidence; implement the new pre-registered physics screen and closed loop.
