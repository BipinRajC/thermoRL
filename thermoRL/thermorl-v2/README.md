# ThermoRL v2

This Python 3.12 project implements the Lassen closed-loop demonstration described in the [design spec](../../docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md). Run tests with `uv run pytest`.

## Phase 0 record

- `uv sync` resolved and installed on CPython 3.12.14 with RAPS as an editable path dependency; no dependency override was needed.
- `uv run pytest tests/unit/test_env_smoke.py -v`: 2 passed.
- Lassen CLI smoke (`10m`, random workload, 50 jobs, seed 1): exit 0; `Time Simulated: 0:10:00`.
- RAPS `tests/systems/test_engine_basic.py -k lassen -q`: 2 passed, 22 deselected, 0 skipped.
- Lassen FMU: `models/POWER9CSM/fmus/lassen.fmu` exists; SHA-256 `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`.

## Task 1.5 closure (option B)

Closed under option B, 2026-10-27, as approved by the [ParasParam design spec](../../../docs/superpowers/specs/2026-10-27-parasparam-demo-design.md) P1. Independent direct-FMU execution is the backend correctness reference. Both replay passes agree within the unchanged `atol=1e-6` direct/backend gate, and the backend's restore deviations match the direct reference at `atol=1e-6`. The observed maximum restore jitter is **0.000143434 °C** (approximately 1.43e-4 °C), a documented FMU limitation.

The historical physical-response test retains its complete body and 500–1000 s bound. It is marked `xfail(strict=True)`; its physical premise is unresolved, and an unexpected pass will fail the suite. The 7200 s snapshot is **capped/preconditioned, not settled**.

Verification on Arch Linux / Python 3.12.14: unit/integration **19 passed**; FMU **4 passed, 1 xfailed**. See the [closure manifest](experiments/lassen/E00_legacy_task15/provenance/option_b_manifest.json) and [legacy evidence index](experiments/lassen/E00_legacy_task15/README.md). No FMU or backend stepping semantics were changed.
