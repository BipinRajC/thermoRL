"""Descriptive E12 input regime; no policy, engine or FMU execution."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from thermorl2.experiments.provenance import sha256_file,require_assertions
from thermorl2.experiments.run import PROJECT,load_config
from thermorl2.raps_adapter.power_model import legacy_config,job_increment_kw
from thermorl2.raps_adapter.systems import repo_root
from thermorl2.raps_adapter.workload.alibaba import load_pods,map_pods


def offered_profile(frame,n_nodes,horizon_s,window_start_s=3600,hour_s=3600):
    starts=frame.submit_time.to_numpy(dtype=float)
    ends=starts+frame.expected_run_time.to_numpy(dtype=float)
    nodes=frame.nodes_required.to_numpy(dtype=float)
    times=np.r_[0.,float(horizon_s),starts,ends]
    deltas=np.r_[0.,0.,nodes,-nodes]
    keep=(times>=0)&(times<=horizon_s)
    times=times[keep];deltas=deltas[keep]
    points,inverse=np.unique(times,return_inverse=True)
    grouped=np.zeros(len(points));np.add.at(grouped,inverse,deltas)
    values=np.cumsum(grouped)[:-1]/n_nodes
    left,right=points[:-1],points[1:]
    def overlaps(a,b): return np.maximum(0.,np.minimum(right,b)-np.maximum(left,a))
    weights=overlaps(window_start_s,horizon_s)
    active=weights>0
    bins=np.arange(0,horizon_s+hour_s,hour_s,dtype=float)
    return {'integration':'exact piecewise-constant offered nodes on continuous [submit,submit+R), not RAPS realised occupancy',
        'hourly_arrivals':np.histogram(starts,bins=bins)[0].astype(int).tolist(),
        'hourly_mean_offered_utilisation':[float(np.sum(values*overlaps(a,b))/(b-a)) for a,b in zip(bins[:-1],bins[1:])],
        'window_mean_offered_utilisation':float(np.sum(values*weights)/(horizon_s-window_start_s)),
        'window_min_offered_utilisation':float(values[active].min()),
        'window_max_offered_utilisation':float(values[active].max()),
        'window_fraction_above_1':float(weights[values>1.].sum()/(horizon_s-window_start_s))}


def creation_concentration(creation):
    values=np.sort(np.asarray(creation,dtype=float));span=float(values[-1]-values[0])
    gaps=np.sort(np.diff(values))[::-1]
    probs=(0,.01,.1,.25,.5,.75,.9,.99,1)
    q=np.quantile(values,probs,method='linear')
    return {'pods':len(values),'span_s':span,'span_days':span/86400,
        'quantiles_s':{f'{p:g}':float(v) for p,v in zip(probs,q)},
        'quantiles_days':{f'{p:g}':float(v/86400) for p,v in zip(probs,q)},
        'largest_gap_span_shares':{str(n):float(gaps[:n].sum()/span) for n in (1,5,10,20)},
        'pods_first_30_days':int((values<values[0]+30*86400).sum()),
        'tail_covering_last_99_percent_s':float(values[-1]-q[1])}


def cap_fractions(uncapped,nodes):
    values=np.asarray(uncapped);weights=np.asarray(nodes)
    return {'pods':len(values),'strictly_clipped_count':int((values>2).sum()),
        'strictly_clipped_pod_fraction':float(np.mean(values>2)),
        'active_at_or_above_cap_pod_fraction':float(np.mean(values>=2)),
        'strictly_clipped_node_fraction':float(np.average(values>2,weights=weights)),
        'definition':'strict clipping uses uncapped CPU>2; active includes equality at 2'}


def make_record(cfg):
    legacy=legacy_config(cfg['system']);n_racks=legacy['NUM_CDUS']*legacy['RACKS_PER_CDU']
    raw_dir=Path(cfg['workload']['raw_dir'])
    if not raw_dir.is_absolute():raw_dir=repo_root()/raw_dir
    source=map_pods(load_pods(raw_dir/'openb_pod_list_default.csv'),legacy['GPUS_PER_NODE'])
    source=source.sort_values(['creation_time','source_row'],kind='stable').reset_index(drop=True)
    uncapped=source.cpu_milli.to_numpy()/1000/20/source.nodes_required.to_numpy()
    raw_multi=pd.read_csv(raw_dir/'openb_pod_list_multigpu50.csv')
    multi=map_pods(raw_multi,legacy['GPUS_PER_NODE'])
    per_seed={};frames={};references={}
    for seed in cfg['seeds']:
        entry=cfg['workload']['by_seed'][seed];path=PROJECT/entry['path']
        assert sha256_file(path)==entry['sha256'], 'frozen workload SHA mismatch'
        frames[seed]=frame=pd.read_parquet(path)
        profile=offered_profile(frame,legacy['TOTAL_NODES'],21600)
        index=(frame.attrs['start_offset']+np.arange(len(frame)))%len(source)
        assert np.array_equal(frame.cpu_util.to_numpy(),np.minimum(2,uncapped[index])), 'CPU source lineage mismatch'
        overlaps=np.maximum(0.,np.minimum(frame.submit_time+frame.expected_run_time,21600)-np.maximum(frame.submit_time,3600))
        increments=np.asarray([job_increment_kw(legacy,float(c),float(g),int(n))
            for c,g,n in zip(frame.cpu_util,frame.gpu_util,frame.nodes_required)])
        profile.update(jobs_offered=len(frame),cpu_cap=cap_fractions(uncapped[index],frame.nodes_required),
            window_mean_modelled_kw_above_idle_per_rack=float(np.sum(increments*overlaps)/(18000*n_racks)),
            power_basis='frozen job_increment_kw; RAPS node model, network0, loss-exclusive; actual rectifier-inclusive rack inputs are observed at execution')
        per_seed[str(seed)]=profile;references[entry['path']]=entry['sha256']
    a,b=frames[2],frames[3].iloc[162:].reset_index(drop=True)
    fields=['nodes_required','cpu_util','gpu_util','expected_run_time','time_limit']
    requests_equal=len(a)==len(b) and all(np.array_equal(a[k],b[k]) for k in fields)
    shift=b.submit_time.to_numpy()-a.submit_time.to_numpy()
    identity={'leading_pods_in_seed3':162,'remaining_jobs':len(b),'request_columns_exactly_equal':requests_equal,
        'id_offset_exact':bool(np.array_equal(b.id.to_numpy()-162,a.id.to_numpy())),
        'time_shift_first_s':float(shift[0]),'time_shift_min_s':float(shift.min()),'time_shift_max_s':float(shift.max()),
        'max_deviation_from_first_s':float(np.max(np.abs(shift-shift[0]))),
        'scope':'about two workload conditions; seed2/3 are not determinism or sensitivity evidence; time-shift differences reflect sequential float accumulation'}
    assert requests_equal and identity['id_offset_exact'], 'seed2/3 request identity differs from review'
    concentration=creation_concentration(source.creation_time)
    scale=frames[1].attrs['arrival_compression_factor']
    return {'scope':'descriptive pre-run input characterisation only; no simulation or policy outcome',
        'window':'3600 < t <= 21600; positive-duration segments; continuous offered demand',
        'nominal_rho':.6,'per_seed':per_seed,'source_creation_concentration':concentration,
        'source_cpu_cap':cap_fractions(uncapped,source.nodes_required),
        'multigpu50_resource_only_cpu_cap':cap_fractions(multi.cpu_milli.to_numpy()/1000/20/multi.nodes_required,multi.nodes_required),
        'seed2_seed3_identity':identity,
        'dense_tail_99_percent_proxy_minutes':concentration['tail_covering_last_99_percent_s']/scale/60,
        'source_span_compressed_minutes':concentration['span_s']/scale/60,
        'references_sha256':{**references,str((raw_dir/'openb_pod_list_default.csv').relative_to(repo_root())):sha256_file(raw_dir/'openb_pod_list_default.csv')},
        'calculation_source_sha256':sha256_file(Path(__file__)),
        'comparison_to_review':'hourly counts should agree exactly; means/overload are exact event integrals rather than any sampled approximation; review numbers rounded to 2-3 decimals'}


def main():
    require_assertions()
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args();cfg=load_config(args.config)
    out=Path(cfg['experiment_dir'].format(system=cfg['system']))/'results/workload_regime.json'
    record=make_record(cfg)
    with out.open('x') as target:target.write(json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps(record,indent=2,sort_keys=True))


if __name__=='__main__':main()
