import json

import pandas as pd
import pytest

from thermorl2.core.metrics import Run,invariants
from thermorl2.experiments import run_matrix


@pytest.mark.parametrize('mutation',['none','power','start','grid','steps'])
def test_lightweight_check_matches_core_semantics(tmp_path,mutation):
    paths=[];runs=[]
    for index in range(2):
        path=tmp_path/f'run{index}';path.mkdir();paths.append(path)
        frame=pd.DataFrame([dict(t_s=t,rack=r,it_kw_total=6.,kw=2.) for t in (10.,20.,30.,40.) for r in range(3)])
        decisions=[dict(job_id=1,t_s=5,irrelevant_array=[0]*100)]
        m=dict(power_tick_s=10,n_racks=3,fmu_steps=4,backend_elapsed_s=40.,config={'horizon_h':40/3600})
        if index==1:
            if mutation=='power':frame.loc[frame.t_s==20,'it_kw_total']+=1
            if mutation=='start':decisions[0]['t_s']=6
            if mutation=='grid':frame=frame[frame.t_s!=40]
            if mutation=='steps':m['fmu_steps']=3
        frame.to_parquet(path/'intervals.parquet',index=False)
        (path/'manifest.json').write_text(json.dumps(m))
        (path/'decisions.jsonl').write_text(json.dumps(decisions[0])+'\n')
        runs.append(Run(path.name,frame,decisions,m))
    assert run_matrix.lightweight_invariants(paths)==invariants(runs)
