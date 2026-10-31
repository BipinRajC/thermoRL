# Reproduce the ParasParam demo

> **Post-rename update (2026-10-31).** Paths in this living runbook now use `thermoRL/backend` (formerly `thermoRL/thermorl-v2`) and `thermoRL/frontend` (formerly `thermoRL/thermoRL-new`). Checkpoints, manifests, inventories and other historical records keep the paths they recorded; see [path mapping](path_mapping.md). The raw-data backup was waived by Bipin; see the packaging section.

This runbook separates **historically executed commands** from **future reproduction commands**. The scientific commands below were **not re-executed in the post-C4 packaging phase**. The only newly authorized FMU execution is the D7(b) Summit smoke. Offline labelled rendering reads existing ledgers and executes no policy or FMU. Current results and limitations are in the [results note](2026-11-parasparam-demo-results.md); presentation assets and claims are mapped in [DEMO.md](../../thermoRL/backend/experiments/DEMO.md).

Use Arch Linux x86-64 for FMU execution. The FMUs ship Linux/Windows binaries, not macOS binaries. On the Mac, present pre-rendered figures/GIFs; a live simulation requires Arch. All commands below, unless explicitly marked otherwise, run from the backend directory `thermoRL/backend` (named `thermoRL/thermorl-v2` before rename `c09f735`; historical records keep that name, see [path mapping](path_mapping.md)) with the locked Python 3.12 environment.

## Executed — historical scientific record

All these scientific runs happened on the Arch machine with Python 3.12.14, FMPy 0.3.32, NumPy 2.5.3 and uv 0.13.0. Source SHA and input identities are recorded per manifest; dirty flags from unrelated user files/artifact writes were preserved. No historical timing below is a fresh-clone measurement.

| Stage | Executed source / anchor | Measured wall scope | Wall seconds | Source |
|---|---|---|---:|---|
| Lassen G2 original | `41c6585` | manifest `timings.total_s`, complete probe | 18.217528 | [manifest](../../thermoRL/backend/experiments/lassen/E02_g2_packed_vs_spread/provenance/manifest.json) |
| Summit G2 original | `41c6585` | same; G2 probes co-scheduled as separate processes | 1172.611832 | [manifest](../../thermoRL/backend/experiments/summit/E02_g2_packed_vs_spread/provenance/manifest.json) |
| Marconi100 G2 original | `41c6585` | same | 22.922057 | [manifest](../../thermoRL/backend/experiments/marconi100/E02_g2_packed_vs_spread/provenance/manifest.json) |
| X01 selection | G2 result commit `2d14161` | offline mechanical selection; separate wall not recorded | not recorded | [selection](../../thermoRL/backend/experiments/cross_system/X01_fmu_selection/results/summary.json) |
| Summit G1 / G3 | `6f88579` | manifest complete probes, run as separate parallel processes | 1792.660297 / 1201.512795 | [C1 timings](../checkpoints/C1-fmu-selection-and-physics.md#wall-times-measured-seconds) |
| Six-hour idle bench | implementation `7695c34`; result `2a2616f` | isolated process launch through exit, imports/warm-up included | 912.539314 | [C2 bench](../checkpoints/C2-vertical-slice.md#task-5-bench-d1-and-d2) |
| E10 packing / PB / packing repeat | `0c32cf5` | EpisodeRunner totals, excluding interpreter imports | 540.665581 / 484.213451 / 538.399463 | [C2](../checkpoints/C2-vertical-slice.md) |
| E11 15-run matrix | `6ee93c4` | three-worker controller `matrix_wall_s`, no retries | 4746.698387 | [runtime](../../thermoRL/backend/experiments/summit/E11_g4_synthetic/results/matrix_runtime.json) |
| E12 recovery controller | `e0e1522` | controller execution after skip validation, 11 completions | 5033.356971 | [runtime](../../thermoRL/backend/experiments/summit/E12_g4_alibaba/results/matrix_runtime.json) |
| E12 complete primary span | original `18dfea1`, recovery `e0e1522` | first original primary start to last primary completion, **including interruption/recovery downtime** | 9565.744325 | same |
| E12 TP seed1 repeat | `e0e1522` | guarded subprocess plus validation | 1479.362241 | [repeat journal](../../thermoRL/backend/experiments/summit/E12_g4_alibaba/provenance/rerun_1/journal.jsonl) |
| E12 final offline report | frozen recovery code | main after imports, validation/metrics/rendering included | 458.675731 | [report runtime](../../thermoRL/backend/experiments/summit/E12_g4_alibaba/provenance/report_runtime.json) |

Earlier per-process memory was not uniformly recorded. Do not infer G2/G1/G3/E10/E11 memory from later E12 measurements. E12 selected simulation own-process peak RSS was **1.63–1.99 GiB**; recovery parent own peak **1.356 GiB**; primary service cgroup high-water **6.925 GiB** includes controller and simultaneous workers. Report own-process high-water was **4.979 GiB**. Follow-up cgroup peak **5.974 GiB** spans the repeat, comparison and report. RSS, cgroup memory and total host memory are different scopes; these figures do not guarantee adequate headroom on a busy machine.

### G2, selection, G1 and G3 commands (historical)

```bash
uv run python -m thermorl2.experiments.probes g2 --system lassen --out experiments/lassen/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.probes g2 --system marconi100 --out experiments/marconi100/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.probes g2 --system summit --out experiments/summit/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.probes g2 --system lassen --out experiments/lassen/E02_g2_packed_vs_spread/provenance/rerun_1_data --verify-against experiments/lassen/E02_g2_packed_vs_spread
uv run python -m thermorl2.experiments.select_fmu --out experiments/cross_system/X01_fmu_selection experiments/lassen/E02_g2_packed_vs_spread/results/summary.json experiments/summit/E02_g2_packed_vs_spread/results/summary.json experiments/marconi100/E02_g2_packed_vs_spread/results/summary.json
uv run python -m thermorl2.experiments.probes g1 --system summit --out experiments/summit/E01_g1_uniform
uv run python -m thermorl2.experiments.probes g3 --system summit --out experiments/summit/E03_g3_room_air
uv run python -m thermorl2.experiments.bench --system summit --hours 6
```

X01 uses original G2 costs, not the faster Lassen repeat. G3's weak-lever result did not authorize a substitute scenario. G1 was frozen before the comparisons and was not refit during E11/E12.

### E10, E11 and E12 commands (historical)

E10 production was launched by the historical FMU tier at preregistration SHA `0c32cf5`:

```bash
THERMORL2_E10_ROOT=experiments/summit/E10_c2_vertical_slice uv run pytest tests/fmu -v
```

That historical command launched these separate OS processes; it is **not authorized in this packaging phase**:

```bash
python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --policy packing --seed 1 --run-dir experiments/summit/E10_c2_vertical_slice/runs/packing_seed1
python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --policy power_balance --seed 1 --run-dir experiments/summit/E10_c2_vertical_slice/runs/power_balance_seed1
python -m thermorl2.experiments.run --config thermorl2/experiments/configs/smoke_2h.yaml --policy packing --seed 1 --run-dir experiments/summit/E10_c2_vertical_slice/provenance/rerun_1_packing_seed1
```

E11:

```bash
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_synthetic.yaml --workers 3
uv run python -m thermorl2.experiments.evidence experiments/summit/E11_g4_synthetic
uv run python -m thermorl2.experiments.report experiments/summit/E11_g4_synthetic --evidence experiments/summit/E11_g4_synthetic/provenance/determinism_evidence.json
```

E12 original interactive launch (interrupted), followed later by ratified recovery and the isolated planned repeat:

```bash
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3 --retry-failed
uv run python -m thermorl2.experiments.e12_evidence rerun --config thermorl2/experiments/configs/g4_alibaba.yaml
uv run python -m thermorl2.experiments.e12_evidence generate --config thermorl2/experiments/configs/g4_alibaba.yaml
uv run python -m thermorl2.experiments.report experiments/summit/E12_g4_alibaba --evidence experiments/summit/E12_g4_alibaba/provenance/determinism_evidence.json
```

The recovery matrix ran under `thermorl-e12-recovery-20261030T2050Z.service`; the guarded repeat → evidence → report sequence under `thermorl-e12-postmatrix-20261030T2123Z.service`. Both user units used `RuntimeMaxSec=infinity`, `Restart=no`, `MemoryAccounting=yes`, `RemainAfterExit=yes`, an explicit working directory, and uniquely created console logs. Both exited successfully with zero restarts. Exact argv, settings, service timestamps and sequential commands are preserved under [recovery_1](../../thermoRL/backend/experiments/summit/E12_g4_alibaba/provenance/recovery_1/).

Bipin ratified reuse4 + restart3 once + first-attempt8 + planned repeat1: **19 cumulative attempts**, including three preserved interruptions. Archive journal records were appended by recovery preservation, not observed by the dead controller; child final exit statuses were unknown (`returncode:null`). **Memory pressure is Bipin-reported**; the controller exited SIGTERM143. The read-only journal query had no corroborating entries. The earlier session-lifetime inference is superseded. Approximately **1850 s downtime** is derived as 9565.7 − (approximately 2680 original-active + 5033.4 recovery), using an approximate original termination time. It is not an exact measured field. E11's `matrix_wall_s` is controller wall; E12's same key is explicitly the downtime-inclusive span. Do not compare them as equivalent execution costs.

Mixed-SHA numerical-source equivalence was independently reviewed for E12; the generic report gate does not itself enforce that equivalence for arbitrary future matrices. Preserve the two [C4-execution](../checkpoints/C4-execution-stop.md) [records](../checkpoints/C4-execution-recovery.md): the recovery document is SHA-pinned by `recovery_approval.json` and `reviewed_recovery()`.

## Reproduction — future, not executed in packaging except D7(b)

### Clean-clone setup and pinned inputs

On Arch x86-64, clone the approved branch to a new directory outside the working repository, record its SHA, then use the locked environment:

```bash
git clone --branch feat/parasparam-demo https://github.com/BipinRajC/thermoRL.git "$HOME/thermorl-reproduction-UNIQUE"
cd "$HOME/thermorl-reproduction-UNIQUE/thermoRL/backend"
uv sync --frozen
uv run pytest tests/unit tests/integration -q
```

Use an on-disk scratch directory with adequate space. In D7, `/tmp` was tmpfs and frozen setup failed with “Disk quota exceeded” while copying Torch; the failed record is preserved. RAPS brings substantial locked dependencies, even though this demo does not run RL. Keeping the clone and uv cache on the same filesystem permits hardlinking and avoids the observed cross-filesystem full-copy fallback. Do not change the lock or omit dependencies to make setup pass.

The editable `sim-raps` dependency resolves within this clone. Do not run unqualified pytest: it includes FMU tests. A same-machine clone/test/smoke establishes only that narrow portability check, not portability across machines or platforms.

Obtain the separately distributed raw dataset only when required by an authorized reproduction; its default CSV SHA and all 26 checksums are committed. From the raw dataset root:

```bash
sha256sum -c checksums.txt
```

E11/E12 workload Parquet files and sidecars are already SHA-pinned and committed. **Never regenerate them**, change scaling or substitute a trace. Verify the FMU, primary.yaml, G1 summary, config copies and all workload/sidecar hashes against each committed preregistration; Appendix A of the [results note](2026-11-parasparam-demo-results.md) gives the principal values. D7 must not copy a missing ignored dataset merely to make a test pass; record such a portability finding instead.

### Scientific reproduction order — requires separate authorization

Order: **FMU smoke → three-system G2 and X01 → G1/G3 → policy matrices → scoped evidence and reports.** These expensive commands were not repeated in packaging. G3 does not authorize G5/E13. No E11/E12 rerun is part of D7(b).

Use the historical commands above only in separately authorized disposable checkouts of the recorded frozen launch SHAs with absent output targets. Current completed experiment directories deliberately refuse overwrite. For probes, new `--out` directories keep original results intact. For matrices, a clean pre-results source snapshot supplies the original experiment root/config; do not delete published outputs to force a rerun, edit configs to bypass identity checks, or feed a fresh G1 refit into the frozen comparisons. Any new evidence remains separate and cannot silently replace accepted results.

Plan for approximately 2 GiB per simulation worker, three workers maximum, primary cgroup peak approximately 6.9 GiB, and report approximately 5 GiB own RSS. Leave additional host memory headroom, including other applications and rendering transients. The original memory-pressure interruption means matching a measured worker count is not itself a resource guarantee. Summit's measured idle bench was 15.2 min per 6 h process; E11 matrix 79.1 min; E12 recovery controller 83.9 min, plus historical active work/downtime and 24.7 min guarded repeat. These are machine/workload-specific observations, not runtime promises.

For any separately authorized matrix, prefer a durable user service with a unique name/log, explicit cwd, no runtime deadline and **no automatic restart**:

```bash
# Future template only; replace UNIQUE and /ABS/NEW-CONSOLE.log before use.
systemd-run --user --unit=thermorl-matrix-UNIQUE --service-type=exec \
  --property=WorkingDirectory=/ABS/CLONE/thermoRL/backend \
  --property=RuntimeMaxSec=infinity --property=Restart=no \
  --property=MemoryAccounting=yes --property=RemainAfterExit=yes \
  --property=StandardOutput=append:/ABS/NEW-CONSOLE.log --property=StandardError=inherit \
  /usr/bin/uv run python -m thermorl2.experiments.run_matrix \
  --config thermorl2/experiments/configs/g4_synthetic.yaml --workers 3
```

Create the new log exclusively first, inspect unit memory/status and worker journals, and preserve any failure. Never reuse the old E12 recovery authorization for a new failure or enable automatic retries.

### D7(b) — the only fresh scientific execution authorized here

The D7 clone follows exactly `uv sync --frozen`, the bounded non-FMU tier, committed input/FMU hash verification and **one** process:

```bash
uv run python -m thermorl2.experiments.fmu_smoke --system summit
```

This uses the existing short 600 s capped smoke, not a policy episode. No `tests/fmu`, unqualified pytest, `run.py`, `run_matrix.py`, report invocation or matrix is allowed in D7. [d7_fresh_clone_check.json](d7_fresh_clone_check.json) records the actual cloned SHA, environment, exact commands, outputs/counts, hashes and smoke JSON. Failures other than documented missing ignored inputs stop; a smoke failure/non-finite result stops with no retry.

## Packaging, presentation and raw-data preservation

The new presentation-only commands read the completed raw ledgers and write unique `plots/demo/` outputs with checks/inventories under each experiment's provenance:

```bash
uv run python -m thermorl2.experiments.demo_assets experiments/summit/E11_g4_synthetic
uv run python -m thermorl2.experiments.demo_assets experiments/summit/E12_g4_alibaba
```

They are offline rendering commands, not the frozen report or a simulation. They refuse an existing destination/check/inventory. The originals remain immutable. E11 and E12 temperature scales differ; keep the printed labels, evaluation marker and negative-G4 caption visible.

Ignored raw data is not supplied by git. **Backup waived by Bipin on 2026-10-31** ("yes lets skip the backup thing"; plan addendum and [backup record](raw_backup_record.json), `status: skipped_by_user`). No off-machine copy exists: the raw ledgers remain local on the Arch disk, and no disaster-recovery guarantee is claimed. If a backup is ever made, copy with `rsync -a` or an equivalent read-only source operation, never delete into the source, and verify every copied file against the E11/E12 primary, repeat and interruption/relocation inventories.

## D7 measured outcome in this phase

The successful on-disk clone at `/home/bipin/thermorl-freshclone-20261031-disk` contains code candidate `06032b45ee650e235d5b2b69a5eb5d012a2732e8`. Frozen setup passed; 196 tests passed in 39.99 s; all 22 pinned hashes passed; exactly one Summit smoke was finite (257 units, 600 s capped warm-up; 67.984 s inside the smoke). Its complete command wall times are in the JSON record. The clone remains outside the working repository; packaging commits up to `b3bd5ac` changed only documents/assets/records. **D7 does not cover current HEAD:** the rename `c09f735` and the later relocation-only path fixes (workload root and application source map; see [path mapping](path_mapping.md)) post-date it and need their own post-rename acceptance (fresh on-disk clone, `uv sync --frozen`, non-FMU tier).

The initial interactive setup controller exited143 before output collection. Its clean clone was verified with Git status/connectivity checks; subsequent frozen setup in `/tmp` then failed on quota copying Torch. That failed setup record is preserved as [d7_setup_attempt1.json](d7_setup_attempt1.json); no tests or smoke had run. Only the failed scratch clone was removed to reclaim tmpfs, as recorded in [cleanup](d7_failed_clone_cleanup.json). A new on-disk clone used the unchanged lock and completed the check. These are environment/setup attempts, not extra FMU runs or policy experiments.
