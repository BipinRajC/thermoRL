# ThermoRL ParasParam: Demo Strategy Recommendation (2026-10-27)

**Status:** strategy recommendation only. This document contains no implementation tasks. The implementation master plan for Sol 6.1 follows once the demo target and the open decisions are agreed.

**Companion document:** [`2026-10-26-thermorl-investigation-findings.md`](2026-10-26-thermorl-investigation-findings.md) records the full evidence base: repo map, capability inventory, readiness matrix, experiment ledger, and open questions.

**Labels:** **[F]** fact (verified from code or artifact) · **[I]** inference · **[A]** assumption · **[U]** unknown.

---

## Context and agreed framing (from the user, 2026-10-27)

1. The goal is a successful ParasParam demonstration. It is not a research paper, and it is not a full realisation of the original ThermoRL vision.
2. Hardware:
   - **Arch Linux machine:** runs the FMUs. It is the primary simulation and experiment environment for everything FMU-based.
   - **Mac M4 Pro (24 GB RAM, 512 GB SSD):** development, visualisation, analysis, and coordination.
3. Stay scientifically honest about limitations. Part of the final story may explain why the original ThermoRL vision cannot be fully demonstrated with the available assets.
4. Roles:
   - **Claude (this planning session):** architecture, planning, experiment design, interpretation, and technical review.
   - **Sol 6.1 (on Arch):** implementation, experiment execution, artifact generation, README creation, and validation.
5. Before the master plan: one pass focused only on an achievable demo strategy. That pass is this document.

---

## 0. Limitations, classified by source

| Source | Limitation | Hard or soft |
|---|---|---|
| **Simulation assets** | All three FMUs (Lassen, Summit, Marconi100) model the **same** POWER9 liquid-cooled plant. There is no air-cooled or immersion model, so there are no heterogeneous cooling zones. | Hard |
| | Each rack has its own CDU (one cabinet per CDU in every FMU). Rack-to-rack thermal coupling is about +0.02 °C on a neighbour for a 29 kW step. | Hard (fixed model structure) |
| | Lassen has no validated PUE, plant-power, or cooling-tower outputs. Only CDU pump power is available. | Hard as validated outputs (lower-level plant variables exist but are unvalidated) |
| | There is no degradation signal, so the THI `d` term is unavailable. Cooling setpoints are not FMU inputs, so the scheduler cannot co-control cooling. | Hard |
| | The FMUs ship without source code, and rebuilding them needs Dymola (commercial), so the models cannot be modified. | Hard |
| | The Alibaba GPU 2023 trace has no power or utilisation data, and its hardware differs from Lassen's. | Hard (workloads can only be *derived* from it, not replayed faithfully) |
| | The Lassen physical floor layout is not in the repo. | Soft (a schematic layout works) |
| **Platform** | The FMU binaries are linux64 (x86-64) and Windows only, so they cannot run on the Mac. | Solved by the Arch-runs / Mac-renders split |
| | Each FMU can be instantiated only once per process, so parallel runs need separate processes. | Soft |
| | The ExaDigiT server and dashboard need about 9 containers and 32 GB RAM, and their submodules are missing. The UE5 visualisation needs Epic and ORNL repo access. | Effectively hard for this timeline |
| **Schedule and compute** | RL needs a correct environment, reward design, training, and evaluation. RAPS's own gym environment is broken. | Soft (possible, not affordable) |
| | FMU-snapshot lookahead control, Summit-scale runs, faithful Alibaba replay, real carbon data, and multi-seed statistics beyond 3 seeds. | Soft |
| **Scientific validity** | Inventing heterogeneity and presenting it as Lassen's real behaviour. | Allowed only as an explicitly labelled what-if scenario |
| | Reusing the paper's numbers. They come from a different simulator in a ~3× overload regime. | Hard (not transferable) |
| | **[I]** A 45 °C limit probably never binds on this model. THI violations would then come from the power term, so "THI" looks like a power metric. | Must be framed honestly |
| | Comparing only against packing would be a straw man. | A power-balancing control is required |
| | In sustained overload every rack is full, so placement has no freedom. | Scenario-design constraint |
| | Lifetime, degradation, and carbon claims without data. | Not claimable |

**About RL:** the assets do **not** rule RL out. The schedule does, and so does the weak Lassen objective: a learned policy would have little to learn beyond "spread power".

---

## A. The strongest demo achievable with the actual assets

**A closed-loop scheduling demonstration on ORNL's Lassen digital twin, where the twin's thermal model is physics-based (Modelica):**

1. Workloads derived from the Alibaba GPU trace enter **RAPS**, which handles the queue, allocation, and per-rack power.
2. The adapter feeds per-rack power into the **Lassen Modelica cooling FMU** every 20 s.
3. The scheduler reads **live coolant temperatures** from the FMU and decides placement.
4. RAPS executes the placement, and the loop repeats.

The same workload runs under a ladder of policies: default packing, node-count balancing, power balancing, and thermal-aware placement. There are two scenarios:

- **Nominal plant.**
- **Degraded-cooling what-if,** clearly labelled, and only if the FMU offers a physical lever for it (see G3).

The output is a side-by-side 3D replay of the 44 racks with a "why this rack?" panel, plus figures.

This is the strongest option because it shows the **full causal chain with real twin assets**, which neither the paper nor the v1 prototype did. It also stays honest about where thermal awareness adds value.

## B. The minimum convincing demo

**Scope:**
- The closed loop running on Lassen.
- One partial-load workload (synthetic or Alibaba-derived).
- Three to four policies: packing, node-count balance, power balance, and thermal-aware.
- 1 seed, 6–12 simulated hours.

**Visuals:** side-by-side rack × time coolant heatmaps, a maximum-rack-temperature line, a metrics table, and an animated floor-grid GIF.

**Claim:** placement measurably changes the thermal distribution on a physics-based twin. Thermal-aware placement removes the hotspots that packing creates, at the same throughput. Power balancing achieves most of the same benefit.

## C. The maximum convincing demo that still feels achievable

**Everything in B, plus:**
- An Alibaba-derived workload with heterogeneous job power and short jobs.
- 3 seeds.
- The degraded-cooling scenario, but only if the lever probe works, and with the scenario designed before any results are seen.
- The v1 three.js replay adapted to Lassen, including decision explanations.
- A characterisation panel showing temperature against rack power.
- A limitations slide.

**Optional:** one FMU-snapshot **lookahead** controller, if decision cost allows.

**Excluded:** RL training, the ExaDigiT dashboard, and UE5.

## D. What is genuinely impossible to demonstrate with the available FMUs and twins

1. Comparing air, D2C, and immersion zones on a cross-technology THI. This is the paper's central contribution.
2. The paper's 3-zone CMDP with per-zone duals, in its original meaning. Per-rack duals over identical racks are possible but degenerate.
3. A validated PUE, plant-level, or cooling-energy objective on Lassen.
4. A degradation term from real signals, or any hardware-lifetime claim.
5. Joint scheduling and cooling control, because setpoints are not FMU inputs.
6. Shared-CDU or spatial airflow coupling. No available FMU has it.
7. Reproducing or validating the paper's numbers.
8. Node- or GPU-level thermals. The model is rack-level only.

## E. Technically possible but lower priority

- **RL:** a custom PPO environment on Arch, with episodes of a few minutes each. It is feasible, but expensive and aimed at a weak objective.
- **Lagrangian constraint handling** applied to a heuristic controller.
- **FMU-snapshot lookahead (MPC-lite).** The backend already supports save and restore. Each decision costs about 44 candidates × the rollout length, so candidates would need pruning.
- **The heterogeneity lever:** per-rack `T_Air` inputs or degraded-CDU parameters. Feasibility is unknown and cheap to probe.
- **Carbon,** using a labelled synthetic or diurnal intensity trace.
- **Larger runs:** Summit scale (257 racks), a 24 h ramp with per-phase reporting, and multi-seed statistics.
- **Integration polish:** registering the scheduler in the RAPS CLI, and integrating the ExaDigiT dashboard through a mock API.
- **Closing the strict Task 1.5 replay-identity gate.**

## F. Honest answer to a mentor: "How close is this demo to the original ThermoRL vision?"

> "On integration it goes **beyond** the original: the paper used a toy RC simulator, and this demo closes the loop with ORNL's actual RAPS and its Modelica cooling twin. On algorithms it shows a **heuristic subset**: THI-style, telemetry-driven placement, but no trained Lagrangian PPO. On scope it is **narrower**: the available twins model one homogeneous liquid-cooled plant, so the heterogeneous air, D2C, and immersion problem that motivates ThermoRL cannot be demonstrated with existing digital twins. The demo proves that the plumbing and the decision loop work on a real twin. It also measures how much thermal awareness is worth when cooling is homogeneous, which is the baseline the full vision has to beat. The missing piece is multi-zone digital twins, not the scheduler."

Component view (in place of a misleading percentage):

| Original component | Status in the demo |
|---|---|
| Thermal-aware placement | Demonstrated (heuristic) |
| THI concept | Demonstrated, temperature-based (the power term is framed explicitly) |
| Heterogeneous zones | Impossible with these assets |
| Lagrangian PPO | Not demonstrated (schedule) |
| Carbon and energy co-optimisation | Not demonstrated (no validated plant energy, no carbon data) |
| Real-twin validation | **New, and exceeds the paper** |

## G. Fastest experiment sequence: does thermal-aware scheduling add value beyond power balancing on Lassen?

**Reasoning.** Lassen's racks are identical and decoupled. Thermal-aware placement can therefore beat power balancing in only two ways:

- **Lag.** Coolant temperature integrates past power. With short, bursty jobs, instantaneous power is a noisy proxy for heat.
- **Uneven cooling.** This needs a lever in the model.

**[I]** Prior experiment G (placement relevance) suggests the lag effect is small, because the peak is set by power regardless of history.

**Design rule.** The thermal-aware controller must score racks on **coolant temperature only**. A THI score that includes the `P/P_max` term would partly *be* a power balancer and would confound the comparison.

The experiments run in two tracks:

- **Track 1 is FMU-only.** Sol can run it on Arch immediately, in parallel with building the loop.
- **Track 2 needs the closed loop.**

| Step | Track | Question | Control vs. intervention | Pre-specified metric | Decision |
|---|---|---|---|---|---|
| **G1** Uniform-load sweep | 1 | Is steady-state temperature T_ss(P) one monotone function shared by all racks? What is the operating range? Is 45 °C ever reached? | All racks at 0/25/50/75/100 % of rack power | Per-rack steady temperature and settling time | If T_ss(P) is monotone and identical across racks, the nominal plant has no uneven-cooling mechanism. This also fixes colour scales and thresholds. |
| **G2** Packed vs. spread | 1 | How large is the hotspot effect? | Same total kW: k racks at peak with the rest idle, vs. uniform | Maximum rack temperature; spread across racks | This gives the headline effect size. If it is below ~2 °C, the visual story weakens. |
| **G3** Lever probe | 1 | Can uneven cooling be represented legitimately? | Nominal vs. `T_Air` raised on a subset of racks (e.g. +10–15 K); optionally one degraded CDU parameter | Change in coolant temperature at fixed power | If the change is ≥ ~1–2 °C, a what-if scenario exists. If it is negligible, uneven cooling is unavailable, and that is documented as an asset limitation. |
| **G4** Closed-loop policy ladder, nominal plant | 2 | Does thermal-aware placement beat power balancing through lag? | Identical workload (a short-job, heterogeneous-power Alibaba-derived variant, plus a homogeneous variant); policies packing / node-count balance / power balance (instantaneous rack kW) / coolest rack (coolant only); 3 seeds | Time-averaged and peak maximum-rack temperature; spread; wait p95; **decision-disagreement rate** between power balance and coolest rack | If the difference is under ~0.5 °C and within seed spread, the finding is "no value beyond power balancing on the homogeneous twin". The disagreement rate explains why. |
| **G5** Closed loop, degraded cooling | 2 | When cooling is uneven, does thermal awareness add value? | The G4 ladder with G3's lever applied to a subset of racks, fixed before running | G4 metrics plus temperature on the degraded racks | This is the only place an honest "thermal beats power" result can appear. |

The answer is decisive after **G1 + G4**. G1 and G2 also show whether the demo's core visual effect exists before any G4 code is written.

## H. Top 5 decisions that still affect architecture or experiment design

1. **Degraded-cooling what-if scenario: allowed or not?** It decides whether G3/G5 exist and whether any "beyond power balancing" claim is possible. Allowing it overrides the old spec's "no artificial heterogeneity" rule.
2. **How the thermal-aware controller and THI are framed.**
   - Option A: the controller scores on coolant temperature only, and THI is a reported metric.
   - Option B: the controller scores on THI, as in the spec.
   - Separately: T_max = 45 °C, the 40 °C CDU setpoint, or no threshold. Decide after G1 and before any comparison.
3. **Baseline ladder.** I recommend adding power balance as the honest control, and naming packing explicitly as "default scheduler behaviour" rather than presenting it as a straw man.
4. **Workload and regime.**
   - Synthetic, Alibaba-derived, or both.
   - Load level: partial load, roughly ρ 0.5–0.7, is recommended.
   - Horizon: 6–12 h.
   - The rules for mapping Alibaba pods onto Lassen nodes.
5. **The Arch↔Mac artifact contract and the visual target.** Sol produces run ledgers and frames on Arch; the Mac renders them. Choosing three.js or a GIF fixes the frame schema the runner must emit.

**Process prerequisites** (not architecture):
- Close Task 1.5 (the FMU-backend acceptance gate) under closeout option B. Under B, the backend agrees with direct FMU calls exactly, and the 1.4e-4 °C replay jitter is recorded as a limitation.
- Adopt lighter demo-mode gates. Keep provenance and honest reporting, and drop blocking gates that do not affect demo validity.

## I. Headline ParasParam story for evaluators

> **"Schedulers are thermally blind. We closed the loop between a production-style scheduler and a physics-based digital twin."**
> GPU jobs derived from the Alibaba GPU trace flow through ORNL's RAPS simulator into the Lassen Modelica cooling model. The scheduler sees live coolant temperatures and decides placement every time jobs arrive.
>
> - **Result 1:** Default packing creates rack hotspots. Thermal-aware placement removes them, cutting peak rack coolant temperature by **X °C** with identical throughput.
> - **Result 2 (honest):** On a uniformly cooled system, simple power balancing gets most of this benefit.
> - **Result 3 (if G3 passes):** When part of the cooling degrades, only the thermal-aware scheduler notices and routes work away.
>
> **Why it matters:** this is the integration foundation for ThermoRL's goal of scheduling across heterogeneous cooling. The next missing piece is multi-zone digital twins, not the scheduler.

---

## Recommended demo targets

All effort figures are **[A]** rough working-day estimates for Sol executing on Arch, with you reviewing. The actual deadline (question D2) is still the deciding input.

### Conservative target: high confidence

| | |
|---|---|
| **Scope** | Closed loop on Lassen. One synthetic partial-load workload. Policies: packing, node-count balance, power balance, coolest rack (coolant only). 6–12 h, 1 seed, nominal plant only. |
| **Expected impact** | Solid. Shows the full twin-in-the-loop chain and a clear hotspot visual. |
| **Risk** | Low. The main residual risk is that G2 shows only a small effect. |
| **Implementation work** | ~5–7 days: engine factory and per-rack power probe; scheduler drop-in; four scorers; episode runner synchronising RAPS and the FMU; decision and interval ledgers plus a run manifest; metrics; plotting script; animated GIF. |
| **Experiments** | RAPS runtime check; G1 (slim); G2; one closed-loop run per policy. |
| **Visualisation** | Side-by-side heatmaps on a shared colour scale; maximum-rack and spread lines; metrics table; animated 44-rack floor-grid GIF. |
| **Legitimate claims** | The closed loop of RAPS plus the Lassen FMU works and is reproducible. Placement changes the rack thermal distribution. Thermal-aware placement lowers peak rack coolant temperature by X °C versus packing, at equal throughput and IT energy. It performs comparably to power balancing on this homogeneous twin. |

### Recommended target: best balance

| | |
|---|---|
| **Scope** | Everything in Conservative, plus: an Alibaba-derived workload (short, heterogeneous-power jobs) alongside the synthetic one; 3 seeds; the G3 lever probe, followed by the G5 degraded-cooling scenario **only if the lever works** (designed before results are seen); the three.js side-by-side replay adapted to 44 Lassen racks with a "why this rack?" panel; a characterisation figure; a limitations slide. |
| **Expected impact** | High. A real-trace-derived workload, an interactive visual, and an honest scientific answer to "does thermal awareness matter here?". Possibly also a "routes around degraded cooling" moment. |
| **Risk** | Medium. The Alibaba mapping and the viz adaptation are the schedule risks. If G3 fails, the demo falls back gracefully to the Conservative claims plus a documented limitation. |
| **Implementation work** | ~10–14 days: everything in Conservative, plus an Alibaba-derived workload builder with documented mapping; a scenario config for the lever; a seed runner; a frame exporter matching the viz schema; the three.js adaptation (data-driven layout, time alignment, shared colour scale, decision panel). |
| **Experiments** | G1–G4 in full; G5 only if G3 passes. |
| **Visualisation** | All Conservative visuals, plus an interactive offline replay (a single-file bundle that runs on the Mac with no server) and the temperature-vs-power characterisation figure. |
| **Legitimate claims** | All Conservative claims, plus: results hold across 3 seeds and on a trace-derived workload, and there is a measured answer (with effect size) to whether thermal state adds value beyond power balancing on Lassen. *If G5 runs:* under a labelled degraded-cooling what-if, thermal-aware placement lowers temperatures on the degraded racks and power balancing does not. |

### Stretch target: if everything goes well

| | |
|---|---|
| **Scope** | Everything in Recommended, plus: a FMU-snapshot lookahead controller (top-k candidates); a 24 h ramp scenario reported per phase, showing where placement freedom disappears; a nominal vs. degraded scenario toggle in the viz; optionally a small 2–3 policy check at Summit scale. |
| **Expected impact** | Very high polish and depth. Lookahead is the natural non-RL bridge to a "predictive" ThermoRL. |
| **Risk** | High on schedule. Neither the lookahead cost nor the 24 h runtime has been measured. |
| **Implementation work** | ~18–25 days: everything in Recommended, plus a lookahead scorer using the backend's save and restore; per-phase metrics; scenario switching in the viz. |
| **Experiments** | Everything above, plus a lookahead cost benchmark and the 24 h ramp. |
| **Visualisation** | Interactive replay with scenario switching and phase markers. |
| **Legitimate claims** | All Recommended claims, plus: model-predictive placement that uses the twin itself, with measured cost and benefit; and where in the load range thermal-aware placement stops mattering. |

**RL** is excluded from all three targets. At most it appears on a "future work" slide explaining why; sections D and E give the reasons.

---

## Recommendation

Commit to the **Recommended target**, with the **Conservative target as the guaranteed fallback**.

- Sequence the work so the Conservative demo is complete first; every addition after that is incremental.
- Start the Track 1 FMU experiments (G1–G3) on Arch immediately, in parallel with building the loop. They de-risk the headline before any comparison code exists.

## Inputs needed to lock the target

1. **Deadline (D2).** This decides between Conservative and Recommended.
2. **Decisions H1–H5,** especially H1 (whether the degraded-cooling what-if is allowed).
3. **Confirmation** that Task 1.5 closes under closeout option B and that the lighter demo-mode gates apply. Assumed "yes" unless you object.

After these are answered, the next artifact is the **implementation master plan for Sol 6.1**, organised around the agreed target and priorities P0–P5:

- **P0** End-to-end vertical slice
- **P1** Validated baseline experiment
- **P2** Parameter characterisation
- **P3** Scheduling improvements
- **P4** Visualisation
- **P5** Optional RL
