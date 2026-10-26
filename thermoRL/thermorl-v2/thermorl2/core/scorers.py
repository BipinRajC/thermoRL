"""Frozen placement scores; no RAPS, FMU or learning dependencies."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class RackContext:
    free_count: np.ndarray
    committed_kw: np.ndarray
    t_c: np.ndarray
    job_kw: float
    job_nodes: int


class Scorer(Protocol):
    name: str
    params: dict

    def score(self, ctx: RackContext) -> np.ndarray: ...


class Packing:
    name = "packing"
    params = {}

    def score(self, ctx):
        return -np.arange(len(ctx.free_count), dtype=float)


class NodeBalance:
    name = "node_balance"
    params = {}

    def score(self, ctx):
        return np.asarray(ctx.free_count, dtype=float).copy()


class PowerBalance:
    name = "power_balance"
    params = {}

    def score(self, ctx):
        return -np.asarray(ctx.committed_kw, dtype=float)


class CoolestRack:
    name = "coolest_rack"
    params = {}

    def score(self, ctx):
        return -np.asarray(ctx.t_c, dtype=float)


@dataclass(frozen=True)
class ThermalPredictive:
    a_c: float
    b_c_per_kw: float
    tau_s: float
    horizon_s: float = 600.0
    name = "thermal_predictive"

    @property
    def params(self):
        return {"a_c": self.a_c, "b_c_per_kw": self.b_c_per_kw, "tau_s": self.tau_s, "horizon_s": self.horizon_s}

    def score(self, ctx):
        weight = 1 - np.exp(-self.horizon_s / self.tau_s)
        return -(ctx.t_c + (self.a_c + self.b_c_per_kw * (ctx.committed_kw + ctx.job_kw) - ctx.t_c) * weight)


def make_scorer(name: str, params: dict) -> Scorer:
    classes = {"packing": Packing, "node_balance": NodeBalance, "power_balance": PowerBalance,
               "coolest_rack": CoolestRack, "thermal_predictive": ThermalPredictive}
    if name not in classes:
        raise ValueError(f"unknown scorer: {name}")
    return classes[name](**params)
