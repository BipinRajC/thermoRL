from pathlib import Path
import json,subprocess
from datetime import datetime,timezone
from thermorl2.experiments.provenance import sha256_file,environment
from thermorl2.raps_adapter.systems import get_system,repo_root
out=Path('experiments/summit/E12_g4_alibaba');prov=out/'provenance';root=repo_root()
old=json.loads((prov/'launch_preflight.json').read_text())
source={p:sha256_file(root/p) for p in old['source_sha256']}
changed=[p for p,h in source.items() if h!=old['source_sha256'][p]]
assert len(changed)==2
assert not subprocess.check_output(['git','diff','HEAD','--','thermoRL/thermorl-v2/thermorl2','sim-raps','uv.lock'],cwd=root)
assert environment()==old['environment']
spec=get_system('summit');assert sha256_file(root/spec.fmu_path)==old['fmu_sha256']
record={'utc':datetime.now(timezone.utc).isoformat(),'launch_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'original_launch_sha':old['launch_sha'],'source_sha256':source,'code_diff_scope':changed,'numerical_path_unchanged':True,'environment':environment(),'fmu_sha256':old['fmu_sha256'],'dataset_checksums_passed':26,'pinned_inputs_and_frozen_sections_verified':True,'tests':{'command':'uv run pytest tests/unit tests/integration -q','passed':189,'unit':161,'integration':28,'duration_s':30.93,'full_fmu_tier_run':False},'primary_attempt_budget':18,'successful_primary_configurations':15,'preserved_interrupted_attempts':3,'remaining_primary_processes':11,'planned_fresh_process_repeat':1,'cumulative_attempt_budget':19,'source_freeze_until':'successful C-prime evidence generation','git_status_porcelain':subprocess.check_output(['git','status','--porcelain'],text=True)}
with (prov/'recovery_launch_preflight.json').open('x') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
base=prov/'recovery_1';base.mkdir(exist_ok=False)
(base/'controller_console.log').open('x').close()
print(record['launch_sha']);print(spec.fmu_path)
