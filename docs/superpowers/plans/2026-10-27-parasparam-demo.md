# ParasParam Closed-Loop Demo — Implementation Plan (FINAL)

> **For agentic workers (Sol 6.1):** Execute task by task, in order. Steps use checkbox (`- [ ]`) syntax. A **CHECKPOINT** is a mandatory stop: write the checkpoint report, commit, push, and wait for steering. Between checkpoints, keep going unless a stop condition below applies.

**Goal:** Produce the first FMU-backed closed-loop thermal result within 2 days, on the primary FMU that the three-FMU gate selects. Then grow it into a reproducible demo with visuals in about 1 week.

**Architecture:** Extend `thermoRL/thermorl-v2/thermorl2` and make it system-generic: Lassen, Summit or Marconi100.
- RAPS runs with its own cooling off.
- `EpisodeRunner` steps the existing `FmuBackend` at every power tick, defined as `t % Δ == 0`.
- A `PlacementScheduler` drop-in sets exact nodes through RAPS's REPLAY path.
- All policies share one FCFS queue, so timing and total power are identical across policies. Only placement differs.
- Metrics and plots are computed only from per-run ledgers.
- Artifacts follow `docs/superpowers/specs/2026-10-27-experiment-conventions.md`.

**Tech stack:**
- Python 3.12 (uv), with editable `raps` from `../../sim-raps`.
- fmpy 0.3.x, numpy, pandas, pyarrow, pyyaml, matplotlib, pillow, pytest.
- Viz: Vite + TypeScript + three.js.

**Spec:** `docs/superpowers/specs/2026-10-27-parasparam-demo-design.md`. Read it first; this plan argues from it. Also read:
- `docs/superpowers/specs/2026-10-27-experiment-conventions.md`
- `docs/repository-notes.md`

Background:
- `docs/2026-10-27-surrogate-and-fmu-selection-assessment.md`
- `docs/2026-10-27-thermorl-demo-strategy.md`
- `docs/2026-10-26-thermorl-investigation-findings.md`

## Global Constraints

- **Machine.** All FMU and RAPS execution happens on the **Arch Linux x86-64** machine.
- **Paths.** Paths are relative to the repo root. Run Python from `thermoRL/thermorl-v2` with `uv run …`.
- **Import boundaries.**
  - `core/` never imports `raps`, `fmpy` or `torch`.
  - Only `raps_adapter/` imports `raps`.
  - Only `thermal/fmu_backend.py` imports `fmpy`.
- **Off-limits.**
  - **No edits to `sim-raps/`.** If one seems needed, stop and report.
  - Do not touch `docs/prompt.md`.
  - Do not use `hpc-cooling-surrogate` or `--cooling-model surrogate`.
- **FMU backend.** It is the only thermal backend. One FMU instance per OS process: run every FMU probe or run in its own process, and never instantiate two FMUs (of any system) in one process.
- **FMU paths and SHA-256.** Must match spec §3.1. Verify the SHA before use.
- **RAPS settings.**
  - `time_unit` 1 s; `time_delta = POWER_UPDATE_FREQ` of the system.
  - `cooling: false`, `output: "none"`, `noui: true`, `timestep_start` 0.
  - **Power tick = `tick.current_timestep % time_delta == 0`.** Never use `power_df is not None`, because RAPS reuses the previous `power_df` on every second.
  - RAPS **raises** when a job exceeds `time_limit`. Every job must have `time_limit ≥ expected_run_time`.
- **Seeds.** Seeds ≥ 1. Reset `raps.job.Job._id_counter = 0` before building each run's jobs.
- **Coupling constants.** Always taken from `CouplingParams.from_legacy_config(legacy_config(system))`.
- **Pre-registration.**
  - Spec §4 thresholds, metrics, policy definitions, workload parameters and scenario definitions are frozen.
  - Changing any of them is a stop condition.
  - Experiment READMEs carry the rule **before** results (conventions §7.1).
- **Provenance.** Every run directory has a manifest: git SHA and dirty flag, system, FMU SHA-256, workload SHA-256, config, policy, seed, `backend: fmu`, and timings.
- **Size.** Commit run directories under 25 MB each. Gitignore larger ones and list their path and SHA in the experiment README.
- **Stop conditions:**
  - an unexplained test failure;
  - mechanics that contradict the spec (for example, IT kW differs across policies);
  - a needed change to a pre-registered item;
  - a needed RAPS patch;
  - the X01 selection result is STOP;
  - any CHECKPOINT.
  
  Otherwise, fix forward.
- **Branch.** `feat/parasparam-demo`, created from `feat/thermorl2-phase0-env`. Commit after every task with the given message.

## Review Focus

1. **Many arrivals within one power-tick window.**
   - `power_balance` must spread back-to-back jobs, because it updates committed kW on every placement.
   - `coolest_rack` is expected to herd. The test pins this behaviour.
   - Owner: Task 7.
2. **Jobs larger than one rack, and fragmented free nodes.** A placement returns exactly `n` distinct free nodes and spans racks in score order. Owner: Task 6.
3. **Power-tick misdetection.** If the FMU is stepped every second, thermal time runs Δ× too fast. A step-count invariant catches this. Owners: Tasks 5 and 9.
4. **Determinism.** The same config, policy and seed give a byte-identical `decisions.jsonl`. Watch the `Job._id_counter` reset, the single RNG, and sorted JSON keys. Owner: Task 9.
5. **Cross-policy invariants.** For one workload, IT kW per tick and job start times are identical across policies. Owners: Tasks 10 and 12.

## Schedule (target)

| Day | Tasks | Gate |
|---|---|---|
| 1 | 1, 2, 3 (three-FMU G2 + selection), 4 (G1 + G3 on primary) | **CHECKPOINT C1**: FMU selection and physics |
| 2 | 5, 6, 7, 8, 9 (vertical slice) | **CHECKPOINT C2**: first closed-loop result |
| 3 | 10, 11, 12 (metrics, plots, G4 synthetic) | **CHECKPOINT C3**: Conservative demo complete |
| 4 | 13, 14 (Alibaba-derived, G4) | **CHECKPOINT C4** |
| 5 | 15 (viz) | — |
| 6 | 16 (what-if, only if G3 USABLE) | **CHECKPOINT C5** |
| 7 | 17 (packaging) | Final review |

**Checkpoint report:** `docs/checkpoints/C<n>-<slug>.md`. It contains:
- the exact commands run;
- git SHA;
- key numbers;
- links to the experiment READMEs;
- each rule outcome;
- anomalies;
- the proposed next step.

Commit it, `git push -u origin feat/parasparam-demo`, and stop.

---

## Phase 0 — Environment, FMU selection, physics (Day 1)

### Task 1: Environment, Task 1.5 closure (option B), experiment scaffold

**Files:**
- Modify: `thermoRL/thermorl-v2/uv.lock` (from `uv lock`)
- Modify: `thermoRL/thermorl-v2/tests/fmu/test_fmu_backend.py` (historical physical-response test: xfail only)
- Modify: `thermoRL/thermorl-v2/tests/fmu/test_direct_backend_replay.py` (within-process replay assertion only)
- Modify: `thermoRL/thermorl-v2/README.md` (add a "Task 1.5 closure (option B)" section)
- Modify: `docs/superpowers/proposals/2026-09-29-task-1-5-backend-closeout.md` (append "Closed under option B, 2026-10-27")
- Create: `thermoRL/thermorl-v2/experiments/INDEX.md`, `experiments/_templates/EXPERIMENT_README.md`, `experiments/_templates/SYSTEM.md`, `experiments/{lassen,summit,marconi100}/SYSTEM.md`, `experiments/lassen/E00_legacy_task15/README.md`
  - Templates are copied verbatim from conventions §4–§5.
  - `SYSTEM.md` gets the spec §3.1 values. Measured fields stay `TBD (Task 2/3)` until filled.

- [ ] **Step 1: Set up the branch and environment.**
  - Run `git pull`, then `git checkout -b feat/parasparam-demo`.
  - In `thermoRL/thermorl-v2`, run `uv lock && uv sync`.
  - Expected: success on CPython 3.12. `uv.lock` changes, because RAPS added `textual` and a newer `requests`.
- [ ] **Step 2: Baseline tests.** Run `uv run pytest tests/unit tests/integration -q`.
  - Expected: `19 passed`.
- [ ] **Step 3: Mark the historical test as an expected failure.**
  - Add `@pytest.mark.xfail(strict=True, reason="Historical cold-start probe bound (500–1000 s); warmed-state t63 measured 1240 s. Retained unchanged as a record; spec 2026-10-27 P1.")` to `test_single_rack_step_is_local_and_matches_probe`.
  - Do not change the test body.
- [ ] **Step 4: Change the replay assertion to option B.**
  - In `test_backend_matches_independent_direct_fmu_with_snapshot_replay`, replace only the within-process `atol=1e-9` replay-1-vs-replay-2 assertion.
  - New assertion: for each key, `(backend_replay2 − backend_replay1)` equals `(direct_replay2 − direct_replay1)` with `atol=1e-6`.
  - Record `max_abs_restore_jitter_c` in the test's manifest output.
  - All direct-vs-backend `atol=1e-6` assertions stay unchanged.
- [ ] **Step 5: FMU tests.** Run `uv run pytest tests/fmu -v`.
  - Expected: lifecycle, reset and replay tests pass; the historical test shows XFAIL.
  - Any other result is a stop condition.
- [ ] **Step 6: Documentation and scaffold.**
  - Write the README closure section: 1.43e-4 °C restore jitter is a documented limitation; direct FMU = backend is the correctness evidence.
  - Write the closeout note.
  - Create the experiment scaffold.
  - `E00_legacy_task15/README.md` holds one row per legacy diagnostic A–H: path, question, key finding. Take these from `docs/2026-10-26-thermorl-investigation-findings.md` §7.
- [ ] **Step 7: Commit.**
  ```
  feat(thermal): close Task 1.5 under option B; uv lock refresh; experiment scaffold
  ```

### Task 2: System registry, per-rack room air, power-model helpers, per-system FMU smoke

**Files:**
- Create: `thermorl2/raps_adapter/systems.py`, `thermorl2/raps_adapter/power_model.py`, `thermorl2/experiments/__init__.py`, `thermorl2/experiments/provenance.py`, `thermorl2/experiments/fmu_smoke.py`
- Modify: `thermorl2/core/state.py`, `thermorl2/raps_adapter/coupling.py`
- Test: `tests/unit/test_coupling.py` (extend), `tests/unit/test_systems.py`, `tests/unit/test_provenance.py`, `tests/integration/test_power_model.py`, `tests/fmu/test_fmu_smoke_all_systems.py`

**Interfaces (produces):**
- `Ambient(t_air_k: float = 290.0, t_ext_k: float = 290.0, t_air_k_by_unit: tuple[float, ...] | None = None)`
- `rack_kw_to_fmu_inputs(rack_kw, p, ambient)`
  - Unchanged when `t_air_k_by_unit is None`.
  - Otherwise, the key `simulator_1_datacenter_1_computeBlock_{i}_cabinet_1_sources_T_Air` takes `t_air_k_by_unit[i-1]`. `_T_ext` still takes `t_ext_k`.
- `SystemSpec` (frozen dataclass). Fields:
  - `name: str`
  - `fmu_path: Path` (repo-relative)
  - `fmu_sha256: str`
  - `grid: tuple[int, int]`
  - `whatif_racks: tuple[int, ...]`
- `SYSTEMS: dict[str, SystemSpec]` holds `lassen`, `summit`, `marconi100` with the values from spec §3.1. Each system's `whatif_racks` is the last ⌈n/4⌉ racks.
- `get_system(name: str) -> SystemSpec`
- `repo_root() -> Path`
- `legacy_config(system: str) -> dict` returns `get_system_config(system).get_legacy()`.
- `node_power_kw(cfg, cpu_util, gpu_util) -> float` returns `compute_node_power(cpu_util, gpu_util, 0, cfg)[0] / 1000`.
- `rack_power_bounds(cfg) -> tuple[float, float]` returns `(idle_kw, peak_kw)`:
  - per rack: `NODES_PER_RACK × node_power_kw(u, g) + CHASSIS_PER_RACK × SWITCHES_PER_CHASSIS × POWER_SWITCH / 1000`;
  - idle uses `u = g = 0`;
  - peak uses `u = CPUS_PER_NODE`, `g = GPUS_PER_NODE`.
- `job_increment_kw(cfg, cpu_util, gpu_util, n_nodes) -> float` returns `n_nodes × (node_power_kw(cpu, gpu) − node_power_kw(0, 0))`.
- `provenance.py`:
  - `git_state() -> {"sha", "dirty"}`
  - `sha256_file(path) -> str`
  - `environment() -> dict` (python, uv, fmpy, numpy versions, platform)
  - `write_manifest(out_dir: Path, **fields) -> Path`
- `fmu_smoke.py` CLI: `uv run python -m thermorl2.experiments.fmu_smoke --system S`.
  1. Verify the FMU SHA.
  2. Build `FmuBackend(fmu_path, CouplingParams.from_legacy_config(cfg))`.
  3. `warm_up(idle_vector, Ambient(), dt_s=Δ, max_s=600)`.
  4. Print JSON: `{system, n_units, t_c_min, t_c_max, finite, wall_s}`.

- [ ] **Step 1: Write failing tests.**
  - `test_per_unit_air_temperature_maps_by_index`: with 44 values `290 + i`, the `computeBlock_34` `T_Air` input is `323.0`.
  - `test_default_ambient_unchanged`: the existing RAPS-equality test still passes.
  - `test_systems_registry`, for each system:
    - `len(whatif_racks) == ceil(n_racks/4)` and `whatif_racks[-1] == n_racks − 1`;
    - `grid[0] × grid[1] ≥ n_racks`;
    - `sha256_file(fmu_path) == fmu_sha256`.
  - `test_rack_power_bounds_all_systems` (parametrised; integration): `idle < peak`. Print both values. Expected approximately:

    | system | idle (kW) | peak (kW) |
    |---|---|---|
    | lassen | 10.86 | 34.43 |
    | summit | 13.2 | 45–47 |
    | marconi100 | 12.4 | 37–39 |

  - `test_job_increment_zero_at_idle`.
  - `test_write_manifest_roundtrip`.
  - `test_fmu_smoke_all_systems` (marked `fmu`): runs `fmu_smoke` **as a subprocess per system**. Each must report `finite` and `n_units` equal to that system's rack count.
- [ ] **Step 2: Confirm they fail.** Run `uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v`.
  - Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Confirm they pass.** Run the command again.
  - Expected: PASS.
  - Fill the measured idle/peak and smoke `wall_s` into each `SYSTEM.md`.
  - If Summit or Marconi100 fails to instantiate, step, or produce finite outputs, record it in `SYSTEM.md`. That system becomes **ineligible** for X01; this is not a stop condition unless all three fail.
- [ ] **Step 5: Commit.**
  ```
  feat(adapter): system registry (lassen/summit/marconi100), per-rack room air, power-model helpers, per-system FMU smoke
  ```

### Task 3: Three-FMU G2 screen and mechanical FMU selection (X01)

**Files:**
- Create: `thermorl2/experiments/probes.py`, `thermorl2/experiments/select_fmu.py`
- Test: `tests/unit/test_probe_vectors.py`, `tests/unit/test_select_fmu.py`
- Output:
  - `experiments/{lassen,summit,marconi100}/E02_g2_packed_vs_spread/`
  - `experiments/cross_system/X01_fmu_selection/`

**Interfaces (produces):**
- `uniform_vector(n, idle_kw, peak_kw, f) -> np.ndarray`
- `packed_vector(n, idle_kw, peak_kw, total_kw) -> np.ndarray`
  - Racks `0..k−1` at peak, rack `k` at the remainder, the rest at idle.
  - The sum equals the total within 1e-9, and every element lies within [idle, peak].
- Probe CLI: `uv run python -m thermorl2.experiments.probes {g1,g2,g3} --system S --out <experiment dir>`.
  1. One process, one `FmuBackend`.
  2. Warm up: `warm_up(idle_vector, Ambient(), dt_s=Δ, max_s=7200)`.
  3. For each branch: `reset()`, then 3 h of `step(·, Δ, ambient)`.
  4. At every step, record all `t_c` and `extras["W_flow_CDUP_kW"]`.
  5. Write:
     - `results/series.parquet` (`branch, t_s, rack, t_c, pump_kw`);
     - `results/summary.json`;
     - `plots/*.png`;
     - `provenance/manifest.json` (including `warmup_used_s`, `fmu_s_per_sim_h`, and `environment()`).
- G2 `summary.json` keys:
  - `system`, `n_racks`, `dt_s`, `idle_kw`, `peak_kw`, `total_kw`, `k_full_racks`
  - `packed: {max_c, mean_c, spread_c}`, `spread: {max_c, mean_c, spread_c}`
  - `delta_max_c`, `class` (`"GO"|"WEAK"|"STOP"`)
  - `fmu_s_per_sim_h`, `projected_closed_loop_min_6h` (`= fmu_s_per_sim_h × 6 × 1.5 / 60`)
  - `sane` (bool), `sanity_detail`
  - Statistics use the final 30 min.
- `select_primary(summaries: list[dict]) -> dict` returns `{eligible: [...], ranking: [...], primary: str, runner_up: str | None, class: str, tie_break_applied: bool, rule_version: "spec-2026-10-27-§4.1"}`, implementing spec §4.1 steps 1–5 exactly.
  - CLI: `uv run python -m thermorl2.experiments.select_fmu --out experiments/cross_system/X01_fmu_selection experiments/*/E02_g2_packed_vs_spread/results/summary.json`
  - It writes `results/summary.json`, `results/g2_comparison.csv`, and `plots/g2_cross_system.png` (Δ bar per system, coloured by class, annotated with C_s).

- [ ] **Step 1: Pre-register.** Create the four experiment READMEs (three E02 plus X01) from the template. Fill Question, Pre-registered decision rule (spec §4.1, verbatim), Configuration and Method. Commit:
  ```
  docs(experiments): pre-register E02 G2 on three FMUs and X01 FMU selection rule
  ```
- [ ] **Step 2: Write failing tests.**
  - `packed_vector`: sum and bounds hold; for `total = 3.5·peak + 40.5·idle` (n = 44), there are 3 full racks plus a partial.
  - `uniform_vector`: endpoints are correct.
  - `select_primary` fixtures:
    - (a) the highest Δ wins;
    - (b) a system with `C_s > 30` is ineligible;
    - (c) tie-break: Δ values 2.5 and 2.2, both GO → the lower-C_s system wins;
    - (d) all STOP → `class == "STOP"`;
    - (e) an insane system is excluded.
- [ ] **Step 3: Confirm they fail.** Run `uv run pytest tests/unit/test_probe_vectors.py tests/unit/test_select_fmu.py -v`.
  - Expected: FAIL.
- [ ] **Step 4: Implement**, then run the tests.
  - Expected: PASS.
- [ ] **Step 5: Run G2 on all three systems in parallel**, as three separate processes:
  ```
  uv run python -m thermorl2.experiments.probes g2 --system lassen     --out experiments/lassen/E02_g2_packed_vs_spread &
  uv run python -m thermorl2.experiments.probes g2 --system marconi100 --out experiments/marconi100/E02_g2_packed_vs_spread &
  uv run python -m thermorl2.experiments.probes g2 --system summit     --out experiments/summit/E02_g2_packed_vs_spread &
  wait
  ```
  - Expected wall time: Lassen and Marconi100 a few minutes each; Summit roughly 30–60 min.
  - Re-run the Lassen G2 once and save `provenance/rerun_1.json`. It must confirm a byte-identical `summary.json`.
- [ ] **Step 6: Apply the selection rule.** Run `select_fmu`.
  - Fill the Results, Observations, Conclusion and Provenance sections in all four READMEs.
  - Update the `SYSTEM.md` cost fields and `INDEX.md`.
  - **If `class == "STOP"`: stop now** and write C1 with the G2 results only.
- [ ] **Step 7: Commit.**
  ```
  exp(x01): three-FMU G2 packed-vs-spread screen and mechanical primary-FMU selection
  ```

### Task 4: G1 and G3 on the primary FMU → CHECKPOINT C1

**Files:**
- Output:
  - `experiments/<primary>/E01_g1_uniform/`
  - `experiments/<primary>/E03_g3_room_air/`
- `<primary>` comes from `experiments/cross_system/X01_fmu_selection/results/summary.json`.

**Interfaces (produces):**
- G1 `summary.json` keys:
  - `levels: [{f, rack_kw, mean_c, min_c, max_c, t63_s}]`
  - `fit: {a_c, b_c_per_kw, r2}`
  - `tau_s` (median `t63_s` over f ∈ {.25, .5, .75})
  - `t_hot_c` (the fit evaluated at the f = 0.9 rack kW)
  - `reaches_40c`, `reaches_45c`, `rack_spread_at_f1_c`
  - `t63` = first time the mean-rack rise reaches 63.2 % of its final-15-min rise.
- G3 `summary.json` keys:
  - `affected_racks` (= `whatif_racks`), `t_air_k_affected: 308.15`
  - `delta_affected_c`, `delta_unaffected_c`
  - `sane`, `decision` (`"USABLE"|"NOT_USABLE"`)
  - Also write `results/candidate_cdu_parameters.txt`: FMU variables with causality `parameter`, variability `tunable`, and a name containing `computeBlock[1].cdu[1]`. **List only; do not use.**

- [ ] **Step 1: Pre-register.** Create both READMEs (rules verbatim from spec §4.2). Commit:
  ```
  docs(experiments): pre-register G1 and G3 on primary FMU
  ```
- [ ] **Step 2: Run the probes.**
  ```
  probes g1 --system <primary> --out experiments/<primary>/E01_g1_uniform
  probes g3 --system <primary> --out experiments/<primary>/E03_g3_room_air
  ```
  These run as separate processes and may run in parallel.
- [ ] **Step 3: Write up.** Complete both READMEs, `SYSTEM.md` and `INDEX.md`.
  - Create `thermorl2/experiments/configs/primary.yaml` containing exactly:
    ```yaml
    system: <primary>
    thermal_predictive:
      from: experiments/<primary>/E01_g1_uniform/results/summary.json
      horizon_s: 600
    ```
    All later configs read the system from this file.
- [ ] **Step 4: Commit.**
  ```
  exp(<primary>): G1 uniform sweep and G3 room-air lever on primary FMU
  ```

**CHECKPOINT C1 — FMU selection and physics.** Write `docs/checkpoints/C1-fmu-selection-and-physics.md` with:
- the X01 table (Δ, class, C_s and sanity per system), the primary, the runner-up, and whether the tie-break applied;
- G1 table, fit, `tau_s`, `t_hot_c`, and whether 40 °C or 45 °C is reached;
- G3 decision;
- links to the experiment READMEs.

Push. **Stop.**

---

## Phase 1 — First closed-loop vertical slice (Day 2)

### Task 5: Engine factory, power probe, timing semantics, cost bench

**Files:**
- Create: `thermorl2/raps_adapter/engine_factory.py`, `thermorl2/experiments/bench.py`
- Test: `tests/integration/test_engine_factory.py`, `tests/integration/test_timing_semantics.py`

**Interfaces (produces):**
- `EngineSpec(system: str, sim_time: str = "6h", seed: int = 1)` is a frozen dataclass. `time_delta` is always `POWER_UPDATE_FREQ` of the system.
- `build_engine(spec, jobs=None) -> raps.engine.Engine`:
  - Builds the config with `SingleSimConfig.model_validate`:
    ```python
    {"system", "time", "time_delta": f"{Δ}s", "workload": "random", "numjobs": 1, "seed",
     "noui": True, "output": "none", "cooling": False, "scheduler": "default", "policy": "fcfs"}
    ```
  - If `jobs` is given, sets `engine.jobs = jobs` and `engine.total_initial_jobs = len(jobs)`.
  - Asserts `timestep_start == 0` and `time_delta == Δ`.
  - Does **not** create the generator.
- `rack_kw_from_power_df(power_df, racks_per_cdu) -> np.ndarray` concatenates columns `Rack 1..Rack R`, row-major.
- `is_power_tick(tick, time_delta: int) -> bool` returns `tick.current_timestep % time_delta == 0`.
- `bench.py` CLI: `uv run python -m thermorl2.experiments.bench --system S --hours 6`.
  - Builds an idle engine and a warmed FMU, and steps the FMU on every power tick.
  - Prints JSON: `{system, raps_s, fmu_s, total_s, power_ticks, fmu_steps}`.

- [ ] **Step 1: Failing tests.** All are parametrised over `[primary]` and read `configs/primary.yaml`. Lassen is the fallback if that file is absent.
  - `test_build_engine_defaults`:
    - `cooling_model is None`;
    - `config["NUM_CDUS"]` equals the registry rack count.
  - `test_idle_power_reconciles` (`sim_time = "2m"`, `jobs=[]`):
    - exactly `120/Δ` power ticks;
    - on every power tick, `rack_kw.shape == (n_racks,)`;
    - `|Σrack_kw − Σpower_df["Sum"]| < 1e-6`;
    - `|mean − idle_kw| < 0.05`.
  - `test_power_df_is_stale_between_ticks` (documents the pitfall):
    - `tick.power_df` is non-None on every yielded second;
    - there are exactly `120/Δ` distinct `power_df` objects (`id()`).
  - `test_arrival_scheduled_at_t_powered_at_next_tick`:
    - Use a minimal recording drop-in that places jobs on the lowest free nodes: set `scheduled_nodes`, then `assign_nodes_to_job(job, t, PolicyType.REPLAY)`.
    - One full-rack job: `nodes = NODES_PER_RACK`, `cpu_trace = CPUS_PER_NODE`, `gpu_trace = GPUS_PER_NODE`, `submit_time = 25`, `expected_run_time = 600`, `time_limit = 1200`.
    - Assert the scheduler is called at t = 25.
    - Assert the first power tick where `rack_kw[0] > idle + 0.5·(peak − idle)` is `ceil(25/Δ)·Δ`.
    - **On failure: stop and report.**
  - `test_time_limit_overrun_raises`: a job with `time_limit < expected_run_time` makes the generator raise an `Exception` whose message contains `"time limit"` (case-insensitive). This documents a RAPS limitation.
- [ ] **Step 2: Run.** `uv run pytest tests/integration/test_engine_factory.py tests/integration/test_timing_semantics.py -v` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run again → PASS, then bench the primary.**
  - Run `bench --system <primary> --hours 6`.
  - **Post-selection guard (spec §4.1 step 6):** if `total_s × 2 > 45 × 60`, switch to the X01 runner-up. Re-run Task 4 for that system, update `primary.yaml`, and record the switch in X01's README. Then continue.
  - **Horizon rule:** use `horizon_h: 12` if `total_s × 2 × 2 ≤ 300`; otherwise use 6.
  - Record the bench JSON and the horizon in `SYSTEM.md`.
- [ ] **Step 5: Commit.**
  ```
  feat(adapter): system-generic engine factory, power-tick detection, timing tests, cost bench
  ```

### Task 6: Placement rule and scorers (pure core)

**Files:**
- Create: `thermorl2/core/placement.py`, `thermorl2/core/scorers.py`
- Test: `tests/unit/test_placement.py`, `tests/unit/test_scorers.py`

**Interfaces (produces):**
- `place(scores: np.ndarray, free_nodes_by_rack: list[list[int]], n: int) -> Placement`
  - `rule="single"`: the best-scoring rack with `len(free) ≥ n`; take its lowest `n` node ids.
  - Otherwise `rule="span"`: walk racks in descending score order (ties go to the lower index) and take the lowest free ids until `n` are taken.
  - Raises `ValueError` if fewer than `n` nodes are free in total.
  - `racks` lists the racks in the order used, without duplicates.
- `RackContext` (frozen): `free_count: np.ndarray`, `committed_kw: np.ndarray`, `t_c: np.ndarray`, `job_kw: float`, `job_nodes: int`.
- `Scorer` Protocol: `name: str`, `params: dict`, `score(ctx) -> np.ndarray` (higher is better).
- Scorer implementations:
  - `Packing` → `−arange(n)`
  - `NodeBalance` → `free_count`
  - `PowerBalance` → `−committed_kw`
  - `CoolestRack` → `−t_c`
  - `ThermalPredictive(a_c, b_c_per_kw, tau_s, horizon_s=600.0)` →
    `−(t_c + (a_c + b_c_per_kw·(committed_kw + job_kw) − t_c)·(1 − exp(−horizon_s/tau_s)))`
- `make_scorer(name, params) -> Scorer`, for names `packing | node_balance | power_balance | coolest_rack | thermal_predictive`.

- [ ] **Step 1: Failing tests.**
  - `test_single_rack_preferred`
  - `test_span_in_score_order`: n = 30, free counts 18/10/18, scores ranking rack 1 > rack 0 > rack 2. Expected: 10 nodes from rack 1, 18 from rack 0, 2 from rack 2; all 30 distinct; `rule == "span"`.
  - `test_ties_break_to_lower_index`
  - `test_insufficient_raises`
  - `test_thermal_predictive_formula`: `a = 20`, `b = 0.5`, `τ = 900`, `t_c = [30, 30]`, `committed = [10, 20]`, `job = 5`. Score[0] must equal `−(30 + (20 + 0.5·15 − 30)·(1 − e^(−600/900)))`, and rack 0 is preferred.
  - `test_power_balance_prefers_lowest_committed`
  - `test_make_scorer_names`
- [ ] **Step 2: Run.** `uv run pytest tests/unit/test_placement.py tests/unit/test_scorers.py -v` → FAIL.
- [ ] **Step 3: Implement.** Then run the tests again → PASS.
- [ ] **Step 4: Commit.**
  ```
  feat(core): placement rule and five rack scorers
  ```

### Task 7: PlacementScheduler (RAPS drop-in)

**Files:**
- Create: `thermorl2/raps_adapter/scheduler.py`
- Test: `tests/integration/test_scheduler.py`

**Interfaces:**
- **Consumes:**
  - `place`, `RackContext`, `make_scorer` (Task 6)
  - `RackGeometry`, `job_increment_kw` (Task 2)
  - `build_engine` (Task 5)
- **Produces:**
  - `ThermalView(t_obs_s: float, t_c: np.ndarray, pump_kw: np.ndarray)`.
  - `PlacementScheduler(resource_manager, geometry, scorer, cfg: dict, sink: Callable[[dict], None])`, with plain attributes `policy = PolicyType.FCFS` and `bfpolicy = None`.
  - `schedule(queue, running, current_time, accounts=None, sorted=False)` does the following:
    1. Sort the queue by `(submit_time, id)`.
    2. Head-of-line FCFS: stop at the first job whose `nodes_required > len(available_nodes)`.
    3. For each placed job:
       - build a `RackContext` from the current free nodes, `committed_kw` and the latest `ThermalView.t_c`;
       - score the racks and call `place`;
       - set `job.scheduled_nodes`;
       - call `assign_nodes_to_job(job, current_time, PolicyType.REPLAY)`;
       - append the job to `running` and remove it from `queue`;
       - add the per-rack increment to `committed_kw`;
       - emit one decision row to `sink`.
    4. Never call `check_available_nodes`.
  - `on_power_tick(rack_kw)` sets `committed_kw = rack_kw.copy()`.
  - `on_thermal(view)` stores the view.
  - Decision row keys, exactly:
    `t_s, job_id, nodes_required, policy, rule, racks, nodes, job_kw, scores, t_c, committed_kw, free, t_obs_s, latency_us`
    - Arrays are rounded to 6 decimals.
    - JSON is serialised with `sort_keys=True`.
    - Trace utilisation is the scalar value, or the mean if the trace is a list.

- [ ] **Step 1: Failing tests** (3-minute engine on the primary system).
  - `test_exact_nodes_allocated`
  - `test_policy_attrs_survive_prepare_system_state`: after priming, `policy == FCFS` and `bfpolicy is None`.
  - `test_power_balance_spreads_same_second_arrivals`: two identical 4-node jobs arriving in the same second land on different racks.
  - `test_coolest_rack_herds_same_second_arrivals`: the same setup lands both jobs on the same rack.
  - `test_nodes_distinct_and_free`: 40 random jobs under `power_balance`; no node is ever double-allocated (tracked through the sink).
  - `test_head_of_line_blocking`: a job requiring more nodes than the system has, at the head of the queue, blocks a 1-node job behind it.
- [ ] **Step 2: Run** `uv run pytest tests/integration/test_scheduler.py -v` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/unit tests/integration -q` → all pass.
- [ ] **Step 5: Commit.**
  ```
  feat(adapter): PlacementScheduler drop-in with committed-power tracking and decision rows
  ```

### Task 8: Synthetic workload and RAPS job construction

**Files:**
- Create: `thermorl2/raps_adapter/workload/__init__.py`, `thermorl2/raps_adapter/workload/synthetic.py`, `thermorl2/raps_adapter/jobs.py`
- Test: `tests/unit/test_synthetic.py`, `tests/integration/test_jobs.py`

**Interfaces (produces):**
- `WORKLOAD_COLUMNS = ["id", "nodes_required", "cpu_util", "gpu_util", "submit_time", "expected_run_time", "time_limit"]`
- `SyntheticSpec` (frozen):
  - `rho = 0.6`
  - `node_sizes = (1, 2, 4, 8, 16, 32)`, `node_weights = (0.35, 0.2, 0.2, 0.12, 0.09, 0.04)`
  - `runtime_median_s = 1800`, `runtime_sigma = 0.8`, `runtime_clip_s = (300, 14400)`
  - `cpu_choices = (0.5, 1.0, 1.5, 2.0)`
  - `limit_factor = 1.5`
  - `from_dict(d)`
- `generate(spec, seed, horizon_s, n_nodes, gpus_per_node) -> pd.DataFrame`:
  - GPU utilisation is uniform over `0..gpus_per_node`.
  - Poisson arrivals at rate `rho·n_nodes / E[nodes·runtime]`.
  - `E[nodes·runtime]` is estimated by Monte Carlo (1e6 samples) from the **same** `default_rng(seed)`, drawn before the arrivals.
  - `time_limit = ceil(runtime × 1.5)`.
- `offered_utilisation(df, horizon_s, n_nodes, window_start_s=3600) -> float`
- `write_workload(df, path, meta) -> str`: writes parquet plus `<path>.meta.json` and returns the SHA-256.
- `jobs_from_frame(df) -> list[Job]`:
  - Sets `Job._id_counter = 0`.
  - Builds each job with `job_dict(nodes_required, name=f"j{id}", account="demo", id, cpu_trace=cpu_util, gpu_trace=gpu_util, ntx_trace=0, nrx_trace=0, submit_time, time_limit, start_time=None, end_time=None, expected_run_time)`.
  - **Asserts `time_limit ≥ expected_run_time` for every row.**

- [ ] **Step 1: Failing tests.**
  - Same seed → identical frame and SHA.
  - `offered_utilisation` within ±10 % of 0.6 (6 h, seed 1, primary system sizes).
  - Columns, bounds, and `time_limit ≥ expected_run_time` hold for all rows.
  - `jobs_from_frame` round-trips fields and raises `AssertionError` on a row with `time_limit < expected_run_time`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_synthetic.py tests/integration/test_jobs.py -v` → FAIL.
- [ ] **Step 3: Implement.** Run the tests again → PASS.
- [ ] **Step 4: Commit.**
  ```
  feat(workload): deterministic synthetic workload targeting node utilisation; RAPS job builder
  ```

### Task 9: EpisodeRunner, run CLI, vertical slice → CHECKPOINT C2

**Files:**
- Create:
  - `thermorl2/raps_adapter/runner.py`
  - `thermorl2/experiments/run.py`
  - `thermorl2/experiments/configs/smoke_2h.yaml`
  - `thermorl2/experiments/configs/g4_synthetic.yaml`
- Test: `tests/fmu/test_vertical_slice.py` (marks: `fmu`, `slow`)
- Output: `experiments/<primary>/E10_c2_vertical_slice/`

**Interfaces:**
- **Consumes:** Tasks 2, 5, 7, 8; `FmuBackend`; `provenance`.
- **Produces:**
  - Config schema. The system comes from `primary.yaml` via `include: primary.yaml`:
    ```yaml
    name: g4_synthetic
    include: primary.yaml
    experiment_dir: experiments/{system}/E11_g4_synthetic
    horizon_h: 6                       # per Task 5 horizon rule
    warmup_s: 7200
    workload: {kind: synthetic, rho: 0.6}
    scenario: {name: nominal, label: "", ambient_schedule: []}
    policies: [packing, node_balance, power_balance, coolest_rack, thermal_predictive]
    seeds: [1, 2, 3]
    ```
    Each `ambient_schedule` entry has the form `{start_s, racks: whatif|[...], t_air_k}`.
  - `EpisodeRunner(cfg, policy, seed, run_dir).run() -> Path`:
    1. Generate or load the workload. It is cached at `experiments/{system}/_workloads/<workload-key>_seed<s>.parquet` and reused by SHA.
    2. Build the engine and inject the jobs.
    3. Swap in `PlacementScheduler`, with its sink writing to `decisions.jsonl`.
    4. Construct the `FmuBackend` (SHA verified) and call `warm_up(idle, Ambient(), Δ, warmup_s)`. Publish the initial `ThermalView`.
    5. Iterate the generator. On each `is_power_tick`:
       - `rack_kw` → `scheduler.on_power_tick`;
       - `backend.step(rack_kw, Δ, ambient_at(t))`;
       - `observe()` → `scheduler.on_thermal`;
       - append the interval rows.
    6. At the end, assert `fmu_steps == horizon_s / Δ`. Then write `intervals.parquet` and `manifest.json`.
  - `intervals.parquet` columns: `t_s, rack, kw, t_c, pump_kw, free, it_kw_total, n_running, n_queued, scenario_active`.
  - Manifest adds:
    - `system`, `idle_kw`, `peak_kw`, `warmup_used_s`
    - `t_idle_c` (per-rack, at the snapshot)
    - `thermal_predictive_params`
    - `workload_path`, `workload_sha256`
    - `fmu_steps`, `raps_s`, `fmu_s`, `total_s`
    - `backend: "fmu"`
  - Run directory: `<experiment_dir>/runs/<policy>_seed<seed>/`.
  - CLI: `uv run python -m thermorl2.experiments.run --config <yaml> --policy <p> --seed <s> [--horizon-h H] [--experiment-dir D]`.

- [ ] **Step 1: Pre-register E10.** Create its README.
  - Question: does the closed loop work and preserve the invariants?
  - Rule: invariants 1–5 hold.
  - Commit it.
- [ ] **Step 2: Failing test `test_vertical_slice`.** Run `smoke_2h.yaml` (2 h, ρ 0.6) with `packing` and `power_balance` into `tmp_path`, then assert:
  - all files exist;
  - `it_kw_total` per `t_s` is identical across the two runs (`atol=1e-6`);
  - every decision has `len(nodes) == nodes_required`;
  - Σ`kw` per tick equals `it_kw_total`;
  - `fmu_steps == 7200/Δ`;
  - re-running `packing` yields a byte-identical `decisions.jsonl`.
- [ ] **Step 3: Run** `uv run pytest tests/fmu/test_vertical_slice.py -v` → FAIL.
- [ ] **Step 4: Implement.** Run the test again → PASS.
- [ ] **Step 5: Produce the E10 artifact.**
  - Run the 2 h smoke into `experiments/<primary>/E10_c2_vertical_slice/runs/`.
  - Write `plots/heatmaps.png`: side-by-side rack × time `t_c` heatmaps on a shared colour scale. A minimal function is fine here; Task 11 generalises it.
  - Record time-averaged max-rack °C over [1 h, 2 h] for both runs, plus wall times.
  - Complete the README and INDEX.
- [ ] **Step 6: Commit.**
  ```
  feat(adapter): EpisodeRunner closed loop, run CLI, vertical slice (E10)
  ```

**CHECKPOINT C2 — first closed-loop result.** Write `docs/checkpoints/C2-vertical-slice.md` with:
- the heatmap figure;
- both max-rack numbers;
- `raps_s`, `fmu_s`, `total_s`;
- the invariant results;
- the chosen horizon.

Push. **Stop.**

---

## Phase 2 — Conservative demo complete (Day 3)

### Task 10: Metrics from ledgers and cross-policy invariants

**Files:**
- Create: `thermorl2/core/metrics.py`
- Test: `tests/unit/test_metrics.py`

**Interfaces (produces):**
- `Run(name, intervals, decisions, manifest)` and `load_run(run_dir) -> Run`. This is the only file I/O in `core`.
- `run_metrics(run, eval_start_s, t_hot_c, t_max_c=45.0) -> dict`. Thermal keys use `t_s ≥ eval_start_s`; `t_idle_c` comes from the manifest. Keys:
  - `maxrack_mean_c`, `maxrack_p99_c`, `spread_mean_c`, `mean_rack_c`
  - `hot_rack_seconds`, `thi_t_below_0p1_frac`
  - `pump_energy_kwh`, `it_energy_kwh`
  - `jobs_started`, `wait_mean_s`, `wait_p95_s` (wait is computed from the workload parquet in the manifest)
- `invariants(runs) -> {it_kw_identical, start_times_identical, max_abs_it_kw_diff, fmu_steps_ok}`
- `disagreement_rate(decisions, scorer) -> float`: re-score each logged context, apply `place`, and compare the first rack against the logged `racks[0]`.
- `affected_metrics(run, racks, eval_start_s) -> {maxrack_mean_c}`

- [ ] **Step 1: Failing tests** on a hand-built 3-rack, 4-tick ledger:
  - `maxrack_mean_c` and `spread_mean_c` equal hand-computed values;
  - `hot_rack_seconds = 2 × Δ`;
  - `invariants` is False when one tick differs by 1 kW;
  - `disagreement_rate = 0.5` on a 2-decision fixture.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_metrics.py -v` → FAIL.
- [ ] **Step 3: Implement.** Run the tests again → PASS.
- [ ] **Step 4: Commit.**
  ```
  feat(core): ledger metrics, cross-policy invariants, decision-disagreement diagnostic
  ```

### Task 11: Plots, animation, report builder

**Files:**
- Create: `thermorl2/experiments/plots.py`, `thermorl2/experiments/report.py`
- Test: `tests/unit/test_plots_smoke.py`

**Interfaces (produces):**
- `heatmaps(runs, out_png, vmin, vmax)` — shared colour scale, titled by policy, with a marker at scenario onset.
- `timeseries(runs, out_png)` — max-rack and spread over time.
- `metrics_table(rows, out_md)` — mean with min/max across seeds.
- `animate_grid(runs, out_path, grid, stride_ticks=3)`:
  - side-by-side schematic grids using the system's `grid`;
  - colour = `t_c` on a shared scale;
  - per-rack kW annotation when there are 60 racks or fewer;
  - placement pulses;
  - GIF output (MP4 if ffmpeg is present).
- `g2_figure(experiment_dir, out_png)`.
- `report.py` CLI: `uv run python -m thermorl2.experiments.report <experiment_dir>`. It writes into `<experiment_dir>/results` and `plots`:
  - `metrics.csv`, `metrics.md`, `invariants.json`;
  - `heatmaps_seed1.png`, `timeseries_seed1.png`;
  - `anim_packing_vs_thermal_predictive_seed1.gif`, `anim_power_balance_vs_thermal_predictive_seed1.gif`;
  - `summary.json`, whose `decision` field codes the spec §4.2 rule exactly. Value beyond power holds iff, for every seed, `power_balance.maxrack_mean_c − thermal_predictive.maxrack_mean_c ≥ 0.5`. It also records per-seed packing-vs-thermal gaps and the disagreement rate.
- `t_hot_c` comes from the G1 summary referenced in `primary.yaml`.

- [ ] **Step 1: Failing smoke tests.**
  - Every function writes a non-empty file.
  - `summary.json` on a fixture gives `value_beyond_power: false` when one seed's gap is 0.3.
- [ ] **Step 2: Run → FAIL. Step 3: Implement. Step 4: Run → PASS.**
  - Also write `experiments/cross_system/X01_fmu_selection/plots/g2_packed_vs_spread_<primary>.png`.
- [ ] **Step 5: Commit.**
  ```
  feat(experiments): heatmaps, time series, animated rack grid, report with pre-registered decision rule
  ```

### Task 12: Run matrix and G4 on the synthetic workload → CHECKPOINT C3

**Files:**
- Create: `thermorl2/experiments/run_matrix.py`
- Output: `experiments/<primary>/E11_g4_synthetic/`

**Interfaces (produces):**
- CLI: `uv run python -m thermorl2.experiments.run_matrix --config <yaml> [--policies …] [--seeds …] --workers N`.
  - Launches one `run` subprocess per (policy, seed); each subprocess owns one FMU.
  - Skips a run whose manifest has the same config hash.
  - Exits non-zero if any run fails.
  - `--workers` defaults to `min(6, cpu_count − 2)`.

- [ ] **Step 1: Pre-register E11.** Write the README with the spec §4.2 G4 rule verbatim, and commit it.
- [ ] **Step 2: Implement.** Smoke-test with `smoke_2h.yaml --policies packing,power_balance --seeds 1`; expect 2 runs.
- [ ] **Step 3: Run the full matrix.** `run_matrix --config configs/g4_synthetic.yaml` (5 policies × 3 seeds), then `report experiments/<primary>/E11_g4_synthetic`.
  - If `invariants.json` contains any false value, **stop**.
- [ ] **Step 4: Finish and commit.** Complete the README and INDEX. Commit code, results, plots and runs (subject to the 25 MB rule):
  ```
  exp(<primary>): E11 G4 synthetic, 5 policies x 3 seeds
  ```

**CHECKPOINT C3 — Conservative demo complete.** Write `docs/checkpoints/C3-g4-synthetic.md` with:
- the metrics table and decision;
- per-seed gaps and the disagreement rate;
- invariant results;
- figure and GIF links;
- runtime per run.

Push. **Stop.**

---

## Phase 3 — Alibaba-derived workload (Day 4)

**Prerequisite:** Bipin copies `datasets/alibaba_gpu_2023/` to the same path on Arch. Verify it with `cd datasets/alibaba_gpu_2023 && shasum -a 256 -c checksums.txt`. If the data is missing, stop and ask for it.

### Task 13: Alibaba-derived workload builder

**Files:**
- Create: `thermorl2/raps_adapter/workload/alibaba.py`, `thermorl2/experiments/configs/g4_alibaba.yaml`
- Modify: `runner.py`, to dispatch on `workload.kind`
- Test: `tests/unit/test_alibaba.py` (uses an inline fixture CSV, not the dataset)

**Interfaces (produces):**
- `load_pods(csv_path) -> pd.DataFrame`
  - Drops rows with `pod_phase == "Pending"` and rows with `num_gpu == 0`.
  - Adds `runtime_s = deletion_time − creation_time`.
- `map_pods(pods, gpus_per_node, cpus_per_socket=20) -> pd.DataFrame` with columns `nodes_required, gpu_util, cpu_util, runtime_s, creation_time`, using the spec §3.4 formulas.
- `pod_power_stats(mapped, cfg) -> {mean_node_increment_kw, share_nodes_ge2_gpu}`
- `derive_workload(mapped, rho, horizon_s, seed, n_nodes) -> pd.DataFrame` (columns: `WORKLOAD_COLUMNS`). Steps:
  1. Clip runtimes to [300, horizon_s].
  2. `default_rng(seed)` picks a start offset into the creation-ordered pods. Iterate cyclically from there.
  3. `scale = mean_original_interarrival / target_interarrival`, where `target = E[nodes·runtime] / (rho·n_nodes)`.
  4. Submit times are the cumulative scaled inter-arrivals, cut off at `horizon_s`.
  5. `time_limit = ceil(1.5·runtime)`.
- `choose_variant(raw_dir, cfg) -> dict` computes stats for `default` and `multigpu50`, picks the variant with the higher `mean_node_increment_kw`, and writes `experiments/<primary>/E12_g4_alibaba/results/variant_choice.json` **before any policy run**.

- [ ] **Step 1: Failing tests.**
  - `num_gpu=8, gpu_milli=1000` → `nodes=2, gpu_util=4.0` (G = 4).
  - `num_gpu=1, gpu_milli=500` → `nodes=1, gpu_util=0.5`.
  - With G = 6: `num_gpu=8` → `nodes=2, gpu_util=4.0`.
  - Pending rows are dropped.
  - Same seed → identical frame.
  - Offered utilisation within ±15 % of 0.6 on the fixture.
  - Submit times are sorted and lie in `[0, horizon)`.
  - `time_limit ≥ runtime` for every row.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_alibaba.py -v` → FAIL.
- [ ] **Step 3: Implement.** Run the tests again → PASS.
- [ ] **Step 4: Pre-register E12.** Write its README, run `choose_variant`, and commit the README together with the variant choice.
- [ ] **Step 5: Commit.**
  ```
  feat(workload): Alibaba GPU 2023-derived workload (documented mapping, rate-scaled arrivals)
  ```

### Task 14: G4 on the Alibaba-derived workload → CHECKPOINT C4

- [ ] **Step 1: Run.** `run_matrix --config configs/g4_alibaba.yaml`, then `report experiments/<primary>/E12_g4_alibaba`.
  - Any false invariant → **stop**.
- [ ] **Step 2: Finish and commit.** Complete the README and INDEX:
  ```
  exp(<primary>): E12 G4 Alibaba-derived, 5 policies x 3 seeds
  ```

**CHECKPOINT C4.** Write `docs/checkpoints/C4-g4-alibaba.md`. Same content as C3, plus the variant choice and realised utilisation. Push. **Stop.**

---

## Phase 4 — Visualisation (Day 5)

### Task 15: Three.js side-by-side replay (fallback: Task 11 GIFs)

**Files:**
- Create: `thermoRL/thermorl-v2/viz/` — copy of `thermoRL/thermoRL-new/viz/`, without `node_modules`
- Create: `thermorl2/experiments/export_viz.py`
- Test: `tests/unit/test_export_viz.py`
- Output: `experiments/<primary>/<EID>/plots/replay_<policyA>_vs_<policyB>_seed<s>/` containing `index.html`, `assets/` and `bundle-data.js`

**Interfaces (produces):**
- `export_bundle(run_a, run_b, out_dir, label, grid, stride_ticks=3) -> Path` writes `bundle-data.js`, which defines `window.THERMORL_DATA = {meta, frames_a, frames_b, decisions_a, decisions_b}`.
  - **`meta`:**
    - `system`, `policy_a`, `policy_b`
    - `scenario: {name, label}`
    - `n_racks`
    - `grid: {rows, cols, schematic: true}`
    - `color: {vmin_c, vmax_c}` (shared; 1st/99th percentiles of `t_c` over both runs)
    - `affected_racks`, `metrics_a`, `metrics_b`
  - **frame:** `{t_s, racks: [{t_c, kw, free}], events: [{job_id, racks, rule, decision_index}], maxrack_c, spread_c, it_kw}`. Frames are aligned on identical `t_s` values.
  - **decision:** `{t_s, job_id, nodes_required, racks, scores, t_c, committed_kw, free}`.
- Changes to `viz/src`:
  - Rack count and grid layout are data-driven. This also fixes the old `rowZ` overlap.
  - Colour comes from `t_c`.
  - Remove the zone, PUE and λ drawers.
  - Metric strip shows: max-rack °C, spread, IT kW, jobs started.
  - The "WHY?" drawer shows the selected decision's per-rack score bars, with the chosen racks highlighted.
  - What-if banner, and outlines on the affected racks.
  - The subtitle comes from `meta.scenario.label`.
  - A scrubber over `t_s`.
- **Time-box:** 1 day. If not done by the end of Day 5, the Task 11 GIFs remain the headline visual. Record this in C5.

- [ ] **Step 1: Failing test.** Using fixture runs:
  - equal frame counts in `frames_a` and `frames_b`;
  - identical `t_s` lists;
  - `n_racks` racks in every frame;
  - `vmin_c < vmax_c`.
- [ ] **Step 2: Run → FAIL. Step 3: Implement the exporter. Run → PASS.**
- [ ] **Step 4: Build the viz.** Adapt `viz/`, then `npm ci && npm run build` (expect the build to pass). Copy `dist/*` into each bundle.
- [ ] **Step 5: Export bundles** from E11 seed 1:
  - `packing` vs `thermal_predictive`
  - `power_balance` vs `thermal_predictive`

  Open each `index.html` from disk to verify it works offline, and save a screenshot PNG of each.
- [ ] **Step 6: Commit.**
  ```
  feat(viz): side-by-side rack replay with decision explanations; bundle exporter
  ```

---

## Phase 5 — Degraded-cooling what-if (Day 6; only if G3 is USABLE)

### Task 16: G5 room-air failure what-if → CHECKPOINT C5

**Files:**
- Create: `thermorl2/experiments/configs/g5_whatif_synthetic.yaml` — a copy of `g4_synthetic.yaml` with:
  ```yaml
  name: g5_whatif_synthetic
  experiment_dir: experiments/{system}/E13_g5_whatif_room_air
  scenario:
    name: whatif_room_air_failure
    label: "What-if: room-air cooling failure on one floor section (not observed {system} behaviour)"
    ambient_schedule: [{start_s: 7200, racks: whatif, t_air_k: 308.15}]
  ```
- Test: `tests/fmu/test_vertical_slice.py::test_whatif_schedule_applies`. Runs 2.5 h; asserts `scenario_active` is false before 7200 s and true after; the manifest records the scenario.

- [ ] **Step 1: Pre-register E13.** Write the README with the spec §4.2 G5 rule verbatim, and commit.
- [ ] **Step 2: Run the failing test → implement if needed → PASS.**
- [ ] **Step 3: Run the matrix and report.**
  - `report` also computes `affected_metrics` over `whatif_racks` and applies the 0.5 °C rule both overall and to the affected racks.
  - Export a viz bundle of `power_balance` vs `thermal_predictive`; it must show the what-if banner.
- [ ] **Step 4: Commit.**
  ```
  exp(<primary>): E13 G5 room-air failure what-if, 5 policies x 3 seeds
  ```

**CHECKPOINT C5.** Write `docs/checkpoints/C5-whatif.md`.
- If G3 was NOT_USABLE, C5 is a single paragraph: cite the G3 numbers and the candidate-parameter list, and state that the what-if was not run.

Push. **Stop.**

---

## Phase 6 — Demo packaging (Day 7)

### Task 17: Results note, runbook, demo folder

**Files:**
- Create: `docs/results/2026-11-parasparam-demo-results.md`
- Create: `thermoRL/thermorl-v2/experiments/DEMO.md`
- Modify: `thermoRL/thermorl-v2/README.md` (add a "Reproduce the demo" section)

- [ ] **Step 1: Results note** (≤ 2 pages). It must contain:
  - what ran: systems, configs, SHAs, FMU hashes, workload hashes;
  - the X01 cross-FMU table;
  - G1 and G3 results;
  - the G4 tables for both workloads;
  - G5, if it ran;
  - each pre-registered decision and its outcome, stated plainly;
  - invariants and runtime;
  - spec §6 allowed claims, with the measured numbers filled in;
  - spec §8 limitations, verbatim.
  
  No lifetime, PUE, carbon, heterogeneous-zone or surrogate claims.
- [ ] **Step 2: Runbook.** Exact commands from a clean Arch checkout, in this order:
  1. `uv sync`
  2. FMU smoke
  3. G2 ×3 and selection
  4. G1 and G3
  5. the matrices
  6. the reports
  7. viz export and build
  
  Give expected wall times for each.
- [ ] **Step 3: `DEMO.md`.** Map each headline asset (figure, GIF, replay bundle) to the claim it supports, and to the experiment README it comes from.
- [ ] **Step 4: Fresh-clone check.**
  - Run `uv run pytest -q`. Expect all pass, with the historical test reported as XFAIL.
  - Re-run one E11 run into a scratch directory and confirm its `decisions.jsonl` is byte-identical.
- [ ] **Step 5: Commit.**
  ```
  docs(results): ParasParam demo results note, runbook, demo asset map
  ```

---

## Explicitly out of scope

These require a new steering decision after C5:
- RL / PPO;
- surrogate models (`hpc-cooling-surrogate`, `--cooling-model surrogate`);
- the ExaDigiT server, dashboard or UE5;
- carbon;
- PUE and plant energy;
- FMU-snapshot lookahead;
- a 24 h ramp;
- RAPS patches;
- repository restructuring.

## Plan self-review

- **Spec coverage:**

  | Spec section | Covered by |
  |---|---|
  | §2 S1–S3 | Global Constraints and Task 1 |
  | §3.1 systems | Task 2 |
  | §3.2 semantics (power tick, overrun, output none) | Tasks 5, 7, 9 |
  | §3.3 policies | Tasks 6, 7 |
  | §3.4 workloads | Tasks 8, 13 |
  | §3.5 scenarios | Tasks 2, 4, 16 |
  | §4.1 selection gate | Tasks 3, 5 (post-selection guard) |
  | §4.2 G1, G3 | Task 4 |
  | §4.2 G4 | Tasks 12, 14 |
  | §4.2 G5 | Task 16 |
  | §4.2 secondary metrics | Task 10 |
  | §5 visuals | Tasks 11, 15 |
  | §6 claims, §8 limitations | Task 17 |
  | §7 invariants 1–6 | Tasks 9, 10, 12, 17 |
  | Experiment conventions | Task 1 scaffold; every experiment task pre-registers its README |

- **Type consistency** — these names are used identically across tasks:
  - `SystemSpec(name, fmu_path, fmu_sha256, grid, whatif_racks)`
  - `RackContext(free_count, committed_kw, t_c, job_kw, job_nodes)`
  - `ThermalView(t_obs_s, t_c, pump_kw)`
  - `Placement(racks, nodes, rule)`
  - `Run(name, intervals, decisions, manifest)`
  - `WORKLOAD_COLUMNS`
  - `rack_power_bounds`, `job_increment_kw`, `is_power_tick(tick, time_delta)`
  - the decision-row keys
- **Pre-registration:** every threshold comes from spec §4. None is derived from closed-loop results.

## Approved Task 3 reproducibility clarification (2026-10-27)

Approved by Bipin in conversation on 2026-10-27: compare canonical deterministic scientific-summary bytes and thermal-series content across the Lassen rerun, excluding exactly `fmu_s_per_sim_h` and `projected_closed_loop_min_6h` from the scientific summary. Preserve each full summary and timing measurement separately. X01 uses only the original runs' costs. Do not claim full-summary byte identity. No physical threshold, input, horizon or selection rule changes. Rerun artifacts: `provenance/rerun_1_data/`; comparison: `provenance/rerun_1.json`.

This supersedes only Task 3 Step 5's full-summary byte-identity requirement. The scientific projection excludes exactly the two timing keys above; both full summaries and all thermal data remain preserved. No physical metric or selection rule changes.

## Approved pre-Task-5 decisions (2026-10-27)

**D1 — Summit rack-power reconciliation.** RAPS applies rectifier losses on Summit (`rectifier_efficiency` 0.96, `rectifier_loss_constant` 17 W). `rack_power_bounds` (spec §3.1) omits them, so RAPS `power_df` idle is ≈ 13.8226 kW per rack against the probe value of 13.2017 kW. Peak is ≈ 49.3233 kW against 47.2823 kW. Lassen and Marconi100 are lossless. Therefore:
- (a) Task 5's idle test compares the idle `power_df` rack mean against RAPS's own loss-inclusive rack power. Compute that with a new adapter helper, `raps_rack_kw(cfg, cpu_util, gpu_util) -> float`, which evaluates RAPS's own power code (`PowerManager` / `compute_rack_power`) on a uniform node state. Do not re-implement the loss formula by hand. The tolerance stays at 0.05 kW.
- (b) The exact reconciliation Σ per-rack kW = Σ `power_df["Sum"]` is still required.
- (c) `summit/SYSTEM.md` records both values. It also notes that the C1 probes used loss-exclusive kW, so closed-loop FMU inputs run about 4–5 % higher for the same node utilisation.
- (d) The G1 fit stays valid and frozen. It maps FMU-input kW to coolant temperature, and `power_df` is the FMU input.
- (e) `job_increment_kw` stays frozen. Its roughly 4 % understatement of between-tick committed power on Summit is documented, not corrected.
- (f) No C1 experiment is re-run.

**D2 — Post-selection cost guard (spec §4.1 step 6, spec-literal reading).**
- Measure the Task 5 bench as **one isolated process**: FMU instantiation, the full 7200 s warm-up, and a 6 h idle RAPS+FMU run at the system's power tick.
- Run it with **no other FMU or RAPS simulation on the machine**. Editing and non-FMU unit tests are allowed meanwhile.
- `total_s` is the end-to-end wall time of that process.
- **Switch condition:** `total_s > 2700` (45 min).
- Also report `2 × total_s` and `2 × (total_s − warm-up/instantiation time)` as information only. They do not decide anything.
- The plan's `total_s × 2 > 45 × 60` wording is superseded.
- Horizon rule: unchanged. A 12 h horizon would need `total_s × 2 × 2 ≤ 300`, so Summit uses 6 h.

## Approved C2 preflight representation decisions (2026-10-27)

Decided by the independent reviewer at Bipin's request (review: `docs/checkpoints/C2-preflight-review-opus.md`, reviewed SHA `037b1dd`). These clarify representation only. All earlier frozen sections, D1/D2 and spec §3–§4 values are unchanged.

**R3 — decision latency versus byte-identical decision ledgers: APPROVED WITH CONDITIONS.**
1. Every run's canonical `decisions.jsonl` keeps all 14 plan keys. Its `latency_us` value is always JSON `null`. The scheduler's measured value is never written there.
2. The measured value is written per run to `runs/<policy>_seed<s>/provenance/decision_latency.jsonl`, one JSON line per decision in the same order, `sort_keys=True`. Each line holds exactly: `decision_index` (0-based line number in `decisions.jsonl`), `job_id`, `t_s`, and `latency_ns` (the integer `perf_counter_ns` difference, unrounded).
3. The measured span is the existing scheduler span: context construction → scoring → `place` → RAPS `assign_nodes_to_job` → committed-power update. It excludes the queue sort and ledger I/O. The manifest records this span text plus the SHA-256 and row count of both ledgers.
4. At the end of each run, the runner asserts equal row counts and an exact `(decision_index, job_id, t_s)` join. A unit test covers both the split and the join.
5. Invariant 3 (spec §7) keeps its meaning without weakening: full-file byte identity of `decisions.jsonl`, plus identical `intervals.parquet` values. The timing ledger is a measurement and is excluded from byte comparison.
6. Latency metrics (Task 10, computational) are computed only from the timing ledger. `null` is never read as zero. A missing timing ledger means a missing metric.

**R4 — runtime representation on the 1 s engine: APPROVED WITH CONDITIONS.**
- Root cause (verified in `sim-raps/raps/engine.py:483,584-587,640-657`). RAPS detects completion using the previous second's integer `current_run_time`, and `tick()` raises if `current_run_time > expected_run_time`. A non-integer runtime therefore raises whenever a power tick lands at `start + ceil(R)`. An integer runtime R never raises, and the job completes at `start + R + 1`.
- **Executed representation.**
  - Draw from the frozen lognormal (median 1800 s, σ 0.8), clip to [300, 14400] s, then apply `ceil` to integer seconds. Represented runtimes are integers in [300, 14400].
  - The 1e6-sample Monte Carlo estimate of E[nodes × runtime] uses the identical representation, with draws from the same single `default_rng(seed)`.
  - RNG draw order: Monte Carlo node sizes; Monte Carlo durations; then per job, in order: inter-arrival, nodes, duration, CPU, GPU.
  - `time_limit = ceil(1.5 × represented_runtime)`.
  - All other frozen parameters are unchanged (node sizes and weights, CPU/GPU choices, ρ, Poisson construction).
- **Bounded effect** (do not describe this as "no change").
  - The continuous distribution is the specified one. The executed durations are its discretisation. Each duration increases by less than 1 s (mean ≈ 0.5 s): at most 0.33 % for a 300 s job, about 0.02 % of the mean.
  - Because the Monte Carlo uses the same representation, the arrival rate targets ρ for the executed durations.
  - RAPS's completion bookkeeping adds one further second of occupancy per job (start + R + 1). This is identical across policies.
- **Submit times stay continuous** (exact Poisson floats). RAPS admits a job at the first integer second ≥ `submit_time`; E10 documents this. Waits are measured from the recorded `submit_time`.
- **Required additions to the reviewed Task 8 draft** (`docs/superpowers/proposals/2026-10-27-c2-runtime-representation-draft.patch`):
  - (a) One helper produces represented runtimes for both the Monte Carlo and the per-job draws.
  - (b) A test asserts that `expected_run_time` and `time_limit` are integer dtype and lie within bounds.
  - (c) The workload `meta.json` records:
    - the spec parameters (`asdict`);
    - the representation text;
    - the RNG draw order;
    - `mc_samples`, `mc_expected_node_seconds`, the arrival rate;
    - the generator source SHA-256;
    - numpy, pandas and pyarrow versions.
  - (d) An integration fixture with several integer runtimes (for example 301–310 s, Summit Δ = 10 s) runs to completion across power ticks without exception.
  - (e) `jobs_from_frame` passes Python `float`/`int` traces, not numpy scalars.
  - (f) Overwrite protection is kept, and workload caching is keyed by SHA-256.

**Task 9 interface conditions (from the same review).**
- (i) `run.py` builds the `thermal_predictive` parameters from `primary.yaml` as exactly `{a_c, b_c_per_kw}` (from the G1 `fit`), `tau_s` (top level) and `horizon_s` (yaml), and records that dict in the manifest. `r2` is not passed.
- (ii) Invariant 5 is checked independently. The runner counts its own `backend.step` calls and also asserts `backend.time_s == horizon_s`.
- (iii) The initial `ThermalView` is published after warm-up with `t_obs_s = 0.0`, episode-relative. All `t_obs_s` values are `float`. `pump_kw` comes from `extras["W_flow_CDUP_kW"]`, and its shape is validated.
- (iv) Interval `free` values come from `geometry.free_per_rack(resource_manager.available_nodes)`.
- (v) Committed kW is not reduced between ticks when a job completes. It is corrected at the next power tick. This is spec-literal, identical across policies, and documented in E10.
- (vi) If a run directory exceeds 25 MB (Summit decision rows are ≈ 8.8 KB each), apply the existing gitignore + SHA-256 rule. The schema is not changed.

## Approved post-C2 evaluation decisions (2026-10-30)

Bipin approved the bounded Tasks 10–12 assignment after Opus accepted C2 with conditions (`docs/checkpoints/C2-review-opus.md`, reviewed `b6fb88f`). All policy definitions, G1 parameters, thresholds, workload methodology, FMU selection, primary metric and G4 rule remain frozen. Tasks 13–16 and further experiments are not authorized. Stop at C3.

**S1 — descriptive secondary metrics.** Over `3600 < t_s <= 21600`, report the time mean of across-rack population coolant standard deviation (`rack_t_std_mean_c`), the mean of the hottest `ceil(0.1*n_racks)` racks per tick (`top_decile_mean_c`; 26 on Summit), and across-rack population power standard deviation (`rack_kw_std_mean`). Also report each tick's argmax rack, its share of evaluation ticks, and resident job ids from job events. These do not enter the G4 rule. Residency is measured at the driving RAPS power tick, not at the FMU endpoint.

**S2 — time-axis statement (verbatim).** published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.

**Ledger analysis corrections.** Thermal windows use strict `t_s > eval_start_s`. RAPS-t inputs and FMU endpoint outputs retain their existing mixed interval representation. IT energy sums held kW×Δ; pump energy uses right endpoints, excluding all warm-up. Disagreement compares two scorers applied to the same rounded logged context; self-reproduction against the live choice is separate. Reconstructed free-node lists use globally distinct ids. Latency comes only from the timing ledger; absent means missing. Waits use integer start minus continuous submit; unstarted jobs are censored. Workload paths resolve from the project root.

**Launch conditions.** SHA-key three separate 6 h workloads in the locked Arch environment; select `workload.by_seed`; verify sidecar horizon equals episode horizon. Record every run file's path, bytes and SHA-256, keeping directories above 25 MB ignored. Never overwrite failures: archive under timestamped provenance and record any retry (at most one); scientific stop conditions still take precedence over retries. Extend latency span text and record FMU timing scope. Pre-register E11 before executing the 15-run, three-worker frozen matrix.
