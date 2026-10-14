# ThermoRL v2 handoff

**State checked:** 2026-09-29, on branch `feat/thermorl2-phase0-env` at commit `3ebcdd7ba775c251ae8e9fb633588a2f01bc6b46`. The source of truth is the [implementation plan](docs/superpowers/plans/2026-09-12-thermorl-v2-raps-demo.md), with the [design spec](docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md) as its referenced rationale. This handoff records implementation progress; the plan's task boundaries and stop conditions still apply.

## Goal and architecture

The immediate goal is a reproducible Lassen closed-loop demo: RAPS supplies jobs, allocation, and rack power; the adapter passes that power to the ORNL Lassen cooling FMU; rack coolant temperatures feed a rack-scoring placement controller; ledgers and plots quantify the resulting behavior. The later research direction includes learned policies and richer thermal models, but those components are outside the current implementation.

The new Python 3.12/uv project is `thermoRL/thermorl-v2/`, package `thermorl2`. Its planned boundaries are:

- `core/`: RAPS/FMU/torch-independent state, constraints, placement, scorers, ledgers, and metrics. State and THI utilities exist; placement, scorers, ledgers, and metrics do not yet exist.
- `raps_adapter/`: the only package allowed to import `raps`. Rack geometry and the RAPS-equivalent power-to-FMU coupling exist. Engine construction, scheduler, runner, workload, and observation builder are still planned.
- `thermal/`: backend interface and FMU implementation. The Task 1.5 implementation exists in untracked files but is **not fully validated or committed**. It owns the sole FMU instance in a process, captures a warmed-idle state, and restores that state on reset. The FMU clock continues from the snapshot's internal time, so `doStep` uses the saved time offset.

The eventual RAPS engine must run with its own cooling disabled; the adapter will own the FMU and synchronize it at RAPS's 20 s power ticks. A `RackScorer` protocol is planned so future learned policies can use the same integration without tying the scorer to FMPy. None of that closed-loop runner or scorer code has been implemented yet.

## Exact plan position and amount completed

| Plan section | Progress |
| --- | --- |
| Phase 0, environment | **1/1 task complete and committed** (Task 0.1). |
| Phase 1, core through characterization | **4/7 tasks complete and committed** (Tasks 1.1–1.4). Task **1.5 is in progress and stopped at its FMU physical-response test**. Tasks 1.6–1.7 have not started. |
| Phase 2, adapter and causal coupling | **0/8 tasks started**. |
| Phase 3, ramp workload, metrics, and controller smoke | **0/3 tasks started**. |
| Phase 4, demo | **0/2 tasks started**. |

Thus **5 of the plan's 21 tasks are committed**. We are in **Phase 1, Task 1.5, Step 4**, after writing and running the prescribed FMU tests. The explicit stop instruction for an out-of-bound thermal time constant has been triggered. No Task 1.5 commit exists, and no later task has been implemented.

| Task | Implemented and verified | Commit |
| --- | --- | --- |
| 0.1 | uv project, editable RAPS dependency, FMPy/RAPS import tests; Lassen CLI 10 min smoke succeeded; RAPS Lassen engine tests: 2 passed, 22 deselected. No dependency override was needed. | `211a921` |
| 1.1 | Dataclasses for ambient, rack resources/thermal state, job request, observation, scores, placement, and `DEFER`. | `b7d092d` |
| 1.2 | Attributed RC and steady-state kernels with golden vectors; headroom and paper-raw THI, hinge, violation. An approved correction to `_safe_div` handles NumPy broadcast shapes; formulas and expectations stayed the same. | `0a7983e` |
| 1.3 | Deterministic node-to-rack geometry for Lassen's 44 racks × 18 nodes. | `0d775b4` |
| 1.4 | Rack-kW-to-FMU input mapping and ambient inputs; integration regression matches RAPS `ThermoFluidsModel.generate_runtime_values` across the Lassen input keys. | `3ebcdd7` |
| 1.5 | Thermal backend protocol and FMPy backend written; FMU tests: **3 passed, 1 failed** on the prescribed physical-response bound. | **Uncommitted** |

The committed non-FMU baseline was rechecked for this handoff: from `thermoRL/thermorl-v2`, `uv run pytest tests/unit tests/integration -q` returned **19 passed in 1.33 s**. The FMU result above is from the preceding Task 1.5 run; it was not rerun while writing this handoff.

## Current Task 1.5 discrepancy

The plan's test warms all 44 racks at **10.86 kW** for up to **7200 s**, restores the snapshot, then applies **40 kW to rack 0 and 10.0 kW to the other 43 racks** for 3600 s at 20 s steps. The warm-up used the full 7200 s. Prior diagnostic measurements under that exact input were:

- Rack 0 coolant: **29.655666 → 40.120176 °C**, a **10.464509 °C** rise.
- The test's 63%-rise calculation: **1240 s**, outside its required **500–1000 s** range. This is the asserted failure.
- Rack 1 and rack 43 each changed by **−1.296349 °C**, also beyond the test's `<0.5 °C` neighbor criterion, although execution stops at the earlier time-constant assertion.

The spec's earlier reference probe used **15 s steps**, all racks at **10 kW**, and a rack-0 step at simulated **1800 s** from a cold-start trajectory. The Task 1.5 test instead uses a warmed snapshot, 20 s steps, and lowers every non-target rack from 10.86 to 10.0 kW at the intervention. These are **protocol differences, not a proven explanation** for the observed discrepancy. The current backend tests confirm basic initialization, observation shapes, deterministic snapshot restore, and single-instance guarding, but the physical-response acceptance gate is unresolved. No threshold, input, or scientific assumption has been changed to obtain a pass.

The FMU at `models/POWER9CSM/fmus/lassen.fmu` matches the plan SHA-256 `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`. The required default FMU variables were found; the model supports FMI 2.0 Co-Simulation and state save/restore and declares a single-instance-per-process restriction. The backend's `fmu.T_prim_supply_C` is read from CDU 1's primary-supply summary, so label it precisely when reporting diagnostics.

## Files to know

| Path | Role / state |
| --- | --- |
| `docs/superpowers/plans/2026-09-12-thermorl-v2-raps-demo.md` | Authoritative sequence, tests, validation commands, commit messages, stop gates. Its Task 1.2 approved `_safe_div` correction is recorded inline. |
| `docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md` | Scientific and architectural rationale; §3.2 contains the earlier FMU probe. |
| `thermoRL/thermorl-v2/pyproject.toml`, `uv.lock`, `README.md` | Python project, dependencies, Phase 0 validation record. |
| `thermoRL/thermorl-v2/thermorl2/core/state.py`, `constraints.py`, `kernels/` | Committed core types and thermal/THI utilities. |
| `thermoRL/thermorl-v2/thermorl2/raps_adapter/rack_geometry.py`, `coupling.py` | Committed geometry and RAPS-equivalent FMU input mapping. |
| `thermoRL/thermorl-v2/thermorl2/thermal/base.py`, `fmu_backend.py` | **Untracked Task 1.5 work**; protocol and FMPy implementation. |
| `thermoRL/thermorl-v2/tests/fmu/test_fmu_backend.py` | **Untracked Task 1.5 test** with the failing physical-response assertion. |
| `thermoRL/thermorl-v2/tests/unit/`, `tests/integration/`, `tests/golden/` | Committed tests and reference vectors for Tasks 0.1–1.4. |
| `sim-raps/raps/cooling.py`, `sim-raps/raps/engine.py` | RAPS behavior used as reference for coupling and future timing semantics; do not modify casually. |
| `thermoRL/thermoRL-new/` | Frozen kernel reference only; never import as a runtime dependency. |

## Constraints and working-tree gotchas

- **Stop on physical or experimental discrepancies.** The next researcher decision is about the Task 1.5 acceptance protocol. Do not widen the 500–1000 s time bound or 0.5 °C neighbor bound, silently change loads, or proceed to Task 1.6 while this gate is unresolved.
- Keep `core/` free of `raps`, `fmpy`, and `torch`; only `raps_adapter/` imports `raps`, and only `thermal/fmu_backend.py` imports `fmpy`. No `sim-raps/` patch has been made; any needed patch must be reported and approved under the plan/spec rules.
- Preserve experiment provenance and separate RAPS runtime, FMU runtime, decision latency, and total runtime when those components are built. No controller comparison or scientific advantage has yet been measured.
- Existing unrelated working-tree changes are `thermoRL/.gitignore` (modified) and `docs/prompt.md` (untracked). **Do not stage, revert, or overwrite them** as part of Task 1.5. The Task 1.5 files are also untracked. This `HANDOFF.md` is a new file and has not been committed.
- `uv` may need write access to `/home/bipin/.cache/uv` when run in a restricted sandbox. An initial verification attempt failed with a read-only cache error; the same `uv run pytest tests/unit tests/integration -q` command succeeded with the required execution approval. Run project tests from `thermoRL/thermorl-v2/`.

## Suggested next steps

1. **Complete the already approved diagnostic before any test revision.** From a fresh warmed snapshot, keep racks 1–43 at their 10.86 kW warm-up power, step rack 0 to 40 kW, run 3600 s at 20 s intervals, and record all rack coolant temperatures and CDU-1 `fmu.T_prim_supply_C`. Record the warm-up duration, exact inputs, code and FMU hashes, and time series under `thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_matched_step_20s/`. This diagnostic was authorized in conversation but **had not been executed when this handoff was written**.
2. Report the measured rack-0 rise and 63%-rise time, rack-1/rack-43 changes, and primary-supply trajectory. Compare them with the original test and probe **without inferring a new acceptance threshold**. Stop for the human research/design decision on whether and how the Task 1.5 test protocol should change.
3. Once that decision is recorded, apply only the authorized correction, rerun the prescribed `uv run pytest tests/fmu -v` and relevant baseline tests, then commit Task 1.5 with the plan's message: `feat(thermal): FMU backend with single-instance guard, warm-up snapshot reset, RAPS-identical stepping`. Report the exact outcome.
4. Resume **Task 1.6 only after Task 1.5 passes and is committed**. Task 1.6 adds the engine factory, rack-power probe, timing-semantics test, and 24 h cost benchmark; Task 1.7 is the uniform-load characterization stop-and-report gate. Later phases remain untouched.

## 2026-09-29 continuation: Task 1.5 diagnostic completed

The authorized matched-background-power diagnostic is now recorded in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_matched_step_20s/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_matched_step_20s/README.md). It includes a rerunnable script, all 44 rack coolant time series, CDU 1 primary supply/return, a plot, exact inputs, code and FMU hashes, and metrics. The full 7200 s warm-up was used. With rack 1 stepped to 40 kW and racks 2–44 held at 10.86 kW, rack 1 rose **10.479756 °C** by 3600 s. Its 63% crossing occurred at **1280 s elapsed**, or **1260 s by the test's zero-based index calculation**. Racks 2 and 44 each changed about **−0.884990 °C**. CDU 1 primary supply started at **18.847383 °C**, peaked at **18.909586 °C at 2920 s**, and ended at **18.688557 °C**.

A fresh `.venv/bin/python -m pytest tests/fmu/test_fmu_backend.py -v` run returned **3 passed, 1 failed**, reproducing the original **1240 s** time-bound failure. The unit and integration baseline returned **19 passed**. The matched run still misses both the 500–1000 s 63%-rise bound and the <0.5 °C neighbor bound. No Task 1.5 implementation or acceptance assertion was changed, and no Task 1.5 commit was made. **Next action remains a human research/design decision about the acceptance protocol**; do not start Task 1.6 yet.

## 2026-09-29 continuation: original probe and no-step control completed

The user authorized two further diagnostics while keeping the Task 1.5 gate unchanged. Results and complete provenance are in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_followup/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_followup/README.md). The original §3.2 cold-start protocol used 15 s steps, 10 kW on all racks until 1800 s, then 40 kW on rack 1 through 7200 s, with RAPS's 0.945 heat-flow factor and 290 K ambient inputs. It reproduced the **750 s** 63% crossing: rack 1 was **34.146521 °C** before the step, **39.974620 °C** at 7200 s, and peaked at **40.587650 °C at 3495 s**. Racks 2 and 44 cooled about **4.997577 °C** after 1800 s amid the cold-start trajectory; this run has no matched cold-start control for causal attribution.

The no-step control reused the same 7200 s warm-up/snapshot protocol as the earlier matched step but kept every rack at 10.86 kW for another 3600 s. All rack coolant temperatures began near **29.655666 °C** and cooled by about **0.908258 °C**. Its initial measurements matched the earlier matched step exactly. At 3600 s, the matched step minus this control was **+11.388014 °C** for rack 1 and about **+0.023268 °C** for each other rack; CDU 1 primary supply and return differences were **+0.025296 °C** and **+4.084305 °C**. Thus the control captures almost all of the neighboring-rack decline seen in the matched step; the full decline must not be described as coupling from rack 1. Both probes produced byte-identical CSV and PNG artifacts on repeated fresh-process execution. The FMU test gate remains unresolved, no acceptance or implementation change was made, and Task 1.6 has not started. **Stop here for the research/design decision.**

## 2026-09-29 research direction decision

The user directed that the original Task 1.5 test and 500–1000 s bound remain unchanged as a historical/specification test while a separate thermal-system characterization gate is designed. The concise evidence synthesis and proposed state-dependent paired experiment are in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_followup/characterization_report.md`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_followup/characterization_report.md). This turn produced a report and experiment design only; it did **not** run the proposed experiment, revise acceptance criteria, change implementation semantics, or start Task 1.6. Review the characterization before choosing an acceptance-test option or scheduler observation fields.

## 2026-09-29 state-dependent response experiment completed

The user approved the paired state-dependent experiment, which is now complete in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_state_dependence/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_state_dependence/README.md). Under identical 10.86 kW background, 40 kW rack-1 step, 20 s ticks, 290 K ambient, and 3600 s branch horizon, states saved at FMU time 1800 s and 7200 s each had an exactly matched no-step control. Target rack step-minus-control end responses were **+9.742147 °C** (evolving state) and **+11.388014 °C** (warmed state); the maximum difference between those two response trajectories was **2.317725 °C at 2560 s**. CDU 1 primary-return responses differed by up to **7.045611 °C**. Neighboring-rack paired end responses remained small, about **+0.031616 °C** and **+0.023268 °C**. Two fresh-process runs produced byte-identical ledgers and plots, and the backend/test/FMU hashes remain unchanged. The evidence supports a state-dependent response for these tested states, not a history-dependence or scheduling-benefit claim. **Stop for user review; do not run the separate history-matching experiment, revise Task 1.5, or start Task 1.6 yet.**

## 2026-09-29 state-sufficiency sweep completed

An external research review advised testing whether current observations might explain the state-dependent response before history matching. The original two states' external observables were enumerated; the prior mean-absolute discrepancy was traced to trapezoidal time averaging versus arithmetic averaging of samples, and both definitions are documented without regenerating the old ledger. The preregistered eight-state paired sweep and all residuals are in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_state_sufficiency/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_state_sufficiency/README.md). States at 60, 120, 600, 1200, 1800, 3600, 5400, and 7200 s used the unchanged 10.86→40 kW rack-1 step with a same-state no-step control. Raw step-branch peaks were narrowly **40.561–40.670 °C**, with peak times **700–2760 s**; final paired rack-1 increments ranged **+8.150 to +11.388 °C**. Two runs had byte-identical full ledgers. The fixed held-out regression ladder did not establish state sufficiency: rack-coolant-only had the smallest held-out final/paired-peak errors among these models, while richer models extrapolated badly at the 60 s initialization transient; all eight states remain correlated on one path. **Stop for review. Do not infer history dependence, choose scheduler features, revise Task 1.5, or start Task 1.6 yet.**

## 2026-09-29 off-trajectory transfer test completed

After research review, the user authorized a coolant-only model transfer test from different preconditioning paths. The model was frozen from the original eight-state data before new FMU runs. The first fixed-pulse profile set matched temperature but converged to nearly the same current plant state; a documented late-pulse revision had a high-path feasibility miss; a second documented switch-point adjustment matched three paths before any off-trajectory step response was collected. All attempts, preregistrations, full ledgers, predictions, and the result are in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_off_trajectory/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_off_trajectory/README.md). At 32 °C ±0.1 °C and the same current 10.86 kW/rack, the paths had distinct coolant slopes and CDU/flow states. Frozen-model signed final-response errors were **−0.035, +0.234, and −0.144 °C**; full-curve maximum absolute errors were **0.817–0.872 °C**. The three observed final effects spanned **0.384 °C** despite a **0.0177 °C** initial rack-temperature spread. Two runs had byte-identical full ledgers and unchanged backend/test/FMU hashes. The evidence supports useful approximate scalar transfer near this state, while exact coolant-only sufficiency and transient prediction remain unresolved; it does **not** establish history dependence or scheduling benefit. **Stop for research review before any further experiment, Task 1.5 revision, or Task 1.6.**

## 2026-09-29 six-state identification sweep completed

The user approved a final small de-confounding sweep. Ten uniform preconditioning candidates were screened; nine matched temperature, but their best six-state subset left CDU return, coolant slope, and primary flow correlated above 0.9998. No branches were run from that weak design. A documented spatial-preconditioning augmentation added six candidates before step outcomes, and selected six matched-temperature states. All attempts, preregistrations, full paired ledgers, frozen-model predictions, residuals, and interpretation are in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_state_identification/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_state_identification/README.md). Initial rack-1 coolant spanned only **0.028 °C**, but paired final responses spanned **0.621 °C**. The response ordering no longer tracks CDU 1 return alone. Primary flow was the strongest within-set predictor in the fixed leave-one-profile-out regression (final/peak MAE **0.052/0.027 °C**), but it may proxy other-rack plant state. Return and slope remained correlated **0.999685**, so their separate roles were not identified. Two fresh-process runs had byte-identical full ledgers; FMU/backend/test hashes are unchanged. **Stop for review; no Task 1.5 acceptance change, Task 1.6, history matching, scheduler, or RL work.**

## 2026-09-29 placement relevance counterfactual completed

After research review, the user authorized the smallest FMU placement-relevance test. A prospective coolant+flow absolute-peak model and four scenario/rule definitions were frozen before outcomes. Each saved scenario state spawned no-step, rack-1-load, and rack-44-load branches. Full decision, power, and thermal ledgers, provenance, and result are in [`thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_placement_relevance/`](thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_placement_relevance/README.md). Round-robin and aware rules disagreed in **2 of 4** scenarios. In those two, the aware choice's measured absolute peak was **higher by 0.001763 and 0.001573 °C**, while its final placed-rack temperature was **lower by about 0.276 °C**. This is a negative result for the preregistered peak objective in this single-rack-perturbation regime; no practical peak advantage was shown. Because the model is additive and primary flow is shared by candidate racks, the flow term cancels from within-state ranking: no flow-specific decision value was tested. Two fresh-process runs had byte-identical ledgers; FMU/backend/test hashes are unchanged. This is a thermal counterfactual without RAPS jobs or a closed-loop scheduler. **Stop for review before any Task 1.5 revision, Task 1.6, history experiment, scheduler comparison, or RL work.**

## 2026-09-29 approved Task 1.5 closeout gate trial blocked

The user approved a separate backend-correctness gate, retaining the historical physical-response test unchanged; the approved clarification and first-trial result are in [`docs/superpowers/proposals/2026-09-29-task-1-5-backend-closeout.md`](docs/superpowers/proposals/2026-09-29-task-1-5-backend-closeout.md). The direct-FMU and backend helpers used separate processes, exactly 7200 s capped preconditioning, the same fixed asymmetric 44-rack sequence, and two restores/replays. Direct and backend outputs matched **exactly at every tick on both passes**, and time/input assertions passed. But within each process replay 1 versus replay 2 differed transiently by up to **0.000143434 °C** in rack coolant, above the approved `1e-9` restore tolerance. Direct-only rollback-flag and fresh-deserialization checks did not remove the difference. The new gate therefore **failed**; its tolerance was not widened. Lifecycle tests: **3 passed**; historical test, run after its warm-up prerequisite: **1240 s assertion failure**; unit/integration: **19 passed**. No Task 1.5 closeout commit was made, Task 1.6 and Task 1.7 have not started. The full failed-trial manifests are under `thermoRL/thermorl-v2/artifacts/diagnostics/task_1_5_backend_replay_trial/` (currently ignored by a separate uncommitted root `.gitignore` change). Stop for a new research/design decision before altering the approved gate.
