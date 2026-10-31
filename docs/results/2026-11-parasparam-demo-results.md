# ParasParam demo results

Prepared 2026-10-31. **Both preregistered G4 evaluations concluded “no material value on the homogeneous twin”; `value_beyond_power=false`.** The deliverable is a working, auditable evaluation testbed with negative materiality results, not a validated thermal-scheduling benefit.

## What ran

On Arch Linux x86-64 with locked Python 3.12.14, the loop is RAPS (cooling off, exact-node allocations) → loss-inclusive rack power → POWER9 cooling FMU → observations used by subsequent placements. A preregistered three-FMU gate selected **Summit** mechanically, with Lassen runner-up and no tie-break changing the winner:

| System | G2 packed−spread Δ °C | Class | Projected C_s min/6 h | Sane |
|---|---:|---|---:|---|
| Lassen | 2.036319592756 | GO | 0.304157671949 | yes |
| Summit | 6.234888984342 | GO | 21.912337247551 | yes |
| Marconi100 | 0.054796806701 | STOP | 0.394916788800 | yes |

C_s uses original FMU-only timing and the assumed 1.5 overhead factor; it is not measured matrix time. Summit G1 froze **a=27.9753857271229 °C, b=0.8052450824355937 °C/kW, tau=4050 s, H=600 s**, with t_hot=63.30492211035258 °C and fit R²=0.9891676476892759. These finite-horizon parameters are heuristics. G3 was **NOT_USABLE**: affected Δ=0.538986 °C (<1.0), unaffected Δ=0.101837 °C. [C5](../checkpoints/C5-whatif.md) records no G5/E13 execution, no alternative lever and 62 listed CDU candidates with none applied.

E11 used `g4_synthetic.yaml`, launch SHA `6ee93c4fb6e3fe019f2d57534d066f208b067c6d`. E12 used `g4_alibaba.yaml`, launch SHAs `18dfea14aa42bc21a191cc1f9a39fc421d8723bd` / `e0e1522ac52b5780cb3088232051e26dbd492804`. Each tested five policies × three seeds, six-hour episodes, 10 s ticks, nominal 290 K and a separate capped 7200 s warm-up. E12 used only the default Alibaba variant with frozen mappings. Appendix A lists the FMU, config and workload SHAs; committed preregistrations also pin sidecars and G1.

## G4 and metric-specific observations

Primary metric: time-mean maximum rack coolant over **3600 < t_s ≤21600**, 1800 endpoints. PB−TP must reach **0.5 °C in every seed**, at full precision. Neither experiment meets this criterion. Rounded tables do not replace the original full-precision decisions.

| Experiment | Seed | Packing °C | NB °C | PB °C | CR °C | TP °C | PB−TP °C | Packing−TP °C |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E11 | 1 | 54.070216 | 53.883515 | 54.330429 | 53.534760 | 53.987934 | 0.342495 | 0.082282 |
| E11 | 2 | 54.177058 | 54.094552 | 54.137678 | 54.123498 | 54.284869 | -0.147190 | -0.107811 |
| E11 | 3 | 54.122798 | 53.559813 | 53.775784 | 53.780430 | 53.846649 | -0.070865 | 0.276150 |
| E12 | 1 | 41.410869 | 41.256919 | 41.235138 | 41.164820 | 41.057548 | 0.177590 | 0.353321 |
| E12 | 2 | 41.345775 | 40.969726 | 40.981985 | 41.239750 | 40.904721 | 0.077265 | 0.441054 |
| E12 | 3 | 41.308922 | 41.128894 | 40.994658 | 41.095216 | 40.885867 | 0.108792 | 0.423055 |

E11 packing ≈ TP on the primary metric: packing−TP approximately +0.08/−0.11/+0.28 °C, without a consistent primary ordering.

> In E12 (small, low-density, bursty Alibaba-derived jobs), thermal_predictive had the lowest and packing the highest time-mean max-rack coolant temperature in all three seeds (PB−TP 0.08–0.18 °C; packing−TP 0.35–0.44 °C). This is below the preregistered 0.5 °C materiality threshold, rests on about two independent workload conditions (seed 3 ≈ seed 2 shifted 33 s), and is descriptive only.

S1 is descriptive. In E11, TP had lower rack-temperature std than PB by 0.374/0.319/0.294 °C and lower hottest-26 mean by 0.538/0.519/0.463 °C; coolest_rack was lowest on these two metrics. In E12, TP was lowest on temperature std and hottest-26 mean; PB−TP gaps were 0.037/0.029/0.029 and 0.047/0.044/0.041 °C. **PB had the lowest rack-power std in both experiments.** E11 spread and p99 were mixed. E12 spread favored TP in all seeds; p99 rankings were mixed (CR lowest in seed 1, TP in seeds 2/3). Appendix B retains per-seed differences. No secondary metric substitutes for G4.

## Validation, reproducibility and regime

All six acceptance gates passed for E10, E11 and E12: identical IT power and job starts; exact free/distinct node allocation and lifecycle; the approved scoped determinism evidence; rack-power reconciliation; independent step/clock counts; and complete provenance/ledger joins. Invariant 3 is its explicit scope, not universal direct repetition.

Closed-loop reproducibility covers **E10 packing seed 1, 2 h fresh-process rerun; E11 seed-1 packing/PB 2 h prefix reproduction; E12 TP seed 1, 6 h byte-identical canonical decisions and exact interval values in a fresh process on the same machine, environment and SHA**. All E11 statuses remain inherited_not_remeasured; only E12 TP seed 1 is verified_E12. Timing measurements were excluded from equality but their joins/hashes validated. Nothing else in the closed-loop matrices was repeated. C1's separate Lassen G2 scientific-output repeat does not extend these policy scopes.

D7(b) fresh-clone check is pending. No fresh-clone success or cross-machine portability is claimed. The final measured record will be [d7_fresh_clone_check.json](d7_fresh_clone_check.json); no E11/E12 rerun is authorized.

E12's three utilisation quantities are distinct: nominal construction rho **0.6**; continuous offered window **0.485766/0.454619/0.456625**, with approximately 23 min dense plus 80 min quiet per 1.74 h cycle; realised ledger **0.485618/0.454570/0.456569**. Mean waits were **8.62/6.00/6.13 s**, peak queues 694/564/577 jobs and zero censoring. Starts/waits are identical across policies by construction. Seed 3 ≈ seed 2 shifted 33.0366 s after 162 leading pods limits independent conditions to about two.

Runtime scopes: original G2 manifest total wall was Lassen **18.218 s**, Summit **1172.612 s**, Marconi100 **22.922 s**; G1/G3 **1792.660/1201.513 s**. The isolated bench took **912.539 s** process wall; E10 EpisodeRunner totals were **540.666/484.213/538.399 s** (packing/PB/packing repeat). E11 three-worker controller wall was **4746.698 s**. E12 recovery controller wall was **5033.357 s**; original-start-to-final-primary span was **9565.744 s including downtime**; guarded repeat wall **1479.362 s** includes subprocess plus validation. Approximately **1850 s downtime** is derived from the approximate original termination time, not directly measured. Selected E12 processes peaked at **1.63–1.99 GiB RSS**, primary cgroup **6.93 GiB**; offline report **458.676 s** after imports, own peak **4.98 GiB**. Earlier memory was not uniformly recorded and is not inferred from E12. [Runbook](runbook.md) identifies scopes and sources.

Bipin ratified retaining 4 successes, preserving/restarting 3 interrupted attempts once, running 8 unstarted configurations, then 1 planned repeat: **19 cumulative attempts**. Only orchestration/accounting changed between E12 launch SHAs. Interruption cause is **Bipin-reported memory pressure**, controller SIGTERM143; the queried journal had no corroborating entries. This supersedes the old session-lifetime inference. Historical recovery records and pinned approval were preserved. Raw backup remains pending a Bipin-provided destination: [backup record](raw_backup_record.json).

## Claims and limitations

The measured allowed claims are the scoped reproducible loop/invariants; the two negative G4 comparisons (largest PB−TP 0.34/0.18 °C); metric-specific spatial-temperature changes at identical IT power/timing; measured packing−TP gaps above; and the preregistered Summit selection. G3 supports only the weak-lever finding and dropped scenario. [DEMO.md](../../thermoRL/thermorl-v2/experiments/DEMO.md) maps labelled seed-1 assets to claims. No validated scheduling benefit, savings or significance is claimed.

Spec §8, verbatim:

- One homogeneous liquid-cooled POWER9 plant per twin; 1 CDU per rack; weak rack-to-rack coupling.
- No validated PUE or plant power.
- FMUs run on Linux/Windows only.
- Capped warm-up snapshot drift.
- Replay jitter of 1.43e-4 °C under FMU state restore.
- Alibaba data lacks power, so job power is modelled. The pod-to-node mapping and time compression are assumptions.
- 3 seeds.
- The ExaDigiT ML surrogates were not used: no trained bundles exist for these systems, and they do not output cabinet coolant temperature. They are listed as future work.

**D8 correction (2026-10-31):** On the Summit twin, rack coolant temperature depends on total facility load and on the placement of load elsewhere, not only on a rack's own power (C1 I1; E10/E11 M3); the mechanism is unresolved.

**S2, verbatim:** published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.

**M2 is E11-only:** large high-power jobs can dominate its max-rack metric under the frozen spanning rule; coexistence does not establish causation. E12's max-two-node jobs require their own attribution. **M3 is unresolved.** Warm-up is capped/unsettled; G1 is a heuristic; committed between-tick job increments understate losses by approximately 4%, while actual FMU inputs are loss-inclusive. 45 °C and t_hot are references only; coolant is modeled. E12 A2–A4 cover assumed seconds/lifetime-as-runtime for Running/Failed pods, clipping, approximately 2064× arrival-only compression, cyclic wraps/correlated rotations, static resource-power mapping and low density. Historical Task 1.5 physical-response testing remains **strict XFAIL, not a pass**. No hardware, safety, PUE, energy/cooling-power saving, carbon, lifetime, RL, surrogate, heterogeneous-zone or identified-mechanism claim is made.

## Appendix A — immutable SHA-256 references

| Input | SHA-256 |
|---|---|
| lassen FMU | `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b` |
| summit FMU | `0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233` |
| marconi100 FMU | `9dac7818338d0be7fcb887ee88acab01a62eeb7aff4bd286e65874e0ef5c3f77` |
| E11_g4_synthetic config | `5de2c6ae8fb753923f49816abded515bfe61ee20c5f46d098d854fe1e211dac9` |
| E11_g4_synthetic 7e06a12548f70d5b6fbd8d3edeacbccaafbe8486dfdea48caa5533696692aa0d.parquet | `7e06a12548f70d5b6fbd8d3edeacbccaafbe8486dfdea48caa5533696692aa0d` |
| E11_g4_synthetic c9bd815fe21806930edf225f6e3c443fcb4e8b49e905edb985190f77de967c27.parquet | `c9bd815fe21806930edf225f6e3c443fcb4e8b49e905edb985190f77de967c27` |
| E11_g4_synthetic d2a64253d18fc92ee3c6bb42eec3189e5cc5ffd50743e3c71fc1dc4b88100b91.parquet | `d2a64253d18fc92ee3c6bb42eec3189e5cc5ffd50743e3c71fc1dc4b88100b91` |
| E12_g4_alibaba config | `a44576795d075c2431ca7cbf7be992dd20d4ebd24bcd7cf930bca7380ac13fbb` |
| E12_g4_alibaba 1e09de8c6573a2474d38f7660da0126a4ce24919b3ba8a8ff1255fc5ad09b904.parquet | `1e09de8c6573a2474d38f7660da0126a4ce24919b3ba8a8ff1255fc5ad09b904` |
| E12_g4_alibaba 28250b8c8834f281aa0cb56d35cb28d550fde05d01b8b36756116211f7fd8ead.parquet | `28250b8c8834f281aa0cb56d35cb28d550fde05d01b8b36756116211f7fd8ead` |
| E12_g4_alibaba 7415a80132d0bcf993071b30bfdc586803c848e1ab582bc9730a71dfddab4c2c.parquet | `7415a80132d0bcf993071b30bfdc586803c848e1ab582bc9730a71dfddab4c2c` |
| thermorl2/experiments/configs/primary.yaml | `bdfdd5b30e893eefc299ed4c6fe43d2d6103ab5d36f4793a57453a53739529ec` |
| experiments/summit/E01_g1_uniform/results/summary.json | `b24aa61fbaab43f44f400c1af1923bc2895ded5a7c85c337c196c6dcc4af91c3` |

## Appendix B — metric-specific differences and sources

| Experiment | Metric (PB−TP) | Seed 1 | Seed 2 | Seed 3 |
|---|---|---:|---:|---:|
| E11 | rack_t_std_mean_c | +0.373589 | +0.318596 | +0.294291 |
| E11 | top_decile_mean_c | +0.537526 | +0.518677 | +0.463433 |
| E11 | rack_kw_std_mean | -0.283286 | -0.421457 | -0.470324 |
| E11 | spread_mean_c | +0.494228 | -0.055594 | +0.062643 |
| E11 | maxrack_p99_c | -0.016459 | +0.549610 | -0.640812 |
| E12 | rack_t_std_mean_c | +0.036912 | +0.028826 | +0.028586 |
| E12 | top_decile_mean_c | +0.047059 | +0.044489 | +0.040633 |
| E12 | rack_kw_std_mean | -0.167812 | -0.148653 | -0.145698 |
| E12 | spread_mean_c | +0.259412 | +0.162479 | +0.182128 |
| E12 | maxrack_p99_c | +0.182178 | +0.049059 | +0.459100 |

Sources: [C1](../checkpoints/C1-fmu-selection-and-physics.md), [C2](../checkpoints/C2-vertical-slice.md), [C3 review](../checkpoints/C3-review-opus.md), [C4 review](../checkpoints/C4-review-opus.md); [E11 metrics](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/metrics.csv), [E11 decision](../../thermoRL/thermorl-v2/experiments/summit/E11_g4_synthetic/results/decision.json), [E12 metrics](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/results/metrics.csv), [E12 decision](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/results/decision.json). No experimental output was regenerated for this note.

## Appendix C — Opus §9 claims table, verbatim

| Allowed (with stated scope) | Unsupported |
|---|---|
| The FMU-backed closed loop runs with all six invariants enforced. Determinism is verified for E10 packing (2 h), the E11 seed-1 packing/PB 2 h prefixes and E12 TP seed 1 (6 h, byte-identical). | "The whole matrix is reproducible"; "portable across machines". |
| Under both preregistered G4 tests (synthetic and Alibaba-derived), thermal_predictive showed **no material value beyond power balancing on the homogeneous twin** (largest per-seed PB−TP 0.34 and 0.18 °C, against 0.5). | "Thermal-aware placement works", or "is useless in general". |
| In E12 (small, low-density, bursty jobs), TP had the lowest and packing the highest time-mean max-rack temperature in all three seeds (PB−TP 0.08–0.18 °C, packing−TP 0.35–0.44 °C). This is below materiality, with ≈ 2 independent conditions. | "TP reduces hotspots by 0.4 °C"; any significance claim; generalising to E11's regime. |
| Placement changes the rack-temperature distribution at identical IT power and timing: S1 differences per metric and per experiment. | Generalising S1 across metrics. In E11 packing ≈ TP on the primary metric. |
| G3 room-air lever NOT_USABLE (0.539 °C); the what-if was not run. | Any degraded-cooling result. |
| Coolant is modelled; 45 °C and t_hot are references. | Hardware temperature, safety, PUE, energy savings, carbon, lifetime, RL, surrogate, heterogeneous-zone or causal-mechanism claims. |
| Summit's rack temperature depends on facility load and on the placement of other load (I1, M3; the D8 wording). | "Weak rack-to-rack coupling" without the D8 correction; an identified mechanism. |
