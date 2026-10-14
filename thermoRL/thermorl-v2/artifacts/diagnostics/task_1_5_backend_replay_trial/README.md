# Task 1.5 independent replay gate: failed trial

The [fixed asymmetric sequence](sequence.json) was run through the [test-only direct FMPy helper](../../../tests/fmu/direct_fmu_replay.py) and the [backend helper](../../../tests/fmu/backend_replay.py) in separate OS processes. The full [direct output](direct.json) and [backend output](backend.json) are preserved. This is a **failed gate trial**, not acceptance evidence. The approved comparison test and its tolerances were not widened.

Both processes used the SHA-256-pinned Lassen FMU `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`; both recorded `warmup_used_s == 7200.0`, snapshot time 7200 s, identical elapsed arrays and communication points, and the prescribed heat/ambient inputs. The backend helper recorded the actual `doStep` communication points. For each replay pass, every direct-FMU and backend temperature/flow output agreed **exactly** at serialized precision (maximum difference 0).

| Variable | Direct replay 1 versus 2 maximum | Backend replay 1 versus 2 maximum | Direct versus backend maximum, either replay |
| --- | ---: | ---: | ---: |
| Rack coolant | **0.000143434 °C** | **0.000143434 °C** | 0 |
| CDU primary supply | 8.12×10⁻⁹ °C | 8.12×10⁻⁹ °C | 0 |
| CDU primary return | 7.74×10⁻⁸ °C | 7.74×10⁻⁸ °C | 0 |
| Datacenter primary flow | 2.50×10⁻⁸ GPM | 2.50×10⁻⁸ GPM | 0 |

Rack-coolant replay divergence first exceeds `1e-9` at elapsed **740 s** (sample 37), following the asymmetric phase transition. It is transient and later shrinks, but its maximum exceeds the approved `1e-9` within-process restore tolerance. The direct helper's JSON was byte-identical across two fresh-process test runs. A targeted direct-only diagnostic using FMI `doStep(..., noSetFMUStatePriorToCurrentPoint=False)` produced the same maximum; restoring a freshly deserialized copy of the snapshot also produced the same maximum. Those checks narrow the issue but do not prove which FMU-internal state or event causes it. [FMI 2.0](https://fmi-standard.org/assets/releases/FMI_for_ModelExchange_and_CoSimulation_v2.0.pdf) defines the rollback flag; no production semantics were changed during these checks.

Separate verification: the three existing lifecycle/reset/single-instance tests passed; the unchanged historical physical-response test failed at its **1240 s** assertion when run after its warm-up test; unit/integration baseline was **19 passed**. The historical test depends on the preceding warm-up test's module fixture and fails earlier at `reset()` if selected alone. No Task 1.5 commit was made, and Task 1.6 has not started.

The direct and backend helpers and their independent process comparison provide strong evidence of backend equivalence for this sequence. The **approved gate as a whole failed** because strict intra-process replay identity did not hold even for direct FMPy. The next step requires an explicit research/design decision; this file does not choose a new acceptance rule.
