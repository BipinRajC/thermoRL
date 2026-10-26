# Repository Notes (2026-10-27)

These notes explain how the workspace is laid out. They hold until after the ParasParam demo; **no restructuring is planned before then**.

## Nested `.git` folders (kept as-is)

| Path | What it is | How the parent repo treats it |
|---|---|---|
| `sim-raps/.git` | A local clone of upstream ExaDigiT RAPS, updated 2026-10-27 (`39a7fa6` in the parent repo) | The parent repo tracks `sim-raps/` **as plain files**. The nested `.git` is not tracked; it exists only so `git -C sim-raps …` can compare against upstream. |
| `exadigit-documentation/.git` | A local clone of the ExaDigiT documentation repo, updated in parent commit `2295f17` | Same arrangement: plain files are tracked and the nested `.git` is not. |

**Rules**
- **Do not edit `sim-raps/`** (RAPS) for the demo.
- `git -C sim-raps …` operates on the **upstream** clone, not on the ThermoRL repo. Run ThermoRL git commands from the repo root.
- On machines that pull the ThermoRL repo (for example Arch), these directories arrive as plain files with no nested `.git`. That is expected.

## `hpc-cooling-surrogate/` (local reference clone only)

- **What it is:** ExaDigiT's ML surrogate research code (`https://github.com/ExaDigiT/hpc-cooling-surrogate`).
  - It contains **no trained weights**.
  - It predicts CDU summary outputs only.
  - The full assessment is in `docs/2026-10-27-surrogate-and-fmu-selection-assessment.md`.
- **Git status:** removed from the ThermoRL repo (it was a bare gitlink with no `.gitmodules`) and listed in `.gitignore`. It is a local clone on the Mac only.
- **Role:** future-work reference. It is **not** a ParasParam dependency and is **not** used for any reported result.
  - Do not use `--cooling-model surrogate` in RAPS.
  - On Arch this directory is absent. That is expected.

## Machines

| Machine | Role |
|---|---|
| **Arch Linux x86-64** | All FMU and RAPS execution: probes, closed-loop runs, matrices. Sol 6.1 runs here. |
| **Mac M4 Pro** | Planning, review, analysis, visualisation of committed artifacts. The FMUs cannot run on macOS: there is no darwin64 binary. |
| **Sync** | Through git (`origin`). Sol pushes `feat/parasparam-demo` at every checkpoint. |

## Other notes

- Raw Alibaba data at `datasets/` is gitignored. Copy it to the same path on Arch, and check it with `datasets/alibaba_gpu_2023/checksums.txt`.
- RAPS writes `./runs/` when `output` is unset. The demo code always passes `output: "none"`, and `runs/` is gitignored.
- `docs/prompt.md` is Bipin's working file. Agents must not modify it.
