# C6 — Final packaging review; raw backup pending destination

**Date:** 2026-10-31. **Branch:** feat/parasparam-demo. **Status:** packaging documents, labelled assets and D7(b) complete; **STOP for final review and the required backup destination**. Off-machine raw preservation is not complete and no unqualified “demo-ready” claim is made. Both frozen G4 outcomes remain **no material value on the homogeneous twin; value_beyond_power=false**.

## Commits

Reviewed starting point: `bd5dedc`, containing the Opus C4 review of `b96a43b`. The first work commit records Bipin's decisions verbatim. The checkpoint/plan/final-checks commit is the commit containing this document.

| SHA | Deliverable |
|---|---|
| `ce9d91220f12bf24509d20ec940427636b529f25` | docs(plan): approved post-C4 decisions |
| `202b9ec5a059ff620c7e6ce9f7b29a79b6539a0a` | docs(checkpoint): C5 what-if not run |
| `1678d0a3ed6ff35abebf1b44081e6c9860cab6db` | docs(experiments): clarify accepted C4 status without changing frozen records |
| `06032b45ee650e235d5b2b69a5eb5d012a2732e8` | feat(demo): add labelled presentation renderer for existing ledgers |
| `35916c52ec89d3c48723d2955683e973da49cdee` | artifacts(demo): labelled E11 and E12 figures with negative-G4 captions |
| `878cca050ea705031dd4f0cace4cfaca2996285a` | docs(results): ParasParam results note, runbook and demo asset map |
| `9abeb118ddfc6b2f55efc305fb6878bff8af789c` | docs(repro): record successful same-Arch fresh clone and single Summit smoke |

## Deliverables and acceptance conditions

- [Approved post-C4 decisions](../superpowers/plans/2026-10-27-parasparam-demo.md#approved-post-c4-decisions-2026-10-31): C4 acceptance, explicit recovery ratification, D7(b), deferred replay and frozen science.
- [C5 non-execution note](C5-whatif.md): G3 NOT_USABLE; G5/E13 not run; 62 candidates, none applied; no alternative lever.
- [Results note](../results/2026-11-parasparam-demo-results.md): measured cross-FMU/G1/G3/G4 results, exact E12 ordering, metric-specific S1, scopes/limitations, SHA appendix and verbatim claims table.
- [Runbook](../results/runbook.md) and [v2 README entry](../../thermoRL/thermorl-v2/README.md#reproduce-the-demo): executed history versus future reproduction, frozen inputs, durable services, memory scopes and actual D7 setup lesson.
- [DEMO.md](../../thermoRL/thermorl-v2/experiments/DEMO.md): every asset maps to an allowed claim and a “must not be used for” claim; separate E11/E12 ranges and a short negative-result narrative.
- [Presentation-only renderer](../../thermoRL/thermorl-v2/thermorl2/experiments/demo_assets.py) and [fixture tests](../../thermoRL/thermorl-v2/tests/unit/test_demo_assets.py).
- [D7 full record](../results/d7_fresh_clone_check.json), [failed setup](../results/d7_setup_attempt1.json), [scratch cleanup](../results/d7_failed_clone_cleanup.json), [service records](../results/d7_service_records.json).
- [Asset verification](../results/demo_asset_verification.json), [render runtime](../results/demo_render_runtime.json), [render service](../results/demo_render_service.json).
- [Frozen-section check](../results/frozen_packaging_verification.json), [protected source/raw preservation](../results/packaging_source_verification.json), [final scope/content checks](../results/final_packaging_checks.json).
- [Raw backup record](../results/raw_backup_record.json): explicitly **pending_destination**, no copy performed.

C4 conditions C1–C3 are addressed: ratification is dated and verbatim; the E12 ordering is quoted exactly with correlation/materiality caveats and E11-only packing≈TP wording; all eight new demo assets carry the requested labels/captions. `C4-execution-stop.md`, `C4-execution-recovery.md` and their SHA-pinned approval are preserved unchanged.

## D7(b): measured outcome and limits

Fresh on-disk clone **`06032b45ee650e235d5b2b69a5eb5d012a2732e8`**, same Arch host; Python 3.12.14, NumPy 2.5.3, FMPy 0.3.32, uv 0.13.0. RAPS imported from the clone's own editable `sim-raps` path. `uv sync --frozen` passed; **196 unit/integration tests passed in 39.99 s**; all **22 pinned hashes** passed (Summit FMU, primary.yaml, G1, E11/E12 config copies/launch configs, workloads/sidecars and other preregistered input records). The tracked clone stayed clean.

Exactly **one** FMU execution occurred in this phase:

```json
{
  "finite": true,
  "fmu_sha256": "0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233",
  "idle_kw": 13.201714285714285,
  "n_units": 257,
  "peak_kw": 47.282326530612245,
  "system": "summit",
  "t_c_max": 37.54036906294215,
  "t_c_min": 37.5403672951083,
  "wall_s": 67.98363489600024,
  "warmup_used_s": 600.0
}
```

The smoke used a 600 s capped warm-up on 257 units. Its command-process wall was **69.599887s**; `wall_s` inside the JSON measures the smoke function, not interpreter startup. No policy run, matrix, report CLI, full FMU pytest tier or E11/E12 repeat was executed. The local targeted renderer/plot fixture tests also passed: **12 passed in 7.98 s** (including 7 new asset cases).

This clone tested the final code candidate; later commits add only documents/assets/records and plan/index status. It is same-machine evidence, not cross-machine portability, universal matrix repetition or a replacement for the historical E10/E11/E12 repeat scopes. The successful clone remains outside the working repo at `/home/bipin/thermorl-freshclone-20261031-disk`.

## New labelled assets

| Experiment | Assets | Total bytes | Common seed 1 colour scale | First 3 TP distinct counts | Renderer wall | Own peak RSS |
|---|---:|---:|---|---|---:|---:|
| E11 | 4 | 35236628 | 39.252402–56.233641 °C | [1, 3, 3] | 196.695937 s | 2.073910 GiB |
| E12 | 4 | 43080555 | 38.702230–42.413286 °C | [1, 1, 1] | 218.146841 s | 2.456234 GiB |

Every PNG/GIF was checked for hash/size and required metadata; all are below 25 MB. Static images and representative first/evaluation/last GIF frames were inspected for the required in-image experiment/workload/system/seed labels, E12 correlation caveat, evaluation marker/state, scale range/note and exact descriptive negative-G4 caption. Inventories: [E11](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/provenance/demo_asset_inventory.json), [E12](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/demo_asset_inventory.json). Originals were never overwritten.

**FACT:** E11's first-three TP logged temperature rows have distinct counts [1,3,3], so its early-frame caption is neutral. E12 counts [1,1,1], so it uses “tie-breaking among thermally identical idle racks; not a thermal decision”. These checks are per-row six-decimal logging checks, not proof of full-precision equality or a physical mechanism. Their exclusive check records were written before rendering.

## Preservation, scope and open items

**FACT:** post-render checks re-hashed **1204 protected original files** and **230 raw inventory entries** with no mismatch. E11/E12 frozen README sections remain byte/hash-identical; original results/plots, policies, core, thermal, adapter, RAPS, models, configs and cached workloads are unchanged. Recovery approval's pinned document SHA still passes. The non-frozen E12 header/status block is the explicitly authorized documentation change; its older non-raw artifact-inventory hash remains a historical snapshot, with old/new identities recorded separately. No historical inventory was rewritten.

**FACT — setup finding:** the first setup controller exited 143 before output collection; its clean clone/connectivity were verified before continuation. Frozen setup in `/tmp` later failed with “Disk quota exceeded” copying the locked Torch library, before any tests or smoke. Both failures are preserved. Only the failed scratch clone was removed; an on-disk home-directory clone then passed using the unchanged lock. No dependency/test/input patch or data copy was used to force success. The runbook now recommends on-disk scratch space. **UNRESOLVED:** the first setup controller's SIGTERM origin. This is separate from the original E12 interruption, which is now **Bipin-reported memory pressure**; the original-period journal query found no corroborating entries.

**Open — backup:** no external disk/rsync destination has been supplied. Therefore copied_files=0, copied_bytes=0, destination verification and post-copy source-sample verification are **not performed**. The prepared record references the 230 expected inventory entries and interruption/relocation inventory SHAs. The temporary clone is not a raw-data backup. Bipin must provide the destination before read-only copy, exhaustive destination hash verification and source recheck can complete. The optional upstream dataset is not included or copied.

Task 15 remains deferred. Task 16 is closed without execution. Task 17's documents/assets and approved D7(b) steps are checked; its added raw-backup condition remains unchecked. Unrelated local deletions remain outside all commits; docs/prompt.md was never staged; no branch/PR or new scientific experiment was created.

**STOP at C6 for final review. Required input: the external disk directory or rsync target for raw-data backup.** No next research/replay task is authorized.
