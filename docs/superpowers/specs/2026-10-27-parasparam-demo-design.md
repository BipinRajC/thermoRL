# ParasParam Demo: Closed-Loop Thermal-Aware Placement on an ExaDigiT POWER9 Digital Twin — Design Spec (FINAL)

**Date:** 2026-10-27. **Status:** FINAL. Decisions were approved by Bipin on 2026-10-27, including amendments A1–A7 and the three-FMU selection gate.

**Scope:** This spec supersedes the scope of `2026-09-12-thermorl-v2-raps-demo-design.md`. That older spec is kept as history and as the source of the verified RAPS and FMU facts.

**Evidence base:**
- `docs/2026-10-26-thermorl-investigation-findings.md`
- `docs/2026-10-27-thermorl-demo-strategy.md`
- `docs/2026-10-27-surrogate-and-fmu-selection-assessment.md`

**Companion documents:**
- `docs/superpowers/specs/2026-10-27-experiment-conventions.md`
- `docs/repository-notes.md`
- Plan: `docs/superpowers/plans/2026-10-27-parasparam-demo.md`

**Roles:**
- **Claude (Mac):** architecture, experiment design, interpretation, review.
- **Sol 6.1 (Arch Linux x86-64):** implementation, experiment execution, artifacts, READMEs, validation.

---

## 1. Goal

Build a working, reproducible, FMU-backed closed loop:

> RAPS (workload, queue, allocation, rack power) → ExaDigiT POWER9 cooling FMU → scheduler placement policy → RAPS

The loop runs on the **primary FMU**. The primary FMU is chosen from Lassen, Summit and Marconi100 by the pre-registered gate in §4.1. It is not assumed in advance.

The demo:
- compares placement policies on identical workloads;
- reports scientifically defensible results;
- includes good visuals.

The schedule is about one week. Order of priority: a working demo first, then risk reduction, then features.

**Not goals:**
- research novelty;
- RL;
- full realisation of the ThermoRL paper;
- the ExaDigiT dashboard or UE5;
- carbon accounting;
- surrogate models.

## 2. Decision register

| ID | Decision (2026-10-27) |
|---|---|
| D2 | About one week of focused work. A working demo matters more than feature count. |
| H1 | Degraded-cooling what-if is allowed only if it is: physically motivated; defined before results; reproducible; labelled "what-if"; never presented as real system behaviour. |
| H2 | **Coolant temperature** is the primary scheduling signal. THI is reported as an outcome metric only. |
| H3 | Baseline ladder: packing → node-count balance → **power balance (primary control)** → thermal-aware. |
| H4 | Synthetic workloads are used for validation; Alibaba-derived workloads for credibility. Target 50–70 % node utilisation. Horizons of 6–12 h. |
| H5 | Adapted three.js replay if low risk. Otherwise: heatmaps, animated rack view, metrics, decision explanations. |
| P1 | Task 1.5 closes under option B. Direct FMU execution is ground truth. Replay jitter (1.43e-4 °C) is a documented limitation. |
| P2 | Demo-mode gates. Keep reproducibility, provenance, experiment docs and validation evidence. Drop heavyweight review. |
| P3 | Work order: physics and FMU selection → vertical slice → conservative demo → baselines → Alibaba → visualisation → what-if. |
| S1 | **FMU-first.** The FMU is the only thermal backend for reported results. `hpc-cooling-surrogate` is future-work reference material: a local clone, not git-integrated, not a dependency. `--cooling-model surrogate` is not used. |
| S2 | **The primary FMU is selected by the three-FMU G2 gate (§4.1).** Lassen is not assumed. |
| S3 | No repository restructuring before the demo. Nested `.git` folders in `sim-raps/` and `exadigit-documentation/` stay as they are (see `docs/repository-notes.md`). |
| S4 | Optional, non-blocking: Bipin asks ORNL (Wes Brewer) for Summit or Frontier surrogate bundles, for future work. |

## 3. Architecture

The existing v2 layout is extended and made **system-generic**. Import boundaries are unchanged:
- `core/` imports nothing from `raps`, `fmpy` or `torch`.
- Only `raps_adapter/` imports `raps`.
- Only `thermal/fmu_backend.py` imports `fmpy`.

```
thermoRL/thermorl-v2/
  thermorl2/
    core/
      state.py            (+ Ambient.t_air_k_by_unit)
      placement.py        place(): single rack if possible, else greedy span, by score
      scorers.py          packing, node_balance, power_balance, coolest_rack, thermal_predictive
      metrics.py          metrics computed from ledgers only
    raps_adapter/
      coupling.py         (+ per-unit T_Air mapping)
      power_model.py      legacy_config(system), node_power_kw(), rack_power_bounds(), job_increment_kw()
      systems.py          SystemSpec registry: lassen | summit | marconi100 (FMU path+sha, grid, what-if racks)
      engine_factory.py   build_engine(), rack_kw_from_power_df(), is_power_tick()
      scheduler.py        PlacementScheduler (RAPS drop-in), ThermalView
      jobs.py             workload parquet → fresh raps Jobs
      runner.py           EpisodeRunner (RAPS ticks ↔ FMU steps, ledgers, manifest)
      workload/synthetic.py, workload/alibaba.py
    thermal/              existing FmuBackend (unchanged API)
    experiments/          code: provenance.py, probes.py, select_fmu.py, bench.py, run.py,
                          run_matrix.py, report.py, plots.py, export_viz.py, configs/*.yaml
  experiments/            ARTIFACTS (see experiment-conventions spec): <system>/<EID>/…, cross_system/…, INDEX.md
  viz/                    copied from thermoRL/thermoRL-new/viz and adapted
```

### 3.1 Systems

All values come from the RAPS config and the FMUs.

| system | racks (= CDUs) | nodes/rack | GPUs/node | power tick Δ (s) | FMU | FMU SHA-256 | schematic grid (rows × cols) | what-if racks (last ⌈n/4⌉) |
|---|---|---|---|---|---|---|---|---|
| lassen | 44 | 18 | 4 | 20 | `models/POWER9CSM/fmus/lassen.fmu` | `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b` | 4 × 11 | 33–43 |
| summit | 257 | 18 | 6 | 10 | `models/POWER9CSM/fmus/summit.fmu` | `0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233` | 13 × 20 (3 empty) | 192–256 |
| marconi100 | 49 | 20 | 4 | 20 | `models/POWER9CSM/fmus/marconi100.fmu` | `9dac7818338d0be7fcb887ee88acab01a62eeb7aff4bd286e65874e0ef5c3f77` | 7 × 7 | 36–48 |

- **Rack power.** `idle` uses `compute_node_power(0, 0, 0)`. `peak` uses `compute_node_power(CPUS_PER_NODE, GPUS_PER_NODE, 0)`. Network utilisation is 0 because RAPS jobs here carry no network traces. Switch power is added on top: `CHASSIS_PER_RACK × SWITCHES_PER_CHASSIS × POWER_SWITCH`.
- Expected values (to be verified in Task 2):

  | system | idle (kW) | peak (kW) |
  |---|---|---|
  | lassen | ≈ 10.86 | ≈ 34.43 |
  | summit | ≈ 13.2 | ≈ 45–47 |
  | marconi100 | ≈ 12.4 | ≈ 37–39 |

### 3.2 Loop semantics

- **Engine.** RAPS runs with `time_unit` 1 s, `time_delta = POWER_UPDATE_FREQ` of the system, RAPS cooling **off**, `output: "none"` (mandatory), `noui: true`, and `timestep_start` 0.
- **Power tick.** A power tick is `tick.current_timestep % time_delta == 0`.
  - Do **not** use `tick.power_df is not None`. RAPS reuses the previous `power_df` object on every non-tick second.
  - Invariant: the number of FMU steps equals `horizon_s / time_delta`.
- **FMU stepping.** The adapter owns the FMU. At each power tick the runner:
  1. gets `rack_kw` from `power_df`;
  2. calls `FmuBackend.step(rack_kw, time_delta, ambient(t))`;
  3. calls `observe()`;
  4. publishes a `ThermalView` containing coolant °C per rack, CDU pump kW, and `t_obs`.
- **What the scheduler sees.** Scheduler calls in the interval (t, t+Δ] see the last `ThermalView` and **committed rack power**. Committed power is the last observed rack kW plus the estimated increments of jobs placed since that tick.
- **Queue discipline (identical for every policy).**
  - FCFS by `(submit_time, id)`, head-of-line blocking, no backfill.
  - A job starts when total free nodes ≥ `nodes_required`. Spanning racks is allowed.
  - Consequence: job start times, total IT power and total heat are **identical across policies**. Only the spatial placement differs. §7 asserts this.
- **Placement.**
  1. Set `job.scheduled_nodes`.
  2. Call `resource_manager.assign_nodes_to_job(job, t, PolicyType.REPLAY)`.
  3. Never call `check_available_nodes`.
  - The scheduler exposes settable `policy` (FCFS) and `bfpolicy` (None).
- **Time limits.**
  - RAPS raises an exception (it does not kill the job) when a job exceeds `time_limit`.
  - Every generated job must satisfy `time_limit ≥ expected_run_time`.
- **Warm-up.**
  - Each process warms up its FMU for 7200 s at idle rack power, capped. The result is "capped, not settled".
  - The warm-up drift is identical across policies, so it cancels in comparisons.

### 3.3 Policies

Higher score is better. Ties go to the lower rack index.

| id | score for rack r | role |
|---|---|---|
| `packing` | −r | Default-scheduler behaviour (first fit by rack index) |
| `node_balance` | free_nodes_r | Thermally blind spreading |
| `power_balance` | −P_committed,r | **Primary control baseline** |
| `coolest_rack` | −T_r (coolant °C) | Pure-coolant ablation (expected to herd because of thermal lag) |
| `thermal_predictive` | −T_pred,r | **Primary thermal-aware policy** |

The predicted temperature is:

`T_pred,r = T_r + (a + b·(P_committed,r + P_job) − T_r) · (1 − exp(−H/τ))`

- `a`, `b` (linear fit of T_ss(P)) and `τ` come from **G1 on the primary FMU**. They are frozen into the config before any closed-loop comparison.
- `H = 600 s`.
- `P_job = n_nodes · (node_power(cpu, gpu) − node_power(0, 0))`, added only to the candidate rack.

**Placement rule:**
- If some rack has `free ≥ n`, choose the best-scoring such rack.
- Otherwise, fill racks in descending score order.
- Within a rack, take the lowest free node ids.
- The rule used is logged.

### 3.4 Workloads

Node and GPU limits come from the primary system's config.

**Synthetic**
- Poisson arrivals targeting node utilisation ρ (default 0.6).
- Nodes per job ∈ {1, 2, 4, 8, 16, 32} with weights {0.35, 0.2, 0.2, 0.12, 0.09, 0.04}.
- Runtime: log-normal, median 1800 s, σ 0.8, clipped to [300, 14400] s.
- GPU utilisation per node: uniform over {0, 1, …, GPUS_PER_NODE} devices.
- CPU utilisation: uniform over {0.5, 1.0, 1.5, 2.0}.
- `time_limit = ceil(runtime × 1.5)`.
- Seeds start at 1. A single `default_rng(seed)` drives all randomness.
- Output: parquet plus `meta.json` with SHA-256.

**Alibaba-derived** (labelled as derived)
- Source: `datasets/alibaba_gpu_2023/raw/openb_pod_list_<variant>.csv`.
- Drop pods with `pod_phase == Pending` or `num_gpu == 0`.
- Mapping (`G = GPUS_PER_NODE`):
  - `nodes = max(1, ceil(num_gpu / G))`
  - `gpu_util = min(G, num_gpu × gpu_milli / 1000 / nodes)`
  - `cpu_util = min(2, cpu_milli / 1000 / 20 / nodes)` — ASSUMPTION: 20 cores per socket.
  - `runtime = deletion − creation`, clipped to [300, horizon].
- Arrivals: creation times are scaled by an analytic factor so that offered node utilisation = ρ. This preserves burstiness.
- The variant (`default` vs `multigpu50`) is chosen **before any policy run**, from workload power statistics only. The choice and the stats are recorded.

**Horizon:** 6 h. Use 12 h if the measured cost per run (Task 5 bench, scaled ×2 for job load) is ≤ 5 min.

### 3.5 Scenarios

- **Nominal.** All `T_Air` and `T_ext` inputs at 290 K (RAPS default).
- **What-if: room-air cooling failure on one floor quarter (H1).**
  - Affected racks: the last ⌈n/4⌉ racks (§3.1) get `T_Air` = 308.15 K (35 °C, ASHRAE A2 allowable upper bound).
  - The event starts at t = 2 h and lasts until the horizon.
  - Used only if G3 is USABLE on the primary FMU.
  - Label: *"What-if: room-air cooling failure on one floor section (not observed <system> behaviour)"*.

## 4. Pre-registered experiments and decision rules

These are frozen. Changing any threshold or definition after results exist is a stop-and-report.

### 4.1 Three-FMU selection gate (G2 screen + selection rule)

**Common methodology.** The same protocol runs on each of Lassen, Summit and Marconi100, each in its own process:

1. Instantiate `FmuBackend` with that system's coupling.
2. Warm up: 7200 s at the idle vector, with `dt = Δ_system`.
3. Run two branches from the snapshot. Each branch: `reset()`, then 3 h at `dt = Δ_system`.
   - **spread:** all racks at `P(0.6) = idle + 0.6·(peak − idle)`.
   - **packed:** the same total (`n × P(0.6)`). Racks 0..k−1 run at `peak`, rack k at the remainder, the rest at `idle`.
4. Ambient: 290 K for all inputs.

**Recorded per system:**

| Name | Definition |
|---|---|
| `Δ_s` | (packed max-rack °C) − (spread max-rack °C), mean over the final 30 min |
| `class_s` | GO if Δ ≥ 2.0 °C; WEAK if 1.0 ≤ Δ < 2.0; STOP if Δ < 1.0 |
| `fmu_s_per_sim_h` | Measured FMU-only wall time per simulated hour |
| `C_s` | Projected closed-loop minutes per 6 h run: `fmu_s_per_sim_h × 6 × 1.5 / 60` (1.5 is the RAPS overhead factor, an ASSUMPTION) |
| `sane_s` | Warm-up completed; all outputs finite; all coolant temperatures in [10, 70] °C; no FMU exception |

**Selection rule (applied mechanically, recorded in `experiments/cross_system/X01_fmu_selection/`):**
1. **Eligible** = `sane_s` AND `C_s ≤ 30` min.
2. Among eligible systems, the **candidate** is the one with the largest `Δ_s`.
3. **Tie-break:** if another eligible system has `Δ ≥ 0.8 × Δ_candidate` and the same class, choose the one with the lower `C_s`.
4. If the chosen class is **STOP**, stop and report. The demo story needs replanning.
5. If the chosen class is **WEAK**, proceed and record that the hotspot story is reframed as "modest".
6. **Post-selection guard:**
   - If the Task 5 bench (RAPS + FMU, idle) measures more than 45 min per 6 h run for the primary, switch to the next eligible system in selection order.
   - Re-run G1 and G3 on that system.
   - Record the switch.

### 4.2 Experiments on the primary FMU

| Exp | Question | Protocol | Primary metric | Decision rule |
|---|---|---|---|---|
| **G1** Uniform sweep | T_ss(P), τ, operating range, rack homogeneity | From the snapshot (reset per level), all racks at `idle + f·(peak−idle)` for f ∈ {0, .25, .5, .75, 1}, 3 h each | Per-level mean/min/max rack °C over the final 15 min; 63 % time; linear fit a, b, R² | Freeze `a`, `b`, `τ` (median t63 over f ∈ {.25, .5, .75}). `t_hot_c` = fit at f = 0.9. Report whether 40 °C or 45 °C is reached. |
| **G3** Lever | Does room air change coolant temperature at fixed power? | All racks at f = 0.6. Control: 290 K. Intervention: what-if racks at 308.15 K. 3 h. | Δ coolant °C on affected racks (mean, final 30 min); Δ on unaffected racks | **USABLE** if ≥ 1.0 °C AND outputs are sane (finite, ≤ 70 °C). Otherwise NOT_USABLE, and the what-if is dropped. |
| **G4** Closed-loop ladder, nominal | Does thermal awareness add value beyond power balance? | 5 policies × seeds {1, 2, 3}, ρ = 0.6. Synthetic first, then Alibaba-derived. | Time-averaged max-rack coolant °C over [1 h, horizon] | **Value beyond power** if `thermal_predictive` is ≥ 0.5 °C lower than `power_balance` in every seed. Otherwise: "no material value on the homogeneous twin". Also report the packing − thermal gap. |
| **G5** What-if ladder | Value under uneven cooling | G4 protocol + §3.5 scenario | G4 metric + same metric over the affected racks | Same 0.5 °C rule |

**Secondary metrics:**
- p99 max-rack °C;
- time-averaged spread;
- hot rack-seconds above `t_hot_c`;
- mean rack °C (consistency check);
- temperature-only THI `1 − (T − T_idle)/(T_max − T_idle)`, with T_max = 45 °C. Report the fraction of samples below 0.10 (outcome only);
- CDU pump energy;
- IT energy;
- jobs started;
- wait mean and p95;
- counterfactual decision disagreement (`power_balance` vs `thermal_predictive`);
- decision latency;
- timings.

## 5. Visuals

**Minimum:**
- Side-by-side rack × time coolant heatmaps on a shared scale.
- Max-rack and spread time series.
- Metrics table.
- G2 packed-vs-spread figure, per system and cross-system.
- Animated schematic rack-grid GIF/MP4 (grid from §3.1).

**Headline (if feasible):** an adapted three.js replay on the primary system's schematic grid. It shows:
- coolant colour on a shared scale;
- placement pulses;
- a time-aligned scrubber;
- a "why this rack?" panel with per-rack scores, coolant °C and committed kW;
- a what-if banner and affected-rack outlines.

It is an offline single-folder bundle.

## 6. Claims allowed / not allowed

**Allowed (conditional on results):**
- The closed loop works and is reproducible on the primary FMU.
- Placement alone changes the rack thermal distribution (identical IT power and timing by construction).
- The measured packing → thermal gap.
- How thermal awareness compares with power balance.
- What-if results, with their label.
- The cross-FMU G2 table ("the hotspot effect across ExaDigiT POWER9 twins").

**Not allowed:**
- heterogeneous-zone claims;
- the paper's numbers;
- PUE, plant energy, carbon, lifetime or degradation claims;
- presenting the what-if as real behaviour;
- RL claims;
- any surrogate-based result.

## 7. Validation invariants

1. Within a workload, total IT kW per power tick is identical across policies (≤ 1e-6 kW), and job start times are identical.
2. Every placement uses exactly `nodes_required` distinct nodes that were free at decision time.
3. The same (config, policy, seed) gives byte-identical `decisions.jsonl`.
4. Σ per-rack kW = Σ `power_df["Sum"]` at every power tick.
5. FMU steps per run = `horizon_s / time_delta`.
6. Every run directory has a manifest containing: git SHA and dirty flag, system, FMU SHA-256, workload SHA-256, config, policy, seed, backend (`fmu`), and timings.

## 8. Known limitations to state in the demo

- One homogeneous liquid-cooled POWER9 plant per twin; 1 CDU per rack; weak rack-to-rack coupling.
- No validated PUE or plant power.
- FMUs run on Linux/Windows only.
- Capped warm-up snapshot drift.
- Replay jitter of 1.43e-4 °C under FMU state restore.
- Alibaba data lacks power, so job power is modelled. The pod-to-node mapping and time compression are assumptions.
- 3 seeds.
- The ExaDigiT ML surrogates were not used: no trained bundles exist for these systems, and they do not output cabinet coolant temperature. They are listed as future work.
