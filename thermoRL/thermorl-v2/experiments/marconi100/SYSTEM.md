# marconi100 system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/marconi100.fmu` |
| FMU SHA-256 | `9dac7818338d0be7fcb887ee88acab01a62eeb7aff4bd286e65874e0ef5c3f77` |
| RAPS config path (repo-relative) | `sim-raps/config/marconi100.yaml` |
| Topology | 49 racks / 49 CDUs; 20 nodes/rack; 4 GPUs/node |
| Power tick Δ | 20 s |
| Measured idle / peak rack kW | TBD (Task 2/3) |
| Smoke wall_s | TBD (Task 2/3) |
| Schematic grid | 7 × 7 |
| What-if racks (zero-based) | 36–48 |
| FMU-only wall s / simulated h | TBD (Task 2/3) |
| Projected closed-loop min / 6 h | TBD (Task 2/3) |

## Known caveats

One homogeneous liquid-cooled POWER9 plant; one CDU per rack. Warm-up is capped, not settled. Restore jitter is documented on Lassen; no thermal backend other than the FMU is used. Global primary supply/return labels refer to CDU 1. Runtime and eligibility will be measured, not assumed.

## Experiments

TBD (Task 2/3).
