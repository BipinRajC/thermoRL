from pathlib import Path
import json,hashlib,re,subprocess
from datetime import datetime,timezone
from thermorl2.experiments.provenance import sha256_file
from thermorl2.experiments.run_matrix import reviewed_recovery,archive_failure,read_events
out=Path('experiments/summit/E12_g4_alibaba');prov=out/'provenance'
pre=json.loads((prov/'preregistration.json').read_text());old=json.loads((prov/'launch_preflight.json').read_text())
for p,h in pre['input_sha256'].items():assert sha256_file(p)==h,p
assert sha256_file(out/'config.yaml')==pre['experiment_config_sha256']
text=(out/'README.md').read_text()
for title,h in pre['frozen_readme_sections_sha256'].items():
    section=text.split('## '+title+'\n',1)[1].split('\n## ',1)[0]
    assert hashlib.sha256(section.encode()).hexdigest()==h,title
root=Path('../..').resolve()
changed={p:sha256_file(root/p) for p,h in old['source_sha256'].items() if sha256_file(root/p)!=h}
assert set(changed)=={'thermoRL/thermorl-v2/thermorl2/experiments/run_matrix.py','thermoRL/thermorl-v2/thermorl2/experiments/e12_evidence.py'},changed
inventory=json.loads((prov/'interruption_inventory.json').read_text())
for p,item in inventory.items():
    assert (out/p).stat().st_size==item['bytes'] and sha256_file(out/p)==item['sha256'],p
approval=reviewed_recovery(out)
assert sum(e['event']=='started' for e in read_events(out))==7
assert not any(e['event']=='failure_archived' for e in read_events(out))
relocations=[]
for name in approval['interrupted_configurations']:
    source=out/'runs'/name
    assert source.is_dir() and not (source/'manifest.json').exists()
    archived=archive_failure(out,source,1,None,'external_interruption','Controller SIGTERM143; child final exit unknown; recorded operational resume')
    for p,item in inventory.items():
        if p.startswith('runs/'+name+'/'):
            target=archived/Path(p).relative_to('runs/'+name)
            assert sha256_file(target)==item['sha256']
            relocations.append({'original_path':p,'archive_path':str(target.relative_to(out)),**item})
    if not any(p.is_file() for p in archived.rglob('*')):relocations.append({'original_path':str(source.relative_to(out)),'archive_path':str(archived.relative_to(out)),'bytes':0,'empty_directory':True})
record={'utc':datetime.now(timezone.utc).isoformat(),'historical_inventory_sha256':sha256_file(prov/'interruption_inventory.json'),'relocations':relocations,'original_logs_preserved_in_place':True,'numerical_source_unchanged':True,'changed_source_sha256':changed,'pinned_inputs_verified':True,'frozen_readme_sections_verified':True}
with (prov/'recovery_relocation_inventory.json').open('x') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,indent=2))
