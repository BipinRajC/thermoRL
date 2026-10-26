# E03 — G3 — What-if: room-air cooling failure on one floor section (not observed summit behaviour)
**System:** summit  **Status:** planned
**Pre-registered:** 2026-10-27; introducing commit to be recorded after commit (before execution).

## Question
Does raising room-air temperature on the frozen last-quarter rack set produce the preregistered coolant change at fixed power?

## Pre-registered decision rule
The following is copied verbatim from design spec §4.2:

| Exp | Question | Protocol | Primary metric | Decision rule |
|---|---|---|---|---|
| **G3** Lever | Does room air change coolant temperature at fixed power? | All racks at f = 0.6. Control: 290 K. Intervention: what-if racks at 308.15 K. 3 h. | Δ coolant °C on affected racks (mean, final 30 min); Δ on unaffected racks | **USABLE** if ≥ 1.0 °C AND outputs are sane (finite, ≤ 70 °C). Otherwise NOT_USABLE, and the what-if is dropped. |

## Configuration
[config.yaml](config.yaml), JSON/YAML. Primary is selected mechanically by [X01](../../cross_system/X01_fmu_selection/README.md), not assumed. Power bounds and geometry come from RAPS configuration; FMU hash must match spec §3.1.

## Method
One FMU process; exactly 7200 s capped idle preconditioning, dt=10 s, snapshot restore before each branch. Both branches use all racks at idle + .6*(peak-idle), 10800 s. Control air/external 290 K; intervention raises air to 308.15 K on zero-based racks 192–256 only; external and all other rack air inputs remain 290 K. Preserve complete paired ledgers and verify identical branch-time observations. A negative settlement threshold enforces the fixed warm-up. The parameter list is descriptive only.

From `thermoRL/thermorl-v2`, after committing this preregistration:

```bash
uv run python -m thermorl2.experiments.probes g3 --system summit --out experiments/summit/E03_g3_room_air
```

G1 and G3 run as separate parallel processes, one FMU per process. Based on the G2 cost, approximate FMU wall costs are 41 minutes for G1 (17 simulated h including warm-up) and 19.5 minutes for G3 (8 simulated h); timing can vary by input and concurrent load. No outcome-dependent horizon adjustment.

## Metrics
Paired intervention minus control, averaged across affected racks and the final 1800 s (`9000 < t_s <= 10800`); report unaffected-rack mean difference too. USABLE iff the affected mean difference is >=1.0 °C and outputs are sane (finite, coolant <=70 °C). No alternative lever is tested if NOT_USABLE. List the modelDescription.xml variables satisfying the exact parameter/tunable/CDU-1 name filters, without setting any of them.

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
What-if: room-air cooling failure on one floor section (not observed summit behaviour). Room air is a model input, not evidence that this event occurred on Summit. A negative result drops the what-if; no post-result parameter tuning or substitute experiment.
## Provenance
Git state, immutable implementation/config/FMUs/input hashes, environment, backend=fmu, timings, policy/seed (not applicable) will be recorded.
## Demo relevance
Determine whether the frozen room-air what-if is available; no substitute lever is introduced.
