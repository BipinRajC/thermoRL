from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from thermorl2.experiments.provenance import sha256_file
out=Path('experiments/summit/E12_g4_alibaba');details={};inventory={}
for path in sorted((out/'runs').iterdir()):
    m=json.loads((path/'manifest.json').read_text())
    frame=pd.read_parquet(path/'intervals.parquet',columns=['t_s','n_running','n_queued','free','it_kw_total','kw','t_c'])
    g=frame.groupby('t_s');series=g.first();tail=series.loc[(series.index>3600)&(series.index<=21600)]
    work=pd.read_parquet(m['workload_path']).set_index('id');waits=[]
    with (path/'decisions.jsonl').open() as f:
        for line in f:
            row=json.loads(line);waits.append(row['t_s']-float(work.loc[row['job_id'],'submit_time']))
    waits=np.asarray(waits)
    details[path.name]={'max_queue_jobs_episode':int(series.n_queued.max()),'queue_positive_fraction_eval':float((tail.n_queued>0).mean()),'full_capacity_fraction_eval':float((g.free.sum().loc[tail.index]==0).mean()),'wait_max_s':float(waits.max()),'wait_over_1s_fraction':float((waits>1).mean()),'it_kw_min_max_eval':[float(tail.it_kw_total.min()),float(tail.it_kw_total.max())],'mean_loss_inclusive_above_idle_kw_per_rack_eval':float(frame.loc[frame.t_s>3600,'kw'].mean()-m['idle_kw']),'coolant_over_70_samples_episode':int((frame.t_c>70).sum()),'negative_episode_pump_samples':m['negative_episode_pump_samples'],'manifest_sha256':sha256_file(path/'manifest.json'),'source_sha256':m['source_sha256'],'launch_sha':m['git']['sha'],'process_peak_rss_bytes':m['process_memory']['peak_rss_bytes']}
    target=out/'provenance/manifests'/f'{path.name}.json';target.parent.mkdir(exist_ok=True)
    with target.open('xb') as f:f.write((path/'manifest.json').read_bytes())
    assert target.read_bytes()==(path/'manifest.json').read_bytes()
with (out/'results/operational_diagnostics.json').open('x') as f:f.write(json.dumps(details,indent=2,sort_keys=True)+'\n')
print(json.dumps({n:{k:v for k,v in r.items() if k!='source_sha256'} for n,r in details.items()},indent=2))
