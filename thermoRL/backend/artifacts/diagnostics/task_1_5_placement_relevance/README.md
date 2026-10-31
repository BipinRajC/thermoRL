# FMU counterfactual placement relevance

**Question:** In a modest, fixed set of FMU states, does a thermal-state rule choose a different rack than state-blind round-robin, and does that change the measured peak coolant temperature? This is a counterfactual *thermal placement* experiment. It has no RAPS jobs, queue, allocation constraints, or closed-loop scheduler, and does not establish an operational scheduling advantage.

## Frozen design and decision rules

The [preregistration](preregistration.json) fixed four ordered scenarios, two candidate racks (1 and 44), a 40 kW offered rack load, 20 s ticks, a 3600 s horizon, two rules, and the primary outcome **actual absolute peak coolant temperature**. Every scenario was warmed at 10.86 kW/rack for 7200 s, given its fixed plant-context and local-candidate preconditioning pulses, then returned to **10.86 kW/rack on all racks** for one full interval before saving the decision state. From that same saved FMU state, three branches ran: no-step control, load on rack 1, and load on rack 44. The [pre-outcome preparation](scenario_preparation.json) fixed the scores and choices before either placement outcome was observed.

The blind rule is the scenario's prelisted round-robin choice. The aware rule chooses lower predicted **absolute placed-rack peak** coolant temperature, using a prospective coolant+primary-flow ridge model; predicted final temperature breaks only a numerical peak tie. The [model](frozen_placement_model.json) was trained and frozen from 13 previously measured states before these scenario FMU runs, excluding the documented 60 s initialization-flow outlier. Its internal leave-one-state-out MAE was **0.012 °C for absolute peak** and **0.172 °C for absolute final temperature**; this is correlated-data internal checking, not independent placement validation.

**Structural limit:** Primary flow is global and identical for both candidate racks in a saved state. Because the frozen model adds coolant and flow terms, the flow term cancels from the *within-state rack ranking*. Thus this experiment tests coolant-informed ranking against round-robin; it **cannot** measure the incremental decision value of primary flow. Three scenario flows are also slightly above the model's training-flow range. The scores are used prospectively, but should not be described as a fully validated coolant+flow placement policy.

| Scenario | Initial rack 1 / 44 coolant | Primary flow | Predicted peak rack 1 / 44 | Blind → aware choice |
| --- | ---: | ---: | ---: | ---: |
| S1: baseline plant, rack 1 preheated | 30.424 / 29.247 °C | 388.233 GPM | 40.5618 / 40.5492 °C | 1 → 44 |
| S2: other racks high, rack 1 preheated | 30.429 / 29.251 °C | 388.047 GPM | 40.5615 / 40.5489 °C | 44 → 44 |
| S3: other racks low, rack 44 preheated | 29.244 / 30.422 °C | 388.352 GPM | 40.5494 / 40.5620 °C | 1 → 1 |
| S4: baseline plant, rack 44 preheated | 29.247 / 30.424 °C | 388.233 GPM | 40.5492 / 40.5618 °C | 44 → 1 |

The predicted peak ranking margin is only about **0.0126 °C**. The local preconditioning creates about a **1.18 °C** candidate starting-temperature difference. S1/S4 exchange rack identity under the same baseline plant context; S2/S3 sample high/low other-rack contexts but do not form a full factorial design.

## Actual counterfactual outcomes

The [decision ledger](run_01/decisions.jsonl) gives every score, choice, both candidate outcomes, and aware-minus-blind difference. The complete [warm-up](run_01/warmup.csv), [scenario preconditioning](run_01/scenario_preconditioning.csv), and [three-branch thermal/power ledger](run_01/branch_ledger.csv) preserve all 44 rack coolant, all 44 CDU primary supply/return, primary flow, all rack powers, and FMU heat inputs at every tick. The [outcome plot](decision_outcomes.png) separates absolute peak, final temperature, and paired incremental rise.

| Scenario | Rules differ? | Aware − blind actual placed-rack peak | Aware − blind actual placed-rack final | Aware − blind paired peak increment |
| --- | --- | ---: | ---: | ---: |
| S1 | Yes | **+0.001763 °C** | −0.276397 °C | +0.440120 °C |
| S2 | No | 0 | 0 | 0 |
| S3 | No | 0 | 0 | 0 |
| S4 | Yes | **+0.001573 °C** | −0.276146 °C | +0.439912 °C |

The rules disagree in **2 of 4** scenarios. In both, the aware rule's actual placed-rack and system-wide peak is *higher* by roughly **1.6–1.8 millidegrees Celsius**, despite its lower predicted peak score. These absolute peaks are tightly clustered around **40.56 °C** across all candidate actions. The aware choice has a lower 3600 s final temperature by about **0.276 °C**, while its *control-subtracted peak rise* is higher by about **0.44 °C**, because it places on the cooler starting rack. Those are different measurements and must not be interchanged. No result-dependent pass threshold was introduced.

In S1/S4 the model predicts the cooler candidate's peak to be about **0.0126 °C lower**, but its measured peak is about **0.0016–0.0018 °C higher**. This prospective ranking reversal is on the scale of the model's internal peak-prediction error and should be read together with the tiny actual peak separation.

## Interpretation and provenance

For this small, single-rack-perturbation FMU regime, state information **changes the selected rack** but does **not produce a meaningful absolute-peak improvement** over round-robin in the two disagreements. The signed millidegree peak difference is deterministic in this FMU, yet is too small to support a practical thermal-peak benefit claim. The roughly 0.276 °C final-temperature difference does not reverse the preregistered peak result. This experiment does not rule out value from other thermal states, jobs, constraints, objectives, or a cooling-constrained regime. It also cannot establish a flow-specific placement benefit because flow cancels from the additive within-state ranking.

The [independent verification](repeat_verification.json) checked **724 aligned counterfactual time rows per fresh-process run**, unchanged FMU inputs, exact branch-time equality, candidate peaks/finals, rule differences, and the algebraic flow cancellation. All four ledgers, including `decisions.jsonl`, were byte-identical on two runs; maximum repeated thermal variation was **0 °C at serialized precision**. Backend, original Task 1.5 test, and FMU hashes remain unchanged. FMU SHA-256: `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`. Full code/data hashes and exact timings are in [run 1 provenance](run_01/metrics_and_provenance.json) and [run 2 provenance](run_02/metrics_and_provenance.json).

**Stop gate:** No Task 1.5 criterion, 500–1000 s bound, original §3.2 protocol, FMU, backend semantic, or original test assertion changed. Task 1.6, history matching, scheduler implementation, controller comparison, and RL remain stopped pending research review.
