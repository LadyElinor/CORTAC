"""Opt-in warning review: supplied records only, never authority or attribution.

This supplement does not change OPS1/Vanguard or establish authenticity,
completeness, legal liability, recipient receipt, or practical independence.
"""
from hashlib import sha256
import json
import re

SCHEMA = 'cortac.relay.warning.v1'


class WarningError(ValueError):
    """Malformed supplied record, not an adverse finding."""


def _shape(value, spec, path='record'):
    if isinstance(spec, dict):
        if type(value) is not dict or set(value) != set(spec):
            raise WarningError(path + ': missing or unknown fields')
        for key, child in spec.items():
            _shape(value[key], child, path + '.' + key)
    elif isinstance(spec, list):
        if type(value) is not list or len(value) > 128:
            raise WarningError(path + ': bounded list required')
        for item in value:
            _shape(item, spec[0], path)
        if len(value) != len(set(value)):
            raise WarningError(path + ': duplicate reference')
    elif isinstance(spec, tuple):
        if type(value) is not str or value not in spec:
            raise WarningError(path + ': unsupported value')
    elif spec == 'digest':
        if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
            raise WarningError(path + ': lowercase SHA256 required')
    elif spec == 'text':
        if type(value) is not str or not value.strip() or len(value) > 4000:
            raise WarningError(path + ': bounded nonblank text required')
    elif spec == 'optional':
        if value is not None:
            _shape(value, 'text', path)
    else:
        raise RuntimeError('invalid internal schema')


REFS = ['digest']
SHAPE = dict(
    schema=(SCHEMA,), case_id='text', decision_digest='digest', predecessor_digest='digest',
    warning=dict(original_digest='digest', dissent_digests=REFS,
        recipient='text', delivery=('UNKNOWN', 'NOT_DELIVERED', 'RECEIVED_REPORTED'),
        delivery_evidence=REFS, response=('UNKNOWN', 'NO_RESPONSE_REPORTED', 'RESPONSE_REPORTED'),
        response_evidence=REFS),
    combined_review=dict(reviewer='optional', controller='optional',
        decision_controller='optional', access_evidence=REFS, review_evidence=REFS,
        scope='text', limitations='text'),
    protection=dict(state=('UNASSESSED', 'PROPOSAL_RECORDED'),
        rationale_evidence=REFS, authority_evidence=REFS, appeal_evidence=REFS),
    attribution=dict(state=('UNASSESSED', 'REVIEW_RECORDED'),
        subject='optional', act_evidence=REFS, knowledge_evidence=REFS,
        authority_evidence=REFS, intent_evidence=REFS,
        response_opportunity_evidence=REFS),
    repair=dict(state=('NOT_ASSESSED', 'REPAIR_REPORTED'), owner_controller='optional',
        verifier_controller='optional', recipient_evidence=REFS,
        observation_evidence=REFS, verification_evidence=REFS,
        independence_evidence=REFS, residual_injury='text'))


def inspect_warning(record):
    """Return explicit gaps; even no gaps is REVIEW_REQUIRED, never a ruling.

References are opaque artifact SHA256 values, not fetched or authenticated.
Original warning, dissent and predecessor bindings remain in the input; the
record digest binds canonical JSON, not original serialization. Callers must
    retain original artifacts and record versions independently.
"""
    _shape(record, SHAPE)
    raw = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    if len(raw) > 200000:
        raise WarningError('record exceeds canonical byte limit')
    gaps = []
    def missing(value, code):
        if not value:
            gaps.append(code)
    warning = record['warning']
    if warning['delivery'] != 'RECEIVED_REPORTED':
        gaps.append('WARNING_' + warning['delivery'])
    else:
        missing(warning['delivery_evidence'], 'RECEIPT_EVIDENCE_MISSING')
    if warning['response'] != 'RESPONSE_REPORTED':
        gaps.append('WARNING_' + warning['response'])
    else:
        missing(warning['response_evidence'], 'RESPONSE_EVIDENCE_MISSING')
    if warning['response'] == 'RESPONSE_REPORTED' and warning['delivery'] != 'RECEIVED_REPORTED':
        gaps.append('RESPONSE_WITHOUT_RECORDED_RECEIPT')
    review = record['combined_review']
    for key in ('reviewer', 'controller', 'decision_controller', 'access_evidence', 'review_evidence'):
        missing(review[key], 'COMBINED_' + key.upper() + '_MISSING')
    if review['controller'] is not None and review['controller'] == review['decision_controller']:
        gaps.append('COMBINED_REVIEW_CONTROL_CONFLICT')
    protection = record['protection']
    if protection['state'] == 'UNASSESSED':
        gaps.append('PROTECTIVE_REVIEW_MISSING')
    else:
        for key in ('rationale_evidence', 'authority_evidence', 'appeal_evidence'):
            missing(protection[key], 'PROTECTION_' + key.upper() + '_MISSING')
    # Attribution gaps never prevent recording a protective proposal, and a
    # protective proposal never supplies a finding about a person's intent.
    attribution_gaps = []
    if record['attribution']['state'] == 'REVIEW_RECORDED':
        attribution_gaps = [key for key, value in record['attribution'].items()
                            if key != 'state' and not value]
    repair = record['repair']
    if repair['state'] == 'REPAIR_REPORTED':
        for key in ('owner_controller', 'verifier_controller', 'recipient_evidence',
                    'observation_evidence', 'verification_evidence', 'independence_evidence'):
            missing(repair[key], 'REPAIR_' + key.upper() + '_MISSING')
        if repair['verifier_controller'] is not None and repair['verifier_controller'] == repair['owner_controller']:
            gaps.append('REPAIR_SELF_VERIFICATION')
        if repair['verifier_controller'] is not None and repair['verifier_controller'] == review['decision_controller']:
            gaps.append('REPAIR_ORIGINAL_DECISION_CONTROL_CONFLICT')
        if set(repair['verification_evidence']) & set(repair['observation_evidence']):
            gaps.append('REPAIR_VERIFICATION_REUSES_OBSERVATION')
    return dict(schema=SCHEMA, record_digest=sha256(raw).hexdigest(),
        status='REVIEW_REQUIRED', gaps=gaps, attribution_gaps=attribution_gaps,
        attribution='NOT_DETERMINED', effectiveness='NOT_VERIFIED',
        controller_closure='SUPPLIED_UNVERIFIED', authority='NONE', execution_enabled=False)
