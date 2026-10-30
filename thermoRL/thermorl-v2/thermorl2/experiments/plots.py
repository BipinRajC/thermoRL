"""Offline figures from frozen ledgers; axes use the recorded episode horizon."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import pandas as pd


def episode_hours(run):
    return float(run.manifest['config']['horizon_h'])


def _target(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def _matrix(run, key='t_c'):
    return run.intervals.pivot(index='rack',columns='t_s',values=key).sort_index().sort_index(axis=1)


def _onset(axis,run):
    if run.manifest['config'].get('scenario',{}).get('name','nominal') != 'nominal':
        axis.axvline(2,color='cyan',linestyle='--',label='Scenario onset')


def heatmaps(runs,out_png,vmin,vmax):
    path = _target(out_png)
    fig,axes = plt.subplots(1,len(runs),figsize=(4*len(runs),5),squeeze=False,
                            sharey=True,layout='constrained')
    for ax,run in zip(axes[0],runs):
        mat = _matrix(run)
        image = ax.imshow(mat.to_numpy(),origin='lower',aspect='auto',
                          extent=(0,episode_hours(run),-0.5,len(mat)-0.5),
                          vmin=vmin,vmax=vmax,cmap='inferno')
        ax.set(title=run.manifest.get('policy',run.name),xlabel='Episode time (h)')
        _onset(ax,run)
    axes[0,0].set_ylabel('Rack index')
    fig.colorbar(image,ax=axes[0].tolist(),label='Coolant temperature (°C)')
    fig.savefig(path,dpi=140)
    plt.close(fig)


def timeseries(runs,out_png):
    path = _target(out_png)
    fig,axes = plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
    for run in runs:
        groups = run.intervals.groupby('t_s').t_c
        maximum,minimum = groups.max(),groups.min()
        axes[0].plot(maximum.index/3600,maximum,label=run.manifest.get('policy',run.name))
        axes[1].plot(maximum.index/3600,maximum-minimum)
    axes[0].set(ylabel='Max-rack coolant (°C)')
    axes[1].set(ylabel='Max − min coolant (°C)',xlabel='Episode time (h)',
                xlim=(0,max(map(episode_hours,runs))))
    axes[0].legend(fontsize=8,ncol=3)
    for ax in axes:
        _onset(ax,runs[0])
        ax.grid(alpha=0.2)
    fig.savefig(path,dpi=140)
    plt.close(fig)


def metrics_table(rows,out_md):
    path = _target(out_md)
    frame = pd.DataFrame(rows)
    keys = [key for key in frame if key not in ('policy','seed','name') and
            pd.api.types.is_numeric_dtype(frame[key])]
    lines = ['Mean [min, max] across seeds; descriptive metrics do not alter G4.','',
             '| Policy | '+' | '.join(keys)+' |',
             '|---|'+'---:|'*len(keys)]
    for policy,group in frame.groupby('policy',sort=False):
        values = []
        for key in keys:
            x = group[key].dropna()
            values.append(f'{x.mean():.6f} [{x.min():.6f}, {x.max():.6f}]' if len(x) else 'missing')
        lines.append('| '+policy+' | '+' | '.join(values)+' |')
    path.write_text('\n'.join(lines)+'\n')


def animate_grid(runs,out_path,grid,stride_ticks=3):
    path = _target(out_path)
    matrices = [_matrix(run).T for run in runs]
    powers = [_matrix(run,'kw').T for run in runs]
    times = matrices[0].index.to_numpy()
    assert all(np.array_equal(mat.index,times) for mat in matrices)
    rows,cols = grid
    n = matrices[0].shape[1]
    assert rows*cols >= n
    low,high = min(float(m.min().min()) for m in matrices),max(float(m.max().max()) for m in matrices)
    fig,axes = plt.subplots(1,len(runs),figsize=(4*len(runs),4),squeeze=False,layout='constrained')
    images,pulses,texts = [],[],[]
    for ax,run in zip(axes[0],runs):
        image = ax.imshow(np.full(grid,np.nan),vmin=low,vmax=high,cmap='inferno',origin='lower')
        images.append(image)
        pulses.append(ax.scatter([],[],s=60,facecolors='none',edgecolors='cyan',linewidths=1.4))
        ax.set(title=run.manifest.get('policy',run.name),xticks=[],yticks=[])
        texts.append([ax.text(r%cols,r//cols,'',ha='center',va='center',fontsize=6,color='white')
                      for r in range(n)] if n <= 60 else [])
    fig.colorbar(images[0],ax=axes[0].tolist(),label='Coolant °C')
    title = fig.suptitle('')
    def update(index):
        t = float(times[index])
        lower = float(times[max(0,index-stride_ticks)]) if index else 0.0
        for j,run in enumerate(runs):
            data = np.full(rows*cols,np.nan)
            data[:n] = matrices[j].iloc[index].to_numpy()
            images[j].set_data(data.reshape(grid))
            racks = sorted({r for d in run.decisions if lower < d['t_s'] <= t for r in d['racks']})
            pulses[j].set_offsets(np.asarray([(r%cols,r//cols) for r in racks]).reshape(-1,2))
            for r,label in enumerate(texts[j]):
                label.set_text(f'{powers[j].iloc[index,r]:.1f}')
        title.set_text(f'Episode {t/3600:.2f} h — schematic layout; cyan: placements since prior frame')
        return images+pulses+[title]
    animation = FuncAnimation(fig,update,frames=range(0,len(times),stride_ticks),cache_frame_data=False)
    animation.save(path,writer=PillowWriter(fps=12),dpi=70)
    plt.close(fig)


def g2_figure(experiment_dir,out_png):
    path = _target(out_png)
    frame = pd.read_parquet(Path(experiment_dir)/'results/series.parquet')
    fig,ax = plt.subplots(figsize=(8,4),layout='constrained')
    for branch,group in frame.groupby('branch'):
        series = group.groupby('t_s').t_c.max()
        ax.plot(series.index/3600,series,label=branch)
    ax.set(xlabel='Branch elapsed time (h)',ylabel='Max-rack coolant (°C)',title='G2 fixed-power branches')
    ax.legend()
    fig.savefig(path,dpi=140)
    plt.close(fig)
