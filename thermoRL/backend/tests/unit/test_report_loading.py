import json
import weakref

import pandas as pd

from thermorl2.core.metrics import Run
from thermorl2.experiments import report


def test_metrics_only_loading_releases_each_seed_before_loading_next(tmp_path,monkeypatch):
    paths=[]
    params=dict(a_c=28,b_c_per_kw=.8,tau_s=4050,horizon_s=600)
    for seed in (1,2,3):
        for policy in report.POLICIES:
            p=tmp_path/'input'/f'{policy}_seed{seed}';p.mkdir(parents=True)
            (p/'manifest.json').write_text(json.dumps(dict(seed=seed,policy=policy)))
            paths.append(p)
    frame=pd.DataFrame([dict(t_s=t,rack=r,t_c=40.+r,kw=1.,pump_kw=1.,free=1,it_kw_total=3.)
                        for t in (10.,20.) for r in range(3)])
    references=[];peak=0
    def load(path):
        nonlocal peak
        alive=sum(ref() is not None for ref in references)
        assert alive<5, 'previous seed must be released before the sixth Run loads'
        m=json.loads((path/'manifest.json').read_text())
        m.update(n_racks=3,nodes_per_rack=2,total_nodes=6,power_tick_s=10,fmu_steps=2,
                 backend_elapsed_s=20.,config={'horizon_h':20/3600},t_idle_c=[30]*3,
                 raps_s=1.,fmu_s=2.,total_s=3.,thermal_predictive_params=params)
        run=Run(path.name,frame.copy(),[],m)
        references.append(weakref.ref(run));peak=max(peak,alive+1)
        return run
    def validate(runs,proof,cfg,**kwargs):
        seed=runs[0].manifest['seed']
        evidence=[dict(kind='inherited_E10',scope='fixture',result=True,ref='fixture')]
        if seed==1:evidence.append(dict(kind='E11_prefix_vs_E10',scope='fixture',result=True,ref='fixture'))
        return {'invariants':{'1_fixture':True,'3_fixture':dict(status='inherited_not_remeasured',evidence=evidence)}}
    monkeypatch.setattr(report,'load_run',load)
    monkeypatch.setattr(report,'validate_seed',validate)
    cfg={'policies':list(report.POLICIES),'seeds':[1,2,3]}
    result=report.build_report_from_paths(paths,tmp_path/'output',0,63.3,(1,3),
        determinism_evidence={},expected_config=cfg,metrics_only=True)
    assert peak==5 and all(ref() is None for ref in references)
    assert result['scope']=='metrics-only regeneration; no new simulation'
    table=pd.read_csv(tmp_path/'output/results/metrics.csv')
    assert table.name.tolist()==[p.name for p in paths]
    assert table.maxrack_mean_c.tolist()==[42.]*15
