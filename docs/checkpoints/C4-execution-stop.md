# Task14 execution STOP — controller SIGTERM before C4

**Launch SHA:** `18dfea14aa42bc21a191cc1f9a39fc421d8723bd`. **Status:** C4 not reached; E12 G4 pending review; C′ not run.

## Facts

- Matrix tool session60914 returned exit143 (SIGTERM). First start:2026-10-30T19:34:24 UTC; exit observed around20:19 UTC, approximately45minutes later.
- Primary journal has7 starts and4 completed/validated runs. Complete: coolest_rack_seed1, node_balance_seed1, packing_seed1, power_balance_seed1.
- Partial: node_balance_seed2, packing_seed2, thermal_predictive_seed1. Eight primary configurations remain unstarted. No retry, rerun or new simulation was launched after the interruption.
- No matrix_stopped journal event or FMU failure.json exists. Listed worker PIDs were absent in the process check. Run/log sizes and mtimes were stable over the final30-second observation.
- Source hashes and HEAD still match launch SHA. Frozen README sections, inputs and policy/model definitions are unchanged.
- Prelaunch tests:157 unit +28 integration =185 passed. First-wave process times were1263.78 /1289.24 /1318.50s; completed workers peaked at1.79–1.99GiB RSS and recorded zero coolant samples above70°C.

## Interpretation and limits

**INFERENCE:** the near45-minute exit is consistent with a tool/session lifetime limit. The cause is not established. It is not evidence of a thermal, policy or FMU-correctness failure. No G4 outcome may be inferred from this incomplete matrix.

## Preservation

All complete and partial raw directories are retained in place and gitignored. The primary journal is unchanged. `experiments/summit/E12_g4_alibaba/provenance/interruption_inventory.json` records file paths, sizes and SHAs. `execution_interruption.json` records the observed state. No output was overwritten.

Committed preparation: f5d6dae (approved decisions),876e678 (pre-run regime),18dfea1 (tested engineering). These commits are pushed without a new commit. This stop report and interruption artifacts remain local/uncommitted because advancing HEAD would affect the exact C′ git.sha precondition.

## Required decision

STOP for Bipin-reviewed recovery. Three partial attempts cannot be silently retried under the original15+1 budget. Recovery must address controller lifetime, preservation/resume accounting, any source-freeze exception and the exact C′ Git/source preconditions. No source change, retry or additional experiment is authorized by this report.
