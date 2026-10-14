from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from shutil import rmtree
from time import perf_counter
from typing import Any

import numpy as np
from fmpy import extract, read_model_description
from fmpy.fmi2 import FMU2Slave

from thermorl2.core.state import Ambient, RackThermal
from thermorl2.raps_adapter.coupling import CouplingParams, power_input_names, rack_kw_to_fmu_inputs


_active_backend = None

_RACK_TEMP = "simulator[1].datacenter[1].computeBlock[{i}].cabinet[1].volume.medium.T"
_CDU_SUMMARY = "simulator[1].datacenter[1].computeBlock[{i}].cdu[1].summary."
_DEFAULT_EXTRA_RACK_VARS = {
    "T_sec_r_C": _CDU_SUMMARY + "T_sec_r_C",
    "T_sec_s_C": _CDU_SUMMARY + "T_sec_s_C",
    "W_flow_CDUP_kW": _CDU_SUMMARY + "W_flow_CDUP_kW",
    "V_flow_sec_GPM": _CDU_SUMMARY + "V_flow_sec_GPM",
}
_DEFAULT_GLOBAL_VARS = {
    "fmu.T_prim_supply_C": _CDU_SUMMARY.format(i=1) + "T_prim_s_C",
    "fmu.T_prim_return_C": _CDU_SUMMARY.format(i=1) + "T_prim_r_C",
    "fmu.V_flow_prim_GPM": "simulator[1].datacenter[1].summary.V_flow_prim_GPM",
}


@dataclass(frozen=True)
class _SavedState:
    fmu_state: object
    time_s: float


class FmuBackend:
    def __init__(
        self,
        fmu_path: Path,
        coupling: CouplingParams,
        extra_rack_vars: dict[str, str] | None = None,
        global_vars: dict[str, str] | None = None,
        tolerance: float = 1e-5,
    ):
        global _active_backend
        if _active_backend is not None:
            raise RuntimeError("canBeInstantiatedOnlyOncePerProcess")

        self.n_units = coupling.num_cdus
        self.time_s = 0.0
        self._snapshot_time_s = 0.0
        self._snapshot = None
        self._runtime_s = 0.0
        self._closed = False
        self._unzipdir = None
        self.fmu = None
        self._coupling = coupling
        self._extra_rack_vars = dict(_DEFAULT_EXTRA_RACK_VARS if extra_rack_vars is None else extra_rack_vars)
        self._global_vars = dict(_DEFAULT_GLOBAL_VARS if global_vars is None else global_vars)

        input_names = power_input_names(coupling) + list(coupling.temperature_keys)
        rack_temp_names = [_RACK_TEMP.format(i=i) for i in range(1, self.n_units + 1)]
        extra_names = {
            label: [template.format(i=i) for i in range(1, self.n_units + 1)]
            for label, template in self._extra_rack_vars.items()
        }
        global_names = list(self._global_vars.values())
        required_names = input_names + rack_temp_names + [name for group in extra_names.values() for name in group] + global_names

        try:
            self._unzipdir = self._timed_call(extract, Path(fmu_path))
            md = self._timed_call(read_model_description, Path(fmu_path))
            if md.coSimulation is None:
                raise ValueError("FMU does not support FMI 2.0 Co-Simulation")

            variables = {v.name: v for v in md.modelVariables}
            missing = sorted(set(required_names) - variables.keys())
            if missing:
                raise KeyError(f"FMU missing variables: {missing}")
            non_real = sorted(name for name in required_names if variables[name].type != "Real")
            if non_real:
                raise TypeError(f"FMU variables are not Real: {non_real}")

            self._input_names = input_names
            self._input_vrs = [variables[name].valueReference for name in input_names]
            self._rack_output_vrs = [variables[name].valueReference for name in rack_temp_names]
            for names in extra_names.values():
                self._rack_output_vrs.extend(variables[name].valueReference for name in names)
            self._global_vrs = [variables[name].valueReference for name in global_names]

            self.fmu = FMU2Slave(
                guid=md.guid,
                unzipDirectory=str(self._unzipdir),
                modelIdentifier=md.coSimulation.modelIdentifier,
                instanceName="thermorl2",
            )
            self._timed_call(self.fmu.instantiate)
            _active_backend = self
            self._timed_call(self.fmu.setupExperiment, tolerance=tolerance, startTime=0.0)
            self._timed_call(self.fmu.enterInitializationMode)
            self._timed_call(self.fmu.exitInitializationMode)
        except Exception:
            if _active_backend is self:
                try:
                    self._timed_call(self.fmu.freeInstance)
                finally:
                    _active_backend = None
            if self._unzipdir is not None:
                rmtree(self._unzipdir, ignore_errors=True)
            raise

    def _timed_call(self, fn, *args, **kwargs) -> Any:
        start = perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            self._runtime_s += perf_counter() - start

    def warm_up(
        self,
        idle_rack_kw: np.ndarray,
        ambient: Ambient,
        dt_s: float,
        max_s: float = 7200.0,
        settle_k_per_min: float = 0.01,
    ) -> float:
        if self._snapshot is not None:
            raise RuntimeError("warm_up has already created a snapshot")

        window_steps = max(1, ceil(300.0 / dt_s))
        history = deque(maxlen=window_steps + 1)
        history.append((self.observe().t_c.copy(), self.global_observe()["fmu.T_prim_supply_C"]))
        used_s = 0.0

        while used_s + dt_s <= max_s:
            self.step(idle_rack_kw, dt_s, ambient)
            used_s += dt_s
            t_c = self.observe().t_c
            supply_c = self.global_observe()["fmu.T_prim_supply_C"]
            history.append((t_c, supply_c))
            if len(history) == window_steps + 1:
                old_t_c, old_supply_c = history[0]
                window_min = window_steps * dt_s / 60.0
                rack_rate = np.max(np.abs(t_c - old_t_c)) / window_min
                supply_rate = abs(supply_c - old_supply_c) / window_min
                if rack_rate < settle_k_per_min and supply_rate < settle_k_per_min:
                    break

        self._snapshot = self._timed_call(self.fmu.getFMUstate)
        self._snapshot_time_s = self.time_s
        self.time_s = 0.0
        return used_s

    def reset(self) -> None:
        if self._snapshot is None:
            raise RuntimeError("warm_up must create a snapshot before reset")
        self._timed_call(self.fmu.setFMUstate, self._snapshot)
        self.time_s = 0.0

    def step(self, unit_power_kw: np.ndarray, dt_s: float, ambient: Ambient) -> None:
        inputs = rack_kw_to_fmu_inputs(unit_power_kw, self._coupling, ambient)
        values = [inputs[name] for name in self._input_names]
        self._timed_call(self.fmu.setReal, self._input_vrs, values)
        self._timed_call(self.fmu.doStep, self._snapshot_time_s + self.time_s, dt_s)
        self.time_s += dt_s

    def observe(self) -> RackThermal:
        values = np.asarray(self._timed_call(self.fmu.getReal, self._rack_output_vrs), dtype=np.float64)
        t_c = values[:self.n_units] - 273.15
        extras = {}
        for j, label in enumerate(self._extra_rack_vars):
            lo = (j + 1) * self.n_units
            extras[label] = values[lo:lo + self.n_units].copy()
        return RackThermal(t_c=t_c, extras=extras)

    def global_observe(self) -> dict[str, float]:
        values = self._timed_call(self.fmu.getReal, self._global_vrs)
        return dict(zip(self._global_vars, values))

    def runtime_s(self) -> float:
        return self._runtime_s

    def save_state(self) -> object:
        return _SavedState(self._timed_call(self.fmu.getFMUstate), self.time_s)

    def restore_state(self, handle: object) -> None:
        self._timed_call(self.fmu.setFMUstate, handle.fmu_state)
        self.time_s = handle.time_s

    def free_state(self, handle: object) -> None:
        self._timed_call(self.fmu.freeFMUstate, handle.fmu_state)

    def close(self) -> None:
        global _active_backend
        if self._closed:
            return
        self._closed = True
        try:
            if self._snapshot is not None:
                self._timed_call(self.fmu.freeFMUstate, self._snapshot)
                self._snapshot = None
            if self.fmu is not None:
                try:
                    self._timed_call(self.fmu.terminate)
                finally:
                    self._timed_call(self.fmu.freeInstance)
        finally:
            if self._unzipdir is not None:
                rmtree(self._unzipdir, ignore_errors=True)
            if _active_backend is self:
                _active_backend = None
