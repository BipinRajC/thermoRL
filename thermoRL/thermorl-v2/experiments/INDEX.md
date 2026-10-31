# Experiment index

| EID | system | question (one line) | status | decision | key number | README link | date |
|---|---|---|---|---|---|---|---|
| E00 | lassen | What legacy evidence exists? | complete | indexed; see option-B backend closure | historical t63 1240 s; restore jitter 1.43e-4 °C | [README](lassen/E00_legacy_task15/README.md) | 2026-10-27 |
| E02 | lassen | Packed vs spread at equal total power? | complete | GO | Δ=2.036320 °C | [README](lassen/E02_g2_packed_vs_spread/README.md) | 2026-10-27 |
| E02 | summit | Packed vs spread at equal total power? | complete | GO | Δ=6.234889 °C | [README](summit/E02_g2_packed_vs_spread/README.md) | 2026-10-27 |
| E02 | marconi100 | Packed vs spread at equal total power? | complete | STOP | Δ=0.054797 °C | [README](marconi100/E02_g2_packed_vs_spread/README.md) | 2026-10-27 |
| X01 | cross_system | Which FMU meets the mechanical selection rule? | complete | GO: summit; runner-up lassen | Δ=6.234889 °C; C_s=21.912337 min | [README](cross_system/X01_fmu_selection/README.md) | 2026-10-27 |
| E01 | summit | Uniform-load operating range and response? | complete | fit frozen | 40.041535–66.792188 °C; τ=4050 s | [README](summit/E01_g1_uniform/README.md) | 2026-10-27 |
| E03 | summit | Does the room-air what-if change coolant? | complete | NOT_USABLE | affected Δ=0.538986 °C | [README](summit/E03_g3_room_air/README.md) | 2026-10-27 |
| Task5 bench | summit | Is the isolated 6 h engine/FMU cost within D2? | complete | PASS; keep summit, horizon 6 h | 912.539314 s; 2160 steps | [SYSTEM](summit/SYSTEM.md#task-5-bench--approved-d1d2-2026-10-27) | 2026-10-27 |
| E10 | summit | Does the closed loop preserve all six invariants? | complete | PASS (6/6) | 720 steps; 1514 starts; max IT diff 1.82e-12 kW | [README](summit/E10_c2_vertical_slice/README.md) | 2026-10-27 |
| E11 | summit | Does thermal_predictive add value beyond power_balance? | complete | no material value on the homogeneous twin | 15 runs; all measured invariants pass; I3 inherited + NEW seed1 prefix | [README](summit/E11_g4_synthetic/README.md) | 2026-10-30 |
| E12 | summit | Does frozen thermal_predictive add value on Alibaba-derived input? | complete; C4 accepted with conditions C1–C3 | no material value on the homogeneous twin | PB−TP: +0.177590°C, +0.077265°C, +0.108792°C; C′ TPseed1 only | [README](summit/E12_g4_alibaba/README.md) | 2026-10-31 |
| C5 | summit | Was the G5/E13 room-air what-if run? | closed; not run | G3 NOT_USABLE; no alternative lever | affected Δ 0.538986 °C < 1.0 °C; 62 candidates, none applied | [C5 note](../../../docs/checkpoints/C5-whatif.md) | 2026-10-31 |
