"""Proposed, opt-in OPS1 supplied trace checks. No fact finding or effect API.

All anchors, identities, chronology, completeness and evidence are caller supplied.
A consistent trace is neither an adjudication nor verified remedy effectiveness.
"""
from hashlib import sha256
import json
import re

VERSION = 'cortac.ops.trace.v1'
CONTEXT_VERSION = 'cortac.ops.context.v1'
DIMENSIONS = frozenset(('FUNDING', 'REMOVAL', 'APPOINTMENT', 'INFORMATION_ACCESS',
                        'RECUSAL', 'INDEPENDENT_ADVICE'))
STAGES = ('ORDERED', 'ACCEPTED', 'ATTEMPTED', 'OBSERVED', 'AUDITED', 'EFFECTIVENESS_REPORTED')
KINDS = frozenset(('ORIGINAL', 'PROVENANCE_CHECK', 'COUNTER', 'REASON', 'HEARING',
                  'DEPENDENCY', 'FUNDING', 'ACCOUNT', 'ORDERED', 'ACCEPTED',
                  'ATTEMPTED', 'OBSERVED', 'AUDITED', 'EFFECTIVENESS_REPORTED'))


class TraceError(ValueError):
    """Malformed or contradictory supplied trace; not an institutional ruling."""


def _list(spec, minimum=0):
    return (spec, minimum)


def _enum(*values):
    return frozenset(values)


def _shape(value, spec, path):
    if isinstance(spec, dict):
        if type(value) is not dict or set(value) != set(spec):
            raise TraceError(path + ': missing or unknown fields')
        for key in spec:
            _shape(value[key], spec[key], path + '.' + key)
    elif isinstance(spec, tuple):
        if type(value) is not list or not spec[1] <= len(value) <= 256:
            raise TraceError(path + ': invalid or oversized list')
        for i, item in enumerate(value):
            _shape(item, spec[0], path + '[' + str(i) + ']')
            if item in value[:i]:
                raise TraceError(path + ': duplicate entry')
    elif isinstance(spec, frozenset):
        if type(value) is not str or value not in spec:
            raise TraceError(path + ': unsupported value')
    elif spec == 'text':
        if type(value) is not str or not value.strip() or len(value) > 8192:
            raise TraceError(path + ': expected bounded nonblank text')
    elif spec == 'digest':
        if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
            raise TraceError(path + ': expected SHA256')
    elif spec == 'int':
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            raise TraceError(path + ': expected bounded nonnegative integer')
    elif spec == 'controller':
        if value is not None:
            _shape(value, 'text', path)
    else:
        raise RuntimeError('invalid internal schema')


TEXTS = _list('text', 1)
REF = dict(id='text', version='int', digest='digest')
BINDING = dict(case_id='text', policy_digest='digest', version='int', predecessor_digest='digest')
EVIDENCE = dict(id='text', version='int', digest='digest', kind=KINDS, observed_at='int')
CLAIM = dict(id='text', version='int', original_ids=TEXTS)
OBJECTION = dict(id='text', version='int', claim_id='text', claim_version='int', evidence_ids=TEXTS,
                 materiality=_enum('MATERIAL', 'NONMATERIAL'), reopened_at='int')
DEPENDENCY = dict(subject='text', dimension=DIMENSIONS, version='int', evidence_ids=TEXTS,
                  changed_at='int', status=_enum('CURRENT_REPORTED', 'UNKNOWN', 'CONFLICT'))
INJURY = dict(id='text', version='int')
CONTEXT = dict(schema=_enum(CONTEXT_VERSION), expected=BINDING, now='int',
    evidence=_list(EVIDENCE, 1), claims=_list(CLAIM, 1), objections=_list(OBJECTION),
    dependencies=_list(DEPENDENCY, 1), injuries=_list(INJURY), remedy_version='int',
    parties=TEXTS, principals=_list(dict(id='text', controller='controller'), 1))
PROVENANCE = dict(original_id='text', original_version='int', original_digest='digest', check_id='text', checker='text', checked_at='int', method='text')
RESOLUTION = dict(id='text', version='int', state=_enum('RESOLUTION_REPORTED', 'UNRESOLVED'),
                  resolved_at='int', evidence_ids=TEXTS, reason='text')
FINDING = dict(id='text', claim_version='int', evidence_refs=_list(REF, 1),
    provenance=_list(PROVENANCE, 1), resolutions=_list(RESOLUTION), decided_at='int',
    hearing=dict(status=_enum('HELD_REPORTED', 'NOT_WARRANTED', 'PENDING'),
                 evidence_ids=TEXTS, reason='text'), reason='text')
DEP_REF = dict(subject='text', dimension=DIMENSIONS, version='int', evidence_ids=TEXTS)
EVENT = dict(id='text', stage=_enum(*STAGES), previous_id='text', at='int',
             actor='text', evidence_ids=TEXTS)
RESIDUAL = dict(id='text', version='int', state=_enum('UNRESOLVED', 'REFERRED', 'CONTESTED',
    'WAIVED_REPORTED', 'REPAIRED_REPORTED'), observation_ids=_list('text'), audit_ids=_list('text'), reason='text')
TRACE = dict(schema=_enum(VERSION), binding=BINDING, context_digest='digest',
    findings=_list(FINDING, 1),
    independence=dict(reviewer='text', verifier='text', checked_at='int', reassess_at='int',
                      dependencies=_list(DEP_REF, 1), evidence_ids=TEXTS, challenge_route='text'),
    remedy=dict(id='text', version='int', findings_digest='digest', owner='text', deadline='int', funding_ids=TEXTS,
        evidence_requirements=_list(_enum(*STAGES), 6), events=_list(EVENT), residuals=_list(RESIDUAL),
        affected_account=dict(status=_enum('SUPPLIED', 'UNAVAILABLE', 'UNSAFE', 'NOT_APPLICABLE'),
                              evidence_ids=_list('text'), reason='text'),
        escalation=dict(owner='text', due_at='int', route='text')))


def digest(value):
    """Unsigned digest of complete supplied JSON; no trusted timestamp or signature."""
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
        if len(encoded) > 1048576:
            raise TraceError('input too large')
        return sha256(encoded.encode('utf-8')).hexdigest()
    except (TypeError, ValueError, RecursionError) as exc:
        raise TraceError('invalid JSON input') from exc


def _index(items, key='id'):
    result = {}
    for item in items:
        k = item[key]
        if k in result:
            raise TraceError('duplicate identity: ' + str(k))
        result[k] = item
    return result


def inspect_trace(trace, context):
    """Inspect one supplied snapshot against a caller-pinned context, without effects."""
    try:
        _shape(trace, TRACE, 'trace')
        _shape(context, CONTEXT, 'context')
    except RecursionError as exc:
        raise TraceError('recursive input') from exc
    td, cd = digest(trace), digest(context)
    t, c = json.loads(json.dumps(trace)), json.loads(json.dumps(context))
    if t['binding'] != c['expected'] or t['context_digest'] != cd:
        raise TraceError('caller anchor mismatch')
    evidence, claims = _index(c['evidence']), _index(c['claims'])
    objections, principals = _index(c['objections']), _index(c['principals'])
    injuries, findings = _index(c['injuries']), _index(t['findings'])
    now, blockers = c['now'], []

    def block(code):
        if code not in blockers:
            blockers.append(code)

    def refs(ids, kind=None):
        for identity in ids:
            if identity not in evidence:
                raise TraceError('unknown evidence: ' + identity)
            if kind is not None and evidence[identity]['kind'] != kind:
                raise TraceError('wrong evidence kind: ' + identity)
        return [evidence[i] for i in ids]

    def actor(identity):
        if identity not in principals:
            raise TraceError('unknown principal: ' + identity)

    def occurred(at):
        if at > now:
            raise TraceError('future event')

    def available(ids, at, kind=None):
        for e in refs(ids, kind):
            if e['observed_at'] > at:
                raise TraceError('evidence postdates use')

    for e in evidence.values():
        occurred(e['observed_at'])
    for party in c['parties']:
        actor(party)
    if set(findings) != set(claims):
        raise TraceError('finding inventory mismatch')
    for claim in claims.values():
        refs(claim['original_ids'], 'ORIGINAL')
    for objection in objections.values():
        if objection['claim_id'] not in claims:
            raise TraceError('unknown objection claim')
        if objection['claim_version'] != claims[objection['claim_id']]['version']:
            raise TraceError('objection claim version mismatch')
        refs(objection['evidence_ids'], 'COUNTER')
        occurred(objection['reopened_at'])
    # Every supplied counter record must be assigned, even if labelled nonmaterial.
    used_counter = {x for o in objections.values() for x in o['evidence_ids']}
    if used_counter != {i for i, e in evidence.items() if e['kind'] == 'COUNTER'}:
        raise TraceError('counterevidence inventory mismatch')
    for identity, finding in findings.items():
        claim = claims[identity]
        at = finding['decided_at']
        occurred(at)
        if finding['claim_version'] != claim['version']:
            raise TraceError('claim version mismatch')
        linked = _index(finding['evidence_refs'])
        for ref in linked.values():
            e = refs([ref['id']])[0]
            if (ref['version'], ref['digest']) != (e['version'], e['digest']):
                raise TraceError('evidence version or digest mismatch')
        available(list(linked), at)
        applicable = {i: o for i, o in objections.items() if o['claim_id'] == identity}
        needed = set(claim['original_ids']) | {i for o in applicable.values() for i in o['evidence_ids']}
        if not needed <= set(linked):
            raise TraceError('missing original or objection evidence link')
        checks = _index(finding['provenance'], 'original_id')
        if set(checks) != set(claim['original_ids']):
            raise TraceError('provenance inventory mismatch')
        for check in checks.values():
            actor(check['checker'])
            original = evidence[check['original_id']]
            if (check['original_version'], check['original_digest']) != (original['version'], original['digest']):
                raise TraceError('provenance original version or digest mismatch')
            if check['checker'] in c['parties']:
                block('PROVENANCE_CHECKER_IS_PARTY')
            available([check['original_id']], check['checked_at'], 'ORIGINAL')
            available([check['check_id']], check['checked_at'], 'PROVENANCE_CHECK')
            if check['check_id'] not in linked or check['checked_at'] > at:
                raise TraceError('provenance check not linked before finding')
        resolutions = _index(finding['resolutions'])
        if set(resolutions) != set(applicable):
            raise TraceError('objection resolution inventory mismatch')
        for oid, resolution in resolutions.items():
            objection = applicable[oid]
            if resolution['version'] != objection['version']:
                raise TraceError('objection version mismatch')
            available(resolution['evidence_ids'], resolution['resolved_at'])
            if not set(resolution['evidence_ids']) <= set(linked):
                raise TraceError('unlinked resolution support')
            if resolution['resolved_at'] > at:
                raise TraceError('resolution postdates finding')
            if resolution['resolved_at'] < objection['reopened_at']:
                block('OBJECTION_REOPENED')
            if resolution['state'] == 'UNRESOLVED' and objection['materiality'] == 'MATERIAL':
                block('MATERIAL_OBJECTION_UNRESOLVED')
        hearing = finding['hearing']
        available(hearing['evidence_ids'], at)
        if not set(hearing['evidence_ids']) <= set(linked):
            raise TraceError('unlinked hearing rationale')
        if hearing['status'] == 'PENDING':
            block('HEARING_PENDING')
        if hearing['status'] == 'HELD_REPORTED':
            refs(hearing['evidence_ids'], 'HEARING')

    independence = t['independence']
    reviewer, verifier = independence['reviewer'], independence['verifier']
    for identity in (reviewer, verifier):
        actor(identity)
    if reviewer == verifier or {reviewer, verifier} & set(c['parties']):
        raise TraceError('reviewer/verifier party or role overlap')
    controls = [principals[i]['controller'] for i in [reviewer, verifier, *c['parties']]]
    if None in controls:
        block('INDEPENDENCE_UNKNOWN')
    if controls[0] is not None and (controls[0] == controls[1] or controls[0] in controls[2:]):
        block('DECLARED_CONTROL_CONFLICT')
    if controls[1] is not None and controls[1] in controls[2:]:
        block('DECLARED_CONTROL_CONFLICT')
    checked = independence['checked_at']
    occurred(checked)
    available(independence['evidence_ids'], checked, 'DEPENDENCY')
    if any(checked > f['decided_at'] for f in findings.values()):
        raise TraceError('independence assessment postdates finding')
    if independence['reassess_at'] <= now:
        block('INDEPENDENCE_REASSESSMENT_DUE')
    deps = {}
    for dep in c['dependencies']:
        key = (dep['subject'], dep['dimension'])
        if key in deps:
            raise TraceError('duplicate dependency dimension')
        deps[key] = dep
        actor(dep['subject'])
        occurred(dep['changed_at'])
        refs(dep['evidence_ids'], 'DEPENDENCY')
    expected = {(who, dimension) for who in (reviewer, verifier) for dimension in DIMENSIONS}
    if set(deps) != expected:
        raise TraceError('dependency inventory mismatch')
    supplied = {}
    for ref in independence['dependencies']:
        key = (ref['subject'], ref['dimension'])
        if key in supplied:
            raise TraceError('duplicate dependency reference')
        supplied[key] = ref
    if set(supplied) != expected:
        raise TraceError('dependency reference inventory mismatch')
    for key, dep in deps.items():
        ref = supplied[key]
        if ref['version'] != dep['version'] or set(ref['evidence_ids']) != set(dep['evidence_ids']):
            raise TraceError('dependency version or evidence mismatch')
        available(dep['evidence_ids'], checked, 'DEPENDENCY')
        if not set(dep['evidence_ids']) <= set(independence['evidence_ids']):
            raise TraceError('unlinked dependency evidence')
        if dep['changed_at'] > checked:
            block('DEPENDENCY_CHANGED_AFTER_ASSESSMENT')
        if dep['status'] != 'CURRENT_REPORTED':
            block('DEPENDENCY_NOT_CURRENT')

    remedy = t['remedy']
    if remedy['findings_digest'] != digest(t['findings']):
        raise TraceError('remedy finding content binding mismatch')
    if remedy['version'] != c['remedy_version']:
        raise TraceError('remedy version mismatch')
    actor(remedy['owner'])
    actor(remedy['escalation']['owner'])
    refs(remedy['funding_ids'], 'FUNDING')
    if set(remedy['evidence_requirements']) != set(STAGES):
        raise TraceError('remedy evidence requirements mismatch')
    events = remedy['events']
    _index(events)
    if [e['stage'] for e in events] != list(STAGES[:len(events)]):
        raise TraceError('remedy stage dependency mismatch')
    previous, last_at = 'NONE', max(f['decided_at'] for f in findings.values())
    for event in events:
        actor(event['actor'])
        occurred(event['at'])
        if event['previous_id'] != previous or event['at'] < last_at:
            raise TraceError('remedy event chain mismatch')
        available(event['evidence_ids'], event['at'], event['stage'])
        if any(e['observed_at'] < last_at for e in refs(event['evidence_ids'])):
            raise TraceError('remedy evidence predates causal predecessor')
        if event['stage'] == 'AUDITED':
            effect_actors = {e['actor'] for e in events if e['stage'] in ('ATTEMPTED', 'OBSERVED')}
            effect_actors.add(remedy['owner'])
            audit_control = principals[verifier]['controller']
            effect_controls = [principals[who]['controller'] for who in effect_actors]
            if audit_control is None or None in effect_controls:
                block('REMEDY_AUDIT_INDEPENDENCE_UNKNOWN')
            if audit_control is not None and audit_control in effect_controls:
                block('REMEDY_AUDIT_CONTROL_CONFLICT')
            if event['actor'] != verifier or event['actor'] == remedy['owner'] or event['actor'] in effect_actors:
                raise TraceError('remedy audit owner is not separate verifier')
            if not checked <= event['at'] < independence['reassess_at']:
                raise TraceError('independence assessment not current at audit')
        previous, last_at = event['id'], event['at']
    if events:
        available(remedy['funding_ids'], events[0]['at'], 'FUNDING')
    if len(events) != len(STAGES):
        block('REMEDY_DELIVERY_TRACE_INCOMPLETE')
    residuals = _index(remedy['residuals'])
    if set(residuals) != set(injuries):
        raise TraceError('residual injury inventory mismatch')
    for identity, residual in residuals.items():
        if residual['version'] != injuries[identity]['version']:
            raise TraceError('residual injury version mismatch')
        available(residual['observation_ids'], last_at, 'OBSERVED')
        available(residual['audit_ids'], last_at, 'AUDITED')
        if residual['state'] == 'REPAIRED_REPORTED':
            if not residual['observation_ids'] or not residual['audit_ids']:
                raise TraceError('repair claim lacks observation and audit')
            if len(events) < 5:
                raise TraceError('residual repair precedes remedy audit')
            if not set(residual['observation_ids']) <= set(events[3]['evidence_ids']) or not set(residual['audit_ids']) <= set(events[4]['evidence_ids']):
                raise TraceError('residual evidence outside remedy event scope')
        else:
            block('RESIDUAL_INJURY_NOT_REPAIRED')
    account = remedy['affected_account']
    available(account['evidence_ids'], last_at, 'ACCOUNT')
    if account['status'] == 'SUPPLIED' and len(events) >= 4:
        if any(e['observed_at'] < events[3]['at'] for e in refs(account['evidence_ids'])):
            raise TraceError('affected delivery account predates observation')
    if account['status'] == 'SUPPLIED' and not account['evidence_ids']:
        raise TraceError('missing affected-party account')
    if account['status'] != 'SUPPLIED':
        if account['evidence_ids']:
            raise TraceError('account status contradicts supplied account')
        block('AFFECTED_ACCOUNT_EXCEPTION_REQUIRES_REVIEW')
    unfinished = len(events) != len(STAGES) or any(r['state'] != 'REPAIRED_REPORTED' for r in residuals.values())
    if unfinished and remedy['deadline'] <= now:
        block('REMEDY_OVERDUE_ESCALATION_REQUIRED')
    if unfinished and remedy['escalation']['due_at'] <= now:
        block('ESCALATION_DUE')
    return dict(schema='cortac.ops.inspection.v1',
        status='SUPPLIED_TRACE_CONSISTENT' if not blockers else 'SUPPLIED_TRACE_INCOMPLETE',
        blockers=blockers, trace_digest=td, context_digest=cd,
        authority='NONE', execution_enabled=False, controller_closure='SUPPLIED_UNVERIFIED',
        evidence_status='REFERENCES_ONLY', inventory_scope='SUPPLIED_INVENTORY_ONLY',
        freshness='CALLER_ANCHOR_ONLY', semantic_assessment='NOT_PERFORMED',
        factual_truth='NOT_ESTABLISHED', actual_independence='NOT_ESTABLISHED',
        remedy_effectiveness='NOT_ESTABLISHED', operational_conformance='NOT_ESTABLISHED')
