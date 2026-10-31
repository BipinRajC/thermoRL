from pathlib import Path
import json,statistics
ROOT=Path('/home/bipin/thermoRL');OUT=ROOT/'thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba'
def read(p):return json.loads((OUT/p).read_text())
s=read('results/summary.json');rows=s['runs'];op=read('results/operational_diagnostics.json');runtime=read('results/matrix_runtime.json');rr=read('provenance/report_runtime.json');audit=read('provenance/final_release_audit.json');attr=read('results/max_rack_attribution.json');regime=read('results/workload_regime.json')
policies=['packing','node_balance','power_balance','coolest_rack','thermal_predictive']
old=read('provenance/launch_preflight.json')['launch_sha'];new=read('provenance/recovery_launch_preflight.json')['launch_sha']
GiB=1024**3

def table(headers,data):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in data)
primary=table(['Policy','Seed 1 maxrack_mean_c','Seed 2','Seed 3'],[[p]+[f"{rows[f'{p}_seed{k}']['maxrack_mean_c']:.12f}" for k in (1,2,3)] for p in policies])
gaps=table(['Seed','PB minus TP (°C, full precision)','Packing minus TP (°C, full precision)'],[[k,repr(v['power_minus_thermal_c']),repr(v['packing_minus_thermal_c'])] for k,v in s['per_seed'].items()])
util=[]
for k,offered in enumerate([0.48576559317193224,0.4546186900899609,0.4566251349855959],1):
    r=rows[f'packing_seed{k}'];o=op[f'packing_seed{k}']
    for p in policies:
        other=rows[f'{p}_seed{k}']
        for key in ['realised_node_utilisation_mean','jobs_started','jobs_censored','wait_mean_s','wait_p95_s']:assert other[key]==r[key],(p,k,key)
    util.append([k,repr(offered),repr(r['realised_node_utilisation_mean']),r['jobs_started'],r['jobs_censored'],f"{r['wait_mean_s']:.9f}",f"{r['wait_p95_s']:.9f}",f"{o['wait_max_s']:.9f}",o['max_queue_jobs_episode'],f"{o['queue_positive_fraction_eval']:.9f}"])
utiltab=table(['Seed','Offered window utilisation','Realised ledger utilisation','Started','Censored','Wait mean s','Wait p95 s','Wait max s','Peak queued jobs (episode)','Queued fraction (evaluation ticks)'],util)
s1=table(['Policy','T std mean °C','Hottest 26 mean °C','Rack kW std mean','PB/TP disagreement','Self reproduction','Latency mean µs','Latency p95 µs'],[[p]+[f"{statistics.mean(rows[f'{p}_seed{k}'][field] for k in (1,2,3)):.9f}" for field in ['rack_t_std_mean_c','top_decile_mean_c','rack_kw_std_mean']]+[f"{statistics.mean(s['diagnostics'][f'{p}_seed{k}'][field] for k in (1,2,3)):.9f}" for field in ['power_vs_thermal_disagreement_rate','self_reproduction_rate']]+[f"{statistics.mean(rows[f'{p}_seed{k}'][field] for k in (1,2,3)):.3f}" for field in ['decision_latency_mean_us','decision_latency_p95_us']] for p in policies])
attribution=[]
for k in (1,2,3):
    for p in policies:
        a=attr[f'{p}_seed{k}'];rack,share=max(a['rack_shares'].items(),key=lambda x:x[1]);counts=[len(t['resident_job_ids']) for t in a['ticks']]
        attribution.append([p,k,rack,f'{share:.9f}',min(counts),max(counts)])
atab=table(['Policy','Seed','Most frequent endpoint max rack','Share of evaluation endpoints','Resident jobs min','Resident jobs max'],attribution)
proc=table(['Policy','Seed','Selected attempt','Launch generation','Process wall s','EpisodeRunner total s','Peak RSS GiB'],[[r['policy'],r['seed'],r['selected_attempt'],'original' if r['run_dir'].endswith(('packing_seed1','node_balance_seed1','power_balance_seed1','coolest_rack_seed1')) else 'recovery',f"{r['process_wall_s']:.9f}",f"{rows[f'{r['policy']}_seed{r['seed']}']['total_s']:.9f}",f"{op[f'{r['policy']}_seed{r['seed']}']['process_peak_rss_bytes']/GiB:.6f}"] for r in runtime['processes']])
first=read('results/first_wave.json');resumed=list((OUT/'provenance').glob('first_wave_resume_*.json'));assert len(resumed)==1
first_resume=json.loads(resumed[0].read_text())
repeat_events=[json.loads(x) for x in (OUT/'provenance/rerun_1/journal.jsonl').read_text().splitlines()];repeat=repeat_events[-1];assert repeat['event']=='rerun_completed'
repeat_m=read('provenance/rerun_1/manifest.json')
memories=[r['process_peak_rss_bytes'] for r in op.values()]
S2='published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies.'
limits=f'''E12 tests only small (1–2-node), low-density, bursty Alibaba-derived jobs on the homogeneous Summit FMU. Nominal construction rho is 0.6; finite-window offered and realised utilisation are separate quantities above. Approximately 23 minutes dense plus 80 minutes near-silent occur per 1.74-hour cycle. Seed 3 is seed 2 shifted by 33.03657272057935 s after 162 leading pods: approximately two independent workload conditions, not three independent replications or a determinism test. A negative result does not confirm E11 for high-power regimes; a positive applies only to this tested regime.

A2: timestamps are assumed seconds; deletion minus creation is interpreted as runtime even for Running/Failed pods. Runtime clips remain 2033 floors and 266 caps among 6203 eligible pods. A3: arrival-only compression 2063.712860793521×, artificial cyclic wrap, empty start and correlated rotations change arrival/runtime relationships. A4: static CPU/GPU mapping assumes 20 cores/socket; about 99.3% of jobs use one node and the maximum is two. Actual loss-inclusive mean above-idle rack inputs are about {op['packing_seed1']['mean_loss_inclusive_above_idle_kw_per_rack_eval']:.6f}/{op['packing_seed2']['mean_loss_inclusive_above_idle_kw_per_rack_eval']:.6f}/{op['packing_seed3']['mean_loss_inclusive_above_idle_kw_per_rack_eval']:.6f} kW; the pre-run mapping estimates 2.8720/2.6763/2.6862 kW were loss-exclusive offered statistics with a different definition.

M2: E11's large-job max-rack domination is not assumed here. E12 endpoint identities and resident jobs are derived separately below; coexistence does not establish causation. No individual E12 job fills a rack. M3: non-local placement dependence was observed in earlier work, but its physical mechanism remains unresolved.

S2, verbatim: {S2}

Warm-up is capped at 7200 s and is evolving, not settled. G1 remains a frozen heuristic, not a validated predictor. Between-tick committed job increments retain the documented roughly 4% loss understatement; actual FMU inputs are loss-inclusive RAPS rack powers. No correction or refit was made. Forty-five °C and G1 t_hot are references, not validated safety limits. Temperatures are modelled coolant, not hardware measurements. No PUE, plant-total energy, carbon, lifetime, heterogeneous-zone, causal-mechanism, RL or surrogate claim follows.

C3 is unchanged: **no material value on the homogeneous twin**, value_beyond_power=false; packing≈TP on the primary metric. E11 PB−TP gaps remain 0.3424946761284602, −0.14719002809689385, −0.07086450347454587 °C. S1 differences remain metric-specific. E11 reproducibility remains Option A: E10 packing seed1 2h fresh-process evidence plus exact E11 seed1 packing/PB two-hour prefix checks; no independent six-hour E11 run and no E11 temperature-reading policy repeat. D7 remains deferred and no E11 rerun was performed.'''
account=f'''**FACT — launches and attempts.** Original launch `{old}`; recovery launch `{new}`. Four completed seed-1 non-TP runs retain the original SHA and unmodified manifests. The other eleven selected primaries and the one repeat use the recovery SHA. The only production-source delta is `run_matrix.py` and `e12_evidence.py` orchestration/accounting; all numerical decision, workload, power, thermal, metric, input, FMU and RAPS paths are unchanged. Full source-map comparison, including the runner's additional RAPS entries, is recorded in [source identity verification](provenance/recovery_1/source_identity_verification.json).

Cumulative accounting is **19 attempts = 15 selected successful primaries + 3 preserved interrupted primary attempts + 1 successful planned repeat**. The primary journal has 18 starts/15 completions; the repeat has its own journal. Reuse4 + restart3 + first-attempt8 produced the selected15; no additional retry occurred. The interrupted TPseed1, packingseed2 and node_balanceseed2 directories were moved exactly once; their original console logs remain in place. [Historical inventory](provenance/interruption_inventory.json), [relocation inventory](provenance/recovery_relocation_inventory.json), [primary file inventory](results/run_files.json), [repeat inventory](provenance/rerun_1/run_files.json), and [portable manifests](provenance/manifests/) make preservation traceable. Raw directories exceed25 MB and remain local/ignored.

**UNRESOLVED — interruption origin.** The original interactive controller exited143/SIGTERM around45 minutes after first launch; exact origin is unknown. An interactive lifetime limit is an INFERENCE, not a proven cause. No FMU failure file, traceback or scientific stop was observed. Bipin's actual instruction was "dont stop, resume wherever it stopped". The 19-attempt accounting and restart scope are the agent's bounded operational interpretation recorded in C4-execution-recovery, not a separately supplied count or Opus approval of this source diff.

Durable user units `thermorl-e12-recovery-20261030T2050Z` and `thermorl-e12-postmatrix-20261030T2123Z` use RuntimeMaxSec=infinity, Restart=no and RemainAfterExit=yes. The second waited for successful primary exit, used the guarded repeat CLI, generated evidence, then ran the offline report. No source change or Git commit occurred from recovery launch through successful C′ evidence generation.

Original first-wave process walls: {', '.join(f"{r['process_wall_s']:.9f}" for r in first)} s. Recovery first-wave process walls: {', '.join(f"{r['process_wall_s']:.9f}" for r in first_resume)} s. These are individual process durations, not a sum or matrix duration. Recovery controller wall: **{runtime['this_controller_wall_s']:.9f} s**, 11 completions. Original-start to final-primary-completion span: **{runtime['matrix_wall_s']:.6f} s, including interruption/recovery downtime**. Primary systemd service ran 20:49:35–22:14:00 UTC; its startup/skip validation is outside the execute_jobs controller timer. The planned repeat took **{repeat['process_wall_s']:.9f} s** by guarded repeat subprocess-plus-validation timing and {repeat_m['total_s']:.9f} s by EpisodeRunner.

Selected-primary process peak RSS range: {min(memories)/GiB:.6f}–{max(memories)/GiB:.6f} GiB; interrupted-process RSS is unknown. Recovery controller own lifetime peak: {runtime['parent_memory']['peak_rss_bytes']/GiB:.6f} GiB. Primary service cgroup high-water (controller plus concurrent workers): {7435931648/GiB:.6f} GiB. Repeat simulation own peak: {repeat_m['process_memory']['peak_rss_bytes']/GiB:.6f} GiB; its validating guard own peak: {repeat['process_memory']['peak_rss_bytes']/GiB:.6f} GiB. Offline report wall: **{rr['main_wall_s']:.6f} s** after imports, with own lifetime peak **{rr['process_memory']['peak_rss_bytes']/GiB:.6f} GiB**, at most one five-policy seed loaded. Service memory and process RSS have different scopes.

Raw storage: selected primaries **{audit['primary_raw_bytes']} bytes**, interrupted archives **{audit['interrupted_raw_bytes']} bytes**, repeat **{audit['repeat_raw_bytes']} bytes**; all raw files are inventoried. Report artifacts/logs have a separate final inventory. All15 primary episodes and the repeat recorded zero coolant samples above70°C and no negative episode pump samples; threshold counts are descriptive, not a new stop rule.'''
commands='''```bash
# Original interactive primary launch (interrupted):
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3
# Recovery under the recorded durable systemd unit:
uv run python -m thermorl2.experiments.run_matrix --config thermorl2/experiments/configs/g4_alibaba.yaml --workers 3 --retry-failed
# Guarded follow-up, alone after successful primary completion:
uv run python -m thermorl2.experiments.e12_evidence rerun --config thermorl2/experiments/configs/g4_alibaba.yaml
uv run python -m thermorl2.experiments.e12_evidence generate --config thermorl2/experiments/configs/g4_alibaba.yaml
uv run python -m thermorl2.experiments.report experiments/summit/E12_g4_alibaba --evidence experiments/summit/E12_g4_alibaba/provenance/determinism_evidence.json
# Allowed tests, before source freeze:
uv run pytest tests/unit tests/integration -q
# Supplemental ledger-only diagnostics and final audit were run from /tmp;
# byte-identical scripts are archived under provenance/recovery_1/.
uv run python /tmp/e12_extra.py
uv run python /tmp/e12_final_audit.py
```

Exact service invocations/settings and sequencing are in `provenance/recovery_1/service_launch.json`, `post_matrix_service_launch.json`, `post_matrix_driver.py` and their journals. Preservation and freeze scripts are archived there too. Dataset command: `sha256sum -c checksums.txt` from datasets/alibaba_gpu_2023, 26/26 passed. Fresh non-FMU tier: **161 unit +28 integration =189 passed in30.93s**. No new full FMU pytest tier was run.'''
proof='''**FACT — C′ direct verification covers TP seed1 only.** Full7200s warm-up,2160 steps and21600s elapsed were verified in both fresh processes. Config, workload, sidecar, FMU, source maps, Git SHA and environment matched exactly. Canonical decisions were byte-identical and complete interval values were equal with check_exact=True. Interval-file, job-event and thermal-publication bytes also matched (information only). Timing values were excluded from deterministic comparison, while row joins and hashes remained valid. The SHA-sealed evidence marks only TPseed1 verified_E12; the other14 are inherited_not_remeasured under "E10 synthetic packing seed1 2h only; weak cross-workload evidence". The entire matrix was not independently repeated. No A′ fallback or equality/tolerance change occurred.

All three seed gates passed: identical job starts, total IT power within1e-6kW, exact/free/distinct allocation and lifecycle replay, per-rack sum reconciliation, independent2160-step/21600s clock, complete provenance/ledger joins, and the accepted scoped C′ evidence. Maximum cross-policy IT-power difference is 1.8189894035458565e-12kW in each seed. See [invariants](results/invariants.json), [comparison](provenance/full_rerun_comparison.json) and [sealed evidence](provenance/determinism_evidence.json).'''
result=f'''**DERIVED — frozen G4 outcome: {s['decision']}; value_beyond_power={str(s['value_beyond_power']).lower()}.** Primary metric is maxrack_mean_c over strict3600<t_s<=21600. PB−TP must be≥0.5°C in every seed at full precision.

{primary}\n{gaps}
[All metrics, all15 runs](results/metrics.csv) · [full five-policy metric table](results/metrics.md) · [machine-readable decision](results/decision.json).

### Utilisation, waits and bursts

Nominal construction rho is **0.6**. Offered finite-window utilisation is a frozen input property; realised utilisation is derived from the RAPS ledger. These are not interchangeable. Values below are policy-identical within each seed; wait=integer start minus continuous submit, and unstarted jobs would be censored separately.

{utiltab}

All offered jobs started. The pre-run continuous overload fractions remain approximately0.0297309/0.0229211/0.0233363. The table's queue fractions use10s RAPS input ticks in the evaluation window, so they need not equal continuous offered overload. Peak queues and maximum waits cover the episode; all other window quantities retain their explicit scope. Finite queues occurred during the accepted bursts. [Operational diagnostics](results/operational_diagnostics.json) include full-capacity fractions, IT-power ranges and waits>1s.

### S1, disagreement and latency (descriptive only)

These are arithmetic means across the three correlated rotations, not independent-replication estimates or alternative success criteria. Hottest decile means26 racks per tick. Disagreement applies both scorers to the same six-decimal logged context; self-reproduction separately compares reconstructed and live choices. Latency uses only the measured joined timing ledger; canonical null is not zero. The last column averages each run's p95, not a pooled p95.

{s1}

### E12's own endpoint attribution

{atab}

Resident counts refer to the endpoint-max rack at the driving RAPS tick, with completions before starts. Full identities, resident job IDs and per-tick shares are in [max-rack attribution](results/max_rack_attribution.json). These observations do not identify a physical mechanism and do not import E11's large-job explanation.
'''
readme=OUT/'README.md';text=readme.read_text()
def replace_section(text,name,body):
    start=text.index('## '+name+'\n')+len('## '+name+'\n');end=text.find('\n## ',start)
    assert end>=0,name
    return text[:start]+body.strip()+'\n'+text[end:]
text=text.replace('**System:** summit  **Status:** preregistered; inputs/protocol prepared for review, execution not authorized.','**System:** summit  **Status:** complete; C4 results ready for Bipin/Opus review (2026-10-31).')
text=replace_section(text,'Results',result)
text=replace_section(text,'Plots','''All figures are **Alibaba-derived workload, Summit FMU, nominal, seed1**. Heatmaps share one temperature scale; animations share a scale within each comparison. They are descriptive and do not replace the frozen G4 rule.

![Alibaba-derived Summit seed1 coolant heatmaps](plots/heatmaps_seed1.png)
![Alibaba-derived Summit seed1 maximum and spread](plots/timeseries_seed1.png)

[Alibaba-derived packing vs TP animation](plots/anim_packing_vs_thermal_predictive_seed1.gif) · [Alibaba-derived PB vs TP animation](plots/anim_power_balance_vs_thermal_predictive_seed1.gif).''')
text=replace_section(text,'Observations (FACT)','All15 selected primary runs and the one planned repeat completed; three interrupted primary attempts remain preserved. All per-seed invariants passed, and exact C′ passed for TPseed1 only. Queueing was observed with zero final censoring. See Results and the dated completion addendum for measured values.')
text=replace_section(text,'Interpretation (INFERENCE)',f'The frozen outcome is "{s["decision"]}" in the accepted small-job, low-density, periodic-burst regime only. No result is generalized to high-power workloads, independent replications, safety or causal thermal mechanisms. S1 and disagreement remain descriptive.')
text=replace_section(text,'Conclusion and decision',f'**C4 reached: {s["decision"]}; value_beyond_power={str(s["value_beyond_power"]).lower()}.** Exact C′ verifies TPseed1 only. Stop for Bipin/Opus review before any Task15–17 work.')
text+='\n## Task14 completion and operational recovery (2026-10-31)\n\nEarlier preparation/frozen sections retain historical future-tense wording; this dated result supersedes their execution-status statements without changing any preregistered text or hashes.\n\n'+proof+'\n\n'+account+'\n\n'+proc+'\n\n### Executed commands and checks\n\n'+commands+'\n\n### Final scope and limitations\n\n'+limits+'\n'
readme.write_text(text)
checkpoint=f'''# C4 — E12 G4 on the Alibaba-derived workload

**Date:** 2026-10-31 IST. **Branch:** feat/parasparam-demo. **Status:** Task14 complete; STOP for Bipin/Opus review.

**Frozen outcome: {s['decision']}; value_beyond_power={str(s['value_beyond_power']).lower()}.**

Original launch SHA `{old}`; recovery launch SHA `{new}`. Recovery interpretation was committed at `f7cde7b`; tested engineering/preservation at `e0e1522`. Result/checkpoint commit is the commit containing this file. [E12 README](../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/README.md) contains all metrics, diagnostics, attribution, exact commands and operational evidence.

## Frozen G4 result

{primary}\n{gaps}
Threshold is PB−TP≥0.5°C in every seed on maxrack_mean_c over strict3600<t_s<=21600. Full precision, not the displayed table rounding, decides. S1 does not replace the rule.

## Validation and directly measured reproducibility

{proof}

## Offered versus realised utilisation and queueing

{utiltab}
Nominal construction rho is0.6; offered window and realised ledger utilisation are distinct. Starts, waits and censoring are policy-identical by construction, with exact starts checked. Actual peak queues694/564/577 jobs and max waits≈290.10/235.55/237.43s occurred in the accepted periodic burst regime. Zero censoring does not mean zero queueing. E12's own endpoint max-rack/job attribution, S1 metrics, rounded-context disagreement/self-reproduction and joined timing-ledger latency are tabulated in the README and full results; none substitutes for G4.

## Recovery, attempts, runtime, storage and source generations

{account}

## Exact commands and tests

{commands}

## Scope and interpretation limits

{limits}

## Final review boundary

Review the frozen G4 result and full five-policy metrics; per-seed invariant and C′ seal/reference evidence; TPseed1-only direct scope; correlated seeds and low-density/bursty regime; observed queues, waits and own attribution; interruption preservation, generic-instruction recovery interpretation, mixed launch SHA proof and complete19-attempt accounting. Raw files remain local/ignored and are inventoried; obtain them separately for full-data review. No E11 rerun, extra research experiment, full FMU pytest tier, RAPS patch, RL, surrogate or Tasks15–17 work was done.

**STOP at C4.** Push this same branch and await Bipin/Opus before any next task.
'''
# README-relative links in shared prose become experiment-root links in checkpoint.
import re
prefix='../../thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba/'
checkpoint=re.sub(r'\]\(((?:results|provenance)/[^)]+)\)',lambda m:']('+prefix+m.group(1)+')',checkpoint)
(ROOT/'docs/checkpoints/C4-g4-alibaba.md').write_text(checkpoint)
index=ROOT/'thermoRL/thermorl-v2/experiments/INDEX.md';lines=index.read_text().splitlines()
for i,l in enumerate(lines):
    if l.startswith('| E12 |'):lines[i]=f"| E12 | summit | Does frozen thermal_predictive add value on Alibaba-derived input? | complete; C4 review | {s['decision']} | PB−TP: "+', '.join(f"{s['per_seed'][str(k)]['power_minus_thermal_c']:+.6f}°C" for k in (1,2,3))+"; C′ TPseed1 only | [README](summit/E12_g4_alibaba/README.md) | 2026-10-31 |"
index.write_text('\n'.join(lines)+'\n')
plan=ROOT/'docs/superpowers/plans/2026-10-27-parasparam-demo.md';t=plan.read_text();start=t.index('### Task 14:');end=t.index('\n---',start);t=t[:start]+t[start:end].replace('- [ ] **Step','- [x] **Step')+t[end:];plan.write_text(t)
print(s['decision']);print(s['per_seed']);print(utiltab)
