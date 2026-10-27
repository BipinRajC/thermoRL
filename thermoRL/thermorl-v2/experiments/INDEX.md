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
