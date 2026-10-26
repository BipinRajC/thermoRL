# ParasParam Closed-Loop Demo — Implementation Plan

> **For agentic workers (Sol 6.1):** Execute task by task, in order. Steps use checkbox (`- [ ]`) syntax. Sections marked **CHECKPOINT** are mandatory stops: write the checkpoint report, commit it, and wait for steering. Between checkpoints, keep going unless a stop condition from Global Constraints applies.

**Goal:** Produce the first FMU-backed closed-loop thermal result within 2 days, then grow it into a reproducible demo with visuals in about 1 week. The demo compares packing, node-balance, power-balance and thermal-aware placement on the Lassen twin.

**Architecture:** Extend `thermoRL/thermorl-v2/thermorl2`.
- RAPS runs Lassen with its own cooling turned off.
- `EpisodeRunner` steps the existing `FmuBackend` at every 20 s power tick.
- A `PlacementScheduler` drop-in sets exact nodes through RAPS's REPLAY allocation path.
- All policies share one FCFS queue, so timing and total power are identical by construction and only the spatial placement differs.
- Metrics and plots are computed only from per-run ledgers.

**Tech stack:** Python 3.12 (uv), editable `raps` (`../../sim-raps`), fmpy 0.3.x, numpy, pandas, pyarrow, pyyaml, matplotlib (+ pillow for GIF), pytest. Viz uses Vite + TypeScript + three.js (copied from `thermoRL/thermoRL-new/viz`).

**Spec:** `docs/superpowers/specs/2026-10-27-parasparam-demo-design.md`. Read it first; this plan argues from it. Background reading:
- `docs/2026-10-26-thermorl-investigation-findings.md`
- `docs/2026-10-27-thermorl-demo-strategy.md`

## Global Constraints

- **Runtime.** FMU work runs only on the **Arch Linux x86-64** machine. The FMUs have no macOS binary.
- **Location.** All paths are relative to the repo root. Python commands run from `thermoRL/thermorl-v2` with `uv run …`.
- **Import boundaries.** `core/` must not import `raps`, `fmpy` or `torch`. Only `raps_adapter/` imports `raps`. Only `thermal/fmu_backend.py` imports `fmpy`.
- **No edits to `sim-raps/`.** If one seems necessary, stop and report.
- **FMU.**
  - Path: `models/POWER9CSM/fmus/lassen.fmu`.
  - SHA-256: `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`.
  - One FMU instance per OS process. Never re-instantiate within a process. Run many simulations as separate processes.
- **RAPS settings.** Lassen with `time_delta` 20 s, `time_unit` 1 s, `cooling` false, and `timestep_start` 0.
- **Seeds.** Use seeds ≥ 1; RAPS ignores 0. Reset `raps.job.Job._id_counter = 0` before building each run's jobs.
- **Coupling constants.** 0.945 heat factor, 1 rack per CDU, 290 K default ambient. Always read them from the RAPS legacy config through `CouplingParams.from_legacy_config`.
- **Pre-registration.** Thresholds, metrics, policies and scenarios are fixed in spec §3–§4. Changing any of them after results exist is a **stop condition**.
- **Run manifest.** Every run writes `manifest.json` containing: git SHA and dirty flag, FMU SHA-256, workload SHA-256, the full config, policy, seed, and timings (`raps_s`, `fmu_s`, `total_s`).
- **Artifacts.** Commit code, configs, probe and run summaries, figures, and run ledgers that are smaller than 25 MB per run directory. Gitignore anything larger and record its path and hash in the checkpoint report. The Mac reads results through git.
- **Stop conditions (demo mode):**
  - a test failure you cannot explain;
  - a result contradicting the spec's mechanics (for example, total IT kW differs across policies);
  - a needed change to a pre-registered item;
  - a needed RAPS patch;
  - a probe decision rule outcome of **STOP**.
  - Otherwise, fix forward and continue.
- **Do not touch** `docs/prompt.md`.
- **Branch.** Work on `feat/parasparam-demo`, created from `feat/thermorl2-phase0-env`. Commit after every task with the message given.

## Review Focus

1. **Many arrivals within one 20 s window.** The thermal view and power ticks are stale between power ticks.
   - `power_balance` must spread back-to-back jobs, because it updates committed kW on every placement.
   - `coolest_rack` is expected to herd. Pin that behaviour so it is visible rather than accidental.
   - Owner: Task 6.
2. **Jobs larger than one rack (> 18 nodes), and fragmented free nodes.** The placement must return exactly `n` distinct, currently free nodes, and must span racks in score order. Owner: Task 5.
3. **`prepare_system_state` flips `scheduler.policy` to REPLAY and back.** The drop-in must have settable attributes and must behave as FCFS afterwards. Owner: Task 6.
4. **Determinism.** The same config, policy and seed must produce byte-identical `decisions.jsonl`. Watch the `Job._id_counter` reset, single-RNG workload generation, and dict ordering in JSON output. Owner: Task 8.
5. **Cross-policy invariants.** For one workload, total IT kW per tick and job start times must be identical across policies. If not, the queue discipline leaked into placement. Owner: Task 9.

## Schedule (target)

| Day | Tasks | Gate |
|---|---|---|
| 1 | 1 (env + Task 1.5 close), 2, 3 (physics probes) | **CHECKPOINT C1**: physics reality check |
| 2 | 4, 5, 6, 7, 8 (vertical slice) | **CHECKPOINT C2**: first closed-loop result |
| 3 | 9, 10, 11 (metrics, plots, G4 synthetic) | **CHECKPOINT C3**: Conservative demo complete |
| 4 | 12, 13 (Alibaba-derived, G4) | **CHECKPOINT C4** |
| 5 | 14 (viz) | — |
| 6 | 15 (what-if, only if G3 passed) | **CHECKPOINT C5** |
| 7 | 16 (packaging, results note, runbook) | Final review |

## Checkpoint report format (all checkpoints)

Write `docs/checkpoints/C<n>-<slug>.md` containing:
- what ran (exact commands);
- git SHA;
- key numbers in a table;
- figure paths;
- each decision rule and its outcome (GO / WEAK / STOP or equivalent);
- anomalies;
- what you will do next if approved.

Commit it, push the branch, and stop.

---

## Phase 0 — Physics reality check (Day 1)

### Task 1: Arch environment and Task 1.5 closure (option B)

**Files:**
- Modify: `thermoRL/thermorl-v2/tests/fmu/test_fmu_backend.py` (historical physical-response test only)
- Modify: `thermoRL/thermorl-v2/tests/fmu/test_direct_backend_replay.py` (intra-process assertion only)
- Modify: `thermoRL/thermorl-v2/README.md` (add a "Task 1.5 closure (option B)" section)
- Modify: `docs/superpowers/proposals/2026-09-29-task-1-5-backend-closeout.md` (append a dated "Closed under option B, 2026-10-27" note)

- [ ] **Step 1:** On Arch, run `git checkout -b feat/parasparam-demo` (from `feat/thermorl2-phase0-env`, after pulling). Then, from `thermoRL/thermorl-v2`, run `uv sync`.
  - Expected: success on CPython 3.12.
- [ ] **Step 2:** Run `uv run pytest tests/unit tests/integration -q`.
  - Expected: `19 passed`.
- [ ] **Step 3:** Mark `test_single_rack_step_is_local_and_matches_probe` with `@pytest.mark.xfail(strict=True, reason="Historical cold-start probe bound (500–1000 s); warmed-state t63 measured 1240 s. Retained unchanged as a record; see 2026-10-27 spec P1.")`.
  - The test body must stay unchanged.
- [ ] **Step 4:** In `test_backend_matches_independent_direct_fmu_with_snapshot_replay`, replace the within-process `atol=1e-9` replay-1-vs-replay-2 assertion with the option-B assertion:
  - for each key, `backend_replay_delta = backend_replay2 − backend_replay1` must equal `direct_replay_delta = direct_replay2 − direct_replay1` with `atol=1e-6`;
  - record `max_abs_restore_jitter_c` in the test's manifest output.
  - Keep every direct-vs-backend `atol=1e-6` assertion unchanged.
- [ ] **Step 5:** Run `uv run pytest tests/fmu -v`.
  - Expected: lifecycle and reset tests pass; the replay test passes; the historical test reports `XFAIL`.
  - If anything else fails: stop and report.
- [ ] **Step 6:** Write the README section. It must record the 1.43e-4 °C restore jitter as a documented limitation and name the direct-FMU-equals-backend agreement as the correctness evidence.
- [ ] **Step 7:** Commit:
  ```
  feat(thermal): FMU backend with single-instance guard, warm-up snapshot reset, RAPS-identical stepping (Task 1.5 closed under option B)
  ```

### Task 2: Per-rack room-air input and RAPS power-model helpers

**Files:**
- Modify: `thermorl2/core/state.py` — add the `Ambient` field
- Modify: `thermorl2/raps_adapter/coupling.py` — per-unit `T_Air` mapping
- Create: `thermorl2/raps_adapter/power_model.py`
- Test: `tests/unit/test_coupling.py` (extend), `tests/integration/test_power_model.py`

**Interfaces (produces):**
- `Ambient(t_air_k: float = 290.0, t_ext_k: float = 290.0, t_air_k_by_unit: tuple[float, ...] | None = None)`. When set, `t_air_k_by_unit` has length `num_cdus`.
- `rack_kw_to_fmu_inputs(rack_kw, p, ambient)`:
  - Behaviour is unchanged when `t_air_k_by_unit is None`.
  - Otherwise, key `simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_T_Air` gets `t_air_k_by_unit[i-1]`, and `_T_ext` still gets `t_ext_k`.
- `legacy_config(system: str = "lassen") -> dict` returns `get_system_config(system).get_legacy()`.
- `node_power_kw(cfg: dict, cpu_util: float, gpu_util: float) -> float` returns `compute_node_power(cpu_util, gpu_util, 0, cfg)[0] / 1000`.
- `rack_power_bounds(cfg: dict) -> tuple[float, float]` returns `(idle_kw, peak_kw)`:
  - per rack: `NODES_PER_RACK × node_power_kw(cfg, u, g) + CHASSIS_PER_RACK × SWITCHES_PER_CHASSIS × POWER_SWITCH / 1000`;
  - idle uses `u = g = 0`; peak uses `u = CPUS_PER_NODE` and `g = GPUS_PER_NODE`.
- `job_increment_kw(cfg: dict, cpu_util: float, gpu_util: float, n_nodes: int) -> float` returns `n_nodes × (node_power_kw(cfg, cpu_util, gpu_util) − node_power_kw(cfg, 0, 0))`.

- [ ] **Step 1: Failing tests.**
  - `test_per_unit_air_temperature_maps_by_index`: build 44 values `290 + i`, and assert the `computeBlock_34` `T_Air` input equals `323.0` and `_T_ext` equals `ambient.t_ext_k`.
  - `test_default_ambient_unchanged`: the existing equality-with-RAPS test still passes.
  - `test_rack_power_bounds_lassen`: assert `10.0 < idle < 12.0` and `30.0 < peak < 38.0`, and print both.
  - `test_job_increment_zero_at_idle`: `job_increment_kw(cfg, 0, 0, 5) == 0`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_coupling.py tests/integration/test_power_model.py -v`.
  - Expected: FAIL (missing attribute or module).
- [ ] **Step 3:** Implement the interfaces above.
- [ ] **Step 4:** Run the same command, then `uv run pytest tests/unit tests/integration -q`.
  - Expected: all pass.
  - Record idle and peak to 3 decimals in the commit body. (The investigation computed ≈ 10.86 and ≈ 34.4 kW; the original plan's hand calculation said ≈ 35.9 kW. Report the measured value.)
- [ ] **Step 5:** Commit:
  ```
  feat(adapter): per-rack room-air ambient input and RAPS power-model helpers
  ```

### Task 3: FMU-only physics probes G1, G2, G3 → CHECKPOINT C1

**Files:**
- Create: `thermorl2/experiments/__init__.py`, `thermorl2/experiments/provenance.py`, `thermorl2/experiments/probes.py`
- Test: `tests/unit/test_probe_vectors.py`, `tests/unit/test_provenance.py`
- Output: `thermoRL/thermorl-v2/artifacts/probes/{g1_uniform,g2_packed_vs_spread,g3_room_air}/`

**Interfaces (produces):**
- `provenance.py`:
  - `git_state() -> dict` with keys `sha` and `dirty`;
  - `sha256_file(path: Path) -> str`;
  - `write_manifest(out_dir: Path, **fields) -> Path`.
  - Later tasks reuse these.
- `probes.py`:
  - `uniform_vector(n: int, idle_kw: float, peak_kw: float, f: float) -> np.ndarray`
  - `packed_vector(n: int, idle_kw: float, peak_kw: float, total_kw: float) -> np.ndarray`
    - Racks `0..k-1` at `peak_kw`, rack `k` at the remainder, the rest at `idle_kw`.
    - `sum == total_kw` within 1e-9.
    - `idle_kw ≤ each element ≤ peak_kw`.
  - CLI: `uv run python -m thermorl2.experiments.probes {g1,g2,g3} --out <dir>`.
  - Each probe:
    1. instantiates one `FmuBackend`;
    2. runs `warm_up(idle vector, Ambient(), dt_s=20, max_s=7200)`;
    3. for each branch: `reset()`, then 540 steps of 20 s (3 h), recording all 44 `t_c` and `extras["W_flow_CDUP_kW"]` at every step.
- Outputs per probe:
  - `series.csv` with columns `branch,t_s,rack,t_c,pump_kw`;
  - `summary.json` (keys below);
  - one PNG;
  - `manifest.json`, including the FMU SHA, the git state, and `warmup_used_s`.
- `summary.json` keys:
  - **G1:** `levels: [{f, rack_kw, mean_c, min_c, max_c, t63_s}]`, `fit: {a_c, b_c_per_kw, r2}`, `tau_s` (median `t63_s` over f ∈ {0.25, 0.5, 0.75}, measured from the idle snapshot), `t_hot_c` (fit evaluated at the f = 0.9 rack kW), `reaches_40c: bool`, `reaches_45c: bool`, `rack_spread_at_f1_c`.
  - **G2:** `total_kw`, `k_full_racks`, `packed: {max_c, mean_c, spread_c}`, `spread: {…}`, `delta_max_c`, `decision: "GO"|"WEAK"|"STOP"`.
  - **G3:** `affected_racks: [33..43]`, `delta_affected_c`, `delta_unaffected_c`, `decision: "USABLE"|"NOT_USABLE"`.
- All last-window statistics use the final 30 min, except G1's `mean_c/min_c/max_c`, which use the final 15 min.

**Protocols (from spec §4, verbatim; do not alter):**

| Probe | Branches | Rule |
|---|---|---|
| G1 | 5 levels, all racks at `uniform_vector(44, idle, peak, f)` for f ∈ {0, 0.25, 0.5, 0.75, 1.0} | `t63` = first time the mean-rack rise reaches 63.2 % of its final-15-min rise |
| G2 | `packed`: `packed_vector(44, idle, peak, 44 × uniform(f = 0.6))`; `spread`: `uniform_vector(…, 0.6)` | `delta_max_c` = packed max − spread max. **GO ≥ 2.0**, **WEAK 1.0–2.0**, **STOP < 1.0** |
| G3 | `control`: f = 0.6, 290 K; `hot_row`: f = 0.6, `t_air_k_by_unit` = 308.15 for racks 33–43 (0-based), 290 for the rest | **USABLE** if the mean Δ over affected racks is ≥ 1.0 °C |

- [ ] **Step 1: Failing unit tests.**
  - `packed_vector` sum equals the total; bounds hold; `k_full_racks` is correct for `total = 3.5·peak + 40.5·idle` (expect 3 full racks plus a partial).
  - `uniform_vector` at f = 0 equals idle, and at f = 1 equals peak.
  - `write_manifest` writes valid JSON containing the given fields.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_probe_vectors.py tests/unit/test_provenance.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement `provenance.py` and `probes.py`.
  - The idle and peak values come from `rack_power_bounds(legacy_config())`.
  - G3 secondary lever: also write `g3_room_air/candidate_cdu_parameters.txt`. List the FMU variables whose causality is `parameter`, whose variability is `tunable`, and whose name contains `computeBlock[1].cdu[1]`. List them only; do not use them.
- [ ] **Step 4:** Run the unit tests, then the three probes, each as its own process:
  ```
  uv run python -m thermorl2.experiments.probes g1 --out artifacts/probes/g1_uniform
  uv run python -m thermorl2.experiments.probes g2 --out artifacts/probes/g2_packed_vs_spread
  uv run python -m thermorl2.experiments.probes g3 --out artifacts/probes/g3_room_air
  ```
  - Expected: each finishes in under 2 min wall time and writes all four outputs.
  - Re-run G2 once and confirm `summary.json` is byte-identical.
- [ ] **Step 5:** Commit:
  ```
  feat(experiments): FMU physics probes G1 uniform sweep, G2 packed-vs-spread, G3 room-air lever
  ```

**CHECKPOINT C1 — physics reality check.** Write `docs/checkpoints/C1-physics.md` with:
- the G1 table and fit, `tau_s`, `t_hot_c`, and whether 40 °C or 45 °C is reached;
- G2 `delta_max_c` and its decision;
- G3 deltas and its decision;
- the paths of the three PNGs.

Then stop. A G2 decision of **STOP** is the first point at which the demo story can be falsified. Steering decides the replan.

---

## Phase 1 — First closed-loop vertical slice (Day 2)

### Task 4: Engine factory, power probe, timing semantics, cost benchmark

**Files:**
- Create: `thermorl2/raps_adapter/engine_factory.py`, `thermorl2/experiments/bench.py`
- Test: `tests/integration/test_engine_factory.py`, `tests/integration/test_timing_semantics.py`

**Interfaces (produces):**
- `EngineSpec(system: str = "lassen", sim_time: str = "6h", time_delta: str = "20s", seed: int = 1)` — frozen dataclass.
- `build_engine(spec: EngineSpec, jobs: list | None = None) -> raps.engine.Engine`
  - Calls `SingleSimConfig.model_validate` with `{"system", "time", "time_delta", "workload": "random", "numjobs": 1, "seed", "noui": True, "output": "none", "cooling": False, "scheduler": "default", "policy": "fcfs"}`.
  - If `jobs` is not None: sets `engine.jobs = jobs` and `engine.total_initial_jobs = len(jobs)`.
  - Asserts `engine.timestep_start == 0` and `engine.time_delta == 20`.
  - Does **not** create the generator.
- `rack_kw_from_power_df(power_df: pd.DataFrame, racks_per_cdu: int) -> np.ndarray`
  - Concatenates columns `Rack 1..Rack racks_per_cdu`, row-major, into an array of length `num_cdus × racks_per_cdu`.
- `is_power_tick(tick) -> bool` returns `tick.power_df is not None`.

- [ ] **Step 1: Failing tests.**
  - `test_build_engine_lassen_defaults`:
    - `cooling_model is None`;
    - `config["NUM_CDUS"] == 44` and `config["NODES_PER_RACK"] == 18`.
  - `test_idle_power_reconciles` (2 min, `jobs=[]`):
    - 6 power ticks;
    - per tick, `rack_kw.shape == (44,)`;
    - `abs(rack_kw.sum() − power_df["Sum"].sum()) < 1e-6`;
    - `abs(rack_kw.mean() − rack_power_bounds(cfg)[0]) < 0.05`.
  - `test_arrival_at_t_scheduled_at_t_powered_at_next_delta`:
    - use a minimal recording drop-in scheduler that places on the lowest free nodes via `assign_nodes_to_job(job, t, PolicyType.REPLAY)` after setting `scheduled_nodes`;
    - one 18-node job with `cpu_trace=2.0`, `gpu_trace=4.0`, `submit_time=25`, `expected_run_time=600`, `time_limit=1200`;
    - assert the scheduler was called at t = 25;
    - assert the first power tick with `rack_kw[0] > 20` is t = 40.
    - **If either assertion fails, stop and report the observed values.**
  - `test_timeout_kill_active_with_dropin`: a job with `time_limit < expected_run_time` is killed (`engine.jobs_killed == 1`).
- [ ] **Step 2:** Run `uv run pytest tests/integration/test_engine_factory.py tests/integration/test_timing_semantics.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement `engine_factory.py`, then `bench.py`.
  - `bench.py` CLI: `uv run python -m thermorl2.experiments.bench --hours 6`.
  - It builds an idle engine, warms the FMU, and steps the FMU at every power tick.
  - It prints JSON `{raps_s, fmu_s, total_s, power_ticks}`.
- [ ] **Step 4:** Run the tests (expected: PASS), then run the bench.
  - **Horizon rule (spec §3.3):** if `total_s × 2 × 2 ≤ 300` (a 12 h run with jobs, assuming 2× overhead), set `horizon_h: 12` in later configs; otherwise use 6.
  - Record the numbers and the chosen horizon in the commit body.
- [ ] **Step 5:** Commit:
  ```
  feat(adapter): engine factory, per-rack power probe, timing-semantics tests, cost benchmark
  ```

### Task 5: Placement rule and scorers (pure core)

**Files:**
- Create: `thermorl2/core/placement.py`, `thermorl2/core/scorers.py`
- Test: `tests/unit/test_placement.py`, `tests/unit/test_scorers.py`

**Interfaces (produces):**
- `place(scores: np.ndarray, free_nodes_by_rack: list[list[int]], n: int) -> Placement`
  - `rule="single"`: choose the best-scoring rack with `len(free) ≥ n`, and take its lowest `n` ids.
  - Otherwise `rule="span"`: walk racks in descending score order (ties broken by lower index), taking the lowest free ids until `n` are taken.
  - Raises `ValueError` if the total free count is less than `n`.
  - `Placement.racks` lists racks in the order used, with no duplicates.
- `RackContext` (frozen dataclass):
  - `free_count: np.ndarray[int]`
  - `committed_kw: np.ndarray`
  - `t_c: np.ndarray`
  - `job_kw: float` — the job's total increment
  - `job_nodes: int`
- `Scorer` Protocol: `name: str`; `params: dict`; `score(ctx: RackContext) -> np.ndarray` (length n_racks; higher is better).
- Scorer classes:
  - `Packing()` → `-arange(n)`
  - `NodeBalance()` → `free_count`
  - `PowerBalance()` → `-committed_kw`
  - `CoolestRack()` → `-t_c`
  - `ThermalPredictive(a_c: float, b_c_per_kw: float, tau_s: float, horizon_s: float = 600.0)` → `-(t_c + (a_c + b_c_per_kw·(committed_kw + job_kw) − t_c)·(1 − exp(−horizon_s/tau_s)))`
- `make_scorer(name: str, params: dict) -> Scorer` — `name` is one of `packing`, `node_balance`, `power_balance`, `coolest_rack`, `thermal_predictive`.
- Tie-breaking is done in `place`, not in the scorers.

- [ ] **Step 1: Failing tests.**
  - `test_single_rack_preferred`: scores favour rack 2, and rack 2 has 5 free → `racks == (2,)` and the lowest 5 ids of rack 2.
  - `test_span_in_score_order`: n = 30, with free counts 18/10/18 and scores favouring rack 1 > rack 0 > rack 2 → takes 10 from rack 1, then 18 from rack 0, then 2 from rack 2. `rule == "span"`, and all 30 nodes are distinct.
  - `test_ties_break_to_lower_index`.
  - `test_insufficient_raises`.
  - `test_thermal_predictive_formula`:
    - inputs: `a = 20`, `b = 0.5`, `tau = 900`, `t_c = [30, 30]`, `committed = [10, 20]`, `job_kw = 5`;
    - expected score[0] = `-(30 + (20 + 0.5·15 − 30)·(1 − e^(−600/900)))`;
    - expected rack 0 preferred.
  - `test_power_balance_prefers_lowest_committed`.
  - `test_make_scorer_names`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_placement.py tests/unit/test_scorers.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests.
  - Expected: PASS.
- [ ] **Step 5:** Commit:
  ```
  feat(core): placement rule and five rack scorers
  ```

### Task 6: PlacementScheduler (RAPS drop-in)

**Files:**
- Create: `thermorl2/raps_adapter/scheduler.py`
- Test: `tests/integration/test_scheduler.py`

**Interfaces:**
- **Consumes:** `place`, `RackContext`, `make_scorer` (Task 5); `RackGeometry`; `job_increment_kw` (Task 2); `build_engine` (Task 4).
- **Produces:**
  - `ThermalView` (dataclass): `t_obs_s: float`, `t_c: np.ndarray`, `pump_kw: np.ndarray`.
  - `PlacementScheduler(resource_manager, geometry: RackGeometry, scorer: Scorer, cfg: dict, sink: Callable[[dict], None])`
    - Attributes: `policy = PolicyType.FCFS` and `bfpolicy = None`, both plain settable attributes.
    - `schedule(queue, running, current_time, accounts=None, sorted=False) -> None`
      - Sort the queue by `(submit_time, id)`.
      - Head-of-line FCFS: stop at the first job with `nodes_required > len(resource_manager.available_nodes)`.
      - For each placed job:
        1. build a `RackContext` from current free nodes, `committed_kw`, and the latest `ThermalView.t_c`;
        2. score, then call `place`;
        3. set `job.scheduled_nodes = list(placement.nodes)`;
        4. call `resource_manager.assign_nodes_to_job(job, current_time, PolicyType.REPLAY)`;
        5. `running.append(job)`, `queue.remove(job)`;
        6. add the per-rack increment to `committed_kw` (nodes on rack × per-node increment);
        7. emit one decision row to `sink`.
      - Never calls `check_available_nodes`.
    - `on_power_tick(rack_kw: np.ndarray) -> None` sets `committed_kw = rack_kw.copy()`.
    - `on_thermal(view: ThermalView) -> None`.
  - Decision row keys, exactly:
    `t_s, job_id, nodes_required, policy, rule, racks, nodes, job_kw, scores, t_c, committed_kw, free, t_obs_s, latency_us`
    - Arrays are lists of floats rounded to 6 decimals.
    - JSON keys are serialised in sorted order.
- Per-node utilisation for the increment comes from the job's scalar `cpu_trace` and `gpu_trace`. If either is a list, use its mean.

- [ ] **Step 1: Failing tests** (integration; each builds a 3 min engine with injected jobs, swaps in the scheduler, and drains the generator).
  - `test_exact_nodes_allocated`: under `packing`, a 4-node job gets nodes 0–3. Under `node_balance`, starting from a state where rack 0 has fewer free nodes, the job goes to another rack. Assert `job.scheduled_nodes` equals the decision row's `nodes`.
  - `test_policy_attrs_survive_prepare_system_state`: after the generator is primed, `scheduler.policy == PolicyType.FCFS` and `bfpolicy is None`.
  - `test_power_balance_spreads_same_second_arrivals`: two identical 4-node jobs with the same `submit_time` → different racks.
  - `test_coolest_rack_herds_same_second_arrivals`: same setup → the same rack (documents the ablation's expected behaviour).
  - `test_nodes_distinct_and_free`: with 40 random jobs over 3 min under `power_balance`, every decision's nodes are distinct, and no node is double-allocated at any time (track it with a set in the sink).
  - `test_head_of_line_blocking`: a 800-node job at the head blocks a 1-node job behind it.
- [ ] **Step 2:** Run `uv run pytest tests/integration/test_scheduler.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `uv run pytest tests/unit tests/integration -q`.
  - Expected: all pass.
- [ ] **Step 5:** Commit:
  ```
  feat(adapter): PlacementScheduler RAPS drop-in with committed-power tracking and decision rows
  ```

### Task 7: Synthetic workload and RAPS job construction

**Files:**
- Create: `thermorl2/raps_adapter/workload/__init__.py`, `thermorl2/raps_adapter/workload/synthetic.py`, `thermorl2/raps_adapter/jobs.py`
- Test: `tests/unit/test_synthetic.py`, `tests/integration/test_jobs.py`

**Interfaces (produces):**
- `WORKLOAD_COLUMNS = ["id", "nodes_required", "cpu_util", "gpu_util", "submit_time", "expected_run_time", "time_limit"]`
- `SyntheticSpec` (frozen):
  - `rho: float = 0.6`
  - `node_sizes = (1, 2, 4, 8, 16, 32)` with `node_weights = (0.35, 0.2, 0.2, 0.12, 0.09, 0.04)`
  - `runtime_median_s = 1800`, `runtime_sigma = 0.8`, `runtime_clip_s = (300, 14400)`
  - `gpu_choices = (0, 1, 2, 3, 4)`, `cpu_choices = (0.5, 1.0, 1.5, 2.0)`
  - `limit_factor = 1.5`
  - `from_dict(d) -> SyntheticSpec`
- `generate(spec, seed: int, horizon_s: int, n_nodes: int = 792) -> pd.DataFrame`
  - Poisson arrivals at rate `rho·n_nodes / E[nodes·runtime]`.
  - `E[nodes·runtime]` is estimated by Monte Carlo (1e6 draws) from the **same** `default_rng(seed)`, before arrivals are drawn.
  - Submit times are integers in `[0, horizon_s)`.
- `offered_utilisation(df, horizon_s, n_nodes, window=(3600, None)) -> float` — node-seconds offered inside the window divided by `n_nodes × window length`.
- `write_workload(df, path: Path, meta: dict) -> str` — writes parquet plus `<path>.meta.json` containing the SHA-256, and returns the SHA.
- `jobs_from_frame(df) -> list[raps.job.Job]`
  - Sets `Job._id_counter = 0`.
  - Builds jobs with `job_dict(nodes_required, name=f"j{id}", account="demo", id, cpu_trace=cpu_util, gpu_trace=gpu_util, ntx_trace=0, nrx_trace=0, submit_time, time_limit, start_time=None, end_time=None, expected_run_time)`.

- [ ] **Step 1: Failing tests.**
  - The same seed produces identical frames and SHA; a different seed differs.
  - `offered_utilisation` is within ±10 % of 0.6 for a 6 h horizon at seed 1.
  - Columns equal `WORKLOAD_COLUMNS`; `time_limit ≥ expected_run_time`; `1 ≤ nodes ≤ 32`; `0 ≤ gpu_util ≤ 4`.
  - `jobs_from_frame` round-trips `nodes_required`, `submit_time`, and `expected_run_time`, and the first job id is consistent across two calls.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_synthetic.py tests/integration/test_jobs.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests.
  - Expected: PASS.
- [ ] **Step 5:** Commit:
  ```
  feat(workload): deterministic synthetic workload targeting node utilisation; RAPS job builder
  ```

### Task 8: EpisodeRunner, run CLI, and the vertical slice → CHECKPOINT C2

**Files:**
- Create: `thermorl2/raps_adapter/runner.py`, `thermorl2/experiments/run.py`, `thermorl2/experiments/configs/smoke_2h.yaml`, `thermorl2/experiments/configs/g4_synthetic.yaml`
- Test: `tests/fmu/test_vertical_slice.py` (marks: `fmu`, `slow`)

**Interfaces:**
- **Consumes:** Tasks 2, 4, 6, 7; `FmuBackend`; `provenance.write_manifest`.
- **Produces:**
  - Config YAML schema:
    ```yaml
    name: g4_synthetic
    system: lassen
    horizon_h: 6            # or 12 per Task 4 rule
    warmup_s: 7200
    fmu: {path: ../../models/POWER9CSM/fmus/lassen.fmu, sha256: 2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b}
    workload: {kind: synthetic, rho: 0.6}          # or {kind: alibaba, variant: <chosen>, rho: 0.6}
    scenario: {name: nominal, ambient_schedule: []} # list of {start_s, t_air_k_by_unit: {racks: [33..43], k: 308.15}}
    thermal_predictive: {from: artifacts/probes/g1_uniform/summary.json, horizon_s: 600}
    policies: [packing, node_balance, power_balance, coolest_rack, thermal_predictive]
    seeds: [1, 2, 3]
    ```
  - `EpisodeRunner(cfg: dict, policy: str, seed: int, out_dir: Path)` with `.run() -> Path`:
    1. Generate or load the workload. It is cached under `artifacts/workloads/<name>_seed<seed>.parquet` and reused by SHA.
    2. Build the engine and inject `jobs_from_frame`.
    3. Swap in `PlacementScheduler` with the decision sink set to `decisions.jsonl`.
    4. Create the backend and `warm_up(idle_vector, Ambient(), 20, warmup_s)`; publish the initial `ThermalView`.
    5. Iterate the generator. On each power tick:
       - `rack_kw` → `scheduler.on_power_tick`;
       - `backend.step(rack_kw, 20, ambient_at(t))`;
       - `observe()` → `scheduler.on_thermal`;
       - append the interval rows.
    6. After the loop, write `intervals.parquet`, `manifest.json`, and `stdout_summary.json`.
  - `intervals.parquet` columns:
    `t_s, rack, kw, t_c, pump_kw, free, it_kw_total, n_running, n_queued, scenario_active`
  - `manifest.json` additionally contains:
    - `idle_kw`, `peak_kw`;
    - `warmup_used_s`;
    - `thermal_predictive_params` (when that policy is used);
    - `workload_sha256` and `workload_path` (relative to the repo root);
    - `t_idle_c`: 44 floats, the per-rack coolant °C at the warm-up snapshot;
    - timings `raps_s`, `fmu_s` (= `backend.runtime_s()`), `total_s`.
  - Run dir: `artifacts/runs/<cfg.name>/<policy>_seed<seed>/`.
  - CLI: `uv run python -m thermorl2.experiments.run --config <yaml> --policy <p> --seed <s> [--horizon-h H] [--out artifacts/runs]`.

- [ ] **Step 1: Failing test** `test_vertical_slice`. Run `smoke_2h.yaml` (horizon 2 h, ρ 0.6) for `packing` and `power_balance` into `tmp_path`, then assert:
  - both run dirs have the three files;
  - `it_kw_total` per `t_s` is identical across the two runs (`atol=1e-6`);
  - every decision's `nodes` length equals `nodes_required`;
  - Σ `kw` per tick equals `it_kw_total`;
  - rerunning `packing` produces a byte-identical `decisions.jsonl`.
- [ ] **Step 2:** Run `uv run pytest tests/fmu/test_vertical_slice.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the test.
  - Expected: PASS.
- [ ] **Step 5:** Produce the vertical-slice figure. Write a small throwaway function inside `run.py --plot-pair`, or use Task 10's plotting early.
  - Output: side-by-side rack × time `t_c` heatmaps for the two smoke runs on a shared colour scale, saved to `artifacts/figures/c2_vertical_slice.png`.
  - Also record the time-averaged max-rack °C over [1 h, 2 h] for both runs.
- [ ] **Step 6:** Commit:
  ```
  feat(adapter): EpisodeRunner closed loop (RAPS ticks -> FMU steps -> placement), run CLI, vertical-slice test
  ```

**CHECKPOINT C2 — first closed-loop result.** Write `docs/checkpoints/C2-vertical-slice.md` containing:
- the figure;
- both max-rack numbers;
- the wall times (`raps_s`, `fmu_s`, `total_s`);
- confirmation of all four invariants;
- the chosen horizon.

Then stop.

---

## Phase 2 — Conservative demo complete (Day 3)

### Task 9: Metrics from ledgers and cross-policy invariants

**Files:**
- Create: `thermorl2/core/metrics.py`
- Test: `tests/unit/test_metrics.py`

**Interfaces (produces):**
- `Run` (dataclass): `name: str`, `intervals: pd.DataFrame`, `decisions: pd.DataFrame`, `manifest: dict`.
- `load_run(run_dir: Path) -> Run`.
  - This is the only file I/O in `core`. Pandas and parquet are allowed.
- `run_metrics(run: Run, eval_start_s: float, t_hot_c: float, t_idle_c: np.ndarray, t_max_c: float = 45.0) -> dict`. Keys:
  - `maxrack_mean_c`, `maxrack_p99_c`, `spread_mean_c`, `mean_rack_c`;
  - `hot_rack_seconds`;
  - `thi_t_below_0p1_frac`;
  - `pump_energy_kwh`, `it_energy_kwh`;
  - `jobs_started`, `wait_mean_s`, `wait_p95_s`.
  - All thermal keys are computed over `t_s ≥ eval_start_s`.
  - Wait is `t_s(decision) − submit_time`, taken from the workload parquet referenced in the manifest.
- `invariants(runs: list[Run]) -> dict` returns:
  - `it_kw_identical: bool` (`atol=1e-6`);
  - `start_times_identical: bool` (decision `t_s` per `job_id`);
  - `max_abs_it_kw_diff`.
- `disagreement_rate(decisions: pd.DataFrame, scorer: Scorer) -> float`.
  - Re-score each logged context (`free`, `committed_kw`, `t_c`, `job_kw`, `nodes_required`) with `scorer`, apply `place`, and compare the first rack with the logged `racks[0]`.
- `affected_metrics(run, racks: list[int], eval_start_s) -> dict` returns `maxrack_mean_c` restricted to the given racks (used by G5).

- [ ] **Step 1: Failing tests** on a hand-built 3-rack, 4-tick ledger:
  - `maxrack_mean_c` and `spread_mean_c` match hand-computed values;
  - `hot_rack_seconds` = 2 rack-ticks × 20 s = 40;
  - `invariants` returns False when one tick's `it_kw_total` differs by 1 kW;
  - `disagreement_rate` = 0.5 on a 2-decision fixture.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_metrics.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests.
  - Expected: PASS.
- [ ] **Step 5:** Commit:
  ```
  feat(core): ledger metrics, cross-policy invariants, decision-disagreement diagnostic
  ```

### Task 10: Plots, animation, and the report builder

**Files:**
- Create: `thermorl2/experiments/plots.py`, `thermorl2/experiments/report.py`
- Test: `tests/unit/test_plots_smoke.py` (uses a synthetic ledger and writes to `tmp_path`)

**Interfaces (produces):**
- `heatmaps(runs: list[Run], out_png: Path, vmin: float, vmax: float)`
  - One rack × time panel per run, sharing a colour scale.
  - Title is the policy name.
  - A vertical line marks `scenario_active` onset if present.
- `timeseries(runs, out_png)` — max-rack °C and spread over time, one line per policy.
- `metrics_table(rows: list[dict], out_md: Path)` — mean ± min/max across seeds, per policy.
- `animate_grid(runs: list[Run], out_path: Path, stride_ticks: int = 3)`
  - Side-by-side 4 × 11 schematic rack grids coloured by `t_c` on a shared scale.
  - Annotate each rack with kW; placement pulses come from the decisions.
  - GIF via pillow; MP4 if ffmpeg is present.
- `g2_figure(probe_dir: Path, out_png: Path)`.
- `report.py` CLI: `uv run python -m thermorl2.experiments.report artifacts/runs/<cfg.name> --probe artifacts/probes/g1_uniform`. It writes into `artifacts/reports/<cfg.name>/`:
  - `metrics.csv`, `metrics.md`;
  - `heatmaps_seed1.png`, `timeseries_seed1.png`, `anim_packing_vs_thermal_predictive_seed1.gif`;
  - `invariants.json`;
  - `decision.json`, which applies the G4/G5 rule from spec §4.
  - **The rule must be coded exactly.** Value is shown if, for every seed, `power_balance.maxrack_mean_c − thermal_predictive.maxrack_mean_c ≥ 0.5`. Also record the per-seed `packing − thermal_predictive` gap.

- [ ] **Step 1: Failing smoke tests.** Each function writes a non-empty file. `decision.json` on a fixture gives `value_beyond_power: false` when the gap is 0.3 in one seed.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS. Also write `artifacts/figures/g2_packed_vs_spread.png` from the probe.
- [ ] **Step 5:** Commit:
  ```
  feat(experiments): heatmaps, time series, animated rack grid, report with pre-registered decision rule
  ```

### Task 11: Run matrix and G4 on the synthetic workload → CHECKPOINT C3

**Files:**
- Create: `thermorl2/experiments/run_matrix.py`
- Modify: `thermorl2/experiments/configs/g4_synthetic.yaml` (set `horizon_h` per the Task 4 rule)

**Interfaces (produces):**
- CLI: `uv run python -m thermorl2.experiments.run_matrix --config <yaml> [--policies …] [--seeds …] --workers 6`.
- It launches one `python -m thermorl2.experiments.run` subprocess per (policy, seed). There is one FMU per process.
- It skips run dirs whose manifest already exists with the same config hash.
- It exits non-zero if any run fails.

- [ ] **Step 1:** Implement `run_matrix.py`. Smoke it with `--config configs/smoke_2h.yaml --policies packing,power_balance --seeds 1`.
  - Expected: 2 run dirs.
- [ ] **Step 2:** Run the full G4 synthetic matrix: 5 policies × 3 seeds.
- [ ] **Step 3:** Run `report.py` on it.
  - Expected: `invariants.json` shows both booleans as true. If not, **stop**.
- [ ] **Step 4:** Commit the code, the report directory, and the run ledgers (respecting the 25 MB rule):
  ```
  exp(g4): synthetic workload, 5 policies x 3 seeds, report
  ```

**CHECKPOINT C3 — Conservative demo complete.** Write `docs/checkpoints/C3-g4-synthetic.md` containing:
- the metrics table;
- the decision JSON;
- the per-seed gaps;
- the invariants;
- the figure and GIF paths;
- runtime per run.

From this point the Conservative target is demo-able.

---

## Phase 3 — Alibaba-derived workload (Day 4)

### Task 12: Alibaba-derived workload builder

**Files:**
- Create: `thermorl2/raps_adapter/workload/alibaba.py`, `thermorl2/experiments/configs/g4_alibaba.yaml`
- Test: `tests/unit/test_alibaba.py` (uses a tiny inline CSV fixture, not the gitignored dataset)

**Interfaces (produces):**
- `load_pods(csv_path: Path) -> pd.DataFrame`
  - Drops `pod_phase == "Pending"` and `num_gpu == 0`.
  - Adds `runtime_s = deletion_time − creation_time`.
- `map_pods(pods: pd.DataFrame, cpus_per_socket: int = 20) -> pd.DataFrame`, with columns `nodes_required, gpu_util, cpu_util, runtime_s, creation_time`:
  - `nodes = max(1, ceil(num_gpu/4))`
  - `gpu_util = min(4, num_gpu·gpu_milli/1000/nodes)`
  - `cpu_util = min(2, cpu_milli/1000/cpus_per_socket/nodes)`
- `pod_power_stats(mapped, cfg) -> dict` with keys `mean_node_increment_kw` and `share_nodes_ge2_gpu`.
- `derive_workload(mapped, rho: float, horizon_s: int, seed: int, n_nodes: int = 792) -> pd.DataFrame` (columns `WORKLOAD_COLUMNS`):
  1. Clip runtimes to `[300, horizon_s]`.
  2. `default_rng(seed)` picks a start offset into the creation-ordered pods. Iterate cyclically.
  3. Compute the time-scale factor analytically, so that offered node-utilisation equals `rho`: `scale = (mean original inter-arrival) / (target inter-arrival)`, where the target inter-arrival is `E[nodes·runtime_clipped] / (rho·n_nodes)`.
  4. Submit times = cumulative scaled inter-arrivals, truncated at `horizon_s`.
  5. `time_limit = ceil(1.5·runtime)`.
- `choose_variant(raw_dir: Path, cfg) -> dict`
  - Computes `pod_power_stats` for `default` and `multigpu50`.
  - Selects the variant with the higher `mean_node_increment_kw`.
  - Writes `artifacts/workloads/alibaba_variant_choice.json` **before** any Alibaba policy run.

- [ ] **Step 1: Failing tests.**
  - Mapping examples: `num_gpu=8, gpu_milli=1000` → `nodes=2, gpu_util=4.0`. `num_gpu=1, gpu_milli=500` → `nodes=1, gpu_util=0.5`.
  - Pending rows are dropped.
  - The same seed gives an identical frame.
  - `offered_utilisation` is within ±15 % of 0.6 on a fixture with enough rows.
  - Submit times are sorted and lie within `[0, horizon_s)`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_alibaba.py -v`.
  - Expected: FAIL.
- [ ] **Step 3:** Implement. Extend the `EpisodeRunner` workload dispatch to accept `kind: alibaba`; it reads `datasets/alibaba_gpu_2023/raw/`.
- [ ] **Step 4:** Run the tests (expected: PASS). Then run `choose_variant` and commit its JSON.
- [ ] **Step 5:** Commit:
  ```
  feat(workload): Alibaba GPU 2023-derived workload (documented pod->node mapping, rate-scaled arrivals)
  ```

### Task 13: G4 on the Alibaba-derived workload → CHECKPOINT C4

- [ ] **Step 1:** Run `run_matrix --config configs/g4_alibaba.yaml --workers 6` (5 policies × 3 seeds), then `report.py`.
- [ ] **Step 2:** If the invariants are false, **stop**.
- [ ] **Step 3:** Commit:
  ```
  exp(g4): Alibaba-derived workload, 5 policies x 3 seeds, report
  ```

**CHECKPOINT C4.** Write `docs/checkpoints/C4-g4-alibaba.md` with the same contents as C3, plus the variant choice and its statistics, and the realised utilisation.

---

## Phase 4 — Visualisation (Day 5)

### Task 14: Three.js side-by-side replay adapted to Lassen (fallback: Task 10 GIFs)

**Files:**
- Create: `thermoRL/thermorl-v2/viz/` — copy `thermoRL/thermoRL-new/viz/`, excluding `node_modules`
- Create: `thermorl2/experiments/export_viz.py`
- Test: `tests/unit/test_export_viz.py`
- Output: `artifacts/demo/replay_<cfg.name>_<policyA>_vs_<policyB>_seed<s>/` (self-contained `index.html`, `assets/`, `bundle-data.js`)

**Interfaces (produces):**
- `export_bundle(run_a: Path, run_b: Path, out_dir: Path, label: str, stride_ticks: int = 3) -> Path` writes `bundle-data.js` defining `window.THERMORL_DATA = {meta, frames_a, frames_b, decisions_a, decisions_b}`:
  - **`meta`:** `policy_a`, `policy_b`, `scenario` (name and label text), `n_racks: 44`, `grid: {rows: 4, cols: 11, schematic: true}`, `color: {vmin_c, vmax_c}` (shared, from both runs' `t_c` 1st/99th percentiles), `affected_racks` (empty for nominal), `metrics_a`, `metrics_b`.
  - **Frame:** `{t_s, racks: [{t_c, kw, free}], events: [{job_id, racks, rule, decision_index}], maxrack_c, spread_c, it_kw}`. Frames align on identical `t_s` across A and B.
  - **Decision:** `{t_s, job_id, nodes_required, racks, scores, t_c, committed_kw, free}`.
- **Viz changes** (`viz/src`):
  - Data-driven rack count and 4 × 11 layout, which fixes the old `rowZ` overlap bug.
  - Colour from `t_c` using the shared `meta.color`.
  - Remove zones, PUE, and λ drawers.
  - Metric strip shows: max-rack °C, spread, IT kW, jobs started.
  - The "WHY?" drawer shows the selected event's per-rack scores as a 44-bar chart, highlighting the chosen racks.
  - A what-if banner and outlines on the affected racks when the scenario is active.
  - Subtitle text comes from `meta.scenario.label`.
  - Scrubber over `t_s`.
- Time-box: **1 day**. If not done by the end of Day 5, keep Task 10's GIFs as the headline visual and record that in C5.

- [ ] **Step 1: Failing test.** On two tiny fixture run dirs, `export_bundle` writes `bundle-data.js`. The parsed JSON (after stripping the `window.THERMORL_DATA =` prefix) has equal `frames_a`/`frames_b` lengths and identical `t_s` lists, each frame has 44 racks, and `vmin_c < vmax_c`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement the exporter and run the test → PASS.
- [ ] **Step 4:** Adapt the viz. Run `npm ci && npm run build` in `viz/`.
  - Expected: `tsc` passes and the build succeeds.
  - Copy `dist/*` into the bundle directory.
- [ ] **Step 5:** Export the headline bundle: G4 synthetic seed 1, `packing` vs `thermal_predictive`. Also export `power_balance` vs `thermal_predictive`.
  - Open `index.html` from disk on any machine to check it renders.
  - Save one screenshot PNG per bundle.
- [ ] **Step 6:** Commit:
  ```
  feat(viz): Lassen 44-rack side-by-side replay with decision explanations; bundle exporter
  ```

---

## Phase 5 — Degraded-cooling what-if (Day 6; only if G3 decision is USABLE)

### Task 15: G5 room-air failure what-if → CHECKPOINT C5

**Files:**
- Create: `thermorl2/experiments/configs/g5_whatif_synthetic.yaml`, a copy of `g4_synthetic.yaml` with:
  ```yaml
  name: g5_whatif_synthetic
  scenario:
    name: whatif_room_air_failure_row
    label: "What-if: room-air cooling failure on one row (not observed Lassen behaviour)"
    ambient_schedule: [{start_s: 7200, t_air_k_by_unit: {racks: [33,34,35,36,37,38,39,40,41,42,43], k: 308.15}}]
  ```
- Modify: `runner.py`, only if Task 8 did not already implement `ambient_schedule` and the `scenario_active` column.

- [ ] **Step 1: Failing test** (`tests/fmu/test_vertical_slice.py::test_whatif_schedule_applies`): run 2.5 h of `smoke_2h` with the what-if starting at 7200 s. Assert:
  - `scenario_active` is false before 7200 s and true after;
  - the manifest records the scenario.
- [ ] **Step 2:** Run → FAIL (if not already implemented). **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Run the matrix and the report.
  - `report.py` also computes `affected_metrics` for racks 33–43 and applies the same 0.5 °C rule to both the overall and the affected-rack `maxrack_mean_c`.
  - Export a viz bundle for `power_balance` vs `thermal_predictive`, which shows the what-if banner.
- [ ] **Step 6:** Commit:
  ```
  exp(g5): room-air failure what-if (pre-registered), 5 policies x 3 seeds, report and replay
  ```

**CHECKPOINT C5.** Write `docs/checkpoints/C5-whatif.md` with the same contents as C3, plus the affected-rack metrics.

If G3 was NOT_USABLE, write C5 instead as a one-paragraph note: "what-if not run; lever not usable", citing the G3 numbers and the candidate CDU parameter list. Then stop for steering.

---

## Phase 6 — Demo packaging (Day 7)

### Task 16: Results note, runbook, demo folder

**Files:**
- Create: `docs/results/2026-11-parasparam-demo-results.md`
- Create: `artifacts/demo/README.md`
- Modify: `thermoRL/thermorl-v2/README.md` (add a "Reproduce the demo" runbook)

- [ ] **Step 1: Results note** (≤ 2 pages). It must cover:
  - what ran (configs, SHAs, FMU hash, workload hashes);
  - the G1–G3 physics table;
  - the G4 tables for both workloads;
  - G5, if it ran;
  - the pre-registered decisions and their outcomes, stated plainly;
  - the invariants;
  - runtime;
  - spec §6 allowed claims, filled in with the measured numbers;
  - spec §8 limitations, verbatim.
  - No lifetime, PUE, carbon, or heterogeneous-zone claims.
- [ ] **Step 2: Runbook.** Exact commands from a clean Arch checkout, in this order:
  1. `uv sync`
  2. probes
  3. matrices
  4. reports
  5. viz export and build
  - Include the expected wall times.
- [ ] **Step 3: Demo folder.** `artifacts/demo/` contains the headline figures, GIFs, replay bundles, and a `README.md` that maps each asset to the claim it supports.
- [ ] **Step 4: Fresh-clone check.** Run the full test suite: `uv run pytest -q`.
  - Expected: all pass, with the historical test reported as XFAIL.
  - Then re-run one demo run and confirm a byte-identical `decisions.jsonl`.
- [ ] **Step 5:** Commit:
  ```
  docs(results): ParasParam demo results note, runbook, demo asset index
  ```

---

## Explicitly out of scope

- RL / PPO.
- The ExaDigiT server, dashboard, or UE5.
- Carbon.
- PUE and plant energy.
- Summit runs.
- FMU-snapshot lookahead.
- A 24 h ramp.
- RAPS patches.

These may be added only by a new steering decision after C5.

## Plan self-review

- **Spec coverage.**

  | Spec section | Covered by |
  |---|---|
  | §3 architecture | Tasks 2, 4–8 |
  | §3.1 semantics | Tasks 4, 6, 8 |
  | §3.2 policies | Tasks 5, 6 |
  | §3.3 workloads | Tasks 7, 12 |
  | §3.4 scenarios | Tasks 2, 3, 15 |
  | §4 G1–G3 | Task 3 |
  | §4 G4 | Tasks 11, 13 |
  | §4 G5 | Task 15 |
  | §4 secondary metrics | Task 9 |
  | §5 visuals | Tasks 10, 14 |
  | §6 claims and §8 limitations | Task 16 |
  | §7 invariants 1–5 | Tasks 8, 9, 11, 16 |
  | P1 (Task 1.5 closure) | Task 1 |

- **Type consistency.** These names are used identically in every task:
  - `RackContext(free_count, committed_kw, t_c, job_kw, job_nodes)`
  - `ThermalView(t_obs_s, t_c, pump_kw)`
  - `Placement(racks, nodes, rule)` (existing)
  - `Run(name, intervals, decisions, manifest)`
  - `WORKLOAD_COLUMNS`
  - `rack_power_bounds`, `job_increment_kw`
  - the decision-row keys, used in Tasks 6, 9 and 14
- **Pre-registration.** All thresholds (2.0 / 1.0 °C for G2, 1.0 °C for G3, 0.5 °C for G4/G5) and the `t_hot_c` and τ derivations come from spec §4. Thresholds are never computed from closed-loop results.
