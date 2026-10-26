"""RAPS power/configuration access stays inside the adapter."""

from raps.power import compute_node_power
from raps.system_config import get_system_config


def legacy_config(system: str) -> dict:
    return get_system_config(system).get_legacy()


def node_power_kw(cfg: dict, cpu_util: float, gpu_util: float) -> float:
    return float(compute_node_power(cpu_util, gpu_util, 0, cfg)[0]) / 1000.0


def rack_power_bounds(cfg: dict) -> tuple[float, float]:
    switches_kw = cfg["CHASSIS_PER_RACK"] * cfg["SWITCHES_PER_CHASSIS"] * cfg["POWER_SWITCH"] / 1000.0
    idle = cfg["NODES_PER_RACK"] * node_power_kw(cfg, 0, 0) + switches_kw
    peak = cfg["NODES_PER_RACK"] * node_power_kw(cfg, cfg["CPUS_PER_NODE"], cfg["GPUS_PER_NODE"]) + switches_kw
    return idle, peak


def job_increment_kw(cfg: dict, cpu_util: float, gpu_util: float, n_nodes: int) -> float:
    return n_nodes * (node_power_kw(cfg, cpu_util, gpu_util) - node_power_kw(cfg, 0, 0))
