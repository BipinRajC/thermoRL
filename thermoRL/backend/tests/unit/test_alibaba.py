import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thermorl2.raps_adapter.workload import alibaba
from thermorl2.raps_adapter.workload.synthetic import offered_utilisation, WORKLOAD_COLUMNS
from thermorl2.raps_adapter.power_model import legacy_config, node_power_kw


def source_frame():
    return pd.DataFrame(dict(name=['a','b','c'],cpu_milli=[2000,4000,6000],
        num_gpu=[1,1,1],gpu_milli=[500,1000,1000],pod_phase=['Running','Failed','Succeeded'],
        creation_time=[0,10,40],deletion_time=[600,610,640]))


def mapped_fixture():
    frame=source_frame()
    frame['runtime_s']=600
    frame['source_row']=range(len(frame))
    return alibaba.map_pods(frame,6)


@pytest.mark.parametrize('gpus,num_gpu,milli,nodes,util',[(4,8,1000,2,4.),(4,1,500,1,.5),(6,8,1000,2,4.)])
def test_plan_gpu_mapping(gpus,num_gpu,milli,nodes,util):
    frame=source_frame().iloc[:1].copy()
    frame['num_gpu']=num_gpu; frame['gpu_milli']=milli
    result=alibaba.map_pods(frame,gpus)
    assert result.nodes_required.iloc[0]==nodes
    assert result.gpu_util.iloc[0]==util
    assert result.cpu_util.iloc[0]==pytest.approx(2000/1000/20/nodes)


def test_filter_preserves_failed_running_and_source_rows(tmp_path):
    frame=source_frame()
    frame=pd.concat([frame,frame.iloc[[0]].assign(name='pending',pod_phase='Pending'),
                     frame.iloc[[0]].assign(name='cpu',num_gpu=0)],ignore_index=True)
    path=tmp_path/'pods.csv';frame.to_csv(path,index=False)
    kept=alibaba.load_pods(path)
    assert kept.name.tolist()==['a','b','c']
    assert kept.source_row.tolist()==[0,1,2]
    assert kept.runtime_s.tolist()==[600,600,600]
    assert kept.attrs['source_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_multigpu_timing_is_rejected_not_imputed(tmp_path):
    path=tmp_path/'pods.csv'
    source_frame().drop(columns=['pod_phase','creation_time','deletion_time']).to_csv(path,index=False)
    with pytest.raises(ValueError,match='missing'):
        alibaba.load_pods(path)


def test_cyclic_incoming_gap_wrap_and_exact_scaling():
    # Original incoming cycle [20(mean wrap),10,30]; target IA=10;
    # seed1 chooses offset1: scaled incoming gaps [5,15,10,5,15,...].
    frame=alibaba.derive_workload(mapped_fixture(),.6,21600,1,100)
    np.testing.assert_array_equal(frame.submit_time.iloc[:5],[5,20,30,35,50])
    assert frame.attrs['start_offset']==1
    assert frame.attrs['mean_original_interarrival_s']==20
    assert frame.attrs['target_interarrival_s']==10
    assert frame.attrs['arrival_compression_factor']==2
    assert frame.attrs['expected_node_seconds_exact']==600
    assert list(frame.columns)==WORKLOAD_COLUMNS


def test_seed_rotations_determinism_and_offered_utilisation():
    a=alibaba.derive_workload(mapped_fixture(),.6,21600,1,100)
    b=alibaba.derive_workload(mapped_fixture(),.6,21600,1,100)
    pd.testing.assert_frame_equal(a,b,check_exact=True)
    c=alibaba.derive_workload(mapped_fixture(),.6,21600,2,100)
    assert c.attrs['start_offset']==2
    assert not a.equals(c)
    assert .51<=offered_utilisation(a,21600,100)<=.69
    assert a.submit_time.is_monotonic_increasing
    assert a.submit_time.between(0,21600,inclusive='left').all()
    assert (a.time_limit>=a.expected_run_time).all()
    assert pd.api.types.is_integer_dtype(a.expected_run_time)
    assert pd.api.types.is_integer_dtype(a.time_limit)


def test_runtime_clipping_integer_assertion_and_limit():
    mapped=pd.concat([mapped_fixture().iloc[[0]]]*4,ignore_index=True)
    mapped['creation_time']=[0,10,20,30];mapped['source_row']=range(4)
    mapped['runtime_s']=[299,321,21600,21601]
    result=alibaba.derive_workload(mapped,.6,21600,1,100)
    assert set(result.expected_run_time)=={300,321,21600}
    np.testing.assert_array_equal(result.time_limit,np.ceil(1.5*result.expected_run_time).astype(int))
    assert result.attrs['runtime_clip']['below_min_count']==1
    assert result.attrs['runtime_clip']['above_max_count']==1
    mapped['runtime_s']=mapped.runtime_s.astype(float)
    mapped.loc[1,'runtime_s']=321.5
    with pytest.raises(AssertionError,match='integer'):
        alibaba.derive_workload(mapped,.6,21600,1,100)


def test_equal_creation_times_use_original_file_row_ties():
    mapped=mapped_fixture()
    mapped['creation_time']=[0,0,30]
    mapped['source_row']=[2,0,1]
    result=alibaba.derive_workload(mapped,.6,21600,1,100)
    # Order becomes source row0 (CPU .2), row2 (.1), row1 (.3).
    # Seed offset1 chooses row2 first, whose incoming gap is zero.
    assert result.submit_time.iloc[0]==0.0
    assert result.cpu_util.iloc[:3].tolist()==pytest.approx([.1,.3,.2])


def test_node_weighted_power_statistics():
    cfg=legacy_config('summit')
    frame=pd.DataFrame(dict(nodes_required=[1,2],cpu_util=[.1,.5],gpu_util=[.5,4.]))
    stats=alibaba.pod_power_stats(frame,cfg)
    a=node_power_kw(cfg,.1,.5)-node_power_kw(cfg,0,0)
    b=node_power_kw(cfg,.5,4)-node_power_kw(cfg,0,0)
    assert stats['mean_node_increment_kw']==pytest.approx((a+2*b)/3)
    assert stats['share_nodes_ge2_gpu']==pytest.approx(2/3)


def test_default_only_variant_record_is_descriptive_and_no_overwrite(tmp_path):
    raw=tmp_path/'raw';raw.mkdir()
    source_frame().to_csv(raw/'openb_pod_list_default.csv',index=False)
    source_frame().drop(columns=['pod_phase','creation_time','deletion_time']).to_csv(raw/'openb_pod_list_multigpu50.csv',index=False)
    out=tmp_path/'results'
    record=alibaba.choose_variant(raw,legacy_config('summit'),out)
    assert record['selected_variant']=='default'
    assert not record['variants']['multigpu50']['simulation_eligible']
    assert set(record['variants']['multigpu50']['missing_timing_fields'])=={'pod_phase','creation_time','deletion_time'}
    assert record['variants']['multigpu50']['power_stats_resource_only']['nodes']>0
    assert json.loads((out/'variant_choice.json').read_text())==record
    with pytest.raises(FileExistsError):alibaba.choose_variant(raw,legacy_config('summit'),out)


def test_prepare_workload_dispatch_and_sha_keyed_sidecar(tmp_path,monkeypatch):
    from thermorl2.experiments.run import prepare_workload
    raw=tmp_path/'raw';raw.mkdir()
    source_frame().to_csv(raw/'openb_pod_list_default.csv',index=False)
    monkeypatch.chdir(tmp_path)
    cfg=dict(system='summit',horizon_h=6,workload=dict(kind='alibaba',rho=.6,raw_dir=str(raw),variant='default'))
    record=prepare_workload(cfg,1)
    path=Path(record['path']);meta=json.loads(Path(record['meta_path']).read_text())
    assert path.stem==hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
    assert meta['workload_kind']=='alibaba' and meta['variant']=='default' and meta['horizon_s']==21600
    assert meta['source_sha256']==hashlib.sha256((raw/'openb_pod_list_default.csv').read_bytes()).hexdigest()
    assert prepare_workload(cfg,1)==record


def test_runner_dispatch_validates_alibaba_kind_without_simulation(tmp_path):
    from thermorl2.raps_adapter.runner import load_episode_workload
    frame=alibaba.derive_workload(mapped_fixture(),.6,21600,1,100)
    from thermorl2.raps_adapter.workload.synthetic import write_workload
    path=tmp_path/'a.parquet'
    digest=write_workload(frame,path,{'horizon_s':21600})
    cfg={'workload':{'kind':'alibaba','path':str(path),'sha256':digest}}
    resolved,loaded,meta=load_episode_workload(cfg,1,21600)
    assert resolved==path and meta['workload_kind']=='alibaba'
    pd.testing.assert_frame_equal(loaded,frame,check_exact=True)
    cfg['workload']['kind']='unknown'
    with pytest.raises(ValueError,match='workload kind'):
        load_episode_workload(cfg,1,21600)
