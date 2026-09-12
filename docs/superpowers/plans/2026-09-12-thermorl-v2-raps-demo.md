# ThermoRL v2 × RAPS Closed-Loop Demo (FMU arm) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the October-2026 closed-loop demo: RAPS (Lassen) supplies jobs, allocation and per-rack power; the adapter couples rack power into ORNL's Lassen cooling FMU; a rack-scoring heuristic controller places jobs on exact node sets; ledgers and plots show, per ramp phase, whether thermal state influenced placement and outcomes.

**Architecture:** New uv project `thermoRL/thermorl-v2/` (package `thermorl2`, Python 3.12). Three layers: `core` (RAPS/FMU/torch-agnostic types, placement, THI, metrics, heuristics), `thermal` (pluggable backend; `FmuBackend` owns the single fmpy instance and a warmed-idle state snapshot), `raps_adapter` (only package importing `raps`: engine factory, job injection, drop-in `RackScheduler`, runner, ramp workload generator). RAPS runs with its own cooling off; the adapter reproduces RAPS's FMU coupling formula.

**Tech Stack:** Python 3.12 via uv; `raps` as editable path dependency (`../../sim-raps`); fmpy 0.3.x; numpy, pandas, pyarrow, pyyaml, matplotlib, pytest.

**Spec:** `docs/superpowers/specs/2026-09-12-thermorl-v2-raps-demo-design.md` (read it first; this plan argues from it). Reconnaissance: `/home/bipin/.claude/plans/thermorl-exadigit-raps-quirky-bird.md`.

## Global Constraints

- Python `>=3.12,<3.13`; RAPS requires `>=3.12`; `thermoRL/thermoRL-new/` is frozen reference, never imported (its pin is `<3.12`).
- **No edits to `sim-raps/`** unless a task explicitly says so; any edit must be recorded in `sim-raps/PATCHES.md` (problem, rationale, exact change, regression test) and approved per spec D2. Expected for this plan: zero patches.
- `core/` must not import `raps`, `fmpy`, or `torch`. `raps_adapter/` is the only package importing `raps`. `thermal/fmu_backend.py` is the only module importing `fmpy`.
- FMU path: `/home/bipin/thermoRL/models/POWER9CSM/fmus/lassen.fmu` (SHA-256 `2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b`). Exactly one FMU instance per OS process; never re-instantiate on reset.
- RAPS coupling constants come from the Lassen legacy config: `COOLING_EFFICIENCY = 0.945`, `RACKS_PER_CDU = 1`, `WET_BULB_TEMP = 290.0` (K), `POWER_UPDATE_FREQ = 20` (s). Adapter `time_delta = 20 s`, `time_unit = 1 s`.
- Seeds are integers `>= 1` (RAPS ignores seed 0). Reset `raps.job.Job._id_counter = 0` before building each episode's jobs.
- All randomness in the workload generator goes through one `numpy.random.default_rng(seed)`.
- Every run writes a manifest (git SHA, config, workload SHA-256, controller name/version/config hash, timings). Metrics are computed **only** from ledgers.
- THI, ε = 0.10, T_max = 45 °C and ramp targets are read from YAML config, never hard-coded in logic, never tuned on results.
- **Stop and report** (do not improvise) on: any unexpected test failure; any discovery contradicting the spec; missing/semantically different FMU observables; questionable physical assumptions; anything needing a RAPS patch; anything requiring a research/design decision; the Phase 1 characterisation numbers.
- Commit after every task with the message given; use `git -C /home/bipin/thermoRL`. All paths below are relative to `/home/bipin/thermoRL/` unless absolute.
- Run tests with the project interpreter: `cd thermoRL/thermorl-v2 && uv run pytest ...`.

## File map (created by this plan)

```
thermoRL/thermorl-v2/
  pyproject.toml, README.md, .python-version
  thermorl2/__init__.py
  thermorl2/core/__init__.py
  thermorl2/core/state.py            RackResource, RackThermal, GlobalFeatures, JobRequest, Observation, Scores, Placement, Ambient
  thermorl2/core/placement.py        feasible_mask(), place()
  thermorl2/core/constraints.py      thi(), hinge(), violation()
  thermorl2/core/kernels/__init__.py, rc.py, thi.py   (copied from thermoRL-new, attribution header)
  thermorl2/core/scoring.py          RackScorer protocol, ScorerInfo
  thermorl2/core/heuristics/__init__.py, lowest_id.py, round_robin.py, load_balance.py, threshold_reactive.py, coolest_rack.py, forced_rack.py
  thermorl2/core/ledger.py           DecisionRow, IntervalRow, Manifest, LedgerWriter
  thermorl2/core/energy.py           it_energy_kwh(), cdu_pump_energy_kwh()
  thermorl2/core/metrics.py          metric hierarchy from ledgers
  thermorl2/thermal/__init__.py, base.py, fmu_backend.py
  thermorl2/raps_adapter/__init__.py
  thermorl2/raps_adapter/coupling.py       rack_kw_to_fmu_inputs()  (RAPS formula)
  thermorl2/raps_adapter/rack_geometry.py  RackGeometry
  thermorl2/raps_adapter/power_probe.py    rack_kw_from_power_df(), reconcile_total()
  thermorl2/raps_adapter/jobs.py           jobs_from_parquet()
  thermorl2/raps_adapter/engine_factory.py build_engine()
  thermorl2/raps_adapter/rack_scheduler.py RackScheduler
  thermorl2/raps_adapter/observation.py    ObservationBuilder
  thermorl2/raps_adapter/runner.py         EpisodeRunner
  thermorl2/raps_adapter/workload/__init__.py, ramp_generator.py
  thermorl2/experiments/__init__.py, characterise.py, run_demo.py, plots.py
  thermorl2/experiments/configs/lassen_fmu.yaml, demo_ramp_lassen.yaml, smoke_2h.yaml
  tests/conftest.py, tests/unit/*, tests/integration/*, tests/fmu/*, tests/golden/kernel_vectors.json
```

---

# Phase 0 — Environment

### Task 0.1: Create the uv project and verify RAPS + fmpy import from one interpreter

**Files:**
- Create: `thermoRL/thermorl-v2/pyproject.toml`, `thermoRL/thermorl-v2/.python-version`, `thermoRL/thermorl-v2/README.md`, `thermoRL/thermorl-v2/thermorl2/__init__.py`, `thermoRL/thermorl-v2/tests/__init__.py`, `thermoRL/thermorl-v2/tests/conftest.py`, `thermoRL/thermorl-v2/tests/unit/test_env_smoke.py`

**Interfaces:**
- Produces: importable package `thermorl2`; `tests/conftest.py` fixtures `fmu_path` (Path, skips if absent) and `repo_root` (Path).

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "thermorl2"
version = "0.1.0"
description = "ThermoRL v2: rack-level thermal-aware placement on the ExaDigiT/RAPS digital twin"
requires-python = ">=3.12,<3.13"
dependencies = [
  "raps",
  "fmpy>=0.3.19",
  "numpy>=1.26",
  "pandas>=2.2",
  "pyarrow>=16.0",
  "pyyaml>=6.0",
  "matplotlib>=3.7",
  "pytest>=8.0",
]

[tool.uv.sources]
raps = { path = "../../sim-raps", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["thermorl2"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["fmu: needs models/POWER9CSM/fmus/lassen.fmu", "integration: needs raps importable", "slow: > 60 s"]
```

`.python-version` contains `3.12`. README: one paragraph pointing to the spec and stating "run tests with `uv run pytest`".

- [ ] **Step 2: Sync**

Run: `cd /home/bipin/thermoRL/thermoRL/thermorl-v2 && uv sync 2>&1 | tail -20`
Expected: resolves and installs; `raps` appears as editable. **If resolution fails** because of RAPS's pins (`stable-baselines3==2.7.0`, `gym==0.26.2`, `pre-commit`), add to `pyproject.toml`:

```toml
[tool.uv]
override-dependencies = [
  "stable-baselines3 ; sys_platform == 'never'",
  "gym ; sys_platform == 'never'",
  "pre-commit ; sys_platform == 'never'",
  "gcsfs ; sys_platform == 'never'",
  "boto3 ; sys_platform == 'never'",
]
```
and re-run `uv sync`. Record which path was needed in README. If it still fails: **stop and report** the resolver output.

- [ ] **Step 3: Write conftest and smoke test**

`tests/conftest.py`:
```python
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]          # /home/bipin/thermoRL
FMU_PATH = REPO_ROOT / "models" / "POWER9CSM" / "fmus" / "lassen.fmu"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def fmu_path() -> Path:
    if not FMU_PATH.exists():
        pytest.skip(f"FMU not found at {FMU_PATH}")
    return FMU_PATH
```

`tests/unit/test_env_smoke.py`:
```python
import importlib


def test_raps_and_fmpy_importable():
    assert importlib.import_module("raps.engine").Engine
    assert importlib.import_module("fmpy").__version__


def test_thermorl2_importable():
    import thermorl2
    assert thermorl2.__name__ == "thermorl2"
```

- [ ] **Step 4: Run**

Run: `uv run pytest tests/unit/test_env_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 5: RAPS CLI smoke on Lassen**

Run: `cd /home/bipin/thermoRL/sim-raps && /home/bipin/thermoRL/thermoRL/thermorl-v2/.venv/bin/python main.py run --system lassen -t 10m --noui -w random -n 50 --seed 1 -o none 2>&1 | tail -15`
Expected: exit code 0 and a printed stats report containing `Time Simulated`. If it fails: **stop and report** the traceback (do not patch RAPS).

- [ ] **Step 6: RAPS's own engine test for Lassen**

Run: `cd /home/bipin/thermoRL/sim-raps && /home/bipin/thermoRL/thermoRL/thermorl-v2/.venv/bin/python -m pytest tests/systems/test_engine_basic.py -k lassen -q 2>&1 | tail -5`
Expected: tests for lassen pass (others may be deselected). Record the exact pass/skip counts in README under "Phase 0 record".

- [ ] **Step 7: Commit**

```bash
git -C /home/bipin/thermoRL add thermoRL/thermorl-v2 docs/superpowers
git -C /home/bipin/thermoRL commit -m "feat(thermorl2): scaffold uv project with editable RAPS dependency and env smoke tests"
```

---

# Phase 1 — Core types, kernels, geometry, coupling, FMU backend, characterisation

### Task 1.1: Core state types

**Files:**
- Create: `thermorl2/core/__init__.py` (empty), `thermorl2/core/state.py`
- Test: `tests/unit/test_state.py`

**Interfaces:**
- Produces (used by every later task):
```python
@dataclass(frozen=True) class Ambient: t_air_k: float = 290.0; t_ext_k: float = 290.0
@dataclass class RackResource: free_nodes: np.ndarray[int]; total_nodes: np.ndarray[int]; power_kw: np.ndarray[float]; n_running: np.ndarray[int]; t_next_limit_s: np.ndarray[float]
@dataclass class RackThermal: t_c: np.ndarray[float]; extras: dict[str, np.ndarray]
@dataclass class GlobalFeatures: sim_time_s: float; total_power_kw: float; queue_depth: int; queued_power_kw: float; backend: dict[str, float]
@dataclass(frozen=True) class JobRequest: job_id: int; nodes_required: int; est_power_per_node_kw: float; time_limit_s: float; wait_s: float; priority: int; defer_count: int
@dataclass class Observation: rack: RackResource; thermal: RackThermal; thi: np.ndarray[float]; glob: GlobalFeatures
@dataclass(frozen=True) class Scores: rack: np.ndarray[float]; defer: float
@dataclass(frozen=True) class Placement: racks: tuple[int, ...]; nodes: tuple[int, ...]; rule: str   # rule ∈ {"single_best","greedy_span","defer"}
DEFER = Placement(racks=(), nodes=(), rule="defer")
```

- [ ] **Step 1: Failing test**

```python
# tests/unit/test_state.py
import numpy as np
from thermorl2.core.state import Ambient, RackResource, RackThermal, JobRequest, Placement, DEFER


def test_defaults_and_shapes():
    amb = Ambient()
    assert amb.t_air_k == 290.0 and amb.t_ext_k == 290.0
    rr = RackResource(free_nodes=np.full(44, 18), total_nodes=np.full(44, 18),
                      power_kw=np.zeros(44), n_running=np.zeros(44, dtype=int),
                      t_next_limit_s=np.full(44, np.inf))
    assert rr.free_nodes.shape == (44,)
    th = RackThermal(t_c=np.full(44, 30.0), extras={})
    assert th.t_c.dtype.kind == "f"
    assert DEFER.rule == "defer" and DEFER.nodes == ()
    j = JobRequest(job_id=1, nodes_required=4, est_power_per_node_kw=1.9, time_limit_s=3600,
                   wait_s=0.0, priority=0, defer_count=0)
    assert j.nodes_required == 4
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/test_state.py -v` → FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `thermorl2/core/state.py`** with exactly the dataclasses in the Interfaces block (`from __future__ import annotations`, `import numpy as np`, `from dataclasses import dataclass, field`). `RackThermal.extras` defaults to `field(default_factory=dict)`. `GlobalFeatures.backend` defaults to empty dict.

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit** `git -C /home/bipin/thermoRL commit -am "feat(core): state dataclasses for rack/thermal/job/observation/placement"` (after `git add thermoRL/thermorl-v2`).

---

### Task 1.2: Kernels copied from thermoRL-new + THI/hinge

**Files:**
- Create: `thermorl2/core/kernels/__init__.py`, `thermorl2/core/kernels/rc.py`, `thermorl2/core/kernels/thi.py`, `thermorl2/core/constraints.py`, `tests/golden/kernel_vectors.json`
- Test: `tests/unit/test_kernels.py`, `tests/unit/test_constraints.py`

**Interfaces:**
- Produces: `rc_alpha(tau_s, dt_s) -> float`; `rc_step(T, T_ss, tau, dt_s) -> np.ndarray`; `t_steady(Q, Q_max, T_amb, T_max) -> np.ndarray` (all copied verbatim); `thi_headroom(t_c, t_idle_c, t_max_c, p_kw, p_max_kw) -> np.ndarray` ; `thi_paper_raw(t_c, t_max_c, p_kw, p_max_kw) -> np.ndarray`; `hinge(thi, eps) -> np.ndarray`; `violation(thi, eps) -> np.ndarray[bool]`; `compute_thi(form, ...)` dispatcher with `form ∈ {"headroom","paper_raw"}`.

- [ ] **Step 1: Copy kernels.** Copy `thermoRL/thermoRL-new/thermorl/sim/kernels/rc.py` → `thermorl2/core/kernels/rc.py` and the `t_steady` function from `thermoRL/thermoRL-new/thermorl/sim/kernels/thi.py` → `thermorl2/core/kernels/thi.py`, each with header `# Copied verbatim from thermoRL-new (thermorl/sim/kernels/...), 2026-09-12.` Copy `thermoRL/thermoRL-new/tests/golden/kernel_vectors.json` → `tests/golden/kernel_vectors.json`. Do **not** copy `thi_batch` (uses T_ss/T_max variant) or degradation/pue.

- [ ] **Step 2: Failing tests**

```python
# tests/unit/test_kernels.py
import json, numpy as np
from pathlib import Path
from thermorl2.core.kernels.rc import rc_alpha, rc_step
from thermorl2.core.kernels.thi import t_steady

G = json.loads((Path(__file__).parents[1] / "golden" / "kernel_vectors.json").read_text())


def test_rc_alpha_golden():
    g = G["rc_alpha"]
    assert abs(rc_alpha(60.0, g["dt_s"]) - g["air"]) < 1e-12
    assert abs(rc_alpha(15.0, g["dt_s"]) - g["d2c"]) < 1e-12
    assert abs(rc_alpha(300.0, g["dt_s"]) - g["immersion"]) < 1e-12


def test_rc_step_golden():
    g = G["rc_step_air"]
    out = rc_step(np.array([g["T"]], np.float32), np.array([g["T_ss"]], np.float32),
                  np.array([g["tau_s"]], np.float32), g["dt_s"])
    assert abs(float(out[0]) - g["expected"]) < 1e-5


def test_t_steady_golden():
    g = G["t_steady_air_mid"]
    out = t_steady(np.array([g["Q"]]), np.array([g["Q_max"]]), np.array([g["T_amb"]]), np.array([g["T_max"]]))
    assert abs(float(out[0]) - g["expected"]) < 1e-5
```

```python
# tests/unit/test_constraints.py
import numpy as np
from thermorl2.core.constraints import thi_headroom, thi_paper_raw, hinge, violation, compute_thi


def test_headroom_is_one_at_idle_zero_power():
    out = thi_headroom(np.array([30.0]), np.array([30.0]), 45.0, np.array([0.0]), 36.0)
    assert out[0] == 1.0


def test_headroom_is_zero_at_limit():
    out = thi_headroom(np.array([45.0]), np.array([30.0]), 45.0, np.array([0.0]), 36.0)
    assert abs(out[0]) < 1e-9


def test_power_term_dominates_paper_example():
    # paper: Q/Qmax = 0.95 -> THI = 0.05 when temperature term is smaller
    out = thi_paper_raw(np.array([20.0]), 45.0, np.array([34.2]), 36.0)
    assert abs(out[0] - 0.05) < 1e-9


def test_clip_to_minus_half_one():
    out = thi_headroom(np.array([80.0]), np.array([30.0]), 45.0, np.array([0.0]), 36.0)
    assert out[0] == -0.5


def test_hinge_and_violation():
    thi = np.array([0.5, 0.10, 0.05, -0.2])
    np.testing.assert_allclose(hinge(thi, 0.10), [0.0, 0.0, 0.05, 0.30])
    assert violation(thi, 0.10).tolist() == [False, False, True, True]


def test_dispatcher():
    a = compute_thi("headroom", t_c=np.array([37.5]), t_idle_c=np.array([30.0]), t_max_c=45.0,
                    p_kw=np.array([18.0]), p_max_kw=36.0)
    assert abs(a[0] - 0.5) < 1e-9
```

- [ ] **Step 3: Run** both → FAIL.

- [ ] **Step 4: Implement `thermorl2/core/constraints.py`**

```python
from __future__ import annotations
import numpy as np

THI_MIN, THI_MAX = -0.5, 1.0


def _safe_div(a, b):
    b = np.asarray(b, dtype=np.float64)
    return np.divide(np.asarray(a, dtype=np.float64), b, out=np.zeros_like(b), where=b != 0)


def thi_headroom(t_c, t_idle_c, t_max_c, p_kw, p_max_kw):
    """Baseline-normalised headroom index (spec §7 primary). 1.0 at idle & zero power, 0.0 at limit."""
    t_term = _safe_div(np.asarray(t_c) - np.asarray(t_idle_c), np.asarray(t_max_c) - np.asarray(t_idle_c))
    p_term = _safe_div(p_kw, p_max_kw)
    return np.clip(1.0 - np.maximum(t_term, p_term), THI_MIN, THI_MAX)


def thi_paper_raw(t_c, t_max_c, p_kw, p_max_kw):
    """Paper eq. 1 without the degradation term: 1 - max(T/Tmax, P/Pmax), T in degC."""
    return np.clip(1.0 - np.maximum(_safe_div(t_c, t_max_c), _safe_div(p_kw, p_max_kw)), THI_MIN, THI_MAX)


def compute_thi(form: str, *, t_c, t_max_c, p_kw, p_max_kw, t_idle_c=None):
    if form == "headroom":
        if t_idle_c is None:
            raise ValueError("headroom form requires t_idle_c")
        return thi_headroom(t_c, t_idle_c, t_max_c, p_kw, p_max_kw)
    if form == "paper_raw":
        return thi_paper_raw(t_c, t_max_c, p_kw, p_max_kw)
    raise ValueError(f"unknown thi form {form!r}")


def hinge(thi, eps: float):
    return np.maximum(0.0, eps - np.asarray(thi, dtype=np.float64))


def violation(thi, eps: float):
    return np.asarray(thi) < eps
```

- [ ] **Step 5: Run** → all PASS.

- [ ] **Step 6: Commit** `feat(core): copy RC/t_steady kernels with golden tests; add headroom and paper THI, hinge, violation`

---

### Task 1.3: Rack geometry (node id ↔ rack, free nodes per rack)

**Files:**
- Create: `thermorl2/raps_adapter/__init__.py` (empty), `thermorl2/raps_adapter/rack_geometry.py`
- Test: `tests/unit/test_rack_geometry.py`

**Interfaces:**
- Produces:
```python
@dataclass(frozen=True) class RackGeometry:
    num_cdus: int; racks_per_cdu: int; nodes_per_rack: int
    n_racks: property -> int                       # num_cdus * racks_per_cdu
    total_nodes: property -> int
    rack_of(node_id: int) -> int                   # node_id // nodes_per_rack
    nodes_of(rack: int) -> range
    free_per_rack(available_nodes: Iterable[int]) -> np.ndarray[int]   # counts, length n_racks
    free_nodes_in_rack(rack: int, available_nodes: Iterable[int], k: int) -> list[int]  # k lowest free ids in rack
    @classmethod from_legacy_config(cfg: dict) -> RackGeometry   # cfg keys NUM_CDUS, RACKS_PER_CDU, NODES_PER_RACK
```
Pure Python/numpy; no `raps` import (the legacy dict is passed in).

- [ ] **Step 1: Failing test**

```python
import numpy as np
from thermorl2.raps_adapter.rack_geometry import RackGeometry


def geo():
    return RackGeometry(num_cdus=44, racks_per_cdu=1, nodes_per_rack=18)


def test_rack_of_and_nodes_of():
    g = geo()
    assert g.n_racks == 44 and g.total_nodes == 792
    assert g.rack_of(0) == 0 and g.rack_of(17) == 0 and g.rack_of(18) == 1 and g.rack_of(791) == 43
    assert list(g.nodes_of(43)) == list(range(774, 792))


def test_free_per_rack_and_lowest_free():
    g = geo()
    avail = [0, 1, 5, 18, 19, 791]
    counts = g.free_per_rack(avail)
    assert counts[0] == 3 and counts[1] == 2 and counts[43] == 1 and counts.sum() == 6
    assert g.free_nodes_in_rack(0, avail, 2) == [0, 1]
    assert g.free_nodes_in_rack(1, avail, 5) == [18, 19]   # fewer than k available -> returns what exists


def test_from_legacy_config():
    g = RackGeometry.from_legacy_config({"NUM_CDUS": 44, "RACKS_PER_CDU": 1, "NODES_PER_RACK": 18})
    assert g.n_racks == 44
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (use `np.bincount(np.asarray(list(avail)) // nodes_per_rack, minlength=n_racks)` for counts; `sorted(n for n in avail if lo <= n < hi)[:k]` for lowest free). **Step 4: Run** → PASS.

- [ ] **Step 5: Commit** `feat(adapter): rack geometry from RAPS sc_shape arithmetic`

---

### Task 1.4: RAPS→FMU coupling formula (must equal RAPS's own)

**Files:**
- Create: `thermorl2/raps_adapter/coupling.py`
- Test: `tests/unit/test_coupling.py` (unit part), `tests/integration/test_coupling_equals_raps.py`

**Interfaces:**
- Produces:
```python
@dataclass(frozen=True) class CouplingParams: num_cdus: int; racks_per_cdu: int; cooling_efficiency: float; temperature_keys: tuple[str, ...]; wet_bulb_temp_k: float
    @classmethod from_legacy_config(cfg: dict) -> CouplingParams   # NUM_CDUS, RACKS_PER_CDU, COOLING_EFFICIENCY, TEMPERATURE_KEYS, WET_BULB_TEMP
def power_input_names(p: CouplingParams) -> list[str]   # f"simulator_1_datacenter_1_computeBlock_{i+1}_cabinet_1_sources_Q_flow_total"
def rack_kw_to_fmu_inputs(rack_kw: np.ndarray, p: CouplingParams, ambient: Ambient) -> dict[str, float]
```
Formula (spec §5.2, RAPS `cooling.py:145-166`): `Q_i = rack_kw[i]*1000 * cooling_efficiency / racks_per_cdu` for each CDU (for Lassen racks_per_cdu = 1 so rack i == CDU i); every `temperature_keys` entry → `ambient.t_air_k` except keys ending in `_T_ext` → `ambient.t_ext_k`. (RAPS uses one scalar for both; with default `Ambient()` both are 290.0 so results are identical.)

- [ ] **Step 1: Failing unit test**

```python
import numpy as np
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, rack_kw_to_fmu_inputs, power_input_names

P = CouplingParams(num_cdus=3, racks_per_cdu=1, cooling_efficiency=0.945,
                   temperature_keys=("a_T_Air", "b_T_Air", "simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"),
                   wet_bulb_temp_k=290.0)


def test_power_scaling_and_names():
    out = rack_kw_to_fmu_inputs(np.array([10.0, 0.0, 40.0]), P, Ambient())
    names = power_input_names(P)
    assert names[0] == "simulator_1_datacenter_1_computeBlock_1_cabinet_1_sources_Q_flow_total"
    assert abs(out[names[0]] - 9450.0) < 1e-9 and out[names[1]] == 0.0 and abs(out[names[2]] - 37800.0) < 1e-9


def test_temperature_keys_default_290():
    out = rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient())
    assert out["a_T_Air"] == 290.0 and out["simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"] == 290.0
    assert len(out) == 6


def test_ambient_override_splits_air_and_ext():
    out = rack_kw_to_fmu_inputs(np.zeros(3), P, Ambient(t_air_k=295.0, t_ext_k=288.0))
    assert out["a_T_Air"] == 295.0 and out["simulator_1_centralEnergyPlant_1_coolingTowerLoop_1_sources_T_ext"] == 288.0
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** exactly per Interfaces. **Step 4: Run** → PASS.

- [ ] **Step 5: Integration equality test against RAPS** (`tests/integration/test_coupling_equals_raps.py`, mark `integration`):

```python
import numpy as np, pytest
from raps.system_config import get_system_config
from raps.cooling import ThermoFluidsModel
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams, rack_kw_to_fmu_inputs

pytestmark = pytest.mark.integration


def test_adapter_inputs_equal_raps_generate_runtime_values():
    legacy = get_system_config("lassen").get_legacy()
    tfm = ThermoFluidsModel(**legacy)                 # no initialize(): no FMU needed
    rng = np.random.default_rng(1)
    rack_kw = rng.uniform(5.0, 36.0, size=legacy["NUM_CDUS"])
    raps_inputs = tfm.generate_runtime_values(rack_kw * 1000.0, engine=None)   # RAPS: cdu_power in W
    ours = rack_kw_to_fmu_inputs(rack_kw, CouplingParams.from_legacy_config(legacy), Ambient())
    assert set(ours) == set(raps_inputs)
    for k in raps_inputs:
        assert ours[k] == pytest.approx(raps_inputs[k], rel=0, abs=1e-9), k
```
Run: `uv run pytest tests/integration/test_coupling_equals_raps.py -v` → PASS (89 keys for Lassen). If `generate_runtime_values` signature or key set differs: **stop and report**.

- [ ] **Step 6: Commit** `feat(adapter): RAPS-equivalent rack power to FMU input coupling with equality test`

---

### Task 1.5: FMU thermal backend (single instance, snapshot reset, RAPS-identical stepping)

**Files:**
- Create: `thermorl2/thermal/__init__.py` (empty), `thermorl2/thermal/base.py`, `thermorl2/thermal/fmu_backend.py`
- Test: `tests/fmu/test_fmu_backend.py` (mark `fmu`; uses `fmu_path` fixture)

**Interfaces:**
- Produces (`thermal/base.py`):
```python
class ThermalBackend(Protocol):
    n_units: int
    def reset(self) -> None
    def step(self, unit_power_kw: np.ndarray, dt_s: float, ambient: Ambient) -> None
    def observe(self) -> RackThermal
    def global_observe(self) -> dict[str, float]
    def runtime_s(self) -> float
```
- Produces (`thermal/fmu_backend.py`):
```python
class FmuBackend:
    def __init__(self, fmu_path: Path, coupling: CouplingParams, extra_rack_vars: dict[str, str] | None = None,
                 global_vars: dict[str, str] | None = None, tolerance: float = 1e-5)
    # default extra_rack_vars = {"T_sec_r_C": "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary.T_sec_r_C",
    #                            "T_sec_s_C": "...T_sec_s_C", "W_flow_CDUP_kW": "...W_flow_CDUP_kW", "V_flow_sec_GPM": "...V_flow_sec_GPM"}
    # rack temperature var  = "simulator[1].datacenter[1].computeBlock[{i}].cabinet[1].volume.medium.T"   (K -> degC)
    # default global_vars   = {"fmu.T_prim_supply_C": "simulator[1].datacenter[1].computeBlock[1].cdu[1].summary.T_prim_s_C",
    #                          "fmu.T_prim_return_C": "...computeBlock[1].cdu[1].summary.T_prim_r_C",
    #                          "fmu.V_flow_prim_GPM": "simulator[1].datacenter[1].summary.V_flow_prim_GPM"}
    n_units: int                       # = coupling.num_cdus
    time_s: float                      # FMU communication point
    def warm_up(self, idle_rack_kw: np.ndarray, ambient: Ambient, dt_s: float, max_s: float = 7200.0,
                settle_k_per_min: float = 0.01) -> float      # steps until every rack |dT/dt| and T_prim_supply < threshold (checked over 5-min window) or max_s; then takes snapshot; returns warm-up seconds used
    def reset(self) -> None            # setFMUstate(snapshot); time_s = 0.0
    def step(self, unit_power_kw, dt_s, ambient) -> None
    def observe(self) -> RackThermal   # t_c = cabinet coolant T in degC; extras = extra_rack_vars arrays
    def global_observe(self) -> dict[str, float]
    def runtime_s(self) -> float
    def save_state(self) -> object ; def restore_state(self, handle) -> None ; def free_state(self, handle) -> None
    def close(self) -> None            # terminate + freeInstance; idempotent
```
Implementation notes: use `fmpy.extract`, `fmpy.read_model_description`, `fmpy.fmi2.FMU2Slave(guid=md.guid, unzipDirectory=unzipdir, modelIdentifier=md.coSimulation.modelIdentifier, instanceName="thermorl2")`; `instantiate(); setupExperiment(tolerance=tolerance, startTime=0.0); enterInitializationMode(); exitInitializationMode()` (mirrors RAPS `cooling.py:124-131`, adding tolerance from `DefaultExperiment`). Resolve value references once from `md.modelVariables` by name (raise `KeyError` listing missing names — **stop and report** if any default var is missing). `step`: `setReal(input_vrs, values)` in the fixed `power_input_names + temperature_keys` order, `doStep(self.time_s, dt_s)`, `self.time_s += dt_s`. Snapshot: `self._snapshot = self.fmu.getFMUstate()` after warm-up; `reset`: `self.fmu.setFMUstate(self._snapshot)`; `time_s = 0.0`. Because FMI time continues from the snapshot's internal time, keep `self._snapshot_time_s` and pass `currentCommunicationPoint = self._snapshot_time_s + self.time_s` to `doStep`. Module-level guard: a second `FmuBackend` in the same process raises `RuntimeError("canBeInstantiatedOnlyOncePerProcess")` unless the first was closed. Wall time accumulates around fmpy calls.

- [ ] **Step 1: Failing tests** (`tests/fmu/test_fmu_backend.py`)

```python
import numpy as np, pytest, time
from raps.system_config import get_system_config
from thermorl2.core.state import Ambient
from thermorl2.raps_adapter.coupling import CouplingParams
from thermorl2.thermal.fmu_backend import FmuBackend

pytestmark = pytest.mark.fmu


@pytest.fixture(scope="module")
def backend(fmu_path):
    cp = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    b = FmuBackend(fmu_path, cp)
    yield b
    b.close()


def test_warm_up_settles_and_observe_shapes(backend):
    used = backend.warm_up(np.full(44, 10.86), Ambient(), dt_s=20.0, max_s=7200.0)
    assert 600.0 <= used <= 7200.0
    th = backend.observe()
    assert th.t_c.shape == (44,) and 15.0 < th.t_c.min() and th.t_c.max() < 45.0
    assert set(th.extras) >= {"T_sec_r_C", "T_sec_s_C", "W_flow_CDUP_kW"}
    g = backend.global_observe()
    assert "fmu.T_prim_supply_C" in g and 5.0 < g["fmu.T_prim_supply_C"] < 40.0


def test_reset_reproduces_trajectory(backend):
    backend.reset()
    p = np.full(44, 10.86); p[0] = 35.0
    a = [backend.step(p, 20.0, Ambient()) or backend.observe().t_c.copy() for _ in range(30)]
    backend.reset()
    b = [backend.step(p, 20.0, Ambient()) or backend.observe().t_c.copy() for _ in range(30)]
    np.testing.assert_allclose(np.array(a), np.array(b), atol=1e-9)


def test_single_rack_step_is_local_and_matches_probe(backend):
    backend.reset()
    idle = backend.observe().t_c.copy()
    p = np.full(44, 10.0); p[0] = 40.0
    t = []
    for _ in range(int(3600 / 20)):
        backend.step(p, 20.0, Ambient()); t.append(backend.observe().t_c.copy())
    t = np.array(t)
    rise0 = t[-1, 0] - idle[0]
    assert rise0 > 4.0                                   # probe: +5.8 degC after 10->40 kW
    frac = (t[:, 0] - idle[0]) / rise0
    t63 = 20.0 * int(np.argmax(frac >= 0.632))
    assert 500.0 <= t63 <= 1000.0                        # probe: ~750 s, tolerance 20-33 %
    assert abs(t[-1, 1] - idle[1]) < 0.5 and abs(t[-1, 43] - idle[43]) < 0.5


def test_second_instance_in_process_is_refused(backend, fmu_path):
    cp = CouplingParams.from_legacy_config(get_system_config("lassen").get_legacy())
    with pytest.raises(RuntimeError):
        FmuBackend(fmu_path, cp)
```
(Note: in `test_reset_reproduces_trajectory` the list comprehension uses `step(...) or observe()` because `step` returns None.)

- [ ] **Step 2: Run** `uv run pytest tests/fmu -v` → FAIL (import). **Step 3: Implement** `base.py` and `fmu_backend.py` per Interfaces. **Step 4: Run** → PASS (expect ~30–60 s total). If `test_single_rack_step_is_local_and_matches_probe` fails on the τ bounds, **stop and report** the measured value (do not widen bounds).

- [ ] **Step 5: Commit** `feat(thermal): FMU backend with single-instance guard, warm-up snapshot reset, RAPS-identical stepping`

---

### Task 1.6: Engine factory, per-rack power probe, timing-semantics test, cost benchmark

**Files:**
- Create: `thermorl2/raps_adapter/engine_factory.py`, `thermorl2/raps_adapter/power_probe.py`
- Test: `tests/integration/test_engine_factory.py`, `tests/integration/test_timing_semantics.py`

**Interfaces:**
- Produces (`engine_factory.py`):
```python
@dataclass(frozen=True) class EngineSpec: system: str = "lassen"; sim_time: str = "24h"; time_delta: str = "20s"; seed: int = 1
def build_engine(spec: EngineSpec, jobs: list["raps.job.Job"] | None = None) -> "raps.engine.Engine"
    # SingleSimConfig.model_validate({"system": spec.system, "time": spec.sim_time, "time_delta": spec.time_delta,
    #   "workload": "random", "numjobs": 1, "seed": spec.seed, "noui": True, "output": "none", "cooling": False,
    #   "scheduler": "default", "policy": "fcfs"})
    # engine = Engine(cfg); if jobs is not None: engine.jobs = jobs; engine.total_initial_jobs = len(jobs)
    # asserts engine.timestep_start == 0 and engine.time_delta == 20 (int seconds); returns engine (generator NOT yet created)
def legacy_config(system: str = "lassen") -> dict          # get_system_config(system).get_legacy()
def idle_rack_kw(cfg: dict) -> float                        # 18 * compute_node_power(0,0,0,cfg)[0]/1000 + SWITCHES_PER_CHASSIS*POWER_SWITCH/1000 * CHASSIS_PER_RACK
def peak_rack_kw(cfg: dict) -> float                        # same with compute_node_power(CPUS_PER_NODE, GPUS_PER_NODE, 1.0, cfg)
```
- Produces (`power_probe.py`):
```python
def rack_kw_from_power_df(power_df: "pd.DataFrame", racks_per_cdu: int) -> np.ndarray   # concat columns "Rack 1".."Rack n" row-major (CDU-major) -> length num_cdus*racks_per_cdu
def reconcile_total(power_df, cfg: dict) -> float           # power_df["Sum"].sum() + cfg["NUM_CDUS"]*cfg["POWER_CDU"]/1000
def is_power_tick(tick, time_delta: int) -> bool            # tick.current_timestep % time_delta == 0
```

- [ ] **Step 1: Failing tests**

```python
# tests/integration/test_engine_factory.py
import numpy as np, pytest
from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine, legacy_config, idle_rack_kw, peak_rack_kw
from thermorl2.raps_adapter.power_probe import rack_kw_from_power_df, reconcile_total, is_power_tick

pytestmark = pytest.mark.integration


def test_build_engine_lassen_defaults():
    e = build_engine(EngineSpec(sim_time="2m"))
    assert e.timestep_start == 0 and e.time_delta == 20
    assert e.config["NUM_CDUS"] == 44 and e.config["NODES_PER_RACK"] == 18
    assert e.cooling_model is None


def test_idle_and_peak_rack_power_bounds():
    cfg = legacy_config()
    idle, peak = idle_rack_kw(cfg), peak_rack_kw(cfg)
    assert 8.0 < idle < 14.0 and 30.0 < peak < 40.0        # hand calc: ~10.9 kW idle, ~35.9 kW peak


def test_power_df_reconciles_with_total_power_on_idle_run():
    e = build_engine(EngineSpec(sim_time="2m"), jobs=[])
    cfg = e.config
    n_power_ticks = 0
    for tick in e.run_simulation():
        if is_power_tick(tick, e.time_delta):
            n_power_ticks += 1
            kw = rack_kw_from_power_df(tick.power_df, cfg["RACKS_PER_CDU"])
            assert kw.shape == (44,)
            assert abs(kw.sum() - tick.power_df["Sum"].sum()) < 1e-6
            assert abs(reconcile_total(tick.power_df, cfg) - e.sys_power) < 1e-6
            assert abs(kw.mean() - idle_rack_kw(cfg)) < 0.05
    assert n_power_ticks == 6                                 # 120 s / 20 s
```

```python
# tests/integration/test_timing_semantics.py
"""Verifies spec §5.8: within one second arrivals -> completions -> schedule -> (power on time_delta) ;
placement at second t appears in power at the next multiple of time_delta; scheduler is called on arrival."""
import pytest
from raps.job import Job, job_dict
from raps.policy import PolicyType
from thermorl2.raps_adapter.engine_factory import EngineSpec, build_engine
from thermorl2.raps_adapter.power_probe import rack_kw_from_power_df, is_power_tick

pytestmark = pytest.mark.integration


class RecordingScheduler:
    """Minimal drop-in: records call times, places every job on the lowest free nodes via the REPLAY path."""
    def __init__(self, rm):
        self.resource_manager, self.policy, self.bfpolicy, self.calls = rm, PolicyType.FCFS, None, []

    def schedule(self, queue, running, current_time, accounts=None, sorted=False):
        self.calls.append((current_time, len(queue)))
        for job in list(queue):
            if job.nodes_required <= len(self.resource_manager.available_nodes):
                job.scheduled_nodes = sorted(self.resource_manager.available_nodes)[: job.nodes_required]
                self.resource_manager.assign_nodes_to_job(job, current_time, PolicyType.REPLAY)
                running.append(job); queue.remove(job)


def make_job(jid, submit, nodes=18, run=600):
    Job._id_counter = 0
    d = job_dict(nodes_required=nodes, name=f"j{jid}", account="t", id=jid, cpu_trace=2.0, gpu_trace=4.0,
                 ntx_trace=0, nrx_trace=0, submit_time=submit, time_limit=run * 2, start_time=None, end_time=None,
                 expected_run_time=run)
    return Job(d)


def test_arrival_at_t_is_scheduled_at_t_and_powered_at_next_delta():
    e = build_engine(EngineSpec(sim_time="3m"), jobs=[make_job(1, submit=25)])
    sched = RecordingScheduler(e.resource_manager); e.scheduler = sched
    first_hot_tick = None
    for tick in e.run_simulation():
        if is_power_tick(tick, e.time_delta):
            kw = rack_kw_from_power_df(tick.power_df, 1)
            if first_hot_tick is None and kw[0] > 20.0:
                first_hot_tick = tick.current_timestep
    assert (25, 1) in sched.calls                    # scheduler invoked in the arrival second with 1 queued job
    assert first_hot_tick == 40                      # placed at t=25 -> first power tick at/after is t=40
    assert e.jobs[0].scheduled_nodes == list(range(18)) if e.jobs else True


def test_replay_path_allocates_exact_nodes_and_timeout_kill_still_active():
    j = make_job(1, submit=0, nodes=4, run=100); j.time_limit = 50   # will exceed limit -> TIMEOUT kill (policy != REPLAY)
    e = build_engine(EngineSpec(sim_time="3m"), jobs=[j])
    e.scheduler = RecordingScheduler(e.resource_manager)
    for _ in e.run_simulation():
        pass
    assert e.jobs_killed == 1
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `engine_factory.py` and `power_probe.py` per Interfaces (imports: `from raps.sim_config import SingleSimConfig`, `from raps.engine import Engine`, `from raps.system_config import get_system_config`, `from raps.power import compute_node_power`). **Step 4: Run** `uv run pytest tests/integration -v` → PASS. If `first_hot_tick` is not 40 or the kill count differs, **stop and report** with the observed values (this is the spec §5.8 verification; the spec may need amending, not the test).

- [ ] **Step 5: Cost benchmark script** — create `thermorl2/experiments/characterise.py` with subcommand `cost`: builds a 24 h idle engine (`jobs=[]`), drives the generator, at every power tick calls `FmuBackend.step` (after a warm-up), and prints `raps_s`, `fmu_s`, `total_s`, `power_ticks`. Run: `uv run python -m thermorl2.experiments.characterise cost --hours 24` and paste the three numbers into README "Phase 1 record". **Stop and report** the numbers (spec §11 Phase 1 gate) before continuing.

- [ ] **Step 6: Commit** `feat(adapter): engine factory with job injection, per-rack power probe, timing-semantics tests, cost benchmark`

---

### Task 1.7: Thermal characterisation under uniform load (stop-and-report gate)

**Files:**
- Modify: `thermorl2/experiments/characterise.py` (add subcommand `uniform`)
- Create: `thermorl2/experiments/configs/lassen_fmu.yaml`
- Output: `thermoRL/thermorl-v2/artifacts/characterisation/uniform_lassen.csv`, `.png`, `t_idle.json`

**Interfaces:**
- Produces `configs/lassen_fmu.yaml` (read by all later tasks):
```yaml
system: lassen
time_delta_s: 20
ambient: {t_air_k: 290.0, t_ext_k: 290.0}
fmu:
  path: ../../models/POWER9CSM/fmus/lassen.fmu       # relative to thermoRL/thermorl-v2
  sha256: 2207549908a4c7452cdb8a5e3409a0ab210a71da199d12809cc621bbaae35c0b
  warmup_max_s: 7200
  settle_k_per_min: 0.01
thermal_limits:
  t_max_c: 45.0        # ASSUMPTION: ASHRAE W45 class upper bound; NOT the 40 C CDU setpoint; never tuned on results
  eps: 0.10            # paper
  thi_form: headroom   # or paper_raw
  t_idle_source: artifacts/characterisation/t_idle.json   # written by Task 1.7
```
- Produces `t_idle.json`: `{"t_idle_c": [44 floats], "warmup_s": float, "fmu_sha256": str}`.

- [ ] **Step 1: Implement `uniform`**: for each load fraction f in `[0, 0.25, 0.5, 0.75, 1.0]`: `reset()`, step 3 h at rack power `idle + f*(peak-idle)` for all 44 racks, record per-rack `t_c` every 20 s plus `fmu.T_prim_supply_C`; write long-format CSV (`load_frac, t_s, rack, t_c, t_prim_supply_c`); plot mean/min/max rack temperature vs time per load and a final-temperature-vs-load curve with a horizontal line at `t_max_c`; write `t_idle.json` from the f = 0 run's warmed state.

- [ ] **Step 2: Run** `uv run python -m thermorl2.experiments.characterise uniform --config thermorl2/experiments/configs/lassen_fmu.yaml` → CSV, PNG, JSON exist.

- [ ] **Step 3: STOP AND REPORT** with: idle temperature range across racks; final temperature at each load fraction; whether any rack reaches 45 °C at f = 1.0 (and at which f the max rack temperature crosses 40 °C); primary supply temperature at each load; warm-up seconds. Do not change `t_max_c`. Wait for the ramp-phase decision before Task 3.3.

- [ ] **Step 4: Commit** `feat(experiments): uniform-load FMU characterisation and lassen_fmu config; record t_idle`

---

# Phase 2 — Adapter: placement, scoring, scheduler drop-in, observation, ledger, runner

### Task 2.1: Placement rule and scorer protocol

**Files:**
- Create: `thermorl2/core/placement.py`, `thermorl2/core/scoring.py`
- Test: `tests/unit/test_placement.py`

**Interfaces:**
- Produces (`placement.py`):
```python
def feasible_mask(free_per_rack: np.ndarray, nodes_required: int) -> np.ndarray[bool]   # rack has >= 1 free node (spec §6.2)
def place(scores: Scores, free_per_rack: np.ndarray, nodes_required: int, geometry_free_nodes: Callable[[int, int], list[int]]) -> Placement
    # geometry_free_nodes(rack, k) -> k lowest free node ids in rack (RackGeometry.free_nodes_in_rack bound with available_nodes)
    # rule: if scores.defer > max finite rack score -> DEFER
    #       elif any rack with free >= nodes_required among finite scores -> "single_best": argmax score among those racks
    #       else fill racks in descending finite score until nodes_required met -> "greedy_span"; if total free < nodes_required -> DEFER
```
- Produces (`scoring.py`):
```python
@dataclass(frozen=True) class ScorerInfo: name: str; version: str; config: dict
class RackScorer(Protocol):
    info: ScorerInfo
    def score(self, obs: Observation, job: JobRequest, feasible: np.ndarray) -> Scores    # infeasible racks must be -inf
def masked(scores: np.ndarray, feasible: np.ndarray) -> np.ndarray    # sets -inf where not feasible
```

- [ ] **Step 1: Failing tests**

```python
import numpy as np
from thermorl2.core.state import Scores, DEFER
from thermorl2.core.placement import feasible_mask, place

FREE = np.array([18, 4, 0, 10])
def free_nodes(rack, k):
    base = rack * 18
    return list(range(base, base + min(k, int(FREE[rack]))))


def test_feasible_mask_requires_one_free_node():
    assert feasible_mask(FREE, 3).tolist() == [True, True, False, True]


def test_single_best_prefers_highest_score_that_fits_whole_job():
    s = Scores(rack=np.array([0.1, 0.9, -np.inf, 0.5]), defer=-1.0)
    p = place(s, FREE, 6, free_nodes)          # rack 1 scores highest but has 4 free -> rack 3 (10 free) fits
    assert p.rule == "single_best" and p.racks == (3,) and p.nodes == tuple(range(54, 60))


def test_greedy_span_when_no_single_rack_fits():
    s = Scores(rack=np.array([0.1, 0.9, -np.inf, 0.5]), defer=-1.0)
    p = place(s, FREE, 20, free_nodes)         # 20 > any rack: fill rack1(4) + rack3(10) + rack0(6)
    assert p.rule == "greedy_span" and p.racks == (1, 3, 0) and len(p.nodes) == 20


def test_defer_when_defer_score_wins_or_capacity_short():
    s = Scores(rack=np.array([0.1, 0.2, -np.inf, 0.3]), defer=0.5)
    assert place(s, FREE, 1, free_nodes) == DEFER
    s2 = Scores(rack=np.array([0.1, 0.2, -np.inf, 0.3]), defer=-9.0)
    assert place(s2, FREE, 40, free_nodes) == DEFER    # only 32 free in total
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(core): placement rule (single_best / greedy_span / defer) and RackScorer protocol`

---

### Task 2.2: Heuristic scorers (five demo controllers + forced-rack test scorer)

**Files:**
- Create: `thermorl2/core/heuristics/__init__.py`, `lowest_id.py`, `round_robin.py`, `load_balance.py`, `threshold_reactive.py`, `coolest_rack.py`, `forced_rack.py`
- Test: `tests/unit/test_heuristics.py`

**Interfaces:**
- Produces: classes `LowestId`, `RoundRobin`, `LoadBalance`, `ThresholdReactive(t_max_c, hi=0.9, lo=0.8)`, `CoolestRack`, `ForcedRack(rack: int)`; each has `info: ScorerInfo` and `score(obs, job, feasible) -> Scores` with `defer = -inf` (heuristics never defer voluntarily). `heuristics/__init__.py` exposes `REGISTRY: dict[str, Callable[..., RackScorer]]` keyed `lowest_id, round_robin, load_balance, threshold_reactive, coolest_rack, forced_rack` and `make_scorer(spec: str, **kwargs)`. `spec` may carry a positional argument after a colon: `"forced_rack:43"` → `ForcedRack(rack=43)`; `"threshold_reactive"` needs `t_max_c=` from the limits config (the runner passes `**limits_kwargs` for names that accept them). Unknown names raise `KeyError`.
- Scores: `LowestId` → `-rack_index`; `RoundRobin` → cursor state: score = `-((rack - cursor) % n)` and advance cursor to chosen+1 via `notify(placement)` (add optional `notify(self, placement: Placement)` to the protocol, default no-op); `LoadBalance` → `free_frac - 1e-3*power_frac`; `ThresholdReactive` → maintains per-rack `excluded` set: exclude when `t_c > hi*t_max_c`, readmit when `t_c < lo*t_max_c`; score = `-inf` for excluded else `-rack_index`; `CoolestRack` → `obs.thi`; `ForcedRack(r)` → `+inf` at r, `0` elsewhere (test-only).

- [ ] **Step 1: Failing tests** (build a helper `obs_with(thi=..., free=..., t_c=..., power=...)` returning an `Observation` with 4 racks):

```python
import numpy as np
from thermorl2.core.heuristics import make_scorer
from thermorl2.core.state import RackResource, RackThermal, GlobalFeatures, Observation, JobRequest

def obs_with(thi, free, t_c=None, power=None):
    n = len(thi)
    rr = RackResource(free_nodes=np.array(free), total_nodes=np.full(n, 18), power_kw=np.array(power or [0]*n),
                      n_running=np.zeros(n, int), t_next_limit_s=np.full(n, np.inf))
    th = RackThermal(t_c=np.array(t_c or [30.0]*n), extras={})
    return Observation(rack=rr, thermal=th, thi=np.array(thi), glob=GlobalFeatures(0.0, 0.0, 0, 0.0, {}))

JOB = JobRequest(1, 2, 1.9, 3600, 0.0, 0, 0)
FEAS = np.array([True, True, True, True])


def test_coolest_rack_scores_equal_thi():
    s = make_scorer("coolest_rack").score(obs_with([0.2, 0.9, 0.5, 0.1], [18]*4), JOB, FEAS)
    assert int(np.argmax(s.rack)) == 1 and s.defer == -np.inf


def test_lowest_id_prefers_rack_zero():
    s = make_scorer("lowest_id").score(obs_with([0]*4, [18]*4), JOB, FEAS)
    assert int(np.argmax(s.rack)) == 0


def test_load_balance_prefers_most_free():
    s = make_scorer("load_balance").score(obs_with([0]*4, [2, 18, 9, 18], power=[0, 5, 0, 1]), JOB, FEAS)
    assert int(np.argmax(s.rack)) == 3      # tie on free broken by lower power


def test_threshold_reactive_hysteresis():
    tr = make_scorer("threshold_reactive", t_max_c=45.0)
    hot = obs_with([0]*4, [18]*4, t_c=[41.0, 30, 30, 30])       # 41 > 0.9*45=40.5 -> exclude rack 0
    assert tr.score(hot, JOB, FEAS).rack[0] == -np.inf
    warm = obs_with([0]*4, [18]*4, t_c=[37.0, 30, 30, 30])      # 37 > 0.8*45=36 -> still excluded
    assert tr.score(warm, JOB, FEAS).rack[0] == -np.inf
    cool = obs_with([0]*4, [18]*4, t_c=[35.0, 30, 30, 30])      # < 36 -> readmitted
    assert np.isfinite(tr.score(cool, JOB, FEAS).rack[0])


def test_round_robin_advances():
    rr = make_scorer("round_robin")
    from thermorl2.core.state import Placement
    s1 = rr.score(obs_with([0]*4, [18]*4), JOB, FEAS); assert int(np.argmax(s1.rack)) == 0
    rr.notify(Placement(racks=(0,), nodes=(0, 1), rule="single_best"))
    s2 = rr.score(obs_with([0]*4, [18]*4), JOB, FEAS); assert int(np.argmax(s2.rack)) == 1


def test_masking_applied():
    s = make_scorer("coolest_rack").score(obs_with([0.9, 0.1, 0.1, 0.1], [0, 18, 18, 18]), JOB, np.array([False, True, True, True]))
    assert s.rack[0] == -np.inf
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** all six scorers + registry, each `ScorerInfo(name, version="0.1", config={...kwargs})`. **Step 4: Run** → PASS. **Step 5: Commit** `feat(core): five heuristic rack scorers plus forced-rack test scorer with registry`

---

### Task 2.3: Jobs from parquet, JobRequest builder, and job-power estimate

**Files:**
- Create: `thermorl2/raps_adapter/jobs.py`
- Test: `tests/integration/test_jobs.py`

**Interfaces:**
- Produces:
```python
WORKLOAD_COLUMNS = ["id", "nodes_required", "cpu_trace", "gpu_trace", "submit_time", "expected_run_time", "time_limit", "priority"]
def jobs_from_parquet(path: Path) -> list["raps.job.Job"]       # resets Job._id_counter = 0; builds via job_dict(name=f"j{id}", account="synthetic", ntx_trace=0, nrx_trace=0, start_time=None, end_time=None, partition=0)
def workload_sha256(path: Path) -> str
def est_power_per_node_kw(job, cfg: dict) -> float               # compute_node_power(job.cpu_trace, job.gpu_trace, 0.0, cfg)[0] / 1000 (scalar traces only; arrays -> mean)
def job_request(job, now_s: float, cfg: dict) -> JobRequest      # wait_s = now_s - submit_time; defer_count = getattr(job, "defer_count", 0)
```

- [ ] **Step 1: Failing test** (writes a 3-row parquet in `tmp_path` with pandas, loads it, asserts `len == 3`, `jobs[0].start_time is None`, `jobs[0].id == 1`, `est_power_per_node_kw(jobs[0], cfg)` within (0.5, 2.0) for cpu_trace 2.0/gpu_trace 4.0, and `workload_sha256` is 64 hex chars and stable across two calls).

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(adapter): build RAPS jobs from parquet workload; job power estimate; JobRequest builder`

---

### Task 2.4: ObservationBuilder

**Files:**
- Create: `thermorl2/raps_adapter/observation.py`
- Test: `tests/integration/test_observation.py`

**Interfaces:**
- Produces:
```python
class ObservationBuilder:
    def __init__(self, geometry: RackGeometry, cfg: dict, limits: dict)   # limits from lassen_fmu.yaml thermal_limits + t_idle_c array + p_max_kw
    def build(self, engine, thermal: RackThermal, backend_globals: dict[str, float], rack_kw: np.ndarray) -> Observation
        # RackResource: free_nodes = geometry.free_per_rack(engine.resource_manager.available_nodes); total_nodes = 18;
        #   power_kw = rack_kw; n_running per rack from engine.running[*].scheduled_nodes; t_next_limit_s per rack =
        #   min over running jobs on that rack of (job.start_time + job.time_limit - engine.current_timestep), inf if none  (NO expected_run_time/end_time use)
        # thi = compute_thi(limits["thi_form"], t_c=thermal.t_c, t_idle_c=t_idle, t_max_c=limits["t_max_c"], p_kw=rack_kw, p_max_kw=p_max)
        # GlobalFeatures: sim_time_s, total_power_kw = rack_kw.sum(), queue_depth = len(engine.queue),
        #   queued_power_kw = sum(nodes_required*est_power_per_node_kw) over engine.queue, backend = backend_globals
```

- [ ] **Step 1: Failing test**: build a 2-minute engine with two injected jobs (18 nodes each, submit 0), attach the `RecordingScheduler` from Task 1.6's test module (import it), run 30 ticks, then `build(...)` with a synthetic `RackThermal(t_c=np.full(44, 30.0))`, `t_idle = 30.0`, rack_kw from the last power tick. Assert `free_nodes[0] == 0 and free_nodes[1] == 0`, `free_nodes[2:].sum() == 42*18`, `n_running[0] == 1`, `t_next_limit_s[0] == pytest.approx(job.start_time + job.time_limit - engine.current_timestep)`, `thi.shape == (44,)`, `thi[0] < thi[5]` (loaded rack has less power headroom), `glob.queue_depth == 0`.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(adapter): observation builder from engine state, rack power and thermal backend`

---

### Task 2.5: RackScheduler drop-in

**Files:**
- Create: `thermorl2/raps_adapter/rack_scheduler.py`
- Test: `tests/integration/test_rack_scheduler.py`

**Interfaces:**
- Produces:
```python
@dataclass class DecisionRecord: sim_time_s: float; job_id: int; nodes_required: int; scores: np.ndarray; defer_score: float; feasible: np.ndarray; placement: Placement; latency_s: float; scorer: ScorerInfo; observation: Observation; forced: bool
class RackScheduler:
    policy: PolicyType = PolicyType.FCFS ; bfpolicy = None ; debug = False       # settable (prepare_system_state writes them)
    def __init__(self, resource_manager, geometry: RackGeometry, scorer: RackScorer, obs_provider: Callable[[float], Observation], cfg: dict, max_defers: int = 10, on_decision: Callable[[DecisionRecord], None] | None = None)
    def schedule(self, queue, running, current_time, accounts=None, sorted=False) -> None
        # FCFS by submit_time; for each job: obs = obs_provider(current_time); job_req = job_request(job, current_time, cfg);
        # feasible = feasible_mask(obs.rack.free_nodes, n); scores = scorer.score(obs, job_req, feasible);
        # placement = place(...); if DEFER and job.defer_count >= max_defers: placement = place(LoadBalance().score(...)), forced=True
        # if DEFER: job.defer_count += 1; continue
        # job.scheduled_nodes = list(placement.nodes); resource_manager.assign_nodes_to_job(job, current_time, PolicyType.REPLAY)
        # running.append(job); queue.remove(job); scorer.notify(placement); on_decision(record)
        # NEVER calls check_available_nodes.
    def reconsider(self, queue, running, current_time) -> None      # alias for schedule(...) used by the runner's periodic deferred re-evaluation
```

- [ ] **Step 1: Failing test**: engine 2 min, jobs: A(18 nodes, submit 0), B(4 nodes, submit 0); scheduler with `ForcedRack(43)` and an `obs_provider` closure that rebuilds `RackResource` from `engine.resource_manager.available_nodes` on each call and uses a constant idle `RackThermal`. Expected after the run: `A.scheduled_nodes == list(range(774, 792))` (rack 43, rule `single_best`); rack 43 is then full, `ForcedRack` scores every other rack 0.0, `np.argmax` breaks the tie toward the lowest index, so `B.scheduled_nodes == list(range(0, 4))` with rule `single_best`; `len(records) == 2`; every record has `latency_s >= 0` and `record.scorer.name == "forced_rack"`. Second test: `scorer=CoolestRack`, one job of 800 nodes (> 792 total) → `place` returns DEFER on every call, `job.defer_count` increments each call, the job stays in `engine.queue`, and no forced placement occurs (capacity is insufficient even for `LoadBalance`); assert `job.defer_count >= 3` after the run and `len(engine.running) == 0`.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(adapter): RackScheduler drop-in placing exact node sets via REPLAY allocation path`

---

### Task 2.6: Ledger (decision rows, interval rows, manifest)

**Files:**
- Create: `thermorl2/core/ledger.py`
- Test: `tests/unit/test_ledger.py`

**Interfaces:**
- Produces:
```python
DECISION_FIELDS = ["run_id","workload_sha256","controller","controller_version","controller_config_hash","sim_time_s","job_id",
                   "nodes_required","est_power_per_node_kw","time_limit_s","wait_s","defer_count","rule","racks","nodes_summary",
                   "forced","latency_s","defer_score","scores","feasible","obs_thi","obs_free","obs_power_kw","obs_global"]
INTERVAL_FIELDS = ["run_id","sim_time_s","phase","rack","t_c","power_kw","free_nodes","n_running","thi","violation","hinge",
                   "extras_json","T_prim_supply_C","queue_depth","queued_power_kw","running_jobs","total_power_kw",
                   "it_energy_kwh_cum","cdu_pump_kw","completed_cum","fmu_step_s","raps_step_s"]
class LedgerWriter:
    def __init__(self, out_dir: Path, run_id: str)
    def decision(self, rec: DecisionRecord, run_meta: dict) -> None       # appends one JSON line to decisions.jsonl (numpy -> lists; nodes_summary = "0-17,36-39")
    def interval(self, rows: list[dict]) -> None                          # buffers; flushes to intervals.parquet every 5000 rows and on close (one row per rack per power tick)
    def manifest(self, meta: dict) -> None                                # writes manifest.json (git_sha, config, workload_sha256, controller info, timings, fmu_sha256, t_idle, started/finished)
    def close(self) -> None
def summarize_nodes(nodes: Sequence[int]) -> str                        # "0-17,36-39"
def load_decisions(path) -> pd.DataFrame ; def load_intervals(path) -> pd.DataFrame
```

- [ ] **Step 1: Failing test**: `summarize_nodes([0,1,2,5,6]) == "0-2,5-6"`; write 2 decisions + 88 interval rows + manifest to `tmp_path`, then `load_decisions` has 2 rows with `racks == [43]` and `load_intervals` has 88 rows with columns ⊇ INTERVAL_FIELDS; manifest JSON round-trips.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(core): decision/interval/manifest ledger writer and loaders`

---

### Task 2.7: EpisodeRunner (ticks, thermal sync, deferred re-evaluation, timings)

**Files:**
- Create: `thermorl2/raps_adapter/runner.py`, `thermorl2/core/energy.py`
- Test: `tests/fmu/test_runner_smoke.py` (mark `fmu`, `integration`, `slow`)

**Interfaces:**
- Produces (`energy.py`): `it_energy_kwh(rack_kw: np.ndarray, dt_s: float) -> float` (= sum*dt/3600); `cdu_pump_energy_kwh(w_flow_cdup_kw: np.ndarray, dt_s: float) -> float`. Separate quantities, never summed.
- Produces (`runner.py`):
```python
@dataclass class RunConfig: run_id: str; out_dir: Path; workload_path: Path; sim_time: str; time_delta_s: int; ambient: Ambient;
                             limits: dict; defer_reeval_s: int = 60; max_defers: int = 10; phases: list[dict] = field(default_factory=list); decision_cadence: str = "event"
class EpisodeRunner:
    def __init__(self, backend: ThermalBackend, scorer: RackScorer, cfg_run: RunConfig, engine_spec: EngineSpec)
    def run(self) -> dict          # returns summary dict (jobs_completed, jobs_killed, running_at_end, queued_at_end, wall_total_s, wall_raps_s, wall_fmu_s, n_decisions, n_power_ticks)
```
`run()` algorithm:
1. `jobs = jobs_from_parquet(...)`; `engine = build_engine(spec, jobs)`; `geometry = RackGeometry.from_legacy_config(engine.config)`; `backend.reset()`; `thermal = backend.observe()`; `rack_kw = idle_rack_kw` array; `obs_provider = lambda t: builder.build(engine, thermal, backend.global_observe(), rack_kw)` (closure reads the latest `thermal`/`rack_kw`); `engine.scheduler = RackScheduler(..., on_decision=ledger.decision)`.
2. `gen = engine.run_simulation()`; `next_reeval = defer_reeval_s`.
3. For each `tick` in `gen` (timing RAPS with `perf_counter` around `next`): if `is_power_tick`: `rack_kw = rack_kw_from_power_df(...)`; `backend.step(rack_kw, time_delta_s, ambient)` (timed); `thermal = backend.observe()`; compute `thi`, `hinge`, `violation`; append 44 interval rows (phase from `phases` by sim time). If `decision_cadence == "fixed:300"`: the scheduler only acts when `current_timestep % 300 == 0` (implemented by wrapping `RackScheduler.schedule` with a time check that otherwise returns immediately). If `tick.current_timestep >= next_reeval and engine.queue`: `engine.scheduler.reconsider(engine.queue, engine.running, engine.current_timestep)`; `next_reeval += defer_reeval_s`.
4. On exhaustion: `ledger.manifest(...)`, `ledger.close()`, return summary.

- [ ] **Step 1: Failing smoke test**: write a 10-job parquet (18 nodes each, submit every 60 s, run 600 s) to `tmp_path`; `FmuBackend` warmed (module fixture as in Task 1.5); `EpisodeRunner(backend, make_scorer("coolest_rack"), RunConfig(sim_time="30m", time_delta_s=20, ...), EngineSpec(sim_time="30m"))`. Assert summary `n_power_ticks == 90`, `n_decisions == 10`, `jobs_completed >= 5`; `intervals.parquet` has `90*44` rows; `decisions.jsonl` has 10 lines; manifest has `workload_sha256`; wall times positive; **bit-identity**: run twice with the same inputs into two dirs → `decisions.jsonl` byte-identical and `intervals.parquet` frames equal (`pd.testing.assert_frame_equal` after dropping timing columns).

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** `uv run pytest tests/fmu/test_runner_smoke.py -v` → PASS. **Step 5: Commit** `feat(adapter): episode runner with thermal sync per power tick, deferred re-evaluation, ledgers, timings`

---

### Task 2.8: Causal coupling check (Experiment 0 gate)

**Files:**
- Create: `thermorl2/experiments/configs/smoke_2h.yaml`, `thermorl2/experiments/run_demo.py` (minimal version: run one controller from a config), `tests/fmu/test_causal_coupling.py` (mark `fmu`, `slow`)

**Interfaces:**
- `run_demo.py` CLI: `uv run python -m thermorl2.experiments.run_demo --config <yaml> --controller <name> [--out artifacts/runs]` → writes `artifacts/runs/<run_id>/{decisions.jsonl,intervals.parquet,manifest.json}`; `run_id = f"{scenario}_{controller}_seed{seed}"`. Config schema (`smoke_2h.yaml`):
```yaml
scenario: smoke_2h
seed: 1
sim_time: "2h"
workload: {generator: fixed_single_rack, n_jobs: 40, nodes: 18, run_s: 900, interarrival_s: 180}   # all jobs fit one rack
system_config: thermorl2/experiments/configs/lassen_fmu.yaml
controllers: [lowest_id, forced_rack:43]
defer_reeval_s: 60
```
- Add generator `fixed_single_rack(cfg, seed) -> parquet` inside `raps_adapter/workload/ramp_generator.py` (Task 3.1 adds the ramp generator to the same module; create the module now with this simple generator and `write_workload(df, path)` helper).

- [ ] **Step 1: Failing test** (`tests/fmu/test_causal_coupling.py`): run both controllers via `run_demo.main([...])` into `tmp_path`; load intervals; compute per-rack mean power over the last hour; assert `mean_power[forced, rack43] - mean_power[lowest, rack43] > 5.0` and `mean_power[lowest, rack0] - mean_power[forced, rack0] > 5.0`; from the forced run, take rack-43 `t_c` series, `idle = t_c[0]`, `rise = t_c[-1] - idle`, assert `rise > 3.0`; `t63 = first time frac >= 0.632`, assert `450 <= t63 <= 1050` (probe 750 s ± 40 % because load steps are staggered); assert `|t_c[rack0][-1] - t_c[rack0][0]| < 0.5` in the forced run.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `run_demo.py` + `fixed_single_rack`. **Step 4: Run** → PASS (~2–4 min). If any assertion fails: **stop and report** the measured values; this is the Phase 2 gate.

- [ ] **Step 5: Commit** `feat(experiments): run_demo CLI, single-rack smoke workload, causal coupling gate test`

---

# Phase 3 — Controllers + ramp workload + metrics

### Task 3.1: Ramp workload generator (deterministic, load-targeted, RAPS schema)

**Files:**
- Modify: `thermorl2/raps_adapter/workload/ramp_generator.py`
- Create: `thermorl2/experiments/configs/demo_ramp_lassen.yaml`
- Test: `tests/unit/test_ramp_generator.py`

**Interfaces:**
- Produces:
```python
@dataclass(frozen=True) class Phase: name: str; start_s: int; end_s: int; rho_n: float
@dataclass(frozen=True) class RampSpec: phases: tuple[Phase, ...]; transition_s: int; n_usable_nodes: int; nodes_lognorm: tuple[float, float]; nodes_clip: tuple[int, int];
      run_lognorm: tuple[float, float]; run_clip_s: tuple[int, int]; cpu_beta: tuple[float, float]; gpu_beta: tuple[float, float]; limit_factor: tuple[float, float]; priority_max: int
      @classmethod from_yaml(d: dict) -> RampSpec
def rho_n_at(t_s: float, spec: RampSpec) -> float                  # piecewise constant with linear transitions of transition_s centred on boundaries
def arrival_rate_at(t_s, spec, mean_nodes, mean_run_s) -> float    # rho_n * n_usable / (mean_nodes*mean_run_s)   [jobs/s]
def generate_ramp(spec: RampSpec, seed: int, horizon_s: int) -> pd.DataFrame   # columns WORKLOAD_COLUMNS; thinning NHPP with lambda_max; analytic means from the lognormal/clip params estimated by 1e6-sample Monte Carlo with the SAME rng first (documented)
def realised_rho_n(df: pd.DataFrame, spec: RampSpec, window_s: int = 3600) -> pd.DataFrame   # per-window realised offered node-load
def write_workload(df: pd.DataFrame, path: Path, meta: dict) -> str   # parquet + <path>.meta.json (spec, seed, phases, sha256); returns sha256
```
- `demo_ramp_lassen.yaml`:
```yaml
scenario: demo_ramp_lassen
seed: 1
sim_time: "24h"
system_config: thermorl2/experiments/configs/lassen_fmu.yaml
controllers: [lowest_id, round_robin, load_balance, threshold_reactive, coolest_rack]
defer_reeval_s: 60          # ASSUMPTION: rack tau (~12 min)/12; keeps deferral latency <= 1 min; fairness knob, not thermal cadence
max_defers: 10
decision_cadence: event
ramp:
  n_usable_nodes: 792       # verified Phase 1 = total_nodes - len(down_nodes)
  transition_s: 600
  phases:                   # PROVISIONAL rho_n targets (spec §8) -- replaced after Task 1.7 stop-and-report, never from scheduler results
    - {name: normal,   start_s: 0,     end_s: 28800, rho_n: 0.5}
    - {name: surge,    start_s: 28800, end_s: 50400, rho_n: 1.0}
    - {name: overload, start_s: 50400, end_s: 86400, rho_n: 1.5}
  nodes_lognorm: [1.4, 0.9]      # ln-space mean/sigma -> median ~4 nodes   ASSUMPTION
  nodes_clip: [1, 64]
  run_lognorm: [7.5, 0.8]        # median ~1800 s                             ASSUMPTION
  run_clip_s: [60, 28800]
  cpu_beta: [4.0, 2.0]           # scaled to [0, CPUS_PER_NODE]               ASSUMPTION
  gpu_beta: [4.0, 2.0]           # scaled to [0, GPUS_PER_NODE]
  limit_factor: [1.1, 2.0]
  priority_max: 10
```

- [ ] **Step 1: Failing tests**: (a) same seed → identical DataFrame and identical sha; different seed → different; (b) `rho_n_at` returns 0.5 at t=1000, 1.0 at t=40000, 1.5 at t=80000, and a value strictly between 0.5 and 1.0 at t=28800; (c) `realised_rho_n` per-hour mean over hours 1–7 is within 10 % of 0.5 and over hours 15–23 within 10 % of 1.5 (seed 1); (d) all `start_time` are NaN/None and `submit_time` sorted ascending, `time_limit >= expected_run_time`, `1 <= nodes_required <= 64`, `0 <= cpu_trace <= 2`, `0 <= gpu_trace <= 4`; (e) `write_workload` produces parquet + meta.json with `phases` list.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(workload): deterministic load-targeted ramp generator with realised-load report`

---

### Task 3.2: Metrics hierarchy from ledgers

**Files:**
- Create: `thermorl2/core/metrics.py`
- Test: `tests/unit/test_metrics.py`

**Interfaces:**
- Produces:
```python
def primary_violation_fraction(intervals: pd.DataFrame, by_phase: bool = True) -> pd.DataFrame     # mean(violation) per phase and overall
def secondary_thermal(intervals, decisions, limits) -> pd.DataFrame     # violations_per_completed_job, hinge_integral (sum hinge*dt), frac_time_above_0p9_tmax, per-rack violation counts, stress_exposure_degsec (sum max(0, t_c - (t_idle+0.85*(t_max-t_idle)))*dt)
def performance(intervals, decisions, summary: dict) -> dict            # jobs_completed, node_hours_delivered, wait_mean_s, wait_p95_s, bounded_slowdown_mean (bound 60 s), utilisation_mean, queue_depth_mean, running_at_end, queued_at_end
def load_bookkeeping(intervals, workload_meta: dict) -> pd.DataFrame     # target rho_n per phase, realised arrival rate, realised offered load, utilisation
def energy(intervals) -> dict                                            # it_energy_kwh (cum last), cdu_pump_energy_kwh (sum cdu_pump_kw*dt/3600); facility_total: "not available (lassen FMU exposes no plant power)"
def placement_independence(decisions_a: pd.DataFrame, decisions_b: pd.DataFrame) -> float   # fraction of matched job_ids whose chosen racks differ
def computational(manifest_a: dict) -> dict                              # decision latency mean/p95, fmu_s, raps_s, total_s
def report(run_dir: Path, limits: dict) -> dict                          # assembles all of the above for one run
```
Stress exposure is labelled `stress_exposure_degsec` and the report dict carries `"note": "exposure proxy, not lifetime"`.

- [ ] **Step 1: Failing tests** on a hand-built 3-rack, 4-interval frame: violation fraction 3/12 = 0.25; hinge integral = Σ(0.1−thi)+·20; exposure computed for one rack above threshold; `placement_independence` = 0.5 for two 4-decision frames differing in two racks; `energy()["facility_total"]` is the not-available string.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(core): pre-specified metric hierarchy computed from ledgers`

---

### Task 3.3: Finalise ramp phases (after Task 1.7 decision) and 2 h all-controller smoke

**Files:**
- Modify: `thermorl2/experiments/configs/demo_ramp_lassen.yaml` (phase `rho_n` values only), `thermorl2/experiments/run_demo.py` (add `--all` to run every controller in `controllers:` on the same parquet; generate parquet once per (scenario, seed) into `artifacts/workloads/` and reuse by sha)
- Test: `tests/fmu/test_all_controllers_smoke.py` (mark `fmu`, `slow`)

- [ ] **Step 1:** Insert the phase targets decided by Bipin after Task 1.7 into the YAML with a comment `# decided 2026-MM-DD from uniform-load characterisation (see artifacts/characterisation)`. Do not proceed without that decision.

- [ ] **Step 2: Failing test**: `run_demo.main(["--config", ..., "--all", "--sim-time", "2h", "--out", tmp])` → five run dirs exist; all manifests share `workload_sha256`; `report()` succeeds for each; `placement_independence(coolest_rack, load_balance)` is a float in [0,1].

- [ ] **Step 3: Run** → FAIL; **Step 4: Implement `--all` and `--sim-time` override**; **Step 5: Run** → PASS (~10–20 min). **Step 6: Commit** `feat(experiments): all-controller demo runner on shared workload; finalised ramp phases`

---

# Phase 4 — Demo

### Task 4.1: Minimum-demo gate — `coolest_rack` full 24 h with plots

**Files:**
- Create: `thermorl2/experiments/plots.py`
- Output: `artifacts/runs/demo_ramp_lassen_coolest_rack_seed1/`, `artifacts/figures/`

**Interfaces:**
- `plots.py`: `plot_run(run_dir, workload_meta, out_png)` → 4-panel figure: (1) target vs realised ρ_N with phase bands; (2) per-rack temperature heat-map (rack × time) with `t_max_c` colour ceiling; (3) violation fraction and mean THI over time; (4) queue depth, running nodes, total power. `plot_compare(run_dirs, out_png)` → per-phase primary metric bars + per-phase jobs completed + wait p95 per controller; phase boundaries drawn as vertical dashed lines with labels.

- [ ] **Step 1:** `uv run python -m thermorl2.experiments.run_demo --config thermorl2/experiments/configs/demo_ramp_lassen.yaml --controller coolest_rack` (expect several minutes; record wall time). Verify `manifest.json` lists `fmu_sha256`, `workload_sha256`, `git_sha`.
- [ ] **Step 2:** Implement `plots.py`; run `uv run python -m thermorl2.experiments.plots run artifacts/runs/demo_ramp_lassen_coolest_rack_seed1` → PNG produced.
- [ ] **Step 3:** Re-run Step 1 into a second directory and assert bit-identical `decisions.jsonl` (`cmp`). If not identical: **stop and report**.
- [ ] **Step 4: Commit** `feat(experiments): run plots; minimum-demo gate passed for coolest_rack` (commit figures under `artifacts/figures/`, not run ledgers; add `artifacts/runs/` and `artifacts/workloads/` to `.gitignore`).

### Task 4.2: All controllers, comparison figures, result note

- [ ] **Step 1:** `uv run python -m thermorl2.experiments.run_demo --config thermorl2/experiments/configs/demo_ramp_lassen.yaml --all`
- [ ] **Step 2:** `uv run python -m thermorl2.experiments.plots compare artifacts/runs/demo_ramp_lassen_*_seed1 --out artifacts/figures/demo_compare.png`; `uv run python -m thermorl2.experiments.plots table artifacts/runs/demo_ramp_lassen_*_seed1 --out artifacts/figures/demo_metrics.md` (metric hierarchy per controller per phase, plus placement-independence vs `load_balance`, plus computational diagnostics).
- [ ] **Step 3:** Write `docs/results/2026-10-demo-ramp-lassen.md` (≤ 1 page): what was run (configs, hashes, git SHA), the primary metric per phase per controller, whether `coolest_rack` differed from `load_balance` in placement and outcome, whether any rack approached `t_max_c`, energy quantities kept separate, computational cost, and a plain statement of what the twin did or did not show. No lifetime language.
- [ ] **Step 4: Commit** `docs(results): October demo ramp on Lassen FMU — all controllers, figures, result note`

---

## Plan self-review (performed by the plan author)

- **Spec coverage:** §4 layout → Tasks 0.1–2.7; §5 lifecycle (cooling off, coupling, warm-up/snapshot, tick loop, deferred re-eval, cadence option, timing verification) → 1.4, 1.5, 1.6, 2.7; §6 interfaces → 1.1, 1.5, 2.1, 2.5; §7 THI/limits/provenance → 1.2, 1.7; §8 workload → 3.1, 3.3; §9 controllers → 2.2 (lookahead deliberately omitted, optional per spec); §10 metrics → 3.2, 4.2; §11 gates → 0.1, 1.6/1.7, 2.8, 3.3, 4.1, 4.2; §12 stop-and-report → Global Constraints + explicit markers.
- **Not covered by design:** RC backend, PPO, multi-seed sweep, Alibaba resampler (separate specs per D3/D8/D11).
- **Type consistency:** `Scores(rack, defer)`, `Placement(racks, nodes, rule)`, `RackThermal(t_c, extras)`, `RackResource(free_nodes, total_nodes, power_kw, n_running, t_next_limit_s)`, `GlobalFeatures(sim_time_s, total_power_kw, queue_depth, queued_power_kw, backend)`, `JobRequest(job_id, nodes_required, est_power_per_node_kw, time_limit_s, wait_s, priority, defer_count)` used identically in 1.1, 2.1, 2.2, 2.4, 2.5, 2.7. `CouplingParams.from_legacy_config` used in 1.4, 1.5. `RackGeometry.free_nodes_in_rack(rack, avail, k)` bound into `place(...)` via closure in 2.5.
- **Known simplification vs spec:** snapshot kept as an in-memory FMU state handle (warm-up ≈ seconds per process) instead of serialised to disk; `t_idle` persisted to JSON. Recorded in spec §5.3 amendment when Task 1.7 lands.
