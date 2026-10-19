"""Opt-in Vanguard packet inspection. No retrieval, model calls or effect API."""
from datetime import date
import json
import re

from .ops_trace_v1 import TraceError, digest, inspect_trace

VERSION = 'cortac.vanguard.review.v1'
CONTEXT_VERSION = 'cortac.vanguard.context.v1'
ROLES = ('SCOUT', 'ARCHIVIST', 'IMPACT_ANALYST', 'COUNTERARGUMENT_REVIEWER',
         'REMEDY_DESIGNER', 'CHALLENGE_DRAFTER', 'AUDIT_REVIEWER')


class ReviewError(ValueError):
    """Malformed, stale or contradictory supplied records."""


def fingerprint(value):
    """Use the OPS1 bounded canonical JSON digest; not an authentication proof."""
    try:
        return digest(value)
    except TraceError as exc:
        raise ReviewError(str(exc)) from exc


def _shape(value, spec, path='record'):
    if isinstance(spec, dict):
        if type(value) is not dict or set(value) != set(spec):
            raise ReviewError(path + ': missing or unknown fields')
        for key in spec:
            _shape(value[key], spec[key], path + '.' + key)
    elif isinstance(spec, list):
        if type(value) is not list or not spec[1] <= len(value) <= 256:
            raise ReviewError(path + ': invalid list length')
        for i, item in enumerate(value):
            _shape(item, spec[0], path + '[' + str(i) + ']')
            if item in value[:i]:
                raise ReviewError(path + ': duplicate item')
    elif isinstance(spec, tuple):
        if type(value) is not str or value not in spec:
            raise ReviewError(path + ': unsupported value')
    elif spec == 'version':
        if type(value) is not int or not 1 <= value <= 2**63 - 1:
            raise ReviewError(path + ': invalid version')
    elif spec == 'controller':
        if value is not None:
            _shape(value, 'text', path)
    else:
        if type(value) is not str or not value.strip() or len(value) > 8192:
            raise ReviewError(path + ': expected bounded nonblank string')
        if spec == 'digest' and re.fullmatch('[0-9a-f]{64}', value) is None:
            raise ReviewError(path + ': invalid digest')
        if spec == 'date':
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError('noncanonical date')
            except ValueError as exc:
                raise ReviewError(path + ': expected YYYY-MM-DD') from exc


REF = dict(id='text', version='version', digest='digest')
BINDING = dict(case_id='text', policy_digest='digest', version='version', predecessor_digest='digest')
INTERVAL = dict(earliest='date', latest='date')
SOURCE = dict(id='text', version='version', origin_group='text', url='text',
              locator='text', passage='text', available=INTERVAL,
              artifact_digest='digest')
OBJECTION = dict(id='text', state=('OPEN', 'RESOLVED_REPORTED'), reason='text', source_ids=['text', 1])
CLAIM = dict(id='text', version='version', subject='text', identity=('RESOLVED_REPORTED', 'AMBIGUOUS'),
             kind=('RECORD_CONTENT', 'ALLEGATION', 'INTERPRETATION', 'OFFICIAL_FINDING'),
             text='text', source_ids=['text', 1], objections=[OBJECTION, 0])
ANALYSIS = dict(concern='text', harm_criterion='text', affected_groups='text', benefits='text',
                alternatives='text', chronology='text', counterargument='text', remedy='text',
                intervention_costs='text', outcome_measure='text', discriminating_test='text',
                limitations='text', correction_route='text')
RECORD = dict(mode=('RETROSPECTIVE', 'PROSPECTIVE', 'SYNTHETIC'),
              decision=dict(title='text', authority='text', jurisdiction='text', objective='text',
                            status='text', occurred=INTERVAL),
              sources=[SOURCE, 1], claims=[CLAIM, 1], analysis=ANALYSIS,
              disposition=('RETAIN_CONCERN', 'CLOSE_CONCERN', 'SEEK_EVIDENCE'),
              disposition_reason='text',
              draft=dict(kind=('INTERNAL_REVIEW', 'NO_CHALLENGE'), audience='text', text='text'))
CONTEXT = dict(schema=(CONTEXT_VERSION,), expected=BINDING, now='date', source_cutoff='date',
               sources=[REF, 1], claims=[REF, 1],
               principals=[dict(id='text', controller='controller'), 1], party_ids=['text', 0])
PACKET = dict(schema=(VERSION,), binding=BINDING, context_digest='digest', record=RECORD,
              reviews=[dict(role=ROLES, principal='text', record_digest='digest', assessment='text'), 0])


def _index(items, key='id'):
    result = {item[key]: item for item in items}
    if len(result) != len(items):
        raise ReviewError('duplicate identity: ' + key)
    return result


def _bound(items, anchors):
    indexed, expected = _index(items), _index(anchors)
    if set(indexed) != set(expected):
        raise ReviewError('inventory mismatch')
    for key, item in indexed.items():
        if item['version'] != expected[key]['version'] or fingerprint(item) != expected[key]['digest']:
            raise ReviewError('stale source or claim: ' + key)
    return indexed


def inspect_review(packet, context):
    """Check supplied dependencies only. Never judge truth or grant authority."""
    pd, cd = fingerprint(packet), fingerprint(context)
    _shape(packet, PACKET, 'packet')
    _shape(context, CONTEXT, 'context')
    if packet['binding'] != context['expected'] or packet['context_digest'] != cd:
        raise ReviewError('caller binding mismatch')
    record = packet['record']
    rd = fingerprint(record)
    sources = _bound(record['sources'], context['sources'])
    claims = _bound(record['claims'], context['claims'])
    principals = _index(context['principals'])
    if not set(context['party_ids']) <= set(principals):
        raise ReviewError('unknown party')
    if context['source_cutoff'] > context['now']:
        raise ReviewError('cutoff after review date')
    intervals = [record['decision']['occurred']] + [s['available'] for s in sources.values()]
    if any(i['earliest'] > i['latest'] for i in intervals):
        raise ReviewError('reversed date interval')
    if record['mode'] == 'PROSPECTIVE' and context['source_cutoff'] > record['decision']['occurred']['earliest']:
        raise ReviewError('prospective cutoff after earliest decision date')
    if record['mode'] != 'PROSPECTIVE' and record['decision']['occurred']['latest'] > context['now']:
        raise ReviewError('retrospective decision after review date')
    blockers = set()
    for source in sources.values():
        # An uncertain interval crossing the cutoff cannot establish availability.
        if source['available']['latest'] > context['source_cutoff']:
            blockers.add('SOURCE_OUTSIDE_CUTOFF')
    origins_by_artifact = {}
    for source in sources.values():
        origins_by_artifact.setdefault(source['artifact_digest'], set()).add(source['origin_group'])
    if any(len(groups) > 1 for groups in origins_by_artifact.values()):
        blockers.add('SAME_ARTIFACT_MULTIPLE_ORIGINS')
    for claim in claims.values():
        if not set(claim['source_ids']) <= set(sources):
            raise ReviewError('unknown claim source')
        if claim['identity'] == 'AMBIGUOUS':
            blockers.add('IDENTITY_AMBIGUOUS')
        _index(claim['objections'])
        for objection in claim['objections']:
            if not set(objection['source_ids']) <= set(sources):
                raise ReviewError('unknown objection source')
            if objection['state'] == 'OPEN':
                blockers.add('MATERIAL_OBJECTION_OPEN')
    reviews = _index(packet['reviews'], 'role')
    if set(reviews) != set(ROLES):
        blockers.add('ROLE_REVIEW_MISSING')
    for review in reviews.values():
        if review['principal'] not in principals:
            raise ReviewError('unknown reviewer')
        if review['record_digest'] != rd:
            raise ReviewError('review predates record amendment')
    separated = ('CHALLENGE_DRAFTER', 'COUNTERARGUMENT_REVIEWER', 'AUDIT_REVIEWER')
    if all(role in reviews for role in separated):
        ids = [reviews[role]['principal'] for role in separated]
        controllers = [principals[i]['controller'] for i in ids]
        parties = [principals[i]['controller'] for i in context['party_ids']]
        if None in controllers or None in parties:
            blockers.add('REVIEW_CONTROL_UNKNOWN')
        if (len(set(ids)) != len(ids) or len(set(controllers)) != len(controllers)
                or set(ids) & set(context['party_ids'])
                or (set(controllers) - {None}) & (set(parties) - {None})):
            blockers.add('DECLARED_REVIEW_CONTROL_CONFLICT')
    if record['disposition'] == 'SEEK_EVIDENCE':
        blockers.add('MORE_EVIDENCE_REQUESTED')
    if record['disposition'] == 'CLOSE_CONCERN' and record['draft']['kind'] != 'NO_CHALLENGE':
        raise ReviewError('closed concern retains challenge')
    return dict(schema='cortac.vanguard.inspection.v1',
                status='SUPPLIED_REVIEW_INCOMPLETE' if blockers else 'SUPPLIED_REVIEW_CONSISTENT',
                blockers=sorted(blockers), packet_digest=pd, context_digest=cd, record_digest=rd,
                supplied_origin_groups=len({s['origin_group'] for s in sources.values()}),
                disposition=record['disposition'], authority='NONE', execution_enabled=False,
                controller_closure='SUPPLIED_UNVERIFIED', inventory_scope='SUPPLIED_INVENTORY_ONLY',
                freshness='CALLER_ANCHOR_ONLY', semantic_assessment='NOT_PERFORMED',
                factual_truth='NOT_ESTABLISHED', actual_independence='NOT_ESTABLISHED',
                remedy_effectiveness='NOT_ESTABLISHED', real_model_calls=0)


def inspect_ops_handoff(packet, context, trace, ops_context, link):
    """Bind a reviewed packet to a separately supplied OPS1 v1 remedy trace.

    The link records a caller assertion of relationship, not semantic equivalence.
    No conversion into findings, authority records or effect instructions occurs.
    """
    _shape(link, dict(schema=('cortac.vanguard.ops_link.v1',), packet_digest='digest',
                     context_digest='digest', trace_digest='digest', ops_context_digest='digest'), 'link')
    values = (packet, context, trace, ops_context)
    keys = ('packet_digest', 'context_digest', 'trace_digest', 'ops_context_digest')
    if any(link[k] != fingerprint(v) for k, v in zip(keys, values)):
        raise ReviewError('handoff digest mismatch')
    review = inspect_review(packet, context)
    try:
        remedy = inspect_trace(trace, ops_context)
    except TraceError as exc:
        raise ReviewError('OPS1: ' + str(exc)) from exc
    for key in ('case_id', 'policy_digest'):
        if packet['binding'][key] != trace['binding'][key]:
            raise ReviewError('handoff case or policy mismatch')
    blockers = ['REVIEW:' + b for b in review['blockers']] + ['OPS1:' + b for b in remedy['blockers']]
    if packet['record']['disposition'] != 'RETAIN_CONCERN':
        blockers.append('REMEDY_HANDOFF_REQUIRES_RETAINED_CONCERN')
    return dict(schema='cortac.vanguard.ops_handoff.v1',
                status='SUPPLIED_HANDOFF_INCOMPLETE' if blockers else 'SUPPLIED_HANDOFF_CONSISTENT',
                blockers=blockers, review=review, remedy=remedy,
                authority='NONE', execution_enabled=False, relationship='CALLER_ASSERTED_ONLY',
                semantic_assessment='NOT_PERFORMED', controller_closure='SUPPLIED_UNVERIFIED')


def main(argv=None):
    """Inspect one local {packet, context} JSON file; no URLs or remote writes."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args(argv)
    try:
        with args.file.open('rb') as stream:
            raw = stream.read(1048577)
        if len(raw) > 1048576:
            raise ReviewError('input too large')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ReviewError('duplicate JSON key')
                result[key] = value
            return result
        supplied = json.loads(raw, object_pairs_hook=unique)
        if type(supplied) is not dict or set(supplied) != {'packet', 'context'}:
            raise ReviewError('expected packet and context')
        report = inspect_review(supplied['packet'], supplied['context'])
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps(dict(status='REJECTED', reason=str(exc), authority='NONE', execution_enabled=False)))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'SUPPLIED_REVIEW_CONSISTENT' else 3


if __name__ == '__main__':
    raise SystemExit(main())
