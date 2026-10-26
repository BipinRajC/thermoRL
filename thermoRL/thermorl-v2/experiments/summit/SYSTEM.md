# summit system card

| Field | Value |
|---|---|
| FMU path (repo-relative) | `models/POWER9CSM/fmus/summit.fmu` |
| FMU SHA-256 | `0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233` |
| RAPS config path (repo-relative) | `sim-raps/config/summit.yaml` |
| Topology | 257 racks / 257 CDUs; 18 nodes/rack; 6 GPUs/node |
| Power tick Δ | 10 s |
| Measured idle / peak rack kW | TBD (Task 2/3) |
| Smoke wall_s | TBD (Task 2/3) |
| Schematic grid | 13 × 20 |
| What-if racks (zero-based) | 192–256 |
| FMU-only wall s / simulated h | TBD (Task 2/3) |
| Projected closed-loop min / 6 h | TBD (Task 2/3) |

## Known caveats

One homogeneous liquid-cooled POWER9 plant; one CDU per rack. Warm-up is capped, not settled. Restore jitter is documented on Lassen; no thermal backend other than the FMU is used. Global primary supply/return labels refer to CDU 1. Runtime and eligibility will be measured, not assumed.

## Experiments

TBD (Task 2/3).
