"""Closed synthetic records and an actual, disposable SQLite effect gateway.

This is a trusted-harness integration test, NOT a security boundary. Caller-supplied
actor IDs are not authenticated. Mandates and controller declarations are fabricated.
No method targets an external resource; the database is newly created and owned here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading

from .decision_records import validate_decision_record, validate_protected_limits
from .io import InputError


class RunnerError(ValueError):
    pass


def digest(kind, value):
    return hashlib.sha256((kind + '\n' + json.dumps(value, sort_keys=True,
                           separators=(',', ':'), ensure_ascii=True, allow_nan=False)).encode()).hexdigest()


def exact(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise RunnerError(label + ': missing or unknown fields')


def text(value, label):
    if type(value) is not str or not value.strip():
        raise RunnerError(label + ': nonblank string required')


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise RunnerError(label + ': integer out of range')


def sha(value, label):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise RunnerError(label + ': SHA-256 required')


POLICY_FIELDS = ('schema', 'case_id', 'epoch', 'principals', 'protected_limits', 'approval_ids',
                 'approval_threshold', 'excluded_ids', 'operation_budget')
PROPOSAL_FIELDS = ('schema', 'case_id', 'policy_digest', 'epoch', 'expected_revision', 'operation',
                   'target', 'value', 'proposer', 'evidence', 'decision_source', 'decision_record')
MANDATE_FIELDS = ('schema', 'id', 'case_id', 'policy_digest', 'proposal_digest', 'authorizer',
                  'expires_tick', 'max_uses', 'scope', 'provenance')
RECEIPT_FIELDS = ('schema', 'id', 'case_id', 'proposal_digest', 'policy_digest', 'epoch',
                  'expected_revision', 'operation', 'evidence_digest', 'kind', 'actor',
                  'challenge_digest', 'result', 'scope', 'provenance')
EVIDENCE_FIELDS = ('schema', 'id', 'origin', 'content', 'content_digest', 'provenance')
ROLES = {'proposer', 'assessor', 'approver', 'authorizer', 'executor', 'auditor', 'reviewer', 'affected_party'}
SCOPE = 'SYNTHETIC_SCRATCH_ONLY'


def validate_policy(policy):
    exact(policy, POLICY_FIELDS, 'policy')
    if policy['schema'] != 'cortac.scratch.policy.v1':
        raise RunnerError('unsupported policy schema')
    text(policy['case_id'], 'case_id')
    integer(policy['epoch'], 'epoch', 1)
    integer(policy['operation_budget'], 'operation_budget', 1)
    if type(policy['principals']) is not list or not policy['principals']:
        raise RunnerError('principals required')
    principals = {}
    for p in policy['principals']:
        exact(p, ('id', 'controller', 'roles'), 'principal')
        text(p['id'], 'principal id'); text(p['controller'], 'controller')
        if p['id'] in principals:
            raise RunnerError('duplicate principal')
        if type(p['roles']) is not list or not p['roles'] or any(type(r) is not str or r not in ROLES for r in p['roles']) or len(set(p['roles'])) != len(p['roles']):
            raise RunnerError('invalid roles')
        principals[p['id']] = p
    for field in ('approval_ids', 'excluded_ids'):
        ids = policy[field]
        if type(ids) is not list or any(type(i) is not str or i not in principals for i in ids) or len(set(ids)) != len(ids):
            raise RunnerError('invalid ' + field)
    if not policy['approval_ids'] or any('approver' not in principals[i]['roles'] for i in policy['approval_ids']):
        raise RunnerError('approval roll invalid')
    integer(policy['approval_threshold'], 'approval_threshold', 1)
    if policy['approval_threshold'] > len(policy['approval_ids']):
        raise RunnerError('approval threshold exceeds frozen roll')
    if len({principals[i]['controller'] for i in policy['approval_ids']}) != len(policy['approval_ids']):
        raise RunnerError('approval roll shares a declared controller')
    try:
        validate_protected_limits(policy['protected_limits'])
    except InputError as exc:
        raise RunnerError(str(exc)) from exc
    return principals


def validate_evidence(record):
    exact(record, EVIDENCE_FIELDS, 'evidence')
    if record['schema'] != 'cortac.scratch.evidence.v1' or record['provenance'] != 'SYNTHETIC_FIXTURE':
        raise RunnerError('unsupported evidence provenance')
    for key in ('id', 'origin', 'content'):
        text(record[key], key)
    sha(record['content_digest'], 'content_digest')
    if hashlib.sha256(record['content'].encode('utf-8')).hexdigest() != record['content_digest']:
        raise RunnerError('evidence bytes mismatch')


def evidence_record(identifier, origin, content):
    record = dict(schema='cortac.scratch.evidence.v1', id=identifier, origin=origin,
                  content=content, content_digest=hashlib.sha256(content.encode('utf-8')).hexdigest(),
                  provenance='SYNTHETIC_FIXTURE')
    validate_evidence(record)
    return record


class ScratchGateway:
    """Single-process serialized, atomic effects with an observable receipt journal.

    A closed constructor pins the harness policy, evidence bytes and exact mandates.
    It never loads credentials, uses network I/O, or accepts a filesystem target.
    TemporaryDirectory cleanup is part of close/context-manager use.
    """
    def __init__(self, policy, evidence, mandates):
        self._policy = deepcopy(policy)
        self._principals = validate_policy(self._policy)
        self._policy_digest = digest('Policy', self._policy)
        self._evidence = {}
        if type(evidence) is not list or not evidence:
            raise RunnerError('evidence inventory required')
        for record in deepcopy(evidence):
            validate_evidence(record)
            if record['id'] in self._evidence:
                raise RunnerError('duplicate evidence ID')
            self._evidence[record['id']] = record
        self._mandates = {}
        if type(mandates) is not list or not mandates:
            raise RunnerError('mandates required')
        for grant in deepcopy(mandates):
            exact(grant, MANDATE_FIELDS, 'mandate')
            if grant['schema'] != 'cortac.scratch.mandate.v1' or grant['scope'] != SCOPE or grant['provenance'] != 'SYNTHETIC_FIXTURE':
                raise RunnerError('unsupported mandate scope')
            text(grant['id'], 'mandate id')
            sha(grant['proposal_digest'], 'proposal_digest')
            if grant['case_id'] != policy['case_id'] or grant['policy_digest'] != self._policy_digest:
                raise RunnerError('mandate policy/case mismatch')
            self._actor(grant['authorizer'], 'authorizer')
            integer(grant['expires_tick'], 'expires_tick', 1)
            if type(grant['max_uses']) is not int or grant['max_uses'] != 1:
                raise RunnerError('mandates must be single-use')
            if grant['id'] in self._mandates:
                raise RunnerError('duplicate mandate ID')
            self._mandates[grant['id']] = grant
        self._lock = threading.RLock()
        self._temporary = tempfile.TemporaryDirectory(prefix='cortac-scratch-')
        self._db = sqlite3.connect(str(Path(self._temporary.name) / 'effects.sqlite'), check_same_thread=False)
        self._db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
        self._db.execute('INSERT INTO state VALUES (1, ?)', (json.dumps(dict(
            revision=0, value=None, tick=0, receipts={}, effects=[], challenges={},
            used_mandates=[], participants=[], pending_audit=None, journal=[])),))
        self._db.commit()

    def close(self):
        self._db.close()
        self._temporary.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def snapshot(self):
        with self._lock:
            return json.loads(self._db.execute('SELECT body FROM state WHERE id=1').fetchone()[0])

    def _actor(self, actor, role):
        if type(actor) is not str or actor not in self._principals or role not in self._principals[actor]['roles']:
            raise RunnerError('actor lacks declared ' + role + ' role')
        return self._principals[actor]['controller']

    def _independent(self, actor, others):
        controller = self._principals[actor]['controller']
        if any(controller == self._principals[o]['controller'] for o in others):
            raise RunnerError('declared controller conflict')

    def _proposal(self, p, state):
        exact(p, PROPOSAL_FIELDS, 'proposal')
        if p['schema'] != 'cortac.scratch.proposal.v1' or p['target'] != 'scratch_document':
            raise RunnerError('unsupported proposal schema/target')
        if p['case_id'] != self._policy['case_id'] or p['policy_digest'] != self._policy_digest:
            raise RunnerError('proposal case/policy mismatch')
        integer(p['epoch'], 'epoch', 1); integer(p['expected_revision'], 'expected_revision')
        if p['epoch'] != self._policy['epoch'] or p['expected_revision'] != state['revision']:
            raise RunnerError('stale epoch/revision')
        if p['operation'] not in ('COMMIT', 'REPAIR') or type(p['operation']) is not str:
            raise RunnerError('unsupported operation')
        if (p['operation'] == 'COMMIT') != (state['revision'] == 0):
            raise RunnerError('operation incompatible with revision')
        text(p['value'], 'value'); self._actor(p['proposer'], 'proposer')
        if type(p['evidence']) is not list or not p['evidence']:
            raise RunnerError('proposal evidence required')
        refs = {}
        for item in p['evidence']:
            exact(item, ('id', 'digest'), 'evidence reference')
            text(item['id'], 'evidence ID'); sha(item['digest'], 'evidence digest')
            if item['id'] in refs or item['id'] not in self._evidence:
                raise RunnerError('duplicate or unresolved evidence')
            if item['digest'] != digest('Evidence', self._evidence[item['id']]):
                raise RunnerError('resolved evidence binding mismatch')
            refs[item['id']] = item['digest']
        if [r['id'] for r in p['evidence']] != sorted(refs):
            raise RunnerError('evidence references must use canonical ID order')
        text(p['decision_source'], 'decision source')
        if p['decision_source'] not in refs or self._evidence[p['decision_source']]['content'] != p['value']:
            raise RunnerError('candidate differs from resolved decision source')
        try:
            if not validate_decision_record(p['decision_record'], self._policy['protected_limits']):
                raise RunnerError('protected limit failed or unknown')
        except InputError as exc:
            raise RunnerError(str(exc)) from exc
        used = set()
        def visit(node):
            if type(node) is dict:
                for key, value in node.items():
                    if key == 'evidence_refs':
                        used.update(value)
                    else:
                        visit(value)
            elif type(node) is list:
                for child in node:
                    visit(child)
        visit(p['decision_record'])
        if used != set(refs):
            raise RunnerError('decision evidence closure mismatch')
        return digest('Proposal', p)

    def _run(self, action, operation):
        with self._lock, self._db:
            state = self.snapshot()
            if state['tick'] >= self._policy['operation_budget']:
                raise RunnerError('operation budget exhausted')
            state['tick'] += 1
            changed = deepcopy(state)
            try:
                result = operation(changed)
            except (ValueError, TypeError, KeyError) as exc:
                state['journal'].append(dict(tick=state['tick'], action=action, result='REJECTED', reason=str(exc)))
                self._db.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(state),))
                # Commit the metered rejection before re-raising outside the transaction.
                error = RunnerError(str(exc))
            else:
                changed['journal'].append(dict(tick=changed['tick'], action=action, result='ACCEPTED',
                                                result_digest=digest('Result', result)))
                self._db.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(changed),))
                error = None
        if error:
            raise error
        return deepcopy(result)

    def _make_receipt(self, p, kind, actor, state, challenge='NONE'):
        receipt = dict(schema='cortac.scratch.receipt.v1', id='r' + str(state['tick']),
                       case_id=p['case_id'], proposal_digest=digest('Proposal', p),
                       policy_digest=p['policy_digest'], epoch=p['epoch'], expected_revision=p['expected_revision'],
                       operation=p['operation'], evidence_digest=digest('EvidenceInventory', p['evidence']),
                       kind=kind, actor=actor, challenge_digest=challenge, result='PASS', scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
        state['receipts'][receipt['id']] = receipt
        return receipt

    def issue(self, proposal, kind, actor):
        """Issue a harness receipt after resolving the pinned bytes, never a signature."""
        p = deepcopy(proposal)
        def issue(state):
            self._proposal(p, state)
            if kind not in ('ASSESSMENT', 'APPROVAL', 'AUTHORIZATION'):
                raise RunnerError('unsupported receipt kind')
            role = {'ASSESSMENT': 'assessor', 'APPROVAL': 'approver', 'AUTHORIZATION': 'authorizer'}[kind]
            self._actor(actor, role)
            self._independent(actor, [p['proposer']] + self._policy['excluded_ids'])
            if kind == 'APPROVAL' and actor not in self._policy['approval_ids']:
                raise RunnerError('actor outside frozen approval roll')
            return self._make_receipt(p, kind, actor, state)
        return self._run('issue_' + str(kind), issue)

    def _receipts(self, receipts, p, state):
        if type(receipts) is not list or not receipts:
            raise RunnerError('receipts required')
        seen = set(); actors = set(); groups = {}
        for receipt in receipts:
            exact(receipt, RECEIPT_FIELDS, 'receipt')
            identifier = receipt['id']
            if type(identifier) is not str or identifier in seen:
                raise RunnerError('duplicate/invalid receipt ID')
            seen.add(identifier)
            # Stored equality includes schema, scope and every typed field. bool != int is
            # separately blocked by digest equality over JSON, including true versus 1.
            if identifier not in state['receipts'] or digest('Receipt', receipt) != digest('Receipt', state['receipts'][identifier]):
                raise RunnerError('unissued or altered receipt')
            if receipt['proposal_digest'] != digest('Proposal', p):
                raise RunnerError('receipt proposal mismatch')
            if receipt['actor'] in actors:
                raise RunnerError('one actor cannot fill multiple checks')
            actors.add(receipt['actor'])
            groups.setdefault(receipt['kind'], []).append(receipt)
        for kind in ('ASSESSMENT', 'AUTHORIZATION'):
            if len(groups.get(kind, [])) != 1:
                raise RunnerError('exactly one ' + kind + ' required')
        approvals = groups.get('APPROVAL', [])
        if len(approvals) < self._policy['approval_threshold']:
            raise RunnerError('frozen approval threshold not met')
        allowed = {'ASSESSMENT', 'APPROVAL', 'AUTHORIZATION'} | ({'REVIEW'} if p['operation'] == 'REPAIR' else set())
        if set(groups) != allowed or (p['operation'] == 'REPAIR' and len(groups['REVIEW']) != 1):
            raise RunnerError('receipt kind inventory mismatch')
        selected = list(actors) + [p['proposer']]
        for actor in actors:
            self._independent(actor, [other for other in selected if other != actor] + self._policy['excluded_ids'])
        return groups, selected

    def commit(self, proposal, receipts, mandate_id, executor):
        p, receipts = deepcopy(proposal), deepcopy(receipts)
        def commit(state):
            pd = self._proposal(p, state)
            if state['pending_audit'] is not None:
                raise RunnerError('previous effect requires audit')
            groups, participants = self._receipts(receipts, p, state)
            self._actor(executor, 'executor')
            self._independent(executor, participants + self._policy['excluded_ids'])
            if type(mandate_id) is not str or mandate_id not in self._mandates:
                raise RunnerError('unknown mandate')
            grant = self._mandates[mandate_id]
            authorizer = groups['AUTHORIZATION'][0]['actor']
            if grant['proposal_digest'] != pd or grant['authorizer'] != authorizer or state['tick'] >= grant['expires_tick']:
                raise RunnerError('mandate mismatch or expired')
            if mandate_id in state['used_mandates']:
                raise RunnerError('mandate already consumed')
            unresolved = [c for c in state['challenges'].values() if c['resolution'] is None]
            resolved_id = None
            if p['operation'] == 'REPAIR':
                review = groups['REVIEW'][0]
                matching = [c for c in unresolved if c['digest'] == review['challenge_digest']]
                if len(matching) != 1 or len(unresolved) != 1:
                    raise RunnerError('repair must resolve exactly one hold; unrelated holds persist')
                self._independent(review['actor'], state['participants'] + [a for a in participants if a != review['actor']] + [executor])
                self._independent(authorizer, state['participants'])
                resolved_id = matching[0]['id']
            elif unresolved:
                raise RunnerError('unresolved challenge hold')
            effect = dict(schema='cortac.scratch.effect.v1', id='effect-' + str(state['revision'] + 1),
                          case_id=p['case_id'], policy_digest=self._policy_digest, proposal_digest=pd,
                          mandate_digest=digest('Mandate', grant), receipt_digests=[digest('Receipt', r) for r in receipts],
                          before_revision=state['revision'], after_revision=state['revision'] + 1,
                          before_value=state['value'], after_value=p['value'], executor=executor,
                          repair_challenge_id=resolved_id, scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
            state['revision'] += 1; state['value'] = p['value']
            state['used_mandates'].append(mandate_id); state['effects'].append(effect)
            state['participants'] = sorted(set(state['participants'] + participants + [executor]))
            state['pending_audit'] = effect['id']
            return effect
        return self._run('commit', commit)

    def audit(self, effect, actor):
        effect = deepcopy(effect)
        def audit(state):
            self._actor(actor, 'auditor')
            self._independent(actor, state['participants'] + self._policy['excluded_ids'])
            if not state['effects'] or digest('Effect', effect) != digest('Effect', state['effects'][-1]) or state['pending_audit'] != effect['id']:
                raise RunnerError('audit effect not current')
            if state['value'] != effect['after_value'] or state['revision'] != effect['after_revision']:
                raise RunnerError('audit state mismatch')
            state['pending_audit'] = None
            if effect['repair_challenge_id'] is not None:
                state['challenges'][effect['repair_challenge_id']]['resolution'] = digest('Effect', effect)
            state['participants'] = sorted(set(state['participants'] + [actor]))
            return dict(schema='cortac.scratch.audit.v1', effect_digest=digest('Effect', effect),
                        observed_value=state['value'], observed_revision=state['revision'], auditor=actor,
                        scope=SCOPE, result='MATCHED_SCRATCH_STATE', provenance='SYNTHETIC_FIXTURE')
        return self._run('audit', audit)

    def challenge(self, identifier, claimant, effect, evidence_ids, reason):
        effect, evidence_ids = deepcopy(effect), deepcopy(evidence_ids)
        def challenge(state):
            text(identifier, 'challenge ID'); text(claimant, 'claimant'); text(reason, 'reason')
            if identifier in state['challenges'] or not state['effects'] or digest('Effect', effect) != digest('Effect', state['effects'][-1]):
                raise RunnerError('duplicate challenge or noncurrent effect')
            if type(evidence_ids) is not list or not evidence_ids or any(type(i) is not str or i not in self._evidence for i in evidence_ids) or len(set(evidence_ids)) != len(evidence_ids):
                raise RunnerError('challenge evidence unresolved/duplicate')
            record = dict(schema='cortac.scratch.challenge.v1', id=identifier, claimant=claimant,
                          case_id=self._policy['case_id'], effect_digest=digest('Effect', effect),
                          evidence=[dict(id=i, digest=digest('Evidence', self._evidence[i])) for i in sorted(evidence_ids)],
                          reason=reason, scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
            stored = dict(record, digest=digest('Challenge', record), resolution=None)
            state['challenges'][identifier] = stored
            return stored
        return self._run('challenge', challenge)

    def review(self, challenge_id, proposal, actor):
        p = deepcopy(proposal)
        def review(state):
            self._proposal(p, state); self._actor(actor, 'reviewer')
            self._independent(actor, state['participants'] + [p['proposer']] + self._policy['excluded_ids'])
            if p['operation'] != 'REPAIR' or type(challenge_id) is not str or challenge_id not in state['challenges']:
                raise RunnerError('review requires known repair challenge')
            challenge = state['challenges'][challenge_id]
            if challenge['claimant'] not in self._principals:
                raise RunnerError('claimant controller unknown; hold preserved')
            self._independent(actor, [challenge['claimant']])
            if challenge['resolution'] is not None:
                raise RunnerError('challenge already resolved')
            refs = {(r['id'], r['digest']) for r in p['evidence']}
            if not all((r['id'], r['digest']) in refs for r in challenge['evidence']):
                raise RunnerError('repair omits challenge evidence')
            return self._make_receipt(p, 'REVIEW', actor, state, challenge['digest'])
        return self._run('review', review)
