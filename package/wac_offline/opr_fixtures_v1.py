"""Fixed structural controls, not semantic OPR acceptance or an agent experiment."""
from copy import deepcopy
from hashlib import sha256

from .opr_records_v1 import inspect_record, RecordError, VERSION, CONTEXT_VERSION


def fixture():
    evidence = [dict(id=name, digest=sha256(('synthetic:' + name).encode()).hexdigest(), kind=kind)
                for name, kind in [('observation', 'OBSERVATION'), ('contrary', 'CONTRARY'), ('control', 'CONTROL')]]
    context = dict(schema=CONTEXT_VERSION, policy_digest='a' * 64, epoch=2, now=12,
        version=3, target='target', burden_group='same-supplied-access-burden',
        operations=['contact'], duration_limit=20, load_limit=40, serious_duration=15,
        serious_load=30, history=[dict(id='earlier', case_label='old-emergency-label',
            start=0, end=10, burden_units=1, operations=['contact'])], evidence=evidence,
        protected_limits=['appeal-preserved'],
        principals=[dict(id=p, controller='supplied-controller-' + p)
                    for p in ['target', 'complainant', 'decision-maker', 'reviewer', 'verifier', 'issuer']],
        parties=['target', 'complainant', 'decision-maker'], grants=[])
    for name, purpose in [('restriction', 'RESTRICTION'), ('review', 'REVIEW'), ('notice', 'NOTICE_DELAY')]:
        context['grants'].append(dict(id=name, purpose=purpose, policy_digest='a' * 64,
            epoch=2, version=3, target='target', operations=['contact'], start=10,
            end=30, issuer='issuer', state='CURRENT'))
    record = dict(schema=VERSION, case_id='synthetic-case', case_label='protective-new-label',
        policy_digest='a' * 64, epoch=2, version=3, target='target',
        burden_group=context['burden_group'], operations=['contact'],
        interval=dict(id='current', case_label='protective-new-label', start=10, end=20,
            burden_units=1, operations=['contact']), cumulative=dict(duration=20, load=20),
        justification=dict(conduct='Supplied repeated contact allegation, not a validated fact.',
            rule='Supplied contact boundary rule.', risk='Supplied risk assertion.',
            urgency='Supplied timing explanation.', alternatives='Narrow contact-only option recorded.',
            burdens='Target and outsider burdens recorded, not evaluated.',
            epistemic='Evidence assessment supplied, not verified.', normative='Normative reasons supplied.',
            dissent='Material objection supplied.', consequence='TEMPORARY', standard='CLEAR_AND_CONVINCING'),
        evidence_refs=[dict(id=e['id'], digest=e['digest']) for e in evidence],
        contrary=[dict(evidence_id='contrary', disposition='ADDRESSED',
            reason='Declared response to contrary material; adequacy remains unchecked.')],
        limits=[dict(id='appeal-preserved', status='SATISFIED',
            reason='Supplied assessment only.', evidence_ids=['observation'])],
        independence=dict(reviewer='reviewer', verifier='verifier', evidence_ids=['control'],
            conflict_route='Supplied independent conflict challenge route.', reassess_at=18),
        notice=dict(status='DELIVERED', summary='Synthetic notice text.',
            authority_ref='NOT_APPLICABLE', deadline=11, reason='Reported delivery only.'),
        review=dict(route='Supplied independent appeal route.', substitute='Supplied alternate route.',
            deadline=18, authority_ref='review', reserved_units=2), authority_ref='restriction',
        continuity='Supplied service continuity plan.', stopping_conditions='Stop by exclusive expiry.',
        complaints=[dict(id='complaint-1', version=1, status='OPEN')],
        correction=dict(decision='No remedy requested.', attempted_effect='None.', observed_effect='None.',
            audit='Not performed.', status='NOT_REQUESTED'))
    return record, context


# Expectations fixed from the structural contract, not generated from outputs.
EXPECTED = {
    'complete_supplied_record': 'STRUCTURALLY_COMPLETE',
    'expired_restriction': 'STRUCTURALLY_INCOMPLETE',
    'stale_epoch': 'REJECTED',
    'label_reset': 'REJECTED',
    'parallel_burden_cap': 'STRUCTURALLY_INCOMPLETE',
    'unknown_independence': 'STRUCTURALLY_INCOMPLETE',
    'common_controller': 'REJECTED',
    'missing_review_route': 'REJECTED',
    'missing_authority': 'REJECTED',
    'empty_review_reserve': 'STRUCTURALLY_INCOMPLETE',
    'notice_unbounded': 'STRUCTURALLY_INCOMPLETE',
    'protected_unknown': 'STRUCTURALLY_INCOMPLETE',
    'protected_failure': 'STRUCTURALLY_INCOMPLETE',
    'contrary_omitted': 'REJECTED',
    'contrary_unresolved': 'STRUCTURALLY_INCOMPLETE',
    'revoked_authority': 'STRUCTURALLY_INCOMPLETE',
    'ideology_capability': 'REJECTED',
    'semantic_promotion': 'REJECTED',
}


def control(name):
    record, context = fixture()
    if name == 'expired_restriction': context['now'] = 20
    elif name == 'stale_epoch': record['epoch'] = 1
    elif name == 'label_reset':
        record['case_label'] = record['interval']['case_label'] = 'another-emergency'
        record['cumulative'] = dict(duration=10, load=10)
    elif name == 'parallel_burden_cap':
        context['history'][0]['start'] = 10
        context['history'][0]['end'] = 20
        context['history'][0]['burden_units'] = 4
        record['cumulative'] = dict(duration=10, load=50)
    elif name == 'unknown_independence': context['principals'][3]['controller'] = None
    elif name == 'common_controller': context['principals'][3]['controller'] = context['principals'][0]['controller']
    elif name == 'missing_review_route': record['review']['route'] = ''
    elif name == 'missing_authority': record['authority_ref'] = 'absent'
    elif name == 'empty_review_reserve': record['review']['reserved_units'] = 0
    elif name == 'notice_unbounded':
        record['notice'].update(status='DELAYED', authority_ref='notice', deadline=99)
    elif name == 'protected_unknown': record['limits'][0]['status'] = 'UNRESOLVED'
    elif name == 'protected_failure': record['limits'][0]['status'] = 'FAILED'
    elif name == 'contrary_omitted': record['contrary'] = []
    elif name == 'contrary_unresolved': record['contrary'][0]['disposition'] = 'UNRESOLVED'
    elif name == 'revoked_authority': context['grants'][0]['state'] = 'REVOKED'
    elif name == 'ideology_capability': record['classifier_authorization'] = 'intolerant'
    elif name == 'semantic_promotion': record['operational_conformance'] = 'ESTABLISHED'
    elif name != 'complete_supplied_record': raise ValueError(name)
    return record, context


def integration_report():
    rows = []
    for name, expected in EXPECTED.items():
        record, context = control(name)
        try:
            report = inspect_record(record, context)
            status = report['status']
        except RecordError as exc:
            status = 'REJECTED'
            report = dict(error=str(exc), authority='NONE', execution_enabled=False)
        if status != expected:
            raise AssertionError(name + ': expected ' + expected + ', observed ' + status)
        rows.append(dict(control=name, expected=expected, observed=status, report=report))
    return dict(schema='cortac.opr.controls.v1', controls=len(rows), rows=deepcopy(rows),
        all_fixed_structural_outcomes=True, authority='NONE', execution_enabled=False,
        controller_closure='SUPPLIED_UNVERIFIED', real_model_calls=0, real_external_principals=0,
        semantic_assessment='NOT_PERFORMED', opr_acceptance_established=False,
        scope='SYNTHETIC_OFFLINE_STRUCTURAL_CONTROLS_ONLY')
