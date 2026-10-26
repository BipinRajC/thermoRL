# summit system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/summit.fmu` |
| FMU SHA-256 | `0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233` |
| RAPS config path (repo-relative) | `sim-raps/config/summit.yaml` |
| Topology | 257 racks / 257 CDUs; 18 nodes/rack; 6 GPUs/node |
| Power tick Δ | 10 s |
| Measured idle / peak rack kW | 13.201714285714 / 47.282326530612 |
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
