# lassen system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/lassen.fmu` |
| FMU SHA-256 | `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b` |
| RAPS config path (repo-relative) | `sim-raps/config/lassen.yaml` |
| Topology | 44 racks / 44 CDUs; 18 nodes/rack; 4 GPUs/node |
| Power tick Δ | 20 s |
| Measured idle / peak rack kW | TBD (Task 2/3) |
| Smoke wall_s | TBD (Task 2/3) |
| Schematic grid | 4 × 11 |
| What-if racks (zero-based) | 33–43 |
| FMU-only wall s / simulated h | TBD (Task 2/3) |
| Projected closed-loop min / 6 h | TBD (Task 2/3) |

## Known caveats

One homogeneous liquid-cooled POWER9 plant; one CDU per rack. Warm-up is capped, not settled. Restore jitter is documented on Lassen; no thermal backend other than the FMU is used. Global primary supply/return labels refer to CDU 1. Runtime and eligibility will be measured, not assumed.

## Experiments

TBD (Task 2/3).
