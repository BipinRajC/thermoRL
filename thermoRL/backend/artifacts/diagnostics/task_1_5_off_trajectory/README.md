# Off-trajectory coolant-only transfer test

**Question:** Does the rack-1-coolant-only response model trained on the original eight-state constant-load trajectory transfer to states with nearly the same current rack temperature and power but different preconditioning paths? This is a research characterization, not a Task 1.5 acceptance test or a history-dependence claim.

## Frozen design and feasibility record

The [initial preregistration](preregistration.json) fixed the **±0.1 °C rack-1 match tolerance**, 10.86 kW current power on all racks, the 40 kW rack-1 step, 20 s cadence, 3600 s horizon, 290 K ambient inputs, frozen coolant-only ridge model, scalar response metrics, and full-curve error metrics. The [model](frozen_coolant_only_model.json) was trained and hashed from the accepted eight-state artifacts **before any new FMU preconditioning or step response**. It was never refit to these off-trajectory results.

Preconditioning-only feasibility, with no step branches, identified two profile-design issues. The first fixed early high/low pulses [matched 32 °C](match_selection.json) but had nearly indistinguishable CDU state, slope, and flow. A [documented late-pulse revision](preregistration_v2.json) created more distinct low and constant states, but its high path [missed the temperature match](match_selection_v2.json) after switching back to baseline power. A second, [high-path-only addendum](preregistration_v3.json) moved its switch point from 31.9 to 32.1 °C using only that preconditioning trace. The [final feasibility selection](match_selection_v3.json) matched all three paths; every attempt and its preconditioning trace is retained. **No off-trajectory step response was inspected before the final profile selection.** The model, target 32 °C, ±0.1 °C tolerance, branch protocol, and metrics remained fixed throughout.

| Path and saved time | Rack 1 coolant | One-tick slope | CDU 1 primary supply / return | Primary flow | Current power |
| --- | ---: | ---: | ---: | ---: | ---: |
| Constant hold, 3640 s | 31.995629 °C | −0.061390 K/min | 19.321600 / 26.115101 °C | 387.401 GPM | 10.86 kW/rack |
| Late high→baseline, 9240 s | 31.986906 °C | −0.094592 K/min | 18.983009 / 25.451577 °C | 387.745 GPM | 10.86 kW/rack |
| Low→raised baseline, 2380 s | 32.004638 °C | −0.045309 K/min | 19.501658 / 26.430593 °C | 387.232 GPM | 10.86 kW/rack |

Rack 1 initial temperatures span **0.017732 °C**. Across these states, CDU 1 primary supply spans **0.519 °C**, return **0.979 °C**, primary flow **0.513 GPM**, and the one-tick slopes span **0.0493 K/min**. The high profile used 20 kW/rack during preconditioning and the low profile 5 kW/rack; **all branches began with the same 10.86 kW/rack current power**. Full selected-state arrays and protocol hashes are in [run 1 provenance](run_01/metrics_and_provenance.json) and [run 2 provenance](run_02/metrics_and_provenance.json).

## Paired branches and frozen predictions

Each saved state was restored separately for a no-step control and an otherwise identical rack-1 40 kW step. Branch-time observations matched exactly. The [preconditioning ledger](run_01/preconditioning.csv), [branch ledger](run_01/branch_ledger.csv), [paired-response ledger](run_01/response_ledger.csv), and [frozen prediction/residual ledger](run_01/prediction_ledger.csv) preserve time, all 44 rack coolant temperatures, all 44 CDU primary supply/return temperatures, primary flow, all rack powers, and FMU heat inputs at every 20 s sample. The [trajectory plot](frozen_model_transfer.png) shows measured responses, frozen predictions, signed error, neighboring racks, and CDU responses.

| Path | Observed paired final / frozen prediction / signed error | Observed paired window peak / frozen prediction / signed error | Full-curve time-mean abs. / maximum abs. error |
| --- | ---: | ---: | ---: |
| Constant | 10.449 / 10.484 / **−0.035 °C** | 10.794 / 10.644 / **+0.151 °C** | 0.270 / 0.817 °C |
| Late high | 10.721 / 10.487 / **+0.234 °C** | 10.941 / 10.647 / **+0.294 °C** | 0.293 / 0.872 °C |
| Low then raised | 10.337 / 10.481 / **−0.144 °C** | 10.723 / 10.640 / **+0.082 °C** | 0.263 / 0.801 °C |

The original eight-state within-path coolant-only leave-one-out MAEs were **0.230 °C final** and **0.198 °C paired peak** (with maximum absolute errors 0.497 and 0.361 °C). The off-path scalar errors are comparable to that reference; **no new pass/fail tolerance was chosen from these outcomes**. Yet the three observed final effects span **0.384 °C** at nearly matched coolant temperature, whereas the frozen model predicts only about **0.006 °C** spread from their small temperature difference. Its maximum pointwise curve errors of **0.80–0.87 °C** show that scalar agreement does not describe all transient shape differences.

The raw step-branch rack-1 peaks remain tightly grouped at **40.570–40.576 °C**, occurring **2200–2320 s** after branching. Paired CDU 1 primary-return responses peak around **+4.21 to +4.40 °C** before swinging negative later; paired primary-supply peaks are about **+0.215 to +0.217 °C**. Neighbor rack paired end increments remain about **+0.024 to +0.026 °C**. Full oscillatory trajectories, extrema, and timestamps are preserved in the ledgers and provenance.

## Reproducibility, interpretation, and stop gate

The [independent verification](repeat_verification.json) checked **543 paired time rows in each fresh-process run**, the common branch-time state, every power and FMU heat input, all step-minus-control values, and every frozen-model prediction. All four CSV ledgers were byte-identical across the two runs; repeated-run thermal variation was **0 °C at serialized precision**. Backend, original Task 1.5 test, and FMU hashes remain unchanged. The FMU SHA-256 is `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`.

**Interpretation:** This small off-trajectory test gives provisional support that current rack coolant is a useful predictor of *final and peak response magnitude* near 32 °C. It does not establish exact coolant-only state sufficiency: the observed matched-temperature response and transient-shape differences are deterministic and remain unexplained by that single predictor. Slope, CDU state, flow, and unobserved FMU state vary together across only three paths; the experiment cannot attribute those differences to any one factor. It does not test whether longer history adds information after current observables are matched, and it does not establish scheduling relevance. A history experiment is **not** justified merely by these residuals.

No Task 1.5 criterion, 500–1000 s bound, original §3.2 protocol, FMU, backend semantic, or test assertion was changed. No Task 1.6, scheduler, controller-comparison, or RL work was started. **Stop for research review.**

### Reproduce

From `thermoRL/thermorl-v2`, using its `.venv`:

1. Read `preregistration.json`, `preregistration_v2.json`, `preregistration_v3.json`, and `frozen_coolant_only_model.json` before running a branch. The two failed/weak feasibility attempts are retained for audit.
2. Run `find_matches_v3.py`, then `run_off_trajectory.py run_01` and `run_off_trajectory.py run_02` in separate OS processes.
3. Run `verify_off_trajectory.py` and `plot_off_trajectory.py` on their saved ledgers.
