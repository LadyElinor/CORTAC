"""Second implementation of chain/count checks; no reducer or agent imports.

Does not validate every AP1/transition/review rule, source truth, or policy fidelity.
Use together with Journal.report's full lifecycle replay, not in its place.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def audit(path, report):
    def hash_value(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                              separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError('duplicate event key')
            obj[key] = value
        return obj
    with closing(sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro', uri=True)) as db:
        rows = db.execute('SELECT seq,kind,body,previous,hash FROM events ORDER BY seq').fetchmany(129)
    if not 1 <= len(rows) <= 128:
        raise ValueError('invalid history size')
    head, decisions, starts, ends, elapsed = '0'*64, 0, 0, 0, 0
    outcome, pending, receipt, state, review, unknown_duration = 'NOT_STARTED', None, None, 'NOT_STAGED', None, False
    completed = False
    for n, kind, raw, previous, expected in rows:
        body = json.loads(raw, object_pairs_hook=pairs)
        actual = hash_value({'seq': n, 'kind': kind, 'body': body, 'previous': previous})
        if previous != head or actual != expected:
            raise ValueError('chain mismatch')
        head = actual
        if kind == 'genesis':
            if n != 1 or body['authority'] != 'NONE' or body['execution_enabled'] is not False:
                raise ValueError('genesis scope mismatch')
            assignment = body['assignment']
        elif kind == 'decision_start':
            decisions += 1
            outcome = 'INTERRUPTED_OR_PENDING'
        elif kind == 'decision_finish':
            if decisions != 1 or completed:
                raise ValueError('decision accounting mismatch')
            completed = True
            outcome = body['reply']['choice'].upper() if body['outcome'] == 'VALID' else body['outcome']
            elapsed += body['elapsed_ns']
        elif kind == 'intent_bound':
            state = 'UNRESOLVED'
        elif kind == 'operation_start':
            if pending:
                raise ValueError('overlapping operations')
            starts += 1; pending = body['kind']
        elif kind == 'operation_finish':
            if not pending:
                raise ValueError('unstarted observation')
            ends += 1; pending = None
            if body['elapsed_ns'] is None:
                unknown_duration = True
            else:
                elapsed += body['elapsed_ns']
            if body['status'] is not None:
                state = body['status']['state']; receipt = body['status']['recorded']
        elif kind == 'advisory_review':
            review = dict(body, supplied_assessments_pass=all(
                x['status'] == 'PASS' for x in body['record']['protected_limit_assessments']))
        else:
            raise ValueError('unknown event')
    if [r[0] for r in rows] != list(range(1, len(rows)+1)) or decisions > 1:
        raise ValueError('nonconsecutive sequence')
    expected = dict(assignment=assignment, events=len(rows), journal_head=head, decision=outcome,
                    decision_attempts=decisions, operations_started=starts, operations_observed=ends,
                    pending_operation=pending, elapsed_ns_observed=elapsed,
                    interrupted_duration_unknown=unknown_duration, transport=state,
                    host_receipt=receipt, advisory_review=review, host_authority='NOT_OBSERVED',
                    authority='NONE', execution_enabled=False, synthetic_decision_slots=None,
                    evidence_authenticated=False, policy_fidelity_verified=False,
                    scope='LOCAL_RESEARCH_ONLY', controller_closure='SUPPLIED_UNVERIFIED',
                    version='cortac.agent-scaffold.v1', real_model_calls='NOT_MEASURED_BY_S1')
    if json.dumps(report, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError('report differs from independent counts')
    return {'verified': True, 'scope': 'CHAIN_AND_LIFECYCLE_COUNTS_ONLY',
            'authority': 'NONE', 'events': len(rows), 'external_authenticity': False}
