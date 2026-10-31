# Path mapping after the backend/frontend rename

**Date:** 2026-10-31. **Rename commit:** `c09f735` ("renamed to backend and frontend"). All 596 moves were byte-identical (`git diff -M` reports `R100`).

| Before `c09f735` (historical records) | Current path |
|---|---|
| `thermoRL/thermorl-v2/` | `thermoRL/backend/` |
| `thermoRL/thermorl-v2/thermorl2/` | `thermoRL/backend/thermorl2/` |
| `thermoRL/thermorl-v2/experiments/` | `thermoRL/backend/experiments/` |
| `thermoRL/thermoRL-new/` | `thermoRL/frontend/` |
| `thermoRL/thermoRL-new/viz/` | `thermoRL/frontend/viz/` |

## Rules
- **Historical records keep their recorded paths:** checkpoints C1–C6, reviews, handoffs, experiment manifests, inventories, `source_sha256` maps, preregistrations, evidence files and D7 records. Never rewrite them. To read a historical source file, use `git show <recorded-SHA>:<old-path>`.
- **Living navigation documents use current paths:** the results note, runbook, `DEMO.md`, `INDEX.md` and the backend README.
- **Executable code must not hardcode either package directory name.** It resolves its inputs from `thermorl2.raps_adapter.systems.project_root()` (the current backend package root), and its application provenance from `thermorl2.experiments.provenance.application_source_hashes()`. Future manifests therefore key application sources as `thermoRL/backend/thermorl2/...`, while historical manifests keep `thermoRL/thermorl-v2/thermorl2/...`. That difference reflects the location only; the bytes of the moved files are identical.
- Relative workload paths in configs (`experiments/summit/_workloads/<sha>.parquet`) are unchanged and resolve under the backend package root.

## Post-rename repairs
1. **Relocation-only code fix (Mac, 2026-10-31).** The workload root (`runner.py`) and the application source map (runner, bench, probes) now use the helpers above. `tests/unit/test_relocation.py` covers this. No scientific code path changed.
2. **Re-tracking (pending on Arch).** The rename dropped 81 previously tracked files from git. Moving a file counts as adding it at the new path, and the `thermoRL/.gitignore` `*.md` and root `*.log` and `runs/` rules then excluded it. Restore them with `python3 docs/handoffs/scripts/retrack_dropped_files.py` (dry run), then `--apply`. The script hash-verifies each file against `docs/handoffs/2026-10-31-post-c6-review-evidence.json`.
3. **Post-rename acceptance (pending on Arch).** Fresh on-disk clone, `uv sync --frozen`, then `uv run pytest tests/unit tests/integration -q`. Expect all tests to pass. Historical D7 at `06032b4` does not cover the current HEAD.
