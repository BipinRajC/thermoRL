"""FCFS exact-node placement with held thermal observations and committed power."""

from dataclasses import dataclass
from time import perf_counter_ns

import numpy as np
from raps.policy import PolicyType

from thermorl2.core.placement import place
from thermorl2.core.scorers import RackContext
from thermorl2.raps_adapter.power_model import job_increment_kw, raps_rack_kw

LATENCY_SPAN = "context construction -> scoring -> place -> placement assertions -> RAPS assign_nodes_to_job -> running.append -> queue.remove -> committed-power update; excludes queue sort, row formatting and ledger I/O"


@dataclass(frozen=True)
class ThermalView:
    t_obs_s: float
    t_c: np.ndarray
    pump_kw: np.ndarray


def _scalar(trace) -> float:
    return float(np.mean(trace))


class PlacementScheduler:
    def __init__(self, resource_manager, geometry, scorer, cfg: dict, sink, timing_sink=None):
        self.resource_manager = resource_manager
        self.geometry = geometry
        self.scorer = scorer
        self.cfg = cfg
        self.sink = sink
        self.timing_sink = timing_sink
        self.decision_index = 0
        self.policy = PolicyType.FCFS
        self.bfpolicy = None
        self.committed_kw = np.full(geometry.n_racks, raps_rack_kw(cfg, 0, 0), dtype=float)
        self._thermal = None

    def on_power_tick(self, rack_kw):
        values = np.asarray(rack_kw, dtype=float)
        if values.shape != (self.geometry.n_racks,):
            raise ValueError("power vector does not match rack geometry")
        self.committed_kw = values.copy()

    def on_thermal(self, view: ThermalView):
        if np.asarray(view.t_c).shape != (self.geometry.n_racks,) or np.asarray(view.pump_kw).shape != (self.geometry.n_racks,):
            raise ValueError("thermal vector does not match rack geometry")
        self._thermal = ThermalView(float(view.t_obs_s), np.asarray(view.t_c).copy(), np.asarray(view.pump_kw).copy())

    def schedule(self, queue, running, current_time, accounts=None, sorted=False):
        if self._thermal is None:
            raise RuntimeError("initial thermal observation must be published before scheduling")
        queue.sort(key=lambda job: (job.submit_time, job.id))
        for job in list(queue):
            if job.nodes_required > len(self.resource_manager.available_nodes):
                break
            start_ns = perf_counter_ns()
            available = set(self.resource_manager.available_nodes)
            free = [[] for _ in range(self.geometry.n_racks)]
            for node in available:
                free[self.geometry.rack_of(node)].append(int(node))
            cpu, gpu = _scalar(job.cpu_trace), _scalar(job.gpu_trace)
            increment = job_increment_kw(self.cfg, cpu, gpu, int(job.nodes_required))
            context = RackContext(np.asarray([len(nodes) for nodes in free]), self.committed_kw.copy(),
                                  np.asarray(self._thermal.t_c).copy(), increment, int(job.nodes_required))
            scores = self.scorer.score(context)
            placement = place(scores, free, int(job.nodes_required))
            assert len(placement.nodes) == len(set(placement.nodes)) == job.nodes_required
            assert set(placement.nodes) <= available
            job.scheduled_nodes = list(placement.nodes)
            self.resource_manager.assign_nodes_to_job(job, current_time, PolicyType.REPLAY)
            running.append(job)
            queue.remove(job)
            per_node_kw = job_increment_kw(self.cfg, cpu, gpu, 1)
            counts = np.bincount([self.geometry.rack_of(node) for node in placement.nodes], minlength=self.geometry.n_racks)
            self.committed_kw += counts * per_node_kw
            latency_ns = perf_counter_ns() - start_ns
            self.sink({
                "t_s": int(current_time), "job_id": int(job.id), "nodes_required": int(job.nodes_required),
                "policy": self.scorer.name, "rule": placement.rule, "racks": list(placement.racks),
                "nodes": list(placement.nodes), "job_kw": round(float(increment), 6),
                "scores": np.round(scores, 6).tolist(), "t_c": np.round(context.t_c, 6).tolist(),
                "committed_kw": np.round(context.committed_kw, 6).tolist(), "free": context.free_count.tolist(),
                "t_obs_s": float(self._thermal.t_obs_s), "latency_us": None,
            })
            if self.timing_sink is not None:
                self.timing_sink({"decision_index": self.decision_index, "job_id": int(job.id),
                                  "t_s": int(current_time), "latency_ns": int(latency_ns)})
            self.decision_index += 1
