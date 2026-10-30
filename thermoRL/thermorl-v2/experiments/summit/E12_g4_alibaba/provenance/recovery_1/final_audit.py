from pathlib import Path
import json,hashlib,re,subprocess
from collections import Counter
from thermorl2.experiments.provenance import sha256_file
from thermorl2.experiments.report import seed_gate,approved_e12_determinism
out=Path('experiments/summit/E12_g4_alibaba');root=Path('../..').resolve();prov=out/'provenance'
pre=json.loads((prov/'preregistration.json').read_text());launch=json.loads((prov/'recovery_launch_preflight.json').read_text())
for p,h in pre['input_sha256'].items():assert sha256_file(p)==h,p
assert sha256_file(out/'config.yaml')==pre['experiment_config_sha256']
text=(out/'README.md').read_text()
for title,h in pre['frozen_readme_sections_sha256'].items():
    section=text.split('## '+title+'\n',1)[1].split('\n## ',1)[0]
    assert hashlib.sha256(section.encode()).hexdigest()==h,title
for p,h in launch['source_sha256'].items():assert sha256_file(root/p)==h,p
old_sha=launch['original_launch_sha'];new_sha=launch['launch_sha']
originals={'packing_seed1','node_balance_seed1','power_balance_seed1','coolest_rack_seed1'}
source_reference=json.loads((out/'runs/thermal_predictive_seed1/manifest.json').read_text())['source_sha256']
for path in (out/'runs').iterdir():
    m=json.loads((path/'manifest.json').read_text())
    assert m['git']['sha']==(old_sha if path.name in originals else new_sha)
    expected=dict(source_reference)
    if path.name in originals:
        for p in expected:
            expected[p]=hashlib.sha256(subprocess.check_output(['git','show',old_sha+':'+p],cwd=root)).hexdigest()
    assert m['source_sha256']==expected,path
    assert m['environment']==launch['environment']
    assert (prov/'manifests'/f'{path.name}.json').read_bytes()==(path/'manifest.json').read_bytes()
    assert m['fmu_steps']==2160 and m['backend_elapsed_s']==21600 and m['warmup_used_s']==7200
oldinv=json.loads((prov/'interruption_inventory.json').read_text());reloc=json.loads((prov/'recovery_relocation_inventory.json').read_text())
moves={r['original_path']:r['archive_path'] for r in reloc['relocations']}
for p,entry in oldinv.items():
    target=out/moves.get(p,p)
    if p=='provenance/matrix_events.jsonl':
        assert hashlib.sha256(target.read_bytes()[:entry['bytes']]).hexdigest()==entry['sha256']
    else:assert target.stat().st_size==entry['bytes'] and sha256_file(target)==entry['sha256'],target
for inv_path,base in [(out/'results/run_files.json',out),(prov/'rerun_1/run_files.json',prov/'rerun_1')]:
    for p,r in json.loads(inv_path.read_text()).items():
        target=base/p;assert target.stat().st_size==r['bytes'] and sha256_file(target)==r['sha256'],target
proof_path=prov/'determinism_evidence.json';proof=json.loads(proof_path.read_text())
assert sha256_file(proof_path)==Path(str(proof_path)+'.sha256').read_text().strip()
assert approved_e12_determinism(proof)
for p,h in proof['references_sha256'].items():assert sha256_file(p)==h,p
checks=json.loads((out/'results/invariants.json').read_text())
assert set(checks)=={'1','2','3'} and all(seed_gate(c,s) for s,c in checks.items())
events=[json.loads(l) for l in (prov/'matrix_events.jsonl').read_text().splitlines()];counts=Counter(e['event'] for e in events)
assert counts['started']==18 and counts['completed']==15 and counts['failure_archived']==3 and counts['seed_cross_policy_invariants_passed']==3 and counts['matrix_stopped']==0
runtime=json.loads((out/'results/matrix_runtime.json').read_text());assert runtime['completed']==15 and runtime['this_controller_completed']==11 and runtime['attempts_started']==18 and runtime['interrupted_attempts']==3
summary=json.loads((out/'results/summary.json').read_text());rows=summary['runs']
for seed in (1,2,3):
    gap=rows[f'power_balance_seed{seed}']['maxrack_mean_c']-rows[f'thermal_predictive_seed{seed}']['maxrack_mean_c']
    assert gap==summary['per_seed'][str(seed)]['power_minus_thermal_c']
assert summary['value_beyond_power']==all(r['power_minus_thermal_c']>=.5 for r in summary['per_seed'].values())
raw={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha256_file(p)} for p in sorted(out.rglob('*')) if p.is_file() and ('runs' in p.relative_to(out).parts or any(x.startswith('failed_') for x in p.relative_to(out).parts))}
record={'frozen_sections_and_inputs_verified':True,'selected_launch_generations_verified':{'original':len(originals),'recovery':11},'source_and_environment_verified':True,'historical_interruption_inventory_and_journal_prefix_preserved':True,'primary_and_repeat_inventories_verified':True,'C_prime_seal_and_reference_hashes_verified':True,'all_three_seed_gates_passed':True,'event_counts':dict(counts),'primary_raw_bytes':sum(v['bytes'] for p,v in raw.items() if p.startswith('runs/')),'interrupted_raw_bytes':sum(v['bytes'] for p,v in raw.items() if p.startswith('provenance/failed_')),'repeat_raw_bytes':sum(v['bytes'] for p,v in raw.items() if p.startswith('provenance/rerun_1/runs/')),'raw_files':len(raw)}
with (prov/'final_release_audit.json').open('x') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,indent=2))
