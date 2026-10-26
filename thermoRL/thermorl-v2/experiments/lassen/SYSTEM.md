# lassen system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/lassen.fmu` |
| FMU SHA-256 | `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b` |
| RAPS config path (repo-relative) | `sim-raps/config/lassen.yaml` |
| Topology | 44 racks / 44 CDUs; 18 nodes/rack; 4 GPUs/node |
| Power tick Δ | 20 s |
| Measured idle / peak rack kW | 10.857680000000 / 34.428680000000 |
| Smoke wall_s | 2.453431820000 (600 s capped preconditioning) |
| Schematic grid | 4 × 11 |
| What-if racks (zero-based) | 33–43 |
| FMU-only wall s / simulated h | 2.027717812993 (original G2) |
| Projected closed-loop min / 6 h | 0.304157671949 (1.5 overhead assumption) |

## Known caveats

One homogeneous liquid-cooled POWER9 plant; one CDU per rack. Warm-up is capped, not settled. Restore jitter is documented on Lassen; no thermal backend other than the FMU is used. Global primary supply/return labels refer to CDU 1. Runtime and eligibility will be measured, not assumed.

## Experiments

TBD (Task 2/3).

## Task 2 mechanical smoke verification (FACT)

`uv run pytest tests/unit tests/integration/test_power_model.py tests/fmu/test_fmu_smoke_all_systems.py -v -s` launches `uv run python -m thermorl2.experiments.fmu_smoke --system lassen` equivalently via the current Python executable, as a separate process. SHA was checked before instantiation. Warm-up used 600.0 s; all recorded outputs were finite; coolant min/max were 36.609148984896/36.609149050257 °C. Initial verification wall time: 2.453431820000 s. Source: Task 2 changes based on `a7a0c1a`, dirty during verification. Backend: fmu. Ambient: 290 K; idle vector: 10.857680000000 kW/rack; no stochastic workload, policy or seed.

Complete corrected Task 2 verification: **33 passed in 81.14 s**. Repeated smoke wall time: 2.479606414000 s; reported coolant min/max and power bounds were identical to the initial smoke. Unit/integration including the existing RAPS-coupling regression: **31 passed in 1.43 s**. These smoke wall times do not replace the G2 cost measurement or establish G2 eligibility.

## E02 G2

[README](E02_g2_packed_vs_spread/README.md): Δ=2.036319592756 °C, GO, sane=True. Cost is from the original experiment. No stationary-state claim.
