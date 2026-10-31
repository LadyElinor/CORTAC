"""Exposed A1/Vanguard interoperability controls; no empirical or authority claim."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'package'))
from wac_offline.commonwealth_intake_v1 import (FIELDS, OPTIONS, LINK_SCHEMA, IntakeError,
    build_intake, inspect_pair)
from wac_offline.vanguard_fixtures_v1 import controls
from wac_offline.vanguard_review_v1 import fingerprint


def a1_corpus(packet):
    rows = [('terra_export', packet), ('empty_answers', dict(schema=packet['schema'], answers={}))]
    for key in FIELDS:
        p = deepcopy(packet)
        p['answers'].pop(key)
        rows.append(('missing_' + key, p))
    for key, values in OPTIONS.items():
        for value in values:
            p = deepcopy(packet)
            p['answers'][key] = value
            rows.append((key + '_' + value, p))
    changes = [lambda p: p.update(schema='warranted-authority-review-2'),
        lambda p: p.update(authority='GRANTED'), lambda p: p.update(permits_execution=True),
        lambda p: p.update(answers=[]), lambda p: p['answers'].update(unknown='text'),
        lambda p: p['answers'].update(stage='unsupported'),
        lambda p: p['answers'].update(case=None), lambda p: p['answers'].update(case=True),
        lambda p: p['answers'].update(case=1), lambda p: p['answers'].update(case=[]),
        lambda p: p['answers'].update(case='x' * 4001),
        lambda p: p['answers'].update({k: '\U0001f600' * 4000 for k in FIELDS if k not in OPTIONS})]
    for i, change in enumerate(changes):
        p = deepcopy(packet)
        change(p)
        rows.append(('malformed_' + str(i), p))
    # No result envelope from either side is a source packet or an authority token.
    rows.append(('adapter_intake_not_a1', build_intake(packet)))
    return rows


def cross_project(checkout, packet):
    manifest = json.loads((ROOT / 'provenance/commonwealth_intake_v1.json').read_text())
    observed_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    if observed_commit != manifest['commonwealth_commit']:
        raise ValueError('Commonwealth reference revision is incompatible with pinned control')
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                    cwd=checkout, text=True).strip()
    if dirty:
        raise ValueError('Commonwealth reference contains tracked modifications')
    for path, expected in manifest['commonwealth_files'].items():
        if hashlib.sha256((checkout / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Commonwealth reference hash mismatch: ' + path)
    # Explicit operator-supplied, pinned local development checkout only. The
    # production adapter never imports Commonwealth or its simulation engines.
    sys.path.insert(0, str(checkout))
    from commonwealth.authority_v1.records import FIELDS as original_fields, OPTIONS as original_options, review
    if tuple(original_fields) != FIELDS or original_options != OPTIONS:
        raise ValueError('A1 executable field/enum contract drift')
    results = []
    for name, supplied in a1_corpus(packet):
        try:
            expected = review(supplied)
        except (ValueError, TypeError):
            expected = None
        try:
            observed = build_intake(supplied)
        except IntakeError:
            observed = None
        matched = (expected is None) == (observed is None)
        if expected is not None and observed is not None:
            matched = matched and expected['packet_digest'] == observed['packet_digest']
            matched = matched and expected['missing_fields'] == observed['missing_answers']
            matched = matched and not expected['permits_execution'] and not observed['execution_enabled']
        results.append(dict(control=name, matched=matched,
                            a1_accepted=expected is not None, adapter_accepted=observed is not None))
    return dict(status='PASSED' if all(r['matched'] for r in results) else 'FAILED',
                reference_revision=observed_commit, controls=len(results), results=results,
                scope='Exposed input, digest and missing-field comparison; not execution or semantic compatibility.')


def integration_report(checkout=None):
    packet = json.loads((ROOT / 'vanguard/commonwealth/terra-a1-packet.json').read_text())
    context = json.loads((ROOT / 'vanguard/commonwealth/source-context.json').read_text())
    intake = build_intake(packet, context)
    rows = []
    for name, (p, c, expected) in controls().items():
        link = dict(schema=LINK_SCHEMA, intake_digest=fingerprint(intake),
                    packet_digest=fingerprint(p), context_digest=fingerprint(c),
                    relationship_basis='Unrelated synthetic fixtures; byte-binding control only.')
        try:
            report = inspect_pair(intake, p, c, link)
            observed = expected if 'VANGUARD:' + expected in report['blockers'] else report['vanguard']['status']
            if report['authority'] != 'NONE' or report['execution_enabled'] is not False or not report['blockers']:
                observed = 'AUTHORITY_OR_EVIDENCE_BOUNDARY_FAILURE'
        except IntakeError:
            observed = 'REJECTED'
        rows.append(dict(control=name, expected=expected, observed=observed, matched=observed == expected))
    cross = cross_project(Path(checkout).resolve(), packet) if checkout else dict(
        status='NOT_RUN', reason='No separately pinned Commonwealth checkout supplied.')
    return dict(schema='cortac.commonwealth.controls.v1', controls=len(rows), results=rows,
                all_fixed_structural_outcomes=all(row['matched'] for row in rows),
                cross_project=cross, authority='NONE', execution_enabled=False,
                controller_closure='SUPPLIED_UNVERIFIED', semantic_assessment='NOT_PERFORMED',
                synthetic_inputs=True, real_model_calls=0, real_external_principals=0,
                empirical_success_established=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commonwealth-checkout', type=Path)
    args = parser.parse_args()
    report = integration_report(args.commonwealth_checkout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['all_fixed_structural_outcomes'] and report['cross_project']['status'] != 'FAILED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
