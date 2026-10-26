# marconi100 system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/marconi100.fmu` |
| FMU SHA-256 | `9dac7818338d0be7fcb887ee88acab01a62eeb7aff4bd286e65874e0ef5c3f77` |
| RAPS config path (repo-relative) | `sim-raps/config/marconi100.yaml` |
| Topology | 49 racks / 49 CDUs; 20 nodes/rack; 4 GPUs/node |
| Power tick Δ | 20 s |
| Measured idle / peak rack kW | 12.365200000000 / 38.555200000000 |
| Smoke wall_s | 2.848765389000 (600 s capped preconditioning) |
| Schematic grid | 7 × 7 |
| What-if racks (zero-based) | 36–48 |
| FMU-only wall s / simulated h | 2.632778592002 (original G2) |
| Projected closed-loop min / 6 h | 0.394916788800 (1.5 overhead assumption) |

## Known caveats

One homogeneous liquid-cooled POWER9 plant; one CDU per rack. Warm-up is capped, not settled. Restore jitter is documented on Lassen; no thermal backend other than the FMU is used. Global primary supply/return labels refer to CDU 1. Runtime and eligibility will be measured, not assumed.

## Experiments

TBD (Task 2/3).

## Task 2 mechanical smoke verification (FACT)

`uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v -s` launches `uv run python -m thermorl2.experiments.fmu_smoke --system marconi100` equivalently via the current Python executable, as a separate process. SHA was checked before instantiation. Warm-up used 600.0 s; all recorded outputs were finite; coolant min/max were 36.856428549590/36.856428708161 °C. Initial verification wall time: 2.848765389000 s. Source: Task 2 changes based on `a7a0c1a`, dirty during verification. Backend: fmu. Ambient: 290 K; idle vector: 12.365200000000 kW/rack; no stochastic workload, policy or seed.

Complete corrected Task 2 verification: **33 passed in 81.14 s**. Repeated smoke wall time: 2.889859461000 s; reported coolant min/max and power bounds were identical to the initial smoke. Unit/integration including the existing RAPS-coupling regression: **31 passed in 1.43 s**. These smoke wall times do not replace the G2 cost measurement or establish G2 eligibility.

## E02 G2

[README](E02_g2_packed_vs_spread/README.md): Δ=0.054796806701 °C, STOP, sane=True. Cost is from the original experiment. No stationary-state claim.
