import hashlib
import json
from pathlib import Path

import pandas as pd
from PIL import Image
import pytest

try:
    from thermorl2.experiments import demo_assets
except ImportError:
    demo_assets = None


def fixture_experiment(tmp_path, name='E12_g4_alibaba', unequal=False):
    assert demo_assets is not None, 'presentation module is not implemented'
    out=tmp_path/name
    (out/'provenance').mkdir(parents=True)
    (out/'plots').mkdir()
    (out/'plots/heatmaps_seed1.png').write_bytes(b'original figure must remain unchanged')
    workload=tmp_path/'workload.parquet'
    pd.DataFrame({'id':[1,2,3],'submit_time':[1.,2.,3.]}).to_parquet(workload,index=False)
    for policy in demo_assets.POLICIES:
        path=out/'runs'/f'{policy}_seed1';path.mkdir(parents=True)
        manifest={'policy':policy,'seed':1,'system':'summit','n_racks':3,
                  'config':{'horizon_h':6,'scenario':{'name':'nominal'}},
                  'workload_path':str(workload)}
        (path/'manifest.json').write_text(json.dumps(manifest))
        frame=pd.DataFrame([dict(t_s=t,rack=r,t_c=30+r+t/21600,kw=1+r)
                            for t in (10.,3600.,3610.,21600.) for r in range(3)])
        frame.to_parquet(path/'intervals.parquet',index=False)
        decisions=[{'t_s':i+1.,'racks':[i%3],
                    't_c':[30.,30.,30.000001 if unequal else 30.0000001]} for i in range(3)]
        (path/'decisions.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in decisions))
    return out


def test_demo_assets_render_labels_checks_inventory_without_touching_originals(tmp_path):
    out=fixture_experiment(tmp_path)
    original=(out/'plots/heatmaps_seed1.png').read_bytes()
    result=demo_assets.generate_demo_assets(out,grid=(1,3),stride_ticks=1)
    assert (out/'plots/heatmaps_seed1.png').read_bytes()==original
    check=json.loads((out/'provenance/demo_asset_checks.json').read_text())
    assert check['initial_tp']['distinct_six_decimal_values_per_row']==[1,1,1]
    assert check['initial_tp']['all_rows_thermally_identical'] is True
    assert check['early_frame_caption']==demo_assets.TIE_CAPTION
    assert len(result['assets'])==4
    for rel,item in result['assets'].items():
        path=out/rel
        assert path.stat().st_size==item['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        with Image.open(path) as image:
            description=image.info.get('Description',image.info.get('comment',b''))
            if isinstance(description,bytes):description=description.decode()
            for label in ['E12','Alibaba-derived','Summit FMU, nominal','seed 1 of 3',
                          'seeds 2/3 correlated','E11 and E12 scales differ',demo_assets.G4_CAPTION]:
                assert label in description
            if path.suffix=='.png':assert 'evaluation window starts' in description
            else:
                assert image.n_frames==4
                assert demo_assets.TIE_CAPTION in description
    with pytest.raises(FileExistsError):demo_assets.generate_demo_assets(out,grid=(1,3))


@pytest.mark.parametrize('existing',['plots/demo','provenance/demo_asset_checks.json','provenance/demo_asset_inventory.json'])
def test_preexisting_output_refused_before_writing_provenance(tmp_path,existing):
    out=fixture_experiment(tmp_path)
    target=out/existing
    if existing=='plots/demo':target.mkdir()
    else:target.write_text('original record')
    with pytest.raises(FileExistsError):demo_assets.generate_demo_assets(out,grid=(1,3))
    if existing!='provenance/demo_asset_checks.json':
        assert not (out/'provenance/demo_asset_checks.json').exists()
    else:assert target.read_text()=='original record'


def test_initial_tp_check_neutral_caption_when_logged_temperatures_differ(tmp_path):
    out=fixture_experiment(tmp_path,unequal=True)
    result=demo_assets.inspect_initial_tp(out/'runs/thermal_predictive_seed1/decisions.jsonl')
    assert result['distinct_six_decimal_values_per_row']==[2,2,2]
    assert result['all_rows_thermally_identical'] is False
    assert demo_assets.early_caption(result)!=demo_assets.TIE_CAPTION
    assert 'not a thermal decision' not in demo_assets.early_caption(result)


def test_e11_labels_and_strict_window_boundary():
    assert demo_assets is not None, 'presentation module is not implemented'
    assert 'synthetic' in demo_assets.experiment_label('E11_g4_synthetic')
    assert 'correlated' not in demo_assets.experiment_label('E11_g4_synthetic')
    assert 'before evaluation window' in demo_assets.window_label(3600)
    assert 'evaluation window' in demo_assets.window_label(3610)
    assert 'before' not in demo_assets.window_label(3610)


def test_source_change_during_rendering_refuses_completion_inventory(tmp_path,monkeypatch):
    out=fixture_experiment(tmp_path)
    render=demo_assets._timeseries
    def changed(*args,**kwargs):
        render(*args,**kwargs)
        path=out/'runs/packing_seed1/decisions.jsonl'
        with path.open('a') as target:target.write('\n')
    monkeypatch.setattr(demo_assets,'_timeseries',changed)
    with pytest.raises(RuntimeError,match='source changed during rendering'):
        demo_assets.generate_demo_assets(out,grid=(1,3),stride_ticks=1)
    assert not (out/'provenance/demo_asset_inventory.json').exists()
