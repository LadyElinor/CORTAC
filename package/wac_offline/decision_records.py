"""Strict supplied decision receipts, not an automated moral or legal judgment.

Completeness makes assertions contestable. Evidence, standing, independence,
representative consent, factual truth and adequacy are NOT established here.
"""
from .io import InputError


def _object(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def _array(items, minimum=1):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'uniqueItems': True}


_TEXT = {'type': 'string', 'minLength': 1, 'pattern': r'[\s\S]*\S[\s\S]*'}
_REFS = _array(_TEXT)
PROTECTED_LIMITS_SCHEMA = _array(_object({'id': _TEXT, 'commitment': _TEXT}))
DECISION_RECORD_SCHEMA = _object({
    'schema': {'type': 'string', 'const': 'cortac.decision.record.v1'},
    'affected_parties': _array(_object({
        'id': _TEXT, 'interests': _TEXT, 'benefits': _TEXT, 'burdens': _TEXT,
        'representation': _TEXT,
    })),
    'alternatives': _array(_object({
        'option': _TEXT, 'less_harmful_analysis': _TEXT,
        'rejection_or_selection_reason': _TEXT, 'evidence_refs': _REFS,
    })),
    'protected_limit_assessments': _array(_object({
        'limit_id': _TEXT,
        'status': {'type': 'string', 'enum': ['PASS', 'FAIL', 'UNKNOWN']},
        'reasons': _TEXT, 'evidence_refs': _REFS,
    })),
    'burden_justification': _TEXT,
    'dissent': _array(_TEXT, 0),
    'dissent_status': {'type': 'string', 'enum': ['NONE_REPORTED', 'RECORDED']},
    'predictions': _array(_TEXT),
    'review_triggers': _array(_object({'condition': _TEXT, 'review_authority': _TEXT})),
    'remedy_plan': _object({
        'authority': _TEXT, 'resources': _TEXT, 'steps': _TEXT, 'evidence_refs': _REFS,
    }),
    'evidence_refs': _REFS,
})


def _shape(value, schema, path):
    kinds = {'object': dict, 'array': list, 'string': str}
    kind = schema['type']
    if type(value) is not kinds[kind]:
        raise InputError(path + ': expected ' + kind)
    if 'const' in schema and value != schema['const']:
        raise InputError(path + ': wrong schema')
    if 'enum' in schema and value not in schema['enum']:
        raise InputError(path + ': unsupported value')
    if kind == 'object':
        if set(value) != set(schema['required']):
            raise InputError(path + ': missing or unknown fields')
        for key, child in value.items():
            _shape(child, schema['properties'][key], path + '.' + key)
    elif kind == 'array':
        if len(value) < schema['minItems']:
            raise InputError(path + ': insufficient entries')
        for i, child in enumerate(value):
            _shape(child, schema['items'], path + '[' + str(i) + ']')
            if child in value[:i]:
                raise InputError(path + ': duplicate entries')
    elif not value.strip():
        raise InputError(path + ': blank text')


def validate_protected_limits(limits):
    """Validate explicitly supplied commitments; do not infer a constitution."""
    _shape(limits, PROTECTED_LIMITS_SCHEMA, 'protected_limits')
    ids = [limit['id'] for limit in limits]
    if len(ids) != len(set(ids)):
        raise InputError('protected_limits: duplicate limit ID')


def require_preserved_limits(old, new):
    """Ordinary and repair amendments cannot remove, add or rewrite these limits."""
    validate_protected_limits(old)
    validate_protected_limits(new)
    if {v['id']: v['commitment'] for v in old} != {v['id']: v['commitment'] for v in new}:
        raise InputError('protected commitments cannot change through amendment or repair')


def validate_decision_record(record, protected_limits=None):
    """Return supplied assessment pass status after exact completeness checks.

    With no policy argument the applicable-limit inventory itself remains a
    caller assertion. AmendmentReplay always supplies its effective inventory.
    FAIL or UNKNOWN never passes, however many votes approve the proposal.
    """
    _shape(record, DECISION_RECORD_SCHEMA, 'decision_record')
    for field, key in [('affected_parties', 'id'), ('protected_limit_assessments', 'limit_id')]:
        ids = [entry[key] for entry in record[field]]
        if len(ids) != len(set(ids)):
            raise InputError('decision_record.' + field + ': duplicate identity')
    assessments = record['protected_limit_assessments']
    if protected_limits is not None:
        validate_protected_limits(protected_limits)
        if {a['limit_id'] for a in assessments} != {a['id'] for a in protected_limits}:
            raise InputError('decision_record: applicable protected limit inventory mismatch')
    if bool(record['dissent']) != (record['dissent_status'] == 'RECORDED'):
        raise InputError('decision_record: inconsistent dissent status')
    return all(assessment['status'] == 'PASS' for assessment in assessments)
