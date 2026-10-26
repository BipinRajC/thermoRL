# ParasParam Demo: Closed-Loop Thermal-Aware Placement on the Lassen Digital Twin — Design Spec

**Date:** 2026-10-27
**Status:** Decisions approved by Bipin on 2026-10-27. This spec supersedes the scope of `2026-09-12-thermorl-v2-raps-demo-design.md`; that document is kept as history and as the source of the verified RAPS and FMU facts.

**Evidence base:**
- `docs/2026-10-26-thermorl-investigation-findings.md`
- `docs/2026-10-27-thermorl-demo-strategy.md`

**Roles:**
- **Claude (Mac):** architecture, experiment design, interpretation, review.
- **Sol 6.1 (Arch Linux):** implementation, experiment execution, artifacts, READMEs, validation.

---

## 1. Goal

A working, reproducible, FMU-backed closed-loop demonstration on ORNL's Lassen twin. The loop is:

> RAPS (workload, queue, allocation, rack power) → Lassen cooling FMU → scheduler placement policy → RAPS

The demo compares placement policies on identical workloads, reports scientifically defensible results, and includes good visuals. The schedule is about one week. The order of work is: get a working demo first, then reduce risk, then add features.

**Not goals:** research novelty, RL, full realisation of the ThermoRL paper, the ExaDigiT dashboard or UE5, carbon.

## 2. Decision register (2026-10-27)

| ID | Decision |
|---|---|
| D2 | About one week of focused work. A working demo matters more than feature count. |
| H1 | A degraded-cooling what-if is approved **only if** it is physically motivated, defined before results are seen, reproducible, labelled "what-if", and never presented as real Lassen behaviour. |
| H2 | **Coolant temperature** is the primary scheduling signal. THI is reported as an outcome metric only. |
| H3 | Baseline ladder: packing → node-count balance → **power balance (primary control)** → thermal-aware. |
| H4 | Synthetic workloads are used for validation; Alibaba-derived workloads for credibility. Target 50–70 % node utilisation; 6–12 h horizons. |
| H5 | Adapted three.js replay if low risk. Otherwise rack heatmaps, an animated rack view, a metrics table, and decision explanations. |
| P1 | Task 1.5 closes under option B. Direct FMU execution is ground truth; replay jitter is a documented limitation. |
| P2 | Demo-mode gates: keep reproducibility, provenance, experiment docs, and validation evidence. Drop heavyweight per-step review. |
| P3 | The work is ordered: physics check → vertical slice → conservative demo → baselines → Alibaba → visualisation → what-if. |

## 3. Architecture

The existing v2 layout is extended, not replaced. The import boundaries are unchanged:
- `core/` imports no `raps`, `fmpy`, or `torch`.
- `raps_adapter/` is the only package that imports `raps`.
- `thermal/fmu_backend.py` is the only module that imports `fmpy`.

```
thermoRL/thermorl-v2/thermorl2/
  core/
    state.py            (+ Ambient.t_air_k_by_unit)
    placement.py        place(): single-rack-if-possible, else greedy span, by score
    scorers.py          packing, node_balance, power_balance, coolest_rack, thermal_predictive
    metrics.py          metrics computed from ledgers only
  raps_adapter/
    coupling.py         (+ per-unit T_Air mapping)
    power_model.py      legacy_config(), node_power_kw(), rack_power_bounds()
    engine_factory.py   build_engine(), rack_kw_from_power_df()
    scheduler.py        PlacementScheduler (RAPS drop-in)
    jobs.py             workload parquet → fresh raps Jobs
    runner.py           EpisodeRunner (RAPS ticks ↔ FMU steps, ledgers, manifest)
    workload/synthetic.py, workload/alibaba.py
  thermal/              (existing FmuBackend, unchanged API)
  experiments/
    probes.py           FMU-only physics checks G1/G2/G3
    run.py              one (config, policy, seed) run → run dir
    run_matrix.py       many runs, one OS process each (one FMU per process)
    plots.py, export_viz.py
    configs/*.yaml
viz/ (new, copied from thermoRL/thermoRL-new/viz and adapted)
```

### 3.1 Loop semantics

- **Engine settings.** RAPS Lassen with `time_unit` 1 s, `time_delta` 20 s, and RAPS cooling **off**.
- **Who owns the FMU.** The adapter owns the FMU. At each power tick (`t % 20 == 0`) the runner:
  1. reads per-rack kW from `power_df`;
  2. calls `FmuBackend.step(rack_kw, 20, ambient(t))`;
  3. calls `observe()` and publishes a `ThermalView` (coolant °C per rack, CDU pump kW, `t_obs`).
- **What the scheduler sees.** Scheduler calls in the interval (t, t+20] see the last `ThermalView` and **committed rack power**. Committed power is the last observed rack kW plus the estimated increment of jobs placed since that tick.
- **Queue discipline (identical for every policy).** FCFS by `submit_time`, head-of-line blocking, no backfill. A job starts when total free nodes ≥ `nodes_required`, and spanning racks is allowed.
  - **Consequence (must be asserted, §7):** job start times, completions, total IT power, and total heat are **identical across policies**. Only the spatial placement differs.
- **How placement is executed.** Set `job.scheduled_nodes`, then call `resource_manager.assign_nodes_to_job(job, t, PolicyType.REPLAY)`. Never call `check_available_nodes`. The scheduler exposes settable `policy` (FCFS) and `bfpolicy` (None).
- **Warm-up.** Each process warms the FMU for 7200 s at idle rack power, capped (the snapshot is "capped, not settled", drifting about −0.9 °C/h). The drift is identical across policies, so it cancels in comparisons.

### 3.2 Policies (rack scores; higher is better; ties broken by lower rack index)

| id | score for rack r | role |
|---|---|---|
| `packing` | −r | Default-scheduler behaviour (first-fit by rack index) |
| `node_balance` | free_nodes_r | Thermally blind spreading |
| `power_balance` | −P_committed,r | **Primary control baseline** |
| `coolest_rack` | −T_r (coolant °C) | Pure-coolant ablation. Expected to herd because of thermal lag. |
| `thermal_predictive` | −T_pred,r | **Primary thermal-aware policy** |

`T_pred,r = T_r + (T_ss(P_committed,r + P_job) − T_r) · (1 − exp(−H/τ))`

- `T_ss(P) = a + b·P` (linear fit) and `τ` (median 63 % time at mid load) are **measured in G1** and frozen into the config before any closed-loop comparison.
- `H = 600 s`.
- P_job is the estimated electrical increment of the job: `n_nodes × (node_power(cpu, gpu) − node_power(0, 0))`. It is added only to the candidate rack.

**Placement rule.** If some rack has `free ≥ n`, choose the best-scoring such rack. Otherwise fill racks in descending score order until n nodes are reached. Within a rack, take the lowest free node ids. The rule used is logged.

### 3.3 Workloads

- **Synthetic.**
  - Poisson arrivals at a rate that targets node utilisation ρ (default 0.6).
  - Nodes per job ∈ {1, 2, 4, 8, 16, 32} with weights {0.35, 0.2, 0.2, 0.12, 0.09, 0.04}.
  - Runtime: log-normal, median 1800 s, σ 0.8, clipped to [300, 14400] s.
  - GPU utilisation per node: uniform over {0, 1, 2, 3, 4} devices. CPU utilisation: uniform over {0.5, 1.0, 1.5, 2.0}. Both are scalar traces.
  - Time limit: `ceil(runtime × 1.5)`.
  - Seeds start at 1. One `numpy.random.default_rng(seed)`.
  - Output is parquet plus `meta.json` containing the SHA-256.
- **Alibaba-derived (labelled as derived).**
  - Source: pods from `openb_pod_list_<variant>.csv`. Drop `Pending` pods and pods with `num_gpu == 0`.
  - `nodes = max(1, ceil(num_gpu/4))`.
  - `gpu_util per node = min(4, num_gpu × gpu_milli / 1000 / nodes)`.
  - `cpu_util = min(2, cpu_milli / 1000 / 20 / nodes)`. This is an assumption: 20 cores per POWER9 socket.
  - Runtime = `deletion_time − creation_time`, clipped to [300, horizon].
  - Arrivals: creation times scaled by a factor c, computed analytically so that offered node-utilisation equals the target ρ. This keeps the trace's burstiness.
  - The pod-list variant is chosen **before any policy run**, using only workload power statistics: mean per-node increment, and the share of nodes with ≥ 2 GPUs busy. Candidates: `default`, `multigpu50`. The choice and the stats are recorded.
- **Horizon.** 6 h by default; 12 h if T1.1's cost benchmark allows ≤ 5 min per run.

### 3.4 Scenarios

- **Nominal.** Every input set to 290 K, as RAPS does.
- **What-if: CRAH/room-air failure (H1).**
  - Racks 33–43, the last 11 racks treated as one schematic row, get `T_Air = 308.15 K` (35 °C, the ASHRAE A2 allowable upper bound).
  - The event starts at t = 2 h and lasts until the horizon. All other inputs stay nominal.
  - It is used only if G3 passes.
  - Label: "What-if: room-air cooling failure on one row (not observed Lassen behaviour)".
  - Secondary lever (only if `T_Air` fails, time-boxed): a degraded-CDU parameter. Sol only lists candidate tunable parameter names and reports them; implementing it needs approval.

## 4. Pre-registered experiments and decision rules

These are fixed now and must not be changed after results are seen. If a threshold needs changing, that is a stop-and-report.

| Exp | Question | Protocol | Primary metric | Decision rule |
|---|---|---|---|---|
| **G1** Uniform sweep | What is T_ss(P), τ, and the operating range? Are all racks identical? | From the snapshot (restored per level), all racks at `idle + f·(peak−idle)` for f ∈ {0, .25, .5, .75, 1}, 3 h each, 20 s steps | Per-level mean, min and max rack °C over the last 15 min; 63 % time; linear fit a, b, R² | Freeze a, b, τ into the config. Report whether any rack reaches 40 °C or 45 °C. Define `T_hot` = fitted T_ss at f = 0.9. |
| **G2** Packed vs spread | Does redistributing identical power create a meaningful hotspot? | Total = 44 × P(f = 0.6). Packed: racks 0..k−1 at peak, rack k at the remainder, the rest idle. Spread: all racks equal. 3 h each from the snapshot. | Δ max-rack °C (packed − spread), mean over the last 30 min | **GO ≥ 2.0 °C**; WEAK 1.0–2.0 (proceed, reframe); **STOP < 1.0** (report, replan) |
| **G3** Lever | Does room-air temperature legitimately change rack coolant temperature at fixed power? | All racks at f = 0.6. Control: 290 K. Intervention: racks 33–43 at 308.15 K. 3 h. | Δ coolant °C on affected racks (mean, last 30 min); Δ on the others | **Usable ≥ 1.0 °C** on affected racks; otherwise the what-if is dropped and recorded as an asset limitation |
| **G4** Closed-loop ladder, nominal | Does thermal awareness add value beyond power balance? | All 5 policies × seeds {1, 2, 3}, ρ = 0.6, synthetic, then Alibaba-derived | Time-averaged max-rack coolant °C over [1 h, horizon] | **Value beyond power** if `thermal_predictive` is ≥ 0.5 °C lower than `power_balance` in every seed. Otherwise the finding is "no material value on the homogeneous twin". Also report the packing − thermal_predictive gap. |
| **G5** What-if ladder | Under uneven cooling, does thermal awareness add value? | G4 protocol plus the §3.4 scenario | Same as G4, plus time-averaged max coolant °C over racks 33–43 | Same 0.5 °C rule |

**Secondary metrics (all runs):**
- **Thermal:**
  - p99 of max-rack °C;
  - time-averaged rack spread (max − min);
  - hotspot rack-seconds above `T_hot`;
  - mean rack °C (expected ≈ equal across policies; this is a consistency check);
  - temperature-only THI: `1 − (T − T_idle)/(T_max − T_idle)`, with T_max = 45 °C and T_idle the per-rack snapshot temperature. Reported as the fraction of rack-intervals below 0.10, an outcome metric only.
- **Energy and performance:**
  - CDU pump energy;
  - IT energy;
  - jobs completed;
  - wait mean and p95.
- **Diagnostics:**
  - counterfactual decision-disagreement rate between `power_balance` and `thermal_predictive`, re-scored on logged observations;
  - decision latency;
  - RAPS, FMU, and total wall time.

## 5. Visuals

**Minimum, from `plots.py`:**
- side-by-side rack × time coolant heatmaps on a shared colour scale;
- max-rack and spread time series per policy;
- a metrics table in markdown;
- a G2 packed-vs-spread figure;
- an animated 4 × 11 schematic rack-grid GIF/MP4 per policy pair.

**Headline, if feasible:** the three.js side-by-side replay, adapted:
- 44 racks on a labelled-schematic 4 × 11 grid, coloured by coolant °C on a shared scale;
- placement pulses;
- a time-aligned scrubber;
- a "why this rack?" panel showing that decision's per-rack scores, coolant °C and committed kW;
- a what-if banner when the scenario is active;
- an offline single-folder bundle that runs on the Mac.

## 6. Claims allowed / not allowed

**Allowed, conditional on the result:**
- The closed loop works and is reproducible.
- Placement alone changes the rack thermal distribution: total IT power and job timing are identical by construction.
- The X °C gap between packing and thermal-aware placement.
- How the result compares with power balance.
- What-if results, with their label.

**Not allowed:**
- Heterogeneous-zone (air / D2C / immersion) claims.
- The paper's numbers.
- PUE, plant-energy, carbon, lifetime, or degradation claims.
- Presenting the what-if as real Lassen behaviour.
- RL claims.

## 7. Validation invariants (asserted in tests or run checks)

1. Within a workload, total IT kW per power tick is identical across policies (≤ 1e-6 kW). Job start times are identical.
2. Every placement uses exactly `nodes_required` distinct nodes that were free at decision time.
3. Same (config, policy, seed) twice gives byte-identical `decisions.jsonl` and identical `intervals.parquet` values.
4. Σ per-rack kW = Σ `power_df["Sum"]` at every power tick.
5. Every run directory has a manifest containing: git SHA (and dirty flag), FMU SHA-256, workload SHA-256, config, policy, seed, and timings.

## 8. Known limitations to state in the demo

- One homogeneous liquid-cooled plant, with 1 CDU per rack.
- Neighbour coupling of about 0.02 °C.
- No PUE or plant power.
- FMUs run on Linux/Windows only.
- A capped warm-up snapshot that drifts.
- Replay jitter of 1.4e-4 °C under FMU state restore.
- Alibaba data lacks power, so job power is modelled.
- The pod → node mapping and time compression are assumptions.
- A single twin.
- 3 seeds.
