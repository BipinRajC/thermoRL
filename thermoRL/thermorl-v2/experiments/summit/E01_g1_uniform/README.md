# E01 — G1 five-level uniform-load physics (summit)
**System:** summit  **Status:** planned
**Pre-registered:** 2026-10-27; introducing commit to be recorded after commit (before execution).

## Question
What are the finite-horizon temperature–power relation, empirical response times, operating range and rack homogeneity on the selected primary?

## Pre-registered decision rule
The following is copied verbatim from design spec §4.2:

| Exp | Question | Protocol | Primary metric | Decision rule |
|---|---|---|---|---|
| **G1** Uniform sweep | T_ss(P), τ, operating range, rack homogeneity | From the snapshot (reset per level), all racks at `idle + f·(peak−idle)` for f ∈ {0, .25, .5, .75, 1}, 3 h each | Per-level mean/min/max rack °C over the final 15 min; 63 % time; linear fit a, b, R² | Freeze `a`, `b`, `τ` (median t63 over f ∈ {.25, .5, .75}). `t_hot_c` = fit at f = 0.9. Report whether 40 °C or 45 °C is reached. |

## Configuration
[config.yaml](config.yaml), JSON/YAML. Primary is selected mechanically by [X01](../../cross_system/X01_fmu_selection/README.md), not assumed. Power bounds and geometry come from RAPS configuration; FMU hash must match spec §3.1.

## Method
Run all racks at each f in {0,.25,.5,.75,1}, restoring the same capped snapshot before every level. Preserve full warm-up, per-rack coolant/pump/power and CDU-1/global ledgers, plus initial observations. Warm-up: exactly 7200 s at measured idle. Each level: 10800 s, dt=10 s, all ambient inputs 290 K. Check finite outputs and sampled coolant range. A negative settlement threshold enforces the prescribed cap. No time-constant acceptance bound is imposed.

From `thermoRL/thermorl-v2`, after committing this preregistration:

```bash
uv run python -m thermorl2.experiments.probes g1 --system summit --out experiments/summit/E01_g1_uniform
```

G1 and G3 run as separate parallel processes, one FMU per process. Based on the G2 cost, approximate FMU wall costs are 41 minutes for G1 (17 simulated h including warm-up) and 19.5 minutes for G3 (8 simulated h); timing can vary by input and concurrent load. No outcome-dependent horizon adjustment.

## Metrics
Final 15 minutes: `9900 < t_s <= 10800`, right-endpoint samples. Compute each rack's time mean, then mean/min/max across racks. t63 is the first mean-rack sample reaching 0.632 of the signed change from the snapshot to the final-window mean. For f=0 a negative change is reported as cooling/relaxation, not a heating time constant; zero change or no crossing is null. Fit all five points by ordinary least squares; report a, b, R², median t63 over .25/.5/.75, and fit at f=.9. Reach flags refer to any sampled coolant value across the branches. No level is dropped. A final-window average is an operating proxy, not certification of equilibrium.

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
The fitted T_ss notation denotes a final-window proxy over a fixed horizon. Capped warm-up and transients can affect the fitted parameters. Empirical t63 is protocol-specific and is not proof of a first-order plant with a constant time constant.
## Provenance
Git state, immutable implementation/config/FMUs/input hashes, environment, backend=fmu, timings, policy/seed (not applicable) will be recorded.
## Demo relevance
Freeze the model parameters and operating range before policy comparisons.
