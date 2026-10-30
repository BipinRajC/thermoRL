# C4 prelaunch status — Alibaba-derived inputs and protocol

**Date:** 2026-10-30. **Branch:** feat/parasparam-demo. **Status:** inputs/protocol prepared for review; execution pending approval and the E12-specific C′ evidence adapter. This is **not** the C4 G4-results checkpoint. No E12 policy simulation or E11 rerun was performed.

## Completed and commits

- `75363ee`: Task 13, test-first Alibaba loader/mapping/cyclic generator, kind dispatch, launch config, approved D2–D6 addendum, default-only variant/power record and 26-file Arch checksum verification. Plan message: `feat(workload): Alibaba GPU 2023-derived workload (documented mapping, rate-scaled arrivals)`.
- `20ff68f`: D5 metric-neutral per-seed report loading; shared metric code and existing build_report API retained; CLI scratch/metrics-only support; weak-reference test proves at most five loaded Run objects; E11 regeneration and byte-identity proof committed.
- `ababba8`: E12 preregistration and three immutable workload/sidecar pairs, committed before any policy run.
- This checkpoint is committed separately after preparation. All unrelated local document deletions and prompt files are preserved and excluded.

[E12 README](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/README.md) · [config](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/config.yaml) · [preregistration hashes](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/preregistration.json).

## Approved source, runtime and arrival rules

**D2:** default only. multigpu50 lacks pod_phase/creation/deletion, so it has descriptive resource statistics only. No inferred timestamps, phase join or outcome-based variant selection.

**D3 / A2:** deletion−creation interpreted as seconds for all non-Pending GPU>0 pods, including Failed/Running; clip [300,21600], assert integer without rounding; limit=ceil(1.5R). Default has 8152 raw rows and 6203 eligible pods: Running 4149, Failed 1869, Succeeded 185. Source duration min/median/max: 4 / 723 / 12537496 s. Exactly 2033 (32.774464%) are floored and 266 (4.288248%) capped. Units and deletion semantics for Running/Failed remain explicit assumptions.

**D4 / A3:** stable (creation_time, original row) sort. Cyclic incoming gaps [mean original IA, diff creation], one default_rng(seed) offset. First chosen pod waits its incoming gap; zero gaps and row ties remain. Target IA=exact E[nodes×clippedR]/(0.6×4626); scale=mean original IA/target; divide gaps by scale and accumulate submits<horizon. Admission ceil(submit), no runtime compression. Mean original IA=2080.258143 s, target=1.008017 s, compression=2063.712861×. Nominal elapsed-time cycles=3.454491. Actual normalized row passes vary with start rotation. Seeds are correlated rotations, not independent draws.

**A4:** source jobs have max two nodes; approximately 99.3% are one-node jobs. Runnable node-weighted GPU utilization is 0.878/6 and CPU 0.459/2. Twenty cores/socket and static resource-to-power mapping are assumptions. Lower power density may weaken thermal contrast; no mapping/power/workload tuning is performed.

## Workloads and material utilisation finding

| Seed | Jobs | Offset | Normalized pod passes | Offered utilisation (3600,21600] | Workload SHA-256 |
|---|---:|---:|---:|---:|---|
| 1 | 21885 | 2935 | 3.528132 | 0.485766 | `7415a80132d0bcf993071b30bfdc586803c848e1ab582bc9730a71dfddab4c2c` |
| 2 | 19627 | 5195 | 3.164114 | 0.454619 | `28250b8c8834f281aa0cb56d35cb28d550fde05d01b8b36756116211f7fd8ead` |
| 3 | 19789 | 5033 | 3.190231 | 0.456625 | `1e09de8c6573a2474d38f7660da0126a4ce24919b3ba8a8ff1255fc5ad09b904` |

**FACT/DERIVED — needs review before execution:** the real-source finite-window offered projections are below the nominal 0.6 and original 50–70% aspiration (also below the inline-fixture ±15% band). The required inline fixture passes its utilisation test. No claim is made that the real traces satisfy that band. Rho=0.6 remains the exact long-run cycle-average input; it does not guarantee a six-hour empty-start average. The projection includes continuous arrival/lifetime horizon overlap, not RAPS queueing/admission/completion effects. No rescaling, reseeding, horizon or runtime adjustment was made.

A separate vectorized reconstruction from the raw CSV matched every generated submit, resource mapping, runtime and limit exactly, including the first excluded arrival. Sidecars pin horizon 21600, generator/source hashes, phase/clip statistics, ordering hash, lineage, RNG rule and versions. Parquets and sidecars are SHA-keyed and pinned by config.by_seed. [Verification](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/verification.json).

## Descriptive power and D5 feasibility

| Population | Pods | Nodes | Mean incremental kW/node | Share node GPU utilization ≥2 |
|---|---:|---:|---:|---:|
| Default runnable | 6203 | 6247 | 0.319982 | 0.018889 |
| Default resource-only, no phase filter | 7064 | 7108 | 0.316042 | 0.016742 |
| multigpu50 resource-only, phase unknown | 7973 | 8529 | 0.476608 | 0.180560 |

These are node-weighted static RAPS-model increments above idle, network zero and loss-exclusive, not measured pod/rack power. Unweighted pod means and schemas are also preserved. [Variant record](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/results/variant_choice.json) was committed before any policy run.

D5 estimates from E11 row formats and the offered job counts:
- Canonical decision files: about **160.9–214.8 MB per run**, **2.840 GB** for the primary 15, plus **0.215 GB** for C′; other ledgers/intervals are additional. These estimates assume all offered jobs start, and are not measured E12 output sizes.
- Decoded Python decision payload about 29 kB/row. Estimated loaded payload **9.429 GiB all15**, versus **3.027–3.353 GiB per seed**, before allocator/import, parsing, counterfactual and GIF overhead.
- Arch snapshot: about 15.31 GiB total RAM and 6.34 GiB available. No E12 report-memory benchmark was run. Keep sequential report seed loading after simulations finish; three simulation workers remain the planned cap.
- E11 scratch regeneration under the refactor produced a **byte-identical metrics.csv**, both SHA `06cf0b3e9705a74549a0b1f3b97a34a92ec3e841d0292792b16c19019d44c43c`. Measured E11 scratch peak RSS **1.534 GiB**, not an E12 RAM measurement. Original E11 artifacts were not overwritten.

[Feasibility detail](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/results/feasibility.json) · [D5 exact-byte proof and command](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/report_loading_verification.json).

## E12 preregistered protocol and C′ scope

Future primary matrix: five frozen policies × seeds1–3, rho0.6, Summit, 6h, nominal290K, 10s ticks, 7200s **capped/not settled** warm-up, 2160 episode steps per run, three workers. Config copy is byte-identical to launch config. G1, primary.yaml, policy definitions, spanning, thresholds and physical assumptions are unchanged.

Primary rule unchanged: mean per-tick max-rack coolant over **3600 < t_s <= 21600**, PB−TP ≥0.5 °C in **every seed**, otherwise "no material value on the homogeneous twin". S1 remains descriptive, not an alternate success criterion. M2/M3, assumptions A2–A4, censoring, mixed interval semantics, latency precision and carry-forward limitations are in the README before any outcome.

**Selected D6=C′:** future **15 primary runs + one fresh-process 6h TP seed1 rerun**, same config/workload/environment and full warm-up, canonical full-file byte identity and exact interval values. Timing measurements are excluded from byte comparison but must retain valid joins/hashes. `verified_E12` may cover **TP seed1 only** after it passes; all other policy/seed configurations remain explicitly inherited and unrepeated. A failed measured repeat invalidates G4, with no fallback to A′. No E11 synthetic-prefix check is a valid Alibaba prefix test.

The extra raw run is planned at `provenance/rerun_1/runs/thermal_predictive_seed1/`, ignored by the existing runs rule, with its own file inventory/linked manifest; it must not enter the primary metrics table. [Scope](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/provenance/determinism_scope.json) records observed_result=null and zero currently authorized policy runs.

**Task14 engineering prerequisite, not a new scientific decision:** implement/test E12-specific C′ evidence generation and reporting acceptance before execution. Current evidence.py / approved_determinism are E11-specific and must not be invoked unchanged on Alibaba. The per-seed metric loader is ready; C′ adapter work is deliberately deferred to the separately authorized execution phase.

## Verification and exact commands

`sha256sum -c checksums.txt` from `datasets/alibaba_gpu_2023`: **26/26 passed**.

From `thermoRL/thermorl-v2`:

```bash
uv run pytest tests/unit tests/integration -q
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --prepare-variant
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --seed 1 --prepare-workload
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --seed 2 --prepare-workload
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --seed 3 --prepare-workload
```

**126 unit + 27 integration = 153 passed (29.10 s).** Tests use inline CSVs/temporary engineering fixtures; no E12 policy simulation. No full pytest/FMU tier was run. Scope verification confirms zero E12 run directories/journal/thermal-results files, protected paths unchanged, import boundaries correct, three caches independently matched and all pinned inputs unchanged. D5 scratch command is recorded in its proof; it reads old E11 ledgers only.

## C3 wording carried forward

C3 remains a valid negative primary result. Packing−TP on that metric was +0.0823, −0.1078, +0.2761 °C, so a primary-metric "packing hotspots removed by TP" headline is unsupported. S1 temperature std/top-decile differences are metric-specific; power std, spread and p99 must not be generalized. No new result is inferred from E12 preflight.

Prior reproducibility claim remains scoped: "Fresh-process reproducibility was verified for E10 packing seed 1 (2 h) and, by exact prefix reproduction, for E11 seed-1 packing and power_balance over the first 2 h; no 6 h E11 configuration and no temperature-reading policy was repeated."

S2, verbatim: published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.

## Stop and required review

**STOP at C4-prelaunch.** Review the under-target finite-window workload regime, preflight feasibility and the frozen C′ protocol. After approval, the bounded next assignment can cover Task14 C′ adapter/tests, the 15+1 execution and C4 report. No execution is authorized by this checkpoint.

No E12 simulation, E11 rerun, full FMU pytest, Task15–17, RAPS patch, policy/G1/spanning/rho/seed/horizon/warm-up change, characterization, predictor selection or RL work was performed. Unrelated working-tree changes were preserved.
