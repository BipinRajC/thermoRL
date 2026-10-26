# Surrogate Repository, RAPS Update, and FMU Selection — Assessment (2026-10-27)

**Status:** **APPROVED 2026-10-27, with these decisions:**
- Amendments A1–A7 are approved.
- `hpc-cooling-surrogate` is removed from git integration. It stays as a local reference clone for future work and is not a dependency.
- Nested `.git` folders stay as they are and are documented in `docs/repository-notes.md`.
- Bipin may ask Wes Brewer for Summit or Frontier bundles; this does not block anything.
- FMU-first: FMUs are the only thermal backend.
- **The primary FMU is selected by a three-FMU G2 gate (Lassen, Summit, Marconi100) with pre-defined criteria. Lassen is not assumed.** This supersedes §6's "Lassen stays primary if GO" rule. The final rule is in spec §4.1.

All of this is incorporated into the FINAL spec, plan, experiment conventions and Sol prompt.

**Inputs:** `hpc-cooling-surrogate/`, the RAPS update in commit `39a7fa6`, the documentation update in commit `2295f17`, and prior documents (`2026-10-26-thermorl-investigation-findings.md`, `2026-10-27-thermorl-demo-strategy.md`, and the 2026-10-27 spec and plan).

**Method:**
- Two independent read-only investigations, one per repository.
- Tests and smoke runs in scratch virtual environments.
- A reconstructed surrogate model timed on this Mac.
- The RAPS power model evaluated for all three systems.
- The repository was not modified.

**Labels:** **[F]** fact (verified from code or artifact, or measured) · **[I]** inference · **[U]** unknown.

---

## 0. Executive summary

1. **The surrogate repository cannot be used for this demo.**
   - **[F]** It contains **no trained weights or checkpoints**. They are absent from the repo, from all three branches, from GitHub releases, and from the Zenodo record.
   - **[F]** Lassen has no trained model at all.
   - **[F]** The surrogate predicts **CDU summary variables only**. It does not predict the per-rack cabinet coolant temperature that our plan uses.
   - **[F]** Its accuracy is only modestly better than persistence ("hold the last value"). At a 10-minute horizon, temperature MAE is 0.246 °C versus 0.262 °C for persistence.
   - **[F]** On the developers' own branches, the Marconi100 surrogate fails inside RAPS, and the Frontier surrogate drifts after 15–30 minutes.
2. **Recommendation: option B, use the surrogate later.**
   - Keep the FMU as the only thermal backend for the demo.
   - Keep `ThermalBackend` pluggable so a surrogate backend can be added after the demo.
3. **The RAPS update does not break the plan.**
   - **[F]** Every engine seam we rely on is unchanged.
   - **[F]** The v2 unit and integration tests pass on the new RAPS: **19 passed**.
   - The investigation did find **two bugs in our own plan** that predate the update, and **one environment issue**. All are corrected in §7:
     - (a) The planned `is_power_tick` test is wrong. RAPS keeps the last `power_df` on every second between ticks, so the test would step the FMU **20× too often**.
     - (b) RAPS never kills jobs for exceeding their time limit. It raises an exception instead.
     - (c) `uv.lock` must be refreshed.
4. **FMU selection.** **Lassen remains the leading candidate. Summit is the backup.**
   - Summit racks reach about **47 kW** at peak, against about 35 kW on Lassen. That could produce larger thermal contrasts.
   - A cheap **cross-FMU G2 screen** on Day 1 turns this into a measured decision.
5. **Repository hygiene blocker.**
   - **[F]** `hpc-cooling-surrogate` is committed as a bare gitlink (mode 160000) with **no `.gitmodules`**. A pull on Arch will produce an **empty directory**.
   - This does not block the FMU work, but it must be fixed or documented.

---

## 1. Surrogate repository assessment

### 1.1 What it is

**[F]** It is **research code** with an SC26 paper attached. It is not production infrastructure.

- **History and authorship:**
  - `main` has 6 commits by one author (Yishak Tadele), dated 2026-09-24 to 2026-09-26.
  - Two branches by Wes Brewer (ORNL), `origin/frontier` and `origin/marconi100`, contain the RAPS integration work and the export tooling (`export_for_raps.py`).
- **Engineering maturity:**
  - No tests and no CI.
  - `pyproject.toml` packages a bundled *old RAPS copy* as "raps 0.0.1", not the surrogate code.
  - The Makefile references a `main.py` that does not exist.
- **Weights policy:** `CLAUDE.md` on the branches says: *"Never commit model weights, normalizers or exported bundles"*.
- **Claims that are not supported by artifacts:**

  | README claim | Evidence |
  |---|---|
  | `sc26-camera-ready` release tag | Does not exist |
  | Zenodo record "data and model weights" | Contains data only |
  | 19,514× speedup | Appears only in the README. The artifact (`rollout_speedup.csv`) gives 16,093×, computed against a *hard-coded* FMU cost of 65.43 s per 30 s step. |
  | 0.492 closed-loop skill | Appears only in the README. The artifact gives a temperature-group skill of 0.227 at 27–30 min. |
  | `models/` directory | Contains copies of the same three FMUs we already have (byte-identical), not trained models |

### 1.2 Relationship to ExaDigiT, RAPS, and the FMUs

- **FMUs:** `fmu2ml` drives the Dymola FMUs to *generate training data*.
  - Inputs are sampled independently per CDU (Latin-hypercube scenarios: steps, ramps, Ornstein–Uhlenbeck processes, pulses).
  - `T_Air` covers about 293–313 K; `T_ext` is varied with weather.
  - The FMUs are needed for training and validation, and **not** for inference.
- **RAPS:** the integration lives in **our updated `sim-raps`**, not in this repo.
  - `raps/cooling_surrogate.py` and the `--cooling-model surrogate` option load a TorchScript `model.ts` plus `bundle.json` from `cooling.surrogate_path`.
  - Surrogate paths are configured for Frontier, Marconi100 and Lux. **Lassen and Summit have no entry.**
  - The bundle directories are gitignored and absent.
- **ExaDigiT:** this is ExaDigiT's official route to replacing the FMU inside RAPS for speed. The updated docs do not yet mention it.

### 1.3 Per-system maturity

| System | Weights | Public data (Zenodo) | Reported accuracy | Maturity for our use |
|---|---|---|---|---|
| **Summit** (257 CDUs) | None | 11 h + 25 h systematic, 10 h operational, 2 h spatial. The 720 h training set is unpublished. | P5 model: temperature R² ≈ 0.999 teacher-forced; rollout MAE 0.6 °C at 30 min, about 10–25 % better than persistence | Best documented as research; **cannot be run** |
| **Frontier** (25 CDUs) | None (FMU not public) | Private | Within 1–2 °C for 15–30 min, then linear drift (branch docs) | Most integrated at ORNL; inaccessible to us |
| **Marconi100** (49 CDUs) | None | 11.4 h systematic, 24 h operational, 5 h spatial | **Fails in RAPS**: T_prim_s off by about +17 °C, flows about 5× too high (branch README) | Not usable |
| **Lassen** (44 CDUs) | **None; no model ever trained** | 3.8 h systematic, 10 h operational, 5 h spatial | — | **None** |

### 1.4 Dependencies

| Phase | Needs FMU? | Needs Linux? | Needs GPU? |
|---|---|---|---|
| Training data generation | Yes | Yes (x86-64 Linux, or Windows) | No |
| Training | No | No | Practically yes. Summit used 8 GPUs; Frontier used one A6000. |
| Validation | Yes (held-out FMU chunks or a RAPS comparison) | Yes | No |
| Initialization | No (quadratic steady-state fit plus 1200 s relaxation) | No | No |
| Inference | No | **No** | No |

### 1.5 Feasibility on the Mac

**[F] Measured.** I reconstructed the exact P5 architecture from the repo's code and config. The parameter count, 5,868,638, matches the repo's own summary. The weights are random, because none exist.

| Model size | Forward pass, batch 1 (CPU) | Forward pass, batch 1 (MPS) |
|---|---|---|
| Summit-sized | 6.5 ms | 5.3 ms |
| Lassen-sized (2.6 M params) | 6.2 ms | 5.2 ms |

- **[I]** Inference is not the bottleneck. Only the missing weights are.

### 1.6 Fit for a scheduler loop

- **Output variable.** The surrogate does not output `cabinet[1].volume.medium.T`. The nearest proxy is `T_sec_r_C`, which RAPS labels "Rack Return Temperature". Switching would change our primary signal and invalidate the existing characterisation evidence.
- **Effective cadence.** Temperature heads advance in **30 s strides** with linear interpolation, so a power change reaches the temperature outputs **up to 30 s late**. This is coarser than our 20 s coupling.
- **Spatial input patterns.** The training data does include non-uniform per-CDU power, which helps packed-vs-spread scenarios.
- **Ambient range.** RAPS feeds 290 K, which is *below* the training range for `T_Air`. Inputs get clipped, and this is a suspected cause of the Marconi100 failure.
- **State handling.** There is no save/restore API, so no snapshot branching or lookahead.
- **[I]** Even with weights, the surrogate would be a *less faithful, coarser* stand-in for exactly the variable we rely on.

---

## 2. RAPS update (commit `39a7fa6`): impact

### 2.1 Unchanged

**[F]** These all still hold:
- Engine construction.
- Lazy reading of `engine.jobs`.
- Replaceable scheduler. The interface is `schedule(...)` plus settable `policy` and `bfpolicy`.
- `prepare_system_state` sets REPLAY and then restores the previous policy.
- Tick-loop order.
- Arrival at t=25 → scheduled at 25 → powered at the t=40 tick.
- `power_df` columns `['CDU','Rack 1','Sum','Loss 1','Loss']`, 44 rows.
- The REPLAY exact-node allocation path.
- The `job_dict` and `Job._id_counter` interfaces.
- `compute_node_power`.
- `generate_runtime_values`, which is byte-equal to our coupling (the test passes).
- Idle rack power 10.858 kW.
- Test result: **19 passed**.

### 2.2 Corrections required in our plan (these errors predate the update)

| Plan item | Problem | Correction |
|---|---|---|
| Task 4: `is_power_tick := tick.power_df is not None` | **[F]** `power_df` is non-None on all 120 of 120 seconds; RAPS reuses the last object between ticks. The runner would step the FMU 120 times instead of 6, so FMU time would run 20× fast. | `is_power_tick(tick) := tick.current_timestep % tick.time_delta == 0`. Add a runner invariant: number of FMU steps = horizon / Δ. |
| Task 4: `test_timeout_kill_active_with_dropin` | **[F]** `run_simulation` calls `prepare_timestep` with `replay=True`, so nothing is ever killed. `tick()` instead **raises** "Job exceeded time limit". This was true before the update too. | Replace the test with one that asserts the exception is raised. Workload generators (Tasks 7, 12) must guarantee `time_limit ≥ expected_run_time` for every job; their tests already check this. Document it as a RAPS limitation. |
| Task 1: `uv run` | **[F]** `uv lock --check` fails because RAPS added `textual` and raised the `requests` version. | Task 1 runs `uv lock` and commits `uv.lock`. |
| Global: output | **[F]** If `output` is unset, RAPS now writes `./runs/<ts>-…` | `output: "none"` stays mandatory. Add `runs/` to `.gitignore`. |

### 2.3 New in RAPS (optional value)

- **Textual terminal UI** (`raps/ui/app.py`): Node Map, Power and Cooling views, including a per-CDU heat grid.
  - It shows the cooling view only when RAPS's own cooling is enabled.
  - It accepts `RapsApp(source=<UISnapshot iterable>)`, so it *could* replay our ledgers. It shows one run at a time with no side-by-side comparison.
  - **Optional stretch** visual only.
- **Surrogate backend hook** (`--cooling-model surrogate`): useful later, irrelevant this week.
- **Updated docs** give run timing: about 2 min per simulated day for Lassen and Marconi100 with FMU cooling; **Summit about 2 min per 2000 simulated seconds**, i.e. about 85 min per simulated day.

---

## 3. Answers to the specific questions

1. **What is it?** Research code, between experimental and research-prototype maturity. It is not production-ready (§1.1).
2. **Relationship to ExaDigiT, RAPS and the FMUs:**
   - an ExaDigiT project;
   - trained on FMU-generated data;
   - integrated into upstream RAPS as an optional cooling backend (§1.2).
3. **Can it replace the FMUs?**
   - Not for any of our three systems today: no weights exist.
   - Lassen: never trained.
   - Summit: trained at ORNL, weights unpublished.
   - Marconi100: fails in RAPS.
   - Only Frontier has a working bundle, and it is ORNL-internal.
4. **What still needs FMUs?**
   - Training data and validation: yes.
   - Initialization and inference: no.
   - Once trained and exported, a bundle runs independently of the FMU.
5. **Assets present:**
   - Code: `fmu2ml` (data generation, training, evaluation) and 5 model architectures.
   - Configs for 7 systems.
   - Summit training-run reports (metrics.csv, report.md, histories).
   - Analysis notebooks with saved plots (data analysis, not accuracy).
   - One benchmark notebook.
   - Copies of the 3 FMUs.
   - **No weights, normalizers, exported bundles or tests.**
6. **Could it be used for screening, scheduler development, sweeps, visualization or RL prototyping?**
   - Only if weights existed. Even then, accuracy close to persistence and the missing cabinet temperature limit its value.
   - **[I]** A *calibrated per-rack first-order model* fitted to our own G1 FMU data would serve screening, development and Mac-side visualization better. Lassen racks are nearly decoupled and their peak temperature is set by power.
   - That model is an optional development tool, never a source of reported results.
7. **Does it overcome the Linux-only FMU constraint?**
   - In principle, yes for inference: train on Linux or a GPU, run on the Mac (measured ~6 ms per forward pass).
   - In practice, not this week: training needs about 25–200+ h of FMU data plus GPU training, followed by validation.
   - The Arch-runs / Mac-renders split already solves the platform problem.
8. **Maturity per system:**

   | System | Maturity |
   |---|---|
   | Lassen | None |
   | Summit | Research-documented, not runnable |
   | Marconi100 | Trained but inaccurate |
   | Frontier | The only one integrated, not accessible |

9. **Does it change our strategy?**
   - FMU selection: no.
   - Experiment plan: no, apart from the cross-FMU screen, which is motivated by Summit's power density rather than the surrogate.
   - Architecture: only to keep `ThermalBackend` pluggable, which it already is.
   - Scheduling: no.
   - Visualization: no.
10. **Recommendation: B, use the surrogate later.** Reasons:

    | Option | Verdict |
    |---|---|
    | A — ignore it | Wastes a credible future-work and scale narrative. ExaDigiT has an official surrogate path that a ThermoRL scheduler could plug into. |
    | C — run it in parallel | Impossible without weights. Training our own Lassen surrogate (Linux data generation plus GPU training plus validation) would consume most of the week, for a model about as good as persistence that lacks our signal. |
    | D — use it as the primary backend | Worse: less faithful, coarser, unvalidated for Lassen. It would replace verified physics with an unverified approximation. |

    The FMU is not even the bottleneck on Lassen: about 1–3 s of FMU wall time per simulated hour (measured), or about 2 min per day including RAPS (docs).

---

## 4. What becomes possible now that was previously infeasible

| Newly possible | Evidence | Use this week? |
|---|---|---|
| A credible **"path to scale" narrative**: ExaDigiT RAPS natively supports ML-surrogate cooling, so the same placement policies could run at Summit or Frontier scale, and at RL-training speed, once bundles exist | `cooling_surrogate.py`; `--cooling-model surrogate` | Yes, as a **future-work slide** only |
| **Mac-side thermal inference** (~6 ms per step) if weights are ever obtained, removing the Linux dependency for development and visualization | Measured on M4 Pro | No |
| A documented **recipe for training our own Lassen surrogate**, using `fmu2ml` generators and Zenodo Lassen data (about 19 h) as a seed | Repo plus Zenodo | No (post-demo) |
| **Independent FMU data** (Zenodo Lassen, Summit and Marconi100 parquet) for cross-checking our characterization | Zenodo API listing | Optional, low priority |
| A live **terminal "twin" view** (RAPS Textual UI, per-CDU heat grid) fed from our ledgers | `raps/ui/app.py`, `source=` | Optional stretch |
| A **higher-power-density Summit** run is better motivated: ExaDigiT treats Summit as its flagship cooling model, and RAPS documents its cost | RAPS config, docs | Yes, **screen only** (§5) |
| Asking ORNL for weights is a concrete request: a Frontier bundle exists, and Summit and Marconi100 checkpoints exist on ORNL systems | Branch docs, run logs | Optional parallel ask (Bipin → Wes Brewer). Non-blocking. |

## 5. What remains infeasible even with the surrogate repository

- **Heterogeneous air / D2C / immersion zones.** No FMU or surrogate models them. The surrogates are trained on the same three POWER9 liquid-cooled plants.
- **Strong rack-to-rack coupling.** Every FMU has one CDU per cabinet. A surrogate learns the same physics.
- **Validated PUE or plant-energy objectives.** The surrogates explicitly exclude the central energy plant, and the Lassen FMU lacks plant outputs.
- **Cabinet coolant temperature from a surrogate.** Not an output; it would require retraining.
- **A runnable surrogate this week, for any of our systems.** No weights exist.
- **Using a surrogate as validated evidence.** Its skill over persistence is about 10–25 %, and the developers report drift and failures in RAPS.
- **RL in a week.** Still limited by the schedule and by the weak homogeneous objective. The surrogate removes neither problem.
- **The degradation signal, cooling-setpoint control, node- or GPU-level thermals, and reproducing the paper's numbers.** Unchanged.

---

## 6. FMU selection (explicit decision)

| Criterion | Lassen | Summit | Marconi100 |
|---|---|---|---|
| Racks × nodes × GPUs per node | 44 × 18 × 4 (792 nodes) | 257 × 18 × 6 (4,626 nodes) | 49 × 20 × 4 (980 nodes) |
| Rack power, idle → peak **[F, RAPS model]** | 10.86 → 34.4 kW (35.9 kW with network at full) | 13.2 → **47.3 kW** | 12.4 → 38.6 kW |
| RAPS power tick | 20 s | **10 s** | 20 s |
| FMU size / variables | 11.6 MB / 66 k | 47 MB / 343 k | 12.5 MB / 73 k |
| FMU + RAPS cost **[F, docs]** | ~2 min per simulated day | **~85 min per simulated day** | ~2 min per simulated day |
| Prior characterization in this repo | **8 experiments, backend verified** | None | None |
| Topology (CDU per rack) | 1 | 1 | 1 |
| Real telemetry available | LAST job traces (not local) | **Cabinet thermal telemetry** (`models/POWER9CSM/data/summit/`) | PM100 job/power traces (not local) |
| Surrogate status | None | Not runnable | Fails |
| Known FMU caveats | Snapshot drift −0.9 °C/h | Cost; unknown behaviour | **Non-physical above ~300 K ambient** (surrogate docs). This endangers the 308 K room-air what-if. |
| Visual layout | 44 racks: easy 4×11 grid | 257 racks: dense but impressive at scale | 49 racks: 7×7 |

**Ranking:**
1. **Leading: Lassen.** Cheapest, fully characterized, backend verified, all plan code targets it. Its weakness is a moderate peak rack power, which may produce a weak hotspot signal.
2. **Backup: Summit.** About 37 % higher peak rack power (47 kW against 34 kW) makes a stronger hotspot contrast plausible, and it is ExaDigiT's flagship model with real cabinet telemetry. Costs: about 40× runtime per simulated hour, a 10 s tick, and 257-rack visuals.
3. **Third: Marconi100.** Physically close to Lassen, so it adds little, and it carries the ambient-instability risk for the what-if.

The surrogate does not change this ranking.

**Decision gate (pre-registered):** run **G2 (packed vs spread)** on all three FMUs on Day 1. Lassen stays primary if its G2 decision is **GO**. If Lassen is WEAK or STOP and another FMU is GO, switch the primary system to that FMU, provided its 6 h closed-loop run costs ≤ 30 min of wall time. Report all three results either way; the cross-system table is itself a demo asset ("the effect holds across ExaDigiT twins").

---

## 7. Should the master plan change?

**Yes, through targeted amendments rather than a rewrite.** On approval I will apply:

| # | Amendment | Tasks |
|---|---|---|
| A1 | Run `uv lock` and commit `uv.lock`; add `runs/` to `.gitignore`; create the experiment hierarchy (§9) with README templates | 1 |
| A2 | **Fix the power-tick definition** (`current_timestep % time_delta == 0`); add the invariant "FMU steps = horizon/Δ" | 4, 8 |
| A3 | Replace the timeout-kill test with an "overrun raises" test; generators enforce `time_limit ≥ expected_run_time` | 4, 7, 12 |
| A4 | Make code system-generic: system name in config; `time_delta` taken from `POWER_UPDATE_FREQ`; FMU path per system; geometry and grid derived from config; probes take `--system` | 2–4, 8, 10, 14 |
| A5 | **New Task 3b: cross-FMU G2 screen** (Summit, Marconi100), FMU-only, with the §6 decision rule. **CHECKPOINT C1** includes the FMU selection decision. | new |
| A6 | Move artifact outputs from `artifacts/probes` and `artifacts/runs` to `experiments/<system>/<EID>/…` (§9). Existing `artifacts/diagnostics` stay where they are and are indexed from `experiments/lassen/E00_legacy_task15/README.md`. | 3, 8, 11, 13, 15 |
| A7 | Surrogate: **no tasks**. Add a limitations and future-work entry. Explicitly forbid using `hpc-cooling-surrogate` for reported results. | 16 |
| A8 | *Optional, after C3 only:* a calibrated RC dev backend (from G1) for Mac-side development and visualization, labelled non-reportable | optional |

The schedule impact is about +0.5 day on Day 1 (Task 3b). That is acceptable because it de-risks system selection before any scheduler code exists.

## 8. Should the Sol prompts change?

**Yes:**
- Add this document to the reading list.
- First assignment becomes Tasks 1, 2, 3 and **3b** (cross-FMU screen) → C1, including the FMU selection decision.
- Explicit warnings:
  - the power-tick pitfall;
  - RAPS raises on time-limit overrun;
  - `output: "none"`;
  - **do not use** `hpc-cooling-surrogate` or `--cooling-model surrogate`.
- Add the experiment-hierarchy and README rules (§9).
- Note that `hpc-cooling-surrogate/` may be empty on Arch, which is expected and harmless.

**If Sol has already started:** Task 1 and Task 2 are unaffected apart from the `uv lock` step. Hold Task 3 until the amended plan is pushed, so that outputs land in the new experiment hierarchy.

## 9. Recommended architecture after considering the surrogate

Unchanged in principle:
- RAPS (cooling off) feeds the adapter, which owns the thermal backend.
- `PlacementScheduler`, ledgers and metrics as planned.

Additions:
- **`ThermalBackend` remains the single pluggable seam.** Its implementations would be:
  - `FmuBackend`: the only source of reported results;
  - *future* `SurrogateBackend` (TorchScript bundle);
  - *optional* `RcDevBackend`.
  
  Backend identity and hash are recorded in every manifest. **Outputs from different backends are never mixed within a comparison.**
- **System-generic configuration:** `system: lassen|summit|marconi100` selects the RAPS config, geometry, power tick, FMU path and SHA, and visual grid.
- **Arch↔Mac contract:**
  - Arch produces `experiments/**` artifacts (parquet, JSON, PNG, GIF, viz bundles).
  - The Mac pulls via git and only renders, analyses and reviews.
  - No FMU or RAPS execution is required on the Mac.

## 10. Recommended experiment structure

Artifacts live at `thermoRL/thermorl-v2/experiments/`. The code stays in `thermorl2/experiments/`.

```
experiments/
  INDEX.md                         registry: ID | system | question | status | decision | link (updated by Sol after every experiment)
  _templates/EXPERIMENT_README.md
  lassen/
    SYSTEM.md                      system card: FMU sha, RAPS config, idle/peak kW, tick, topology, known caveats
    E00_legacy_task15/README.md    index of existing artifacts/diagnostics (A–H), key findings, not moved
    E01_g1_uniform/
    E02_g2_packed_vs_spread/
    E03_g3_room_air/
    E10_c2_vertical_slice/
    E11_g4_synthetic/
    E12_g4_alibaba/
    E13_g5_whatif_room_air/
  summit/
    SYSTEM.md
    E02_g2_packed_vs_spread/
  marconi100/
    SYSTEM.md
    E02_g2_packed_vs_spread/
  cross_system/
    X01_g2_screen/                 comparison table + FMU selection decision
```

**Each experiment directory is self-contained:**

```
E0x_<slug>/
  README.md          sections: ID & status · Question · Pre-registered decision rule (with date) ·
                     Configuration (link) · Method (exact commands) · Metrics · Results table ·
                     Plots · Observations (FACT) · Interpretation (INFERENCE) · Conclusion & decision ·
                     Limitations · Provenance (git SHA, FMU SHA, workload SHA, backend) · Demo relevance
  config.yaml        exact inputs (frozen before the run)
  results/           summary.json, metrics.csv, series.parquet/csv
  plots/             *.png, *.gif
  provenance/        manifest.json (+ rerun verification)
  runs/<policy>_seed<s>/   (closed-loop experiments only: decisions.jsonl, intervals.parquet, manifest.json)
```

**Rules:**
- Experiment IDs are immutable.
- Reruns create a new `runs/` entry or a `provenance/rerun_*.json`. Nothing is overwritten.
- Pre-registered rules are written into the README **before** the run, and the commit that contains them precedes the results commit.
- Demo preparation and analysis cite experiment READMEs, not memory.

---

## 11. Updated risk assessment

| # | Risk | Change | Likelihood / impact | Mitigation |
|---|---|---|---|---|
| R1 | FMU runtime platform | Unchanged; resolved by Arch | Low / high | Arch for all FMU work |
| R2 | Null result against power balance | Unchanged | High / medium | Ladder; what-if; honest framing |
| R3 | Process stalls | Unchanged | Medium / high | Demo-mode gates |
| R4 | Runtime cost | **Lower for Lassen and Marconi100** (~2 min/day); **high for Summit** (~85 min/day) | Low / medium | Lassen primary; Summit screen only unless it wins C1 |
| R5 | **Plan bug: FMU stepped 20× too often** | **New, now caught** | Would have been high / high | A2 plus the step-count invariant |
| R6 | **RAPS raises on time-limit overrun** | **New, now caught** | Medium / medium | A3 |
| R7 | **Empty `hpc-cooling-surrogate` on Arch; nested `.git` directories in `sim-raps/` and `exadigit-documentation/`** | New | Medium / low | Fix the gitlink (decision G0); not needed for the FMU path |
| R8 | **Scope creep into surrogate training** | New | Medium / high | Option B; forbidden this week |
| R9 | `uv.lock` drift dirties the tree | New | High / low | A1 |
| R10 | Marconi100 ambient instability | New | Medium / medium for the what-if | Use the what-if only on Lassen or Summit |
| R11 | Summit 257-rack visuals become cluttered | New | Medium / low | 2D heatmaps scale; 3D replay stays Lassen-first |

## 12. Decision gates before implementation proceeds

| Gate | When | Decision | Owner |
|---|---|---|---|
| **G0 — Freeze and hygiene** | Before Sol continues past Task 2 | (a) Approve amendments A1–A7. (b) Fix the `hpc-cooling-surrogate` gitlink: add a proper submodule with URL, or remove the gitlink and keep it as a local-only clone. (c) Nested `.git` in `sim-raps/` and `exadigit-documentation/`: keep as untracked nested repos, but document that the parent repo tracks their files; or move them out. (d) Optionally email ORNL (Wes Brewer) for Summit or Frontier surrogate bundles. Non-blocking. | Bipin → Claude applies |
| **G1 — Physics and FMU selection (C1)** | End of Day 1 | Lassen G1/G2/G3 and Summit/Marconi100 G2 → primary FMU frozen; hotspot story GO/WEAK/STOP; what-if lever usable or not | Claude reviews → Bipin approves |
| **G2 — Closed-loop validity (C2)** | Day 2 | Invariants hold (identical IT kW, exact nodes, FMU step count, determinism) → proceed to the comparison matrix | Claude reviews |
| **G3 — Conservative demo (C3)** | Day 3 | Pre-registered G4 outcome recorded. Decide Alibaba plus visualization next, and whether a second-system panel is worth its cost. | Claude → Bipin |
| **G4 — Surrogate revisit** | After C3 or post-demo | Only if ORNL supplies a bundle, or the demo is complete with time to spare | Bipin |
