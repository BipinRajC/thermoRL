# Experiment Directory Conventions — ParasParam Demo (FINAL, 2026-10-27)

Every experiment for the demo leaves a self-contained, reviewable record. Later analysis and demo preparation must rely on these artifacts, not on memory or chat history.

## 1. Location and layout

- **Artifacts** live in `thermoRL/thermorl-v2/experiments/`, which is a plain directory, not a Python package.
- **Code** lives in `thermoRL/thermorl-v2/thermorl2/experiments/`.

```
thermoRL/thermorl-v2/experiments/
  INDEX.md                          registry of every experiment (one row each; updated after every experiment)
  _templates/
    EXPERIMENT_README.md            copy for every new experiment
    SYSTEM.md                       copy for every system
  lassen/
    SYSTEM.md
    E00_legacy_task15/README.md     index of thermoRL/thermorl-v2/artifacts/diagnostics/* (A–H), not moved
    E02_g2_packed_vs_spread/
  summit/
    SYSTEM.md
    E02_g2_packed_vs_spread/
  marconi100/
    SYSTEM.md
    E02_g2_packed_vs_spread/
  cross_system/
    X01_fmu_selection/              G2 comparison table + mechanical selection decision
  <primary>/                        (whichever system X01 selects)
    E01_g1_uniform/
    E03_g3_room_air/
    E10_c2_vertical_slice/
    E11_g4_synthetic/
    E12_g4_alibaba/
    E13_g5_whatif_room_air/         (only if G3 is USABLE)
```

## 2. Experiment IDs

| Prefix | Meaning |
|---|---|
| `E0x` | FMU-only physics probes on one system |
| `E1x` | Closed-loop (RAPS + FMU) experiments on one system |
| `X0x` | Cross-system analyses and decisions |

- **IDs are immutable.**
  - A changed protocol gets a **new ID**, for example `E11b_…`.
  - The new README explains the change and links the old one.
- **Slugs** are lower_snake_case.

## 3. Contents of every experiment directory

```
<EID>_<slug>/
  README.md        required; sections below
  config.yaml      exact inputs, frozen before the run (copy of / pointer to the code config + overrides)
  results/         summary.json (machine-readable decisions + key numbers), metrics.csv, series.csv|parquet
  plots/           *.png, *.gif, *.mp4
  provenance/      manifest.json; rerun_<n>.json (determinism checks); environment.txt (uv/python/fmpy versions)
  runs/            closed-loop only: <policy>_seed<s>/{decisions.jsonl, intervals.parquet, manifest.json}
```

## 4. README.md template (`_templates/EXPERIMENT_README.md`)

```markdown
# <EID> — <title>
**System:** <lassen|summit|marconi100|cross_system>  **Status:** planned | running | complete | superseded by <EID>
**Pre-registered:** <date, commit SHA of the commit that added this README's Question + Decision rule>

## Question
## Pre-registered decision rule        (copied verbatim from spec §4; written BEFORE results)
## Configuration                        (link config.yaml; list key values)
## Method                               (exact commands, in order; expected wall time)
## Metrics                              (definitions, windows, units)
## Results                              (table of key numbers; link results/summary.json)
## Plots                                (embedded links to plots/*)
## Observations (FACT)                  (what was measured, no interpretation)
## Interpretation (INFERENCE)
## Conclusion and decision              (rule outcome, e.g. GO/WEAK/STOP, USABLE/NOT_USABLE, value_beyond_power true/false)
## Limitations
## Provenance                           (git SHA + dirty flag, FMU SHA-256, workload SHA-256, backend=fmu, seeds, rerun verification)
## Demo relevance                       (which claim/visual this supports)
```

## 5. SYSTEM.md template (`_templates/SYSTEM.md`)

A `SYSTEM.md` records the following:
- system name;
- FMU path and SHA-256;
- RAPS config path;
- topology (racks/CDUs, nodes per rack, GPUs per node);
- power tick Δ;
- measured idle and peak rack kW (from `rack_power_bounds`);
- schematic grid;
- what-if racks;
- FMU-only cost per simulated hour (filled in by G2);
- known caveats;
- links to all of this system's experiments.

## 6. INDEX.md

`INDEX.md` has one row per experiment:

`| EID | system | question (one line) | status | decision | key number | README link | date |`

Sol updates it at the end of every experiment, in the same commit as the results.

## 7. Rules

1. **Pre-register first.** Commit the README sections Question, Pre-registered decision rule, Configuration and Method before running. The results commit must follow that commit.
2. **Never overwrite.** Reruns go into `provenance/rerun_<n>.json` (determinism) or a new `runs/` subdirectory. A protocol change gets a new EID.
3. **Machine-readable decisions.** `results/summary.json` must contain:
   - the decision field(s) named in the rule;
   - the numbers the rule used.
4. **Size.** Commit run directories smaller than 25 MB each. Anything larger is gitignored and listed in the README with its path and SHA-256.
5. **Backend.** Every manifest records `backend: fmu`. Results from other backends must never sit in these directories.
6. **Labels.** The README states which statements are FACT and which are INFERENCE. What-if experiments carry the scenario's label text in the title and in every plot title.
7. **Checkpoints.** `docs/checkpoints/C<n>-<slug>.md` summarises the experiments a checkpoint covers and links their READMEs. It does not duplicate their contents.
