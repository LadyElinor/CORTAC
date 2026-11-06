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
from wac_offline.repository_task_v1.journal import MAX_EVENTS, Task, project_report
from wac_offline.scaffold_v1.wire import canonical, exact, label, parse


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def validate_manifest(manifest):
    exact(manifest, ('schema', 'design_commit', 'base_commit', 'candidate_commit',
                     'candidate_tree', 'task_id', 'scope', 'authority',
                     'independent_review_established', 'files', 'validator_commit'))
    require(manifest['schema'] == 'cortac.r1.self-application.v1', 'manifest version')
    require(manifest['scope'] == 'LOCAL_RESEARCH_ONLY' and manifest['authority'] == 'NONE'
            and manifest['independent_review_established'] is False, 'manifest nonpromotion limits')
    for name in ('design_commit', 'base_commit', 'candidate_commit', 'candidate_tree', 'validator_commit'):
        require(type(manifest[name]) is str and repository.HEX.fullmatch(manifest[name]), 'manifest Git identifier: ' + name)
    label(manifest['task_id'])
    expected = {'journal.json', 'baseline.json', 'validator.json', 'verification.json',
                'final-report.json', 'preflight.json'}
    require(type(manifest['files']) is dict and set(manifest['files']) == expected, 'retained file inventory')
    for sha in manifest['files'].values():
        require(type(sha) is str and repository.SHA.fullmatch(sha), 'retained file digest')


def replay_rows(rows):
    require(type(rows) is list and 1 <= len(rows) <= MAX_EVENTS, 'bounded event array required')
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT, body TEXT, previous TEXT, hash TEXT)')
        for row in rows:
            exact(row, ('seq', 'kind', 'body', 'previous', 'hash'))
            require(type(row['seq']) is int, 'integer event sequence')
            require(type(row['body']) is dict, 'object event body')
            require(all(type(row[k]) is str for k in ('kind', 'previous', 'hash')), 'string event metadata')
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                       (row['seq'], row['kind'], canonical(row['body']), row['previous'], row['hash']))
        return Task._read(db)


def validate_report(report, state, head, count):
    require(type(report) is dict, 'object report required')
    current = report.get('candidate_current')
    require(current is None or type(current) is bool, 'historical freshness must be bool or null')
    expected = project_report(state, head, count, current)
    exact(report, expected)
    # Python equality treats True, 1 and 1.0 as equal. JSON contract types do not.
    require(canonical(report) == canonical(expected), 'report differs from journal projection')


def check(directory):
    manifest = parse((directory / 'manifest.json').read_bytes())
    validate_manifest(manifest)
    for name, sha in manifest['files'].items():
        require(hashlib.sha256((directory / name).read_bytes()).hexdigest() == sha, 'retained digest: ' + name)
    rows = parse((directory / 'journal.json').read_bytes())
    state, head, count = replay_rows(rows)
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
    validate_report(report, state, head, count)
    require(state['pending'] is None and all(c['outcome'] == 'PASS' for c in state['checks'].values()), 'observed checks')
    require(report['declared_control'] == 'SHARED', 'shared control retained')
    require(state['review']['supplied_assessments_pass'] is False, 'unknown review retained')
    return dict(schema='cortac.r1.self-application-replay.v1', journal_events=count,
                historical_source_match=True, current_head_freshness_claim=False,
                report_projection_valid=True, historical_freshness_verified=False,
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
