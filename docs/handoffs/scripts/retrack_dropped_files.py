#!/usr/bin/env python3
"""Re-track the 81 files dropped from git by the c09f735 directory rename.

Run from the repository root on the Arch machine, where the untracked copies
exist locally. Dry-run by default; pass --apply to stage. It never commits.

Safety rules (from docs/handoffs/2026-10-31-sonnet-5-5-demo-integration-brief.md, A2):
- every file must exist and match its recorded historical SHA-256 exactly;
- nothing under E11/E12 raw runs/ is ever staged (only E10's small committed runs);
- every file stays below 25 MB;
- paths are force-added one at a time (no directories, no `git add -A`);
- the index must hold no other staged change before and after.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE = Path('docs/handoffs/2026-10-31-post-c6-review-evidence.json')
REPORT = Path('docs/results/post_rename_retrack_check.json')
FORBIDDEN_RUNS = ('/E11_g4_synthetic/runs/', '/E12_g4_alibaba/runs/')
ALLOWED_RUNS = '/E10_c2_vertical_slice/runs/'
LIMIT = 25_000_000


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--apply', action='store_true', help='stage the verified paths (default: dry run)')
    args = parser.parse_args()
    if not (Path('.git').exists() and EVIDENCE.is_file()):
        sys.exit('run from the repository root containing the evidence JSON')
    entries = json.loads(EVIDENCE.read_text())['dropped_tracked_files']
    assert len(entries) == 81, f'expected 81 entries, found {len(entries)}'
    if git('diff', '--cached', '--quiet').returncode != 0:
        sys.exit('refusing: the index already has staged changes')

    problems, checked = [], []
    for entry in entries:
        path = entry['current_local_path']
        record = {'path': path, 'old_path': entry['old_path']}
        if any(part in path for part in FORBIDDEN_RUNS) or ('/runs/' in path and ALLOWED_RUNS not in path):
            problems.append({**record, 'problem': 'raw runs/ path is never staged'}); continue
        if not Path(path).is_file():
            problems.append({**record, 'problem': 'missing locally'}); continue
        size = Path(path).stat().st_size
        actual = sha256(path)
        if not (actual == entry['historical_sha256'] == entry['current_sha256']):
            problems.append({**record, 'problem': 'sha256 mismatch', 'actual': actual}); continue
        if size >= LIMIT:
            problems.append({**record, 'problem': f'{size} bytes exceeds 25 MB'}); continue
        if git('ls-files', '--error-unmatch', '--', path).returncode == 0:
            record['already_tracked'] = True
        checked.append({**record, 'bytes': size, 'sha256': actual})

    print(json.dumps({'verified': len(checked), 'problems': problems}, indent=2))
    if problems:
        sys.exit(f'{len(problems)} problem(s); nothing staged')
    if not args.apply:
        print('dry run OK: all 81 verified; re-run with --apply to stage')
        return

    for item in checked:
        if item.get('already_tracked'):
            continue
        result = git('add', '-f', '--', item['path'])
        if result.returncode != 0:
            sys.exit(f"git add failed for {item['path']}: {result.stderr}")
    staged = set(git('diff', '--cached', '--name-only').stdout.split())
    expected = {item['path'] for item in checked if not item.get('already_tracked')}
    if staged != expected:
        sys.exit(f'staged set differs from the verified list: extra={sorted(staged - expected)} '
                 f'missing={sorted(expected - staged)}; inspect with `git diff --cached --stat`')
    head = git('rev-parse', 'HEAD').stdout.strip()
    with REPORT.open('x') as out:
        json.dump({'utc': datetime.now(timezone.utc).isoformat(), 'head_before_commit': head,
                   'evidence': str(EVIDENCE), 'staged': len(staged), 'files': checked},
                  out, indent=2, sort_keys=True)
        out.write('\n')
    subprocess.run(['git', 'add', '--', str(REPORT)], check=True)
    print(f'staged {len(staged)} re-tracked files + {REPORT}; review `git diff --cached --stat`, then commit')


if __name__ == '__main__':
    main()
