"""Fabricated Vanguard controls, exposed in full; not agent-performance trials."""
from copy import deepcopy

from .vanguard_review_v1 import (VERSION, CONTEXT_VERSION, ROLES, ReviewError,
                                 fingerprint, inspect_review)


def rebind(packet, context):
    """Fixture authoring only: replace caller anchors and every review binding.

    This is NOT a production re-review procedure or endorsement of amendments.
    """
    record = packet['record']
    for inventory in ('sources', 'claims'):
        context[inventory] = [dict(id=v['id'], version=v['version'], digest=fingerprint(v))
                              for v in record[inventory]]
    packet['binding'] = deepcopy(context['expected'])
    packet['context_digest'] = fingerprint(context)
    for review in packet['reviews']:
        review['record_digest'] = fingerprint(record)


def fixture(resolved=False):
    """A fictional ignored warning, or a supported decision closing the concern."""
    source = dict(id='log', version=1, origin_group='synthetic-log', url='urn:synthetic:log',
                  locator='Invented event log, entries 1-3',
                  passage=('Warning received; owner examined evidence; documented correction verified.'
                           if resolved else 'Warning received; no owner assigned; control failed.'),
                  available=dict(earliest='2020-01-03', latest='2020-01-03'),
                  artifact_digest=fingerprint('fabricated log resolved=' + str(resolved)))
    analysis = dict(concern='Was a material fictional warning given a reasoned disposition?',
        harm_criterion='A missed warning permits a preventable interruption of the fictional service.',
        affected_groups='Fictional service users and staff.', benefits='Timely processing preserves service.',
        alternatives='Assign an owner and investigate; retain current routing only with supporting evidence.',
        chronology='January 1 warning; January 2 decision; January 3 log available.',
        counterargument='The warning might be erroneous or already addressed; inspect the disposition record.',
        remedy='Require a named owner, receipt, reasoned disposition and later outcome review.',
        intervention_costs='Review time, delay and false alarms can themselves harm service.',
        outcome_measure='Fraction of synthetic material warnings with evidenced dispositions.',
        discriminating_test='A documented assessment and successful correction would weaken the concern.',
        limitations='All events, evidence, reviewers and declared controllers are fabricated.',
        correction_route='Amend the case and obtain fresh reviews of its full record.')
    claim = dict(id='warning', version=1, subject='Fictional service', identity='RESOLVED_REPORTED',
                 kind='RECORD_CONTENT', text=source['passage'], source_ids=['log'], objections=[])
    record = dict(mode='SYNTHETIC', decision=dict(title='Disposition of a fictional warning',
        authority='Fictional operations owner', jurisdiction='Synthetic exercise',
        objective='Keep service available', status='Historical fictional decision',
        occurred=dict(earliest='2020-01-02', latest='2020-01-02')),
        sources=[source], claims=[claim], analysis=analysis,
        disposition='CLOSE_CONCERN' if resolved else 'RETAIN_CONCERN',
        disposition_reason='The supplied log supports closure.' if resolved else 'The supplied log lacks a disposition.',
        draft=dict(kind='NO_CHALLENGE' if resolved else 'INTERNAL_REVIEW', audience='Fictional internal reviewer',
                   text='Close the fictional concern with the documented rationale.' if resolved
                   else 'Please assess the routing gap and proposed ownership control.'))
    principals = [dict(id=role.lower(), controller='fabricated-' + role.lower()) for role in ROLES]
    context = dict(schema=CONTEXT_VERSION,
        expected=dict(case_id='vanguard-fictional-resolved' if resolved else 'vanguard-fictional-failure',
                      policy_digest=fingerprint('fabricated policy'), version=1, predecessor_digest='0'*64),
        now='2020-01-04', source_cutoff='2020-01-03', sources=[], claims=[], principals=principals, party_ids=[])
    packet = dict(schema=VERSION, binding={}, context_digest='0'*64, record=record,
        reviews=[dict(role=role, principal=role.lower(), record_digest='0'*64,
                      assessment='Fabricated role output: inspect the supplied record; no independent review occurred.')
                 for role in ROLES])
    rebind(packet, context)
    return packet, context


def controls():
    result = {}

    def add(name, mutate, expected, refresh=True, resolved=False):
        p, c = fixture(resolved)
        mutate(p, c)
        if refresh:
            rebind(p, c)
        result[name] = (p, c, expected)

    add('ignored_warning', lambda p, c: None, 'SUPPLIED_REVIEW_CONSISTENT')
    add('supported_closure', lambda p, c: None, 'SUPPLIED_REVIEW_CONSISTENT', resolved=True)
    add('unresolved_objection', lambda p, c: p['record']['claims'][0]['objections'].append(
        dict(id='counter', state='OPEN', reason='A contradictory log remains unexplained.', source_ids=['log'])), 'MATERIAL_OBJECTION_OPEN')
    add('ambiguous_identity', lambda p, c: p['record']['claims'][0].update(identity='AMBIGUOUS'), 'IDENTITY_AMBIGUOUS')
    add('missing_counterreview', lambda p, c: p['reviews'].pop(3), 'ROLE_REVIEW_MISSING')
    add('shared_control', lambda p, c: c['principals'][3].update(controller=c['principals'][5]['controller']), 'DECLARED_REVIEW_CONTROL_CONFLICT')
    add('unknown_control', lambda p, c: c['principals'][6].update(controller=None), 'REVIEW_CONTROL_UNKNOWN')
    add('party_reviews_self', lambda p, c: c['party_ids'].append('audit_reviewer'), 'DECLARED_REVIEW_CONTROL_CONFLICT')
    add('source_after_cutoff', lambda p, c: c.update(source_cutoff='2020-01-02'), 'SOURCE_OUTSIDE_CUTOFF')
    add('uncertain_source_date', lambda p, c: p['record']['sources'][0].update(
        available=dict(earliest='2020-01-01', latest='2020-01-31')), 'SOURCE_OUTSIDE_CUTOFF')
    add('hindsight_called_prospective', lambda p, c: p['record'].update(mode='PROSPECTIVE'), 'REJECTED')
    add('stale_claim', lambda p, c: p['record']['claims'][0].update(version=2), 'REJECTED', refresh=False)
    add('draft_changed_after_review', lambda p, c: p['record']['draft'].update(text='Amended wording.'), 'REJECTED', refresh=False)
    add('audience_changed_after_review', lambda p, c: p['record']['draft'].update(audience='Another recipient.'), 'REJECTED', refresh=False)
    add('invented_authority', lambda p, c: p.update(execution_enabled=True), 'REJECTED')
    add('seek_more_evidence', lambda p, c: p['record'].update(disposition='SEEK_EVIDENCE'), 'MORE_EVIDENCE_REQUESTED')
    add('closure_with_challenge', lambda p, c: p['record']['draft'].update(kind='INTERNAL_REVIEW'), 'REJECTED', resolved=True)

    def echoes(p, c):
        s = p['record']['sources'][0]
        p['record']['sources'].extend([dict(deepcopy(s), id='echo-1'), dict(deepcopy(s), id='echo-2')])
    add('three_records_one_origin', echoes, 'SUPPLIED_REVIEW_CONSISTENT')
    def false_origins(p, c):
        echoes(p, c)
        p['record']['sources'][1]['origin_group'] = 'claimed-independent'
    add('identical_bytes_claimed_independent', false_origins, 'SAME_ARTIFACT_MULTIPLE_ORIGINS')
    # Deliberate limitation control: populated fields do not establish meaning.
    add('irrelevant_nonblank_reason', lambda p, c: p['record']['analysis'].update(
        counterargument='The moon is made of cheese.'), 'SUPPLIED_REVIEW_CONSISTENT')
    return result


def integration_report():
    rows = []
    for name, (packet, context, expected) in controls().items():
        try:
            report = inspect_review(packet, context)
            observed = expected if expected in report['blockers'] else report['status']
        except ReviewError:
            observed = 'REJECTED'
        rows.append(dict(control=name, expected=expected, observed=observed, matched=observed == expected))
    return dict(schema='cortac.vanguard.controls.v1', controls=len(rows), results=rows,
                all_fixed_structural_outcomes=all(row['matched'] for row in rows),
                authority='NONE', execution_enabled=False, controller_closure='SUPPLIED_UNVERIFIED',
                semantic_assessment='NOT_PERFORMED', synthetic_inputs=True, real_model_calls=0,
                real_external_principals=0, empirical_success_established=False)
