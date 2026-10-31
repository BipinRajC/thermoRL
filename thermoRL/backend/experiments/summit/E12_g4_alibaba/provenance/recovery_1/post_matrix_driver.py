"""Durable sequencing of the already-authorized C-prime and offline report.
No retry: any failed command exits and leaves its evidence for review.
"""
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone
import hashlib

PROJECT=Path('/home/bipin/thermoRL/thermoRL/thermorl-v2')
ROOT=PROJECT.parents[1]
OUT=PROJECT/'experiments/summit/E12_g4_alibaba'
BASE=OUT/'provenance/recovery_1'
CONFIG='thermorl2/experiments/configs/g4_alibaba.yaml'
PRE=json.loads((OUT/'provenance/recovery_launch_preflight.json').read_text())

def event(kind,**fields):
    with (BASE/'post_matrix_events.jsonl').open('a') as f:
        f.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'event':kind,**fields},sort_keys=True)+'\n')

def frozen():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PRE['launch_sha']
    for p,h in PRE['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p

def command(name,args):
    frozen();event(name+'_started',command=args)
    subprocess.run(args,cwd=PROJECT,check=True)
    event(name+'_completed')

try:
    event('waiting_for_primary_service')
    while True:
        state=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','--user','show','thermorl-e12-recovery-20261030T2050Z','-p','ActiveState','-p','SubState','-p','ExecMainStatus'],text=True).splitlines())
        if state['ActiveState']=='failed':raise RuntimeError('primary service failed; STOP')
        if state['SubState']=='exited':
            assert state['ExecMainStatus']=='0',state
            assert (OUT/'results/matrix_runtime.json').is_file()
            break
        time.sleep(10)
    command('guarded_C_prime_repeat',['/usr/bin/uv','run','python','-m','thermorl2.experiments.e12_evidence','rerun','--config',CONFIG])
    command('exact_C_prime_evidence',['/usr/bin/uv','run','python','-m','thermorl2.experiments.e12_evidence','generate','--config',CONFIG])
    command('offline_report',['/usr/bin/uv','run','python','-m','thermorl2.experiments.report','experiments/summit/E12_g4_alibaba','--evidence','experiments/summit/E12_g4_alibaba/provenance/determinism_evidence.json'])
except BaseException as exc:
    event('stopped',error=repr(exc));raise
