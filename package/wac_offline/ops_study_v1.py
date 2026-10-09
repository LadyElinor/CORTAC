"""Opt-in OPS1 shadow-study plan/trace inspection, entirely offline.

The plan is an immutable proposed specification. Context contains supplied pins,
preregistration and observations, keeping the plan digest independent of later
observations. Hashes are Python canonical JSON bindings, not signatures, trusted
registry heads, RFC 8785 JCS, or proof that preregistration actually occurred.
No statistics, empirical comparisons, authority, effects, or model calls exist.
"""
from hashlib import sha256
import json
import re

VERSION = 'cortac.ops.study.plan.v1'
CONTEXT_VERSION = 'cortac.ops.study.context.v1'
MAX_LIST = 256
MAX_TEXT = 8192
MAX_INTEGER = 2 ** 63 - 1
MAX_INPUT_BYTES = 1024 * 1024
ENDPOINTS = ('mistaken_restrictions', 'missed_harms', 'delay',
             'residual_injury', 'remedy_completion')
ARMS = ('MINIMAL', 'FULL')


class StudyError(ValueError):
    """Malformed or inconsistent supplied plan/trace binding."""


def _obj(**fields):
    return fields


def _seq(item, minimum=0):
    return (item, minimum)


def _maybe(item):
    return (item, None)


def _enum(*values):
    return frozenset(values)


def _shape(value, spec, path):
    if isinstance(spec, dict):
        if type(value) is not dict or set(value) != set(spec):
            raise StudyError(path + ': missing or unknown fields')
        for key in spec:
            _shape(value[key], spec[key], path + '.' + key)
    elif isinstance(spec, tuple):
        if spec[1] is None:
            if value is not None:
                _shape(value, spec[0], path)
        else:
            if type(value) is not list or not spec[1] <= len(value) <= MAX_LIST:
                raise StudyError(path + ': invalid list')
            for i, item in enumerate(value):
                _shape(item, spec[0], path + '[' + str(i) + ']')
                if item in value[:i]:
                    raise StudyError(path + ': duplicate entry')
    elif isinstance(spec, frozenset):
        if type(value) is not str or value not in spec:
            raise StudyError(path + ': unsupported value')
    elif spec == 'text':
        if type(value) is not str or not value.strip() or len(value) > MAX_TEXT:
            raise StudyError(path + ': expected nonblank text')
    elif spec == 'digest':
        if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
            raise StudyError(path + ': expected SHA256 digest')
    elif spec == 'integer':
        if type(value) is not int or not 0 <= value <= MAX_INTEGER:
            raise StudyError(path + ': expected nonnegative integer')
    else:
        raise RuntimeError('internal schema error')


REF = _obj(id='text', digest='digest')
REFS = _seq(REF, 1)
PLAN = _obj(schema=_enum(VERSION), study_id='text', version='integer',
    condition_set_digest='digest',
    arms=_seq(_obj(id=_enum(*ARMS), condition_set_digest='digest', procedure='text'), 2),
    endpoints=_seq(_obj(id=_enum(*ENDPOINTS), definition='text', criterion='text'), 5),
    assessment=_obj(assessor='text', verifier='text', independence_evidence_refs=REFS),
    uncertainty_protocol='text', missingness_protocol='text', stopping_criteria='text',
    protected_group_comparison_protocol='text', privacy_permission_protocol='text',
    privacy_permission_evidence_refs=REFS,
    evidence_source_requirements=_seq(_obj(id='text', requirement='text'), 1))
PREREGISTRATION = _obj(plan_digest='digest', plan_version='integer',
    registered_at='integer', assessor='text', verifier='text',
    independence_evidence_refs=REFS)
OUTCOME = _obj(endpoint=_enum(*ENDPOINTS), state=_enum('REPORTED', 'MISSING'),
    value=_maybe('text'), uncertainty='text', missingness='text', evidence_refs=_seq(REF))
OBSERVATION = _obj(id='text', plan_digest='digest', plan_version='integer',
    arm=_enum(*ARMS), condition_set_digest='digest', observed_at='integer',
    recorded_at='integer', assessor='text', outcomes=_seq(OUTCOME, 5))
CONTEXT = _obj(schema=_enum(CONTEXT_VERSION), expected_study_id='text',
    expected_plan_version='integer', expected_plan_digest='digest', now='integer',
    designated_assessor='text', designated_verifier='text',
    principals=_seq(_obj(id='text', controller=_maybe('text')), 1), parties=_seq('text', 1),
    expected_independence_evidence_refs=REFS,
    evidence=_seq(_obj(id='text', digest='digest', available_at='integer',
        kind=_enum('INDEPENDENCE', 'PRIVACY_PERMISSION', 'OBSERVATION'), source_id='text')),
    preregistration=_maybe(PREREGISTRATION), observations=_seq(OBSERVATION))


def input_digest(value):
    """Hash every supplied JSON field; no authentication or archival guarantee.

    Encoding: sorted keys, compact separators, ensure_ascii=True, allow_nan=False,
    UTF-8. Object key order is immaterial; array order is retained.
    """
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
            ensure_ascii=True, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, RecursionError) as error:
        raise StudyError('input is not a finite JSON tree') from error
    _fail(len(encoded) <= MAX_INPUT_BYTES, 'input exceeds 1 MiB canonical JSON bound')
    return sha256(encoded).hexdigest()


def _fail(condition, message):
    if not condition:
        raise StudyError(message)


def _index(items, label, key='id'):
    result = {item[key]: item for item in items}
    _fail(len(result) == len(items), label + ': duplicate identifier')
    return result


def inspect_study(plan, context):
    """Check a closed supplied snapshot, without mutating or retaining inputs.

    PLAN_TRACE_CONSISTENT means only the implemented shape/linkage checks passed.
    Even that status establishes neither a completed study nor empirical success.
    Caller-supplied pins, logical times, actors, sources and declarations remain
    unauthenticated. Coordinated rewrites/re-signing are not detected; no trusted
    historical registry, source-content resolver or real independence check exists.
    Independence freshness across the study span is not checked or established.
    """
    try:
        _shape(plan, PLAN, 'plan')
        _shape(context, CONTEXT, 'context')
    except RecursionError as error:
        raise StudyError('input exceeds supported nesting') from error
    # Bound and hash each complete input before allocating private snapshots.
    plan_digest = input_digest(plan)
    context_digest = input_digest(context)
    plan = json.loads(json.dumps(plan, allow_nan=False))
    context = json.loads(json.dumps(context, allow_nan=False))
    _fail(plan['version'] > 0, 'plan version must be positive')
    _fail(plan['study_id'] == context['expected_study_id'], 'study identifier mismatch')
    _fail(plan['version'] == context['expected_plan_version'], 'pinned plan version mismatch')
    _fail(plan_digest == context['expected_plan_digest'], 'pinned plan digest mismatch')
    arms = _index(plan['arms'], 'arms')
    endpoints = _index(plan['endpoints'], 'endpoints')
    _fail(set(arms) == set(ARMS), 'MINIMAL and FULL arms required')
    _fail(set(endpoints) == set(ENDPOINTS), 'required endpoint inventory mismatch')
    _fail(all(a['condition_set_digest'] == plan['condition_set_digest'] for a in arms.values()),
          'comparison arms must bind the same condition set')

    evidence = _index(context['evidence'], 'evidence')
    sources = _index(plan['evidence_source_requirements'], 'evidence sources')
    _fail(all(e['source_id'] in sources for e in evidence.values()), 'unregistered evidence source')
    _fail(all(e['available_at'] <= context['now'] for e in evidence.values()),
          'future claimed evidence availability')

    def refs(items, kind, by=None):
        indexed = _index(items, 'evidence references')
        for identifier, item in indexed.items():
            _fail(identifier in evidence and evidence[identifier]['digest'] == item['digest'],
                  'unresolved evidence reference: ' + identifier)
            _fail(evidence[identifier]['kind'] == kind, 'evidence kind mismatch: ' + identifier)
            if by is not None:
                _fail(evidence[identifier]['available_at'] <= by,
                      'evidence unavailable at claimed record time: ' + identifier)
        return {key: item['digest'] for key, item in indexed.items()}

    assessment = plan['assessment']
    _fail(assessment['assessor'] == context['designated_assessor'] and
          assessment['verifier'] == context['designated_verifier'], 'designated assessment role mismatch')
    control_refs = refs(assessment['independence_evidence_refs'], 'INDEPENDENCE')
    _fail(control_refs == refs(context['expected_independence_evidence_refs'], 'INDEPENDENCE'),
          'pinned independence evidence mismatch')
    refs(plan['privacy_permission_evidence_refs'], 'PRIVACY_PERMISSION')
    principals = _index(context['principals'], 'principals')
    assessor, verifier = assessment['assessor'], assessment['verifier']
    participants = context['parties'] + [assessor, verifier]
    _fail(all(p in principals for p in participants), 'unknown assessment participant')
    _fail(assessor != verifier and not {assessor, verifier} & set(context['parties']),
          'assessment roles overlap each other or a party')
    controllers = {p: principals[p]['controller'] for p in participants}
    for actor in (assessor, verifier):
        for other in participants:
            if actor != other and controllers[actor] is not None:
                _fail(controllers[actor] != controllers[other], 'disclosed common control')

    blockers = []
    if any(controller is None for controller in controllers.values()):
        blockers.append('INDEPENDENCE_CONTROLLER_UNKNOWN')
    if set(sources) - {e['source_id'] for e in evidence.values()}:
        blockers.append('REQUIRED_EVIDENCE_SOURCE_ABSENT')
    registration = context['preregistration']
    observations = context['observations']
    _index(observations, 'observations')
    if registration is None:
        _fail(not observations, 'observations require a supplied prior preregistration')
        blockers.append('PREREGISTRATION_ABSENT')
    else:
        _fail(registration['plan_digest'] == plan_digest and
              registration['plan_version'] == plan['version'], 'preregistration plan binding mismatch')
        _fail(registration['assessor'] == assessor and registration['verifier'] == verifier,
              'preregistration assessment role mismatch')
        _fail(refs(registration['independence_evidence_refs'], 'INDEPENDENCE') == control_refs,
              'preregistration independence evidence mismatch')
        _fail(registration['registered_at'] <= context['now'], 'future claimed preregistration')
        refs(registration['independence_evidence_refs'], 'INDEPENDENCE', registration['registered_at'])
        refs(plan['privacy_permission_evidence_refs'], 'PRIVACY_PERMISSION', registration['registered_at'])

    counts = {arm: {endpoint: dict(reported=0, missing=0) for endpoint in ENDPOINTS} for arm in ARMS}
    for observation in observations:
        _fail(observation['plan_digest'] == plan_digest and
              observation['plan_version'] == plan['version'], 'observation plan binding mismatch')
        _fail(observation['condition_set_digest'] == plan['condition_set_digest'],
              'observation condition-set binding mismatch')
        _fail(observation['assessor'] == assessor, 'observation assessor substitution')
        _fail(registration['registered_at'] < observation['observed_at'] <=
              observation['recorded_at'] <= context['now'],
              'preregistration must strictly precede observations and recording')
        outcomes = _index(observation['outcomes'], 'outcomes', 'endpoint')
        _fail(set(outcomes) == set(ENDPOINTS), 'observation endpoint inventory mismatch')
        for endpoint, outcome in outcomes.items():
            refs(outcome['evidence_refs'], 'OBSERVATION', observation['recorded_at'])
            if outcome['state'] == 'MISSING':
                _fail(outcome['value'] is None, 'missing outcome must not contain a value')
                counts[observation['arm']][endpoint]['missing'] += 1
            else:
                _fail(outcome['value'] is not None and bool(outcome['evidence_refs']),
                      'reported outcome requires a value and evidence reference')
                counts[observation['arm']][endpoint]['reported'] += 1
    if not observations:
        blockers.append('OBSERVATIONS_ABSENT')
    elif set(ARMS) != {o['arm'] for o in observations}:
        blockers.append('COMPARISON_ARM_OBSERVATIONS_ABSENT')
    if any(cell['missing'] for arm in counts.values() for cell in arm.values()):
        blockers.append('MISSING_OUTCOMES_DECLARED')
    if observations and not any(cell['reported'] for arm in counts.values() for cell in arm.values()):
        blockers.append('REPORTED_OUTCOMES_ABSENT')
    return dict(schema='cortac.ops.study.inspection.v1',
        status='PLAN_TRACE_INCOMPLETE' if blockers else 'PLAN_TRACE_CONSISTENT',
        phase=('DRAFT' if registration is None else
               'OBSERVATIONS_SUPPLIED' if observations else 'PREPARED_NO_OBSERVATIONS'),
        blockers=blockers, plan_digest=plan_digest, context_digest=context_digest,
        observation_count=len(observations), supplied_outcome_inventory=counts,
        authority='NONE', execution_enabled=False, study_validity='NOT_ESTABLISHED',
        study_completion='NOT_ESTABLISHED', empirical_superiority='NOT_ESTABLISHED',
        input_status='ALL_SUPPLIED_UNVERIFIED', context_status='SUPPLIED_UNVERIFIED',
        caller_pins_status='SUPPLIED_UNAUTHENTICATED', preregistration_status='SUPPLIED_UNVERIFIED',
        chronology_status='SUPPLIED_LOGICAL_TICKS_UNVERIFIED',
        independence_status='SUPPLIED_UNVERIFIED', controller_closure='SUPPLIED_UNVERIFIED',
        independence_over_study_span='NOT_ESTABLISHED',
        evidence_status='REFERENCES_ONLY_UNVERIFIED',
        privacy_permission_status='SUPPLIED_UNVERIFIED', semantic_assessment='NOT_PERFORMED',
        statistical_analysis='NOT_PERFORMED', stopping_assessment='NOT_PERFORMED',
        scope='OFFLINE_SUPPLIED_PLAN_TRACE_STRUCTURE_ONLY')
