# C4 Independent Review — E12 G4 on the Alibaba-Derived Workload, Recovery, C′, and Project Progress

**Reviewer:** Claude (Opus), the independent technical and scientific reviewer. **Date:** 2026-10-31.

**Reviewed SHA:** `b96a43b400d60a341dc1be0e4e2adbc84c10b186`. This is the local HEAD and `origin/feat/parasparam-demo`, with no later commits.
- Delta since my C4 prelaunch review (`5a0828b`): `f5d6dae`, `876e678`, `18dfea1`, `f7cde7b`, `e0e1522`, `b96a43b`.

**Environment:** the Mac (macOS, arm64).
- The working tree has unrelated local deletions (`CLAUDE.md`, `HANDOFF.md`, `docs/prompt.md`, `docs/repository-notes.md`). I left them untouched and read `repository-notes.md` from `b96a43b`.
- I ran no FMU and no matrix, and changed no artifact.
- My scratch outputs are outside the repository.
- This review is **not committed or pushed**, pending Bipin's authorisation.

**Labels:**
- FACT: checked directly.
- DERIVED: I calculated it myself.
- INFERENCE: a supported interpretation.
- HYPOTHESIS: plausible but not tested.
- UNRESOLVED: not established.
- **SOL-REPORTED:** asserted by Sol's records; I could not verify it independently here.

---

## Executive summary for Bipin

**Verdict: ACCEPT C4 WITH CONDITIONS.** There are no scientific, protocol or invariant blockers. The conditions are documentation and governance (§10).

1. **E12 is scientifically valid under its frozen protocol.** The frozen outcome is **"no material value on the homogeneous twin"**. Recomputing from the committed per-tick max-rack series, I get PB−TP = **+0.1776, +0.0773, +0.1088 °C**. None reaches 0.5 °C, so `value_beyond_power = false`.
2. **E12 is not a repeat of E11's pattern, and it must not be reported as one.**
   - In all three seeds, thermal_predictive had the **lowest** time-mean max-rack temperature and packing the **highest**: packing−TP = +0.35 / +0.44 / +0.42 °C.
   - TP also has the lowest spread, rack-temperature std and hottest-decile mean in every seed.
   - These differences are **small in absolute terms** (the whole E12 coolant range is about 38.7–42.7 °C) and **below the preregistered materiality threshold**.
   - They rest on about **two** independent workload conditions, because seed 3 ≈ seed 2.
   - The near-duplicate seeds 2 and 3 differ from each other by up to 0.16 °C for single policies, which is the same order as the PB−TP gaps (INFERENCE: the consistent sign is fragile).
3. **The recovery is auditable and stayed within the recorded interpretation.**
   - I verified from the records: the journal has 18 starts and 15 completions; the 3 interrupted attempts are archived with unchanged hashes; the 4 original runs are byte-unchanged; attempt numbering is correct; no scientific failure was reclassified.
   - The two launch SHAs differ only in `run_matrix.py` and `e12_evidence.py`. I checked all 41 manifest source entries against git at both SHAs.
   - **One governance gap:** the machine record `recovery_approval.json` says `approved_by: "Bipin"`, but you gave only "dont stop, resume wherever it stopped". The 19-attempt interpretation should be **explicitly ratified by you** in a dated addendum (condition C1).
4. **C′ adds real, but narrow, reproducibility evidence.** It is the project's first byte-identical **6 h** fresh-process repeat of a **temperature-reading** policy: TP seed 1, Alibaba workload, same machine, environment and SHA. All 14 other configurations, every E11 6 h configuration and cross-machine portability remain unrepeated.
5. **The figures are honest in content but not self-describing.**
   - They show the whole episode with no marker for the 1 h evaluation start.
   - They carry no workload, seed or "G4 negative" label inside the image.
   - They use a narrow (~3.7 °C) inferno scale that visually amplifies small differences.
   - They are seed-1 only.
   - In the first GIF frame, thermal_predictive's scattered placements are most plausibly tie-breaking among nearly identical racks, not visible intelligence (HYPOTHESIS).

   None of this blocks C4. All of it must be fixed or captioned before demo use.
6. **Progress.** The engineering and both preregistered G4 evaluations are done. What remains is mostly **packaging** (Task 17), a **C5 non-execution note** (Task 16), and **optional** replay work (Task 15). **No further simulation is required** to finish the approved scope. The only open simulation question is D7 (§9).
7. **Recommended next step:** accept C4 with conditions, then authorise one bounded **packaging assignment**:
   - C5 note;
   - Task 17 results note, `DEMO.md` and runbook;
   - demo-labelled re-renders of the existing figures from existing ledgers, without overwriting the originals.

   Defer Task 15 replay work. Decide D7 explicitly.

---

## 1. Scope, environment, commands and evidence access

**Commands run (Mac):**
- `git fetch`, `status`, `log`, `diff` and `show` across `5a0828b..b96a43b`, `18dfea1..e0e1522` and `e0e1522..b96a43b`.
- `shasum`, plus Python scripts over committed JSON/CSV/parquet.
- `uv run --frozen --no-sync pytest tests/unit tests/integration -q`, in a scratch venv built earlier from the unchanged `uv.lock`. Result: **189 passed in 24.77 s**. This is the bounded non-FMU tier; integration tests construct small RAPS engines with no FMU. Repository status was unchanged afterwards.
- Frame extraction from both GIFs (Pillow, into scratch).

**Evidence available:** all committed artifacts, including the per-tick max-rack series (`results/max_rack_attribution.json`), the 15 manifest mirrors, the repeat manifest, journals, inventories, service snapshots, workloads, the Alibaba CSV on the Mac (SHA-equal), and all plots.

**Not available on the Mac** (a reviewer-access limitation, not an experiment defect): all raw run directories (`runs/`, `provenance/rerun_1/runs/`, `provenance/failed_*/`), about 3.6 GB on Arch. So:
- I did **not** recompute invariants 1, 2 and 4, the S1 values, disagreement or self-reproduction from the raw ledgers;
- I did **not** re-hash raw files or re-run the C′ comparison.

These remain SOL-REPORTED, but they are corroborated by consistent hashes across independently produced records. The read-only commands for closing them are in §11.

---

## 2. Verdict and reasons

**ACCEPT WITH CONDITIONS.**
- The protocol was frozen and followed. Preregistered README sections are hash-identical at `ababba8` and `b96a43b` (DERIVED with my own section parser).
- The config is byte-identical to the launch config; workloads are unchanged; `primary.yaml`, G1, the FMU and `sim-raps` are unchanged.
- The primary metric and rule recompute exactly.
- Invariants pass per the report, and the gate code is correct for the C′ scope.
- Recovery provenance is complete and consistent.

The conditions (§10) are needed so that the record and the presentation do not overstate the outcome.

---

## 3. Findings, by severity

### 3.1 Scientific, protocol or invariant blockers
**None.**

### 3.2 Engineering and provenance

| ID | Finding | Evidence | Impact | Smallest correction | Blocks? |
|---|---|---|---|---|---|
| P1 | The recovery approval is machine-labelled as Bipin's, but its content (19 attempts, restart 3, source diff) is the agent's interpretation. No dated plan addendum records the recovery decision. | `provenance/recovery_approval.json` (`approved_by: "Bipin"`, written 20:36:47 UTC by the agent); `run_matrix.reviewed_recovery` treats that file as approval; the plan has no recovery addendum. The prose in C4 and README is accurate ("agent's bounded operational interpretation"). | Governance: a future reader of the JSON could believe you approved the specific accounting and source change. | Bipin adds a **dated ratification addendum** to the plan (accept or qualify the interpretation). Do not edit the JSON. | **Yes, cheap (condition C1)** |
| P2 | The report gate accepts runs from different git SHAs, provided the configs match. Numerical-source equivalence across generations rests on a separate record, not on a gate. | `report.validate_expected` (config only); `provenance/recovery_1/source_identity_verification.json` | For E12 I verified it independently (all 41 source entries match git at each SHA; only the 2 orchestration files differ). The general risk is future mixed-generation matrices. | Document in Task 17. Optionally add a gate later. | No |
| P3 | `matrix_runtime.json` reuses `matrix_wall_s` for the span **including downtime** (9565.7 s), whereas E11's means controller wall. Downtime is not a separate field. | `results/matrix_runtime.json` (scope string present) | Possible confusion in cross-experiment runtime tables. Derived downtime ≈ 9565.7 − (≈2680 original active + 5033.4) ≈ 1850 s; the exact original exit time is unknown. | State it explicitly in the Task 17 runbook. | No |
| P4 | The interruption-archive journal events were appended post hoc by the preservation step (20:47:26 UTC, `returncode: null`), not by the controller. | Journal lines 11–13 | Correctly labelled, and appending is consistent. Readers should know these are recovery records, not controller observations. | Note in Task 17. | No |
| P5 | The SIGTERM origin is unresolved; interrupted-process RSS and the children's final exit status are unknown. Signal handling (R6) is still not implemented; the durable services mitigated it this time. | `execution_interruption.json`; C4 | Operational only. | Note; optionally fix R6 in packaging. | No |
| P6 | **Auditability depends on one machine.** The raw E11, E12, repeat and interrupted ledgers exist only on Arch (gitignored). | `results/run_files.json`; storage totals | Losing that disk would leave only hashes, summaries and the per-tick max series. | Make a checksum-verified off-machine copy and record its location in Task 17. | No (recommended) |
| P7 | The service-success snapshots and memory peaks are agent-recorded `systemctl` output. | `provenance/recovery_1/*service*.json` | Cannot be verified independently after the fact. | Accept as SOL-REPORTED. | No |

### 3.3 Analysis and interpretation

| ID | Finding | Impact | Correction | Blocks? |
|---|---|---|---|---|
| I1 | C4 states the rule outcome correctly but does **not describe** E12's consistent primary-metric ordering (TP lowest and packing highest in all seeds). That ordering differs from E11. | Risk in both directions: a reader may wrongly assume E12 ≈ E11 (packing ≈ TP), or later over-promote the ordering. | Task 17 uses the wording in §9 (allowed claims). | **Condition C2** |
| I2 | The seed-2/3 near-duplication matters for interpreting the ordering. Seed 3 − seed 2 per policy: packing −0.037, NB +0.159, PB +0.013, CR −0.145, TP −0.019 °C. These are comparable to the PB−TP gaps (0.08–0.11 °C). | Consistent sign in ≈ 2 conditions is weak evidence. This is informal context, not a designed sensitivity test. | State it alongside I1. | Part of C2 |
| I3 | High PB-vs-TP counterfactual disagreement (0.90–0.93 on PB contexts) alongside small temperature consequences. | HYPOTHESIS: with 1–2-node jobs and many nearly equivalent racks, the scorers differ mostly among near-ties with little thermal consequence per decision. Not tested. | Keep it as a hypothesis. | No |

### 3.4 Presentation and documentation

| ID | Finding | Correction | Blocks? |
|---|---|---|---|
| V1 | The figures have no evaluation-window marker (t = 1 h), no in-image workload/system/seed label, and no "descriptive; G4 negative" note. They show the whole episode including the first hour. Captions exist only in the README. | Demo-labelled re-renders from existing ledgers (Task 17). Never overwrite originals. | **Condition C3** before any demo use |
| V2 | The heatmap/GIF colour range is ≈ 38.7–42.4 °C with `inferno`. A ~1 °C difference looks dramatic. E11 figures span ≈ 39.5–56 °C. | Print the range on the figure; never juxtapose E11 and E12 without stating the scales. | Part of C3 |
| V3 | In the GIF's t = 0 frame, packing and PB place in index order (bottom rows), while TP's placements look scattered. This is most plausibly tie-breaking on sub-micro-degree differences between nearly identical idle racks (C1 G1 spread ≈ 9e-10 °C; C3 F3 precision finding). HYPOTHESIS. | Caption it, or do not feature that frame. To check on Arch: first TP decisions' logged `t_c` values identical at six decimals. | Part of C3 |
| V4 | Frozen README sections still read as prelaunch: "No policy simulation or rerun is authorized", "Review operating-regime acceptability before authorizing execution", Limitations "E12's planned C′ repeat is not yet evidence". The "Execution interruption" section says "G4 is pending review" and "artifacts remain uncommitted". The status line and dated completion addendum supersede these, but a mid-document reader can be misled. | Add a non-frozen "Read first: current status and superseded wording" pointer under the header (Task 17). | No |
| V5 | All visuals are seed 1 only. | Label "seed 1 of 3 (seeds 2/3 correlated)". | Part of C3 |

### 3.5 Optional improvements
- **O1. Zero-simulation cross-generation prefix check (read-only, Arch).** Compare the complete lines of interrupted attempt-1 `decisions.jsonl` (written under `18dfea1`) with the selected attempt-2 files (written under `e0e1522`):
  - TP seed 1: attempt 1 reached about 16200 s;
  - packing seed 2: attempt 1 reached about 19800 s.

  Identical prefixes would be **empirical** support that the source change did not affect numerical paths, and a partial second repeat for packing seed 2. It is descriptive only, and must not be relabelled as `verified_E12`.
- **O2.** Signal handling (R6), and an explicit `downtime_s` field.
- **O3.** A future gate for mixed-SHA source equivalence (P2).

---

## 4. Independent G4 calculation and all-policy analysis

### 4.1 Primary metric (DERIVED from `results/max_rack_attribution.json`)
- The per-tick endpoint maxima cover exactly t_s = 3610…21600, 1800 samples per run.
- `raps_power_tick_s = t_s − 10`.
- All 15 means match `metrics.csv` to within 1e-12.

| Seed | packing | node_balance | power_balance | coolest_rack | thermal_predictive | PB−TP | packing−TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 41.4109 | 41.2569 | 41.2351 | 41.1648 | **41.0575** | 0.17758993078025043 | 0.35332112789507875 |
| 2 | 41.3458 | 40.9697 | 40.9820 | 41.2398 | **40.9047** | 0.077264841939523876 | 0.44105441733383799 |
| 3 | 41.3089 | 41.1289 | 40.9947 | 41.0952 | **40.8859** | 0.10879156917675914 | 0.42305513292543395 |

**Rule applied myself:** no seed reaches 0.5 °C, so `value_beyond_power = false`. This matches `decision.json`.

**Per-tick view (DERIVED):**
- PB−TP is positive in 85 % / 70 % / 71 % of ticks. Medians are 0.13 / 0.07 / 0.09 °C; 5th–95th percentile ranges are −0.02…0.48, −0.20…0.36 and −0.34…0.50.
- By hour, the PB−TP gap varies, and in seeds 2 and 3 it changes sign in some hours.
- packing−TP is positive in 78–97 % of ticks.

### 4.2 Secondary metrics (DERIVED from `metrics.csv`; descriptive only)

| Metric | PB−TP (s1, s2, s3) | packing−TP | Lowest policy per seed |
|---|---|---|---|
| `maxrack_p99_c` | +0.18, +0.05, +0.46 | +0.21, +0.79, +0.96 | CR, TP, TP |
| `raw_max_c` | +0.16, +0.05, +0.48 | +0.18, +0.82, +0.98 | CR, TP, TP |
| `spread_mean_c` | +0.26, +0.16, +0.18 | +0.54, +0.62, +0.59 | TP ×3 |
| `rack_t_std_mean_c` | +0.037, +0.029, +0.029 | +0.11, +0.10, +0.10 | TP ×3 |
| `top_decile_mean_c` | +0.047, +0.045, +0.041 | +0.19, +0.20, +0.19 | TP ×3 |
| `rack_kw_std_mean` (kW) | **−0.17, −0.15, −0.15** | +0.61, +0.69, +0.68 | PB ×3 |
| `mean_rack_c` | ≈ +0.001 | ≈ +0.03 | mixed |
| Pump energy (kWh, right-endpoint, warm-up excluded) | ≈ 0.01 of 6376 | ≤ 0.17 | — |
| IT energy (held-input, warm-up excluded) | 0 (identical by construction) | 0 | — |
| Hot rack-seconds above t_hot 63.3 °C; THI < 0.1 at 45 °C reference | 0 everywhere | 0 | not discriminating |
| Jobs, utilisation, waits, censoring | identical across policies by construction | — | — |

**What the evidence does and does not show:**
- **Consistent across seeds:** on the primary metric, spread, rack-temperature std and hottest decile, TP ≤ every other policy and packing ≥ every other policy.
- **Metric-specific:** PB has the most balanced rack power, but not the coolest hottest rack. TP trades slightly higher power imbalance for lower coolant extremes. p99 and raw max are mixed.
- **Small:** the mean rack temperature is the same within 0.03 °C (identical IT power). The whole spatial spread is only about 1.2–1.7 °C.
- **Not shown:**
  - material benefit by the preregistered rule;
  - generality beyond this regime;
  - any physical mechanism;
  - statistical significance (none was preregistered, and there are about 2 independent conditions).

**Disagreement vs self-reproduction (SOL-REPORTED values; method verified at C3):**
- PB-vs-TP disagreement on each policy's contexts is 0.57–0.93.
- Self-reproduction: TP 0.975–0.981; coolest_rack 0.83–0.91 (herding and near ties); PB about 0.998.

**Latency (SOL-REPORTED):** mean about 0.43–0.51 ms, p95 about 0.89–0.99 ms per decision.

**Runtime:** about 1150–1690 s per process (§6).

---

## 5. Figures and animations (opened and inspected; GIF frames 0, 30, 120, 240, 330, 420, 540, 600, 660 and 719 extracted)

- **`timeseries_seed1.png`**
  - **Top panel:** max-rack °C over 0–6 h. Every policy rises from 39.5 °C during hour 0–0.3, then follows the burst cycle:
    - plateau at about 40.3 °C;
    - burst peak around 2–3 h, where packing reaches ≈ 42.4 °C against TP ≈ 41.2 °C;
    - quiet dip near 3.3 h;
    - second peak at 4.5 h, where PB is highest (≈ 42.4 °C) and packing is *not* the highest;
    - dip near 5.2 h, then rise to 6 h.
  - **Bottom panel:** max−min spread, 0–2.8 °C.
  - **Assessment:** it agrees with the numbers (the packing−TP gap is concentrated in hours 2–3 of seed 1). However:
    - the y-axis spans only 3 °C;
    - there is no t = 1 h window marker;
    - there is no in-figure seed or workload label.

    The 2–3 h hump is the most "headline-like" feature and is seed-specific (V1, V5).
- **`heatmaps_seed1.png`:** five panels on a shared 38.7–42.4 °C scale over rack index and time.
  - **Packing:** fills low-index racks first, leaving racks ≥ 155 untouched until about 1.8 h, then fills diagonally.
  - **Other policies:** spread load across all racks from the start.
  - **All panels:** vertical light/dark bands show the **whole facility** warming in bursts and cooling below the post-warm-up level (dark ≈ 38.8 °C) in quiet periods. Per I1, facility-level dynamics dominate the time pattern. Why temperatures fall below the post-warm-up level is UNRESOLVED; one HYPOTHESIS is control-loop undershoot.
  - **Assessment:** good for showing that "placement changes the spatial distribution at identical power". The narrow colour range exaggerates contrast (V2). The first hour is shown without marking.
- **`anim_packing_vs_thermal_predictive_seed1.gif`:** 720 frames at 80 ms; 13×20 schematic grid with 3 blank cells; shared scale within the comparison; cyan rings mark placements since the previous frame.
  - **Early frames:** packing concentrates in the bottom rows; TP spreads.
  - **2.75 h:** packing has a bright bottom-row rack.
  - **3.5 h burst:** many rings.
  - **5.0 h quiet:** few rings and a dark field.
  - **Endpoint (5.99 h):** both panels show scattered hot racks, and TP does *not* look obviously cooler.
  - **Missing:** rack numbers, workload label, window marker. Frame 0's TP scatter needs caption V3.
- **`anim_power_balance_vs_thermal_predictive_seed1.gif`:** PB's frame 0 places along the first two rows in index order, because committed-power ties break to the lower index. The rest is visually very similar to TP. **Assessment:** an honest visual of a negative result, provided it is captioned.
- **Comparison with E11 and E10:** E11's figures share the same layout and the same missing window marker, on a much wider scale. Comparing across experiments requires explicit scale labels.

**Do any figures suggest an unsupported positive headline?** Not in content. The risk lies in presentation: an unlabelled seed-1 time series with a 3 °C axis and the packing hump, shown without "G4 negative, below 0.5 °C, regime-specific", could suggest "thermal-aware placement removes hotspots". **Cosmetic fixes, not scientific blockers.**

---

## 6. Recovery, accounting, source freeze, C′

### 6.1 Accounting (FACT from `matrix_events.jsonl`, 43 lines)

**Starts — 18 in total:**
- 7 original (lines 0, 1, 2, 4, 6, 8, 10);
- 3 restarts, each `attempt: 2` with a matching `console_*_attempt2.log` (lines 18–20, at 20:50:03 UTC);
- 8 first attempts of previously unstarted configurations (lines 22–38).

**Completions — 15:**
- 4 original (19:55–20:18 UTC);
- 11 in the recovery.

**Other events:**
- 3 `failure_archived` with `failure_kind: external_interruption` and `returncode: null`;
- 4 `skipped_matching_config` (the original runs; re-validated by `_verify_run` before skipping);
- 3 `seed_cross_policy_invariants_passed`.

**Repeat:** separate journal (`provenance/rerun_1/journal.jsonl`), started 22:14:29 UTC after the primary service exited at 22:14:00 UTC, completed 22:39:09 UTC.

**Checklist:**
- **A. Original four runs unchanged.** FACT: all 20 inventoried files of the four complete runs match the historical interruption inventory exactly in `results/run_files.json`. Their manifests carry `18dfea1`.
- **B. Interrupted attempts traceable.** FACT: all 6 relocated files match historical bytes and SHA. The relocation inventory hashes the historical inventory (match). All six appear in `run_files.json` under `provenance/failed_*`. The original console logs are committed and SHA-equal to the historical inventory.
  - Progress at interruption: TP seed 1 reached about 16200 s; packing seed 2 about 19800 s; node_balance seed 2 had zero decisions.
- **C. Attempt numbers and identities correct; no extra retry.** FACT. `primary_attempt_summary` enforces this (tests in `test_recovery_accounting.py`).
- **D. No scientific failure reclassified.** FACT: no `failure.json` existed; no scientific failure kind appears; the only kind is `external_interruption`.
- **E. Runtime merges both generations** (5033.36 s recovery controller; 9565.74 s span including downtime). Downtime is implicit (P3).
- **F. Services succeeded.** SOL-REPORTED snapshots: `ExecMainStatus 0`, `Result success`, `NRestarts 0`, `Restart no`, `RuntimeMaxUSec infinity`.
- **G. First waves are identified by policy and run.** Original: packing, NB, PB seed 1. Recovery: NB s2, packing s2, TP s1 (`index` is controller-local).
- **H. Memory scopes are distinguished.**
  - Process RSS 1.63–1.99 GiB (DERIVED from the manifests).
  - Recovery parent 1.356 GiB.
  - Primary cgroup 6.925 GiB (7435931648 B).
  - Report 4.979 GiB.
  - Follow-up cgroup 5.974 GiB.
  - Repeat 1.992 GiB; guard 1.304 GiB.

**Authorisation precision:** C4, the README and the recovery checkpoint represent your instruction and the agent's interpretation correctly. Only the JSON's `approved_by` field overstates it (P1). The SIGTERM origin is correctly left UNRESOLVED.

### 6.2 Mixed source generations (DERIVED)
- The 15 manifests split 4 × `18dfea1` and 11 × `e0e1522`.
- Each has 41 source entries (38 thermorl2 files plus the 3 RAPS files: `config/summit.yaml`, `raps/engine.py`, `raps/power.py`).
- Every entry equals `git show <sha>:<path>`.
- **Only `run_matrix.py` and `e12_evidence.py` differ.** Workers run `run.py` → runner, scheduler, scorers, placement and backend, all identical. Environment dicts are identical across all 15 and the repeat.
- `git diff 6ee93c4..b96a43b` is empty for `core/`, `thermal/`, `sim-raps/`, `models/`, `primary.yaml` and E01. The only `raps_adapter/` changes since E11 are workload loading and validation and a manifest memory field. **The E11 and E12 decision and thermal paths are the same.**
- **Source freeze:**
  - `e0e1522` committed at 20:47:52 UTC;
  - service started at 20:49:35;
  - evidence completed at 22:39:18;
  - next commit `b96a43b` at 23:01:22.

  So there was no commit in between, and both TP seed-1 manifests carry `e0e1522`.
  - Porcelain at the run commits shows only the unrelated deletions plus untracked or modified experiment artifacts (journal, inventories); no tracked source changes.
  - `e0e1522..b96a43b` contains no production or test code.

### 6.3 C′ (FACT for structure and hashes; the raw comparison is SOL-REPORTED)
- `determinism_evidence.json` SHA = `a24fcdea…d604` = its seal.
- `full_rerun_comparison.json` SHA equals its reference.
- Every referenced primary and repeat file SHA equals the corresponding inventory entry, and both manifest mirrors equal their referenced manifests.
- Both TP seed-1 manifests have identical `git`, config, workload, meta, FMU, source map and environment; 7200 s warm-up, 2160 steps, 21600 s; identical `decisions_sha256` (`74e81979…`) and `intervals_sha256` (`292819e1…`); identical job-event SHAs.
- Their timing-ledger SHAs differ, as expected.
- **Gate code** (`report.approved_e12_determinism`, `seed_gate`) accepts only the exact C′ pattern: TP seed 1 `verified_E12`, the other 14 `inherited_not_remeasured` with the exact inherited scope string, and `fallback_to_A_prime: false`. Comparison (`e12_evidence.compare_full_rerun`) is full-file decision bytes AND `assert_frame_equal(check_exact=True)`. Interval, job-event and publication bytes are information only.
- **The repeat is excluded from primary aggregation**: paths come only from `runs/`, and 15 distinct paths are asserted.

**How much C′ strengthens reproducibility:**
- **Before:** E10 packing seed 1, 2 h, plus E11 seed-1 packing/PB 2 h prefixes.
- **Now added:** one full 6 h temperature-reading-policy configuration, E12 TP seed 1, reproduced byte-for-byte in a fresh process on the same machine, environment and SHA. That is the strongest single determinism datum the project has.
- **Still not shown:**
  - the other 14 E12 configurations;
  - any 6 h E11 configuration;
  - cross-machine or cross-environment portability;
  - the original-SHA runs.

  O1 could add cheap cross-generation evidence.

### 6.4 Tests (189 passed here; blind spots)
**Good coverage:**
- C′ comparison: identical pair, byte change, interval change, timing-only change, each precondition, A′ rejection, E11 compatibility, no overwrite, repeat exclusion, per-seed gate.
- Lightweight invariants match the core semantics under mutations.
- Full-machine head-of-line queueing across ticks, with allocation replay.
- Recovery accounting, including unapproved and scientific retry rejection.
- `MemoryError` classified as non-scientific.

**Blind spots:**
- No test that the report detects numerically different source across mixed SHAs (P2).
- Recovery tests use synthetic journals. There is no end-to-end skip-plus-restart through `execute_jobs` with archive-path or hash checks; the relocation inventory covers that in practice.
- The queueing test covers packing and PB only.
- A human approval cannot be verified by code (P1).

---

## 7. Workload validity and E11-versus-E12 synthesis

**Utilisation, kept as three separate quantities:**
- **Nominal construction ρ:** 0.6.
- **Offered window utilisation:** 0.48577 / 0.45462 / 0.45663 (DERIVED at prelaunch).
- **Realised ledger utilisation:** 0.48562 / 0.45457 / 0.45657 (SOL-REPORTED; consistent with my FCFS emulation).
- **Queueing:** mean waits 8.62 / 6.00 / 6.13 s; peak queue 694 / 564 / 577 jobs; zero censoring.

**Regime limits (all carried correctly in C4):**
- 1–2-node, low-density jobs: loss-inclusive load about 2.79–2.99 kW per rack above idle, against about 10 kW in E11;
- about 23 minutes dense and 80 minutes near-silent per 1.74 h cycle, with brief overload;
- seed 3 ≈ seed 2 (+33.0366 s, +162 pods);
- lifecycle-as-runtime and seconds-unit assumptions; Running/Failed pods included; heavy clipping;
- about 2064× arrival-only compression with an artificial wrap; empty start;
- static mapping; loss-exclusive estimates versus loss-inclusive FMU inputs;
- capped, unsettled warm-up; G1 heuristic; ≈ 4 % committed-increment understatement;
- 45 °C is a reference only; coolant is modelled; S2 applies verbatim.

**E12's own attribution (DERIVED from the attribution file):**
- Argmax racks hold 13.8–26.7 kW, roughly idle to about +13 kW. Median argmax-rack power: TP ≈ 19.0–19.6, PB ≈ 19.4–20.2, packing ≈ 21.6–22.1 kW.
- Argmax racks rotate widely: 41–49 distinct racks under packing, 84–100 under TP.
- Ticks whose argmax rack has **no** resident job at the driving tick: 0–0.9 %. These racks were recently vacated or are affected by non-local temperature; descriptive only (M3 mechanism unresolved).
- No rack-filling jobs, so E11's M2 explanation does not transfer.

**Synthesis (INFERENCE):**

| | E11 (synthetic, large and high-power jobs) | E12 (Alibaba-derived, small, low-power, bursty) |
|---|---|---|
| G4 | No material value (+0.34, −0.15, −0.07) | No material value (+0.18, +0.08, +0.11) |
| Packing vs TP on the primary metric | ≈ (+0.08, −0.11, +0.28); no consistent order | packing highest in all seeds (+0.35 to +0.44) |
| TP rank on the primary metric | Never lowest | Lowest in all seeds |
| Explanation status | Max governed by rack-filling high-power jobs (M2) | Placement has more leverage, but the thermal range is small. Mechanism UNRESOLVED |

Both preregistered tests reach the same decision: **no material value beyond power balancing on the homogeneous twin.** E12 suggests that, where placement has full leverage and loads are light, the frozen thermal heuristic produces a small, consistently directed reduction in hottest-rack temperature. It is far below materiality, and the evidence is fragile (about 2 conditions; I2).

E12 does **not** confirm E11 for high-power regimes, and E11 does not invalidate E12's descriptive ordering. Neither experiment supports thermal-aware placement as materially useful on this twin, and neither shows that thermal information is useless in general.

---

## 8. Overall progress (evidence-backed; percentages are approximate judgements, not counts of plan tasks)

| Area | Status | Evidence | Remaining |
|---|---|---|---|
| Environment, core and backend; Task 1.5 closeout | Completed | C1 checkpoint and review; option-B closeout; the historical physical-response test remains **strict XFAIL** (not a pass) | none |
| Three-FMU selection; G1/G3 physics (C1) | Completed, reviewed | X01, E01, E03 (G3 NOT_USABLE, 0.538986 °C) | none |
| Closed-loop integration and invariants (C2/E10) | Completed; accepted with conditions | C2 review | none |
| Metrics, reporting and visualisation infrastructure | Completed | Tasks 10–11; D5 loader; C′ adapter; 189 tests | demo labelling of figures |
| Synthetic matrix (C3/E11) | Completed; accepted with conditions (negative) | C3 review | none |
| Alibaba mapping, workloads, preregistration | Completed; prelaunch accepted; all launch conditions met (regime record, queueing test, lightweight check, C′ adapter) | prelaunch review; `18dfea1` | none |
| E12 execution, recovery, C′, C4 | **Completed; review = this document** | §§4–6 | conditions C1–C3 |
| Task 15 replay | Not started; GIF fallback exists (needs labels) | — | optional, time-boxed |
| Task 16 / C5 | Conditional, not applicable (G3 NOT_USABLE); **C5 non-execution note not yet written** | E03 | a one-paragraph note |
| Task 17 packaging | **Incomplete (not started)** | — | results note, runbook, `DEMO.md`, D7 decision, D8 wording, backup |

**Separate assessments:**
1. **Implementation and integration: ≈ 90–95 %** of the approved scope. All pipelines are built and tested. What remains is optional viewer export and runbook polish.
2. **Scientific validation and supported claims: ≈ 90 %.** Every preregistered gate has an answer: G1, G2, G3, G4 synthetic and G4 Alibaba. What remains is writing them up without overclaiming.
3. **Reproducibility and auditability: ≈ 60–70 %.** Strong provenance and hashing, and one full 6 h C′ repeat. Not yet: a fresh-clone runbook, an off-machine raw copy, or a portability demonstration. Most configurations are unrepeated.
4. **Demo and presentation readiness: ≈ 50 %.** Assets exist but are not self-describing. The story must be reframed (below).
5. **Packaging and handoff: ≈ 20–30 %.** The checkpoints and READMEs are thorough. The Task 17 deliverables do not exist.

**Plainly:**
- **What we have built and established:**
  - a deterministic (verified within stated scope), FMU-backed, closed-loop RAPS ↔ POWER9-cooling testbed on Summit, with five placement policies, strict invariants, full provenance and preregistered evaluation;
  - two preregistered negative G4 results;
  - evidence that placement changes the spatial thermal distribution at identical power.
- **What the negatives change:** the demo cannot claim "thermal-aware scheduling cools hotspots" as a validated benefit. The credible story is: *a rigorous digital-twin testbed that can answer such questions, and the honest answer on a homogeneous liquid-cooled twin is "not materially, beyond power balancing"; the small E12 ordering is a lead, not a result.*
- **Uncertain or unproven:**
  - mechanisms (M3);
  - whether any regime yields material value;
  - portability;
  - repeatability of most configurations;
  - real-hardware relevance.
- **Required to finish:** Task 17 deliverables, the C5 note, conditions C1–C3, and a D7 decision.
- **Optional research expansion, not required:** a replay viewer, more seeds or workloads, heterogeneous twins, RL, surrogates, mechanism studies.

---

## 9. Allowed versus unsupported claims

| Allowed (with stated scope) | Unsupported |
|---|---|
| The FMU-backed closed loop runs with all six invariants enforced. Determinism is verified for E10 packing (2 h), the E11 seed-1 packing/PB 2 h prefixes and E12 TP seed 1 (6 h, byte-identical). | "The whole matrix is reproducible"; "portable across machines". |
| Under both preregistered G4 tests (synthetic and Alibaba-derived), thermal_predictive showed **no material value beyond power balancing on the homogeneous twin** (largest per-seed PB−TP 0.34 and 0.18 °C, against 0.5). | "Thermal-aware placement works", or "is useless in general". |
| In E12 (small, low-density, bursty jobs), TP had the lowest and packing the highest time-mean max-rack temperature in all three seeds (PB−TP 0.08–0.18 °C, packing−TP 0.35–0.44 °C). This is below materiality, with ≈ 2 independent conditions. | "TP reduces hotspots by 0.4 °C"; any significance claim; generalising to E11's regime. |
| Placement changes the rack-temperature distribution at identical IT power and timing: S1 differences per metric and per experiment. | Generalising S1 across metrics. In E11 packing ≈ TP on the primary metric. |
| G3 room-air lever NOT_USABLE (0.539 °C); the what-if was not run. | Any degraded-cooling result. |
| Coolant is modelled; 45 °C and t_hot are references. | Hardware temperature, safety, PUE, energy savings, carbon, lifetime, RL, surrogate, heterogeneous-zone or causal-mechanism claims. |
| Summit's rack temperature depends on facility load and on the placement of other load (I1, M3; the D8 wording). | "Weak rack-to-rack coupling" without the D8 correction; an identified mechanism. |

---

## 10. Required conditions and next steps

**Conditions for accepting C4:**
- **C1 (Bipin).** Ratify or qualify the recovery interpretation in a dated plan addendum: "dont stop, resume wherever it stopped" interpreted as reuse 4, restart 3 once, run 8, then 1 repeat (19 attempts), with orchestration-only source changes. Note that `recovery_approval.json`'s `approved_by` reflects that instruction, not a review of the accounting or the diff.
- **C2 (Task 17 wording).** Use the E12 ordering statement from §9 together with the seed-correlation caveat (I1, I2). Keep C3's "packing ≈ TP" for E11 only.
- **C3 (before any demo use).** Produce demo-labelled re-renders of existing figures from existing ledgers, without overwriting originals: experiment, workload, seed, window marker, scale note, "descriptive; G4 negative" caption, and a caption for GIF frame 0 (V1–V3, V5).

**Smallest useful next bounded assignment** (documentation and offline only; zero simulations):
1. Add the C1 addendum (after you have provided the text).
2. Write the C5 non-execution note: G3 numbers and the 62-parameter list; the what-if was not run.
3. Write the Task 17 results note covering X01, G1, G3, G4 for E11 and E12 with the §9 wording; invariants; reproducibility scope; spec §8 verbatim plus the D8 correction; and the limitations.
4. Write `experiments/DEMO.md`, mapping each asset to the claim it supports, with captions.
5. Produce labelled demo copies of the figures (offline, from existing ledgers on Arch).
6. Write a runbook that separates **executed** commands from **reproduction** commands, with wall times and memory notes.
7. Make an off-machine raw-data copy with a checksum verification record.
8. Optional O1 prefix check (read-only).
9. Stop for final review.

**Decisions for Bipin:**
- **C1 ratification.**
- **D7:** Task 17 Step 4's fresh-clone obligations. Options:
  - **(a)** fresh clone on Arch, `uv sync --frozen`, non-FMU tier, plus input and FMU hash verification, and **no** simulation;
  - **(b)** (a) plus the existing short FMU smoke;
  - **(c)** (a) plus one E11 TP seed-1 6 h rerun, about 20 min. This is cross-version (`runner.py` changed after `6ee93c4`) and would extend reproducibility to a high-power regime.

  **I recommend (a) or (b).** (c) is optional, not required for the approved scope.
- **Task 15:** defer, or time-box to 1 day after packaging. The labelled GIFs are an adequate fallback.

**Explicitly deferred (optional research):** more seeds or workloads, heterogeneous or degraded-cooling twins, a G3 lever redesign, mechanism studies (M3), RL, surrogates.

**Is more simulation necessary to finish the current scope? No.** Only D7(b) or (c) would add any, and both are optional.

---

## 11. Read-only commands for Sol, if raw verification is wanted (Arch)

Run from `thermoRL/thermorl-v2`:

```bash
# Re-hash every raw file against the committed inventories (no writes):
python - <<'EOF'
import json,hashlib,pathlib
E=pathlib.Path('experiments/summit/E12_g4_alibaba')
for inv,base in ((E/'results/run_files.json',E),(E/'provenance/rerun_1/run_files.json',E/'provenance/rerun_1')):
    d=json.load(open(inv)); bad=[k for k,v in d.items() if hashlib.sha256((base/k).read_bytes()).hexdigest()!=v['sha256']]
    print(inv,len(d),'mismatches',bad)
EOF
# O1 cross-generation prefix (descriptive only):
python - <<'EOF'
import pathlib
E=pathlib.Path('experiments/summit/E12_g4_alibaba')
for name,arch in (('thermal_predictive_seed1','failed_20261030T204726_816159Z'),('packing_seed2','failed_20261030T204726_700443Z')):
    a=(E/'provenance'/arch/name/'decisions.jsonl').read_bytes().split(b'\n'); b=(E/'runs'/name/'decisions.jsonl').read_bytes().split(b'\n')
    full=[l for l in a[:-1]]  # drop a possibly truncated last line
    print(name,len(full),'prefix identical:',full==b[:len(full)])
EOF
# V3 check: first TP decisions' logged t_c identical at six decimals?
python -c "import json;r=[json.loads(l) for _,l in zip(range(3),open('experiments/summit/E12_g4_alibaba/runs/thermal_predictive_seed1/decisions.jsonl'))];print([len(set(x['t_c'])) for x in r])"
```
