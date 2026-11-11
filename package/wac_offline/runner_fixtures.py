"""Exposed synthetic inputs and scripted integration; no model or real principals."""
from copy import deepcopy
import time

from .runner import ScratchGateway, RunnerError, SCOPE, digest, evidence_record


SCENARIOS = ('repair', 'budget', 'audit_budget', 'conflicted_review',
             'missing_repair_mandate', 'two_complaints', 'revoked_repair_mandate',
             'conflicted_repair_authorizer')


def fixture(arm='minimal', budget=24, scenario='repair'):
    if arm not in ('minimal', 'full'):
        raise ValueError('unknown arm')
    if scenario not in SCENARIOS:
        raise ValueError('unknown scenario')
    roles = {'proposer': ['proposer'], 'assessor': ['assessor'],
             'authorizer': ['authorizer'], 'repair_authorizer': ['authorizer'],
             'executor': ['executor'], 'auditor': ['auditor'], 'repair_auditor': ['auditor'],
             'reviewer': ['reviewer'], 'outsider': ['affected_party']}
    approvals = ['approval' + str(i) for i in range(4 if arm == 'full' else 1)]
    roles.update({actor: ['approver'] for actor in approvals})
    principals = [dict(id=actor, controller='synthetic-controller-' + actor, roles=actor_roles)
                  for actor, actor_roles in roles.items()]
    if scenario == 'conflicted_review':
        next(p for p in principals if p['id'] == 'reviewer')['controller'] = 'synthetic-controller-authorizer'
    if scenario == 'conflicted_repair_authorizer':
        next(p for p in principals if p['id'] == 'repair_authorizer')['controller'] = 'synthetic-controller-executor'
    policy = dict(schema='cortac.scratch.policy.v1', case_id='synthetic-contested-document', epoch=1,
                  principals=principals, protected_limits=[dict(id='independent-review', commitment='Preserve independent review')],
                  approval_ids=approvals, approval_threshold=3 if arm == 'full' else 1,
                  excluded_ids=['outsider'], operation_budget=14 if scenario == 'budget' else (15 if scenario == 'audit_budget' else budget))
    evidence = [evidence_record('source-v1', 'synthetic-owner-ledger-v1', '10'),
                evidence_record('source-v2', 'synthetic-owner-ledger-correction', '12')]
    def proposal(revision, source):
        decision = dict(schema='cortac.decision.record.v1',
            affected_parties=[dict(id='outsider', interests='Correct fixture document', benefits='Correction',
                                  burdens='Bounded review delay', representation='Open outsider complaint route')],
            alternatives=[dict(option='Leave existing value', less_harmful_analysis='Avoid mutation; preserves possible error',
                               rejection_or_selection_reason='Use supplied ledger revision', evidence_refs=[source])],
            protected_limit_assessments=[dict(limit_id='independent-review', status='PASS',
                                             reasons='Separate declared review remains available', evidence_refs=[source])],
            burden_justification='Finite scratch-only review; no real effects claimed',
            dissent=['Outsider disputes old ledger'] if revision else [],
            dissent_status='RECORDED' if revision else 'NONE_REPORTED',
            predictions=['Scratch document equals selected supplied evidence'],
            review_triggers=[dict(condition='A newer supplied correction arrives', review_authority='reviewer')],
            remedy_plan=dict(authority='Pinned synthetic repair mandate', resources='Same total operation cap',
                             steps='Review challenge, authorize exact correction, re-audit', evidence_refs=[source]),
            evidence_refs=[source])
        item = next(e for e in evidence if e['id'] == source)
        return dict(schema='cortac.scratch.proposal.v1', case_id=policy['case_id'], policy_digest=digest('Policy', policy),
                    epoch=1, expected_revision=revision, operation='REPAIR' if revision else 'COMMIT',
                    target='scratch_document', value=item['content'], proposer='proposer',
                    evidence=[dict(id=source, digest=digest('Evidence', item))], decision_source=source,
                    decision_record=decision)
    initial = proposal(0, 'source-v1'); repair = proposal(1, 'source-v2')
    def grant(identifier, proposal, actor):
        return dict(schema='cortac.scratch.mandate.v1', id=identifier, case_id=policy['case_id'],
                    policy_digest=digest('Policy', policy), proposal_digest=digest('Proposal', proposal),
                    authorizer=actor, expires_tick=100, max_uses=1, scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
    mandates = [grant('initial', initial, 'authorizer')]
    if scenario != 'missing_repair_mandate':
        mandates.append(grant('repair', repair, 'repair_authorizer'))
    return dict(policy=policy, evidence=evidence, mandates=mandates, initial=initial, repair=repair)


def checks(gateway, p, policy, repair=False):
    receipts = [gateway.issue(p, 'ASSESSMENT', 'assessor')]
    receipts.extend(gateway.issue(p, 'APPROVAL', actor) for actor in policy['approval_ids'][:policy['approval_threshold']])
    receipts.append(gateway.issue(p, 'AUTHORIZATION', 'repair_authorizer' if repair else 'authorizer'))
    return receipts


def episode(arm, scenario='repair'):
    data = fixture(arm, scenario=scenario)
    cpu = time.process_time(); wall = time.perf_counter()
    status = 'REPAIRED'; error = None
    with ScratchGateway(data['policy'], data['evidence'], data['mandates']) as gateway:
        try:
            initial = gateway.commit(data['initial'], checks(gateway, data['initial'], data['policy']), 'initial', 'executor')
            gateway.audit(initial, 'auditor')
            gateway.challenge('outsider-correction', 'outsider', initial, ['source-v2'],
                              'The newer supplied ledger corrects the old value.')
            review = gateway.review('outsider-correction', data['repair'], 'reviewer')
            receipts = checks(gateway, data['repair'], data['policy'], repair=True) + [review]
            if scenario == 'two_complaints':
                gateway.challenge('second-correction', 'outsider', initial, ['source-v2'],
                                  'A separately recorded complaint remains open.')
            if scenario == 'revoked_repair_mandate':
                gateway.revoke('repair', 'repair_authorizer', 'Withdraw the synthetic repair grant before commit.')
            effect = gateway.commit(data['repair'], receipts, 'repair', 'executor')
            gateway.audit(effect, 'repair_auditor')
        except RunnerError as exc:
            status = 'BLOCKED'; error = str(exc)
        state = gateway.snapshot()
        # Outcomes come from persisted state, not actor success assertions.
        repaired = state['value'] == '12' and state['revision'] == 2
        audited = repaired and state['pending_audit'] is None
        unresolved = sum(c['resolution'] is None for c in state['challenges'].values())
        report = dict(arm=arm, scenario=scenario, status=status, blocker=error,
                      outcome=dict(initial_effect_observed=bool(state['effects']), correction_effect_observed=repaired,
                                   audited_correction=audited, unresolved_challenges=unresolved,
                                   final_revision=state['revision'], final_value=state['value'],
                                   mutation_count=len(state['effects']), pending_audit=state['pending_audit'],
                                   unmetered_budget_refusals=int(error == 'operation budget exhausted'),
                                   metered_rejected_operations=sum(e['result'] == 'REJECTED' for e in state['journal'])),
                      costs=dict(operation_cap=data['policy']['operation_budget'], operations_used=state['tick'],
                                 declared_principals=len(data['policy']['principals']),
                                 participating_principals=len(state['participants']), model_calls=0, model_tokens=0,
                                 paid_provider_cost_usd=0, cpu_seconds=time.process_time()-cpu,
                                 wall_seconds=time.perf_counter()-wall),
                      trace=state, inputs=deepcopy(data),
                      authority='NONE', external_execution_enabled=False, scratch_effects_enabled=True,
                      controller_closure='SUPPLIED_UNVERIFIED', provenance='SYNTHETIC_FIXTURE')
    return report


def integration_report():
    rows = [episode(arm, scenario) for scenario in SCENARIOS
            for arm in ('minimal', 'full')]
    return dict(schema='cortac.scratch.integration.v1', scope=SCOPE, scenarios=len(SCENARIOS), episodes=len(rows),
                real_model_calls=0, real_external_principals=0, scored_study=False,
                external_execution_enabled=False, actual_disposable_database_effects=True,
                rows=rows)
