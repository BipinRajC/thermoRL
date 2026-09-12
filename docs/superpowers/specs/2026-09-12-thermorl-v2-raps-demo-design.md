# ThermoRL v2 × ExaDigiT/RAPS — Design Spec: Closed-Loop Digital-Twin Demo (FMU arm)

Date: 2026-09-12. Status: design approved in six sections by Bipin Raj C; awaiting spec review.
Scope of this spec: the **October 2026 closed-loop demo** on the Lassen digital twin. Later work (PPO, RC arm, multi-seed load sweep, Alibaba-calibrated resampling, ablations, paper-grade evaluation) is **out of scope** and gets its own specs; nothing here may block the minimum closed-loop demo.

Related documents: reconnaissance plan `/home/bipin/.claude/plans/thermorl-exadigit-raps-quirky-bird.md` (sections A–L, source-cited); ThermoRL paper `docs/thermoRL_ODA.pdf`.

Labels: VERIFIED (read in source or measured), PROVISIONAL (to be finalised by a named phase), DECISION (confirmed by Bipin), ASSUMPTION (documented, not tuned).

---

## 1. Purpose

Build a technically credible, reproducible closed loop in which RAPS (workload, queue, allocation, power) and ORNL's Lassen cooling FMU (per-rack thermal response) form the environment, and a rack-scoring controller decides placement:

```
job stream → RAPS Engine (queue, allocation, node/rack power)
          → adapter couples rack power into the Lassen FMU (same formula RAPS uses)
          → per-rack thermal state → normalised observation
          → rack-scoring controller → placement (exact node set) → RAPS executes
          → next power tick → next thermal state → …
```

The demo is falsification-oriented: it must be able to show that rack-level placement does **not** matter thermally on this twin, if that is what the twin says. No workload, heterogeneity, constraint, reward or metric may be tuned to manufacture an advantage.

## 2. Decision register (DECISION unless noted)

| # | Decision | Date |
|---|---|---|
| D1 | New uv project `thermoRL/thermorl-v2/`, package `thermorl2`, Python 3.12; `thermoRL/thermoRL-new/` frozen as reference, numpy kernels copied with attribution | 2026-09-12 |
| D2 | RAPS edits only via numbered `sim-raps/PATCHES.md` entries (problem, rationale, exact change, regression test); adapter-first; patch only for correctness, reproducibility, or a required experiment; verify the adapter cannot solve it cleanly first | 2026-09-12 |
| D3 | Two thermal arms behind one pluggable backend: **FMU arm first** (October demo), RC arm later; never mix outputs in one run; observables and THI defined explicitly per backend; divergent conclusions are a finding | 2026-09-12 |
| D4 | Thermal unit = physical rack/CDU (44 on Lassen). No 3-zone abstraction in the core; derivable later as ablation | 2026-09-12 |
| D5 | Common controller interface = permutation-invariant **rack-scoring policy**; all baselines are scoring functions; top-k greedy fill for multi-rack jobs; masked; DEFER as virtual candidate. Final RL/action/Lagrangian formulation **deferred** | 2026-09-12 |
| D6 | Decisions are **event-driven** on RAPS scheduler calls; thermal backend synchronised immediately after each authoritative RAPS power update; RL transition semantics support variable Δt (deferred) | 2026-09-12 |
| D7 | Demo scenario = 24 h **load ramp** normal → surge → sustained overload; identical deterministic job file for every controller; regime markers on plots | 2026-09-12 |
| D8 | RC arm (later) = per-rack RC with cooling-class attribute per rack, same interface; 3-zone RC only as ablation | 2026-09-12 |
| D9 | Primary THI candidate = baseline-normalised headroom form; paper's raw form kept as flag for parity; degradation term excluded | 2026-09-12 |
| D10 | Carbon disabled initially | 2026-09-12 |
| D11 | Test-first, phase-gated execution; Sonnet 5 executes small gated tasks from the implementation plan; strengthened stop-and-report rule (§12) | 2026-09-12 |
| D12 | Demo content = closed loop with heuristic controllers + reproducible static plots; no trained RL, no live animation required for October | 2026-09-12 |

## 3. Verified facts this design depends on

### 3.1 RAPS (`sim-raps/`, identical to upstream `ExaDigiT/RAPS@6c142bf` except `raps/dataloaders/marconi100.py`)
- Tick order (`raps/engine.py:773-845`, VERIFIED): each `time_unit` (1 s): admit arrivals → `prepare_timestep` (completions free nodes, TIMEOUT kills) → `add_eligible_jobs_to_queue` (submit_time ≤ t) → `scheduler.schedule(queue, running, t, accounts, sorted)` → **only if `t % time_delta == 0`**: `tick()` = per-job utilisation → `PowerManager.simulate_power` → `power_df` per rack (kW) → (RAPS cooling, if enabled) → yield `TickData` → `current_timestep += 1`.
- `Engine.__init__` stores `self.jobs = jobs` (`engine.py:276`); `run_simulation` reads it lazily (`:756-761`) → **jobs can be injected after construction**. The generator must be primed once so `prepare_system_state` (`:707`) runs before the first decision.
- `run_simulation` reads `self.scheduler.policy` (`:744`) to set `replay`; `prepare_system_state` temporarily sets `scheduler.policy = REPLAY`, `bfpolicy = None`, then restores (`:725-739`). Scheduler is only otherwise used via `.schedule(...)` (`:800`) → **`engine.scheduler` can be replaced after construction** with an object exposing settable `policy` (non-REPLAY) and `bfpolicy`.
- `ExclusiveNodeResourceManager.assign_nodes_to_job(job, t, policy, node_id=None)` (`raps/resmgr/default.py:41-60`): ignores `node_id`; with `policy == REPLAY` and `job.scheduled_nodes` set it allocates **exactly those nodes**; otherwise first-N lowest ids. `Scheduler.check_available_nodes` clears `scheduled_nodes` for non-replay policies (`schedulers/default.py:136`) → the drop-in scheduler must never call it.
- Geometry: `sc_shape = [num_cdus, racks_per_cdu, nodes_per_rack]` (`system_config.py:54-56`); Lassen `config/lassen.yaml`: 44 × 1 × 18 = 792 nodes, `missing_racks: []`, `down_nodes: []`, lossless SIVOC/rectifier, `power_update_freq: 20`, `power_cdu: 0`. Node id → rack = `id // 18`.
- `power_df` columns `["CDU", "Rack 1", "Sum", "Loss 1", "Loss"]` for Lassen; `total_power_kw = Σ Sum + NUM_CDUS·POWER_CDU/1000`.
- RAPS cooling coupling (`raps/cooling.py:145-166, 326-336`): input `simulator_1_datacenter_1_computeBlock_{i+1}_cabinet_1_sources_Q_flow_total = cdu_power_W[i] · COOLING_EFFICIENCY(0.945) / RACKS_PER_CDU(1)`; every `temperature_keys` entry ← `WET_BULB_TEMP` (290 K); `doStep(current_time, POWER_UPDATE_FREQ)`. Outputs = variables matching `.summary.`. `calculate_pue` indexes plant keys that **do not exist in the Lassen FMU** → RAPS's own cooling path would KeyError on Lassen (not used by this design).
- Seeding: `random.seed(seed); np.random.seed(seed+1)` guarded by `if sim_config.seed:` → seed 0 ignored (`engine.py:162-164`). `Job._id_counter` is a class attribute.
- `time_unit` and `time_delta` are independent (`sim_config.py:52-60`); `tick_return` is unbound if `timestep_start % time_delta != 0` (`engine.py:809-835`) → keep `timestep_start = 0`.

### 3.2 Lassen FMU (`ExaDigiT/POWER9CSM` `fmus/lassen.fmu`, 11.6 MB, Apache-2.0 OR MIT, VERIFIED 2026-09-12)
- FMI 2.0 **Co-Simulation** only; Dymola 2024x; `binaries/linux64/Simulator.so` present; loads and steps with fmpy on this machine.
- Flags: `canGetAndSetFMUstate=true`, `canSerializeFMUstate=true`, `canHandleVariableCommunicationStepSize=true`, **`canBeInstantiatedOnlyOncePerProcess=true`**, `canInterpolateInputs=true`.
- Inputs (89): 44 × `..._computeBlock_i_cabinet_1_sources_Q_flow_total` (W), 44 × `..._sources_T_Air` (K), 1 × `..._coolingTowerLoop_1_sources_T_ext` (K). Matches RAPS `config/lassen.yaml` exactly.
- Per-rack observables: `simulator[1].datacenter[1].computeBlock[i].cabinet[1].volume.medium.T` (K; V = 0.1 m³, init 303.15 K), `…cdu[1].summary.{T_sec_s_C, T_sec_r_C, T_prim_s_C, T_prim_r_C, V_flow_sec_GPM, V_flow_prim_GPM, m_flow_sec, m_flow_prim, p_*_psig, W_flow_CDUP_kW}`. Datacenter: `summary.V_flow_prim_GPM`, `m_flow_prim`. CDU control constants: `T_setpoint = 313.15 K` (40 °C), `dp_setpoint = 200 kPa`. **No per-CDU capacity parameter; no plant-level power summary.**
- Probe (2 h sim, 15 s steps, all racks 10 kW, rack 1 stepped to 40 kW at 1 800 s): 5.4 s wall (11 ms/step); rack-1 coolant 34.2 → 40.4 °C, 63 % rise in ≈ 750 s (τ ≈ 12 min); racks 2 and 44 unaffected except the shared plant transient; cold-start settling ≈ 1 h; first output sample contains initialisation artefacts.

### 3.3 Machine
Arch Linux, 8 cores, 15 GB RAM, RTX 3060 Laptop 6 GB (not needed for the demo), system Python 3.14, uv 0.12.6. No venv exists yet.

## 4. Architecture

```
thermoRL/thermorl-v2/                 uv project, Python 3.12
  pyproject.toml                      deps: numpy, pandas, pyarrow, pyyaml, fmpy, matplotlib, pytest;
                                      raps = editable path ../../sim-raps; torch NOT a demo dependency
  thermorl2/
    core/                             imports nothing from raps, fmpy, torch
      units.py                        Kelvin/Celsius/kW/seconds helpers (from thermoRL-new contracts/units.py)
      kernels/rc.py, kernels/thi.py   copied from thermoRL-new sim/kernels + golden tests (RC arm later; THI now)
      state.py                        RackResource, RackThermal, GlobalState, JobRequest, Observation
      scoring.py                      RackScorer protocol
      placement.py                    feasibility mask + greedy score-ordered fill → node list (pure)
      constraints.py                  headroom index, hinge C_r, violation flag (multiplier structure deferred)
      energy.py                       IT energy, FMU-observable CDU pump energy, (later) RC class-PUE energy — separate quantities
      metrics.py                      metric hierarchy (§10) computed from ledgers only
      ledger.py                       decision/interval/manifest schemas + parquet/JSONL writers
      heuristics/                     lowest_id.py, round_robin.py, load_balance.py, threshold_reactive.py, coolest_rack.py, (optional) lookahead.py
    thermal/
      base.py                         ThermalBackend protocol (§6.1)
      fmu_backend.py                  Lassen FMU via fmpy; owns the single instance; snapshot save/restore
      rc_backend.py                   (later spec) per-rack RC with cooling-class attributes
    raps_adapter/                     the only package importing raps
      engine_factory.py               build Engine (cooling off), inject jobs, attach scheduler, prime generator
      rack_geometry.py                node id ↔ rack via sc_shape; free nodes per rack from resource_manager
      rack_scheduler.py               RAPS Scheduler drop-in (§6.3)
      power_probe.py                  power_df → per-rack kW; reconciliation with total_power_kw
      runner.py                       episode runner: ticks, thermal sync, ledger, timing diagnostics
      workload/ramp_generator.py      scenario YAML + seed → parquet in raps job_dict schema
      workload/jobs.py                parquet → fresh raps.job.Job objects; id counter reset
    experiments/
      configs/demo_ramp_lassen.yaml   scenario, controller list, backend, seeds
      run_demo.py, plots.py           run all controllers on one file; figures with phase markers
  tests/unit, tests/integration (needs raps), tests/fmu (skips if FMU absent), tests/golden
models/POWER9CSM/                     cloned by Bipin; fmus/lassen.fmu at the path RAPS configs expect
```

Boundaries (approved with amendments):
- `core` is RAPS-, FMU- and torch-agnostic.
- `thermal` is the **sole** FMU-vs-RC boundary. `RackThermal` carries thermal state only (no duplicated power); rack power and resource state come from `raps_adapter` as `RackResource`.
- PUE/energy accounting lives in `core/energy.py`, not in thermal kernels.
- Controllers are scoring objects; PPO (later) replaces the scorer without touching `raps_adapter` or `thermal`.
- The architecture must allow later changes to formulation, metrics, constraints, action representation or thermal abstraction without restructuring.

## 5. Data flow and episode lifecycle

1. **Build.** `engine_factory.build(system="lassen", time_unit=1 s, time_delta=20 s, cooling=False, seed≥1, sim_time=24 h)`: construct `Engine` with a 1-job dummy synthetic workload (so `timestep_start = 0`), replace `engine.jobs` with fresh `Job`s from the parquet, replace `engine.scheduler` with `RackScheduler`, prime the generator once. VERIFIED seams §3.1. `time_delta = 20 s` reproduces RAPS's configured Lassen coupling interval (`power_update_freq: 20`); it is a config value, not a constant.
2. **RAPS cooling off; adapter owns the FMU.** After every RAPS power tick the runner computes per-rack kW from `power_df`, converts with **the same formula RAPS uses** (`W = kW·1000·0.945/1`, `T_Air = T_ext = 290 K` unless a scenario overrides), and calls `ThermalBackend.step(rack_kw, dt=20 s)`. A unit test asserts byte-equality of the adapter's FMU input vector with `ThermoFluidsModel.generate_runtime_values` output for the same `rack_power`. Consequence: no RAPS patch is needed for the FMU arm; the one-instance-per-process limit is honoured because the backend owns the instance for the process lifetime.
3. **Warm-up and reset.** First use: instantiate FMU, run at idle rack power (RAPS idle node power × 18, computed via `compute_node_power(0,0,0)` from the Lassen config) for a warm-up length determined in Phase 1 (≥ 1 h until |dT/dt| of every cabinet and the primary supply < 0.01 K/min), then `getFMUstate` → snapshot handle held **in memory** for the process lifetime (warm-up costs only a few seconds per process, so disk serialisation is deferred until multi-process training needs it). Every reset: `setFMUstate(snapshot)`. The idle temperatures derived from the snapshot are persisted to `artifacts/characterisation/t_idle.json` together with the FMU hash. Idle steady temperatures from the snapshot define `T_idle` (§7).
4. **Tick loop.** Runner drives `next(generator)` one simulated second at a time. RAPS calls `RackScheduler.schedule(...)` whenever it decides to (new arrivals, completions); the scheduler consults the controller synchronously using the **latest** `RackThermal` (≤ 20 s old) and current `RackResource`. On power ticks the runner syncs the backend, refreshes `RackThermal`, computes constraints, and writes an interval row.
5. **Deferred jobs.** A deferred job stays in `engine.queue` and is reconsidered on every scheduler call. A configurable periodic re-evaluation (`defer_reeval_s`, initial value 60 s, ASSUMPTION documented in the config: "one rack time-constant / 12, keeps deferral latency ≤ 1 min") guarantees progress when no events occur; it is fairness handling, separate from thermal cadence. Starvation guard: after `max_defers` (initial 10) the job is placed by the load-balance rule and flagged `forced=True` in the ledger.
6. **Cadence options.** `decision_cadence = "event"` (default) or `"fixed:300"` (paper parity; decisions allowed only at 300 s boundaries). Both via the same scheduler.
7. **End.** At 24 h the runner stops; unfinished jobs are counted as `running_at_end` / `queued_at_end`.
8. **Timing semantics to re-verify by test in Phase 1** (D6 amendment): order arrivals → completions → schedule → power → thermal within a second; that placement at second t is reflected in power at the next multiple of 20 s; that the controller never sees thermal state older than one coupling interval.

## 6. Interfaces

### 6.1 `ThermalBackend` (thermal/base.py)
```
class ThermalBackend(Protocol):
    n_units: int
    def reset(self) -> None                         # restore snapshot / steady state
    def step(self, unit_power_kw: np.ndarray, dt_s: float, ambient: Ambient) -> None
    def observe(self) -> RackThermal                # temperatures only + backend extras dict
    def global_observe(self) -> dict[str, float]    # backend-named globals, e.g. {"fmu.T_prim_supply_C": ...}
    def runtime_s(self) -> float                    # cumulative backend wall time (diagnostic)
RackThermal: t_c: float[n]  (per-rack temperature, °C; FMU: cabinet coolant volume T), extras: dict[str, float[n]]
Ambient: t_air_k: float, t_ext_k: float   (defaults 290.0 K and 290.0 K, matching RAPS WET_BULB_TEMP; scenario-overridable)
```
Backends that support snapshot rollouts (FMU) additionally expose `save_state() -> handle` / `restore_state(handle)`; any lookahead controller must restore the live state before returning, and the runner asserts the post-decision `observe()` equals the pre-decision one.
FMU extras: `T_sec_r_C`, `T_sec_s_C`, `W_flow_CDUP_kW`, `V_flow_sec_GPM`. FMU globals: `T_prim_supply_C`, `T_prim_return_C`, `V_flow_prim_GPM`. RC (later) globals are named `rc.*` and are **not** asserted equivalent to FMU globals.

### 6.2 `RackScorer` (core/scoring.py)
```
class RackScorer(Protocol):
    name: str; version: str; config: dict         # logged with every decision
    def score(self, obs: Observation, job: JobRequest, feasible: np.ndarray[bool]) -> Scores
Scores: rack: float[n] (−inf where infeasible), defer: float
```
Placement (core/placement.py, pure): `place(scores, free_nodes_per_rack, nodes_required) -> Placement{racks: list[int], nodes: list[int], spanned: bool, rule: "single_best" | "greedy_span"}`: if some feasible rack has `free ≥ nodes_required`, pick the highest-scoring such rack; else fill racks in descending score until met; nodes within a rack = lowest free ids. If `defer` exceeds every rack score, or no placement is possible, return `DEFER`. The rule is logged per decision.

Feasibility uses only decision-time information: current free nodes per rack and current queue state. Never `expected_run_time` or `end_time` of running jobs; "time to next completion" uses `start_time + time_limit − now` (requested limit), which a real scheduler knows.

### 6.3 `RackScheduler` (raps_adapter/rack_scheduler.py)
Drop-in for RAPS: attributes `policy = PolicyType.FCFS`, `bfpolicy = None` (settable, because `prepare_system_state` writes them); `schedule(queue, running, current_time, accounts=None, sorted=False)`: FCFS by `submit_time`; for each job: build `Observation` (§7), call `controller.score`, `place`; on placement set `job.scheduled_nodes = nodes` and call `resource_manager.assign_nodes_to_job(job, current_time, PolicyType.REPLAY)`, then `running.append(job); queue.remove(job)`; on DEFER increment `job.defer_count`. Never calls `check_available_nodes`. Records every decision (scores, mask, placement, controller identity, latency).

### 6.4 Observation (core/state.py) — controller input, normalised
- Per rack (n × F_r): `headroom` (= THI_r as defined in §7, under the configured `thi_form`), `free_frac = free/18`, `power_frac = P_r/P_max`, `n_running`, `t_next_limit_frac` (min over running jobs of remaining requested time / 8 h, 1 if none), `feasible`.
- Job: `nodes_frac = n/18`, `spans = n > 18`, `est_power_per_node_frac` (RAPS `compute_node_power(cpu_util, gpu_util, 0)` / peak), `runtime_limit_frac` (time_limit / 8 h), `wait_frac`, `priority_frac`, `defer_count/ max_defers`.
- Global: backend globals normalised with documented bounds (FMU: `T_prim_supply_C` between snapshot idle value and `T_max`), `total_power_frac`, `queue_depth/cap` (cap 500), `queued_power_frac`, `tod_sin`, `tod_cos`. Carbon: absent (D10).
Raw values are stored in the ledger; only normalised features reach the controller.

## 7. Thermal headroom index and constraint (FMU arm)

- **Primary (D9):** `THI_r = 1 − max( (T_r − T_idle,r) / (T_max − T_idle,r), P_r / P_max )`, clipped to [−0.5, 1]. `T_r` = cabinet coolant temperature (°C). `T_idle,r` = per-rack warmed-idle coolant temperature from the snapshot (Phase 1 measures it; PROVISIONAL). `P_max` = 18 × peak node power from the Lassen power config via `compute_node_power(CPUS_PER_NODE, GPUS_PER_NODE, 1)`.
- **Parity flag:** `thi_form = "paper_raw"` gives `1 − max(T_r/T_max, P_r/P_max)` with T in °C, as in the paper. Degradation excluded in both.
- **`T_max = 45 °C` (ASSUMPTION, provenance to be written into the spec by Phase 1):** coolant temperature limit; rationale = upper bound of ASHRAE liquid-cooling class W45, distinct from the FMU's 40 °C CDU supply setpoint (a control target, not a safety limit). Phase 1 must (a) characterise warmed-idle and operating coolant ranges under uniform 0/25/50/75/100 % rack power so the normalisation is numerically well behaved, (b) document what 45 °C means semantically for this model, (c) never adjust it based on scheduler outcomes. If the characterisation shows racks cannot approach 45 °C at 100 % load, that is reported as-is (the constraint may not bind on this twin) — not fixed by lowering the limit.
- **Constraint:** `C_r = max(0, ε − THI_r)`, `ε = 0.10` (paper). Violation flag `THI_r < ε` per rack per interval. Multiplier structure deferred (D5).

## 8. Workload generator and ramp scenario (D7)

- `ramp_generator.generate(scenario_yaml, seed) -> parquet` with columns = RAPS `job_dict` fields: `id, nodes_required, cpu_trace (scalar, CPUs at max ∈ [0, 2]), gpu_trace (scalar, GPUs at max ∈ [0, 4]), submit_time (s), expected_run_time (s), time_limit (s), priority, start_time=None, end_time=None, partition=None` plus metadata (scenario, seed, phase boundaries, targets, file hash).
- Distributions (ASSUMPTION, all in the YAML): nodes ~ discretised log-normal clipped [1, 64]; cpu/gpu util ~ Beta (parameters in YAML); run time ~ log-normal median 30 min clipped [60 s, 8 h]; `time_limit = ceil_minutes(run_time × U(1.1, 2.0))`; priority ~ uniform int.
- Offered load: `ρ_N(t) = λ(t)·E[nodes]·E[runtime] / N_usable`, `N_usable = total_nodes − |down_nodes|` from the RAPS system config (Phase 1 verifies = 792 for Lassen). `ρ_P(t) = λ(t)·E[P_job]·E[runtime] / (N_usable·p_peak)`. Arrivals: non-homogeneous Poisson by thinning, single `default_rng(seed)`.
- Ramp phases (PROVISIONAL, D7): normal ρ_N ≈ 0.5 (0–8 h), surge ≈ 1.0 (8–14 h), sustained overload ≈ 1.5 (14–24 h), 10-min linear transitions. **Phase 1 characterisation finalises the three targets from the twin's uniform-load response, never from scheduler results.**
- Identity: one parquet per (scenario, seed); SHA-256 in every ledger row, manifest and figure caption; `Job._id_counter` reset per episode.
- Logged alongside targets: realised arrival rate, realised offered load, running nodes, running power, queue depth (§10).
- Phase 1 verifies RAPS's interpretation of `submit_time`/`start_time=None`/`end_time=None` so generated jobs enter the queue as fresh arrivals.

## 9. Controllers (demo set, all via §6.2)

| id | score | role |
|---|---|---|
| `lowest_id` | −rack_index | reproduces RAPS first-N packing (reference) |
| `round_robin` | rotating cursor | paper's primary baseline |
| `load_balance` | free_frac (tie: −power_frac) | **thermal-blind control** — key comparison |
| `threshold_reactive` | exclude racks with T_r > 0.9·T_max until < 0.8·T_max, then `lowest_id` | paper's alarm-style baseline |
| `coolest_rack` | THI_r | **primary thermal-aware heuristic** |
| `lookahead` (optional) | min THI after k-min FMU snapshot rollout per candidate | only if Phase 1 cost allows; must not block demo |

RAPS-native FCFS through RAPS's own default scheduler is run once as an **external reference** (different execution path), never as the primary comparison.

## 10. Metric hierarchy (pre-specified; computed from ledgers only)

- **Primary thermal-safety metric:** violation fraction = (rack-intervals with THI_r < ε) / (racks × intervals), per phase and overall.
- **Secondary thermal (pre-specified):** violations per completed job; violation magnitude integral Σ C_r·Δt; time fraction with T_r > 0.9·T_max; per-rack breakdown; **stress exposure** = degree-seconds above `T_idle + 0.85·(T_max − T_idle)` — an exposure proxy, never a lifetime or lifetime-extension measure.
- **Performance:** jobs completed, node-hours delivered, mean and p95 wait, bounded slowdown, running nodes, realised utilisation, queue depth over time, jobs running/queued at end.
- **Load bookkeeping:** target ρ_N/ρ_P per phase, realised arrival rate, realised offered load, actual utilisation — reported separately.
- **Energy (kept distinct, never summed into a "facility" total for the FMU arm):** IT energy (RAPS `RunningStats.total_energy_consumed`); FMU-observable CDU pump energy (Σ_r W_flow_CDUP_kW·Δt); total facility energy = **not available** for the Lassen FMU (no plant power summary) and is reported as such.
- **Diagnostics:** placement-independence = fraction of decisions where `coolest_rack` and `load_balance` would choose different racks on the same observation (computed by scoring both on every logged observation); realised rack-temperature spread; controller identity (name, version, config hash) per decision.
- **Computational:** controller decision latency (per decision), thermal-backend runtime, RAPS runtime, total wall-clock per episode.

Metrics are not selected after seeing outcomes.

## 11. Testing and phase gates

Tiers: **unit** (no raps/FMU): kernels vs golden vectors, `placement.place`, `rack_geometry`, THI both forms, metrics on synthetic ledgers, generator determinism (same seed → identical hash) and realised-vs-target load within 5 % over 24 h; **integration** (raps): engine build, job injection, scheduler drop-in allocates exact nodes, Σ per-rack kW reconciles with `total_power_kw` (1e-6), two identical seeds → bit-identical ledgers, TIMEOUT kills still active (policy ≠ REPLAY); **fmu** (skip if `models/POWER9CSM/fmus/lassen.fmu` absent): instance lifecycle, snapshot restore reproduces trajectory, single-rack step reproduces §3.2 probe within 5 %, adapter input vector equals RAPS's `generate_runtime_values`.

| Phase | Gate (all must pass) |
|---|---|
| 0 Environment | `uv sync` in `thermorl-v2`; `raps run --system lassen -t 10m --noui -w random -n 50 --seed 1` exits 0; `python -c "import fmpy, raps"` from the project interpreter; FMU at expected path |
| 1 Characterise | timing-semantics test (§5.8) green; end-to-end cost of a 24 h idle episode measured (RAPS + FMU separately); uniform-load FMU sweep 0/25/50/75/100 % → `T_idle,r`, operating range, load at which any rack reaches 45 °C (or report it cannot); `N_usable` confirmed; warm-up length determined; job-field semantics verified. **Stop and report** the numbers before Phase 3 uses them |
| 2 Adapter | integration + fmu tiers green; **causal coupling check**: on a 2 h smoke file whose jobs all fit in one rack (≤ 18 nodes), run `lowest_id` vs a forced "all-to-rack-44" scorer (+∞ for rack 44); pass if rack-44 mean power differs between the two runs by > 5 kW while rack-1 differs by > 5 kW in the opposite direction, and rack-44 coolant temperature in the forced run rises with a 63 % time within 20 % of the §3.2 probe while rack-1 coolant stays within 0.5 °C of idle — a controlled, not aggregate, test |
| 3 Controllers + ramp | five heuristics pass a shared contract test; ramp generator produces the demo parquet with finalised phases; metrics + manifest produced on a 2 h smoke run |
| 4 Demo | **minimum-demo gate:** `coolest_rack` completes the full 24 h loop with reproducible plots even if another controller is incomplete; then all controllers on the same file; figures with phase markers; a one-page result note that states plainly whether thermal state mattered |

## 12. Executor protocol (D11)

The implementation plan lists small tasks; each names files, existing functions with paths, tests to write first, the exact command, and expected output. **Stop and report** (do not improvise) on: any unexpected test failure; any discovery contradicting this spec or the architecture; missing or semantically different FMU observables; questionable physical assumptions; any RAPS patch larger than a few lines or not covered by D2; anything requiring a research/design decision (phase loads, T_max provenance, THI form, cadence, Lagrangian structure); Phase 1 characterisation numbers. Fable reviews at every gate.

## 13. Open items resolved by named phases

| Item | Phase |
|---|---|
| Warm-up length; `T_idle,r`; operating temperature range; whether 45 °C is reachable | 1 |
| End-to-end cost; whether `lookahead` is affordable | 1 |
| Final ramp phase targets | 1 → 3 |
| `N_usable` semantics | 1 |
| RAPS job-field semantics for fresh arrivals | 1 |
| Whether a scheduler call with multiple jobs is one or several RL transitions | later RL spec |
| Multiplier structure (per-rack / pooled / class) | later RL spec, after RC vs FMU characterisation |
| RC-arm global observable analogue to plant supply temperature | RC spec |

## 14. Risks specific to the demo

| Risk | Mitigation |
|---|---|
| Rack placement barely affects thermal outcomes in a high-flow homogeneous loop | Placement-independence diagnostic; report as finding; do not add artificial heterogeneity |
| 45 °C unreachable at 100 % load ⇒ constraint never binds | Report; do not lower the limit; consider plant-level constraint as a *separate, documented* later formulation |
| End-to-end cost too high (86 400 RAPS iterations + 4 320 FMU steps per day) | Measure in Phase 1; options: shorter demo horizon, `time_unit` 5 s (documented), profiling |
| One FMU instance per process | Backend owns instance for process lifetime; no re-instantiation on reset |
| `prepare_system_state` writes scheduler attributes | Settable `policy`/`bfpolicy` on `RackScheduler`; test |
| RAPS global RNG / seed 0 / `Job._id_counter` | File-based workloads, seeds ≥ 1, counter reset, bit-identity test |
| Adapter coupling drifts from RAPS's formula | Equality test against `generate_runtime_values` |
| Executor reinterprets an under-specified step | §12 stop-and-report; gates reviewed by Fable |
