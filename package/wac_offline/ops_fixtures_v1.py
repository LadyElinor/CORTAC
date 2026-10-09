"""Fabricated OPS1 trace controls. These are not observations or adjudications."""
from copy import deepcopy
from .ops_trace_v1 import (CONTEXT_VERSION, VERSION, DIMENSIONS, STAGES, TraceError,
                           digest, inspect_trace)


def fixture():
    """Return fresh fabricated trace/context dictionaries."""
    evidence = []
    for identity, kind in [('original', 'ORIGINAL'), ('check', 'PROVENANCE_CHECK'),
                           ('counter', 'COUNTER'), ('reason', 'REASON'),
                           ('dependency', 'DEPENDENCY'), ('funding', 'FUNDING'),
                           ('account', 'ACCOUNT')]:
        evidence.append(dict(id=identity, version=1, digest=digest(identity), kind=kind, observed_at=1))
    for i, stage in enumerate(STAGES):
        evidence.append(dict(id=stage.lower(), version=1, digest=digest(stage), kind=stage, observed_at=11+i))
    next(e for e in evidence if e['id'] == 'account')['observed_at'] = 14
    binding = dict(case_id='fabricated-case', policy_digest='a' * 64, version=2, predecessor_digest='b' * 64)
    context = dict(schema=CONTEXT_VERSION, expected=binding, now=20, evidence=evidence,
        claims=[dict(id='claim', version=1, original_ids=['original'])],
        objections=[dict(id='objection', version=1, claim_id='claim', claim_version=1, evidence_ids=['counter'],
                         materiality='MATERIAL', reopened_at=4)],
        dependencies=[dict(subject=who, dimension=dimension, version=1, evidence_ids=['dependency'],
                           changed_at=1, status='CURRENT_REPORTED')
                      for who in ('reviewer', 'verifier') for dimension in sorted(DIMENSIONS)],
        injuries=[dict(id='injury', version=1)], remedy_version=1, parties=['party'],
        principals=[dict(id=who, controller='controller-' + who)
                    for who in ('party', 'reviewer', 'verifier', 'owner')])
    linked = [dict(id=e['id'], version=e['version'], digest=e['digest']) for e in evidence
              if e['id'] in ('original', 'check', 'counter', 'reason')]
    events = [dict(id='event-' + str(i), stage=stage, previous_id='NONE' if i == 0 else 'event-' + str(i-1),
                   at=11+i, actor='verifier' if stage == 'AUDITED' else 'owner', evidence_ids=[stage.lower()])
              for i, stage in enumerate(STAGES)]
    trace = dict(schema=VERSION, binding=deepcopy(binding), context_digest=digest(context),
        findings=[dict(id='claim', claim_version=1, evidence_refs=linked,
            provenance=[dict(original_id='original', original_version=1, original_digest=digest('original'), check_id='check', checker='verifier', checked_at=3,
                             method='Fabricated provenance inspection narrative')],
            resolutions=[dict(id='objection', version=1, state='RESOLUTION_REPORTED', resolved_at=8,
                              evidence_ids=['counter', 'reason'], reason='Fabricated disposition')],
            decided_at=10, hearing=dict(status='NOT_WARRANTED', evidence_ids=['reason'],
                                       reason='Fabricated hearing assessment'), reason='Fabricated finding')],
        independence=dict(reviewer='reviewer', verifier='verifier', checked_at=2, reassess_at=40,
            dependencies=[{key: dep[key] for key in ('subject', 'dimension', 'version', 'evidence_ids')}
                          for dep in context['dependencies']], evidence_ids=['dependency'],
            challenge_route='Fabricated existing conflict route'),
        remedy=dict(id='remedy', version=1, findings_digest='0' * 64, owner='owner', deadline=30, funding_ids=['funding'],
            evidence_requirements=list(STAGES), events=events,
            residuals=[dict(id='injury', version=1, state='REPAIRED_REPORTED', observation_ids=['observed'],
                            audit_ids=['audited'], reason='Fabricated residual repair claim')],
            affected_account=dict(status='SUPPLIED', evidence_ids=['account'], reason='Fabricated account'),
            escalation=dict(owner='reviewer', due_at=35, route='Fabricated existing escalation route')))
    trace['remedy']['findings_digest'] = digest(trace['findings'])
    return trace, context


def controls():
    """Fixed, exposed negative controls. No adaptive search or semantic oracle."""
    cases = {}

    def add(name, mutate, expected):
        t, c = fixture()
        mutate(t, c)
        t['remedy']['findings_digest'] = digest(t['findings'])
        t['context_digest'] = digest(c)
        cases[name] = (t, c, expected)

    add('consistent_fabrication', lambda t, c: None, 'SUPPLIED_TRACE_CONSISTENT')
    add('unresolved_material_objection', lambda t, c: t['findings'][0]['resolutions'][0].update(state='UNRESOLVED'), 'MATERIAL_OBJECTION_UNRESOLVED')
    add('reopened_objection', lambda t, c: c['objections'][0].update(reopened_at=9), 'OBJECTION_REOPENED')
    add('missing_counterevidence', lambda t, c: t['findings'][0]['evidence_refs'].pop(2), 'REJECTED')
    add('deleted_objection_only', lambda t, c: c['objections'].clear(), 'REJECTED')
    add('stale_claim_version', lambda t, c: c['claims'][0].update(version=2), 'REJECTED')
    add('stale_objection_version', lambda t, c: c['objections'][0].update(version=2), 'REJECTED')
    add('missing_original_check', lambda t, c: t['findings'][0]['provenance'].clear(), 'REJECTED')
    add('provenance_after_finding', lambda t, c: t['findings'][0]['provenance'][0].update(checked_at=11), 'REJECTED')
    add('hearing_pending', lambda t, c: t['findings'][0]['hearing'].update(status='PENDING'), 'HEARING_PENDING')
    add('expired_independence', lambda t, c: t['independence'].update(reassess_at=20), 'INDEPENDENCE_REASSESSMENT_DUE')
    add('changed_dependency', lambda t, c: c['dependencies'][0].update(changed_at=3), 'DEPENDENCY_CHANGED_AFTER_ASSESSMENT')
    add('unknown_dependency', lambda t, c: c['dependencies'][0].update(status='UNKNOWN'), 'DEPENDENCY_NOT_CURRENT')
    add('stale_dependency_version', lambda t, c: c['dependencies'][0].update(version=2), 'REJECTED')
    add('unknown_controller', lambda t, c: c['principals'][1].update(controller=None), 'INDEPENDENCE_UNKNOWN')
    add('verifier_party_control', lambda t, c: c['principals'][2].update(controller='controller-party'), 'DECLARED_CONTROL_CONFLICT')
    add('same_reviewer_verifier', lambda t, c: t['independence'].update(verifier='reviewer'), 'REJECTED')
    add('missing_observation_phase', lambda t, c: t['remedy']['events'].pop(3), 'REJECTED')
    add('observation_wrong_evidence', lambda t, c: t['remedy']['events'][3].update(evidence_ids=['attempted']), 'REJECTED')
    add('audit_by_remedy_owner', lambda t, c: t['remedy']['events'][4].update(actor='owner'), 'REJECTED')
    add('broken_event_chain', lambda t, c: t['remedy']['events'][2].update(previous_id='event-0'), 'REJECTED')
    add('residual_referral', lambda t, c: t['remedy']['residuals'][0].update(state='REFERRED'), 'RESIDUAL_INJURY_NOT_REPAIRED')
    add('residual_repair_without_audit', lambda t, c: t['remedy']['residuals'][0].update(audit_ids=[]), 'REJECTED')
    add('new_residual_version', lambda t, c: c['injuries'][0].update(version=2), 'REJECTED')
    add('stale_remedy_version', lambda t, c: c.update(remedy_version=2), 'REJECTED')
    add('unsupported_effect_flag', lambda t, c: t.update(execution_enabled=True), 'REJECTED')
    add('caller_head_mismatch', lambda t, c: c['expected'].update(predecessor_digest='c' * 64), 'REJECTED')
    add('caller_policy_mismatch', lambda t, c: c['expected'].update(policy_digest='c' * 64), 'REJECTED')
    add('irrelevant_nonblank_reason', lambda t, c: t['findings'][0].update(reason='The moon is made of cheese.'), 'SUPPLIED_TRACE_CONSISTENT')
    return cases


def integration_report():
    results = []
    for name, (trace, context, expected) in controls().items():
        try:
            report = inspect_trace(trace, context)
            observed = report['status'] if expected.startswith('SUPPLIED_') else expected if expected in report['blockers'] else report['status']
        except TraceError:
            observed = 'REJECTED'
        results.append(dict(control=name, expected=expected, observed=observed, matched=expected == observed))
    return dict(schema='cortac.ops.controls.v1', controls=len(results),
        all_fixed_structural_outcomes=all(r['matched'] for r in results), results=results,
        authority='NONE', execution_enabled=False, real_model_calls=0, real_external_principals=0,
        semantic_assessment='NOT_PERFORMED', operational_conformance='NOT_ESTABLISHED',
        empirical_success_established=False, synthetic_inputs=True)
