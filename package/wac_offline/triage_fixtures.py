"""Exposed, deterministic triage regression episodes; no model or real people.

Expected final states below are fixed independently of the execution path. Every
row, including blocked/incomplete work, is retained. Supplied controller finding
outcomes are fixtures, not semantic inference, source authentication, or truth.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from .runner import RunnerError, SCOPE, digest, evidence_record
from .runner_fixtures import fixture as legacy_fixture, checks
from .triage import TriageGateway, make_grant


EXPECTED = {
    'multi_complaint': dict(revision=2, holds=[], pending_audit=None, status='REPAIRED'),
    'unknown_unresolved': dict(revision=1, holds=['c1', 'c2'], pending_audit=None, status='BLOCKED'),
    'unknown_declared': dict(revision=2, holds=[], pending_audit=None, status='REPAIRED'),
    'omitted_hold': dict(revision=1, holds=['c1', 'c2'], pending_audit=None, status='BLOCKED'),
    'ordinary_exhausted_audit': dict(revision=1, holds=[], pending_audit=None, status='INITIAL_AUDITED'),
    'repair_exhausted': dict(revision=1, holds=['c1', 'c2'], pending_audit=None, status='INCOMPLETE'),
    'review_exhausted': dict(revision=1, holds=['c1', 'c2'], pending_audit=None, status='INCOMPLETE'),
    'audit_exhausted': dict(revision=2, holds=['c1', 'c2'], pending_audit='effect-2', status='INCOMPLETE'),
    'later_complaint': dict(revision=2, holds=['late'], pending_audit=None, status='SURVIVING_HOLD'),
    'appeal_before_audit': dict(revision=2, holds=['c1'], pending_audit=None, status='SURVIVING_HOLD'),
    'duplicate_isolation': dict(revision=2, holds=[], pending_audit=None, status='REPAIRED'),
    'duplicate_before_admission': dict(revision=2, holds=[], pending_audit=None, status='REPAIRED'),
    'revoked_review': dict(revision=1, holds=['c1', 'c2'], pending_audit=None, status='BLOCKED'),
    'grant_replay': dict(revision=2, holds=[], pending_audit=None, status='REPAIRED'),
    'concurrent_commit': dict(revision=2, holds=[], pending_audit=None, status='REPAIRED'),
}


def fixture(scenario='multi_complaint'):
    """Return a fully constructor-pinned, inspectable episode inventory."""
    if scenario not in EXPECTED:
        raise ValueError('unknown triage scenario')
    data = legacy_fixture(budget=200)
    data['policy']['principals'].extend([
        dict(id='factfinder', controller='synthetic-factfinder', roles=['assessor']),
        dict(id='support_authorizer', controller='synthetic-support-authorizer', roles=['authorizer']),
    ])
    data['evidence'].extend([
        evidence_record('source-overlap', 'second-supplied-correction', '12'),
        evidence_record('source-appeal', 'supplied-appeal-correction', '12'),
        evidence_record('control-source', 'synthetic-controller-declaration', 'synthetic-unknown-claimant'),
    ])
    refs = [dict(id=e['id'], digest=digest('Evidence', e)) for e in sorted(data['evidence'], key=lambda e: e['id'])
            if e['id'] in ('source-v2', 'source-overlap', 'source-appeal')]
    data['repair']['evidence'] = refs
    data['repair']['decision_record']['evidence_refs'] = [r['id'] for r in refs]
    for p in (data['initial'], data['repair']):
        p['policy_digest'] = digest('Policy', data['policy'])
    for mandate in data['mandates']:
        mandate['policy_digest'] = digest('Policy', data['policy'])
        mandate['proposal_digest'] = digest('Proposal', data[mandate['id']])
    ids = ['c1', 'c2'] + (['duplicate'] if scenario in ('duplicate_isolation', 'duplicate_before_admission') else [])
    slots = []
    for identifier in ids + ['late']:
        duplicate = identifier == 'duplicate'
        slots.append(dict(id=identifier,
            claimant='unknown-outsider' if identifier == 'c2' and scenario.startswith('unknown_') else 'outsider',
            work_item_id='repair' if identifier == 'late' else 'initial',
            evidence_ids=['source-overlap'] if identifier == 'c2' else ['source-v2'],
            reason='Separate supplied concern: ' + identifier,
            duplicate_of='c1' if duplicate else None,
            appeals=[dict(evidence_ids=['source-appeal'], reason='Retained appeal: ' + identifier)],
            factfinding_budget=0 if duplicate else 2,
            review_budget=0 if duplicate or scenario == 'review_exhausted' else 3))
    config = dict(schema='cortac.scratch.triage.config.v1',
        evidence_digest=digest('TriageEvidence', sorted(data['evidence'], key=lambda e: e['id'])),
        ordinary_budget=4 if scenario in ('ordinary_exhausted_audit', 'duplicate_before_admission') else 24,
        repair_budget=0 if scenario == 'repair_exhausted' else 12,
        complaints=slots,
        work_items=[dict(id=name, proposal_digest=digest('Proposal', data[name]),
            expected_revision=0 if name == 'initial' else 1,
            operation='COMMIT' if name == 'initial' else 'REPAIR',
            mandate_id=name, executor='executor', complaint_ids=[] if name == 'initial' else ids,
            audit_budget=0 if name == 'repair' and scenario == 'audit_exhausted' else 3)
            for name in ('initial', 'repair')])
    grants = []
    def grant(identifier, action, actor, *, versions=None, item=None, revision=1, finding=None):
        grants.append(make_grant(identifier, action, actor, 'support_authorizer',
            data['policy'], config, complaint_versions=versions, work_item_id=item,
            expected_revision=revision, finding=finding))
    versions = {i: 0 for i in ids}
    grant('initial-audit', 'AUDIT', 'auditor', item='initial')
    grant('review-all', 'REVIEW', 'reviewer', versions=versions, item='repair')
    grant('repair-audit', 'AUDIT', 'repair_auditor', versions=versions, item='repair', revision=2)
    if scenario.startswith('unknown_'):
        declared = scenario == 'unknown_declared'
        grant('find-c2', 'FACT_FINDING', 'factfinder', versions={'c2': 0}, finding=dict(
            status='DECLARED_CONTROLLER' if declared else 'UNRESOLVED',
            controller='synthetic-unknown-claimant' if declared else None,
            evidence_ids=['control-source'] if declared else []))
    data.update(triage_config=config, grants=grants, scenario=scenario)
    return data


def _lodge(gateway, data, effect, identifier):
    slot = next(s for s in data['triage_config']['complaints'] if s['id'] == identifier)
    return gateway.lodge(identifier, slot['claimant'], effect, slot['evidence_ids'],
                         slot['reason'], duplicate_of=slot['duplicate_of'])


def episode(scenario='multi_complaint'):
    data = fixture(scenario)
    errors = []; observations = {}
    with TriageGateway(data['policy'], data['evidence'], data['mandates'],
                       triage_config=data['triage_config'], grants=data['grants']) as gateway:
        def expect_rejected(fn):
            try:
                fn()
            except RunnerError as exc:
                errors.append(str(exc))
            else:
                raise AssertionError('predetermined rejection unexpectedly accepted')
        try:
            initial = gateway.commit(data['initial'], checks(gateway, data['initial'], data['policy']),
                                     'initial', 'executor', 'initial')
            if scenario == 'ordinary_exhausted_audit':
                expect_rejected(lambda: gateway.issue(data['initial'], 'ASSESSMENT', 'assessor'))
                gateway.audit(initial, 'auditor', 'initial-audit')
            else:
                gateway.audit(initial, 'auditor', 'initial-audit')
                ids = data['triage_config']['work_items'][1]['complaint_ids']
                if scenario == 'duplicate_before_admission':
                    _lodge(gateway, data, initial, 'c1')
                    _lodge(gateway, data, initial, 'duplicate')
                    for _ in range(3):
                        expect_rejected(lambda: _lodge(gateway, data, initial, 'duplicate'))
                    before = gateway.snapshot()['budgets']['review:c2']['used']
                    _lodge(gateway, data, initial, 'c2')
                    budgets = gateway.snapshot()['budgets']
                    observations['other_complaint_admitted_after_duplicate_flood'] = True
                    observations['unrelated_review_pool_unchanged'] = budgets['review:c2']['used'] == before
                    observations['duplicate_appeal_intake_retained'] = budgets['intake:duplicate']['used'] == 1
                    if not all(observations.values()):
                        raise AssertionError('duplicate traffic harmed isolated admission/appeal reserves')
                else:
                    for identifier in ids:
                        _lodge(gateway, data, initial, identifier)
                if scenario.startswith('unknown_'):
                    gateway.factfind('c2', 'factfinder', 'find-c2')
                if scenario == 'duplicate_isolation':
                    before = gateway.snapshot()['budgets']['review:c2']['used']
                    expect_rejected(lambda: gateway.review(['c2', 'duplicate'], data['repair'], 'reviewer', 'ungranted'))
                    after = gateway.snapshot()['budgets']['review:c2']['used']
                    observations['unrelated_review_pool_unchanged'] = before == after
                    if before != after:
                        raise AssertionError('duplicate traffic spent unrelated protected reserve')
                selected = ['c1'] if scenario == 'omitted_hold' else ids
                review = gateway.review(selected, data['repair'], 'reviewer', 'review-all')
                receipts = checks(gateway, data['repair'], data['policy'], repair=True) + [review]
                if scenario == 'revoked_review':
                    gateway.revoke_grant('review-all', 'support_authorizer', 'Withdraw exact review authority.')
                def commit():
                    try:
                        return gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
                    except RunnerError as exc:
                        return str(exc)
                if scenario == 'concurrent_commit':
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        results = list(pool.map(lambda _: commit(), range(2)))
                    effects = [r for r in results if type(r) is dict]
                    rejected = [r for r in results if type(r) is str]
                    observations['concurrent_effects'] = len(effects)
                    observations['concurrent_rejections'] = len(rejected)
                    if len(effects) != 1 or len(rejected) != 1:
                        raise AssertionError('concurrent commits did not serialize to one effect')
                    effect = effects[0]; errors.extend(rejected)
                else:
                    effect = gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
                if scenario == 'later_complaint':
                    _lodge(gateway, data, effect, 'late')
                if scenario == 'appeal_before_audit':
                    gateway.appeal('c1', 'outsider', ['source-appeal'], 'Retained appeal: c1')
                gateway.audit(effect, 'repair_auditor', 'repair-audit')
                if scenario == 'grant_replay':
                    expect_rejected(lambda: gateway.audit(effect, 'repair_auditor', 'repair-audit'))
        except RunnerError as exc:
            errors.append(str(exc))
        state = gateway.snapshot()
        holds = sorted(i for i, c in state['complaints'].items() if c['hold'])
        if state['revision'] == 2 and state['pending_audit'] is None:
            status = 'SURVIVING_HOLD' if holds else 'REPAIRED'
        elif state['revision'] == 1 and not holds and state['pending_audit'] is None:
            status = 'INITIAL_AUDITED'
        else:
            status = 'INCOMPLETE' if state['incomplete'] else 'BLOCKED'
        observed = dict(revision=state['revision'], holds=holds,
                        pending_audit=state['pending_audit'], status=status)
        expected = EXPECTED[scenario]
        if observed != expected:
            raise AssertionError('triage scenario ' + scenario + ': expected ' + repr(expected) + ', observed ' + repr(observed))
        return dict(scenario=scenario, expected=deepcopy(expected), observed=observed,
                    expected_outcome_matched=observed == expected, errors=errors,
                    observations=observations, trace=state, inputs=data,
                    authority='NONE', controller_closure='SUPPLIED_UNVERIFIED',
                    external_execution_enabled=False, scratch_effects_enabled=True,
                    model_calls=0, provenance='SYNTHETIC_FIXTURE')


def integration_report():
    rows = [episode(scenario) for scenario in EXPECTED]
    return dict(schema='cortac.scratch.triage.integration.v1', scope=SCOPE,
                episodes=len(rows), rows=rows,
                all_expected_outcomes=all(r['expected_outcome_matched'] for r in rows),
                authority='NONE', controller_closure='SUPPLIED_UNVERIFIED',
                real_model_calls=0, real_external_principals=0, scored_study=False,
                external_execution_enabled=False, actual_disposable_database_effects=True,
                provenance='SYNTHETIC_FIXTURE')
