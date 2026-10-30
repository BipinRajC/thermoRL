import hashlib
import json

import pytest

from thermorl2.experiments import run_matrix

POLICIES=['packing','node_balance','power_balance','coolest_rack','thermal_predictive']
INTERRUPTED=['thermal_predictive_seed1','packing_seed2','node_balance_seed2']


def journal(tmp_path,extras=False,approve=False,bad_kind=False):
    prov=tmp_path/'provenance';prov.mkdir()
    review=tmp_path/'review.md';review.write_text('User instruction: resume wherever it stopped; preserve all attempted runs.')
    snapshot=prov/'execution_interruption.json'
    snapshot.write_text(json.dumps({'controller_tool_exit_code':143,'partial_run_names':INTERRUPTED}))
    if approve:
        approval={'approved_by':'Bipin','scope':'E12_SIGTERM_resume','review_ref':str(review),
            'review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),
            'interruption_record_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            'interrupted_configurations':INTERRUPTED,'authorized_extra_attempts':3}
        (prov/'recovery_approval.json').write_text(json.dumps(approval))
    rows=[]
    for seed in (1,2,3):
        for policy in POLICIES:
            name=f'{policy}_seed{seed}';path=str(tmp_path/'runs'/name)
            rows.append(dict(event='started',policy=policy,seed=seed,run_dir=path,attempt=1))
            if extras and name in INTERRUPTED:
                rows.append(dict(event='failure_archived',run_dir=path,attempt=1,
                    failure_kind='fmu_error' if bad_kind else 'external_interruption',archive='preserved'))
                rows.append(dict(event='started',policy=policy,seed=seed,run_dir=path,attempt=2))
            rows.append(dict(event='completed',policy=policy,seed=seed,run_dir=path,process_wall_s=1.,index=len(rows)))
    for i,row in enumerate(rows):row['utc']=f'2026-10-31T00:00:{i:02d}+00:00'
    (prov/'matrix_events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))


def test_normal_matrix_keeps_exact15_accounting(tmp_path):
    journal(tmp_path)
    result=run_matrix.primary_attempt_summary(tmp_path,POLICIES,[1,2,3])
    assert result['completed']==15 and result['attempts_started']==15
    assert result['interrupted_attempts']==0


def test_reviewed_recovery_preserves18_attempts_15_outcomes(tmp_path):
    journal(tmp_path,extras=True,approve=True)
    result=run_matrix.primary_attempt_summary(tmp_path,POLICIES,[1,2,3])
    assert result['completed']==15 and result['attempts_started']==18
    assert result['interrupted_attempts']==3 and len(result['processes'])==15


@pytest.mark.parametrize('approval,bad_kind',[(False,False),(True,True)])
def test_unreviewed_or_scientific_retries_rejected(tmp_path,approval,bad_kind):
    journal(tmp_path,extras=True,approve=approval,bad_kind=bad_kind)
    with pytest.raises((ValueError,AssertionError)):
        run_matrix.primary_attempt_summary(tmp_path,POLICIES,[1,2,3])
