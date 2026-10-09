"""Opt-in OPR1 supplied-record inspection. No adjudication or effect interface.

This module checks closed syntax, supplied linkage and arithmetic only. Neither
success nor any supplied assertion establishes truth, moral adequacy, authority,
authentication, real independence, conformance, or permission to restrict anyone.
"""
from hashlib import sha256
import json
import re

VERSION = 'cortac.opr.record.v1'
CONTEXT_VERSION = 'cortac.opr.context.v1'


class RecordError(ValueError):
    """Malformed or internally inconsistent supplied record."""


def _obj(**fields):
    return fields


def _seq(item, minimum=0):
    return (item, minimum)


def _enum(*values):
    return frozenset(values)


def _shape(value, spec, path):
    if isinstance(spec, dict):
        if type(value) is not dict or set(value) != set(spec):
            raise RecordError(path + ': missing or unknown fields')
        for key in spec:
            _shape(value[key], spec[key], path + '.' + key)
    elif isinstance(spec, tuple):
        if type(value) is not list or len(value) < spec[1]:
            raise RecordError(path + ': invalid list')
        for i, item in enumerate(value):
            _shape(item, spec[0], path + '[' + str(i) + ']')
            if item in value[:i]:
                raise RecordError(path + ': duplicate entry')
    elif isinstance(spec, frozenset):
        if type(value) is not str or value not in spec:
            raise RecordError(path + ': unsupported value')
    elif spec == 'text':
        if type(value) is not str or not value.strip():
            raise RecordError(path + ': expected nonblank text')
    elif spec == 'digest':
        if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
            raise RecordError(path + ': expected SHA256 digest')
    elif spec == 'integer':
        if type(value) is not int or value < 0:
            raise RecordError(path + ': expected nonnegative integer')
    elif spec == 'controller':
        if value is not None:
            _shape(value, 'text', path)
    else:
        raise RuntimeError('internal schema error')


TEXTS = _seq('text', 1)
EVIDENCE_REF = _obj(id='text', digest='digest')
INTERVAL = _obj(id='text', case_label='text', start='integer', end='integer',
                burden_units='integer', operations=TEXTS)
GRANT = _obj(id='text', purpose=_enum('RESTRICTION', 'REVIEW', 'NOTICE_DELAY'),
             policy_digest='digest', epoch='integer', version='integer',
             target='text', operations=TEXTS, start='integer', end='integer',
             issuer='text', state=_enum('CURRENT', 'REVOKED'))
CONTEXT = _obj(schema=_enum(CONTEXT_VERSION), policy_digest='digest', epoch='integer',
               now='integer', version='integer', target='text', burden_group='text',
               operations=TEXTS, duration_limit='integer', load_limit='integer',
               serious_duration='integer', serious_load='integer', history=_seq(INTERVAL),
               evidence=_seq(_obj(id='text', digest='digest',
                   kind=_enum('OBSERVATION', 'CLAIM', 'INFERENCE', 'CONTRARY', 'CONTROL')), 1),
               protected_limits=TEXTS,
               principals=_seq(_obj(id='text', controller='controller'), 1),
               parties=TEXTS, grants=_seq(GRANT, 1))
RECORD = _obj(schema=_enum(VERSION), case_id='text', case_label='text',
    policy_digest='digest', epoch='integer', version='integer', target='text',
    burden_group='text', operations=TEXTS, interval=INTERVAL,
    cumulative=_obj(duration='integer', load='integer'),
    justification=_obj(conduct='text', rule='text', risk='text', urgency='text',
        alternatives='text', burdens='text', epistemic='text', normative='text',
        dissent='text', consequence=_enum('TEMPORARY', 'LONG_EXCLUSION', 'ROLE_LOSS',
            'PUBLIC_SERIOUS_FINDING', 'IRREVERSIBLE'), standard=_enum('ARTICULABLE_RISK', 'CLEAR_AND_CONVINCING')),
    evidence_refs=_seq(EVIDENCE_REF, 1),
    contrary=_seq(_obj(evidence_id='text', disposition=_enum('ADDRESSED', 'UNRESOLVED'), reason='text')),
    limits=_seq(_obj(id='text', status=_enum('SATISFIED', 'FAILED', 'UNRESOLVED'),
        reason='text', evidence_ids=TEXTS), 1),
    independence=_obj(reviewer='text', verifier='text', evidence_ids=TEXTS,
        conflict_route='text', reassess_at='integer'),
    notice=_obj(status=_enum('DELIVERED', 'DELAYED', 'UNDELIVERED'), summary='text',
        authority_ref='text', deadline='integer', reason='text'),
    review=_obj(route='text', substitute='text', deadline='integer', authority_ref='text',
        reserved_units='integer'), authority_ref='text', continuity='text',
    stopping_conditions='text',
    complaints=_seq(_obj(id='text', version='integer', status=_enum('OPEN', 'RESOLVED'))),
    correction=_obj(decision='text', attempted_effect='text', observed_effect='text',
        audit='text', status=_enum('NOT_REQUESTED', 'INCOMPLETE', 'REPORTED_COMPLETE')))


def _index(items, label):
    result = {item['id']: item for item in items}
    if len(result) != len(items):
        raise RecordError(label + ': duplicate identifier')
    return result


def _fail(condition, message):
    if not condition:
        raise RecordError(message)


def _intervals(items):
    """Union duration and additive burden-unit time, including parallel loads."""
    for item in items:
        _fail(item['end'] > item['start'] and item['burden_units'] > 0,
              'interval must have positive duration and burden units')
    duration = 0
    stop = None
    for item in sorted(items, key=lambda x: (x['start'], x['end'])):
        duration += max(0, item['end'] - max(item['start'], stop if stop is not None else item['start']))
        stop = max(stop if stop is not None else item['end'], item['end'])
    return duration, sum((x['end'] - x['start']) * x['burden_units'] for x in items)


def inspect_record(record, context):
    """Inspect supplied snapshot; never issue a receipt usable by another gateway.

    Context pins the finite known history/evidence/actors/grants. It is not an
    authenticated policy registry. Logical integer ticks have no wall-clock force.
    Any effect-boundary adapter, dependency discovery or authority check is absent.
    Unknown fields (including purported execution/authority flags) fail closed.
    """
    _shape(context, CONTEXT, 'context')
    _shape(record, RECORD, 'record')
    # Freeze a private JSON snapshot so neither return values nor later caller
    # mutation can change an already produced report; no objects are retained.
    context = json.loads(json.dumps(context, allow_nan=False))
    record = json.loads(json.dumps(record, allow_nan=False))
    for field in ('policy_digest', 'epoch', 'version', 'target', 'burden_group'):
        _fail(record[field] == context[field], 'stale or mismatched ' + field)
    _fail(set(record['operations']) == set(context['operations']), 'operation scope mismatch')
    _fail(set(record['interval']['operations']) == set(record['operations']), 'interval scope mismatch')
    _fail(record['interval']['case_label'] == record['case_label'], 'interval case label mismatch')
    evidence = _index(context['evidence'], 'evidence')
    references = _index(record['evidence_refs'], 'evidence refs')
    for identifier, ref in references.items():
        _fail(identifier in evidence and evidence[identifier]['digest'] == ref['digest'],
              'unresolved evidence reference: ' + identifier)
    def refs(ids):
        _fail(all(identifier in references for identifier in ids), 'unlinked evidence reference')
    contrary = {e['id'] for e in evidence.values() if e['kind'] == 'CONTRARY'}
    dispositions = {x['evidence_id'] for x in record['contrary']}
    _fail(len(dispositions) == len(record['contrary']) and contrary == dispositions,
          'contrary evidence coverage mismatch')
    refs(dispositions)
    limits = _index(record['limits'], 'protected limits')
    _fail(set(limits) == set(context['protected_limits']), 'protected limit inventory mismatch')
    for item in limits.values():
        refs(item['evidence_ids'])
    principals = _index(context['principals'], 'principals')
    _fail(all(p in principals for p in context['parties']), 'unknown party')
    _fail(context['target'] in context['parties'], 'target missing from declared parties')
    independence = record['independence']
    refs(independence['evidence_ids'])
    _fail(all(evidence[e]['kind'] == 'CONTROL' for e in independence['evidence_ids']),
          'independence needs control evidence references')
    participants = context['parties'] + [independence['reviewer'], independence['verifier']]
    _fail(all(p in principals for p in participants), 'unknown independence participant')
    _fail(independence['reviewer'] != independence['verifier'] and
          not set(context['parties']) & {independence['reviewer'], independence['verifier']},
          'independent roles overlap parties or one another')
    controllers = {p: principals[p]['controller'] for p in participants}
    for actor in (independence['reviewer'], independence['verifier']):
        for other in participants:
            if actor != other and controllers[actor] is not None:
                _fail(controllers[actor] != controllers[other], 'disclosed common control')
    history = _index(context['history'], 'history')
    _fail(record['interval']['id'] not in history, 'interval already present in history')
    intervals = list(history.values()) + [record['interval']]
    _fail(all(set(x['operations']).issubset(set(context['operations'])) for x in intervals),
          'historical operation outside supplied burden group')
    duration, load = _intervals(intervals)
    _fail(record['cumulative'] == dict(duration=duration, load=load),
          'cumulative burden mismatch; case labels do not reset history')
    _fail(context['serious_duration'] <= context['duration_limit'] and
          context['serious_load'] <= context['load_limit'], 'invalid burden thresholds')
    grants = _index(context['grants'], 'grants')
    blockers = []
    def blocked(condition, code):
        if condition:
            blockers.append(code)
    def grant(identifier, purpose):
        _fail(identifier in grants, 'missing supplied authority reference')
        item = grants[identifier]
        _fail(item['purpose'] == purpose, 'authority purpose mismatch')
        for key in ('policy_digest', 'epoch', 'version', 'target'):
            _fail(item[key] == context[key], 'stale authority ' + key)
        _fail(set(item['operations']) == set(record['operations']), 'authority scope mismatch')
        _fail(item['issuer'] in principals, 'unknown supplied issuer')
        _fail(item['end'] > item['start'], 'invalid authority interval')
        blocked(item['state'] != 'CURRENT', purpose + '_AUTHORITY_REVOKED')
        blocked(not item['start'] <= context['now'] < item['end'], purpose + '_AUTHORITY_NOT_CURRENT')
        return item
    restriction = grant(record['authority_ref'], 'RESTRICTION')
    review = grant(record['review']['authority_ref'], 'REVIEW')
    interval = record['interval']
    _fail(restriction['start'] <= interval['start'] < interval['end'] <= restriction['end'],
          'restriction window exceeds supplied authority')
    blocked(not interval['start'] <= context['now'] < interval['end'], 'RESTRICTION_NOT_CURRENT')
    blocked(duration > context['duration_limit'], 'CUMULATIVE_DURATION_EXCEEDED')
    blocked(load > context['load_limit'], 'CUMULATIVE_LOAD_EXCEEDED')
    blocked((duration >= context['serious_duration'] or load >= context['serious_load'] or
            record['justification']['consequence'] != 'TEMPORARY') and
            record['justification']['standard'] != 'CLEAR_AND_CONVINCING', 'HEIGHTENED_FACTUAL_STANDARD_MISSING')
    blocked(any(v is None for v in controllers.values()), 'INDEPENDENCE_UNKNOWN')
    blocked(independence['reassess_at'] <= context['now'], 'INDEPENDENCE_REASSESSMENT_DUE')
    blocked(any(x['status'] != 'SATISFIED' for x in limits.values()), 'PROTECTED_LIMIT_UNSATISFIED')
    blocked(any(x['disposition'] == 'UNRESOLVED' for x in record['contrary']), 'CONTRARY_EVIDENCE_UNRESOLVED')
    blocked(record['review']['reserved_units'] == 0, 'REVIEW_RESERVE_EMPTY')
    blocked(not context['now'] < record['review']['deadline'] <= min(interval['end'], review['end']),
            'REVIEW_DEADLINE_INVALID')
    notice = record['notice']
    if notice['status'] == 'DELAYED':
        delay = grant(notice['authority_ref'], 'NOTICE_DELAY')
        blocked(not context['now'] < notice['deadline'] <= min(interval['end'], delay['end'],
                record['review']['deadline']), 'NOTICE_DELAY_NOT_BOUNDED')
    else:
        _fail(notice['authority_ref'] == 'NOT_APPLICABLE', 'unexpected notice-delay authority')
        blocked(notice['status'] == 'UNDELIVERED', 'NOTICE_UNDELIVERED')
        if notice['status'] == 'DELIVERED':
            _fail(notice['deadline'] <= context['now'], 'future claimed notice delivery')
    _index(record['complaints'], 'complaints')
    blocked(record['correction']['status'] == 'INCOMPLETE', 'CORRECTION_REPORTED_INCOMPLETE')
    # Complaint status and correction narratives are retained declarations only;
    # this module never closes a complaint or promotes REPORTED_COMPLETE to proof.
    return dict(schema='cortac.opr.inspection.v1',
        status='STRUCTURALLY_INCOMPLETE' if blockers else 'STRUCTURALLY_COMPLETE',
        blockers=blockers, cumulative_duration=duration, cumulative_load=load,
        record_digest=sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
            ensure_ascii=True, allow_nan=False).encode()).hexdigest(),
        context_digest=sha256(json.dumps(context, sort_keys=True, separators=(',', ':'),
            ensure_ascii=True, allow_nan=False).encode()).hexdigest(),
        authority='NONE', execution_enabled=False, controller_closure='SUPPLIED_UNVERIFIED',
        context_status='SUPPLIED_UNVERIFIED', evidence_status='REFERENCES_ONLY',
        semantic_assessment='NOT_PERFORMED', operational_conformance='NOT_ESTABLISHED',
        scope='OFFLINE_SUPPLIED_RECORD_STRUCTURE_ONLY')
