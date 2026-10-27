# summit system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/summit.fmu` |
| FMU SHA-256 | `0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233` |
| RAPS config path (repo-relative) | `sim-raps/config/summit.yaml` |
| Topology | 257 racks / 257 CDUs; 18 nodes/rack; 6 GPUs/node |
| Power tick Δ | 10 s |
| Probe idle / peak rack kW (loss-exclusive) | 13.201714285714 / 47.282326530612 |
| RAPS idle / peak rack kW (loss-inclusive, D1) | 13.822619047619 / 49.323256802721 |
| Smoke wall_s | 73.791710919000 (600 s capped preconditioning) |
| Schematic grid | 13 × 20 |
| What-if racks (zero-based) | 192–256 |
| FMU-only wall s / simulated h | 146.082248317006 (original G2) |
| Projected closed-loop min / 6 h | 21.912337247551 (1.5 overhead assumption) |

## Known caveats

One homogeneous liquid-cooled POWER9 plant; one CDU per rack. Warm-up is capped, not settled. Restore jitter is documented on Lassen; no thermal backend other than the FMU is used. Global primary supply/return labels refer to CDU 1. Runtime and eligibility will be measured, not assumed.

## Experiments

TBD (Task 2/3).

## Task 2 mechanical smoke verification (FACT)

`uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v -s` launches `uv run python -m thermorl2.experiments.fmu_smoke --system summit` equivalently via the current Python executable, as a separate process. SHA was checked before instantiation. Warm-up used 600.0 s; all recorded outputs were finite; coolant min/max were 37.540367295108/37.540369062942 °C. Initial verification wall time: 73.791710919000 s. Source: Task 2 changes based on `a7a0c1a`, dirty during verification. Backend: fmu. Ambient: 290 K; idle vector: 13.201714285714 kW/rack; no stochastic workload, policy or seed.

The RAPS power config has `power_switch: 0`. A new test initially assumed strictly positive switch overhead; that unsupported test assumption was corrected to permit zero. The power formula and system inputs were unchanged.

Complete corrected Task 2 verification: **33 passed in 81.14 s**. Repeated smoke wall time: 69.812412241000 s; reported coolant min/max and power bounds were identical to the initial smoke. Unit/integration including the existing RAPS-coupling regression: **31 passed in 1.43 s**. These smoke wall times do not replace the G2 cost measurement or establish G2 eligibility.

## E02 G2 and X01

[README](E02_g2_packed_vs_spread/README.md): Δ=6.234888984342 °C, GO, sane. [X01](../cross_system/X01_fmu_selection/README.md) selects Summit as primary, Lassen runner-up, without tie-break. Higher observed coolant temperatures (up to 61.087591 °C) are retained; no threshold or power change. Task 5 cost guard remains pending.

## E03 G3 room-air what-if

[README](E03_g3_room_air/README.md): NOT_USABLE; affected paired difference 0.538986028132 °C, unaffected 0.101837403880 °C. The frozen room-air what-if is dropped. [62 candidate CDU parameters](E03_g3_room_air/results/candidate_cdu_parameters.txt) are listed only; none were applied. (not observed summit behaviour)

## E01 G1 operating range and frozen fit

[README](E01_g1_uniform/README.md): final means 40.041535–66.792188 °C; a=27.975385727123, b=0.805245082436, R²=0.989167647689, empirical τ=4050 s, t_hot=63.304922110353 °C. Both 40 °C and 45 °C were reached. Capped initial mean 39.028228 °C; idle branch subsequently rose 1.013307 °C. Final-window values are not certified equilibria.

## Task 5 bench — approved D1/D2 (2026-10-27)

Exact command, from `thermoRL/thermorl-v2`:

```bash
uv run python -m thermorl2.experiments.bench --system summit --hours 6
```

[Raw bench JSON](_bench/task5_bench_20261026T224138_640592Z.json) and [environment](_bench/environment.txt). Measured one simulation worker from process launch to exit, including interpreter imports, FMU instantiation, full fixed 7200 s capped warm-up, 6 h idle RAPS+FMU episode, and shutdown. A lightweight timing parent runs no simulation. No other FMU or RAPS simulation ran concurrently; only editing and non-FMU unit tests were used. All recorded source hashes verify against the worker's immutable start commit, `7695c34`, including files subsequently edited for Tasks 6–8.

```json
{
  "episode_fmu_s": 579.4736320299344,
  "fmu_s": 902.9637261998796,
  "fmu_steps": 2160,
  "horizon_h": 6,
  "instantiation_s": 7.787814560000697,
  "power_ticks": 2160,
  "rack_kw_reference": {
    "probe_idle_kw": 13.201714285714285,
    "probe_peak_kw": 47.282326530612245,
    "raps_idle_kw": 13.822619047619046,
    "raps_peak_kw": 49.32325680272109
  },
  "raps_s": 3.9649237830744823,
  "switch_required": false,
  "system": "summit",
  "total_s": 912.5393135249997,
  "twice_after_warmup_instantiation_s_information_only": 1177.2581247300004,
  "twice_total_s_information_only": 1825.0786270499993,
  "warmup_instantiation_s": 323.91025115999946,
  "warmup_used_s": 7200.0,
  "warmup_wall_s": 316.12243659999876
}
```

**D2 guard: PASS — 912.539313525 s <= 2700 s. Summit remains primary.** Both doubled quantities are information only. Horizon is **6 h** because 4×total_s exceeds 300 s. Raw maximum episode coolant was 40.182141793 °C; outputs checked were finite.

**D1 rack-power reconciliation:** RAPS's own `PowerManager.compute_rack_power` gives 13.822619047619 kW idle and 49.323256802721 kW peak, including rectifier losses. C1 probe references were 13.201714285714 and 47.282326530612 kW. Closed-loop FMU inputs therefore run about 4–5% higher at equal node utilisation. C1 experiments and the G1 fit remain frozen: the fit maps FMU-input kW to coolant temperature. `job_increment_kw` remains frozen and understates between-tick Summit committed increments by roughly 4%; this limitation is documented, not corrected.

**FACT:** the only pre-existing dirty path at bench start was ` D docs/prompt.md`; it was neither staged nor modified by this work. The raw `git_status_porcelain` records it. RAPS emitted its existing missing-Summit-dataloader warning while constructing the discarded random workload; the benchmark injected `jobs=[]`, disabled cooling/UI/file output, and completed all idle ticks successfully.

## E10 / C2 closed-loop mechanics

[README](E10_c2_vertical_slice/README.md): PASS, all six invariants. Packing, power_balance and independent packing rerun use the same SHA-keyed seed-1 rho=.6 two-hour workload, 7200 s capped warm-up and 720 FMU steps. Job starts and IT power match; packing decisions are byte-identical on rerun and interval values match. No coolant above 70 °C or negative episode pump sample occurred.

Observed final-hour mean maximum coolant: packing 53.445128703 °C; power_balance 54.115585107 °C. This unexpected ordering is reported as mechanics evidence, without a G4 conclusion or input tuning. The heatmaps show concentration on lower rack indices under packing and distributed hot stripes under power_balance, not a thermally flat panel. Realised sampled node utilisation is 0.544679229 for both. The experiment has 1514 starts; one of 1515 offered jobs is admitted at the excluded t=7200 boundary.

[R3/R4 and timing provenance](E10_c2_vertical_slice/provenance/manifest.json) and [runtime projection](E10_c2_vertical_slice/results/runtime_projection.json) are retained. Proposed future matrix workers: 3, matching tested E10 concurrency; linear projected 15-run wall time about 70–84 min. No matrix has run. C2 is a mandatory stop for review.
