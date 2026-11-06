"""Single-assignment journal; local evidence only, never a workshop event writer."""
from contextlib import closing
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import sqlite3

from ..decision_records import validate_decision_record, validate_protected_limits
from . import VERSION
from . import ap1
from .wire import bounded, canonical, digest, exact, integer, label, parse

MAX_EVENTS = 128
ZERO = '0' * 64
SCOPE = {'scope': 'LOCAL_RESEARCH_ONLY', 'authority': 'NONE',
         'execution_enabled': False, 'controller_closure': 'SUPPLIED_UNVERIFIED'}


def initial(genesis):
    exact(genesis, ('version', 'assignment', 'brief', 'protected_limits', *SCOPE))
    if genesis['version'] != VERSION or any(type(genesis[k]) is not type(v) or genesis[k] != v for k, v in SCOPE.items()):
        raise ValueError('unsupported scope/version')
    a = genesis['assignment']
    exact(a, ('id', 'agent', 'implementation', 'controller', 'reviewer', 'reviewer_controller'))
    for value in a.values():
        label(value)
    if a['agent'] == a['reviewer'] or a['controller'] == a['reviewer_controller']:
        raise ValueError('declared reviewer conflict')
    validate_protected_limits(genesis['protected_limits'])
    b = genesis['brief']
    exact(b, ('profile', 'role', 'external_authority', 'instance', 'view_head',
              'attempts_remaining', 'work', 'assembly_reference', 'brief_id'))
    if (b['profile'] != ap1.PROFILE_1_1 or b['role'] != 'workshop-proposer'
            or b['external_authority'] != 'NONE' or b['assembly_reference'] is not None
            or not ap1.matches(ap1.INSTANCE, b['instance']) or not ap1.matches(ap1.HEAD, b['view_head'])
            or b['brief_id'] != digest({k: v for k, v in b.items() if k != 'brief_id'})):
        raise ValueError('invalid brief binding')
    integer(b['attempts_remaining'])
    # Rebuild from only public fields; require the complete pinned AP1 projection.
    rebuilt = ap1.brief(dict(protocol=ap1.PROTOCOL, disposition='TASK', external_authority='NONE',
        instance=b['instance'], view_head=b['view_head'], attempts_remaining=b['attempts_remaining'],
        task=dict(b['work'], protocol=ap1.TASK, scope='LOCAL_RESEARCH', external_authority='NONE')),
        profile=ap1.PROFILE_1_1)
    if rebuilt != b:
        raise ValueError('incomplete or unprojected brief fields')
    return {'genesis': deepcopy(genesis), 'decision': None, 'decision_started': False,
            'binding': None, 'pending': None, 'operations': [], 'transport': None,
            'review': None, 'elapsed_ns_observed': 0, 'decision_elapsed_ns': None}


def transport_status(status, state):
    exact(status, ('version', 'state', 'request_id', 'instance', 'operations_started',
                   'operations_observed', 'latest_observation', 'recorded',
                   'external_authority', 'assurance'))
    binding = state['binding']
    if (status['version'] != 'client-only-2.0.0' or status['external_authority'] != 'NONE'
            or status['request_id'] != binding['request_id'] or status['instance'] != binding['instance']):
        raise ValueError('transport binding mismatch')
    for key in ('operations_started', 'operations_observed'):
        integer(status[key], 256)
        old = state['transport']
        if old and status[key] < old[key]:
            raise ValueError('transport counters regressed')
    if status['operations_observed'] > status['operations_started']:
        raise ValueError('observation without operation')
    if status['latest_observation'] not in (None, 'RECORDED', 'UNRESOLVED',
            'RECEIPT_REQUIRES_EXACT_RETRY', 'NOT_SENT_ALREADY_RECORDED'):
        raise ValueError('unknown transport observation')
    if type(status['assurance']) is not str:
        raise ValueError('missing transport scope')
    if status['state'] == 'UNRESOLVED':
        if status['recorded'] is not None:
            raise ValueError('unresolved receipt contradiction')
    elif status['state'] == 'RECORDED':
        if status['operations_started'] < 1 or status['operations_observed'] < 1:
            raise ValueError('recorded receipt needs an observed client operation')
        rec = status['recorded']
        exact(rec, ('http_status', 'receipt'))
        p = rec['receipt']
        common = ('protocol', 'disposition', 'external_authority', 'request_id')
        accepted = rec['http_status'] == 200 and type(rec['http_status']) is int
        exact(p, common + (('instance', 'event_seq', 'event_hash', 'proposal_id', 'permits_execution') if accepted else ()))
        if p['protocol'] != ap1.PROTOCOL or p['external_authority'] != 'NONE' or p['request_id'] != binding['request_id']:
            raise ValueError('receipt binding mismatch')
        if accepted:
            integer(p['event_seq'])
            if (p['disposition'] != 'ACCEPTED' or p['instance'] != binding['instance']
                    or p['event_seq'] < 1 or not ap1.matches(ap1.HEAD, p['event_hash'])
                    or type(p['proposal_id']) is not str
                    or not re.fullmatch(r'propose-[0-9]{1,8}', p['proposal_id'])
                    or p['permits_execution'] is not False):
                raise ValueError('invalid acceptance')
        else:
            allowed = {400: 'INVALID_REQUEST', 409: 'STALE_VIEW', 422: 'PROPOSAL_REFUSED'}
            if type(rec['http_status']) is not int or allowed.get(rec['http_status']) != p['disposition']:
                raise ValueError('unrecordable refusal')
    else:
        raise ValueError('unsupported transport state')
    if state['transport'] and state['transport']['state'] == 'RECORDED' and status != state['transport']:
        raise ValueError('recorded observation changed')


def advance(state, kind, data):
    s = deepcopy(state)
    if kind == 'decision_start':
        exact(data, ())
        if s['decision_started']:
            raise ValueError('decision already started')
        s['decision_started'] = True
    elif kind == 'decision_finish':
        exact(data, ('outcome', 'reply', 'response_sha256', 'elapsed_ns'))
        integer(data['elapsed_ns'])
        if not s['decision_started'] or s['decision'] is not None:
            raise ValueError('decision out of order')
        if data['outcome'] == 'VALID':
            bounded(data['reply'])
            if data['response_sha256'] is not None:
                raise ValueError('valid decision uses retained canonical content')
            ap1.interpret(s['genesis']['brief'], data['reply'])
        elif data['outcome'] in ('INVALID', 'TIMEOUT', 'CRASH'):
            if data['reply'] is not None:
                raise ValueError('failure cannot supply a decision')
            if data['outcome'] == 'INVALID':
                if not ap1.matches(ap1.HEAD, data['response_sha256']):
                    raise ValueError('invalid response digest')
            elif data['response_sha256'] is not None:
                raise ValueError('no response expected')
        else:
            raise ValueError('invalid decision outcome')
        s['decision'] = data
        s['decision_elapsed_ns'] = data['elapsed_ns']
        s['elapsed_ns_observed'] += data['elapsed_ns']
    elif kind == 'intent_bound':
        exact(data, ('outbox', 'url', 'credential_digest', 'instance', 'request_id', 'raw_sha256'))
        d = s['decision']
        if s['binding'] or not d or d['outcome'] != 'VALID' or d['reply']['choice'] != 'propose':
            raise ValueError('no new proposal to bind')
        request = ap1.interpret(s['genesis']['brief'], d['reply'])
        if (data['instance'] != s['genesis']['brief']['instance'] or data['request_id'] != request['request_id']
                or data['raw_sha256'] != digest(request)
                or not ap1.matches(ap1.HEAD, data['credential_digest'])):
            raise ValueError('intent differs from decision')
        if type(data['outbox']) is not str or not Path(data['outbox']).is_absolute():
            raise ValueError('absolute custodian path required')
        from .transport import check_endpoint
        check_endpoint(data['url'])
        s['binding'] = data
    elif kind == 'operation_start':
        exact(data, ('kind',))
        if not s['binding'] or s['pending'] or data['kind'] not in ('stage', 'submit', 'resolve', 'inspect'):
            raise ValueError('operation out of order')
        if data['kind'] == 'stage' and s['operations']:
            raise ValueError('no restaging a possibly created intent')
        if data['kind'] != 'stage' and not s['operations']:
            raise ValueError('stage required first')
        s['pending'] = data['kind']
        s['operations'].append({'kind': data['kind'], 'observed': False})
    elif kind == 'operation_finish':
        exact(data, ('status', 'elapsed_ns', 'recovered'))
        if not s['pending'] or type(data['recovered']) is not bool:
            raise ValueError('no pending operation')
        if data['recovered']:
            if data['elapsed_ns'] is not None:
                raise ValueError('interrupted duration unknown')
        else:
            integer(data['elapsed_ns'])
            s['elapsed_ns_observed'] += data['elapsed_ns']
        transport_status(data['status'], s)
        if s['pending'] == 'stage' and not data['recovered'] and (
                data['status']['state'] != 'UNRESOLVED' or data['status']['operations_started'] != 0):
            raise ValueError('new stage cannot perform network work')
        s['transport'] = data['status']
        s['operations'][-1]['observed'] = True
        s['operations'][-1]['duration_unknown'] = data['elapsed_ns'] is None
        s['pending'] = None
    elif kind == 'advisory_review':
        exact(data, ('reviewer', 'decision_digest', 'record'))
        if s['review'] or not s['transport'] or s['transport']['state'] != 'RECORDED':
            raise ValueError('recorded accepted proposal required')
        if s['transport']['recorded']['receipt']['disposition'] != 'ACCEPTED':
            raise ValueError('refusal cannot receive proposal review')
        if (data['reviewer'] != s['genesis']['assignment']['reviewer']
                or data['decision_digest'] != digest(s['decision']['reply'])):
            raise ValueError('review assignment/binding mismatch')
        passes = validate_decision_record(data['record'], s['genesis']['protected_limits'])
        s['review'] = {**data, 'supplied_assessments_pass': passes}
    else:
        raise ValueError('unknown event kind')
    return s


class Journal:
    def __init__(self, path):
        self.path = Path(path).absolute()

    def connect(self):
        if self.path.is_symlink():
            raise ValueError('journal symlink refused')
        return sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=10)

    @classmethod
    def create(cls, path, task, assignment, protected_limits):
        bounded(task)
        brief = ap1.brief(task, profile=ap1.PROFILE_1_1)
        genesis = bounded(dict(version=VERSION, assignment=assignment, brief=brief,
                               protected_limits=protected_limits, **SCOPE))
        initial(genesis)
        target = cls(path)
        fd = os.open(target.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        try:
            with closing(target.connect()) as db, db:
                db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
                event = dict(seq=1, kind='genesis', body=genesis, previous=ZERO)
                db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (1, 'genesis', canonical(genesis), ZERO, digest(event)))
        except BaseException:
            target.path.unlink(missing_ok=True)
            raise
        return target

    @staticmethod
    def _read(db):
        rows = db.execute('SELECT seq,kind,body,previous,hash FROM events ORDER BY seq').fetchmany(MAX_EVENTS + 1)
        if not rows or len(rows) > MAX_EVENTS:
            raise ValueError('event count out of bounds')
        state, head = None, ZERO
        for n, (seq, kind, raw, previous, stored) in enumerate(rows, 1):
            if n == 1 and kind != 'genesis':
                raise ValueError('genesis must be first')
            body = parse(raw.encode())
            if seq != n or previous != head or stored != digest(dict(seq=seq, kind=kind, body=body, previous=previous)):
                raise ValueError('journal chain mismatch')
            state = initial(body) if n == 1 and kind == 'genesis' else advance(state, kind, body)
            head = stored
        return state, head, len(rows)

    def state(self):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return self._read(db)[0]

    def append(self, kind, data):
        bounded(data)
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            state, head, count = self._read(db)
            limit = MAX_EVENTS - 1 if kind in ('operation_start', 'decision_start') else MAX_EVENTS
            if count >= limit:
                raise ValueError('event budget exhausted')
            updated = advance(state, kind, data)
            event = dict(seq=count+1, kind=kind, body=data, previous=head)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                       (count+1, kind, canonical(data), head, digest(event)))
            return updated

    def begin_decision(self):
        self.append('decision_start', {})
        return self.state()['genesis']['brief']

    def finish_decision(self, raw=None, *, outcome='RESPONSE', elapsed_ns=0):
        s = self.state()
        reply, fingerprint = None, None
        if outcome == 'RESPONSE':
            if type(raw) is not bytes:
                raise ValueError('response bytes required')
            try:
                reply = parse(raw)
                ap1.interpret(s['genesis']['brief'], reply)
                outcome = 'VALID'
            except (ValueError, KeyError, TypeError):
                outcome, reply = 'INVALID', None
                fingerprint = hashlib.sha256(raw).hexdigest()
        elif outcome not in ('TIMEOUT', 'CRASH') or raw is not None:
            raise ValueError('unsupported reported outcome')
        return self.append('decision_finish', dict(outcome=outcome, reply=reply,
                           response_sha256=fingerprint, elapsed_ns=elapsed_ns))

    def review(self, reviewer, record):
        s = self.state()
        return self.append('advisory_review', dict(reviewer=reviewer,
                           decision_digest=digest(s['decision']['reply']), record=record))

    def report(self):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            s, head, count = self._read(db)
        d = s['decision']
        outcome = ('INTERRUPTED_OR_PENDING' if s['decision_started'] else 'NOT_STARTED') if d is None else (
            d['reply']['choice'].upper() if d['outcome'] == 'VALID' else d['outcome'])
        transport = s['transport']
        return dict(version=VERSION, **SCOPE, assignment=s['genesis']['assignment'],
                    decision=outcome, transport='NOT_STAGED' if not s['binding'] else (
                        transport['state'] if transport else 'UNRESOLVED'),
                    host_authority='NOT_OBSERVED', host_receipt=transport['recorded'] if transport else None,
                    advisory_review=s['review'], journal_head=head, events=count,
                    decision_attempts=int(s['decision_started']), operations_started=len(s['operations']),
                    operations_observed=sum(x['observed'] for x in s['operations']),
                    pending_operation=s['pending'], elapsed_ns_observed=s['elapsed_ns_observed'],
                    interrupted_duration_unknown=any(x.get('duration_unknown') for x in s['operations']),
                    synthetic_decision_slots=None, real_model_calls='NOT_MEASURED_BY_S1',
                    evidence_authenticated=False, policy_fidelity_verified=False)
