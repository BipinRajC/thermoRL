"""Alibaba-derived workload under Bipin's D2–D4 decisions (2026-10-30).

Only default has the phase/timing fields needed for simulation. Arrival gaps
are compressed; durations are not. Seeds rotate one cyclic source sequence.
"""

import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from thermorl2.raps_adapter.power_model import node_power_kw
from thermorl2.raps_adapter.systems import repo_root
from thermorl2.raps_adapter.workload.synthetic import WORKLOAD_COLUMNS

TIMING_FIELDS = ('pod_phase','creation_time','deletion_time')
RESOURCE_FIELDS = ('cpu_milli','num_gpu','gpu_milli')


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _source_path(path):
    path=Path(path).resolve()
    try:
        return str(path.relative_to(repo_root()))
    except ValueError:
        return str(path)


def _numeric(frame,columns):
    for name in columns:
        frame[name]=pd.to_numeric(frame[name],errors='raise')
        if not np.isfinite(frame[name].to_numpy(dtype=float)).all():
            raise ValueError(f'non-finite source field: {name}')


def _phase_mix(frame):
    return {str(key):int(value) for key,value in frame.pod_phase.value_counts().sort_index().items()}


def load_pods(csv_path) -> pd.DataFrame:
    path=Path(csv_path)
    frame=pd.read_csv(path)
    missing=sorted(set(TIMING_FIELDS+RESOURCE_FIELDS)-set(frame.columns))
    if missing:
        raise ValueError(f'missing required phase/timing/resource fields: {missing}')
    frame['source_row']=np.arange(len(frame),dtype=np.int64)
    _numeric(frame,('num_gpu','creation_time','deletion_time'))
    if frame.pod_phase.isna().any():
        raise ValueError('missing source phase')
    kept=frame.loc[(frame.pod_phase!='Pending') & (frame.num_gpu>0)].copy()
    kept['runtime_s']=kept.deletion_time-kept.creation_time
    kept.attrs={'source_path':_source_path(path),'source_sha256':_sha(path),
                'raw_rows':len(frame),'source_phase_mix_raw':_phase_mix(frame),
                'source_phase_mix_kept':_phase_mix(kept),
                'phase_filter':'pod_phase != Pending and num_gpu > 0; includes Failed and Running',
                'runtime_assumption':'deletion_time - creation_time in seconds, regardless of kept phase'}
    return kept.reset_index(drop=True)


def map_pods(pods,gpus_per_node,cpus_per_socket=20) -> pd.DataFrame:
    """Resource-only mapping is also usable descriptively without timing fields."""
    if gpus_per_node<=0 or cpus_per_socket<=0:
        raise ValueError('positive device/socket capacities required')
    frame=pods.copy()
    _numeric(frame,RESOURCE_FIELDS)
    frame=frame.loc[frame.num_gpu>0].copy()
    if (frame[list(RESOURCE_FIELDS)]<0).any().any():
        raise ValueError('negative source resource request')
    if not np.equal(frame.num_gpu,np.floor(frame.num_gpu)).all():
        raise ValueError('num_gpu must be an integer device count')
    frame['nodes_required']=np.maximum(1,np.ceil(frame.num_gpu/gpus_per_node)).astype(np.int64)
    frame['gpu_util']=np.minimum(gpus_per_node,frame.num_gpu*frame.gpu_milli/1000/frame.nodes_required)
    frame['cpu_util']=np.minimum(2,frame.cpu_milli/1000/cpus_per_socket/frame.nodes_required)
    if 'source_row' not in frame:
        frame['source_row']=np.arange(len(frame),dtype=np.int64)
    frame.attrs={**pods.attrs,'gpus_per_node':int(gpus_per_node),'cpus_per_socket_assumption':cpus_per_socket,
                 'mapping':'nodes=ceil(num_gpu/G); gpu=min(G,num_gpu*gpu_milli/1000/nodes); cpu=min(2,cpu_milli/1000/20/nodes)'}
    return frame.reset_index(drop=True)


def _runtime_clip(raw,horizon_s):
    values=np.asarray(raw,dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('finite nonempty source runtimes required')
    clipped=np.clip(values,300,horizon_s)
    assert np.equal(clipped,np.floor(clipped)).all(), 'clipped Alibaba runtimes must be integer seconds; no rounding authorized'
    return clipped.astype(np.int64),{
        'min_s':300,'max_s':int(horizon_s),'source_count':len(values),
        'below_min_count':int((values<300).sum()),'above_max_count':int((values>horizon_s).sum()),
        'below_min_fraction':float(np.mean(values<300)),'above_max_fraction':float(np.mean(values>horizon_s)),
        'nonpositive_raw_count':int((values<=0).sum()),'raw_min_s':float(values.min()),
        'raw_median_s':float(np.median(values)),'raw_max_s':float(values.max())}


def pod_power_stats(mapped,cfg) -> dict:
    weights=mapped.nodes_required.to_numpy(dtype=int)
    if not len(weights) or weights.sum()<=0:
        raise ValueError('nonempty mapped node population required')
    idle=node_power_kw(cfg,0,0)
    increments=np.asarray([node_power_kw(cfg,float(cpu),float(gpu))-idle
                           for cpu,gpu in zip(mapped.cpu_util,mapped.gpu_util)])
    return {'pods':len(mapped),'nodes':int(weights.sum()),'max_nodes_per_pod':int(weights.max()),
            'mean_node_increment_kw':float(np.average(increments,weights=weights)),
            'share_nodes_ge2_gpu':float(np.average(mapped.gpu_util.to_numpy()>=2,weights=weights)),
            'mean_gpu_util_per_node':float(np.average(mapped.gpu_util,weights=weights)),
            'mean_cpu_util_per_node':float(np.average(mapped.cpu_util,weights=weights)),
            'unweighted_mean_pod_node_increment_kw':float(increments.mean()),
            'weighting':'node-weighted across mapped nodes; unweighted pod mean reported separately',
            'power_basis':'frozen RAPS compute_node_power increment above idle, network=0; loss-exclusive, no rectifier correction'}


def choose_variant(raw_dir,cfg,out_dir=None) -> dict:
    """D2 fixes default; resource-only statistics never select a source variant."""
    variants={}
    for variant in ('default','multigpu50'):
        path=Path(raw_dir)/f'openb_pod_list_{variant}.csv'
        raw=pd.read_csv(path)
        missing=[name for name in TIMING_FIELDS if name not in raw]
        item={'source_path':_source_path(path),'source_sha256':_sha(path),'columns':raw.columns.tolist(),
              'raw_rows':len(raw),'simulation_eligible':not missing,'missing_timing_fields':missing,
              'power_stats_resource_only':pod_power_stats(map_pods(raw,cfg['GPUS_PER_NODE']),cfg),
              'resource_only_population':'all rows with num_gpu > 0; no phase filter applied'}
        if not missing:
            mapped=map_pods(load_pods(path),cfg['GPUS_PER_NODE'])
            _,clip=_runtime_clip(mapped.runtime_s,21600)
            item.update(runnable_rows=len(mapped),phase_mix_raw=_phase_mix(raw),phase_mix_kept=_phase_mix(mapped),
                        runtime_clip=clip,power_stats_runnable=pod_power_stats(mapped,cfg))
        else:
            item['timing_note']='phase, arrival and duration unavailable; no timing join or imputation; statistics descriptive only'
        variants[variant]=item
    record={'selected_variant':'default','selection_rule':'Bipin D2: default only; not selected by power or policy outcomes',
            'variants':variants,'generator_source_sha256':_sha(__file__),
            'mapping_assumptions':{'cpus_per_socket':20,'cpu_util_cap':2,'gpus_per_node':cfg['GPUS_PER_NODE']}}
    if out_dir is not None:
        path=Path(out_dir)/'variant_choice.json';path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as out:
            out.write(json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return record


def derive_workload(mapped,rho,horizon_s,seed,n_nodes) -> pd.DataFrame:
    if seed<1 or not 0<rho<=1 or horizon_s<300 or n_nodes<1:
        raise ValueError('positive seed/nodes, rho in (0,1], and horizon >=300 required')
    frame=mapped.copy()
    _numeric(frame,('creation_time','runtime_s','nodes_required','cpu_util','gpu_util'))
    if 'source_row' not in frame: frame['source_row']=np.arange(len(frame),dtype=np.int64)
    frame=frame.sort_values(['creation_time','source_row'],kind='stable').reset_index(drop=True)
    if len(frame)<2 or frame.nodes_required.max()>n_nodes:
        raise ValueError('at least two feasible source pods required')
    runtimes,clip=_runtime_clip(frame.runtime_s,horizon_s)
    original_gaps=np.diff(frame.creation_time.to_numpy(dtype=float))
    mean_gap=float(original_gaps.mean())
    if mean_gap<=0:
        raise ValueError('positive mean original inter-arrival required')
    incoming=np.concatenate(([mean_gap],original_gaps))
    expected=float(np.mean(frame.nodes_required.to_numpy()*runtimes))
    target=expected/(rho*n_nodes)
    scale=mean_gap/target
    offset=int(np.random.default_rng(seed).integers(len(frame)))
    count=0;submit=0.0;rows=[]
    while True:
        index=(offset+count)%len(frame)
        submit+=float(incoming[index]/scale)
        if submit>=horizon_s: break
        source=frame.iloc[index]
        runtime=int(runtimes[index]);limit=int(np.ceil(1.5*runtime))
        assert limit>=runtime, 'time_limit must cover represented runtime'
        rows.append((count,int(source.nodes_required),float(source.cpu_util),float(source.gpu_util),submit,runtime,limit))
        count+=1
    if not rows: raise ValueError('no arrivals within the requested horizon')
    result=pd.DataFrame(rows,columns=WORKLOAD_COLUMNS)
    selected=(offset+np.arange(len(result)))%len(frame)
    result.attrs={**mapped.attrs,'workload_kind':'alibaba','variant':'default','seed':int(seed),
        'rho':float(rho),'start_offset':offset,'source_pods':len(frame),
        'mean_original_interarrival_s':mean_gap,'wrap_gap_s':mean_gap,'expected_node_seconds_exact':expected,
        'target_interarrival_s':target,'arrival_compression_factor':scale,
        'source_cycle_passes':len(result)/len(frame),'wrap_events':int((selected==0).sum()),'runtime_clip':clip,
        'source_creation_min_s':float(frame.creation_time.min()),'source_creation_max_s':float(frame.creation_time.max()),
        'ordered_source_rows_sha256':hashlib.sha256(json.dumps(frame.source_row.astype(int).tolist(),separators=(',',':')).encode()).hexdigest(),
        'generator_source_sha256':_sha(__file__),
        'representation':'D3: deletion-creation seconds, clip [300,horizon], assert integer, limit=ceil(1.5R); no runtime compression',
        'rng_draw_order':'one default_rng(seed).integers(source_pods) start offset only; seeds are rotations',
        'arrival_rule':'sort (creation_time,source_row); incoming gaps=[mean(diff creation),diff creation]; gap/scale; cumulative submits < horizon; admission ceil(submit)',
        'lineage_rule':'job id i uses ordered source pod (start_offset+i) % source_pods',
        'versions':{name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow')}}
    if 'pod_phase' in frame:
        result.attrs['generated_phase_mix']=_phase_mix(frame.iloc[selected])
    return result
