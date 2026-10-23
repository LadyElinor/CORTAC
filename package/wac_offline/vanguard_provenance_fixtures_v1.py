"""Exposed synthetic provenance controls. These helpers do NOT enroll real trust."""
from copy import deepcopy
from hashlib import sha256

from .vanguard_fixtures_v1 import fixture as review_fixture, rebind
from .vanguard_review_v1 import ReviewError, fingerprint
from .vanguard_provenance_v1 import INVENTORY_VERSION, inspect_provenance


def freeze_synthetic_inventory(case, *, frozen_review=False):
    """Fixture authoring only: never use this operation to accept a candidate pin."""
    packet, context = case['packet'], case['context']
    case['inventory'] = dict(
        schema=INVENTORY_VERSION, id='synthetic-inventory', version=1,
        binding=deepcopy(packet['binding']), source_cutoff=context['source_cutoff'],
        established_on='2020-01-04', valid_until='2020-01-31',
        sources=[dict(id=s['id'], version=s['version'], digest=fingerprint(s),
                      artifact_digest=s['artifact_digest'], origin_group=s['origin_group'],
                      available=deepcopy(s['available']), valid_until='2020-01-31',
                      provenance_refs=['urn:synthetic:custody:' + s['id']])
                 for s in packet['record']['sources']],
        review_input_commitment=[dict(record_digest=fingerprint(packet['record']),
                                      context_digest=fingerprint(context))] if frozen_review else [])
    case['expected_inventory_digest'] = fingerprint(case['inventory'])


def fixture(*, frozen_review=False):
    p, c = review_fixture()
    raw = b'SYNTHETIC log: Warning received; no owner assigned; control failed.\n'
    artifact_digest = sha256(raw).hexdigest()
    p['record']['sources'][0]['artifact_digest'] = artifact_digest
    rebind(p, c)
    case = dict(packet=p, context=c, as_of='2020-01-04', artifacts={artifact_digest: raw})
    freeze_synthetic_inventory(case, frozen_review=frozen_review)
    return case


def controls():
    cases = {}

    def add(name, mutate, expected, *, frozen_review=False):
        case = fixture(frozen_review=frozen_review)
        mutate(case)
        cases[name] = (case, expected)

    def rewrite_claim(case):
        case['packet']['record']['claims'][0]['text'] = 'An entirely different, unverified narrative.'
        rebind(case['packet'], case['context'])

    def rewrite_source(case):
        case['packet']['record']['sources'][0]['passage'] = 'Changed substantive source account.'
        rebind(case['packet'], case['context'])

    def rewrite_inventory(case):
        old_pin = case['expected_inventory_digest']
        rewrite_source(case)
        freeze_synthetic_inventory(case)
        case['expected_inventory_digest'] = old_pin

    def replace_pin_too(case):
        rewrite_source(case)
        freeze_synthetic_inventory(case)

    def mutate_source(case, **values):
        case['packet']['record']['sources'][0].update(values)
        rebind(case['packet'], case['context'])

    def stale_source(case):
        case['inventory']['sources'][0]['valid_until'] = '2020-01-03'
        case['expected_inventory_digest'] = fingerprint(case['inventory'])

    def derivatives(case):
        # Different bytes copying one underlying account, but mislabeled *before*
        # pinning. The checker must not claim to discover hidden shared origin.
        s = deepcopy(case['packet']['record']['sources'][0])
        raw = b'SYNTHETIC derivative: The same log says a warning was ignored.\n'
        s.update(id='derivative', origin_group='misleading-independent-label',
                 passage='A retelling of the same account.', artifact_digest=sha256(raw).hexdigest())
        case['packet']['record']['sources'].append(s)
        case['artifacts'][s['artifact_digest']] = raw
        rebind(case['packet'], case['context'])
        freeze_synthetic_inventory(case)

    def unknown_reviewer(case):
        case['context']['principals'][6]['controller'] = None
        rebind(case['packet'], case['context'])

    def changed_cutoff(case):
        case['context']['source_cutoff'] = '2020-01-04'
        rebind(case['packet'], case['context'])

    def changed_case(case):
        case['context']['expected']['case_id'] = 'unrelated-case'
        rebind(case['packet'], case['context'])

    ok = 'PINNED_PROVENANCE_CONSISTENT'
    add('unchanged_source_scope', lambda c: None, ok)
    add('unchanged_frozen_review', lambda c: None, ok, frozen_review=True)
    add('claim_rewrite_source_only_limitation', rewrite_claim, ok)
    add('claim_rewrite_frozen_review_detected', rewrite_claim, 'REJECTED', frozen_review=True)
    add('source_joint_rewrite_detected', rewrite_source, 'REJECTED')
    add('inventory_joint_rewrite_fixed_pin_detected', rewrite_inventory, 'REJECTED')
    add('replacement_of_pin_itself_limitation', replace_pin_too, ok)
    add('origin_relabel_after_pin_detected', lambda c: mutate_source(c, origin_group='new-origin'), 'REJECTED')
    add('different_bytes_derivative_before_pin_limitation', derivatives, ok)
    add('source_version_rewrite_detected', lambda c: mutate_source(c, version=2), 'REJECTED')
    add('declared_artifact_rewrite_detected', lambda c: mutate_source(c, artifact_digest='a'*64), 'REJECTED')
    add('artifact_bytes_changed_detected', lambda c: c['artifacts'].update(
        {next(iter(c['artifacts'])): b'Altered bytes'}), 'REJECTED')
    add('inventory_unavailable', lambda c: c.update(inventory=None), 'INVENTORY_UNAVAILABLE')
    add('pin_unavailable', lambda c: c.update(expected_inventory_digest=None), 'INVENTORY_PIN_UNAVAILABLE')
    add('date_unavailable', lambda c: c.update(as_of=None), 'EVALUATION_DATE_UNAVAILABLE')
    add('artifact_unavailable', lambda c: c.update(artifacts=None), 'PINNED_PROVENANCE_INCOMPLETE')
    add('inventory_expired', lambda c: c.update(as_of='2020-02-01'), 'INVENTORY_EXPIRED')
    add('source_expired', stale_source, 'SOURCE_EXPIRED:log')
    add('as_of_backdated_before_review', lambda c: c.update(as_of='2020-01-03'), 'REJECTED')
    add('changed_provenance_reference_detected', lambda c: c['inventory']['sources'][0].update(
        provenance_refs=['urn:replacement']), 'REJECTED')
    add('reviewer_unknown_hold_propagates', unknown_reviewer, 'REVIEW:REVIEW_CONTROL_UNKNOWN')
    add('cutoff_rewrite_detected', changed_cutoff, 'REJECTED')
    add('case_rewrite_detected', changed_case, 'REJECTED')
    return cases


def integration_report():
    rows = []
    for name, (case, expected) in controls().items():
        try:
            report = inspect_provenance(**case)
            observed = expected if expected in report['blockers'] else report['status']
        except ReviewError:
            observed = 'REJECTED'
        rows.append(dict(control=name, expected=expected, observed=observed, matched=expected == observed))
    return dict(schema='cortac.vanguard.provenance_controls.v1', controls=len(rows), results=rows,
                all_fixed_structural_outcomes=all(r['matched'] for r in rows),
                authority='NONE', execution_enabled=False, controller_closure='SUPPLIED_UNVERIFIED',
                authentication='NOT_ESTABLISHED', factual_truth='NOT_ESTABLISHED',
                actual_independence='NOT_ESTABLISHED', semantic_assessment='NOT_PERFORMED',
                synthetic_inputs=True, real_model_calls=0, real_external_principals=0,
                empirical_success_established=False)
