# ThermoRL v2

This Python 3.12 project implements the Lassen closed-loop demonstration described in the [design spec](../../docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md). Run tests with `uv run pytest`.

## Phase 0 record

- `uv sync` resolved and installed on CPython 3.12.14 with RAPS as an editable path dependency; no dependency override was needed.
- `uv run pytest tests/unit/test_env_smoke.py -v`: 2 passed.
- Lassen CLI smoke (`10m`, random workload, 50 jobs, seed 1): exit 0; `Time Simulated: 0:10:00`.
- RAPS `tests/systems/test_engine_basic.py -k lassen -q`: 2 passed, 22 deselected, 0 skipped.
- Lassen FMU: `models/POWER9CSM/fmus/lassen.fmu` exists; SHA-256 `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`.
