"""Bounded offline amendment replay. No signatures, live grants, or execution.

All identities, domains, evidence, timestamps and approval statements are supplied
and unverified. A local lock models CAS; it is not a distributed reference monitor.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading

SCHEMA = json.loads((Path(__file__).parent / 'data' / 'amendment_records.schema.json').read_text(encoding='utf-8'))


class AmendmentError(ValueError):
    """A malformed record, missing prerequisite, or stale transition."""


def _validate(value, schema, path='$'):
    if '$ref' in schema:
        schema = SCHEMA['$defs'][schema['$ref'].split('/')[-1]]
    kind = schema['type']
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if type(value) is not types[kind]:
        raise AmendmentError(path + ': expected ' + kind)
    if 'const' in schema and value != schema['const']:
        raise AmendmentError(path + ': wrong constant')
    if 'enum' in schema and value not in schema['enum']:
        raise AmendmentError(path + ': unsupported value')
    if kind == 'object':
        if set(value) != set(schema['required']):
            raise AmendmentError(path + ': missing or unknown fields')
        for key, child in value.items():
            _validate(child, schema['properties'][key], path + '.' + key)
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0):
            raise AmendmentError(path + ': insufficient entries')
        if schema.get('uniqueItems') and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise AmendmentError(path + ': duplicate entries')
        for child in value:
            _validate(child, schema['items'], path + '[]')
    elif kind == 'integer' and value < schema.get('minimum', 0):
        raise AmendmentError(path + ': below minimum')
    elif kind == 'string':
        if len(value) < schema.get('minLength', 0):
            raise AmendmentError(path + ': empty string')
        if schema.get('pattern'):
            import re
            if re.fullmatch(schema['pattern'], value) is None:
                raise AmendmentError(path + ': invalid format')


def validate_record(kind, record):
    if kind not in SCHEMA['$defs']:
        raise AmendmentError('unknown record kind')
    _validate(record, SCHEMA['$defs'][kind])


def digest(kind, record):
    """Domain-separated canonical-JSON SHA256; this is not a signature."""
    validate_record(kind, record)
    body = json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(('cortac.amendments.v1/' + kind + '\0' + body).encode('utf-8')).hexdigest()


def _policy(policy):
    validate_record('Policy', policy)
    rules = policy['rules']
    actors = {a['id']: a['domain'] for a in rules['actors']}
    if len(actors) != len(rules['actors']):
        raise AmendmentError('duplicate actor identity')
    for field in ('decisionmakers', 'registrars', 'external_principals', 'appeal_authorities', 'replacement_authorities'):
        if not set(rules[field]) <= actors.keys():
            raise AmendmentError('unknown actor in ' + field)
    if rules['quorum'] > len({actors[a] for a in rules['decisionmakers']}):
        raise AmendmentError('quorum exceeds declared decision domains')
    return rules, actors


class AmendmentReplay:
    """One-process synthetic timeline. New instances are independent simulations.

    No API makes a real capability. `is_current` only tests supplied epoch/digest
    equality. All boundary code/config must be committed into policy `content`.
    This model cannot discover omitted dependencies, forged attestations, or host
    writes; it does not authenticate clocks, identities, signatures or evidence.
    """
    def __init__(self, policy, epoch=1):
        _policy(policy)
        if type(epoch) is not int or epoch < 1:
            raise AmendmentError('invalid epoch')
        self._policy = deepcopy(policy)
        self._epoch = epoch
        self._lock = threading.RLock()
        self._registrations = {}
        self._events = []
        self._challenges = {}
        self._invalidated = set()
        self._last_time = 0

    def state(self):
        with self._lock:
            return {'policy_digest': digest('Policy', self._policy), 'epoch': self._epoch,
                    'authority': 'NONE', 'execution_enabled': False,
                    'controller_closure': 'SUPPLIED_UNVERIFIED'}

    def events(self):
        with self._lock:
            return deepcopy(self._events)

    def _time(self, now):
        if type(now) is not int or now < self._last_time:
            raise AmendmentError('invalid or regressing supplied time')

    def _check(self, proposal, approval, procedure, registrar, now):
        validate_record('Proposal', proposal)
        validate_record('Approval', approval)
        validate_record('Procedure', procedure)
        rules, domains = _policy(self._policy)
        _policy(proposal['new_policy'])
        for field in ('society_id', 'attempt_id'):
            if proposal['new_policy'][field] != self._policy[field]:
                raise AmendmentError('amendment cannot change society or attempt identity')
        state = self.state()
        basis = (state['policy_digest'], state['epoch'])
        if basis in self._invalidated or any(v['disposition'] != 'RESOLVED' for v in self._challenges.get(basis, {}).values()):
            raise AmendmentError('current policy epoch revoked or challenge unresolved')
        if (proposal['old_policy_digest'], proposal['expected_epoch']) != (state['policy_digest'], state['epoch']):
            raise AmendmentError('stale policy or epoch')
        if proposal['new_policy_digest'] != digest('Policy', proposal['new_policy']):
            raise AmendmentError('new policy digest mismatch')
        if proposal['new_policy_digest'] == proposal['old_policy_digest']:
            raise AmendmentError('no policy change')
        if proposal['proposer'] not in domains:
            raise AmendmentError('unknown proposer')
        pd = digest('Proposal', proposal)
        if approval['proposal_digest'] != pd or procedure['proposal_digest'] != pd:
            raise AmendmentError('evidence bound to another proposal')
        if approval['decision'] != 'APPROVE':
            raise AmendmentError('no affirmative decision approval')
        voters = approval['decisionmakers']
        if not set(voters) <= set(rules['decisionmakers']):
            raise AmendmentError('unauthorized decisionmaker')
        if len({domains[v] for v in voters}) < rules['quorum']:
            raise AmendmentError('insufficient distinct decision domains')
        if set(approval['external_principals']) != set(rules['external_principals']):
            raise AmendmentError('missing or unauthorized external principal approval')
        approvers = voters + approval['external_principals']
        if registrar not in rules['registrars']:
            raise AmendmentError('unauthorized registrar under current rules')
        if domains[registrar] in {domains[x] for x in [proposal['proposer']] + approvers}:
            raise AmendmentError('registrar conflicts with proposal or approval')
        if domains[proposal['proposer']] in {domains[x] for x in voters}:
            raise AmendmentError('proposer supplies decisive decision review')
        if not procedure['conflicts_cleared'] or not procedure['challenge_inventory_complete']:
            raise AmendmentError('unresolved conflicts or incomplete challenge inventory')
        if not procedure['mandatory_checks_passed']:
            raise AmendmentError('mandatory procedural check failed or unknown')
        if not (proposal['submitted_at'] <= procedure['notice_at'] <= approval['issued_at'] <= now):
            raise AmendmentError('invalid notice or approval chronology')
        earliest = procedure['notice_at'] + rules['notice_period'] + rules['challenge_period']
        if not (earliest <= procedure['review_closed_at'] <= now <= proposal['expires_at']):
            raise AmendmentError('notice/challenge interval open or proposal expired')
        if not (procedure['review_closed_at'] <= proposal['activate_at'] <= proposal['expires_at']):
            raise AmendmentError('activation time outside reviewed validity window')
        ids = [c['id'] for c in procedure['challenges']]
        if len(ids) != len(set(ids)):
            raise AmendmentError('duplicate challenge id')
        for challenge in procedure['challenges']:
            if challenge['disposition'] != 'RESOLVED':
                raise AmendmentError('unresolved challenge or stay')
            reviewer = challenge['reviewer']
            if reviewer not in rules['appeal_authorities']:
                raise AmendmentError('unauthorized challenge reviewer')
            if domains[reviewer] in {domains[x] for x in [registrar, proposal['proposer']] + approvers}:
                raise AmendmentError('conflicted challenge reviewer')
        return pd

    def register(self, proposal, approval, procedure, registrar, now):
        """Affirmative procedural check, separate from decision approval.

        Failure raises with a reason and creates no certificate. See refuse() for
        an explicitly recorded reasoned refusal; elapsed deadlines never approve.
        """
        with self._lock:
            self._time(now)
            proposal, approval, procedure = deepcopy((proposal, approval, procedure))
            pd = self._check(proposal, approval, procedure, registrar, now)
            rules = self._policy['rules']
            if now > proposal['submitted_at'] + rules['registrar_deadline']:
                raise AmendmentError('registrar deadline exceeded; independent appeal/replacement required')
            cert = {'schema': 'cortac.amendment.registration.v1', 'proposal_digest': pd,
                    'approval_digest': digest('Approval', approval), 'procedure_digest': digest('Procedure', procedure),
                    'registrar': registrar, 'registered_at': now, 'old_policy_digest': proposal['old_policy_digest'],
                    'new_policy_digest': proposal['new_policy_digest'], 'expected_epoch': proposal['expected_epoch'],
                    'activate_at': proposal['activate_at'], 'expires_at': proposal['expires_at'],
                    'status': 'SYNTHETICALLY_REGISTERED', 'authority': 'NONE', 'execution_enabled': False}
            key = digest('Registration', cert)
            self._last_time = now
            self._registrations[key] = (deepcopy(cert), proposal, approval, procedure)
            self._events.append({'kind': 'registration', 'record': deepcopy(cert)})
            return deepcopy(cert)

    def activate(self, certificate, now):
        """Under one lock, revalidate stored evidence and CAS old digest + epoch.

        Only this instance's registered exact certificate can advance its local
        timeline. Duplicate/replayed or concurrently stale activation is rejected.
        """
        with self._lock:
            self._time(now)
            certificate = deepcopy(certificate)
            key = digest('Registration', certificate)
            if key not in self._registrations:
                raise AmendmentError('unknown or changed local registration')
            cert, proposal, approval, procedure = self._registrations[key]
            basis = (cert['old_policy_digest'], cert['expected_epoch'])
            if basis in self._invalidated or any(v['disposition'] != 'RESOLVED' for v in self._challenges.get(basis, {}).values()):
                raise AmendmentError('registration revoked or current challenge unresolved')
            self._check(proposal, approval, procedure, cert['registrar'], now)
            if now < cert['activate_at']:
                raise AmendmentError('activation not yet due')
            old = self.state()
            self._last_time = now
            self._policy = deepcopy(proposal['new_policy'])
            self._epoch += 1
            receipt = {'schema': 'cortac.amendment.activation.v1', 'registration_digest': key,
                       'old_policy_digest': old['policy_digest'], 'new_policy_digest': self.state()['policy_digest'],
                       'old_epoch': old['epoch'], 'new_epoch': self._epoch, 'activated_at': now,
                       'status': 'SYNTHETICALLY_ACTIVATED', 'authority': 'NONE', 'execution_enabled': False}
            validate_record('Activation', receipt)
            self._events.append({'kind': 'activation', 'record': deepcopy(receipt)})
            return receipt

    def refuse(self, proposal, registrar, reason, evidence_refs, now):
        """Record refusal/deadline route; not a veto, approval, or appeal decision."""
        with self._lock:
            self._time(now)
            validate_record('Proposal', proposal)
            rules, _ = _policy(self._policy)
            if registrar not in rules['registrars']:
                raise AmendmentError('unauthorized registrar')
            if (proposal['old_policy_digest'], proposal['expected_epoch']) != (self.state()['policy_digest'], self._epoch):
                raise AmendmentError('stale refusal basis')
            if now < proposal['submitted_at']:
                raise AmendmentError('refusal precedes submission')
            record = {'schema': 'cortac.amendment.refusal.v1', 'proposal_digest': digest('Proposal', proposal),
                      'registrar': registrar, 'reason': reason, 'evidence_refs': evidence_refs, 'issued_at': now,
                      'deadline': proposal['submitted_at'] + rules['registrar_deadline'],
                      'appeal_authorities': rules['appeal_authorities'], 'replacement_authorities': rules['replacement_authorities'],
                      'authority': 'NONE', 'execution_enabled': False}
            validate_record('Refusal', record)
            self._last_time = now
            self._events.append({'kind': 'refusal', 'record': deepcopy(record)})
            return deepcopy(record)

    def challenge(self, certificate, challenge_id, disposition, actor, reason, evidence_refs, now):
        """Append local challenge state; independent current-policy review resolves.

        OPEN/STAY conservatively hold ALL amendments in the current policy epoch; supplied standing is not verified.
        A production intake must provide authenticated, timely challenge freshness.
        """
        with self._lock:
            self._time(now)
            key = digest('Registration', certificate)
            if key not in self._registrations:
                raise AmendmentError('unknown local registration')
            cert, proposal, approval, _ = self._registrations[key]
            if not self.is_current(cert['old_policy_digest'], cert['expected_epoch']):
                raise AmendmentError('stale challenge basis')
            record = {'schema': 'cortac.amendment.challenge.v1', 'registration_digest': key,
                      'challenge_id': challenge_id, 'disposition': disposition, 'actor': actor,
                      'reason': reason, 'evidence_refs': evidence_refs, 'issued_at': now,
                      'authority': 'NONE', 'execution_enabled': False}
            validate_record('ChallengeUpdate', record)
            rules, domains = _policy(self._policy)
            basis = (cert['old_policy_digest'], cert['expected_epoch'])
            involved = {domains[x] for x in [cert['registrar'], proposal['proposer']] + approval['decisionmakers'] + approval['external_principals']}
            previous = self._challenges.get(basis, {}).get(challenge_id)
            if previous:
                involved |= previous['involved_domains']
            if disposition == 'RESOLVED':
                if actor not in rules['appeal_authorities'] or domains[actor] in involved:
                    raise AmendmentError('resolution needs independent current appeal authority')
                if previous is None:
                    raise AmendmentError('no pending local challenge to resolve')
            self._last_time = now
            self._challenges.setdefault(basis, {})[challenge_id] = {'disposition': disposition, 'involved_domains': involved}
            self._events.append({'kind': 'challenge', 'record': deepcopy(record)})
            return deepcopy(record)

    def invalidate(self, certificate, reason, now):
        """Conservative epoch-wide local revocation input; never grants authority."""
        with self._lock:
            self._time(now)
            key = digest('Registration', certificate)
            if key not in self._registrations or type(reason) is not str or not reason:
                raise AmendmentError('unknown registration or missing reason')
            cert = self._registrations[key][0]
            if not self.is_current(cert['old_policy_digest'], cert['expected_epoch']):
                raise AmendmentError('stale invalidation basis')
            record = {'schema': 'cortac.amendment.invalidation.v1', 'registration_digest': key,
                      'old_policy_digest': cert['old_policy_digest'], 'expected_epoch': cert['expected_epoch'],
                      'reason': reason, 'issued_at': now, 'authority': 'NONE', 'execution_enabled': False}
            validate_record('Invalidation', record)
            self._last_time = now
            self._invalidated.add((cert['old_policy_digest'], cert['expected_epoch']))
            self._events.append({'kind': 'invalidation', 'record': record})
            return deepcopy(record)

    def is_current(self, policy_digest, epoch):
        """Synthetic freshness comparison ONLY, never permission to execute."""
        with self._lock:
            return type(epoch) is int and (policy_digest, epoch) == (self.state()['policy_digest'], self._epoch)
