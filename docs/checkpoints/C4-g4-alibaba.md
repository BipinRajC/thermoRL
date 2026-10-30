# C4 — E12 G4 on the Alibaba-derived workload

**Date:** 2026-10-31 IST. **Branch:** feat/parasparam-demo. **Status:** Task 14 complete; STOP for Bipin/Opus review.

**Frozen outcome: no material value on the homogeneous twin; value_beyond_power=false.**

Original launch SHA `18dfea14aa42bc21a191cc1f9a39fc421d8723bd`; recovery launch SHA `e0e1522ac52b5780cb3088232051e26dbd492804`. Recovery interpretation was committed at `f7cde7b`; tested engineering/preservation at `e0e1522`. Result/checkpoint commit is the commit containing this file. [E12 README](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/README.md) contains all metrics, diagnostics, attribution, exact commands and operational evidence.

## Frozen G4 result

| Policy | Seed 1 maxrack_mean_c | Seed 2 | Seed 3 |
| --- | --- | --- | --- |
| packing | 41.410869466295 | 41.345774966856 | 41.308922026266 |
| node_balance | 41.256918573934 | 40.969725531173 | 41.128894157054 |
| power_balance | 41.235138269180 | 40.981985391462 | 40.994658462517 |
| coolest_rack | 41.164820218149 | 41.239750477448 | 41.095216301964 |
| thermal_predictive | 41.057548338400 | 40.904720549522 | 40.885866893341 |

| Seed | PB minus TP (°C, full precision) | Packing minus TP (°C, full precision) |
| --- | --- | --- |
| 1 | 0.17758993078025043 | 0.35332112789507875 |
| 2 | 0.07726484193952388 | 0.441054417333838 |
| 3 | 0.10879156917675914 | 0.42305513292543395 |

Threshold is PB−TP≥0.5°C in every seed on maxrack_mean_c over strict 3600<t_s<=21600. Full precision, not the displayed table rounding, decides. S1 does not replace the rule.

## Validation and directly measured reproducibility

**FACT — C′ direct verification covers TP seed1 only.** Full 7200 s warm-up, 2160 steps and 21600 s elapsed were verified in both fresh processes. Config, workload, sidecar, FMU, source maps, Git SHA and environment matched exactly. Canonical decisions were byte-identical and complete interval values were equal with check_exact=True. Interval-file, job-event and thermal-publication bytes also matched (information only). Timing values were excluded from deterministic comparison, while row joins and hashes remained valid. The SHA-sealed evidence marks only TP seed 1 verified_E12; the other 14 are inherited_not_remeasured under "E10 synthetic packing seed1 2h only; weak cross-workload evidence". The entire matrix was not independently repeated. No A′ fallback or equality/tolerance change occurred.

All three seed gates passed: identical job starts, total IT power within 1e-6 kW, exact/free/distinct allocation and lifecycle replay, per-rack sum reconciliation, independent 2160-step/21600 s clock, complete provenance/ledger joins, and the accepted scoped C′ evidence. Maximum cross-policy IT-power difference is 1.8189894035458565e-12 kW in each seed. See [invariants](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/results/invariants.json), [comparison](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/full_rerun_comparison.json) and [sealed evidence](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/determinism_evidence.json).

## Offered versus realised utilisation and queueing

| Seed | Offered window utilisation | Realised ledger utilisation | Started | Censored | Wait mean s | Wait p95 s | Wait max s | Peak queued jobs (episode) | Queued fraction (evaluation ticks) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.48576559317193224 | 0.4856178844213863 | 21885 | 0 | 8.621865745 | 38.150916804 | 290.095277413 | 694 | 0.031666667 |
| 2 | 0.4546186900899609 | 0.4545704232117981 | 19627 | 0 | 6.000436318 | 0.996434839 | 235.551878482 | 564 | 0.023888889 |
| 3 | 0.4566251349855959 | 0.4565686698371524 | 19789 | 0 | 6.129541603 | 0.997273608 | 237.425800645 | 577 | 0.022777778 |

Nominal construction rho is 0.6; offered window and realised ledger utilisation are distinct. Starts, waits and censoring are policy-identical by construction, with exact starts checked. Actual peak queues of 694/564/577 jobs and max waits ≈290.10/235.55/237.43s occurred in the accepted periodic burst regime. Zero censoring does not mean zero queueing. E12's own endpoint max-rack/job attribution, S1 metrics, rounded-context disagreement/self-reproduction and joined timing-ledger latency are tabulated in the README and full results; none substitutes for G4.

## Recovery, attempts, runtime, storage and source generations

**FACT — launches and attempts.** Original launch `18dfea14aa42bc21a191cc1f9a39fc421d8723bd`; recovery launch `e0e1522ac52b5780cb3088232051e26dbd492804`. Four completed seed-1 non-TP runs retain the original SHA and unmodified manifests. The other eleven selected primaries and the one repeat use the recovery SHA. The only production-source delta is `run_matrix.py` and `e12_evidence.py` orchestration/accounting; all numerical decision, workload, power, thermal, metric, input, FMU and RAPS paths are unchanged. Full source-map comparison, including the runner's additional RAPS entries, is recorded in [source identity verification](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/recovery_1/source_identity_verification.json).

Cumulative accounting is **19 attempts = 15 selected successful primaries + 3 preserved interrupted primary attempts + 1 successful planned repeat**. The primary journal has 18 starts/15 completions; the repeat has its own journal. Reusing 4 complete runs, restarting 3 interrupted configurations and executing 8 previously unstarted configurations produced the selected 15; no additional retry occurred. The interrupted TP seed 1, packing seed 2 and node_balance seed 2 directories were moved exactly once; their original console logs remain in place. [Historical inventory](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/interruption_inventory.json), [relocation inventory](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/recovery_relocation_inventory.json), [primary file inventory](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/results/run_files.json), [repeat inventory](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/rerun_1/run_files.json), and [portable manifests](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/manifests/) make preservation traceable. Completed raw run directories exceed 25 MB and remain local/ignored; interrupted archives remain ignored and inventoried regardless of size.

**UNRESOLVED — interruption origin.** The original interactive controller exited 143/SIGTERM around 45 minutes after first launch; exact origin is unknown. An interactive lifetime limit is an INFERENCE, not a proven cause. No FMU failure file, traceback or scientific stop was observed. Bipin's actual instruction was "dont stop, resume wherever it stopped". The 19-attempt accounting and restart scope are the agent's bounded operational interpretation recorded in C4-execution-recovery, not a separately supplied count or Opus approval of this source diff.

Durable user units `thermorl-e12-recovery-20261030T2050Z` and `thermorl-e12-postmatrix-20261030T2123Z` use RuntimeMaxSec=infinity, Restart=no and RemainAfterExit=yes. The second waited for successful primary exit, used the guarded repeat CLI, generated evidence, then ran the offline report. No source change or Git commit occurred from recovery launch through successful C′ evidence generation.

Original first-wave process walls (packing, node_balance, power_balance seed1): 1263.783793608, 1289.237131012, 1318.495860319 s. Recovery first-wave process walls (node_balance seed2, packing seed2, TP seed1, in completion order): 1245.809995674, 1323.944600355, 1688.275010045 s. These are individual process durations, not a sum or matrix duration. Recovery controller wall: **5033.356971426 s**, 11 completions. Original-start to final-primary-completion span: **9565.744325 s, including interruption/recovery downtime**. Primary systemd service ran 20:49:35–22:14:00 UTC; its startup/skip validation is outside the execute_jobs controller timer. The planned repeat took **1479.362240931 s** by guarded repeat subprocess-plus-validation timing and 1470.616880302 s by EpisodeRunner.

Selected-primary process peak RSS range: 1.630260–1.990356 GiB; interrupted-process RSS is unknown. Recovery controller own lifetime peak: 1.356224 GiB. Primary service cgroup high-water (controller plus concurrent workers): 6.925251 GiB. Repeat simulation own peak: 1.992161 GiB; its validating guard own peak: 1.304073 GiB. Offline report wall: **458.675731 s** after imports, with own lifetime peak **4.979103 GiB**, at most one five-policy seed loaded. The follow-up service cgroup high-water was 6414262272 bytes (5.973747 GiB), spanning the guarded repeat, comparison and report. Both services exited successfully with zero restarts and remain available for inspection. Service memory and process RSS have different scopes.

Raw storage: selected primaries **3044923184 bytes**, interrupted archives **326105782 bytes**, repeat **229356244 bytes**; all raw files are inventoried. Report artifacts/logs have a separate final inventory. All 15 primary episodes and the repeat recorded zero coolant samples above 70°C and no negative episode pump samples; threshold counts are descriptive, not a new stop rule.

## Exact commands and tests

```bash
# Original interactive primary launch (interrupted):
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3
# Recovery under the recorded durable systemd unit:
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3 --retry-failed
# Guarded follow-up, alone after successful primary completion:
uv run python -m thermorl2.experiments.e12_evidence rerun --config thermorl2/experiments/configs/g4_alibaba.yaml
uv run python -m thermorl2.experiments.e12_evidence generate --config thermorl2/experiments/configs/g4_alibaba.yaml
uv run python -m thermorl2.experiments.report experiments/summit/E12_g4_alibaba --evidence experiments/summit/E12_g4_alibaba/provenance/determinism_evidence.json
# Allowed tests, before source freeze:
uv run pytest tests/unit tests/integration -q
# Supplemental ledger-only diagnostics and final audit were run from /tmp;
# byte-identical scripts are archived under provenance/recovery_1/.
uv run python /tmp/e12_extra.py
uv run python /tmp/e12_final_audit.py
```

Exact service invocations/settings and sequencing are in `provenance/recovery_1/service_launch.json`, `post_matrix_service_launch.json`, `post_matrix_driver.py` and their journals. Preservation and freeze scripts are archived there too. Dataset command: `sha256sum -c checksums.txt` from datasets/alibaba_gpu_2023, 26/26 passed. Fresh non-FMU tier: **161 unit + 28 integration = 189 passed in 30.93 s**. No new full FMU pytest tier was run.

## Scope and interpretation limits

E12 tests only small (1–2-node), low-density, bursty Alibaba-derived jobs on the homogeneous Summit FMU. Nominal construction rho is 0.6; finite-window offered and realised utilisation are separate quantities above. Approximately 23 minutes dense plus 80 minutes near-silent occur per 1.74-hour cycle. Seed 3 is seed 2 shifted by 33.03657272057935 s after 162 leading pods: approximately two independent workload conditions, not three independent replications or a determinism test. A negative result does not confirm E11 for high-power regimes; a positive applies only to this tested regime.

A2: timestamps are assumed seconds; deletion minus creation is interpreted as runtime even for Running/Failed pods. Runtime clips remain 2033 floors and 266 caps among 6203 eligible pods. A3: arrival-only compression 2063.712860793521×, artificial cyclic wrap, empty start and correlated rotations change arrival/runtime relationships. A4: static CPU/GPU mapping assumes 20 cores/socket; about 99.3% of jobs use one node and the maximum is two. Actual loss-inclusive mean above-idle rack inputs are about 2.990621/2.787416/2.797622 kW; the pre-run mapping estimates 2.8720/2.6763/2.6862 kW were loss-exclusive offered statistics with a different definition.

M2: E11's large-job max-rack domination is not assumed here. E12 endpoint identities and resident jobs are derived separately in the E12 README and attribution record; coexistence does not establish causation. No individual E12 job fills a rack. M3: non-local placement dependence was observed in earlier work, but its physical mechanism remains unresolved.

S2, verbatim: published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.

Warm-up is capped at 7200 s and is evolving, not settled. G1 remains a frozen heuristic, not a validated predictor. Between-tick committed job increments retain the documented roughly 4% loss understatement; actual FMU inputs are loss-inclusive RAPS rack powers. No correction or refit was made. Forty-five °C and G1 t_hot are references, not validated safety limits. Temperatures are modelled coolant, not hardware measurements. No PUE, plant-total energy, carbon, lifetime, heterogeneous-zone, causal-mechanism, RL or surrogate claim follows.

C3 is unchanged: **no material value on the homogeneous twin**, value_beyond_power=false; packing≈TP on the primary metric. E11 PB−TP gaps remain 0.3424946761284602, −0.14719002809689385, −0.07086450347454587 °C. S1 differences remain metric-specific. E11 reproducibility remains Option A: E10 packing seed1 2h fresh-process evidence plus exact E11 seed1 packing/PB two-hour prefix checks; no independent six-hour E11 run and no E11 temperature-reading policy repeat. D7 remains deferred and no E11 rerun was performed.

## Final review boundary

Review the frozen G4 result and full five-policy metrics; per-seed invariant and C′ seal/reference evidence; TP seed 1-only direct scope; correlated seeds and low-density/bursty regime; observed queues, waits and own attribution; interruption preservation, generic-instruction recovery interpretation, mixed launch SHA proof and complete 19-attempt accounting. Raw files remain local/ignored and are inventoried; obtain them separately for full-data review. No E11 rerun, extra research experiment, full FMU pytest tier, RAPS patch, RL, surrogate or Tasks 15–17 work was done.

**STOP at C4.** Push this same branch and await Bipin/Opus before any next task.
