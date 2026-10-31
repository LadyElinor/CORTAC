"""Preserve A1 declarations and inspect explicitly supplied Vanguard pairs.

No evidence completion, reviewer creation, authorization or execution interface.
Schema compatibility is pinned in provenance/commonwealth_intake_v1.json.
"""
from copy import deepcopy
from datetime import date
import json
import re

from .vanguard_review_v1 import ReviewError, fingerprint, inspect_review

ADAPTER_VERSION = 'commonwealth-vanguard-intake-1.0.0'
SCHEMA = 'cortac.commonwealth.intake.v1'
CONTEXT_SCHEMA = 'cortac.commonwealth.source_context.v1'
LINK_SCHEMA = 'cortac.commonwealth.vanguard_link.v1'
A1_SCHEMA = 'warranted-authority-review-1'
A1_LIMIT = 120000
CONTEXT_LIMIT = 32000
INTAKE_LIMIT = 180000
FILE_LIMIT = 3 * 1048576

# Exact A1 answer contract. These names are not Vanguard evidence fields.
FIELDS = tuple('case assessment legitimacy stage source_record source_status '
    'counterevidence action proposer decision_maker authority_basis authority_status '
    'affected_people representation trigger scope expiry dissent reversal reviewer '
    'public_language working_language analyst_language'.split())
OPTIONS = {
    'legitimacy': ('not specified', 'public acceptance', 'moral justification',
                   'electoral validity', 'legal authority', 'not applicable'),
    'stage': ('not established', 'hypothesis', 'proposal', 'commitment',
              'authorization', 'execution', 'outcome'),
    'source_status': ('not reviewed', 'reported excerpt only', 'primary record reviewed'),
    'authority_status': ('not established', 'claimed', 'disputed', 'supported by cited instrument'),
}
REQUIREMENTS = (
    'CASE_POLICY_AND_PREDECESSOR_ANCHORS', 'DECISION_SCOPE_AND_UNCERTAIN_DATES',
    'SOURCE_INVENTORY_AND_ORIGINAL_ARTIFACTS', 'CLAIM_INVENTORY_AND_IDENTITIES',
    'SOURCE_LINKED_OBJECTIONS_AND_DISPOSITIONS', 'REASONED_ANALYSIS_AND_ALTERNATIVES',
    'SEPARATELY_AUTHORED_DISPOSITION_AND_INTERNAL_DRAFT',
    'CURRENT_RECORD_ROLE_REVIEWS', 'PRINCIPALS_CONTROLLERS_AND_CONFLICTS',
    'MANDATE_SCOPE_EXPIRY_AND_REVOCATION', 'AFFECTED_POPULATION_AND_REPRESENTATION',
    'SOURCE_AUTHENTICITY_AND_INVENTORY_COMPLETENESS',
)
CONTEXT_FIELDS = ('schema', 'packet_digest', 'locator', 'version', 'origin_group',
                  'event_interval', 'publication_interval', 'scope', 'original_artifact_digest')


class IntakeError(ValueError):
    """Malformed, unsupported or changed intake material."""


def _require(ok, message):
    if not ok:
        raise IntakeError(message)


def _object(value, keys, name):
    _require(type(value) is dict and set(value) == set(keys), name + ': missing or unknown fields')


def _text(value, name):
    _require(type(value) is str and bool(value.strip()) and len(value) <= 4000,
             name + ': bounded nonblank string required')


def _digest(value, name):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
             name + ': lowercase SHA-256 required')


def _bounded(value, limit):
    # Bound depth/nodes before serialization; reject Python-only values as well as
    # JSON nonfinite numbers. No recursion into arbitrary caller objects.
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(depth <= 24 and count <= 30000, 'JSON depth or node limit exceeded')
        if type(item) is dict:
            _require(len(item) <= 256, 'JSON object size limit exceeded')
            _require(all(type(key) is str for key in item), 'JSON string keys required')
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            _require(len(item) <= 256, 'JSON list size limit exceeded')
            pending.extend((child, depth + 1) for child in item)
        else:
            _require(type(item) in (str, int, float, bool, type(None)), 'JSON values required')
            _require(type(item) is not str or len(item) <= limit, 'JSON string byte limit exceeded')
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    except (TypeError, ValueError, RecursionError) as exc:
        raise IntakeError('invalid JSON value') from exc
    _require(len(raw) <= limit, 'canonical JSON byte limit exceeded')
    return raw


def _hash(value):
    try:
        return fingerprint(value)
    except ReviewError as exc:
        raise IntakeError(str(exc)) from exc


def validate_a1(packet):
    """A1 input only. No interpretation, defaults or field completion."""
    _object(packet, ('schema', 'answers'), 'A1 packet')
    _require(packet['schema'] == A1_SCHEMA, 'unsupported A1 schema')
    answers = packet['answers']
    _require(type(answers) is dict and set(answers) <= set(FIELDS), 'unknown A1 answer fields')
    for key, value in answers.items():
        _require(type(value) is str and len(value) <= 4000, 'bounded string answers required')
        _require(key not in OPTIONS or value in OPTIONS[key], 'unknown A1 answer option')
    _bounded(packet, A1_LIMIT)


def _interval(value, name):
    _object(value, ('earliest', 'latest'), name)
    for key in ('earliest', 'latest'):
        try:
            _require(type(value[key]) is str and date.fromisoformat(value[key]).isoformat() == value[key],
                     name + ': canonical YYYY-MM-DD required')
        except (TypeError, ValueError) as exc:
            raise IntakeError(name + ': canonical YYYY-MM-DD required') from exc
    _require(value['earliest'] <= value['latest'], name + ': reversed interval')


def _context(context, packet_digest):
    if context is None:
        return ['SOURCE_CONTEXT_MISSING']
    _object(context, CONTEXT_FIELDS, 'source context')
    _require(context['schema'] == CONTEXT_SCHEMA, 'unsupported source context schema')
    _digest(context['packet_digest'], 'packet_digest')
    _require(context['packet_digest'] == packet_digest, 'source context packet digest mismatch')
    _require(context['scope'] in ('SYNTHETIC', 'UNESTABLISHED', 'DECLARED_EXTERNAL'),
             'unsupported source scope')
    for key in ('locator', 'version', 'origin_group'):
        if context[key] is not None:
            _text(context[key], key)
    for key in ('event_interval', 'publication_interval'):
        if context[key] is not None:
            _interval(context[key], key)
    if context['original_artifact_digest'] is not None:
        _digest(context['original_artifact_digest'], 'original_artifact_digest')
    _bounded(context, CONTEXT_LIMIT)
    gaps = ['SOURCE_CONTEXT_MISSING:' + key for key in CONTEXT_FIELDS if context[key] is None]
    if context['scope'] == 'UNESTABLISHED':
        gaps.append('SOURCE_SCOPE_UNESTABLISHED')
    return gaps


def build_intake(packet, source_context=None):
    """Return a deterministic, unverified snapshot; inputs are not mutated.

    Hashes bind supplied JSON, never original evidence or authenticated identity.
    A supplied original_artifact_digest remains a declaration, not a checked hash.
    """
    validate_a1(packet)
    pd = _hash(packet)
    provenance_gaps = _context(source_context, pd)
    answers = packet['answers']
    missing = [key for key in FIELDS if not answers.get(key, '').strip()
               or (key in OPTIONS and answers.get(key) == OPTIONS[key][0])]
    result = dict(schema=SCHEMA, adapter_version=ADAPTER_VERSION,
        source_packet=deepcopy(packet), source_context=deepcopy(source_context),
        packet_digest=pd, source_context_digest=_hash(source_context),
        missing_answers=missing, provenance_gaps=provenance_gaps,
        unsupported_vanguard_requirements=list(REQUIREMENTS),
        status='INTAKE_REQUIRES_EVIDENCE', authority='NONE', execution_enabled=False,
        controller_closure='SUPPLIED_UNVERIFIED', source_authentication='NOT_PERFORMED',
        original_artifact_verification='NOT_PERFORMED', semantic_assessment='NOT_PERFORMED')
    _bounded(result, INTAKE_LIMIT)
    return result


def inspect_intake(intake):
    """Recompute all derived fields; altered result flags cannot be imported."""
    _bounded(intake, INTAKE_LIMIT)
    _require(type(intake) is dict and 'source_packet' in intake and 'source_context' in intake,
             'expected intake envelope')
    expected = build_intake(intake['source_packet'], intake['source_context'])
    _require(_bounded(intake, INTAKE_LIMIT) == _bounded(expected, INTAKE_LIMIT),
             'intake schema, version or derived content mismatch')
    return expected


def inspect_pair(intake, packet, context, link):
    """Inspect two separately supplied records without modifying or completing them.

    An explicit caller link binds bytes only. It never establishes same-case
    identity, scope equivalence or that Vanguard reviewers considered the A1 text.
    """
    checked = inspect_intake(intake)
    _bounded(dict(packet=packet, context=context, link=link), FILE_LIMIT)
    _object(link, ('schema', 'intake_digest', 'packet_digest', 'context_digest',
                   'relationship_basis'), 'link')
    _require(link['schema'] == LINK_SCHEMA, 'unsupported link schema')
    _text(link['relationship_basis'], 'relationship_basis')
    for key, value in (('intake_digest', intake), ('packet_digest', packet), ('context_digest', context)):
        _digest(link[key], key)
        _require(link[key] == _hash(value), 'pair link digest mismatch: ' + key)
    try:
        target = inspect_review(packet, context)
    except ReviewError as exc:
        raise IntakeError('VANGUARD: ' + str(exc)) from exc
    supplied = checked['source_context']
    if supplied is not None and supplied['scope'] == 'SYNTHETIC':
        _require(packet['record']['mode'] == 'SYNTHETIC', 'synthetic source scope promotion')
    # Neither a consistent target nor full prose can discharge these obligations.
    blockers = ['RELATIONSHIP_NOT_INDEPENDENTLY_ESTABLISHED',
                'A1_OBJECTIONS_AND_CONTEXT_NOT_SEMANTICALLY_REVIEWED',
                'INDEPENDENT_EVIDENCE_AND_GOVERNANCE_NOT_ESTABLISHED']
    blockers.extend('INTAKE:' + gap for gap in checked['provenance_gaps'])
    blockers.extend('A1_MISSING:' + field for field in checked['missing_answers'])
    blockers.extend('VANGUARD:' + gap for gap in target['blockers'])
    return dict(schema='cortac.commonwealth.pair_inspection.v1', adapter_version=ADAPTER_VERSION,
        status='SUPPLIED_PAIR_REQUIRES_EVIDENCE', intake=checked, vanguard=target,
        link=deepcopy(link), blockers=blockers, authority='NONE', execution_enabled=False,
        relationship='CALLER_ASSERTED_ONLY', controller_closure='SUPPLIED_UNVERIFIED',
        semantic_assessment='NOT_PERFORMED', governance_approval='NOT_ESTABLISHED')


def read_json(path, maximum=FILE_LIMIT):
    """Bound raw bytes as well as parsed JSON; duplicate keys never disappear."""
    from pathlib import Path
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    _require(len(raw) <= maximum, 'input byte limit exceeded')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def nonfinite(value):
        raise IntakeError('nonfinite JSON value: ' + value)

    result = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    _bounded(result, maximum)
    return result


def main(argv=None):
    """Read local files; print intake/inspection JSON only. No persistence or calls."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('intake')
    create.add_argument('packet')
    create.add_argument('--source-context')
    sub.add_parser('inspect').add_argument('file')
    sub.add_parser('pair').add_argument('file')
    args = parser.parse_args(argv)
    try:
        if args.command == 'intake':
            context = read_json(args.source_context, CONTEXT_LIMIT) if args.source_context else None
            report = build_intake(read_json(args.packet, A1_LIMIT), context)
        elif args.command == 'inspect':
            report = inspect_intake(read_json(args.file, INTAKE_LIMIT))
        else:
            supplied = read_json(args.file)
            _object(supplied, ('intake', 'packet', 'context', 'link'), 'pair file')
            report = inspect_pair(**supplied)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps(dict(status='REJECTED', reason=str(exc),
                             authority='NONE', execution_enabled=False)))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    # Every valid intake/pair still requires independently established evidence.
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
