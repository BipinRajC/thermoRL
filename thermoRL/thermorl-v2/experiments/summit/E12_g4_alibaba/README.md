# E12 — G4 on an Alibaba GPU 2023-derived workload
**System:** summit  **Status:** preregistered; inputs/protocol prepared for review, execution not authorized.
**Pre-registered:** 2026-10-30, commit `ababba8220c2143c67a588a2fdc2d6e1062d9a4d`, after Task 13 `75363ee` and D5 `20ff68f`; before any E12 policy run.

## Question
Does the frozen thermal_predictive heuristic demonstrate material value beyond power_balance on the approved Alibaba-derived workload under the same G4 protocol?

## Pre-registered decision rule
**Value beyond power** if `thermal_predictive` is ≥ 0.5 °C lower than `power_balance` in every seed. Otherwise: "no material value on the homogeneous twin". Also report the packing − thermal gap.

Only **maxrack_mean_c**, the time mean of per-tick maximum rack coolant °C over **3600 < t_s <= 21600**, decides G4. Each seed must meet PB−TP ≥ 0.5 °C at full precision. No mean-across-seeds, alternate policy, secondary metric, threshold or workload tuning replaces this rule. Any measured invariant failure makes G4 INVALID pending review.

### D6: selected C′ determinism scope
The future experiment consists of **15 primary runs plus exactly one fresh-process six-hour thermal_predictive seed-1 rerun**, with full canonical decisions.jsonl byte identity and interval values exactly identical. The measured timing ledger is excluded from byte comparison; its join/hash validity still applies. Every process uses the same frozen inputs and a full capped 7200 s warm-up.

Direct `verified_E12` status may apply **only to thermal_predictive seed 1**, after the comparison passes. All other 14 primary policy/seed configurations remain `inherited_not_remeasured`, relying on E10's synthetic packing seed-1 two-hour evidence; this is weak cross-workload inheritance, not Alibaba reproducibility verification. No E11 synthetic-prefix comparison applies to E12. Any failed measured repeat or invariant invalidates G4; do not fall back to inherited-only A′ after failure.

[Machine-readable scope](provenance/determinism_scope.json) contains requirements and planned per-configuration statuses, with observed_result=null. The current E11 evidence generator/gate is not C′-compatible: **Task 14 must implement and test the E12-specific adapter before execution.** No policy simulation or rerun is authorized in this prelaunch assignment.

## Configuration
[config.yaml](config.yaml) is byte-identical to `thermorl2/experiments/configs/g4_alibaba.yaml`. It includes the three immutable workload/sidecar SHAs via workload.by_seed. System and predictor remain pinned through primary.yaml and G1.

- Summit, 257 racks × 18 nodes = 4626 nodes, six GPUs/node, power/communication interval 10 s.
- Five frozen policies × seeds 1, 2, 3: packing, node_balance, power_balance, coolest_rack, thermal_predictive. Three workers for the primary matrix; fresh OS process per run, one FMU per process.
- 6 h episode, 7200 s **capped, not settled** warm-up at RAPS loss-inclusive idle; 2160 episode steps; nominal 290 K ambient. RAPS cooling off, output none, noui, FCFS/head-of-line/no backfill, frozen spanning and committed-power semantics.
- Input rho=0.6 is the long-run cycle-average target derived from exact E[nodes×clippedR]. It does not promise a finite empty-start window at 0.6.
- G1 parameters unchanged: a=27.9753857271229, b=0.8052450824355937, tau=4050 s, H=600 s. Summit FMU SHA `0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233`.

| Seed | Jobs | Offset | Pod-count passes | Offered utilisation | SHA-256 |
|---|---:|---:|---:|---:|---|
| 1 | 21885 | 2935 | 3.528132 | 0.485766 | `7415a80132d0bcf993071b30bfdc586803c848e1ab582bc9730a71dfddab4c2c` |
| 2 | 19627 | 5195 | 3.164114 | 0.454619 | `28250b8c8834f281aa0cb56d35cb28d550fde05d01b8b36756116211f7fd8ead` |
| 3 | 19789 | 5033 | 3.190231 | 0.456625 | `1e09de8c6573a2474d38f7660da0126a4ce24919b3ba8a8ff1255fc5ad09b904` |

**Prelaunch review issue — utilisation.** The approved, untuned generator produces continuous offered-node utilisation **0.485766 / 0.454619 / 0.456625** over (3600,21600]. These are below the original 50–70% aspiration and the inline-fixture ±15% band; the real traces are not claimed to satisfy that band. The inline fixture passes its requested utilisation test. The real projection accounts for continuous submits, clipped durations, empty start and horizon overlap, but excludes RAPS admission/completion bookkeeping and queueing. No rho, scaling, duration, seed or horizon was adjusted. Review operating-regime acceptability before authorizing execution.

### D2 source and descriptive power statistics
Default is fixed by Bipin, not selected from policy outcomes or from the larger resource requests in multigpu50. `default` has 8152 raw rows and 6203 runnable non-Pending GPU>0 pods. `multigpu50` has 9061 raw resource rows and lacks pod_phase, creation_time and deletion_time; no phase/timing join or imputation is performed.

Node-weighted incremental kW above idle, through the frozen RAPS node-power model (network=0, loss-exclusive; not measured pod power):

| Population | Pods | Mapped nodes | Mean incremental kW/node | Share nodes using ≥2 GPUs |
|---|---:|---:|---:|---:|
| Default runnable (phase filter) | 6203 | 6247 | 0.319982 | 0.018889 |
| Default resource-only (GPU>0, no phase filter) | 7064 | 7108 | 0.316042 | 0.016742 |
| multigpu50 resource-only (GPU>0, phase unknown) | 7973 | 8529 | 0.476608 | 0.180560 |

The resource-only populations are labelled separately from the runnable set. [Full variant record](results/variant_choice.json), including unweighted pod means, was committed at `75363ee` before any policy run. Dataset verification passed all 26 checksums on Arch; raw CSVs remain outside git. No source data was modified.

### D3/D4 and assumptions A2–A4
**A2 / D3 — lifetime as runtime.** Interpret creation/deletion as seconds. Keep Running (4149), Failed (1869) and Succeeded (185) non-Pending GPU pods. Use deletion−creation as modeled runtime regardless of phase; the semantics of deletion for Running/Failed pods are not independently established. This is a lifecycle-to-execution assumption, not a claim of measured runtime. Clip to [300,21600], assert integer (no rounding), time_limit=ceil(1.5R). Source runtimes are integer seconds. Floors: **2033/6203 = 32.774464%**; caps: **266/6203 = 4.288248%**. RAPS adds its common one-second completion occupancy. All phase and clip statistics are retained in metadata.

**A3 / D4 — arrival-only compression and cycling.** Stable sort by (creation_time, original file row). Incoming gaps are [mean(diff creation), diff creation]; zero gaps and file-row ties remain. Choose one default_rng(seed) source offset, then cycle in that order. First submit waits the chosen pod's incoming gap. Wrap gap equals mean original IA. Compute exact E[nodes×clippedR] across all mapped pods; target IA=E[nodes×R]/(rho×4626); scale=mean original IA/target IA; divide each gap by scale, accumulate submits<horizon, admit at ceil(submit). Mean original IA **2080.258143 s**, target **1.008017 s**, compression **2063.712861×**. Durations are uncompressed. Nominal elapsed-time cycles are **3.454491**; actual normalized pod-count passes depend on rotation, as shown above. Seeds are correlated rotations, not independent resamples. Original burst ordering is retained, while absolute arrival/runtime time-scale relationships and the artificial wrap are assumptions. Job id i maps to ordered pod (offset+i)%6203; ordering/source hashes are preserved.

**A4 — weak power-density regime.** Almost all source jobs map to one node (max two); node-weighted mean GPU utilization is **0.878/6** and CPU **0.459/2** per node. CPU mapping assumes 20 cores/socket; GPU sharing and resources are mapped by the fixed spec formulas. These are static modeled loads, not utilization traces or measured power. Lower power density and no rack-filling source jobs may yield weak thermal contrast. This is legitimate external-validity scope, not a reason to increase power, choose another variant, or tune outcomes.

## Method
**Preparation executed on Arch (no FMU/RAPS policy simulation):**

```bash
# repository root / datasets/alibaba_gpu_2023
sha256sum -c checksums.txt
# cwd thermoRL/thermorl-v2
uv run pytest tests/unit/test_alibaba.py -q
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --prepare-variant
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --seed 1 --prepare-workload
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --seed 2 --prepare-workload
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --seed 3 --prepare-workload
```

**Prospective Task 14 commands — NOT authorized or executed here:**

```bash
# cwd thermoRL/thermorl-v2; only after prelaunch review and C′ adapter tests
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3
uv run python -m thermorl2.experiments.run --config thermorl2/experiments/configs/g4_alibaba.yaml --policy thermal_predictive --seed 1 --run-dir experiments/summit/E12_g4_alibaba/provenance/rerun_1/runs/thermal_predictive_seed1
# Generate a separate SHA-sealed E12 C′ evidence file using the Task14 adapter.
uv run python -m thermorl2.experiments.report experiments/summit/E12_g4_alibaba --evidence experiments/summit/E12_g4_alibaba/provenance/determinism_evidence.json
```

Do not invoke the current E11-only evidence command on Alibaba data. Future rerun files live under provenance/rerun_1/runs/ (automatically ignored) and need their own byte/SHA inventory plus a linked manifest; preserve the primary 15-run inventory. Never overwrite any primary or rerun directory. The extra run is excluded from primary policy metrics.

Expected execution cost is uncertain; no E12 benchmark has run. E11's 15-run analogue took 79.11 min at three workers, but E12 has about 4–5× as many jobs and a different power regime. No horizon, worker or primary-system switch is inferred from this estimate. Record first-wave timings when execution is authorized.

### Invariants (all primary runs, per seed)
1. Identical total IT kW per tick (absolute tolerance 1e-6 kW) and identical job start times across policies.
2. Exact nodes_required distinct free nodes per decision; complete lifecycle and node-reuse replay from required SHA-recorded job events.
3. C′ scope above: one direct full-six-hour repeat for TP seed1 only, others explicitly inherited. Canonical full-file bytes and interval values exact; timing ledger measured and excluded from byte comparison. Failed measured evidence => INVALID, not fallback.
4. Sum rack kW equals RAPS power_df Sum every power tick (1e-6 kW).
5. Independently counted backend.step calls=2160, complete 10 s grid, backend elapsed clock=21600, full 7200 s capped warm-up.
6. Complete manifests, source/environment/config/FMU/workload/sidecar SHA provenance; canonical/timing row joins and hashes, required job-events file/hash. Config equals frozen per-seed selection.

Frozen policies, spans, G1, primary.yaml, rho, seeds, horizon, warm-up and workload construction are unchanged. Stop for non-finite coolant, FMU error, invariant failure, frozen-item change, RAPS patch need or unexplained test failure. Above-70 °C samples are reported, not a stop. Scientific failures cannot be retried without a separately recorded Bipin-reviewed override. No retry is authorized by this prelaunch record.

## Metrics
Primary: maxrack_mean_c over **3600 < t_s <= 21600**; 1800 right endpoints. p99 uses linear interpolation.

S1, descriptive only in the same window: time mean of population rack-temperature std (ddof=0); mean hottest ceil(0.1×257)=26 rack temperatures selected per tick; time mean of population rack-kW std; per-tick argmax rack (lower-index tie), rack shares and resident job IDs at the driving RAPS tick from job events. No S1 metric replaces G4 or is generalized to all thermal/power metrics.

Also retain p99 maximum, mean rack, spread, raw max, hot rack-seconds at frozen G1 t_hot=63.30492211035258 °C, THI_T below 0.10 at T_max=45 °C reference, pump/IT kWh, realised utilization, jobs started/censored, waits, disagreement, self-reproduction, decision latency and separate RAPS/FMU/total scopes. Warm-up/initialization samples are excluded. kw/free/counts are RAPS-t inputs; t_c/pump are t+Delta endpoints. IT energy sums held kW×Delta; pump energy uses right endpoints.

Wait=integer start−continuous submit. Unstarted jobs are censored and counted separately, including admissions outside the horizon; no zero wait imputation. Disagreement reapplies both scorers to the same six-decimal logged context with distinct reconstructed free-node IDs. Self-reproduction is separate and imperfect for near ties; no exact full-precision decision reconstruction is claimed. Latency comes only from the joined timing ledger; missing means missing and canonical null is never zero.

## Results
**No E12 policy outcome exists.** Only input preparation is complete. [Variant statistics](results/variant_choice.json), [workload/size/memory feasibility](results/feasibility.json), [checksum verification](provenance/dataset_verification.json) and [D5 byte-identity proof](provenance/report_loading_verification.json) are prelaunch artifacts.

The primary 15 canonical ledgers are estimated at **2.840 GB**, plus **0.215 GB** for the C′ rerun (decimal units), before interval/event/timing files. Estimated per-run canonical files: **160.9–214.8 MB**. All raw run directories will exceed 25 MB and must remain gitignored, inventoried by relative file path/bytes/SHA, with portable manifest copies. Do not reduce the 14-key canonical schema to fit git.

Parsed payload estimate: **9.429 GiB** for all 15 versus **3.027–3.353 GiB** for one five-policy seed, before allocator/import, parsing, diagnostic and GIF overhead. One-seed loading is implemented. E11 scratch metric regeneration was byte-identical to committed metrics.csv (SHA `06cf0b3e9705a74549a0b1f3b97a34a92ec3e841d0292792b16c19019d44c43c`), measured peak RSS **1.534 GiB** for that E11 validation. E12 memory figures are estimates, not measured E12 execution or report RAM.

## Plots
No E12 thermal plots yet. Future plots must say Alibaba-derived, use shared scales and retain the frozen primary outcome even if negative.

## Observations (FACT)
All 26 source checksums passed. Default only, 6203 eligible pods, fixed phase/runtime/arrival construction, three SHA-keyed workloads. No E12 simulation, E11 rerun or new characterization was performed. The real-trace finite-window utilisation shortfall is reported before execution, without tuning.

## Interpretation (INFERENCE)
This is an external-validity workload with substantial assumptions and weaker mapped power density. No thermal-policy ranking or value is inferred from preflight statistics. Seeds are rotations of one source cycle. The pending low-utilisation operating regime requires review, not silent rescaling.

## Conclusion and decision
**Inputs/protocol prepared for C4-prelaunch review; execution pending approval and the E12 C′ adapter.** E12 G4 is pending. Stop after the prelaunch checkpoint.

## Limitations
- A2–A4 above: undocumented time units assumed seconds; Running/Failed lifetimes used as runtime, substantial clipping; arrival-only ≈2064× compression, artificial wrap and repeated correlated rotations; static resource-to-power mapping, low GPU/CPU density and max-two-node jobs; lower finite-window offered utilization than the nominal long-run target.
- **M2:** rare large/full-power jobs can dominate max-rack temperature in E11; that observed composition must not be assumed for this very different max-two-node source. E12 attribution will describe its own hottest racks without treating coexistence as causation.
- **M3:** E10/E11 exhibited non-local placement dependence at matched own/total power; the mechanism remains unresolved. No new characterization is a prerequisite or authorized.
- published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.
- Capped warm-up is evolving, not settled; frozen G1 is a heuristic, not a validated predictor. Forty-five °C and G1 t_hot are references, not validated safety limits.
- C3 remains "no material value on the homogeneous twin" on its primary metric; packing≈TP there too. Distributional S1 statements are metric-specific and cannot be used as a substitute criterion.
- Prior reproducibility wording: "Fresh-process reproducibility was verified for E10 packing seed 1 (2 h) and, by exact prefix reproduction, for E11 seed-1 packing and power_balance over the first 2 h; no 6 h E11 configuration and no temperature-reading policy was repeated." E12's planned C′ repeat is not yet evidence.
- Six-decimal reconstruction cannot explain every live choice exactly; E11 self-reproduction was about 94.8% TP and 90.0–90.6% coolest_rack. Actual logged racks and rounded reconstructions are distinct.
- One homogeneous POWER9 twin, modelled coolant and power rather than production hardware measurements; only three correlated rotations. No PUE, plant-total energy, carbon, lifetime, heterogeneous-zone, surrogate or RL claims. G3 what-if remains dropped. No model, policy, fit, threshold or workload tuning.
- Summit between-tick committed job increments retain the documented roughly 4% loss understatement; actual FMU inputs use loss-inclusive RAPS rack power. No correction or G1 refit is made.
- Timing/canonical ledgers remain separate. Large raw data stays local/ignored with hashes and must be obtained separately for full-data review. Report/RAPS job volume is larger than E11; memory/runtime projections are uncertain.

## Provenance
[preregistration.json](provenance/preregistration.json) pins the byte-identical config, source module hashes, raw/derived inputs, sidecars, variant record and C′ scope before any outcome. Source CSVs and dataset version are hashed; no raw data was modified. Workload metadata records raw/filter phase mix, runtime clip counts/fractions, ordered source-row hash, offset/cycles, exact population expectation, representation, RNG draw rule, lineage rule, generator source SHA and numpy/pandas/pyarrow versions.

## Demo relevance
A preplanned external-validity test, not an attempt to rescue a positive thermal headline. Any eventual result must remain scoped to the frozen rule, mapped Alibaba-derived input and Summit FMU. Task 15–17 and every policy simulation remain outside this assignment.

## Prelaunch review addendum (2026-10-30)

Bipin approved E-A (proceed untuned) and E-B (keep the rotations) after review `5a0828b`; decisions are committed in plan addendum `f5d6dae`. Task14 now authorizes exactly 15 primary runs plus one isolated fresh-process TP seed1 repeat, after the engineering gates. This supersedes the historical prelaunch execution hold; all hashed protocol sections remain unchanged.

**Narrow regime:** small 1–2-node, low-density jobs with periodic bursts: approximately 23 minutes dense and 80 minutes near-silent per 1.74-hour cycle. A negative E12 does not confirm E11 for high-power regimes; a positive applies only here. No workload, policy, model, fit, threshold or timing parameter was changed.

| Seed | Arrivals per hour | Hourly mean offered utilisation | Window min/max | Exact time fraction >1 | Mean modelled kW/rack above idle | CPU cap clipping, pods |
|---|---|---|---|---:|---:|---:|
| 1 | 3278, 6195, 11, 6193, 21, 6187 | 0.2528, 0.3267, 0.4128, 0.5673, 0.4099, 0.7121 | 0.094250 / 1.150238 | 2.973093% | 2.872016 | 0.420379% |
| 2 | 1021, 6193, 12, 6195, 2178, 4028 | 0.0579, 0.3392, 0.2952, 0.5770, 0.3730, 0.6887 | 0.019023 / 1.123433 | 2.292106% | 2.676330 | 0.422887% |
| 3 | 1183, 6193, 12, 6195, 2086, 4120 | 0.0717, 0.3395, 0.3014, 0.5769, 0.3735, 0.6917 | 0.023346 / 1.124946 | 2.333633% | 2.686167 | 0.419425% |

[Full pre-run regime record](results/workload_regime.json). Offered demand is integrated exactly over positive-duration segments of continuous [submit,submit+R). Review values are rounded: [definition comparison](provenance/workload_regime_review_comparison.json) shows that 10-second sampling with ceil admission and +1 s occupancy gives the rounded review fractions/maxima. These are distinct descriptions; neither is realised RAPS occupancy. No input was modified to match the review.

The largest 20 creation gaps cover 76.900184% of the 149.325938-day source span. Only 3 eligible pods occur in the first 30 days; the first-percentile creation time is day 115.837838. The last-99%-of-pods tail compresses to 23.367041 minutes.

**Seed identity:** seed3 has 162 leading pods, then all 19627 seed2 job requests exactly, delayed 33.036572720579 s (maximum accumulated floating-point deviation 3.624e-13 s). Treat this as about two workload conditions. Seeds2/3 are not determinism or sensitivity evidence.

CPU cap clipping counts use uncapped mapped CPU>2; active-cap fractions including equality are also recorded. Source runnable default clips 26/6203 pods (0.419152%); resource-only multigpu50 clips 339/7973 (4.251850%). Power estimates use the frozen loss-exclusive node increment; actual loss-inclusive rack power comes from the future ledgers.

Nominal rho=0.6, offered finite-window utilisation (0.455–0.486 plus bursts), and realised ledger utilisation/waits/censoring must be reported separately. Queueing coverage, the lightweight parent seed check and C′ adapter are required before launch. D7 remains deferred; D8 is recorded for Task17 without editing the frozen spec.

## Execution interruption (2026-10-31)

The primary controller exited unexpectedly with code143 (SIGTERM), after approximately45minutes. Four primary runs completed and passed run-level validation; three started runs remain partial; eight primary configurations never started. No C′ rerun or evidence comparison was attempted. G4 is pending review, not a negative or positive policy result. No source was changed and no retry launched. [Interruption record](provenance/execution_interruption.json) and [complete/partial file inventory](provenance/interruption_inventory.json) preserve the state. The temporal association with45minutes is consistent with a session lifetime limit, but the cause is unresolved.

HEAD is deliberately kept at the launch SHA to preserve the exact Git precondition; interruption artifacts remain uncommitted pending recovery review. The committed preparation is pushed separately without advancing HEAD. Any retry budget, infrastructure/source change and resume plan need an explicit Bipin-reviewed decision.
