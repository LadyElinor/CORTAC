"""R1 deterministic lifecycle and durable local receipts; no automatic approvals."""
from contextlib import closing
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
from . import VERSION, SCOPE
from . import contract, repository
from ..decision_records import validate_decision_record
from ..scaffold_v1.wire import bounded, canonical, digest, exact, integer, parse

ZERO = '0' * 64
MAX_EVENTS = 64
MAX_OUTPUT = 1024 * 1024


def initial(g):
    exact(g, ('version', 'root', 'task', 'base', *SCOPE))
    if g['version'] != VERSION or any(type(g[k]) is not type(v) or g[k] != v for k, v in SCOPE.items()):
        raise ValueError('scope/version mismatch')
    if type(g['root']) is not str or not Path(g['root']).is_absolute():
        raise ValueError('absolute custodian root required')
    contract.task(g['task']); repository.validate_inventory(g['base'])
    return dict(genesis=deepcopy(g), started=False, decision=None, proposal=None, checks={}, pending=None, review=None)


def evidence(s):
    return digest(dict(candidate=digest(s['proposal']) if s['proposal'] else None, checks=s['checks']))


def references(s):
    return dict(task=digest(s['genesis']['task']), candidate=digest(s['proposal']),
                **{'check:'+key: digest(value) for key, value in s['checks'].items() if value is not None})


def check_references(record, available):
    if type(record) is dict:
        for key, value in record.items():
            if key == 'evidence_refs':
                if not set(value) <= set(available):
                    raise ValueError('unresolved review evidence reference')
            else:
                check_references(value, available)
    elif type(record) is list:
        for value in record:
            check_references(value, available)


def outcome(s, data):
    exact(data, ('id', 'before', 'after', 'process', 'elapsed_ns'))
    integer(data['elapsed_ns'])
    for name in ('before', 'after'):
        if data[name] is not None and (type(data[name]) is not str or not repository.SHA.fullmatch(data[name])):
            raise ValueError('invalid source digest')
    process = data['process']
    if process is not None:
        exact(process, ('status', 'exit_code', 'stdout', 'stderr'))
        if process['status'] not in ('EXITED', 'TIMEOUT', 'ERROR'):
            raise ValueError('unknown process status')
        if process['status'] == 'EXITED':
            if type(process['exit_code']) is not int or not -(2**31) <= process['exit_code'] <= 2**32-1:
                raise ValueError('invalid exit code')
        elif process['exit_code'] is not None:
            raise ValueError('unknown exit must remain null')
        for stream in ('stdout', 'stderr'):
            exact(process[stream], ('bytes', 'sha256'))
            integer(process[stream]['bytes'])
            if type(process[stream]['sha256']) is not str or not repository.SHA.fullmatch(process[stream]['sha256']):
                raise ValueError('invalid output digest')
    bound = digest(s['proposal'])
    if data['before'] != bound or data['after'] != bound:
        return 'SOURCE_UNAVAILABLE' if data['before'] is None or data['after'] is None else 'SOURCE_CHANGED'
    if process is None:
        raise ValueError('matching source without process observation')
    if process['status'] != 'EXITED':
        return process['status']
    if any(process[k]['bytes'] > MAX_OUTPUT for k in ('stdout', 'stderr')):
        return 'OUTPUT_LIMIT'
    spec = next(c for c in s['genesis']['task']['checks'] if c['id'] == data['id'])
    return 'PASS' if process['exit_code'] == spec['expected_exit'] else 'FAIL'


def advance(state, kind, data):
    s = deepcopy(state); t = s['genesis']['task']
    if kind == 'decision_start':
        exact(data, ())
        if s['started']:
            raise ValueError('one participant attempt per task')
        s['started'] = True
    elif kind == 'decision_finish':
        exact(data, ('response', 'invalid_sha256', 'candidate'))
        if not s['started'] or s['decision'] is not None:
            raise ValueError('decision finish out of order')
        if data['response'] is None:
            if data['candidate'] is not None or type(data['invalid_sha256']) is not str or not repository.SHA.fullmatch(data['invalid_sha256']):
                raise ValueError('invalid decision needs only retained byte digest')
        else:
            contract.decision(s['genesis'], data['response'])
            if data['invalid_sha256'] is not None:
                raise ValueError('valid response retained directly')
            if data['response']['choice'] == 'propose':
                repository.scoped(s['genesis']['base'], data['candidate'], t['allowed_paths'])
                if digest(data['candidate']) != data['response']['candidate_digest']:
                    raise ValueError('candidate binding mismatch')
                s['proposal'] = data['candidate']
            elif data['candidate'] is not None:
                raise ValueError('nonproposal cannot supply candidate')
        s['decision'] = data
    elif kind == 'check_start':
        exact(data, ('id',))
        if (s['proposal'] is None or s['pending'] or s['review'] or data['id'] in s['checks']
                or data['id'] not in [c['id'] for c in t['checks']]):
            raise ValueError('check not available')
        s['pending'] = data['id']; s['checks'][data['id']] = None
    elif kind == 'check_finish':
        if s['pending'] != data.get('id') or s['pending'] is None:
            raise ValueError('no matching pending check')
        result = outcome(s, data)
        s['checks'][data['id']] = dict(data, outcome=result); s['pending'] = None
    elif kind == 'review':
        exact(data, ('reviewer', 'candidate_digest', 'evidence_digest', 'record'))
        if (s['proposal'] is None or s['review'] or s['pending']
                or len(s['checks']) != len(t['checks']) or any(v is None for v in s['checks'].values())):
            raise ValueError('all check observations required before review')
        if (data['reviewer'] != t['reviewer'] or data['candidate_digest'] != digest(s['proposal'])
                or data['evidence_digest'] != evidence(s)):
            raise ValueError('review role/candidate/evidence binding mismatch')
        passed = validate_decision_record(data['record'], t['protected_limits'])
        check_references(data['record'], references(s))
        s['review'] = dict(data, supplied_assessments_pass=passed)
    else:
        raise ValueError('unknown repository event')
    return s


class Task:
    def __init__(self, path):
        # Canonicalize parent aliases (including Windows short paths), while
        # retaining the leaf itself so _connect still refuses a symlink journal.
        target = Path(path).absolute()
        self.path = target.parent.resolve(strict=True) / target.name

    def _connect(self):
        if self.path.is_symlink():
            raise ValueError('journal symlink refused')
        return sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, timeout=10)

    @classmethod
    def create(cls, path, root, specification):
        contract.task(specification); root = repository.root_path(root)
        target = cls(path)
        if target.path.is_relative_to(root):
            relative = target.path.relative_to(root).as_posix()
            try:
                repository.git(root, 'check-ignore', '--no-index', '--', relative)
            except Exception as exc:
                raise ValueError('journal inside repository must be ignored') from exc
        genesis = bounded(dict(version=VERSION, **SCOPE, root=str(root), task=specification,
                               base=repository.base_inventory(root, specification['base_commit'])))
        initial(genesis)
        fd = os.open(target.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
        try:
            with closing(target._connect()) as db, db:
                db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
                event = dict(seq=1, kind='genesis', body=genesis, previous=ZERO)
                db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (1, 'genesis', canonical(genesis), ZERO, digest(event)))
        except BaseException:
            target.path.unlink(missing_ok=True); raise
        return target

    @staticmethod
    def _read(db):
        rows = db.execute('SELECT seq,kind,body,previous,hash FROM events ORDER BY seq').fetchmany(MAX_EVENTS+1)
        if not 1 <= len(rows) <= MAX_EVENTS:
            raise ValueError('journal event limit')
        s = None; head = ZERO
        for expected, (n, kind, raw, previous, h) in enumerate(rows, 1):
            data = parse(raw.encode())
            if n != expected or previous != head or h != digest(dict(seq=n, kind=kind, body=data, previous=previous)):
                raise ValueError('journal chain mismatch')
            if n == 1:
                if kind != 'genesis':
                    raise ValueError('genesis required')
                s = initial(data)
            else:
                s = advance(s, kind, data)
            head = h
        return s, head, len(rows)

    def snapshot(self):
        with closing(self._connect()) as db:
            db.execute('BEGIN')
            return self._read(db)

    def append(self, kind, data):
        bounded(data)
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            s, head, n = self._read(db)
            reserve = 1 if kind in ('decision_start', 'check_start') else 0
            if n >= MAX_EVENTS-reserve:
                raise ValueError('journal exhausted')
            updated = advance(s, kind, data)
            event = dict(seq=n+1, kind=kind, body=data, previous=head)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (n+1, kind, canonical(data), head, digest(event)))
            return updated

    def begin(self):
        s = self.append('decision_start', {})
        return contract.brief(s['genesis'])

    def candidate(self):
        s, _, _ = self.snapshot()
        observed = repository.observe(Path(s['genesis']['root']), s['genesis']['base'])
        paths = repository.scoped(s['genesis']['base'], observed, s['genesis']['task']['allowed_paths'])
        return dict(candidate_digest=digest(observed), changed_paths=paths)

    def decide(self, raw):
        s, _, _ = self.snapshot()
        if not s['started'] or s['decision'] is not None:
            raise ValueError('no pending participant decision')
        candidate = None
        try:
            response = parse(raw); contract.decision(s['genesis'], response)
            if response['choice'] == 'propose':
                candidate = repository.observe(Path(s['genesis']['root']), s['genesis']['base'])
                repository.scoped(s['genesis']['base'], candidate, s['genesis']['task']['allowed_paths'])
                if digest(candidate) != response['candidate_digest']:
                    raise ValueError('stale candidate response')
        except (ValueError, OSError, TypeError, KeyError):
            if type(raw) is not bytes:
                raise ValueError('response bytes required')
            return self.append('decision_finish', dict(response=None, candidate=None, invalid_sha256=hashlib.sha256(raw).hexdigest()))
        return self.append('decision_finish', dict(response=response, candidate=candidate, invalid_sha256=None))

    def review(self, packet):
        s, _, _ = self.snapshot()
        if s['proposal'] is None or repository.observe(Path(s['genesis']['root']), s['genesis']['base']) != s['proposal']:
            raise ValueError('review source no longer current')
        return self.append('review', packet)

    def report(self, refresh=False):
        s, head, n = self.snapshot(); t = s['genesis']['task']
        current = None
        if refresh and s['proposal'] is not None:
            try:
                current = repository.observe(Path(s['genesis']['root']), s['genesis']['base']) == s['proposal']
            except (ValueError, OSError, UnicodeError, subprocess.SubprocessError):
                current = None
        d = s['decision']
        decision = ('PENDING' if s['started'] else 'NOT_STARTED') if d is None else ('INVALID' if d['response'] is None else d['response']['choice'].upper())
        return dict(version=VERSION, **SCOPE, task_id=t['id'], journal_head=head, events=n,
                    decision=decision, candidate_digest=digest(s['proposal']) if s['proposal'] else None,
                    candidate_current=current, evidence_digest=evidence(s), checks=s['checks'], pending_check=s['pending'],
                    evidence_refs=references(s),
                    local_checks_passed=len(s['checks']) == len(t['checks']) and all(c and c['outcome']=='PASS' for c in s['checks'].values()),
                    review=s['review'], review_applicable=bool(current and s['review']),
                    declared_control='SHARED' if t['proposer_controller']==t['reviewer_controller'] else 'DIFFERENT_UNVERIFIED',
                    approval_granted=False, local_effects='JOURNAL_AND_EXPLICIT_TEST_PROCESSES',
                    parent_receipt=t['parent_receipt'], parent_authenticity=False, source_authenticity=False)
