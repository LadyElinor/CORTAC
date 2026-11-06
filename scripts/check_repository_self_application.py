"""Replay the retained R1 task and bind it to historical Git source bytes.

No checks are executed, no freshness at current HEAD is claimed, and no external
custody or independent judgment is established. Requires the retained commits.
"""
import argparse
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'package'))
from wac_offline.repository_task_v1 import repository
from wac_offline.repository_task_v1.journal import Task
from wac_offline.scaffold_v1.wire import canonical, digest, exact, parse


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def check(directory):
    manifest = parse((directory / 'manifest.json').read_bytes())
    require(manifest['schema'] == 'cortac.r1.self-application.v1', 'manifest version')
    expected = {'journal.json', 'baseline.json', 'validator.json', 'verification.json',
                'final-report.json', 'preflight.json'}
    require(set(manifest['files']) == expected, 'retained file inventory')
    for name, sha in manifest['files'].items():
        require(hashlib.sha256((directory / name).read_bytes()).hexdigest() == sha, 'retained digest: ' + name)
    rows = parse((directory / 'journal.json').read_bytes())
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT, body TEXT, previous TEXT, hash TEXT)')
        for row in rows:
            require(type(row.get('seq')) is int, 'integer event sequence')
            exact(row, ('seq', 'kind', 'body', 'previous', 'hash'))
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                       (row['seq'], row['kind'], canonical(row['body']), row['previous'], row['hash']))
        state, head, count = Task._read(db)
    genesis = state['genesis']
    require(genesis['task']['base_commit'] == manifest['base_commit'], 'task base binding')
    require(genesis['task']['id'] == manifest['task_id'], 'task id binding')
    require(repository.base_inventory(ROOT, manifest['base_commit']) == genesis['base'], 'historical base bytes')
    candidate = repository.base_inventory(ROOT, manifest['candidate_commit'])
    require(candidate == state['proposal'], 'historical candidate bytes')
    require(repository.git(ROOT, 'rev-parse', manifest['candidate_commit']+'^{tree}').decode().strip() == manifest['candidate_tree'], 'candidate tree')
    pin = parse((directory / 'validator.json').read_bytes())
    require(pin['base_commit'] == manifest['validator_commit'], 'validator base')
    module = ROOT / 'package/wac_offline/repository_task_v1'
    require(set(pin['files']) == {p.name for p in module.glob('*.py')}, 'validator source inventory')
    for name, sha in pin['files'].items():
        key = 'package/wac_offline/repository_task_v1/' + name
        require(genesis['base'][key]['sha256'] == sha, 'base validator pin')
        old = repository.git(ROOT, 'show', manifest['validator_commit']+':'+key)
        require(hashlib.sha256(old).hexdigest() == sha, 'historical installed validator pin')
    report = parse((directory / 'final-report.json').read_bytes())
    require(report['journal_head'] == head and report['events'] == count, 'final journal head')
    require(report['candidate_digest'] == digest(candidate), 'final candidate')
    require(report['checks'] == state['checks'] and report['review'] == state['review'], 'final outcomes')
    require(state['pending'] is None and all(c['outcome'] == 'PASS' for c in state['checks'].values()), 'observed checks')
    require(report['declared_control'] == 'SHARED' and report['approval_granted'] is False
            and report['independent_review_established'] is False and report['authority'] == 'NONE', 'nonpromotion limits')
    require(state['review']['supplied_assessments_pass'] is False, 'unknown review retained')
    return dict(schema='cortac.r1.self-application-replay.v1', journal_events=count,
                historical_source_match=True, current_head_freshness_claim=False,
                checks_executed=0, local_checks_recorded_pass=True,
                replay_validator_matches_historical=all(hashlib.sha256((module/name).read_bytes()).hexdigest() == sha for name, sha in pin['files'].items()),
                independent_review_established=False, authority='NONE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT / 'provenance/r1_self_application')
    args = parser.parse_args()
    try:
        print(canonical(check(args.evidence)))
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print('RETAINED_R1_REPLAY_REFUSED: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
