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
