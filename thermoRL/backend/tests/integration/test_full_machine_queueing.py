import numpy as np
import pandas as pd
from raps.job import Job,job_dict

from thermorl2.core.metrics import Run
from thermorl2.core.scorers import make_scorer
from thermorl2.experiments.report import allocation_valid
from thermorl2.raps_adapter.engine_factory import EngineSpec,build_engine,is_power_tick,rack_kw_from_power_df
from thermorl2.raps_adapter.power_model import legacy_config
from thermorl2.raps_adapter.rack_geometry import RackGeometry
from thermorl2.raps_adapter.scheduler import PlacementScheduler,ThermalView


def test_full_and_partial_capacity_head_of_line_persists_across_ticks():
    cfg=legacy_config('summit');g=RackGeometry.from_legacy_config(cfg)
    start_maps=[]
    for policy in ('packing','power_balance'):
        requests=[(0,g.total_nodes-1,0.,301),(1,1,0.,201),(2,2,1.,301),(3,1,2.,301)]
        jobs=[Job(job_dict(id=i,name=f'fixture{i}',account='test',nodes_required=n,submit_time=t,
            expected_run_time=runtime,time_limit=1200,cpu_trace=1.,gpu_trace=1.,ntx_trace=0,nrx_trace=0,
            start_time=None,end_time=None)) for i,n,t,runtime in requests]
        engine=build_engine(EngineSpec('summit','620s',1),jobs=jobs)
        decisions=[];events=[];full_ticks=[];partial_ticks=[]
        def record(row):
            decisions.append(row)
            events.append(dict(event='start',t_s=row['t_s'],job_id=row['job_id'],nodes=row['nodes'],decision_index=len(decisions)-1))
        scheduler=PlacementScheduler(engine.resource_manager,g,make_scorer(policy,{}),cfg,record)
        scheduler.on_thermal(ThermalView(0.,np.full(g.n_racks,30.),np.ones(g.n_racks)))
        engine.scheduler=scheduler
        for tick in engine.run_simulation():
            for job in tick.completed:
                events.append(dict(event='complete',t_s=int(tick.current_timestep),job_id=job.id,nodes=list(job.scheduled_nodes)))
            if not is_power_tick(tick,10):continue
            t=tick.current_timestep;free=len(engine.resource_manager.available_nodes)
            scheduler.on_power_tick(rack_kw_from_power_df(tick.power_df,cfg['RACKS_PER_CDU']))
            if 10<=t<=200:
                assert free==0 and [job.id for job in tick.queue]==[2,3]
                full_ticks.append(t)
            if 210<=t<=300:
                assert free==1 and [job.id for job in tick.queue]==[2,3]
                partial_ticks.append(t)
        starts={r['job_id']:r['t_s'] for r in decisions}
        assert starts=={0:0,1:0,2:302,3:302}
        assert len(full_ticks)==20 and len(partial_ticks)==10
        assert len(engine.resource_manager.available_nodes)==g.total_nodes
        events.sort(key=lambda e:(e['t_s'],e['event']!='complete',e.get('decision_index',e['job_id'])))
        workload=pd.DataFrame([dict(id=i,nodes_required=n,submit_time=t) for i,n,t,_ in requests])
        run=Run(policy,pd.DataFrame(),decisions,dict(total_nodes=g.total_nodes,n_racks=g.n_racks,nodes_per_rack=g.nodes_per_rack),
                workload=workload,job_events=events)
        assert allocation_valid(run)
        start_maps.append(starts)
    assert start_maps[0]==start_maps[1]
