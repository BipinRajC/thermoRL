# Copyable prompt — Opus 5.5 final backend review and Sonnet integration brief

You are Opus 5.5, ThermoRL’s independent reviewer and integration architect. Bipin wants one final assessment of the completed backend/experiments/packaging, then an implementation-ready brief for Sonnet 5.5 to build a good frontend demo. Substantial frontend changes are acceptable; changing the accepted science is not.

This is a **review and planning assignment**. Do not implement fixes, regenerate outputs, run physics, or start the Sonnet work. You may write the review and implementation brief. Do not commit/push unless Bipin authorizes it.

## Start here

Repository: `/home/bipin/thermoRL` on Arch, or the equivalent checkout on your machine. Branch: `feat/parasparam-demo`. The implementation snapshot audited by the handoff is `c09f735ddde82d0acaf54f2f0900a2563c3915ee`; the handoff commit comes after it. Inspect any subsequent changes rather than assuming they were reviewed.

Read **in full**:
1. `docs/handoffs/2026-10-31-post-c6-backend-frontend-review.md`
2. `docs/handoffs/2026-10-31-post-c6-review-evidence.json`
3. `docs/checkpoints/C6-final-packaging.md`
4. `docs/checkpoints/C4-review-opus.md`, `C4-g4-alibaba.md`, `C3-review-opus.md`, `C3-g4-synthetic.md` and `C5-whatif.md`.
5. `docs/results/2026-11-parasparam-demo-results.md`, `runbook.md`, `d7_fresh_clone_check.json`, `final_packaging_checks.json` and `raw_backup_record.json`.
6. Dated approved addenda and Tasks 15–17 in `docs/superpowers/plans/2026-10-27-parasparam-demo.md`; spec§6/§8 and experiment conventions.
7. The actual current backend/frontend code and E11/E12 results/plots referenced by the report.

Current physical roots are **`thermoRL/backend/`** and **`thermoRL/frontend/`**. Historical records used `thermoRL/thermorl-v2/` and `thermoRL/thermoRL-new/`. Some moved files are present on Arch but no longer tracked. When absent in your checkout, use `git show b3bd5ac:<old-path>` to read their prior committed contents. Do not restore user-owned local deletions or rewrite historical evidence. Preserve the two C4-execution documents and their pinned SHA references.

**Backup is waived.** Bipin said “yes lets skip the backup thing”. No backup copy was made or verified; raw data remains local on Arch. Older C6/pending-destination wording is superseded. Do not make backup a gate or ask for a destination again.

## Verify current readiness, not only past success

Historical D7 at code candidate 06032b4 passed196 non-FMU tests, 22 pinned hashes and one finite Summit smoke. **Current post-rename acceptance is195 passed, 1 failed in35.43s**, from:

```bash
# cwd: thermoRL/backend; existing Python3.12.14 environment
.venv/bin/python -m pytest tests/unit tests/integration -q
```

The failing runner-contract test and direct workload-loader check both hit the removed `thermorl-v2` root before FMU initialization. The source collectors in runner/bench/probes also search the removed directory and discover0 application modules. Treat these as real release/integration blockers. Do not mark the current branch green merely because historical D7 passed.

Verify the companion evidence’s claims:
- 43 package/config files are byte-identical to the tested backend after path mapping.
- c09f735 contains596 renames and 81 deletions; all 81 mapped files remain locally byte-identical, but are absent from Git at their new paths. Review which should be retained versus intentionally retired. Never force-add the entire backend and accidentally ingest ignored multi-GB raw runs.
- All 230 raw inventory entries and 12 frozen README sections still match locally under the new root.
- The moved editable environment and many documentation links still reference old paths. Imports from backend cwd can succeed despite a stale `.pth`; verify the correct boundary instead of declaring all imports broken.

You may run bounded non-FMU tests/read-only checks if the environment supports them. Do not patch tests or code to make them pass in this review. No full pytest, tests/fmu, FMU smoke, run.py/run_matrix/report CLI, workload generation, legacy simulator or `make_demo_bundle.py` execution. For frontend build/browser checks, use scratch outputs and preserve original bundles/dist; record exactly what was tested and any limitations.

## Review the science and presentation

Independently check the two frozen G4 outcomes, five-policy/three-seed tables, metric-specific S1, invariants, 19-attempt E12 accounting, mixed launch generations, exact C′ scope, resource definitions and new labelled assets. Open PNGs and inspect GIF frames; do not rely only on filenames or summaries.

Both outcomes remain “no material value on the homogeneous twin”, value_beyond_power=false. PB−TP must reach0.5°C in every seed. E11 packing≈TP applies to E11 only. Preserve the exact E12 descriptive-ordering sentence and about-two-condition correlation caveat. Preserve E10 packing2 h, E11 seed 1 packing/PB2 h prefixes and E12 TPseed1 6 h direct-repeat scopes; do not imply the whole matrix or cross-machine portability was verified.

M3 is unresolved. M2 is E11-specific. S2 and spec§8/D8 must stay accurate. No hardware, safety, PUE, energy/cooling-power savings, carbon, lifetime, RL, surrogate, heterogeneous-zone or identified-mechanism claims. No threshold/policy/workload/G1/spanning/FMU tuning or extra experiment is needed to rescue a positive headline.

On the Mac, ignored raw files may be absent. Distinguish independent checks, calculations from committed derived artifacts, Sol-reported raw verification and missing access. Continue a bounded review; do not invent raw verification or treat reviewer access alone as a mechanics failure.

## Assess frontend reuse and choose the integration boundary

Inspect `thermoRL/frontend/viz/src/{main.ts,schema/vizevent.ts,replay/player.ts,scene/racks.ts}`, index.html/CSS and the legacy S5/S6/bundle pipeline.

The old bundle is24 frames over0–460s, RR versus THI-Lookahead, 3 cooling zones×16 racks. The current experiment is homogeneous Summit, 257 racks/4626 nodes, nominal6 h traces. The frontend also expects unsupported PUE/carbon/SLO/emergency/dual-price/counterfactual fields. Do not fill incompatible fields with invented zeros or reuse legacy simulated results.

Review the reported source-geometry defect:4 columns and 16 instances require4 rows, but `rowZ` has2 entries and rows2/3 co-locate;12 default positions for16 racks per zone. Browser behavior was not newly validated by Sol.

Recommend a replay-first architecture unless you identify a concrete need for browser-controlled live runs. Existing immutable FMU ledgers can feed a compact exporter and the adapted player; no new scientific run is required. A live job API/queue/progress lifecycle is a separate larger scope and must be explicitly justified.

A good demo should clearly show experiment/workload/seed/policy identity, 257-rack schematic, actual modeled coolant°C and power/occupancy, a shared time axis, strict evaluation-window context, real placement events, frozen primary outcome/gaps and logged decision details with precision caveats. Keep payload/browser-memory limits explicit; do not inline hundreds of MB of canonical decision contexts. Do not run replacement thermal physics in JavaScript.

## Required outputs

Write:
1. `docs/reviews/2026-10-31-opus-post-c6-integration-review.md`
2. `docs/handoffs/2026-10-31-sonnet-5-5-demo-integration-brief.md`

The review must contain:
- Reviewed SHA, environment, commands and evidence limits.
- Clear verdict on scientific completion, present backend operability and demo integration readiness.
- Severity-ranked findings with exact files/lines and smallest corrections.
- Review of results and actual figures/animations, plus supported/unsupported claims.
- What is complete, what is blocked, what is optional, and a grounded remaining-work estimate.
- Which decisions Bipin must make; do not treat backup as unresolved.

The Sonnet brief must be ready to execute after Bipin approval:
- Ordered tasks: relocation/tracking repair → bounded regression tests → replay contract/exporter → frontend adaptation → build/browser/interaction/payload checks → final demo packaging.
- Exact files and a minimal versioned data contract with field semantics, timestamps, decision references, scales, summaries, hashes and unavailable-field handling.
- Which existing UI/player parts to reuse, what to replace, and what unsupported panels/data to remove.
- Initial experiment/seed/policy comparisons, controls, loading/error states and scientific labelling.
- No-overwrite outputs, immutable historical-record handling, scoped commits and validation/acceptance criteria.
- Scope exclusions, checkpoints and explicit escalation for anything requiring new simulations or altered science.
- Clear separation of backend housekeeping/export work from frontend rendering work. Do not assume Sonnet has this conversation.

Bipin accepts frontend changes for a good demo, so do not preserve the old three-zone model merely to minimize edits. Preserve truthful data and a coherent walkthrough instead. Review and plan only; **STOP after providing the review, Sonnet brief and a concise recommendation to Bipin**.
