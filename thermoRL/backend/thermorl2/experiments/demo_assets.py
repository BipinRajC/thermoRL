"""Presentation-only seed-1 copies from existing ledgers; never simulate or overwrite.

The matrix/metric functions are not invoked. Full decision contexts are released
one run at a time, retaining only the interval frame and placement pulse fields.
"""

import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

from thermorl2.core.metrics import Run, load_run
from thermorl2.experiments import plots
from thermorl2.experiments.provenance import process_memory, sha256_file

POLICIES=('packing','node_balance','power_balance','coolest_rack','thermal_predictive')
G4_CAPTION=('Descriptive. Preregistered G4 outcome: no material value beyond power '
            'balancing (threshold 0.5 °C)')
TIE_CAPTION='tie-breaking among thermally identical idle racks; not a thermal decision'
ASSET_NAMES=('heatmaps_seed1.png','timeseries_seed1.png',
             'anim_packing_vs_thermal_predictive_seed1.gif',
             'anim_power_balance_vs_thermal_predictive_seed1.gif')


def experiment_label(name):
    if name=='E11_g4_synthetic':workload='E11 — synthetic'
    elif name=='E12_g4_alibaba':workload='E12 — Alibaba-derived'
    else:raise ValueError('demo copies cover only E11_g4_synthetic and E12_g4_alibaba')
    return workload+' | Summit FMU, nominal | seed 1 of 3'+(
        ' | seeds 2/3 correlated' if name.startswith('E12') else '')


def window_label(t_s):
    return ('before evaluation window (t ≤ 1 h)' if t_s<=3600 else
            'evaluation window (1 h < t ≤ 6 h)')


def inspect_initial_tp(path, sample_rows=3):
    """Read the first few rows before rendering; compare six-decimal logging."""
    path=Path(path);rows=[]
    with path.open() as source:
        for line in source:
            if not line.strip():continue
            row=json.loads(line)
            values=np.asarray(row['t_c'],dtype=float)
            if not values.size or not np.isfinite(values).all():
                raise ValueError('initial TP t_c must be non-empty and finite')
            rows.append({'t_s':row['t_s'],
                         'distinct':len({round(float(x),6) for x in values})})
            if len(rows)==sample_rows:break
    if not rows:raise ValueError('initial TP decisions are missing')
    return {'source_path':str(path),'source_sha256':sha256_file(path),
            'sample_rows_requested':sample_rows,'sample_rows_checked':len(rows),
            'times_s':[r['t_s'] for r in rows],
            'distinct_six_decimal_values_per_row':[r['distinct'] for r in rows],
            'all_rows_thermally_identical':all(r['distinct']==1 for r in rows),
            'scope':'per-row logged t_c at six decimals only; not full-precision equality or causation'}


def early_caption(check):
    if check['all_rows_thermally_identical']:return TIE_CAPTION
    return 'logged initial rack temperatures differ; early TP placements are descriptive only'


def _json_x(path, record):
    with Path(path).open('x') as target:
        target.write(json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+'\n')


def _load_plot_run(path):
    loaded=load_run(path)
    m=loaded.manifest
    if m['system']!='summit' or m['seed']!=1 or m['config']['scenario']['name']!='nominal':
        raise ValueError('demo assets require nominal Summit seed 1')
    if float(m['config']['horizon_h'])!=6:raise ValueError('demo assets require the six-hour episode')
    # These are exactly the only decision fields used by plots.animate_grid.
    return Run(loaded.name,loaded.intervals,
               [{'t_s':d['t_s'],'racks':d['racks']} for d in loaded.decisions],m,Path(path))


def _description(label, low, high, caption):
    return (label+'\n'+f'Temperature colour-scale range: {low:.6f}–{high:.6f} °C; '
            'E11 and E12 scales differ.\n'+G4_CAPTION+'\n'
            'evaluation window starts at t = 1 h (strict t > 1 h).\n'
            'Early-frame TP scatter: '+caption)


def _decorate(fig, label, low, high, caption, colour=True):
    fig.text(.5,.975,label,ha='center',va='top',fontsize=11)
    kind='Colour-scale range' if colour else 'Companion heatmap/GIF colour-scale range'
    fig.text(.5,.925,f'{kind}: {low:.6f}–{high:.6f} °C; E11 and E12 scales differ.',
             ha='center',va='top',fontsize=9)
    fig.text(.5,.115,G4_CAPTION,ha='center',va='center',fontsize=9)
    fig.text(.5,.055,'Early-frame TP scatter: '+caption,ha='center',va='center',fontsize=8)


def _window_marker(ax, heatmap=False):
    ax.axvline(1,color='cyan' if heatmap else 'black',linestyle='--',linewidth=1)
    ax.text(1,.98,'evaluation window starts',transform=ax.get_xaxis_transform(),
            rotation=90,va='top',ha='right',fontsize=8,
            color='white' if heatmap else 'black',
            bbox={'facecolor':'black' if heatmap else 'white','alpha':.6,'edgecolor':'none'})


def _heatmaps(runs,path,label,low,high,caption):
    fig,axes=plt.subplots(1,len(runs),figsize=(20,6.5),sharey=True,squeeze=False)
    fig.subplots_adjust(left=.04,right=.92,bottom=.23,top=.8,wspace=.08)
    for ax,run in zip(axes[0],runs):
        matrix=plots._matrix(run)
        image=ax.imshow(matrix.to_numpy(),origin='lower',aspect='auto',
                        extent=(0,plots.episode_hours(run),-.5,len(matrix)-.5),
                        vmin=low,vmax=high,cmap='inferno')
        ax.set(title=run.manifest['policy'],xlabel='Episode time (h)')
        _window_marker(ax,heatmap=True)
    axes[0,0].set_ylabel('Rack index')
    cax=fig.add_axes([.94,.23,.009,.57]);fig.colorbar(image,cax=cax,label='Coolant temperature (°C)')
    _decorate(fig,label,low,high,caption)
    fig.savefig(plots._target(path),dpi=100,metadata={'Description':_description(label,low,high,caption)})
    plt.close(fig)


def _timeseries(runs,path,label,low,high,caption):
    fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True)
    fig.subplots_adjust(left=.08,right=.98,bottom=.22,top=.79,hspace=.15)
    for run in runs:
        grouped=run.intervals.groupby('t_s').t_c
        maximum,minimum=grouped.max(),grouped.min()
        axes[0].plot(maximum.index/3600,maximum,label=run.manifest['policy'])
        axes[1].plot(maximum.index/3600,maximum-minimum)
    axes[0].set_ylabel('Max-rack coolant (°C)')
    axes[1].set(ylabel='Max − min coolant (°C)',xlabel='Episode time (h)',
                xlim=(0,max(map(plots.episode_hours,runs))))
    axes[0].legend(fontsize=8,ncol=3)
    for ax in axes:_window_marker(ax);ax.grid(alpha=.2)
    _decorate(fig,label,low,high,caption,colour=False)
    fig.savefig(plots._target(path),dpi=100,metadata={'Description':_description(label,low,high,caption)})
    plt.close(fig)


class _CaptionedWriter(PillowWriter):
    def __init__(self,description,**kwargs):
        super().__init__(**kwargs);self.description=description

    def finish(self):
        self._frames[0].save(self.outfile,save_all=True,append_images=self._frames[1:],
                             duration=int(1000/self.fps),loop=0,
                             comment=self.description.encode('utf-8'))


def _animation(runs,path,grid,stride_ticks,label,low,high,caption):
    matrices=[plots._matrix(run).T for run in runs];times=matrices[0].index.to_numpy()
    if not all(np.array_equal(m.index,times) for m in matrices):raise ValueError('interval time grids differ')
    rows,cols=grid;n=matrices[0].shape[1]
    if rows*cols<n:raise ValueError('schematic grid too small')
    fig,axes=plt.subplots(1,len(runs),figsize=(12,7),squeeze=False)
    fig.subplots_adjust(left=.04,right=.91,bottom=.23,top=.75,wspace=.12)
    images=[];pulses=[]
    for ax,run in zip(axes[0],runs):
        images.append(ax.imshow(np.full(grid,np.nan),vmin=low,vmax=high,cmap='inferno',origin='lower'))
        pulses.append(ax.scatter([],[],s=60,facecolors='none',edgecolors='cyan',linewidths=1.4))
        ax.set(title=run.manifest['policy'],xticks=[],yticks=[])
    cax=fig.add_axes([.94,.23,.012,.52]);fig.colorbar(images[0],cax=cax,label='Coolant °C')
    _decorate(fig,label,low,high,caption)
    title=fig.text(.5,.845,'',ha='center',va='center',fontsize=10)
    # Pre-sort pulse events once; no rescoring and no policy execution.
    events=[sorted(run.decisions,key=lambda d:d['t_s']) for run in runs]
    def update(index):
        t=float(times[index]);lower=float(times[max(0,index-stride_ticks)]) if index else 0.
        for j in range(len(runs)):
            data=np.full(rows*cols,np.nan);data[:n]=matrices[j].iloc[index].to_numpy()
            images[j].set_data(data.reshape(grid))
            racks=sorted({r for d in events[j] if lower<d['t_s']<=t for r in d['racks']})
            pulses[j].set_offsets(np.asarray([(r%cols,r//cols) for r in racks]).reshape(-1,2))
        title.set_text(f'Episode {t/3600:.2f} h | {window_label(t)}\nSchematic layout; cyan: placements since prior frame')
        return images+pulses+[title]
    animation=FuncAnimation(fig,update,frames=range(0,len(times),stride_ticks),cache_frame_data=False)
    animation.save(plots._target(path),writer=_CaptionedWriter(_description(label,low,high,caption),fps=12),dpi=70)
    plt.close(fig)


def generate_demo_assets(experiment_dir,grid=(13,20),stride_ticks=3):
    """Write four new labelled assets and separate provenance, never old results."""
    start=perf_counter();out=Path(experiment_dir);label=experiment_label(out.name)
    if stride_ticks<1:raise ValueError('stride_ticks must be positive')
    destination=out/'plots/demo';checks=out/'provenance/demo_asset_checks.json'
    inventory=out/'provenance/demo_asset_inventory.json'
    for path in (destination,checks,inventory):
        if path.exists():raise FileExistsError(f'never overwrite demo output: {path}')
    paths=[out/'runs'/f'{p}_seed1' for p in POLICIES]
    for path in paths:
        for name in ('manifest.json','intervals.parquet','decisions.jsonl'):
            if not (path/name).is_file():raise FileNotFoundError(path/name)
    initial=inspect_initial_tp(paths[-1]/'decisions.jsonl');caption=early_caption(initial)
    source={str((p/name).relative_to(out)):sha256_file(p/name) for p in paths
            for name in ('manifest.json','intervals.parquet','decisions.jsonl')}
    _json_x(checks,{'experiment':out.name,'initial_tp':initial,'early_frame_caption':caption,
                   'read_only_check_before_rendering':True,'created_utc':datetime.now(timezone.utc).isoformat()})
    runs=[]
    for path in paths:runs.append(_load_plot_run(path));gc.collect()
    low=min(float(r.intervals.t_c.min()) for r in runs)
    high=max(float(r.intervals.t_c.max()) for r in runs)
    if not np.isfinite([low,high]).all():raise ValueError('non-finite interval coolant')
    destination.mkdir(exist_ok=False)
    _heatmaps(runs,destination/ASSET_NAMES[0],label,low,high,caption)
    _timeseries(runs,destination/ASSET_NAMES[1],label,low,high,caption)
    by_policy={run.manifest['policy']:run for run in runs}
    for base,name in zip(('packing','power_balance'),ASSET_NAMES[2:]):
        _animation([by_policy[base],by_policy['thermal_predictive']],destination/name,
                   grid,stride_ticks,label,low,high,caption)
        gc.collect()
    assets={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha256_file(p),
             'exceeds_25_MB':p.stat().st_size>25_000_000} for p in sorted(destination.iterdir())}
    for name,digest in source.items():
        if sha256_file(out/name)!=digest:raise RuntimeError(f'source changed during rendering: {name}')
    record={'experiment':out.name,'scope':'presentation-only copies from unchanged seed-1 ledgers; no metrics or simulation',
            'temperature_colour_scale_c':[low,high],'colour_scale_scope':'all five seed-1 policies within this experiment',
            'stride_ticks':stride_ticks,'assets':assets,'source_sha256':source,
            'checks_sha256':sha256_file(checks),'source_files_unchanged_after_rendering':True,'wall_s':perf_counter()-start,'process_memory':process_memory()}
    _json_x(inventory,record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_dir',type=Path)
    args=parser.parse_args()
    result=generate_demo_assets(args.experiment_dir)
    print(json.dumps({'experiment':result['experiment'],'assets':result['assets'],
                      'wall_s':result['wall_s'],'process_memory':result['process_memory']},indent=2),flush=True)


if __name__=='__main__':main()
