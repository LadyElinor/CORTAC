"""Bounded offline amendment replay. No signatures, live grants, or execution.

All identities, domains, evidence, timestamps and approval statements are supplied
and unverified. A local lock models CAS; it is not a distributed reference monitor.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from .decision_records import validate_decision_record, validate_protected_limits, require_preserved_limits
from .io import InputError
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
        if len(value) < schema.get('minLength', 0) or (schema.get('minLength', 0) >= 1 and not value.strip()):
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
    return hashlib.sha256(('cortac.amendments.v2/' + kind + '\0' + body).encode('utf-8')).hexdigest()


def _policy(policy):
    validate_record('Policy', policy)
    rules = policy['rules']
    actors = {a['id']: a['domain'] for a in rules['actors']}
    if len(actors) != len(rules['actors']):
        raise AmendmentError('duplicate actor identity')
    for field in ('decisionmakers', 'registrars', 'external_principals', 'appeal_authorities', 'replacement_authorities', 'replacement_registrars'):
        if not set(rules[field]) <= actors.keys():
            raise AmendmentError('unknown actor in ' + field)
    if rules['quorum'] > len({actors[a] for a in rules['decisionmakers']}):
        raise AmendmentError('quorum exceeds declared decision domains')
    try:
        validate_protected_limits(policy['protected_limits'])
    except InputError as exc:
        raise AmendmentError(str(exc)) from exc
    if rules['repair_resource_cost'] > rules['repair_resource_limit']:
        raise AmendmentError('repair resource cost exceeds old-rule resource limit')
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
        self._invalidated = {}
        self._revoked_approvals = set()
        self._submissions = {}
        self._refusals = {}
        self._deadline_refused = set()
        self._complaints = {}
        self._reviews = {}
        self._grant_reservations = {}
        self._grants = {}
        self._history_domains = {}
        self._hold_generation = {}
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

    def _check(self, proposal, approval, procedure, registrar, now, repair=None):
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
        self._check_holds(basis, repair)
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
        try:
            require_preserved_limits(self._policy['protected_limits'], proposal['new_policy']['protected_limits'])
            if not validate_decision_record(approval['decision_record'], self._policy['protected_limits']):
                raise AmendmentError('protected limit assessment failed or unknown')
        except InputError as exc:
            raise AmendmentError(str(exc)) from exc
        if digest('Approval', approval) in self._revoked_approvals:
            raise AmendmentError('approval was revoked; fresh affirmative evidence required')
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
        if registrar not in (rules['replacement_registrars'] if repair else rules['registrars']):
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

    def _basis(self):
        return digest('Policy', self._policy), self._epoch

    @staticmethod
    def _record(tag, **fields):
        return {'schema': 'cortac.amendment.' + tag + '.v2', **fields,
                'authority': 'NONE', 'execution_enabled': False}

    def _append(self, kind, record):
        self._events.append({'kind': kind, 'record': deepcopy(record)})

    def _proposal(self, proposal, now):
        validate_record('Proposal', proposal)
        _policy(proposal['new_policy'])
        if (proposal['old_policy_digest'], proposal['expected_epoch']) != self._basis():
            raise AmendmentError('stale policy or epoch')
        if any(proposal['new_policy'][f] != self._policy[f] for f in ('society_id', 'attempt_id')):
            raise AmendmentError('amendment cannot change society or attempt identity')
        if proposal['new_policy_digest'] != digest('Policy', proposal['new_policy']):
            raise AmendmentError('new policy digest mismatch')
        if proposal['new_policy_digest'] == proposal['old_policy_digest']:
            raise AmendmentError('no policy change')
        if proposal['proposer'] not in {a['id'] for a in self._policy['rules']['actors']}:
            raise AmendmentError('unknown proposer')
        if not proposal['submitted_at'] <= now <= proposal['expires_at']:
            raise AmendmentError('proposal not submitted or expired')
        if not proposal['submitted_at'] <= proposal['activate_at'] <= proposal['expires_at']:
            raise AmendmentError('invalid proposal chronology')
        return digest('Proposal', proposal)

    def _participants(self, proposal, registrar, approval=None):
        _, domains = _policy(self._policy)
        actors = [proposal['proposer'], registrar]
        if approval is not None:
            actors += approval['decisionmakers'] + approval['external_principals']
        if any(a not in domains for a in actors):
            raise AmendmentError('unknown involved actor')
        return {domains[a] for a in actors}

    def _new_hold(self):
        basis = self._basis()
        self._hold_generation[basis] = self._hold_generation.get(basis, 0) + 1

    def _check_holds(self, basis, repair=None):
        exempt_invalidation = repair['source_digest'] if repair and repair['remedy'] == 'REPAIR_INVALIDATION' else None
        if any(key != exempt_invalidation for key in self._invalidated.get(basis, {})):
            raise AmendmentError('current policy epoch has unrelated invalidation')
        if any(v['record']['disposition'] != 'RESOLVED' for v in self._challenges.get(basis, {}).values()):
            raise AmendmentError('current policy epoch challenge unresolved')
        exempt_complaint = repair['complaint_digest'] if repair else None
        if any(v['record']['disposition'] != 'RESOLVED' and digest('Complaint', v['record']) != exempt_complaint
               for (b, _), v in self._complaints.items() if b == basis):
            raise AmendmentError('current policy epoch complaint unresolved')

    def _submission(self, proposal, registrar, now):
        pd = self._proposal(proposal, now)
        rules = self._policy['rules']
        if registrar not in rules['registrars']:
            raise AmendmentError('unauthorized original registrar')
        existing = self._submissions.get(pd)
        if existing:
            return existing['record']
        record = self._record('submission', proposal_digest=pd, old_policy_digest=proposal['old_policy_digest'],
                              expected_epoch=proposal['expected_epoch'], registrar=registrar,
                              submitted_at=proposal['submitted_at'], recorded_at=now,
                              deadline=proposal['submitted_at'] + rules['registrar_deadline'])
        validate_record('Submission', record)
        self._submissions[pd] = {'record': record, 'proposal': deepcopy(proposal)}
        self._history_domains.setdefault(self._basis(), set()).update(self._participants(proposal, registrar))
        self._append('submission', record)
        return record

    def submit(self, proposal, registrar, now):
        """Track a case before approval/registration, without granting anything."""
        with self._lock:
            self._time(now)
            proposal = deepcopy(proposal)
            record = self._submission(proposal, registrar, now)
            self._last_time = now
            return deepcopy(record)

    def _refusal(self, proposal, registrar, reason, evidence_refs, now):
        record = self._record('refusal', proposal_digest=digest('Proposal', proposal), registrar=registrar,
                              reason=reason, evidence_refs=deepcopy(evidence_refs), issued_at=now,
                              deadline=proposal['submitted_at'] + self._policy['rules']['registrar_deadline'],
                              appeal_authorities=self._policy['rules']['appeal_authorities'],
                              replacement_authorities=self._policy['rules']['replacement_authorities'])
        validate_record('Refusal', record)
        return record

    def _record_deadline(self, proposal, registrar, now):
        pd = digest('Proposal', proposal)
        if pd in self._deadline_refused:
            return None
        record = self._refusal(proposal, registrar, 'Registrar deadline exceeded; independent appeal and scoped replacement required.',
                               ['supplied-clock:' + str(now), 'proposal:' + pd], now)
        self._refusals[digest('Refusal', record)] = deepcopy(record)
        self._deadline_refused.add(pd)
        self._append('refusal', record)
        return record

    def tick(self, now):
        """Explicit supplied clock tick; expiry records escalation, never assent."""
        with self._lock:
            self._time(now)
            start = len(self._events)
            registered = {c[0]['proposal_digest'] for c in self._registrations.values()}
            for pd, item in self._submissions.items():
                r = item['record']
                if (r['old_policy_digest'], r['expected_epoch']) == self._basis() and pd not in registered and now > r['deadline']:
                    self._record_deadline(item['proposal'], r['registrar'], now)
            for (basis, _), item in self._complaints.items():
                r = item['record']
                if basis == self._basis() and r['disposition'] == 'OPEN' and now > r['deadline']:
                    r.update(disposition='ESCALATION_REQUIRED', revision=r['revision'] + 1, issued_at=now)
                    self._new_hold()
                    self._append('complaint', r)
            for item in self._challenges.get(self._basis(), {}).values():
                r = item['record']
                if r['disposition'] in ('OPEN', 'STAY') and now > r['deadline']:
                    r.update(disposition='ESCALATION_REQUIRED', revision=r['revision'] + 1, issued_at=now)
                    self._new_hold()
                    self._append('challenge', r)
            self._last_time = now
            return deepcopy(self._events[start:])

    def _certificate(self, proposal, approval, procedure, registrar, now, repair_digest=''):
        cert = self._record('registration', proposal_digest=digest('Proposal', proposal),
                            approval_digest=digest('Approval', approval), procedure_digest=digest('Procedure', procedure),
                            registrar=registrar, registered_at=now, old_policy_digest=proposal['old_policy_digest'],
                            new_policy_digest=proposal['new_policy_digest'], expected_epoch=proposal['expected_epoch'],
                            activate_at=proposal['activate_at'], expires_at=proposal['expires_at'],
                            status='SYNTHETICALLY_REGISTERED', repair_review_digest=repair_digest)
        key = digest('Registration', cert)
        self._registrations[key] = deepcopy((cert, proposal, approval, procedure))
        self._history_domains.setdefault(self._basis(), set()).update(self._participants(proposal, registrar, approval))
        self._append('registration', cert)
        return cert

    def register(self, proposal, approval, procedure, registrar, now):
        """Validate, then register; a valid late attempt records a refusal and raises.

        Other failed inputs have no state or clock effect. Expiry is never approval.
        """
        with self._lock:
            self._time(now)
            proposal, approval, procedure = deepcopy((proposal, approval, procedure))
            self._proposal(proposal, now)
            self._check(proposal, approval, procedure, registrar, now)
            self._submission(proposal, registrar, now)
            if now > proposal['submitted_at'] + self._policy['rules']['registrar_deadline']:
                self._history_domains.setdefault(self._basis(), set()).update(self._participants(proposal, registrar, approval))
                self._record_deadline(proposal, registrar, now)
                self._last_time = now
                raise AmendmentError('registrar deadline exceeded; independent appeal/replacement required')
            cert = self._certificate(proposal, approval, procedure, registrar, now)
            self._last_time = now
            return deepcopy(cert)

    def refuse(self, proposal, registrar, reason, evidence_refs, now):
        with self._lock:
            self._time(now)
            proposal = deepcopy(proposal)
            self._proposal(proposal, now)
            if registrar not in self._policy['rules']['registrars']:
                raise AmendmentError('unauthorized registrar')
            record = self._refusal(proposal, registrar, reason, evidence_refs, now)
            self._submission(proposal, registrar, now)
            self._refusals[digest('Refusal', record)] = deepcopy(record)
            self._append('refusal', record)
            self._last_time = now
            return deepcopy(record)

    def _stored_submission(self, submission):
        key = digest('Submission', submission)
        item = self._submissions.get(submission['proposal_digest'])
        if not item or digest('Submission', item['record']) != key:
            raise AmendmentError('unknown or changed local submission')
        if (submission['old_policy_digest'], submission['expected_epoch']) != self._basis():
            raise AmendmentError('stale submission')
        return key, item

    def complain(self, submission, complaint_id, actor, reason, evidence_refs, now, source=None):
        """Affected nonmembers may lodge supplied complaints before registration.

        Source is an exact local refusal/invalidation, or defaults to submission.
        Reusing an ID creates a new revision and cannot erase conflict history.
        """
        with self._lock:
            self._time(now)
            submission = deepcopy(submission)
            skey, item = self._stored_submission(submission)
            source_kind, source_record = 'Submission', submission
            if source is not None:
                if type(source) is not dict:
                    raise AmendmentError('malformed complaint source')
                source = deepcopy(source)
                if source.get('schema') == 'cortac.amendment.refusal.v2':
                    source_kind = 'Refusal'
                    source_record = self._refusals.get(digest('Refusal', source))
                    if not source_record or source_record['proposal_digest'] != submission['proposal_digest']:
                        raise AmendmentError('refusal not bound to submitted complaint case')
                elif source.get('schema') == 'cortac.amendment.invalidation.v2':
                    source_kind = 'Invalidation'
                    source_record = self._invalidated.get(self._basis(), {}).get(digest('Invalidation', source))
                    if not source_record or self._registrations[source_record['registration_digest']][0]['proposal_digest'] != submission['proposal_digest']:
                        raise AmendmentError('invalidation not bound to submitted complaint case')
                else:
                    raise AmendmentError('unsupported complaint source')
            _validate(complaint_id, {'type': 'string', 'minLength': 1})
            previous = self._complaints.get((self._basis(), complaint_id))
            record = self._record('complaint', complaint_id=complaint_id, revision=previous['record']['revision'] + 1 if previous else 1,
                                  submission_digest=skey, source_kind=source_kind, source_digest=digest(source_kind, source_record),
                                  proposal_digest=submission['proposal_digest'], old_policy_digest=submission['old_policy_digest'],
                                  expected_epoch=submission['expected_epoch'], actor=actor, reason=reason,
                                  evidence_refs=deepcopy(evidence_refs), issued_at=now,
                                  deadline=now + self._policy['rules']['review_deadline'], disposition='OPEN')
            validate_record('Complaint', record)
            involved = self._participants(item['proposal'], submission['registrar']) | self._history_domains.get(self._basis(), set())
            if previous:
                involved |= previous['involved_domains']
            _, domains = _policy(self._policy)
            if actor in domains:
                involved.add(domains[actor])
            self._complaints[(self._basis(), complaint_id)] = {'record': record, 'source': deepcopy(source_record), 'involved_domains': involved}
            self._new_hold()
            self._append('complaint', record)
            self._last_time = now
            return deepcopy(record)

    def _current_complaint(self, complaint):
        key = digest('Complaint', complaint)
        item = self._complaints.get((self._basis(), complaint['complaint_id']))
        if not item or digest('Complaint', item['record']) != key:
            raise AmendmentError('unknown, stale or changed complaint revision')
        return key, item

    def resolve_complaint(self, complaint, reviewer, reason, evidence_refs, now):
        with self._lock:
            self._time(now)
            _, item = self._current_complaint(complaint)
            rules, domains = _policy(self._policy)
            involved = item['involved_domains'] | self._history_domains.get(self._basis(), set())
            if reviewer not in rules['appeal_authorities'] or domains[reviewer] in involved:
                raise AmendmentError('complaint resolution requires independent old-rule appeal authority')
            if item['record']['disposition'] == 'RESOLVED':
                raise AmendmentError('complaint already resolved')
            record = deepcopy(item['record'])
            record.update(revision=record['revision'] + 1, disposition='RESOLVED', actor=reviewer,
                          reason=reason, evidence_refs=deepcopy(evidence_refs), issued_at=now)
            validate_record('Complaint', record)
            item['record'] = record
            item['involved_domains'] = involved
            self._append('complaint', record)
            self._last_time = now
            return deepcopy(record)
    def _repair_inputs(self, complaint, proposal, approval, procedure, grant, reviewer,
                       replacement_authorizer, replacement_registrar, now):
        cd, item = self._current_complaint(complaint)
        validate_record('ResourceRemedyGrant', grant)
        validate_record('Approval', approval)
        validate_record('Procedure', procedure)
        known_grant = self._grants.get(grant['grant_id'])
        if known_grant is not None and known_grant != digest('ResourceRemedyGrant', grant):
            raise AmendmentError('grant identity already binds another exact record')
        rules, domains = _policy(self._policy)
        pd = self._proposal(proposal, now)
        if complaint['disposition'] != 'OPEN' or now > complaint['deadline']:
            raise AmendmentError('complaint review deadline expired; escalation required')
        remedy = 'REPAIR_INVALIDATION' if complaint['source_kind'] == 'Invalidation' else 'REPLACE_REGISTRATION'
        expected = {'complaint_digest': cd, 'source_digest': complaint['source_digest'],
                    'repair_proposal_digest': pd, 'old_policy_digest': self._basis()[0],
                    'expected_epoch': self._epoch, 'remedy': remedy}
        if any(grant[k] != v for k, v in expected.items()):
            raise AmendmentError('grant not bound to exact complaint, source, repair or old basis')
        if set(grant['external_principals']) != set(rules['external_principals']):
            raise AmendmentError('remedy grant lacks exact old external-principal authorization')
        if not rules['repair_resource_cost'] <= grant['resource_units'] <= rules['repair_resource_limit']:
            raise AmendmentError('grant resource budget insufficient or exceeds old-rule bound')
        if not complaint['issued_at'] <= grant['issued_at'] <= now <= grant['expires_at']:
            raise AmendmentError('grant not current for this complaint')
        if not grant['issued_at'] < grant['expires_at'] <= min(proposal['expires_at'], grant['issued_at'] + rules['repair_deadline']):
            raise AmendmentError('grant validity exceeds bounded case duration')
        if reviewer not in rules['appeal_authorities'] or replacement_authorizer not in rules['replacement_authorities']:
            raise AmendmentError('review or replacement authority not eligible under old rules')
        if replacement_registrar not in rules['replacement_registrars']:
            raise AmendmentError('substitute registrar not eligible under old rules')
        chosen = [reviewer, replacement_authorizer, replacement_registrar]
        if len({domains[a] for a in chosen}) != 3:
            raise AmendmentError('appeal, appointment and substitute registrar must be independent')
        involved = item['involved_domains'] | self._history_domains.get(self._basis(), set())
        involved |= self._participants(proposal, self._submissions[complaint['proposal_digest']]['record']['registrar'], approval)
        # A substitute's own prior certificate is permitted at activation, while
        # reviewer/appointing authority never become their own historical reviewer.
        if domains[reviewer] in involved or domains[replacement_authorizer] in involved:
            raise AmendmentError('historically conflicted review or replacement authority')
        source_registrar = self._submissions[complaint['proposal_digest']]['record']['registrar']
        source_involved = item['involved_domains'] | self._participants(proposal, source_registrar, approval)
        if domains[replacement_registrar] in source_involved:
            raise AmendmentError('substitute conflicts with original case or substantive approval')
        source_time = item['source'].get('issued_at', item['source'].get('recorded_at'))
        if not all(t > source_time for t in (proposal['submitted_at'], approval['issued_at'], procedure['notice_at'], procedure['review_closed_at'])):
            raise AmendmentError('repair requires freshly submitted proposal, approval and procedure after source record')
        context = {**expected, 'resource_units': rules['repair_resource_cost'],
                   'hold_generation': self._hold_generation.get(self._basis(), 0)}
        self._check(proposal, approval, procedure, replacement_registrar, now, context)
        return context

    def review_repair(self, complaint, proposal, approval, procedure, grant, reviewer,
                      replacement_authorizer, replacement_registrar, reason, evidence_refs, now):
        """Old-rule independent review and appointment for exactly one bounded case.

        The supplied grant separately affirms remedy authorization by all old
        external principals and a finite resource budget. Funding alone is not
        a remedy mandate. Nothing authenticates these offline declarations.
        """
        with self._lock:
            self._time(now)
            complaint, proposal, approval, procedure, grant = deepcopy((complaint, proposal, approval, procedure, grant))
            context = self._repair_inputs(complaint, proposal, approval, procedure, grant, reviewer,
                                          replacement_authorizer, replacement_registrar, now)
            record = self._record('repair-review', **context, approval_digest=digest('Approval', approval),
                                  procedure_digest=digest('Procedure', procedure), grant_digest=digest('ResourceRemedyGrant', grant),
                                  reviewer=reviewer, replacement_authorizer=replacement_authorizer,
                                  replacement_registrar=replacement_registrar, decision='AUTHORIZE_SCOPED_REPAIR',
                                  issued_at=now, expires_at=min(grant['expires_at'], complaint['deadline'],
                                                             now + self._policy['rules']['repair_deadline']),
                                  reason=reason, evidence_refs=deepcopy(evidence_refs))
            if not now <= proposal['activate_at'] <= record['expires_at']:
                raise AmendmentError('repair activation outside bounded review validity')
            key = digest('RepairReview', record)
            self._reviews[key] = deepcopy((record, complaint, proposal, approval, procedure, grant))
            self._grants[grant['grant_id']] = digest('ResourceRemedyGrant', grant)
            self._append('resource_remedy_grant', grant)
            self._append('repair_review', record)
            self._last_time = now
            return deepcopy(record)

    def _stored_review(self, review, now):
        key = digest('RepairReview', review)
        stored = self._reviews.get(key)
        if not stored:
            raise AmendmentError('unknown or changed local repair review')
        r, complaint, proposal, approval, procedure, grant = stored
        if r['hold_generation'] != self._hold_generation.get(self._basis(), 0):
            raise AmendmentError('new or reopened hold requires fresh repair review')
        if not r['issued_at'] <= now <= r['expires_at']:
            raise AmendmentError('repair review expired; escalation required')
        self._repair_inputs(complaint, proposal, approval, procedure, grant, r['reviewer'],
                            r['replacement_authorizer'], r['replacement_registrar'], now)
        return key, stored

    def register_replacement(self, review, now):
        """Reserve a grant once and issue one new certificate; no old assent needed."""
        with self._lock:
            self._time(now)
            key, stored = self._stored_review(review, now)
            r, _, proposal, approval, procedure, _ = stored
            gd = r['grant_digest']
            if gd in self._grant_reservations:
                raise AmendmentError('single-case resource grant already reserved or depleted')
            cert = self._certificate(proposal, approval, procedure, r['replacement_registrar'], now, key)
            reservation = self._record('resource-reservation', grant_digest=gd, review_digest=key,
                                       registration_digest=digest('Registration', cert), resource_units=r['resource_units'], reserved_at=now)
            validate_record('ResourceReservation', reservation)
            self._grant_reservations[gd] = deepcopy(reservation)
            self._append('resource_reservation', reservation)
            self._last_time = now
            return deepcopy(cert)

    def activate(self, certificate, now):
        """Recheck exact stored evidence and every current hold, then local CAS."""
        with self._lock:
            self._time(now)
            key = digest('Registration', certificate)
            if key not in self._registrations:
                raise AmendmentError('unknown or changed local registration')
            cert, proposal, approval, procedure = self._registrations[key]
            repair = None
            if cert['repair_review_digest']:
                stored = self._reviews[cert['repair_review_digest']]
                _, stored = self._stored_review(stored[0], now)
                repair = stored[0]
                reservation = self._grant_reservations.get(repair['grant_digest'])
                if not reservation or reservation['registration_digest'] != key:
                    raise AmendmentError('missing exact resource reservation')
            self._check(proposal, approval, procedure, cert['registrar'], now, repair)
            if now < cert['activate_at']:
                raise AmendmentError('activation not yet due')
            old = self.state()
            receipt = self._record('activation', registration_digest=key, old_policy_digest=old['policy_digest'],
                                   new_policy_digest=proposal['new_policy_digest'], old_epoch=old['epoch'],
                                   new_epoch=self._epoch + 1, activated_at=now, status='SYNTHETICALLY_ACTIVATED')
            validate_record('Activation', receipt)
            self._policy = deepcopy(proposal['new_policy'])
            self._epoch += 1
            self._last_time = now
            self._append('activation', receipt)
            return deepcopy(receipt)

    def challenge(self, certificate, challenge_id, disposition, actor, reason, evidence_refs, now):
        """Epoch-wide hold; past deadline requires escalation, never tacit assent."""
        with self._lock:
            self._time(now)
            key = digest('Registration', certificate)
            if key not in self._registrations:
                raise AmendmentError('unknown local registration')
            cert, proposal, approval, _ = self._registrations[key]
            if not self.is_current(cert['old_policy_digest'], cert['expected_epoch']):
                raise AmendmentError('stale challenge basis')
            rules, domains = _policy(self._policy)
            basis = self._basis()
            _validate(challenge_id, {'type': 'string', 'minLength': 1})
            previous = self._challenges.get(basis, {}).get(challenge_id)
            involved = self._participants(proposal, cert['registrar'], approval) | self._history_domains.get(basis, set())
            if previous:
                involved |= previous['involved_domains']
            if disposition == 'RESOLVED':
                if actor not in rules['appeal_authorities'] or domains[actor] in involved:
                    raise AmendmentError('resolution needs independent current appeal authority')
                if previous is None or previous['record']['disposition'] == 'RESOLVED':
                    raise AmendmentError('no pending local challenge to resolve')
            elif actor in domains:
                involved.add(domains[actor])
            record = self._record('challenge', registration_digest=key, challenge_id=challenge_id,
                                  disposition=disposition, actor=actor, reason=reason, evidence_refs=deepcopy(evidence_refs),
                                  issued_at=now, deadline=now + rules['review_deadline'],
                                  revision=previous['record']['revision'] + 1 if previous else 1)
            validate_record('ChallengeUpdate', record)
            self._challenges.setdefault(basis, {})[challenge_id] = {'record': record, 'involved_domains': involved}
            if disposition != 'RESOLVED':
                self._new_hold()
            self._append('challenge', record)
            self._last_time = now
            return deepcopy(record)

    def invalidate(self, certificate, reason, now, evidence_refs=None):
        """Immutable exact local revocation; records and old approvals stay revoked.

        Missing evidence is represented explicitly by an empty list, never invented.
        Recovery review binds the whole source record, including reason/evidence.
        """
        with self._lock:
            self._time(now)
            key = digest('Registration', certificate)
            if key not in self._registrations:
                raise AmendmentError('unknown registration')
            cert = self._registrations[key][0]
            if not self.is_current(cert['old_policy_digest'], cert['expected_epoch']):
                raise AmendmentError('stale invalidation basis')
            record = self._record('invalidation', registration_digest=key, old_policy_digest=cert['old_policy_digest'],
                                  expected_epoch=cert['expected_epoch'], reason=reason, evidence_refs=deepcopy([] if evidence_refs is None else evidence_refs),
                                  revision=len(self._invalidated.get(self._basis(), {})) + 1, issued_at=now)
            ik = digest('Invalidation', record)
            self._invalidated.setdefault(self._basis(), {})[ik] = deepcopy(record)
            for c, _, _, _ in self._registrations.values():
                if (c['old_policy_digest'], c['expected_epoch']) == self._basis():
                    self._revoked_approvals.add(c['approval_digest'])
            self._new_hold()
            self._append('invalidation', record)
            self._last_time = now
            return deepcopy(record)

    def is_current(self, policy_digest, epoch):
        """Synthetic freshness comparison only, never permission to execute."""
        with self._lock:
            return type(epoch) is int and (policy_digest, epoch) == self._basis()
