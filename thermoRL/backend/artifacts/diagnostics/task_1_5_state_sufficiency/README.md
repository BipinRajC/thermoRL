# State-sufficiency characterization preregistration

This phase asks which **current observable thermal state** can predict the effect of the same rack-power action. It does not yet test matched-current-state history dependence, scheduler benefit, or RL. The eight saved-state times, predictors, response metrics, model ladder, and sensitivity analysis were fixed in [`preregistration.json`](preregistration.json) before any sweep branch was run.

The existing two-state [observable-difference table](initial_observable_differences.csv) and [summary](initial_observable_differences.json) enumerate all 44 rack coolant temperatures, CDU primary supply/return temperatures, rack powers, FMU heat inputs, primary flow, and a one-tick rack slope. State A minus B differs by about +4.758 °C coolant, +0.985 °C primary supply, +3.348 °C primary return, and −1.461 GPM primary flow, while every rack power and heat input is equal. With only two states these associations cannot attribute the response difference to any variable.

The predeclared sweep uses the same 10.86 kW background and 40 kW rack 1 step at 20 s ticks from states at 60, 120, 600, 1200, 1800, 3600, 5400, and 7200 s. State 60 s captures the observed fast initial overshoot, but its primary-flow value is an initialization transient; all-eight-state and seven-state-without-60-s analyses were both retained. Each state receives a true saved-state step/control pair over 3600 s.

The fixed regression ladder begins with rack 1 current coolant alone, adds its preceding-20-s slope, then compares current CDU supply/return and flow representations. It uses leave-one-state-out ridge regression with no tuning and publishes every held-out residual. Eight correlated states are **not** enough for causal attribution or a general sufficiency claim. A small residual would be provisional evidence only within this one preconditioning path; a structured residual can falsify a proposed simple representation but does not by itself prove history dependence.

## Earlier ledger-metric clarification

The earlier state-dependence report used `mean_abs_over_3600s` for the rack 1 B-minus-A response. Its value **1.012915167 °C** is the trapezoidal time average of absolute difference over 0–3600 s. The independently computed **1.011865545 °C** is the plain arithmetic mean of all 181 stored samples. Endpoint half-weighting accounts for the difference. The saved CSV and metric were not regenerated or changed; the same clarification was added to the earlier report.

## Eight-state sweep result

The sweep followed [`preregistration.json`](preregistration.json) without changing its state times, powers, metrics, or predictor list. A single FMU instance was preconditioned at 10.86 kW per rack. At each saved time, both branches restored the same state: a 3600 s no-step control and a 3600 s rack-1 40 kW step, both at 20 s communication intervals. Every branch-time observation and power input matched exactly within its pair. The [run 1 provenance](run_01/metrics_and_provenance.json) and [run 2 provenance](run_02/metrics_and_provenance.json) contain full initial vectors, code/config/FMU hashes, and ledger hashes. The full [preconditioning](run_01/preconditioning.csv), [branch](run_01/branch_ledger.csv), and [step-minus-control response](run_01/response_ledger.csv) ledgers include all 44 rack coolant values, all 44 CDU primary supply/return values, primary flow, all rack powers, and all FMU heat inputs. At each post-zero branch row, the input columns are those used for the preceding 20 s interval.

| Saved FMU time | Initial rack 1 coolant | Initial one-tick slope | Initial CDU 1 supply / return | Initial primary flow | Rack 1 paired final | Rack 1 paired window peak / time | Raw step peak / time |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 60 s | 38.182 °C | +3.389 K/min | 27.231 / 29.449 °C | 3061.18 GPM | +8.150 °C | +8.150 °C / 3600 s* | 40.670 °C / 700 s |
| 120 s | 37.774 °C | −0.299 K/min | 26.520 / 29.437 °C | 387.01 GPM | +8.183 °C | +8.183 °C / 3600 s* | 40.662 °C / 740 s |
| 600 s | 36.609 °C | −0.115 K/min | 20.779 / 29.769 °C | 386.12 GPM | +8.458 °C | +8.687 °C / 3220 s | 40.623 °C / 1020 s |
| 1200 s | 35.469 °C | −0.112 K/min | 20.091 / 28.657 °C | 386.28 GPM | +9.435 °C | +9.484 °C / 3520 s | 40.602 °C / 1360 s |
| 1800 s | 34.414 °C | −0.099 K/min | 19.832 / 27.833 °C | 386.65 GPM | +9.742 °C | +9.742 °C / 3600 s* | 40.591 °C / 1640 s |
| 3600 s | 32.037 °C | −0.062 K/min | 19.330 / 26.144 °C | 387.39 GPM | +10.416 °C | +10.774 °C / 3360 s | 40.573 °C / 2240 s |
| 5400 s | 30.564 °C | −0.038 K/min | 19.031 / 25.118 °C | 387.84 GPM | +11.364 °C | +11.364 °C / 3600 s* | 40.565 °C / 2560 s |
| 7200 s | 29.656 °C | −0.024 K/min | 18.847 / 24.485 °C | 388.11 GPM | +11.388 °C | +11.675 °C / 2780 s | 40.561 °C / 2760 s |

`*` A window maximum at 3600 s is right-censored as an eventual peak. All current rack powers were **10.86 kW** before the step; rack 1 alone changed to **40 kW** in each step branch. The [response-family plot](response_family.png) shows complete rack/CDU paired trajectories; the [absolute-peak plot](absolute_peak_vs_initial_state.png) shows the common-peak hypothesis check. Absolute step-branch rack 1 peaks span only **40.561–40.670 °C** despite an **8.527 °C** initial rack-temperature range, while time to the absolute peak spans **700–2760 s**. This is consistent with a power-dependent common peak or attractor, but does not identify the mechanism. The paired curves and CDU return oscillations are richer than a monotonic first-order response. Neighbor rack coolant increments remain small: the largest absolute neighbor paired response across the sweep is about **0.0405 °C**.

### Predeclared held-out regression

The [state-observation/response table](state_observables_and_responses.csv), [every held-out signed residual](held_out_residuals.csv), and [aggregate analysis](analysis_summary.json) preserve all outcomes. Models used leave-one-state-out ridge regression, fixed alpha 1.0, training-fold standardization, and no feature or hyperparameter tuning. Target metrics were final paired increment, peak paired increment, time of window maximum, and absolute step-branch peak.

| Model | Eight-state MAE: final / paired peak | Seven-state MAE without 60 s: final / paired peak |
| --- | ---: | ---: |
| Current rack coolant only | 0.230 / 0.198 °C | 0.254 / 0.213 °C |
| Coolant + preceding-20-s slope | 1.526 / 1.738 °C | 0.450 / 0.421 °C |
| Coolant + current CDU supply/return + flow | 106.296 / 112.276 °C | 0.536 / 0.330 °C |
| All five predeclared current/slope predictors | 113.965 / 122.266 °C | 0.634 / 0.448 °C |

The enormous eight-state errors in richer models are from **held-out 60 s extrapolation**, not a physical FMU response or an evidence-based feature ranking: its primary flow is 3061 GPM while the other saved states are near 386–388 GPM, and the models predict implausible values when trained without it. The sensitivity analysis avoids that particular extrapolation. There, coolant-only has the lowest held-out MAE for final and paired-peak increments among these fixed models, but eight temporally correlated states on one trajectory cannot establish coolant sufficiency. For that model, signed final-increment residuals include −0.457 °C at 600 s and +0.497 °C at 5400 s; they could reflect nonlinearity, correlated plant state, or model limitations. They do **not** establish hidden state or history dependence. Four time-of-window-maximum values are horizon-censored, so its regression errors should not be read as true peak-time prediction errors.

The [independent repeat verification](repeat_verification.json) checked **1,448 paired time rows in each fresh-process run**, exact inputs and differences, and unchanged backend/test/FMU hashes. All three large CSV ledgers are byte-identical between runs; maximum repeated thermal difference is **0 °C at serialized precision**. The preregistered source preconditioning CSV also reproduced its earlier SHA-256. This is deterministic variation evidence, not statistical uncertainty across independent plant realizations.

## Interpretation and stop gate

The sweep confirms a range of state-conditioned responses and a narrow range of raw step peaks along this **one** preconditioning trajectory. It does not distinguish whether rack temperature alone, current CDU/flow state, a derivative, or unobserved FMU state is sufficient across other trajectories. The fixed regression ladder provides a falsification attempt, not causal attribution or a general prediction model. No temporal-history sufficiency, scheduler relevance, controller benefit, or RL claim follows from these data. Further state-identification work would need states produced by distinct preconditioning paths to break the present collinearity; that experiment has **not** been run.

**No original Task 1.5 acceptance criterion, 500–1000 s bound, §3.2 protocol, FMU, backend semantic, workload power, or test assertion was changed. Task 1.6 and the history-matching experiment remain stopped for research review.**
