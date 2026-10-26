# E02 — G2 packed versus spread (summit)
**System:** summit  **Status:** planned
**Pre-registered:** 2026-10-27; introducing commit to be recorded after commit (before execution).

## Question
At identical total rack power, how large is the packed-minus-spread hotspot effect, and is this FMU eligible for primary selection?

## Pre-registered decision rule
**Common methodology.** The same protocol runs on each of Lassen, Summit and Marconi100, each in its own process:

1. Instantiate `FmuBackend` with that system's coupling.
2. Warm up: 7200 s at the idle vector, with `dt = Δ_system`.
3. Run two branches from the snapshot. Each branch: `reset()`, then 3 h at `dt = Δ_system`.
   - **spread:** all racks at `P(0.6) = idle + 0.6·(peak − idle)`.
   - **packed:** the same total (`n × P(0.6)`). Racks 0..k−1 run at `peak`, rack k at the remainder, the rest at `idle`.
4. Ambient: 290 K for all inputs.

**Recorded per system:**

| Name | Definition |
|---|---|
| `Δ_s` | (packed max-rack °C) − (spread max-rack °C), mean over the final 30 min |
| `class_s` | GO if Δ ≥ 2.0 °C; WEAK if 1.0 ≤ Δ < 2.0; STOP if Δ < 1.0 |
| `fmu_s_per_sim_h` | Measured FMU-only wall time per simulated hour |
| `C_s` | Projected closed-loop minutes per 6 h run: `fmu_s_per_sim_h × 6 × 1.5 / 60` (1.5 is the RAPS overhead factor, an ASSUMPTION) |
| `sane_s` | Warm-up completed; all outputs finite; all coolant temperatures in [10, 70] °C; no FMU exception |

**Selection rule (applied mechanically, recorded in `experiments/cross_system/X01_fmu_selection/`):**
1. **Eligible** = `sane_s` AND `C_s ≤ 30` min.
2. Among eligible systems, the **candidate** is the one with the largest `Δ_s`.
3. **Tie-break:** if another eligible system has `Δ ≥ 0.8 × Δ_candidate` and the same class, choose the one with the lower `C_s`.
4. If the chosen class is **STOP**, stop and report. The demo story needs replanning.
5. If the chosen class is **WEAK**, proceed and record that the hotspot story is reframed as "modest".
6. **Post-selection guard:**
   - If the Task 5 bench (RAPS + FMU, idle) measures more than 45 min per 6 h run for the primary, switch to the next eligible system in selection order.
   - Re-run G1 and G3 on that system.
   - Record the switch.


### Approved reproducibility clarification
Approved by Bipin in conversation on 2026-10-27: compare canonical deterministic scientific-summary bytes and thermal-series content across the Lassen rerun, excluding exactly `fmu_s_per_sim_h` and `projected_closed_loop_min_6h` from the scientific summary. Preserve each full summary and timing measurement separately. X01 uses only the original runs' costs. Do not claim full-summary byte identity. No physical threshold, input, horizon or selection rule changes. Rerun artifacts: `provenance/rerun_1_data/`; comparison: `provenance/rerun_1.json`.

## Configuration
[config.yaml](config.yaml), encoded as JSON (a YAML subset). 257 racks, 10 s ticks, 7200 s capped idle preconditioning, 10800 s per branch, load fraction 0.6, air/external 290 K. Idle/peak are measured RAPS model values. A negative settlement threshold enforces the prescribed fixed warm-up without altering backend semantics.

## Method
From `thermoRL/thermorl-v2`, after committing this preregistration:

```bash
uv run python -m thermorl2.experiments.probes g2 --system summit --out experiments/summit/E02_g2_packed_vs_spread
```

Launch all three systems as separate parallel OS processes. Verify SHA before instantiation. One backend; restore the same snapshot before spread and packed. Check all sampled rack/CDU/global outputs for finiteness and sampled coolant in [10,70] °C, including warm-up. Preserve branch t=0 and every subsequent tick. Expected wall time: minutes for Lassen/Marconi100, 30–60 minutes for Summit. Rerun Lassen independently into its retained provenance subtree using the identical frozen config.

## Metrics
At each right endpoint, compute max rack coolant, mean rack coolant, and max-minus-min spread. Average each over the final 1800 s (`9000 < t_s <= 10800`). Δ is packed mean maximum minus spread mean maximum, °C. FMU-only cost includes initialization, warm-up, branch resets, observation calls, steps and close, divided by the total 8 simulated hours. Python aggregation and plotting are excluded from FMU runtime and recorded separately in wall timings. C_s uses the frozen 1.5 overhead assumption.

## Results
Pending execution.
## Plots
Pending execution.
## Observations (FACT)
Pending execution.
## Interpretation (INFERENCE)
Pending execution.
## Conclusion and decision
Pending execution.
## Limitations
One homogeneous twin; capped initialization; restore jitter. G2 measures placement contrast, not advantage beyond power balancing. Wall cost is machine-specific; 1.5 overhead is an assumption.
## Provenance
Git state, source/config/workload-vector/FMUs hashes, environment, policy/seed (not applicable), backend=fmu and timings will be recorded.
## Demo relevance
Earliest falsification gate for the hotspot demonstration; feeds mechanical primary selection.
