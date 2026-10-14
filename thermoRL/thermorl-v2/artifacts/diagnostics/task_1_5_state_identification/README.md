# Six-state thermal-state identification sweep

**Question:** At nearly matched rack-1 coolant temperature and identical current rack powers, can CDU 1 primary return, one-tick rack coolant slope, or datacenter primary flow explain variation in the effect of the same rack-1 workload step? This is a small observational identification experiment, not a Task 1.5 acceptance test or evidence for thermal history or scheduling benefit.

## Design and retained feasibility work

The [original preregistration](preregistration.json) fixed the **32.0 ±0.1 °C** rack-1 match, 10.86 kW/rack current power, 40 kW rack-1 step, 20 s ticks, 3600 s paired control/step horizon, response metrics, and fixed leave-one-profile-out ridge models. Ten uniform-power candidates were screened using **preconditioning only**; nine matched temperature. Even the best [uniform six-state selection](selection.json) left CDU return, slope, and flow correlated above 0.9998, so those step branches were not run. A [documented spatial-preconditioning addendum](preregistration_spatial_addendum.json) added six candidates that briefly changed rack 1 or the other 43 racks to 5 or 20 kW, then restored **every rack to 10.86 kW before branching**. Its [full candidate selection](selection_spatial.json) retains successes, failures, source hashes, predictor correlations, and the deterministic six-profile selection. No step response was inspected while choosing profiles.

All six selected states satisfied the same saved-state paired design: restore one FMU state for the no-step control, restore that same state for the rack-1 40 kW step, then subtract control from step. Every branch-time observation matched exactly. The [run 1 provenance](run_01/metrics_and_provenance.json) and [run 2 provenance](run_02/metrics_and_provenance.json) include the complete 44-rack/44-CDU initial arrays, powers, FMU heat inputs, protocol, hashes, and extrema. Full [preconditioning](run_01/preconditioning.csv), [branch](run_01/branch_ledger.csv), [paired-response](run_01/response_ledger.csv), and [frozen-model prediction](run_01/frozen_prediction_ledger.csv) ledgers retain every 20 s sample. Post-zero power and heat columns denote inputs during the preceding 20 s interval.

| Profile | Initial rack 1 coolant | Initial CDU 1 return | One-tick slope | Primary flow | Mean other-rack coolant | Rack 1 paired final / peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| High, then baseline | 31.987 °C | 25.452 °C | −0.0946 K/min | 387.745 GPM | 31.987 °C | +10.721 / +10.941 °C |
| Low, then baseline | 32.008 °C | 26.298 °C | −0.0524 K/min | 387.304 GPM | 32.008 °C | +10.375 / +10.748 °C |
| Other racks high, long pulse | 31.998 °C | 26.224 °C | −0.0561 K/min | 386.752 GPM | 35.194 °C | +10.107 / +10.546 °C |
| Other racks low, long pulse | 31.980 °C | 26.039 °C | −0.0644 K/min | 387.810 GPM | 29.861 °C | +10.728 / +10.965 °C |
| Rack 1 high pulse | 32.001 °C | 26.090 °C | −0.0630 K/min | 387.413 GPM | 31.955 °C | +10.456 / +10.799 °C |
| Rack 1 low pulse | 32.003 °C | 26.447 °C | −0.0445 K/min | 387.023 GPM | 33.246 °C | +10.216 / +10.633 °C |

The initial rack-1 coolant range is only **0.028 °C**; paired final increments span **0.621 °C**. CDU return spans **0.995 °C**, primary flow **1.059 GPM**, and mean other-rack coolant **5.334 °C**. The [response-family plot](paired_response_family.png) retains the full rack and CDU dynamics. Absolute step-branch rack-1 peaks are **40.566–40.588 °C** within this 3600 s window, with peak times **2160–2320 s**. Those nearly invariant *window peaks* are consistent with the earlier common-peak observation, but they are not proof of an equilibrium destination. Neighbor rack paired coolant effects remain small (maximum absolute across selected profiles about **0.028 °C**).

## Fixed models and all residuals

The [state/outcome table](state_observables_and_outcomes.csv), [every signed leave-one-profile-out residual](held_out_residuals.csv), [analysis summary](analysis_summary.json), and [predictor scatter plots](predictor_associations.png) publish the preregistered comparisons. Models used ridge alpha 1.0, standardization within each training fold, an unpenalized intercept, and no feature or hyperparameter selection after outcomes.

| Predictor model | Held-out MAE: paired final | Held-out MAE: paired peak |
| --- | ---: | ---: |
| CDU 1 primary return only | 0.187 °C | 0.135 °C |
| Rack-1 one-tick coolant slope only | 0.184 °C | 0.133 °C |
| Datacenter primary flow only | **0.052 °C** | **0.027 °C** |
| Return + slope | 0.193 °C | 0.139 °C |
| Return + slope + flow | 0.056 °C | 0.041 °C |

The selected-state predictor correlation between **CDU return and slope is 0.999685**, and the standardized design condition number is about **109**. This design does **not** separate return from slope despite the spatial augmentation. Flow is less correlated with them and is the strongest *within-set predictor* among these fixed models. It may proxy the substantially different other-rack thermal states or other FMU variables; six chosen deterministic profiles are not independent plant replicates. The earlier simple claim that response ordering follows CDU 1 return **does not survive** these spatial profiles—for example, the highest-return state is not the highest-response state. These regression results cannot identify a causal or generally sufficient observation vector.

The frozen original eight-state coolant-only model was also applied without refitting. On these six profiles its **mean absolute scalar errors** are **0.207 °C for final increment** and **0.164 °C for peak increment**. This is a different training comparison from the six-profile held-out regressions, so the MAEs are not a direct algorithm contest. Its full-curve signed residuals, including timings, are in the prediction ledger.

**Peak-metric convention:** `peak_to_peak_scalar_residual_c` is the *observed paired window peak minus the frozen model's scalar prediction of the window peak*. Its mean absolute value is **0.164 °C** here. `curve_residual_at_observed_peak_time_c` instead compares the observed paired response to the frozen *time-series prediction at the observed peak's timestamp*; its mean absolute value is **0.490 °C**. These are distinct quantities. The peak time is descriptive; no horizon-censored time is treated as an uncensored physical peak.

## Reproducibility and research decision

The [independent verification](repeat_verification.json) checked **1,086 paired time rows per fresh-process run**, exact branch-time state equality, every power and FMU heat input, all paired differences, frozen-model predictions, and both peak-residual definitions. All four CSV ledgers were byte-identical between runs, with **0 °C repeated thermal variation at serialized precision**. FMU, backend, and original Task 1.5 test hashes are unchanged. FMU SHA-256: `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`.

**Interpretation:** Current rack coolant alone is useful for approximate final/peak magnitude prediction in the tested regime, but does not uniquely determine the response at matched temperature. The present sweep weakens a CDU-return-only account and makes primary flow or correlated global plant state a stronger predictive candidate. It still does not establish which physical state variable causes the difference, whether a compact current observation is sufficient across other profiles, or whether history adds information after current observables are matched. No scheduler action or learned policy was tested. These pure thermal/power ledgers can inform the later ParasParam decision ledger, but cannot demonstrate scheduling benefit themselves.

**Stop gate:** No Task 1.5 criterion, 500–1000 s bound, §3.2 protocol, FMU/backend semantic, or original test assertion was changed. Task 1.6, history matching, scheduling comparisons, and RL remain stopped pending research review.
