"""Optional offline comparisons to an externally pinned inventory; no authority."""
from hashlib import sha256
import json

from .vanguard_review_v1 import (
    BINDING, INTERVAL, ReviewError, _index, _shape, fingerprint,
    inspect_ops_handoff, inspect_review,
)

INVENTORY_VERSION = 'cortac.vanguard.source_inventory.v1'
VERSION = 'cortac.vanguard.provenance.v1'
MAX_JSON_BYTES = 1048576
MAX_ARTIFACT_BYTES = 16 * 1048576
MAX_TOTAL_ARTIFACT_BYTES = 64 * 1048576
ANCHOR = dict(id='text', version='version', digest='digest',
              artifact_digest='digest', origin_group='text', available=INTERVAL,
              provenance_refs=['text', 1], valid_until='date')
INVENTORY = dict(schema=(INVENTORY_VERSION,), id='text', version='version',
                 binding=BINDING, source_cutoff='date', established_on='date',
                 valid_until='date', sources=[ANCHOR, 1],
                 review_input_commitment=[dict(record_digest='digest', context_digest='digest'), 0])


class ProvenanceError(ReviewError):
    """Malformed input or a contradiction with the supplied external pin."""


def inspect_provenance(packet, context, inventory=None, *,
                       expected_inventory_digest=None, as_of=None, artifacts=None):
    """Compare pinned descriptors and raw bytes, conditionally on external trust.

    artifacts maps lowercase raw-byte SHA-256 to bytes. Inventory JSON uses the
    existing bounded OPS1/Vanguard canonical JSON digest. No arguments are mutated.
    Missing anchors are holds; contradictions raise ReviewError. No auto-enrollment.
    """
    review = inspect_review(packet, context)
    blockers = {'REVIEW:' + b for b in review['blockers']}
    report = dict(schema=VERSION, authority='NONE', execution_enabled=False,
                  controller_closure='SUPPLIED_UNVERIFIED',
                  semantic_assessment='NOT_PERFORMED', factual_truth='NOT_ESTABLISHED',
                  actual_independence='NOT_ESTABLISHED', authentication='NOT_ESTABLISHED',
                  institutional_approval='NOT_ESTABLISHED',
                  pin_custody='EXTERNAL_PREREQUISITE_NOT_VERIFIED',
                  freshness='RELATIVE_TO_SUPPLIED_DATE_AND_PIN_ONLY',
                  as_of=as_of, inventory_digest=None,
                  expected_inventory_digest=expected_inventory_digest,
                  commitment_scope='NOT_CHECKED', inventory_origin_groups=None,
                  matched_source_ids=[], verified_artifact_digests=[],
                  review=review, real_model_calls=0)

    def finish():
        report['blockers'] = sorted(blockers)
        report['status'] = ('PINNED_PROVENANCE_INCOMPLETE' if blockers
                            else 'PINNED_PROVENANCE_CONSISTENT')
        return report

    if as_of is None:
        blockers.add('EVALUATION_DATE_UNAVAILABLE')
    else:
        _shape(as_of, 'date', 'as_of')
        if context['now'] > as_of:
            raise ProvenanceError('REVIEW_AFTER_EVALUATION_DATE')
    if expected_inventory_digest is None:
        blockers.add('INVENTORY_PIN_UNAVAILABLE')
    else:
        _shape(expected_inventory_digest, 'digest', 'expected_inventory_digest')
    if inventory is None:
        blockers.add('INVENTORY_UNAVAILABLE')
    # Unpinned content is not promoted into an anchor or silently enrolled.
    if inventory is None or expected_inventory_digest is None:
        return finish()

    actual_digest = fingerprint(inventory)
    if actual_digest != expected_inventory_digest:
        raise ProvenanceError('INVENTORY_PIN_MISMATCH')
    _shape(inventory, INVENTORY, 'inventory')
    anchors = _index(inventory['sources'])
    sources = _index(packet['record']['sources'])
    if inventory['binding'] != packet['binding']:
        raise ProvenanceError('PINNED_CASE_POLICY_OR_VERSION_MISMATCH')
    if inventory['source_cutoff'] != context['source_cutoff']:
        raise ProvenanceError('PINNED_CUTOFF_MISMATCH')
    if set(anchors) != set(sources):
        raise ProvenanceError('PINNED_SOURCE_INVENTORY_MISMATCH')
    if inventory['established_on'] > inventory['valid_until']:
        raise ProvenanceError('REVERSED_INVENTORY_VALIDITY')
    if inventory['source_cutoff'] > inventory['established_on']:
        raise ProvenanceError('INVENTORY_ESTABLISHED_BEFORE_CUTOFF')
    if as_of is not None:
        if inventory['established_on'] > as_of:
            raise ProvenanceError('INVENTORY_NOT_YET_ESTABLISHED')
        if inventory['valid_until'] < as_of:
            blockers.add('INVENTORY_EXPIRED')

    commitment = inventory['review_input_commitment']
    if len(commitment) > 1:
        raise ProvenanceError('MULTIPLE_REVIEW_INPUT_COMMITMENTS')
    if commitment and commitment[0] != dict(record_digest=review['record_digest'],
                                            context_digest=review['context_digest']):
        raise ProvenanceError('PINNED_REVIEW_INPUT_MISMATCH')
    report.update(inventory_digest=actual_digest,
                  commitment_scope='FROZEN_REVIEW_INPUT' if commitment else 'SOURCE_INVENTORY_ONLY',
                  inventory_origin_groups=len({a['origin_group'] for a in anchors.values()}))

    for key in sorted(sources):
        source, anchor = sources[key], anchors[key]
        if any(source[field] != anchor[field] for field in
               ('version', 'artifact_digest', 'origin_group', 'available')):
            raise ProvenanceError('PINNED_SOURCE_BINDING_MISMATCH:' + key)
        if fingerprint(source) != anchor['digest']:
            raise ProvenanceError('PINNED_SOURCE_DESCRIPTOR_MISMATCH:' + key)
        if anchor['available']['latest'] > inventory['established_on']:
            raise ProvenanceError('SOURCE_NOT_AVAILABLE_AT_ESTABLISHMENT:' + key)
        if anchor['available']['latest'] > anchor['valid_until']:
            raise ProvenanceError('REVERSED_SOURCE_VALIDITY:' + key)
        if as_of is not None and anchor['valid_until'] < as_of:
            blockers.add('SOURCE_EXPIRED:' + key)
        report['matched_source_ids'].append(key)

    artifacts = {} if artifacts is None else artifacts
    if type(artifacts) is not dict or len(artifacts) > 256:
        raise ProvenanceError('INVALID_ARTIFACT_MAP')
    expected_artifacts = {s['artifact_digest'] for s in sources.values()}
    if not set(artifacts) <= expected_artifacts:
        raise ProvenanceError('UNEXPECTED_ARTIFACT')
    total = 0
    for key in sorted(artifacts):
        content = artifacts[key]
        if type(content) is not bytes or len(content) > MAX_ARTIFACT_BYTES:
            raise ProvenanceError('INVALID_OR_OVERSIZED_ARTIFACT:' + key)
        total += len(content)
        if total > MAX_TOTAL_ARTIFACT_BYTES:
            raise ProvenanceError('ARTIFACT_TOTAL_TOO_LARGE')
        if sha256(content).hexdigest() != key:
            raise ProvenanceError('ARTIFACT_BYTES_MISMATCH:' + key)
        report['verified_artifact_digests'].append(key)
    for key in sorted(expected_artifacts - set(artifacts)):
        blockers.add('ARTIFACT_UNAVAILABLE:' + key)
    return finish()


def inspect_pinned_ops_handoff(packet, context, trace, ops_context, link, inventory=None,
                               *, expected_inventory_digest=None, as_of=None, artifacts=None):
    """Add provenance holds to the unchanged v1 handoff; never accept cached reports."""
    provenance = inspect_provenance(packet, context, inventory,
                                    expected_inventory_digest=expected_inventory_digest,
                                    as_of=as_of, artifacts=artifacts)
    handoff = inspect_ops_handoff(packet, context, trace, ops_context, link)
    blockers = sorted(set(handoff['blockers']) |
                      {'PROVENANCE:' + b for b in provenance['blockers']})
    return dict(schema='cortac.vanguard.provenance_ops_handoff.v1',
                status='PINNED_HANDOFF_INCOMPLETE' if blockers else 'PINNED_HANDOFF_CONSISTENT',
                blockers=blockers, provenance=provenance, handoff=handoff,
                authority='NONE', execution_enabled=False,
                controller_closure='SUPPLIED_UNVERIFIED', relationship='CALLER_ASSERTED_ONLY',
                authentication='NOT_ESTABLISHED', semantic_assessment='NOT_PERFORMED',
                factual_truth='NOT_ESTABLISHED', actual_independence='NOT_ESTABLISHED',
                institutional_approval='NOT_ESTABLISHED')


def _read_json(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ProvenanceError('JSON_INPUT_TOO_LARGE')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProvenanceError('DUPLICATE_JSON_KEY')
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique)
    fingerprint(value)  # Includes rejection of nonfinite/deep/oversized JSON.
    return value


def _read_artifacts(path):
    """Only explicit operator paths; never read paths/URLs from review or inventory."""
    from pathlib import Path
    mapping = _read_json(path)
    if type(mapping) is not dict or len(mapping) > 256:
        raise ProvenanceError('INVALID_ARTIFACT_MAP')
    result, total = {}, 0
    for key, filename in mapping.items():
        _shape(key, 'digest', 'artifact_key')
        _shape(filename, 'text', 'artifact_path')
        source = Path(filename)
        if not source.is_absolute():
            source = path.parent / source
        try:
            # Avoid special devices, pipes and directories. Paths are operator input.
            if source.exists() and not source.is_file():
                raise ProvenanceError('ARTIFACT_NOT_REGULAR_FILE')
            with source.open('rb') as stream:
                content = stream.read(MAX_ARTIFACT_BYTES + 1)
        except FileNotFoundError:
            continue  # Inspector reports the expected digest as unavailable.
        if len(content) > MAX_ARTIFACT_BYTES:
            raise ProvenanceError('ARTIFACT_TOO_LARGE')
        total += len(content)
        if total > MAX_TOTAL_ARTIFACT_BYTES:
            raise ProvenanceError('ARTIFACT_TOTAL_TOO_LARGE')
        result[key] = content
    return result


def main(argv=None):
    """Read local inputs only. Exit 0=conditional match, 2=rejected, 3=incomplete."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path, help='Unchanged Vanguard v1 {packet, context}')
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--inventory-sha256', help='Independently established canonical JSON pin')
    parser.add_argument('--as-of', help='Separately supplied evaluation date YYYY-MM-DD')
    parser.add_argument('--artifact-map', type=Path, help='Operator JSON map: raw SHA-256 to local path')
    args = parser.parse_args(argv)
    try:
        supplied = _read_json(args.file)
        if type(supplied) is not dict or set(supplied) != {'packet', 'context'}:
            raise ProvenanceError('EXPECTED_PACKET_AND_CONTEXT')
        inventory, artifacts = None, None
        if args.inventory is not None:
            try:
                inventory = _read_json(args.inventory)
            except FileNotFoundError:
                pass
        # Do not access artifact paths until the inventory pin/structure is checked.
        preflight = inspect_provenance(supplied['packet'], supplied['context'], inventory,
                                       expected_inventory_digest=args.inventory_sha256,
                                       as_of=args.as_of)
        if args.artifact_map is not None and preflight['inventory_digest'] is not None:
            try:
                artifacts = _read_artifacts(args.artifact_map)
            except FileNotFoundError:
                pass
        report = inspect_provenance(supplied['packet'], supplied['context'], inventory,
                                    expected_inventory_digest=args.inventory_sha256,
                                    as_of=args.as_of, artifacts=artifacts)
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps(dict(schema=VERSION, status='REJECTED', reason=str(exc),
                              authority='NONE', execution_enabled=False,
                              controller_closure='SUPPLIED_UNVERIFIED',
                              authentication='NOT_ESTABLISHED', semantic_assessment='NOT_PERFORMED',
                              factual_truth='NOT_ESTABLISHED', actual_independence='NOT_ESTABLISHED',
                              institutional_approval='NOT_ESTABLISHED')))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'PINNED_PROVENANCE_CONSISTENT' else 3


if __name__ == '__main__':
    raise SystemExit(main())
