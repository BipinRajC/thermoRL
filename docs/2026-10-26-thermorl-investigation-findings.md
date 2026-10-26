# ThermoRL: Investigation Findings and Demo Readiness (2026-10-26)

**Purpose.** This is a single reference for the current state of ThermoRL before the ParasParam demo plan is written. It records what exists and what has been measured. It also lists what is missing, what is risky, and what must be decided first.

**Status.** Investigation only. No code was changed. Scratch environments used for verification lived only under the system temp directory.

**How to read this.** Every claim carries one label:

| Label | Meaning |
|---|---|
| **[F]** | Fact, verified from code, artifact, or a command run during this investigation |
| **[I]** | Inference, a reasoned conclusion from facts |
| **[A]** | Assumption, plausible but needs validation |
| **[U]** | Unknown, not enough evidence |

**Stated aim.** The aim is the *easiest path to a good, sound demo with visuals*. Section 12 sketches that direction, and the questions in Section 13 each carry a recommended default so you can answer quickly.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Repository map](#2-repository-map)
3. [Architecture: intended vs. built](#3-architecture-intended-vs-built)
4. [Subsystem deep dives](#4-subsystem-deep-dives)
5. [Capability inventory (Artifact 2)](#5-capability-inventory-artifact-2)
6. [End-to-end readiness matrix (Artifact 3)](#6-end-to-end-readiness-matrix-artifact-3)
7. [Experiment evidence ledger (Artifact 4)](#7-experiment-evidence-ledger-artifact-4)
8. [What the physics implies for a scheduling demo](#8-what-the-physics-implies-for-a-scheduling-demo)
9. [Demo readiness assessment (Artifact 5)](#9-demo-readiness-assessment-artifact-5)
10. [Answers to the 13 critical questions](#10-answers-to-the-13-critical-questions)
11. [Risks, technical debt, and known bugs](#11-risks-technical-debt-and-known-bugs)
12. [Direction: the easiest sound demo with visuals (pre-plan sketch)](#12-direction-the-easiest-sound-demo-with-visuals-pre-plan-sketch)
13. [Questions that must be answered before planning](#13-questions-that-must-be-answered-before-planning)
14. [Appendix: key numbers, paths, and commands](#14-appendix-key-numbers-paths-and-commands)

---

## 1. Executive summary

1. **The closed loop has never run.** **[F]** No run has ever fed RAPS rack power into the FMU and then fed FMU temperatures back into a scheduler. That holds on any machine. The pieces exist separately:
   - RAPS Lassen runs (verified on Linux).
   - A standalone FMU backend (verified on Linux).
   - A bit-exact power→FMU-input formula (verified by test).
2. **This Mac cannot run the FMUs.** **[F]** All three FMUs (`lassen`, `summit`, `marconi100`) ship only `win32`, `win64` and `linux64` (x86-64 ELF) binaries; this machine is macOS arm64. FMPy fails with `Cannot find shared library …/binaries/darwin64/Simulator.dylib`. The earlier work ran on an Arch Linux x86-64 machine.
3. **v2 progress is 5 of 21 plan tasks.** **[F]** Task 1.5 (the FMU backend) is committed only as WIP and its gate is not closed. Since 2026-09-29, eight preregistered FMU characterisation experiments were run instead of moving forward.
4. **The v1 "ThermoRL" demo is not evidence.** **[F]** It uses a toy 3-zone simulator (no RAPS, no FMU, no RL) and 24 hand-built jobs. Its Alibaba loader is a stub, and its final metrics are identical to round-robin. Its **three.js visualisation is reusable**.
5. **The Lassen twin is thermally homogeneous and decoupled.** **[F]** It has 44 racks, each on its own CDU. A neighbouring rack responds about **+0.02 °C** to a 29 kW step on another rack. The peak temperature at a given rack power is nearly independent of history (about **40.6 °C** at 40 kW).
   - **[I]** Thermal-aware placement on this twin is almost equivalent to power-balanced placement.
   - **[A]** It should clearly beat RAPS's default lowest-ID *packing*, which concentrates heat. That has not yet been measured.
6. **Other ExaDigiT pieces are not laptop-viable.** **[F]** The ExaDigiT dashboard and server need Druid, Kafka and about 9 containers (32 GB RAM), and their submodules are missing. The server's cooling parser assumes Frontier. The UE5 visualisation is not in the repo.
7. **Alibaba GPU 2023 data is present but has no loader.** **[F]** The data is checksummed. It has 8,152 pods over about 149 days, mostly single or fractional GPUs. It has no power or utilisation columns.
8. **[I] Recommended shape of the demo:** a heuristic thermal-aware controller (not RL) in a RAPS+FMU closed loop on Linux, compared against packing and power-balancing at partial load. It would show rack×time heatmaps and a side-by-side replay.

---

## 2. Repository map

Root: `/Users/bipin/Desktop/thermoRL-new/thermoRL`. Git branch: `feat/thermorl2-phase0-env`, up to date with origin. Only `docs/prompt.md` is modified.

| Path | What it is | State |
|---|---|---|
| `thermoRL/thermorl-v2/` | **Current** ThermoRL v2 (`thermorl2`, Python 3.12, uv, editable RAPS dependency) | Foundations only (Section 4.1) |
| `thermoRL/thermoRL-new/` | ThermoRL v1, frozen reference (Python 3.11) | Self-contained toy simulator plus three.js viz (Section 4.2) |
| `sim-raps/` | ExaDigiT RAPS (Resource Allocator & Power Simulator) | Matches upstream; Lassen config identical (Section 4.3) |
| `sim-server/` | ExaDigiT simulation REST server (FastAPI + Kafka + Druid) | Submodules `raps/` and `simulation_dashboard/` absent (Section 4.4) |
| `sim-dashboard/` | ExaDigiT React dashboard | Reads only the server API (Section 4.4) |
| `exadigit-documentation/` | Sphinx docs (RAPS, cooling model, UE5) | Partly outdated (Section 4.4) |
| `models/POWER9CSM/` | Modelica library plus pre-built FMUs (lassen, marconi100, summit) | linux64/win only (Section 4.5) |
| `datasets/alibaba_gpu_2023/` | Raw `openb_*` CSVs, checksums, provenance JSON | Gitignored; checksums OK (Section 4.6) |
| `docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md` | Approved design spec (October demo, FMU arm) | Authoritative rationale |
| `docs/superpowers/plans/2026-09-12-thermorl-v2-raps-demo.md` | 21-task implementation plan | 5/21 done |
| `docs/superpowers/proposals/2026-09-29-task-1-5-backend-closeout.md` | Task 1.5 closeout gate | Approved, then trial **failed**; decision pending |
| `docs/thermoRL_ODA.pdf` | ThermoRL paper (8 pages) | Different simulator; heterogeneous zones |
| `HANDOFF.md` | Progress log up to 2026-09-29 | Accurate for v2 status |
| `CLAUDE.md` | Project agent rules | Path references are Linux (`/home/bipin/...`) |

**Machine (this session).** **[F]**
- Darwin 25.5.0, arm64 (Apple silicon).
- System `python3` 3.14.5; `uv` at `/opt/homebrew/bin/uv`.
- Docker CLI installed but **daemon not running**; no `podman`.
- No `.venv` in `thermorl-v2/` or `sim-raps/`.

---

## 3. Architecture: intended vs. built

### 3.1 Intended closed loop (design spec §1, §5)

```
job file (parquet, deterministic, hashed)
   │
   ▼
RAPS Engine  (system=lassen, time_unit=1 s, time_delta=20 s, RAPS cooling OFF)
   │  queue, allocation, per-node power → power_df (kW per rack) every 20 s
   ▼
Adapter (thermorl2.raps_adapter)
   │  rack_kW × 1000 × 0.945 → 44 × Q_flow_total inputs; 45 ambient temps (290 K)
   ▼
FmuBackend (thermorl2.thermal)  ── owns the single FMU instance, warm-up snapshot
   │  per-rack coolant T; per-CDU temps, flows, pump kW; facility primary flow
   ▼
Observation + THI (thermorl2.core)
   │
   ▼
RackScorer (heuristic controller) → place() → exact node list
   │
   ▼
RackScheduler drop-in: job.scheduled_nodes = nodes; assign_nodes_to_job(job, t, REPLAY)
   │
   └──► RAPS executes → next power tick → next thermal state → …
   ▼
Ledgers (decisions, intervals, manifest) → metrics → plots
```

### 3.2 What is actually built (v2)

| Layer | Built | Missing |
|---|---|---|
| `core/` | `state.py` (dataclasses), `constraints.py` (THI headroom and paper-raw, hinge, violation), `kernels/rc.py`, `kernels/thi.py` | `placement.py`, `scoring.py`, `heuristics/*`, `ledger.py`, `energy.py`, `metrics.py` |
| `raps_adapter/` | `rack_geometry.py`, `coupling.py` (bit-equal to RAPS) | `engine_factory.py`, `power_probe.py`, `rack_scheduler.py`, `observation.py`, `runner.py`, `jobs.py`, `workload/*` |
| `thermal/` | `base.py` (Protocol), `fmu_backend.py` (single instance, warm-up, snapshot, branch, runtime accounting) | — |
| `experiments/` | (diagnostic scripts under `artifacts/diagnostics/` only) | `characterise.py`, `run_demo.py`, `plots.py`, configs |

### 3.3 Integration seams in RAPS (verified by reading code; never executed)

- **[F]** `Engine.__init__` stores `self.jobs`, and `run_simulation` reads it lazily. Jobs can therefore be injected after construction (`sim-raps/raps/engine.py:276, 756-761`).
- **[F]** The engine uses only `scheduler.schedule(queue, running, t, accounts=, sorted=)` and the settable `.policy` and `.bfpolicy` attributes. `engine.scheduler` can be replaced (`engine.py:725-744, 800-803`).
- **[F]** `ExclusiveNodeResourceManager.assign_nodes_to_job(job, t, policy)` allocates exactly `job.scheduled_nodes` **only when `policy == REPLAY`**. Otherwise it takes the lowest-ID free nodes (`raps/resmgr/default.py:41-60`). It does not check that the given nodes are free; the caller must.
- **[F]** `Scheduler.check_available_nodes` clears `scheduled_nodes` for non-replay policies (`raps/schedulers/default.py:127-136`). A custom scheduler must not call it.
- **[F]** FMU outputs are never referenced by any RAPS scheduler or resource manager. RAPS has no thermal feedback.
- **[I]** RAPS default placement packs jobs into the lowest-numbered racks first (rack = node_id // 18 on Lassen). This makes it a natural "thermally naive" baseline.

---

## 4. Subsystem deep dives

### 4.1 ThermoRL v2 (`thermoRL/thermorl-v2/`)

**Core and adapter [F]**
- **THI headroom:** `clip(1 − max((T−T_idle)/(T_max−T_idle), P/P_max), −0.5, 1)`. Paper-raw form: `1 − max(T/T_max, P/P_max)` (`core/constraints.py:13-22`).
- **Coupling:** `Q_flow_total[i] = rack_kw[i]·1000·0.945/racks_per_cdu` W. Air temperature goes to all `_T_Air` keys and external temperature to `_T_ext`. The integration test matches RAPS `generate_runtime_values` to 1e-9 (`raps_adapter/coupling.py`, `tests/integration/test_coupling_equals_raps.py`).
- **Geometry:** 44 × 1 × 18 = 792 nodes; rack = id // 18.

**FMU backend (`thermal/fmu_backend.py`) [F]**
- A module-level guard enforces one instance per process. It uses `setupExperiment(tolerance=1e-5, startTime=0)`.
- **Per-rack observation:** `simulator[1].datacenter[1].computeBlock[i].cabinet[1].volume.medium.T` (cabinet coolant, K→°C).
- **Per-CDU extras:** `T_sec_r_C`, `T_sec_s_C`, `W_flow_CDUP_kW`, `V_flow_sec_GPM`.
- **Globals:** `fmu.T_prim_supply_C` and `fmu.T_prim_return_C` (from **CDU 1 only**), and `fmu.V_flow_prim_GPM` (datacenter).
- **`warm_up()`:** steps at idle until |dT/dt| < 0.01 K/min over 300 s, or until `max_s` (7200 s). Then it saves the snapshot.
  - In practice it always hit the cap, so the snapshot is "capped, not settled". It drifts −0.9 °C/h.
- **Also provided:** `reset()`, `step()`, `save_state`/`restore_state`/`free_state` (branching), `runtime_s()`, and an idempotent `close()`.

**Tests [F, run this session in a scratch venv]**

| Suite | Result on this Mac |
|---|---|
| `tests/unit tests/integration` | **19 passed** (70.9 s) |
| `tests/fmu` | **1 failed, 4 errors**: missing `darwin64/Simulator.dylib` |

On Linux (recorded in `HANDOFF.md` and the closeout doc):
- 3 lifecycle tests passed.
- The historical physical-response test **fails** (t63 = 1240 s against a 500–1000 s bound).
- The replay gate **failed** its strict intra-process 1e-9 check by 1.43e-4 °C. Direct FMPy and the backend still matched **exactly**.

**Task 1.5 gate status [F]**
- Pending a decision between closeout option **(A)**, keep strict replay identity and keep investigating, and option **(B)**, accept the exact direct/backend agreement and record the FMU replay jitter as a limitation.
- **[I]** The 1.4e-4 °C jitter is about 1/1000 of any effect a demo would show. Option B is scientifically safe.

### 4.2 ThermoRL v1 (`thermoRL/thermoRL-new/`): frozen reference

**Pipeline [F]**
- Stages `s1_extract → s6_bundle` exist. The only runnable entry point is `thermorl/stages/make_demo_bundle.py`, and it **skips s1/s2** and hand-builds 24 identical jobs.
- Scenario and profile YAMLs are read only by tests.

**Simulator [F]**
- State is 3 zones × 16 racks, with rack temperatures starting at 0 °C.
- Thermal model: `T_ss = T_amb + (Q/Q_max)(T_max−T_amb)` plus a first-order RC lag (τ = 60/15/300 s).
- Power is a constant per job. Toy PUE and degradation kernels; carbon is a constant 0.4 intensity.
- No RAPS, FMU, RL or torch.

**Policies [F]**
- Implemented: `round_robin`, `fcfs_naive`, `thi_greedy`, `thi_lookahead` (labelled "ThermoRL"), `threshold_reactive`, `carbon_only`, and `oracle_lp` (not actually an LP).
- In the demo, lookahead degenerates to first-feasible because the air zone pins the facility-minimum THI.

**Alibaba loader [F]**
- `data/alibaba_gpu_v2023.py` is 10 lines and reads nothing. "Alibaba" appears only as a label on PM100-paper constants.

**Metrics [F]**
- `jobs_completed`, violations/1k jobs, emergencies/1k jobs and facility kW are computed.
- Wait, SLO, CO₂/job and cooling-kWh/job are **hardcoded** to 0 or 1.

**Viz [F]** (`viz/`, Vite + TypeScript + three.js 0.170)
- Two side-by-side orthographic 3D floors (round-robin vs "ThermoRL"). Racks are coloured by THI, the newly placed rack pulses, and zones flash during emergencies.
- UI: a metric strip, a "WHY?" decision drawer, a λ drawer, play/scrub controls, and offline inline data via `bundle-data.js`.
- Frame schema: `VizFrame{t, sim_time_s, regime, zones, racks[zone][rack]{THI,T_c,util,color}, events, metrics}`.
- **Bugs:** `rowZ` has 2 entries while `ROWS=4`, so racks 8–15 overlap. Zone and rack counts and names are hardcoded. Frames are aligned by index, not by time.

**Bundle `artifacts/bundles/demo_ramp` [F]**
- 24 frames per policy; final metrics identical (18 jobs, 0 violations, 400 kW).

**Tests [F]**
- 61/61 pass on this Mac (Python 3.11 scratch venv).

**[I] Reusable:** the viz, the bundle and inline-data pattern, and the ledger and decision schemas (good for a "why this rack?" audit trail).

**[I] Not reusable:** the simulator, the Alibaba loader, the metrics, and the bundle numbers.

### 4.3 RAPS (`sim-raps/`)

**CLI [F]**
- Command: `raps run [yaml] --system lassen -t 10m -w random -n 50 --seed 1 --noui -o none`.
- Key flags: `-c` (cooling), `--time-delta`, `--scheduler {default,experimental,fastsim,multitenant,scheduleflow}`, `--policy {replay,fcfs,priority,sjf,ljf}`, `--backfill {firstfit,easy}`, and `-w` (workload: `random`, `synthetic`, `peak`, `idle`, `benchmark`, `randomAI`, `multitenant`, `replay`, …).
- If `--policy` is omitted, the scheduler silently uses `replay`.

**Engine loop [F]**
- Runs every 1 s: admit arrivals → `prepare_timestep` (completions free nodes; TIMEOUT kills when not replaying) → enqueue (`submit_time ≤ t`) → `scheduler.schedule(...)` → `tick()` only when `t % time_delta == 0` (power, optional cooling) → yield `TickData`.

**Power [F]**
- Node power = `cpu_util·CPU_MAX + (CPUS−cpu_util)·CPU_IDLE` + GPU (same form) + MEM + NIC + NVMe. Here `cpu_util` and `gpu_util` are **device counts** (0..2, 0..4), not fractions.
- `power_df` has one row per CDU with columns `[CDU, Rack 1, Sum, Loss…]` in kW.
- **[I]** On Lassen: idle node ≈ 533.8 W and full node ≈ 1,843 W. A rack (with 5 × 250 W switches) runs from **≈ 10.86 kW idle to ≈ 34.4 kW full**.
  - The plan's hand calculation said ~35.9 kW peak. This needs a one-line check (Task 1.6).

**Cooling (`raps/cooling.py`) [F]**
- Reads every variable matching `.summary.`.
- PUE = (ΣQ_in + CDU pumps + HTWP + CTWP + CT)/ΣQ_in. Missing keys default to 0, so on Lassen it **counts only CDU pumps**. The denominator also sums the kelvin temperature inputs (about 13 "kW" of bias).
- Cabinet coolant temperature is **not** read by RAPS.
- `terminate()` is never called.
- **Pitfalls:**
  - The Lassen `fmu_path` resolves to a non-existent `sim-raps/models/...`.
  - With the default `time_delta=1`, the FMU is stepped 20 s on every 1 s tick. **[I]** Its clock would then run 20× fast.

**Schedulers [F]**
- `default` works: FCFS/priority/SJF/LJF, plus EASY or firstfit backfill only.
- Broken:
  - `experimental`: wrong `assign_nodes_to_job` call signature, and an attribute typo.
  - `fastsim`: imports a name that doesn't exist.
  - `scheduleflow`: missing submodule.
  - `RAPSEnv` (gym): wrong method arity, carbon key typo, and it builds a new Engine on reset (a second FMU instance).
  - `rl`: not in the CLI choices.

**Workloads [F]**
- No Alibaba loader. GPU-trace loaders exist for Philly, Marconi100/PM100 and Frontier.
- Lassen's `max_nodes_per_job: 3000` exceeds its 792 nodes, so some `random` jobs never fit.

**Outputs [F]**
- `power_history.parquet`, `util.parquet`, `job_history.csv`, `cooling_model.parquet` (with `-c`), and `stats.out`.
- `stats.out` includes energy, carbon, cost, wait, turnaround and utilisation. The carbon method is **[U]**.
- The queue/running histories are swapped in code.

**Seeding [F]**
- Seed 0 is ignored. `Job._id_counter` is a class attribute that must be reset per episode.

### 4.4 ExaDigiT server, dashboard, and docs

**sim-server [F]**
- Stack: FastAPI + Kafka + Druid (5 services) + Postgres + Zookeeper, roughly 9 containers. The README asks for ≥ 32 GB RAM.
- RAPS comes from an **absent** submodule.
- Lassen replay needs Druid ingestion of LAST data.
- The CEP/PUE output parser assumes Frontier keys (`hotWaterLoop`, `pue`, `V_flow_bypass_GPM`). **[I]** It would KeyError on Lassen with cooling enabled.
- Scheduler choices are the fixed RAPS list.
- An offline `--dest` JSONL mode exists.

**sim-dashboard [F]**
- React + Vite + Plotly.
- Pages: simulation list, summary gauges, console (CDU table with "Rack 1/2/3" columns), cooling time series, jobs.
- No heatmap, no 3D, and **no offline file mode**: it needs the server.

**ExaDigiT UE5 [F]**
- Unreal Engine 5.1 with the FMI plugin, Desktop or HoloLens 2. It needs Epic GitHub access and an ORNL repo; nothing is present locally.

**[I] Feasibility:** none of these three is a realistic demo surface on this laptop in the time available.

### 4.5 FMUs (`models/POWER9CSM/fmus/`)

| FMU | Size | Compute blocks (1 CDU + 1 cabinet each) | Inputs | `.summary.` vars | Binaries |
|---|---|---|---|---|---|
| `lassen.fmu` | 11.6 MB | **44** | 89 (44 Q, 44 T_Air, 1 T_ext) | 1,014 | win32, win64, linux64 (x86-64) |
| `marconi100.fmu` | 12.5 MB | 49 | 99 | 1,129 | same |
| `summit.fmu` | 47.1 MB | 257 | 515 | 5,913 | same |

**Lassen FMU details [F]**
- FMI 2.0 Co-Simulation (Dymola 2024x, Sdirk34hw, tol 1e-5), 66,197 variables.
- Flags: `canBeInstantiatedOnlyOncePerProcess=true`; get/set and serialize state supported.
- SHA-256 `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`.

**Available signals [F]**
- **Per CDU (×44):** primary/secondary supply and return temperatures, flows (GPM, kg/s), pressures, CDU pump power `W_flow_CDUP_kW`.
- **Per cabinet:** coolant `volume.medium.T`.
- **Facility:** primary flow.
- CDU control setpoint: 40 °C.

**Not available [F]:** PUE, central-plant power (HTWP, CTWP, tower fans), facility power. Lower-level local variables exist (plant pump `.W`, tower cells), but nobody has validated them.

**Topology [F]**
- All three FMUs use one cabinet per CDU, and racks are coupled only through the shared primary/central plant loop. **[I]** No FMU offers shared-CDU coupling.

**`T_Air` inputs [F]**
- There are 44 per-cabinet `T_Air` inputs ("Room Air Temperature", start value 297.2 K). RAPS and v2 set them all to 290 K.
- **[U]** Whether varying them changes cabinet coolant temperature meaningfully. This is the possible lever for legitimate heterogeneity (Section 8).

### 4.6 Alibaba GPU 2023 (`datasets/alibaba_gpu_2023/`)

**Provenance [F]**
- `cluster-trace-gpu-v2023` (Weng et al., FGD, ATC'23); clusterdata HEAD `0d0f3f1…`; prepared 2026-09-11.
- `checksums.txt` (25 lines) verifies OK.

**Pod CSV header [F]:** `name,cpu_milli,memory_mib,num_gpu,gpu_milli,gpu_spec,qos,pod_phase,creation_time,deletion_time,scheduled_time`

**`openb_pod_list_default.csv` [F]**

| Field | Value |
|---|---|
| Pods | 8,152 |
| Creation span | 0 → 12.9 M s (≈ 149 days) |
| Lifetime p50 / p90 / max | 540 s / 6,574 s / 12.5 M s |
| Phases | Running 5,193; Failed 1,870; Pending 897 (no `scheduled_time`); Succeeded 192 |
| `num_gpu` | 1 → 6,989; 0 → 1,088; 8 → 44; 2 → 16; 4 → 15 |
| `gpu_milli` | Often fractional (shared GPUs) |
| `gpu_spec` | Empty everywhere |

**Node list [F]**
- 1,213 GPU nodes and 6,212 GPUs. Models: G2 549, T4 404, P100 134, V100M16 55, G3 39, V100M32 30, A10 2.

**[I] Implications**
- Arrivals average about 55 pods/day over the full span. A faithful real-time replay would barely load Lassen (792 nodes, 3,168 GPUs). Time compression or resampling to a target load is needed.
- RAPS's resource manager is node-exclusive, while Alibaba pods share GPUs fractionally. A mapping rule is needed (Section 13, W-questions).
- There is no power data, so power must come from the RAPS node power model driven by a GPU utilisation proxy.

---

## 5. Capability inventory (Artifact 2)

| Subsystem | Exists | Partial | Missing | Unknown |
|---|---|---|---|---|
| RAPS Lassen simulation (no cooling) | ✔ (Linux) | | | Mac execution |
| RAPS built-in cooling (`-c`) on Lassen | | ✔ (path bug, step-size pitfall, PUE incomplete) | | Whether it runs end to end |
| Custom placement hook (no patch) | | ✔ (seams read, untested) | | |
| v2 FMU backend | ✔ (Linux) | | | Mac via Docker amd64 |
| Power→FMU coupling formula | ✔ | | | |
| RAPS→FMU closed loop | | | ✔ | |
| Thermal-aware controller(s) | | ✔ (v1 toy policies only) | ✔ (v2) | |
| Baseline controllers on RAPS | | ✔ (RAPS default FCFS = packing) | ✔ (round-robin, load-balance in v2) | |
| Workload generator (ramp) | | | ✔ | |
| Alibaba loader / mapper | | | ✔ | Mapping rules |
| Metrics from ledgers | | | ✔ | |
| Ledger / manifest / provenance | | ✔ (diagnostics follow the discipline; v1 schemas) | ✔ (v2 runtime ledgers) | |
| Static plots | | ✔ (diagnostic plots; RAPS plots) | ✔ (demo plots) | |
| Interactive visualisation | | ✔ (v1 three.js, toy data) | | |
| ExaDigiT dashboard / UE5 | | ✔ (code present) | | Laptop feasibility (likely no) |
| RL agent | | | ✔ | |
| Carbon accounting | | ✔ (RAPS stat, constant v1 intensity) | | RAPS carbon method |
| PUE / facility energy (Lassen) | | ✔ (CDU pumps only) | ✔ (plant power) | |
| Reproducible env on this Mac | | ✔ (non-FMU parts) | ✔ (FMU) | Docker amd64 |

---

## 6. End-to-end readiness matrix (Artifact 3)

| Pipeline link | Status | Evidence / note |
|---|---|---|
| Workload loading: RAPS synthetic | **Likely** | Phase 0 CLI smoke on Linux (exit 0). Unverified on Mac. |
| Workload loading: Alibaba | **Missing** | No loader anywhere |
| Job generation (deterministic file) | **Missing** | Plan Task 3.1 not started |
| Scheduling (custom drop-in) | **Missing** | Interface verified by reading only |
| Placement (exact nodes via REPLAY) | **Likely** | `resmgr/default.py:41-60` read; never executed |
| RAPS execution | **Verified (Linux)** / **Unverified (Mac)** | `tests/systems/test_engine_basic.py -k lassen` passed on Linux |
| Power accounting (per rack) | **Likely** | `power_df` layout read; reconciliation test not yet written |
| FMU coupling | **Verified (formula)** / **Missing (runtime)** | Equality test passes; never driven by RAPS |
| Thermal response | **Verified (Linux)** / **Broken (Mac)** | 8 diagnostics; darwin binary absent |
| Metrics | **Missing** | v1 metrics are placeholders |
| Visualisation | **Partial** | v1 three.js replay; v2 none |
| Baseline comparison | **Missing** | |

**Earliest broken link:** running the FMU on the current machine. The earliest *missing* link is the engine factory and scheduler drop-in (plan Task 1.6, then 2.x).

---

## 7. Experiment evidence ledger (Artifact 4)

All entries are under `thermoRL/thermorl-v2/artifacts/diagnostics/`.

**Shared protocol, unless noted [F]**
- Lassen FMU (hash above), 290 K air and external temperature, heat factor 0.945.
- Background 10.86 kW per rack; rack 1 stepped to 40 kW (+29.14 kW electrical, +27.5 kW heat).
- 20 s ticks, 3600 s horizon.
- Paired design: one saved state, a no-step control, a step branch, and the reported quantity is step − control.
- Every run was repeated in a fresh process with **byte-identical** results. That shows determinism, not statistical spread.
- All ran on the Linux host.

### A. `task_1_5_matched_step_20s`
- **Purpose:** explain the historical test failure by matching background power to the warm-up level.
- **Configuration:** 7200 s capped warm-up at 10.86 kW; rack 1 → 40 kW; others held at 10.86 kW; 3600 s.
- **Findings:**
  - Rack 1 rose 29.656 → 40.135 °C (+10.48 °C).
  - t63 = 1280 s elapsed (1260 s by the test's index).
  - Peak 40.561 °C at 2760 s (non-monotone).
  - Neighbours fell −0.885 °C.
- **Limitations:** no control, so the neighbour change is confounded with drift.
- **Confidence:** high. **Runtime:** 5.6 s wall for 3 simulated hours.
- **Current relevance:** explains the gate failure. Low value for the demo.

### B. `task_1_5_followup` (exact §3.2 probe, no-step control, `characterization_report.md`)
- **Purpose:** reproduce the spec probe and separate drift from coupling.
- **Findings:**
  - The cold-start 15 s probe reproduces **t63 = 750 s** (34.15 → 39.97 °C; peak 40.59 °C at 3495 s).
  - The warmed no-step control drifts **−0.908 °C/h**.
  - Matched step minus control at 3600 s: rack 1 **+11.39 °C**; racks 2–44 **+0.023 °C**; CDU 1 primary return +4.08 °C; supply +0.025 °C.
- **Limitations:** only one cold-start trajectory.
- **Confidence:** high.
- **Current relevance:** **high**. It establishes rack independence and snapshot drift.

### C. `task_1_5_state_dependence`
- **Purpose:** does the response depend on plant state?
- **Configuration:** state A = 1800 s from cold; state B = 7200 s warmed.
- **Findings:**
  - Paired rack-1 response at 3600 s: +9.74 °C (A) vs +11.39 °C (B); maximum difference 2.32 °C at 2560 s.
  - Raw peaks are nearly equal (40.59 vs 40.56 °C) but 1120 s apart in time.
  - Neighbours ≤ +0.032 °C.
- **Confidence:** high for these two states.
- **Current relevance:** low for the demo.

### D. `task_1_5_state_sufficiency` (preregistered)
- **Purpose:** can current observables predict the response?
- **Configuration:** 8 states on one trajectory (60–7200 s); leave-one-state-out ridge regression ladder.
- **Findings:**
  - Paired final rise ranges +8.15 to +11.39 °C.
  - **Absolute peak 40.561–40.670 °C regardless of starting temperature (29.7–38.2 °C).**
  - Coolant-only model is best (held-out MAE 0.23 °C on the final value, 0.016 °C on the absolute peak).
  - Richer models extrapolate badly.
- **Limitations:** the states are collinear.
- **Current relevance:** **high**. The steady temperature is set by power, not history.

### E. `task_1_5_off_trajectory`
- **Purpose:** does the frozen coolant-only model transfer to other preconditioning paths?
- **Configuration:** three paths matched to 32 ± 0.1 °C (protocol revised v1→v3, documented).
- **Findings:** final errors −0.035 / +0.234 / −0.144 °C; observed spread 0.384 °C from 0.018 °C initial spread.
- **Conclusion:** coolant is useful but not sufficient.
- **Current relevance:** low.

### F. `task_1_5_state_identification`
- **Purpose:** which of CDU return, slope or flow explains the residual?
- **Findings:**
  - Paired final spread 0.621 °C.
  - Primary flow is the best predictor (LOPO MAE 0.052 / 0.027 °C).
  - Return and slope are collinear (r = 0.9997).
- **Conclusion:** no causal claim.
- **Current relevance:** low.

### G. `task_1_5_placement_relevance` (preregistered)
- **Purpose:** does a thermal-state-aware single-job placement reduce peak temperature?
- **Configuration:** 4 scenarios (plant context × preheated candidate); candidates rack 1 vs rack 44.
  - Blind rule: prelisted round-robin.
  - Aware rule: frozen coolant+flow peak predictor. Flow cancels, so it is effectively "pick the cooler rack".
- **Findings:**
  - The rules disagreed in 2 of 4 scenarios. In both, the aware choice had a **higher peak, by 0.0018 / 0.0016 °C** (a negligible difference).
  - Its final temperature was 0.276 °C lower.
  - All peaks were about 40.56 °C.
- **Limitations:** single job, single-rack perturbation, no RAPS, no closed loop.
- **Current relevance:** **high**. Choosing the cooler rack does not change a single job's peak on this twin.

### H. `task_1_5_backend_replay_trial` (closeout gate)
- **Purpose:** independent backend correctness check.
- **Configuration:** 7200 s capped preconditioning, then a 960 s asymmetric 4-phase sequence over all 44 inputs and ambient, replayed twice in separate processes for direct FMPy and the backend.
- **Findings:**
  - Direct and backend outputs are **identical (difference 0)** on both passes.
  - Within each process, replay 1 vs replay 2 differ by up to **1.43e-4 °C** (starting at 740 s), which fails the 1e-9 gate for both access paths.
  - The rollback flag and deserialisation did not fix it.
- **Current relevance:** **blocks Task 1.5 closure.** **[I]** The jitter is irrelevant at demo scale.

### Experiment-level conclusions

- **Answered and done (do not repeat):** rack independence (B), power-set peak (D), cooler-rack single-job value (G), backend fidelity (H direct vs backend).
- **Low marginal value:** C, E, F (state and history characterisation).
- **FMU runtime [F, derived]:** about 1.2–2.8 s of wall time per simulated hour (about 8–15 ms per 20 s step) on Linux. A 24 h FMU-only run takes about a minute.
- **Not yet measured:** RAPS's per-second Python loop cost for 24 h, and the cost of the full closed loop.
- **Never tested:**
  - load-distribution effects (packing vs spreading)
  - multi-job interactions
  - `T_Air` sensitivity
  - degraded-CDU parameters
  - the uniform-load sweep (plan Task 1.7)

---

## 8. What the physics implies for a scheduling demo

1. **Placement moves heat, it cannot remove it.** **[I]** Total IT heat is fixed by the workload. On Lassen each rack's temperature is essentially a lagged function of *its own* power (neighbour effect about 0.02 °C per 29 kW). A scheduler can only change *where* heat goes.
2. **The expected visible effect is hotspot reduction relative to packing.** **[A, untested]**
   - RAPS's lowest-ID packing should fill racks 0..k. Full racks (about 34 kW) should sit near the high 30s °C while idle racks stay around 29–30 °C.
   - Spreading the same jobs should flatten the rack×time heatmap and lower the maximum rack temperature, at identical IT energy.
   - This is physically sound and visually striking.
3. **Thermal-aware and power-balanced placement will likely look nearly identical.** **[I]** With homogeneous, decoupled racks, "coolest rack" and "least-loaded rack" rank racks almost the same way (the cooler rack is mostly the less-loaded one, with lag). Experiment G already shows that state information beyond that adds only fractions of a degree.
4. **The 45 °C T_max probably never binds.** **[I]**
   - The peak at 40 kW is about 40.6 °C, and a full rack is about 34.4 kW (< 40 kW). So with the spec's T_max = 45 °C, the temperature term of THI stays well below 1.
   - THI violations would then be driven by the `P/P_max` term, i.e. "rack ≥ 90 % of peak power".
   - This must be reported honestly, not tuned. The plan's Task 1.7 uniform-load sweep is designed to measure exactly this.
5. **Overload removes placement freedom.** **[I]** When offered load ≥ 1, every rack is full whatever the policy. Differences appear only at partial load (roughly 30–80 % utilisation). The spec's planned 24 h ramp spends 10 h at ρ = 1.5, so that whole phase would show no difference between policies.
6. **Making thermal awareness genuinely matter needs heterogeneity.** **[U]** Two candidate levers, both modelled on real conditions the paper itself cites (maintenance, degraded cooling, hot aisles):
   - **Per-rack `T_Air`** (room air temperature): for example, a "hot aisle" or "CRAH failure" region with higher inlet air on some racks.
   - **FMU tunable parameters** (2,877 exist): for example, a degraded CDU with reduced pump capacity or heat-exchanger effectiveness.

   If either visibly changes rack temperature at a given power, a thermal-aware controller would avoid the affected racks, and a power-only balancer could not tell them apart. **This is the only path to an honest "thermal-aware beats power-aware" result on this twin.** The spec currently forbids "artificial heterogeneity", so this needs your explicit decision (Q-S4).

---

## 9. Demo readiness assessment (Artifact 5)

| Deliverable | Status | What exists | What is missing |
|---|---|---|---|
| A. Working simulation | **Partial** | RAPS runs (Linux); FMU backend runs (Linux) | Runtime on this Mac; connecting the two |
| B. Scheduling behaviour | **Not started** | Interface seams understood | Drop-in scheduler, controllers |
| C. Closed-loop thermal response | **Not started** | Coupling formula verified | Runner synchronising RAPS ticks ↔ FMU |
| D. Baseline comparison | **Not started** | RAPS default FCFS (packing) | Shared workload, multiple controllers, same seed |
| E. Results | **Not started** | Thermal characterisation only | Metrics, result note |
| F. Visualisation | **Partial** | v1 three.js replay, RAPS/diagnostic plots | Data adapter for Lassen, demo plots |
| G. Reproducibility | **Partial** | `uv.lock`, hashes, preregistration discipline | Working FMU runtime here; run manifests |

---

## 10. Answers to the 13 critical questions

1. **Smallest end-to-end path that works today?**
   - On this Mac: only the v1 toy pipeline, which is not credible.
   - On Linux: RAPS-only Lassen runs and standalone FMU stepping, but never together.
2. **Earliest broken link?** FMU execution on this machine. After that, the engine factory and scheduler drop-in, which don't exist.
3. **Most likely to prevent a successful demo?**
   - (a) The runtime environment: FMU binaries are x86-64 Linux only.
   - (b) Scenario design that produces a null or near-null result: overload phase, or comparing only against load-balancing.
   - (c) Process paralysis from strict gates.
4. **Experiments that already answered useful questions?** B (independence, drift), D (power-set peak), G (cooler-rack single-job value is negligible), H (backend equals direct FMU).
5. **What should not be repeated?** State/history characterisation (C, E, F), replay-identity tuning, and v1 toy comparisons.
6. **Untested assumptions:**
   - packing produces visible hotspots under RAPS
   - the FMU runs under Docker `linux/amd64` on this Mac
   - RAPS 24 h loop cost
   - spec §5.8 timing semantics
   - `T_Air` and parameter sensitivity
   - an Alibaba→Lassen mapping that yields meaningful load
   - the rack peak power figure (34.4 vs 35.9 kW)
7. **Thermal parameters available today:**
   - per-rack cabinet coolant temperature
   - per-CDU primary and secondary supply and return temperatures, flows, pressures, pump kW
   - facility primary flow
   
   **Not available:** PUE, plant power.
8. **Scheduling inputs available today:** free nodes per rack, rack power (`power_df`), queue contents, job size, time limit, CPU/GPU utilisation of jobs, plus the FMU signals above once coupled.
9. **Measurable outputs today:** RAPS stats and parquet histories; FMU diagnostic CSVs. No closed-loop outputs.
10. **Can thermal-aware scheduling be demonstrated with current capabilities?**
    - Mechanically, yes, once the loop is built (about 6 v2 modules).
    - Scientifically: "beats packing, roughly ties power-balancing" **[I]**, unless a heterogeneity scenario is approved.
11. **Is RL feasible before the deadline?** **[I] No credible path.**
    - No working environment; the RAPS gym environment is broken.
    - One FMU instance per process.
    - About 1–2 min per 24 h episode before RAPS cost.
    - A nearly null objective on the homogeneous twin.
12. **Would a thermal-aware heuristic be the better demo strategy?** **[I] Yes.** It is explainable, deterministic, fast, and matches the spec's D12 ("heuristic controllers + reproducible plots, no trained RL").
13. **Simplest credible demo if time is short:**
    - Lassen RAPS+FMU closed loop on Linux.
    - One synthetic workload at partial load.
    - Three controllers: RAPS-style packing, load-balance, coolest-rack.
    - 6–12 simulated hours.
    - Visuals: a side-by-side rack×time coolant heatmap, a max-rack temperature line, and a metrics table.
    - A one-paragraph honest result note.

---

## 11. Risks, technical debt, and known bugs

### 11.1 Demo risks (ranked)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | FMU cannot run on available hardware | High on Mac / Low on Linux box | Blocks C, D, E | Use the Linux machine, or spike Docker `--platform linux/amd64` first |
| R2 | Null thermal result vs load-balance | High **[I]** | Weak story | Lead with packing as the naive baseline; partial-load scenario; optional approved heterogeneity scenario |
| R3 | Strict gates stall progress again | High (history) | Schedule | Adopt a lighter demo-mode protocol (keep provenance, drop blocking gates that don't affect demo validity) |
| R4 | RAPS 1 s Python loop too slow for 24 h × N controllers | Medium **[U]** | Schedule | Measure early; shorten horizon (6–12 h); run controllers in parallel processes (one FMU each) |
| R5 | Alibaba mapping consumes the timeline | Medium | Scope | Use synthetic first; Alibaba-derived distributions second |
| R6 | Visualisation over-engineering | Medium | Schedule | Static plots first; three.js replay as a stretch |
| R7 | T_max = 45 °C never binds, so THI looks meaningless | High **[I]** | Credibility | Measure (Task 1.7), report honestly, decide the framing explicitly |
| R8 | Overload phase erases differences | High **[I]** | Weak result | Scenario at partial load, or report per phase |

### 11.2 Technical debt and bugs

**RAPS** (avoid these paths rather than fixing them)
- Lassen `fmu_path` points to a non-existent location.
- The FMU step is mismatched when `time_delta ≠ 20`.
- PUE counts only CDU pumps and includes kelvin inputs in the denominator.
- `terminate()` is never called.
- The `experimental`, `fastsim` and `scheduleflow` schedulers and `RAPSEnv` are broken.
- The queue/running histories are swapped.
- The backfill guard is always true.
- Seed 0 is ignored.
- `max_nodes_per_job` (3000) exceeds 792.
- The temperature plot uses a non-Lassen key.

**v1**
- Rack temperatures start at 0 °C.
- Deferred jobs are dropped.
- Running jobs are never drained.
- The viz `rowZ` overlap.
- Hardcoded zone and rack counts and the scenario subtitle.
- Placeholder metrics.

**v2**
- Global primary supply/return come from CDU 1 only (label precisely).
- The warm-up snapshot is capped, not settled (−0.9 °C/h drift).
- Spec-internal inconsistencies about the t63 bounds (750 s ± 5 % vs 500–1000 s vs 450–1050 s) are flagged in the closeout doc.
- `defer_reeval_s = 60` is justified by a fixed time constant that the data do not support.

**Environment**
- Plan and `CLAUDE.md` paths are `/home/bipin/...`.
- The `uv` cache path assumes Linux.
- No virtual environments exist on this Mac.

---

## 12. Direction: the easiest sound demo with visuals (pre-plan sketch)

> This is a **direction**, not the master plan. It is written to make the questions in Section 13 concrete. The master plan (P0–P5 with objectives, dependencies, validation, artifacts, risk and relevance) follows once those questions are answered.

### 12.1 Proposed demo story (one sentence)

> "On ORNL's Lassen digital twin (RAPS power model + POWER9 cooling FMU), the same GPU workload is scheduled by three policies. The default packing scheduler creates rack hotspots; a thermal-aware scheduler that reads live coolant temperatures from the twin spreads the heat, lowering peak rack temperature with no throughput cost. *(Optionally:)* when part of the cooling degrades, only the thermal-aware scheduler notices and routes around it."

### 12.2 Minimal vertical slice (what has to exist)

1. **Runtime:** x86-64 Linux (existing box or Docker `linux/amd64`), plus `uv sync` for `thermorl-v2`.
2. **Close Task 1.5** under option B; keep the historical test as a documented failure.
3. **Engine factory and power probe** (plan Task 1.6, slimmed): build Lassen with RAPS cooling off, inject jobs, swap the scheduler, read per-rack kW.
4. **RackScheduler drop-in plus three scorers:**
   - `lowest_id` (packing; reproduces RAPS default)
   - `load_balance` (thermal-blind spreading)
   - `coolest_rack` (thermal-aware, using FMU coolant temperature)
5. **EpisodeRunner:** RAPS ticks → every 20 s, step the FMU → refresh observation → write an interval row; log every decision.
6. **Workload:** one deterministic synthetic file at partial load (for example ρ ≈ 0.5–0.7) over 6–12 h. Then an Alibaba-derived variant if time allows.
7. **Metrics:** max-rack coolant temperature over time, rack-temperature spread (std or max−min), time above a threshold, jobs completed, mean and p95 wait, IT energy, CDU pump energy.
8. **Visuals** (see 12.3).

### 12.3 Visual options, cheapest first

| Option | Effort | Impact | Notes |
|---|---|---|---|
| V1. Static matplotlib figures: side-by-side rack×time coolant heatmaps (one per controller, shared colour scale); max-rack and spread lines; metrics table | Low | High | Minimum demo; directly from ledgers |
| V2. Animated heatmap or "floor view" GIF/MP4 (matplotlib animation of 44 racks as a 4×11 grid coloured by coolant temperature, jobs appearing) | Low–Medium | High | Works in any slide deck; no web stack |
| V3. Adapt the v1 three.js side-by-side replay to 44 Lassen racks (data-driven layout, fix `rowZ`, time-aligned frames, shared colour scale, "WHY this rack?" drawer fed by decision ledgers) | Medium | Very high | Offline single-file bundle already proven; the most "demo-like" |
| V4. ExaDigiT dashboard / UE5 | High / very high | High | **Not recommended**: infrastructure and access blockers (Section 4.4) |

**[I] Recommendation:** V1 is mandatory and V2 or V3 is the headline visual. V3 gives the strongest live impression, but it depends on V1's data pipeline anyway.

### 12.4 What *not* to do for the demo

- No RL training. The most RL could be is a clearly labelled "future work" slide.
- No ExaDigiT server or dashboard stack, and no UE5.
- No further FMU state or history characterisation.
- No 24 h ramp into sustained overload as the headline scenario. It erases differences.
- No carbon claims unless an explicit, documented intensity source is approved.
- No tuning of thresholds, loads or heterogeneity after seeing results.

### 12.5 Cheap spikes that would de-risk planning (each well under a day)

| Spike | Question | Control / intervention | Metric | Interpretation |
|---|---|---|---|---|
| S1. FMU runtime | Does `lassen.fmu` run here under Docker `linux/amd64` (or on the Linux box), and how fast? | Run the existing `tests/fmu` lifecycle tests | Pass/fail; seconds per simulated hour | Pass, so plan locally; fail or too slow, so plan on the Linux box |
| S2. RAPS loop cost | Is a 6–24 h Lassen run tractable per controller? | `raps run --system lassen -t 6h --noui -o none` with a fixed workload | Wall time | Sets the horizon and the number of controllers |
| S3. Packing vs spreading (FMU-only proxy) | Does concentrating the same total power create a visible hotspot? | Same total kW: packed (k racks at peak, others idle) vs uniform | Max-rack T, spread at steady state | Confirms the demo's core visual before building the loop |
| S4. Heterogeneity lever (only if allowed) | Does per-rack `T_Air` (or a CDU parameter) change coolant T at fixed power? | All racks 290 K vs a subset at e.g. 300–305 K | ΔT coolant on affected racks | Large: a legitimate "hot aisle" scenario exists. Negligible: drop it. |

---

## 13. Questions that must be answered before planning

Each question has a **recommended default** that favours the easiest sound demo. Answer "default" to accept it.

The most decision-critical questions are **D2, D4, R1, R2, S3 and S4**.

### Demo expectations

| ID | Question | Recommended default |
|---|---|---|
| D1 | What is ParasParam (internal HPE review, conference, customer)? Who is the audience, and how long is the slot? | — (needed) |
| D2 | What is the hard date, and how many working days are available? | — (needed) |
| D3 | Live run, recorded video, or slides plus a pre-computed interactive replay? | Pre-computed runs plus an offline interactive replay (no live simulation on stage) |
| D4 | Success means (a) the loop runs, (b) a measured thermal-aware advantage, or (c) an honest comparison even if null vs power-balancing? | (c), with the "beats packing" result as the headline |
| D5 | Must the demo use the ThermoRL name, THI and the paper's framing? Must it cite the paper's numbers? | Use the ThermoRL and THI names; do **not** reuse the paper's numbers (different simulator) |
| D6 | Does this mission supersede the 2026-09-12 spec's scope (Alibaba, viz, RL were out of scope)? | Yes: new demo spec derived from the old one; old spec kept as history |

### Repository and process

| ID | Question | Recommended default |
|---|---|---|
| R1 | Is the x86-64 Linux machine (Arch, `/home/bipin/...`) still available? Or any x86 Linux server? | — (needed). Fallback: Docker `linux/amd64` on this Mac (spike S1) |
| R2 | Close Task 1.5 under closeout option B (backend equals direct FMU exactly; 1.4e-4 °C restore jitter recorded as a limitation)? | Yes |
| R3 | Switch to a lighter "demo mode" protocol: keep hashes, manifests and honest reporting, but drop blocking stop-and-report gates that don't affect demo validity? | Yes |
| R4 | Keep the v2 architecture (`core` / `thermal` / `raps_adapter`) as the base? | Yes |
| R5 | Keep the "no RAPS patches" rule? | Yes (not needed for the demo) |
| R6 | Leave the historical Task 1.5 physical-response test failing (documented) and remove it from the default test run? | Yes (mark it `xfail` with a reason) |

### Experiments

| ID | Question | Recommended default |
|---|---|---|
| E1 | Approve spikes S1–S3 (Section 12.5) before the master plan? | Yes |
| E2 | Approve spike S4 (heterogeneity lever)? | Yes, but only if S-question S4 below allows heterogeneity |
| E3 | Run the plan's Task 1.7 uniform-load sweep (0/25/50/75/100 %) to establish the operating range and whether 45 °C is reachable? | Yes, slimmed (it also feeds colour scales and thresholds) |

### RAPS

| ID | Question | Recommended default |
|---|---|---|
| P1 | System = Lassen? (Summit has 257 racks, also 1 CDU each, and a much larger FMU.) | Lassen |
| P2 | Simulated horizon per run? | 6–12 h (24 h only if S2 shows it is cheap) |
| P3 | Use RAPS's own node power model (utilisation → watts) for job power? | Yes |
| P4 | Decision cadence: event-driven (on RAPS scheduler calls) with the latest ≤ 20 s-old thermal state? | Yes |

### FMUs

| ID | Question | Recommended default |
|---|---|---|
| F1 | Accept that PUE and plant energy are unavailable for Lassen, so energy is reported as IT energy plus CDU pump energy only? | Yes |
| F2 | Thermal limit framing: keep T_max = 45 °C (likely never reached, so THI is driven by the power term)? Or adopt a threshold tied to the model, e.g. the 40 °C CDU setpoint? Decide **before** seeing scheduler results. | Decide after the E3 sweep, before any controller comparison |
| F3 | Ambient: fixed 290 K for air and external? | Yes, unless S4 introduces a documented hot-aisle profile |

### ExaDigiT

| ID | Question | Recommended default |
|---|---|---|
| X1 | Does "ExaDigiT" in the demo mean the RAPS + POWER9CSM FMU twin components (feasible)? Or must the ExaDigiT dashboard or UE5 itself appear (likely infeasible)? | The twin components, credited clearly on slides |

### Scheduling

| ID | Question | Recommended default |
|---|---|---|
| S1 | Which baselines are mandatory? | `lowest_id` (RAPS-default packing), `load_balance`; optional `round_robin` |
| S2 | Thermal-aware controller(s)? | `coolest_rack` (THI or coolant-based); optional `threshold_reactive` |
| S3 | Is "thermal-aware ≈ power-balancing on this homogeneous twin; both clearly beat packing" an acceptable headline? | Yes |
| S4 | Allow a **documented, physically motivated heterogeneity scenario** (hot-aisle `T_Air` on some racks, or a degraded CDU), framed as a "maintenance or degraded cooling" event? This overrides the old spec's "no artificial heterogeneity". | Yes, as a second scenario, defined before results and reported alongside the homogeneous baseline |
| S5 | Include `DEFER` (admission control), or placement only? | Placement only (simpler; no fairness logic) |
| S6 | Is RL strictly optional (P5) and may it be shown only as future work? | Yes |

### Workload (Alibaba)

| ID | Question | Recommended default |
|---|---|---|
| W1 | Is Alibaba data **mandatory** in the demo, or is a synthetic workload acceptable with Alibaba as a second variant? | Synthetic first; Alibaba-derived second |
| W2 | Which pod list? | `openb_pod_list_default.csv` |
| W3 | A faithful replay would barely load Lassen. Accept time-compression or resampling to a target load, keeping the trace's empirical job sizes, durations and arrival burstiness? | Yes: "Alibaba-derived", clearly labelled |
| W4 | How to map pods onto RAPS's exclusive-node model? | `nodes = max(1, ceil(num_gpu/4))`; `gpu_util = num_gpu × gpu_milli/1000` per node (capped at 4); CPU from `cpu_milli`; drop 0-GPU pods or map them as CPU-only |
| W5 | Failed and Pending pods? | Drop Pending (never scheduled); keep Failed with their observed lifetime |
| W6 | Cap extreme lifetimes (max 12.5 M s)? | Clip to the simulated horizon |

### Metrics

| ID | Question | Recommended default |
|---|---|---|
| M1 | Primary (pre-specified) thermal metric? | Peak and time-averaged **max-rack coolant temperature**, plus **rack-temperature spread** |
| M2 | Secondary metrics? | Time above threshold, THI violation fraction (framing per F2), CDU pump energy, IT energy |
| M3 | Performance metrics to show "no throughput cost"? | Jobs completed, mean and p95 wait, utilisation |
| M4 | Carbon? | Excluded (or one explicit constant-intensity line clearly labelled illustrative) |
| M5 | Seeds and repeats? | 1 seed for the demo; 3 seeds if runtime allows, for a robustness footnote |

### Visualisation

| ID | Question | Recommended default |
|---|---|---|
| V1 | Is the static figure set (Section 12.3, V1) the minimum? | Yes |
| V2 | Headline visual: animated GIF/MP4 (V2) or adapted three.js replay (V3)? | V3 if time allows, else V2 |
| V3 | Lassen floor layout: physical rack positions aren't in the repo. Is a schematic grid (e.g. 4 rows × 11) acceptable? | Yes, labelled schematic |
| V4 | Show the "why this rack?" decision explanation (scores per rack) in the viz? | Yes (cheap from decision ledgers; strong for an audience) |

---

## 14. Appendix: key numbers, paths, and commands

### 14.1 Key numbers

| Quantity | Value | Label |
|---|---|---|
| Lassen topology | 44 CDUs × 1 rack × 18 nodes = 792 nodes; 2 CPUs + 4 GPUs per node | F |
| RAPS power tick (Lassen) | `power_update_freq: 20` s | F |
| Rack power idle / full | ≈ 10.86 kW / ≈ 34.4 kW (plan's hand calc ≈ 35.9 kW) | I (verify) |
| Heat factor into FMU | 0.945 | F |
| Default ambient | 290 K air and external | F |
| CDU control setpoint | 40 °C | F |
| Rack coolant at capped warm idle | ≈ 29.66 °C | F |
| Response to 10.86 → 40 kW | +8.2 to +11.4 °C paired; absolute peak ≈ 40.56–40.67 °C | F |
| t63 | 750 s (cold-start probe) to 1300 s (warmed) | F |
| Neighbour coupling | +0.02 to +0.04 °C per 29 kW step | F |
| Warm-snapshot drift | −0.9 °C per hour | F |
| FMU cost | ≈ 1.2–2.8 s wall per simulated hour (Linux) | F (derived) |
| Backend vs direct FMU | identical; restore jitter 1.43e-4 °C | F |

### 14.2 Key paths

- FMU: `models/POWER9CSM/fmus/lassen.fmu`
- RAPS Lassen config: `sim-raps/config/lassen.yaml`
- RAPS seams: `sim-raps/raps/engine.py` (loop at 741-845, cooling call at 654-658), `sim-raps/raps/resmgr/default.py:41-60`, `sim-raps/raps/schedulers/default.py`
- v2 package: `thermoRL/thermorl-v2/thermorl2/`
- Diagnostics: `thermoRL/thermorl-v2/artifacts/diagnostics/`
- v1 viz: `thermoRL/thermoRL-new/viz/src/` (`main.ts`, `scene/racks.ts`, `schema/vizevent.ts`)
- v1 bundle: `thermoRL/thermoRL-new/artifacts/bundles/demo_ramp/`
- Alibaba: `datasets/alibaba_gpu_2023/raw/openb_pod_list_default.csv`, `openb_node_list_gpu_node.csv`

### 14.3 Commands verified this session (scratch environments, repo untouched)

- **v1 tests:** `UV_PROJECT_ENVIRONMENT=<tmp>/thermorl_v1_venv uv run --frozen --extra dev pytest -q -p no:cacheprovider` → **61 passed**.
- **v2 unit and integration:** with a Python 3.12 scratch venv (fmpy 0.3.32, RAPS dependencies, `PYTHONPATH` to `thermorl2` and `sim-raps`), `pytest tests/unit tests/integration -q` → **19 passed**.
- **v2 FMU:** `pytest tests/fmu -q` → **1 failed, 4 errors**: `Cannot find shared library …/binaries/darwin64/Simulator.dylib`.
- **FMU binaries:** `unzip -l models/POWER9CSM/fmus/lassen.fmu | grep binaries` → win32, win64, linux64 only.
- **Docker:** `docker info` → daemon not running.

---

*Next step: answer Section 13 (defaults are acceptable). Then run spikes S1–S3 if approved, followed by the ThermoRL Master Plan (P0 vertical slice → P1 baseline experiment → P2 characterisation → P3 scheduling improvements → P4 visualisation → P5 optional RL).*
