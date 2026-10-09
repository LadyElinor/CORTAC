"""Independent opt-in complaint-triage regressions.

Expected outcomes were fixed before inspecting the new implementation:

* Every complaint keeps separate evidence, a hold, and an appeal route. One
  resolved complaint never silently resolves another, including a later arrival.
* Unknown claimant control requires the pinned independent factfinding route;
  absent evidence stays unresolved and known declared conflicts cannot disappear.
* Protected review/audit allocations cannot become ordinary work or repair funds.
  Exhaustion is explicit, retains holds, and preserves observable partial effects.
* Reserved work for a finite known worklist cannot be consumed by duplicates;
  duplicate reports remain individually traceable.
* Stale, revoked, replayed, conflicted, and malformed requests fail closed.
  Serialization, rollback, and copy isolation protect the exact pinned record.

These are synthetic trusted-harness assertions, not proof of authentication,
real-world controller discovery, institutional independence, or real authority.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3
import threading
import unittest

from wac_offline.runner import RunnerError, SCOPE, digest, evidence_record
from wac_offline.runner_fixtures import checks, fixture as legacy_fixture
from wac_offline.triage import TriageGateway, make_grant


def repin(data):
    """Pin the intentionally changed synthetic inputs, without changing authority."""
    policy_digest = digest('Policy', data['policy'])
    for name in ('initial', 'repair'):
        data[name]['policy_digest'] = policy_digest
        data[name]['case_id'] = data['policy']['case_id']
    for mandate in data['mandates']:
        mandate['policy_digest'] = policy_digest
        mandate['case_id'] = data['policy']['case_id']
        mandate['proposal_digest'] = digest('Proposal', data[mandate['id']])
    return data


def triage_fixture(complaints=('c1', 'c2'), *, ordinary=24, repair=12,
                   factfinding=4, review=6, audit=3, repair_audit=None,
                   unknown_controller=None, controllers=None, late_source='repair'):
    """Independent test inputs; expected outcomes do not come from demo output."""
    data = legacy_fixture(budget=300)
    data['policy']['principals'].extend([
        dict(id='factfinder', controller='synthetic-factfinder', roles=['assessor']),
        dict(id='second_reviewer', controller='synthetic-second-reviewer', roles=['reviewer']),
        dict(id='support_authorizer', controller='synthetic-support-authorizer', roles=['authorizer']),
    ])
    for principal in data['policy']['principals']:
        if principal['id'] in (controllers or {}):
            principal['controller'] = controllers[principal['id']]
    data['evidence'].extend([
        evidence_record('source-overlap', 'second-supplied-ledger', '12'),
        evidence_record('source-appeal', 'supplied-appeal-ledger', '12'),
        evidence_record('control-source', 'supplied-controller-declaration', 'synthetic-outsider-control'),
    ])
    data['repair']['evidence'] = [dict(id=item['id'], digest=digest('Evidence', item))
        for item in sorted(data['evidence'], key=lambda item: item['id'])
        if item['id'] in ('source-v2', 'source-overlap', 'source-appeal')]
    data['repair']['decision_record']['evidence_refs'] = [r['id'] for r in data['repair']['evidence']]
    repin(data)
    slots = []
    for identifier in tuple(complaints) + ('late',):
        duplicate = 'c1' if identifier == 'duplicate' else None
        claimant = 'unknown-outsider' if identifier == 'unknown' else 'outsider'
        slots.append(dict(id=identifier, claimant=claimant,
            work_item_id=late_source if identifier == 'late' else 'initial',
            evidence_ids=['source-overlap'] if identifier == 'c2' else ['source-v2'],
            reason='Second independent concern' if identifier == 'c2' else 'Correct the supplied ledger',
            duplicate_of=duplicate,
            appeals=[dict(evidence_ids=['source-appeal'], reason='Independently retained appeal')],
            factfinding_budget=0 if duplicate else factfinding,
            review_budget=0 if duplicate else review))
    config = dict(schema='cortac.scratch.triage.config.v1',
        evidence_digest=digest('TriageEvidence', sorted(data['evidence'], key=lambda item: item['id'])),
        ordinary_budget=ordinary,
        repair_budget=repair, complaints=slots,
        work_items=[dict(id=name, proposal_digest=digest('Proposal', data[name]),
                         expected_revision=0 if name == 'initial' else 1,
                         operation='COMMIT' if name == 'initial' else 'REPAIR',
                         mandate_id=name, executor='executor',
                         complaint_ids=[] if name == 'initial' else sorted(complaints),
                         audit_budget=(repair_audit if name == 'repair' and repair_audit is not None else audit))
                    for name in ('initial', 'repair')])
    data['triage_config'] = config
    versions = {identifier: 0 for identifier in complaints}
    grants = []
    def grant(identifier, action, actor, *, bound=None, item=None, revision=1, finding=None):
        record = make_grant(identifier, action, actor, 'support_authorizer',
                            data['policy'], config, complaint_versions=bound,
                            work_item_id=item, expected_revision=revision,
                            expires_tick=1000, finding=finding)
        grants.append(record)
        return record
    grant('initial-audit', 'AUDIT', 'auditor', bound={}, item='initial')
    grant('review-all', 'REVIEW', 'reviewer', bound=versions, item='repair')
    grant('repair-audit', 'AUDIT', 'repair_auditor', bound=versions, item='repair', revision=2)
    if 'unknown' in complaints:
        grant('find-unresolved', 'FACT_FINDING', 'factfinder', bound={'unknown': 0},
              finding=dict(status='UNRESOLVED', controller=None, evidence_ids=[]))
        grant('find-controller', 'FACT_FINDING', 'factfinder', bound={'unknown': 0},
              finding=dict(status='DECLARED_CONTROLLER',
                           controller=unknown_controller or 'synthetic-found-outsider',
                           evidence_ids=['control-source']))
    data['grants'] = grants
    return data


def add_grant(data, identifier, action, actor, *, versions=None, item=None,
              revision=1, expires=1000, finding=None, authorizer='support_authorizer'):
    grant = make_grant(identifier, action, actor, authorizer, data['policy'],
                       data['triage_config'], complaint_versions=versions,
                       work_item_id=item, expected_revision=revision,
                       expires_tick=expires, finding=finding)
    data['grants'].append(grant)
    return grant


def without_accounting(state):
    """Select effects/holds/authority; attempted work may remain metered."""
    return {key: deepcopy(state[key]) for key in (
        'revision', 'value', 'effects', 'used_mandates', 'revoked_mandates',
        'pending_audit', 'participants', 'receipts', 'challenges',
        'complaints', 'used_grants', 'revoked_grants', 'review_records',
        'factfinding_records', 'audit_records', 'work_item_effects', 'activity_participants',
    ) if key in state}


class TriageTests(unittest.TestCase):
    def gateway(self, data):
        gateway = TriageGateway(data['policy'], data['evidence'], data['mandates'],
                                triage_config=data['triage_config'], grants=data['grants'])
        self.addCleanup(gateway.close)
        return gateway

    def initial(self, gateway, data, audit=True):
        effect = gateway.commit(data['initial'], checks(gateway, data['initial'], data['policy']),
                                'initial', 'executor', 'initial')
        if audit:
            gateway.audit(effect, 'auditor', 'initial-audit')
        return effect

    def lodge(self, gateway, data, effect, identifiers=None):
        identifiers = (data['triage_config']['work_items'][1]['complaint_ids']
                       if identifiers is None else identifiers)
        result = []
        for identifier in identifiers:
            slot = next(s for s in data['triage_config']['complaints'] if s['id'] == identifier)
            result.append(gateway.lodge(identifier, slot['claimant'], effect,
                slot['evidence_ids'], slot['reason'], duplicate_of=slot['duplicate_of']))
        return result

    def prepared(self, data=None):
        data = triage_fixture() if data is None else data
        gateway = self.gateway(data)
        effect = self.initial(gateway, data)
        self.lodge(gateway, data, effect)
        return data, gateway, effect

    def repair_receipts(self, gateway, data):
        identifiers = data['triage_config']['work_items'][1]['complaint_ids']
        review = gateway.review(identifiers, data['repair'], 'reviewer', 'review-all')
        return checks(gateway, data['repair'], data['policy'], repair=True) + [review]

    def repair(self, gateway, data):
        return gateway.commit(data['repair'], self.repair_receipts(gateway, data),
                              'repair', 'executor', 'repair')

    def assert_open(self, gateway, *identifiers):
        state = gateway.snapshot()
        for identifier in identifiers:
            with self.subTest(complaint=identifier):
                self.assertIs(state['complaints'][identifier]['hold'], True)
                self.assertIsNone(state['complaints'][identifier]['resolution'])

    def assert_incomplete(self, gateway):
        state = gateway.snapshot()
        self.assertTrue(state['incomplete'])
        self.assertTrue(any(c['hold'] for c in state['complaints'].values()) or state['pending_audit'])

    def denied(self, gateway, operation, pattern=None):
        before = gateway.snapshot()
        with self.assertRaises(RunnerError) as caught:
            operation()
        if pattern:
            self.assertRegex(str(caught.exception), pattern)
        after = gateway.snapshot()
        self.assertEqual(without_accounting(after), without_accounting(before))
        return before, after

    def test_overlapping_complaints_keep_independent_evidence_and_holds(self):
        data, gateway, original = self.prepared()
        before = gateway.snapshot()
        self.assert_open(gateway, 'c1', 'c2')
        self.assertNotEqual(before['complaints']['c1']['current_digest'],
                            before['complaints']['c2']['current_digest'])
        self.assertEqual(before['complaints']['c1']['versions'][0]['evidence'][0]['id'], 'source-v2')
        self.assertEqual(before['complaints']['c2']['versions'][0]['evidence'][0]['id'], 'source-overlap')
        receipts = self.repair_receipts(gateway, data)
        self.assert_open(gateway, 'c1', 'c2')
        effect = gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
        self.assert_open(gateway, 'c1', 'c2')
        state = gateway.snapshot()
        self.assertEqual((state['revision'], state['value']), (2, '12'))
        self.assertEqual(state['pending_audit'], effect['id'])
        self.assertEqual(state['effects'][0], original)
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        state = gateway.snapshot()
        for identifier in ('c1', 'c2'):
            self.assertIs(state['complaints'][identifier]['hold'], False)
            self.assertEqual(state['complaints'][identifier]['appeal_status'], 'RESOLVED')
            self.assertTrue(state['complaints'][identifier]['resolution'])
            self.assertEqual(state['complaints'][identifier]['versions'], before['complaints'][identifier]['versions'])
        self.assertEqual(state['used_mandates'], ['initial', 'repair'])
        self.assertIsNone(state['pending_audit'])

    def test_appealing_one_resolved_complaint_does_not_reopen_or_erase_another(self):
        data, gateway, _ = self.prepared()
        effect = self.repair(gateway, data)
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        second = deepcopy(gateway.snapshot()['complaints']['c2'])
        gateway.appeal('c1', 'outsider', ['source-appeal'], 'Independently retained appeal')
        self.assert_open(gateway, 'c1')
        state = gateway.snapshot()
        self.assertEqual(state['complaints']['c2'], second)
        self.assertEqual(state['complaints']['c1']['version'], 1)
        self.assertEqual(len(state['complaints']['c1']['versions']), 2)
        self.assertEqual(len(state['complaints']['c1']['resolutions']), 1)
        self.assertEqual(len(state['complaints']['c1']['appeals']), 1)

    def test_audit_resolves_only_unchanged_complaint_versions(self):
        data, gateway, _ = self.prepared()
        effect = self.repair(gateway, data)
        gateway.appeal('c2', 'outsider', ['source-appeal'], 'Independently retained appeal')
        appealed = deepcopy(gateway.snapshot()['complaints']['c2'])
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assertIs(gateway.snapshot()['complaints']['c1']['hold'], False)
        self.assert_open(gateway, 'c2')
        self.assertEqual(gateway.snapshot()['complaints']['c2'], appealed)
        self.assertIsNone(gateway.snapshot()['pending_audit'])

    def test_later_complaint_before_commit_is_not_covered_by_old_review(self):
        data, gateway, original = self.prepared(triage_fixture(late_source='initial'))
        receipts = self.repair_receipts(gateway, data)
        self.lodge(gateway, data, original, ['late'])
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assert_open(gateway, 'c1', 'c2', 'late')
        self.assertEqual(len(gateway.snapshot()['effects']), 1)

    def test_later_complaint_after_commit_survives_original_audit(self):
        data, gateway, _ = self.prepared()
        effect = self.repair(gateway, data)
        self.lodge(gateway, data, effect, ['late'])
        late = deepcopy(gateway.snapshot()['complaints']['late'])
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assertEqual(gateway.snapshot()['complaints']['late'], late)
        self.assert_open(gateway, 'late')
        self.assertIs(gateway.snapshot()['complaints']['c1']['hold'], False)
        self.assertIs(gateway.snapshot()['complaints']['c2']['hold'], False)

    def test_appeal_before_commit_invalidates_version_bound_review(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        gateway.appeal('c1', 'outsider', ['source-appeal'], 'Independently retained appeal')
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assert_open(gateway, 'c1', 'c2')

    def test_unknown_claimant_without_evidence_stays_visibly_unresolved(self):
        data, gateway, _ = self.prepared(triage_fixture(('unknown',)))
        self.assert_open(gateway, 'unknown')
        self.assertEqual(gateway.snapshot()['complaints']['unknown']['appeal_status'], 'FACT_FINDING_REQUIRED')
        self.denied(gateway, lambda: gateway.review(['unknown'], data['repair'], 'reviewer', 'review-all'))
        finding = gateway.factfind('unknown', 'factfinder', 'find-unresolved')
        self.assertEqual(finding['result'], 'UNRESOLVED')
        self.assertEqual(finding['independence'], 'CLAIMANT_CONTROLLER_UNKNOWN')
        self.assertEqual(finding['controller_closure'], 'SUPPLIED_UNVERIFIED')
        complaint = gateway.snapshot()['complaints']['unknown']
        self.assertIsNone(complaint['controller'])
        self.assertEqual(complaint['appeal_status'], 'FACT_FINDING_REQUIRED')
        self.assert_open(gateway, 'unknown')

    def test_supplied_factfinding_can_route_review_but_does_not_authenticate(self):
        data, gateway, _ = self.prepared(triage_fixture(('unknown',)))
        finding = gateway.factfind('unknown', 'factfinder', 'find-controller')
        self.assertEqual(finding['result'], 'DECLARED_CONTROLLER')
        self.assertEqual(finding['controller_closure'], 'SUPPLIED_UNVERIFIED')
        self.assertEqual(finding['controller'], 'synthetic-found-outsider')
        self.assert_open(gateway, 'unknown')
        effect = self.repair(gateway, data)
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assertIs(gateway.snapshot()['complaints']['unknown']['hold'], False)

    def test_factfinding_actor_and_exact_grant_are_pinned(self):
        data, gateway, _ = self.prepared(triage_fixture(('unknown',)))
        self.denied(gateway, lambda: gateway.factfind('unknown', 'assessor', 'find-controller'))
        self.denied(gateway, lambda: gateway.factfind('unknown', 'factfinder', 'self-issued'))
        self.assert_open(gateway, 'unknown')
        self.assertIsNone(gateway.snapshot()['complaints']['unknown']['controller'])

    def test_discovered_declared_conflict_cannot_be_overwritten(self):
        data = triage_fixture(('unknown',), unknown_controller='synthetic-controller-reviewer')
        add_grant(data, 'find-new-label', 'FACT_FINDING', 'factfinder', versions={'unknown': 0},
                  finding=dict(status='DECLARED_CONTROLLER', controller='synthetic-new-label', evidence_ids=['control-source']))
        data, gateway, _ = self.prepared(data)
        gateway.factfind('unknown', 'factfinder', 'find-controller')
        self.denied(gateway, lambda: gateway.review(['unknown'], data['repair'], 'reviewer', 'review-all'))
        self.denied(gateway, lambda: gateway.factfind('unknown', 'factfinder', 'find-new-label'))
        self.assertEqual(gateway.snapshot()['complaints']['unknown']['controller'], 'synthetic-controller-reviewer')
        self.assert_open(gateway, 'unknown')

    def test_original_declared_controller_conflict_blocks_grant_construction(self):
        data = triage_fixture(controllers={'reviewer': 'synthetic-controller-outsider'})
        with self.assertRaisesRegex(RunnerError, 'controller conflict'):
            self.gateway(data)

    def test_protected_audit_survives_ordinary_budget_exhaustion(self):
        data = triage_fixture(ordinary=4)
        gateway = self.gateway(data)
        effect = self.initial(gateway, data, audit=False)
        before = gateway.snapshot()['budgets']
        self.assertEqual(before['ordinary'], dict(limit=4, used=4))
        gateway.audit(effect, 'auditor', 'initial-audit')
        after = gateway.snapshot()['budgets']
        self.assertEqual(after['ordinary'], before['ordinary'])
        self.assertEqual(after['repair'], before['repair'])
        self.assertEqual(after['audit:initial']['used'], before['audit:initial']['used'] + 1)
        self.assertIsNone(gateway.snapshot()['pending_audit'])

    def test_review_reserve_does_not_authorize_or_fund_repair(self):
        data, gateway, _ = self.prepared(triage_fixture(repair=0))
        before = gateway.snapshot()['budgets']
        gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all')
        self.assert_open(gateway, 'c1', 'c2')
        after_review = gateway.snapshot()['budgets']
        self.assertEqual(after_review['ordinary'], before['ordinary'])
        self.assertEqual(after_review['repair'], before['repair'])
        self.assertEqual(after_review['review:c1']['used'], before['review:c1']['used'] + 1)
        self.assertEqual(after_review['review:c2']['used'], before['review:c2']['used'] + 1)
        self.denied(gateway, lambda: gateway.issue(data['repair'], 'ASSESSMENT', 'assessor'))
        self.assert_incomplete(gateway)
        self.assertEqual((gateway.snapshot()['revision'], gateway.snapshot()['value']), (1, '10'))

    def test_exhausted_review_reserve_retains_holds_without_borrowing(self):
        data, gateway, _ = self.prepared(triage_fixture(review=0))
        before = gateway.snapshot()['budgets']
        self.denied(gateway, lambda: gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all'))
        after = gateway.snapshot()['budgets']
        self.assertEqual(after['ordinary'], before['ordinary'])
        self.assertEqual(after['repair'], before['repair'])
        self.assertEqual(after['audit:repair'], before['audit:repair'])
        self.assert_open(gateway, 'c1', 'c2')
        self.assert_incomplete(gateway)

    def test_exhausted_final_audit_preserves_observable_partial_effect(self):
        data, gateway, _ = self.prepared(triage_fixture(repair_audit=0))
        effect = self.repair(gateway, data)
        before = gateway.snapshot()
        self.denied(gateway, lambda: gateway.audit(effect, 'repair_auditor', 'repair-audit'))
        after = gateway.snapshot()
        self.assertEqual((after['revision'], after['value']), (2, '12'))
        self.assertEqual(after['effects'], before['effects'])
        self.assertEqual(after['pending_audit'], effect['id'])
        self.assertEqual(after['used_mandates'], ['initial', 'repair'])
        self.assert_open(gateway, 'c1', 'c2')
        self.assert_incomplete(gateway)

    def test_exhausted_factfinding_reserve_keeps_unknown_claimant_hold(self):
        data, gateway, _ = self.prepared(triage_fixture(('unknown',), factfinding=0))
        before = gateway.snapshot()['budgets']
        self.denied(gateway, lambda: gateway.factfind('unknown', 'factfinder', 'find-controller'))
        self.assert_open(gateway, 'unknown')
        self.assert_incomplete(gateway)
        self.assertEqual(gateway.snapshot()['budgets']['repair'], before['repair'])
        self.assertEqual(gateway.snapshot()['budgets']['review:unknown'], before['review:unknown'])

    def test_duplicate_complaints_share_work_but_retain_individual_traceability(self):
        data, gateway, _ = self.prepared(triage_fixture(('c1', 'duplicate', 'c2')))
        before = gateway.snapshot()
        self.assertEqual(before['complaints']['duplicate']['duplicate_of'], 'c1')
        self.assertNotEqual(before['complaints']['c1']['current_digest'],
                            before['complaints']['duplicate']['current_digest'])
        self.assert_open(gateway, 'c1', 'duplicate', 'c2')
        effect = self.repair(gateway, data)
        after = gateway.snapshot()
        self.assertEqual(after['budgets']['review:c1']['used'], before['budgets']['review:c1']['used'] + 1)
        self.assertEqual(after['budgets']['review:c2']['used'], before['budgets']['review:c2']['used'] + 1)
        self.assertNotIn('review:duplicate', after['budgets'])
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assertEqual(set(gateway.snapshot()['complaints']), {'c1', 'duplicate', 'c2'})
        for identifier in ('c1', 'duplicate', 'c2'):
            self.assertIs(gateway.snapshot()['complaints'][identifier]['hold'], False)

    def test_repeated_duplicate_attempts_cannot_starve_other_reserved_work(self):
        data, gateway, original = self.prepared(triage_fixture(('c1', 'duplicate', 'c2')))
        before = deepcopy(gateway.snapshot()['budgets']['review:c2'])
        for _ in range(8):
            self.denied(gateway, lambda: self.lodge(gateway, data, original, ['duplicate']))
        self.assertEqual(gateway.snapshot()['budgets']['review:c2'], before)
        self.assertEqual(gateway.snapshot()['budgets']['review:c1']['used'], 0)
        gateway.review(['c1', 'c2', 'duplicate'], data['repair'], 'reviewer', 'review-all')
        self.assertEqual(gateway.snapshot()['budgets']['review:c2']['used'], 1)
        self.assert_open(gateway, 'c1', 'duplicate', 'c2')

    def test_duplicate_appeal_is_independently_retained(self):
        data, gateway, _ = self.prepared(triage_fixture(('c1', 'duplicate', 'c2')))
        effect = self.repair(gateway, data)
        gateway.appeal('duplicate', 'outsider', ['source-appeal'], 'Independently retained appeal')
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assert_open(gateway, 'duplicate')
        self.assertIs(gateway.snapshot()['complaints']['c1']['hold'], False)
        self.assertIs(gateway.snapshot()['complaints']['c2']['hold'], False)
        self.assertEqual(gateway.snapshot()['complaints']['duplicate']['version'], 1)

    def test_unpinned_complaint_and_changed_pinned_lodgement_fail_closed(self):
        data = triage_fixture()
        gateway = self.gateway(data)
        original = self.initial(gateway, data)
        for args in (
            ('unbounded', 'outsider', ['source-v2'], 'Correct the supplied ledger'),
            ('c1', 'other-claimant', ['source-v2'], 'Correct the supplied ledger'),
            ('c1', 'outsider', ['source-overlap'], 'Correct the supplied ledger'),
            ('c1', 'outsider', ['source-v2'], 'Changed reason'),
        ):
            with self.subTest(args=args):
                self.denied(gateway, lambda: gateway.lodge(args[0], args[1], original, args[2], args[3]))
        self.assertEqual(gateway.snapshot()['complaints'], {})

    def test_forged_current_effect_and_unresolved_lodgement_evidence_fail_closed(self):
        data = triage_fixture()
        gateway = self.gateway(data)
        original = self.initial(gateway, data)
        forged = deepcopy(original)
        forged['after_value'] = 'forged'
        self.denied(gateway, lambda: gateway.lodge('c1', 'outsider', forged, ['source-v2'], 'Correct the supplied ledger'))
        for evidence in ([], ['missing'], ['source-v2', 'source-v2'], 'source-v2'):
            with self.subTest(evidence=evidence):
                self.denied(gateway, lambda: gateway.lodge('c1', 'outsider', original, evidence, 'Correct the supplied ledger'))

    def test_appeals_must_match_claimant_and_next_exact_pinned_version(self):
        data, gateway, _ = self.prepared()
        for actor, evidence, reason in (
            ('reviewer', ['source-appeal'], 'Independently retained appeal'),
            ('outsider', ['source-v2'], 'Independently retained appeal'),
            ('outsider', ['source-appeal'], 'Changed reason'),
        ):
            with self.subTest(actor=actor, evidence=evidence, reason=reason):
                self.denied(gateway, lambda: gateway.appeal('c1', actor, evidence, reason))
        gateway.appeal('c1', 'outsider', ['source-appeal'], 'Independently retained appeal')
        self.denied(gateway, lambda: gateway.appeal('c1', 'outsider', ['source-appeal'], 'Independently retained appeal'))
        self.assertEqual(gateway.snapshot()['complaints']['c1']['version'], 1)

    def test_review_grant_replay_and_cross_work_item_use_are_rejected(self):
        data, gateway, _ = self.prepared()
        gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all')
        self.denied(gateway, lambda: gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all'))
        self.denied(gateway, lambda: gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'initial-audit'))
        self.assert_open(gateway, 'c1', 'c2')

    def test_unissued_review_receipt_is_not_a_self_issued_grant(self):
        data, source, _ = self.prepared()
        foreign = source.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all')
        target = self.gateway(data)
        initial = self.initial(target, data)
        self.lodge(target, data, initial)
        receipts = checks(target, data['repair'], data['policy'], repair=True) + [foreign]
        self.denied(target, lambda: target.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assert_open(target, 'c1', 'c2')

    def test_expired_and_stale_grants_cannot_authorize_review(self):
        data = triage_fixture()
        add_grant(data, 'expired', 'REVIEW', 'reviewer', versions={'c1': 0, 'c2': 0}, item='repair', expires=1)
        data, gateway, _ = self.prepared(data)
        self.denied(gateway, lambda: gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'expired'))
        gateway.appeal('c1', 'outsider', ['source-appeal'], 'Independently retained appeal')
        self.denied(gateway, lambda: gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all'))
        self.assert_open(gateway, 'c1', 'c2')

    def test_grant_revocation_requires_exact_pinned_authorizer(self):
        data, gateway, _ = self.prepared()
        self.denied(gateway, lambda: gateway.revoke_grant('review-all', 'repair_authorizer', 'Unapproved withdrawal'))
        gateway.revoke_grant('review-all', 'support_authorizer', 'Withdraw review support')
        self.denied(gateway, lambda: gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all'))
        self.denied(gateway, lambda: gateway.revoke_grant('review-all', 'support_authorizer', 'Repeat withdrawal'))
        self.assert_open(gateway, 'c1', 'c2')

    def test_revoked_repair_mandate_blocks_effect_despite_review_reserve(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        gateway.revoke('repair', 'repair_authorizer', 'Withdraw exact repair mandate')
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assertEqual(gateway.snapshot()['used_mandates'], ['initial'])
        self.assert_open(gateway, 'c1', 'c2')

    def test_revoked_audit_grant_cannot_erase_already_committed_effect(self):
        data, gateway, _ = self.prepared()
        effect = self.repair(gateway, data)
        gateway.revoke_grant('repair-audit', 'support_authorizer', 'Withdraw future audit support')
        self.denied(gateway, lambda: gateway.audit(effect, 'repair_auditor', 'repair-audit'))
        self.assertEqual(gateway.snapshot()['effects'][-1], effect)
        self.assertEqual(gateway.snapshot()['pending_audit'], effect['id'])
        self.assert_open(gateway, 'c1', 'c2')

    def test_repair_and_audit_replay_never_repeat_effect_or_resolution(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        effect = gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.denied(gateway, lambda: gateway.audit(effect, 'repair_auditor', 'repair-audit'))
        self.assertEqual(len(gateway.snapshot()['effects']), 2)
        for complaint in gateway.snapshot()['complaints'].values():
            self.assertEqual(len(complaint['resolutions']), 1)

    def test_forged_audit_cannot_clear_any_complaint(self):
        data, gateway, _ = self.prepared()
        effect = self.repair(gateway, data)
        forged = deepcopy(effect)
        forged['after_value'] = 'forged'
        self.denied(gateway, lambda: gateway.audit(forged, 'repair_auditor', 'repair-audit'))
        self.assert_open(gateway, 'c1', 'c2')

    def test_repair_authorizer_and_executor_declared_conflict_is_preserved(self):
        data = triage_fixture(controllers={'repair_authorizer': 'synthetic-controller-executor'})
        data, gateway, _ = self.prepared(data)
        receipts = self.repair_receipts(gateway, data)
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assertEqual((gateway.snapshot()['revision'], gateway.snapshot()['value']), (1, '10'))
        self.assert_open(gateway, 'c1', 'c2')

    def test_concurrent_repair_commits_consume_one_mandate_and_one_effect(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        barrier = threading.Barrier(8)
        def attempt():
            barrier.wait(timeout=10)
            try:
                return gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
            except RunnerError:
                return None
        with ThreadPoolExecutor(max_workers=8) as workers:
            futures = [workers.submit(attempt) for _ in range(8)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sum(result is not None for result in results), 1)
        state = gateway.snapshot()
        self.assertEqual((state['revision'], state['value']), (2, '12'))
        self.assertEqual(len(state['effects']), 2)
        self.assertEqual(state['used_mandates'], ['initial', 'repair'])
        self.assert_open(gateway, 'c1', 'c2')

    def test_concurrent_appeal_and_review_have_serialized_version_outcome(self):
        data, gateway, _ = self.prepared()
        barrier = threading.Barrier(2)
        def review():
            barrier.wait(timeout=10)
            try:
                return gateway.review(['c1', 'c2'], data['repair'], 'reviewer', 'review-all')
            except RunnerError:
                return None
        def appeal():
            barrier.wait(timeout=10)
            return gateway.appeal('c1', 'outsider', ['source-appeal'], 'Independently retained appeal')
        with ThreadPoolExecutor(max_workers=2) as workers:
            reviewed, appealed = workers.submit(review), workers.submit(appeal)
            receipt = reviewed.result(timeout=20)
            appealed.result(timeout=20)
        state = gateway.snapshot()
        self.assertEqual(state['complaints']['c1']['version'], 1)
        self.assertEqual(len(state['complaints']['c1']['appeals']), 1)
        self.assert_open(gateway, 'c1', 'c2')
        if receipt is not None:
            receipts = checks(gateway, data['repair'], data['policy'], repair=True) + [receipt]
            self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assertEqual(len(gateway.snapshot()['effects']), 1)

    def test_concurrent_grant_revocation_and_commit_follow_committed_order(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        barrier = threading.Barrier(2)
        def commit():
            barrier.wait(timeout=10)
            try:
                return gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
            except RunnerError:
                return None
        def revoke():
            barrier.wait(timeout=10)
            return gateway.revoke_grant('review-all', 'support_authorizer', 'Withdraw before any later repair')
        with ThreadPoolExecutor(max_workers=2) as workers:
            committed, revoked = workers.submit(commit), workers.submit(revoke)
            effect, revocation = committed.result(timeout=20), revoked.result(timeout=20)
        state = gateway.snapshot()
        self.assertIn('review-all', state['revoked_grants'])
        relevant = [r for r in state['journal'] if r['action'] in ('commit', 'revoke_grant')][-2:]
        self.assertEqual({r['action'] for r in relevant}, {'commit', 'revoke_grant'})
        if relevant[0]['action'] == 'revoke_grant':
            self.assertIsNone(effect)
            self.assertEqual(state['revision'], 1)
        else:
            self.assertIsNotNone(effect)
            self.assertEqual(state['revision'], 2)
            self.assertEqual(state['pending_audit'], effect['id'])
        self.assertEqual(revocation, state['revoked_grants']['review-all'])
        self.assert_open(gateway, 'c1', 'c2')

    def test_sqlite_commit_failure_rolls_back_funds_grants_effect_and_journal(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        before = gateway.snapshot()
        with gateway._db:
            gateway._db.execute("CREATE TRIGGER fail_write BEFORE UPDATE ON state "
                                "BEGIN SELECT RAISE(ABORT, 'injected persistence failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'injected persistence failure'):
            gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
        self.assertEqual(gateway.snapshot(), before)
        with gateway._db:
            gateway._db.execute('DROP TRIGGER fail_write')
        effect = gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair')
        self.assertEqual(gateway.snapshot()['effects'][-1], effect)
        self.assertEqual(gateway.snapshot()['used_mandates'], ['initial', 'repair'])

    def test_sqlite_audit_failure_rolls_back_all_complaint_resolutions(self):
        data, gateway, _ = self.prepared()
        effect = self.repair(gateway, data)
        before = gateway.snapshot()
        with gateway._db:
            gateway._db.execute("CREATE TRIGGER fail_write BEFORE UPDATE ON state "
                                "BEGIN SELECT RAISE(ABORT, 'injected audit failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'injected audit failure'):
            gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assertEqual(gateway.snapshot(), before)
        self.assert_open(gateway, 'c1', 'c2')
        with gateway._db:
            gateway._db.execute('DROP TRIGGER fail_write')
        gateway.audit(effect, 'repair_auditor', 'repair-audit')
        self.assertIsNone(gateway.snapshot()['pending_audit'])

    def test_constructor_inputs_and_all_returned_records_are_copy_isolated(self):
        data = triage_fixture()
        original = deepcopy(data)
        gateway = self.gateway(data)
        data['policy']['operation_budget'] = 1
        data['triage_config']['ordinary_budget'] = 0
        data['triage_config']['complaints'][0]['appeals'].clear()
        data['evidence'][0]['content'] = 'caller modification'
        data['grants'][0]['actor'] = 'caller modification'
        initial = self.initial(gateway, original)
        lodged = self.lodge(gateway, original, initial)
        lodged[0]['hold'] = False
        lodged[0]['versions'][0]['reason'] = 'caller modification'
        snapshot = gateway.snapshot()
        snapshot['complaints']['c2']['hold'] = False
        snapshot['budgets']['review:c1']['limit'] = 999
        self.assert_open(gateway, 'c1', 'c2')
        self.assertEqual(gateway.snapshot()['budgets']['review:c1']['limit'], 6)
        self.assertEqual(gateway.snapshot()['complaints']['c1']['versions'][0]['reason'], 'Correct the supplied ledger')
        receipts = self.repair_receipts(gateway, original)
        retained = deepcopy(receipts)
        receipts[-1]['actor'] = 'caller modification'
        self.assertEqual(gateway.snapshot()['receipts'][retained[-1]['id']], retained[-1])
        effect = gateway.commit(original['repair'], retained, 'repair', 'executor', 'repair')
        stored_effect = deepcopy(effect)
        effect['complaint_bindings'].clear()
        self.assertEqual(gateway.snapshot()['effects'][-1], stored_effect)
        result = gateway.audit(stored_effect, 'repair_auditor', 'repair-audit')
        result['resolved_complaints'].clear()
        self.assertEqual(gateway.snapshot()['audit_records'][-1]['resolved_complaints'], ['c1', 'c2'])

    def test_closed_constructor_records_reject_every_missing_and_unknown_field(self):
        selectors = {
            'config': lambda d: d['triage_config'],
            'slot': lambda d: d['triage_config']['complaints'][0],
            'appeal': lambda d: d['triage_config']['complaints'][0]['appeals'][0],
            'work_item': lambda d: d['triage_config']['work_items'][0],
            'grant': lambda d: d['grants'][0],
            'binding': lambda d: d['grants'][1]['complaints'][0],
            'finding': lambda d: d['grants'][-1]['finding'],
        }
        for label, select in selectors.items():
            template = triage_fixture(('unknown',))
            for field in list(select(template)) + ['unknown_field']:
                with self.subTest(record=label, field=field):
                    data = triage_fixture(('unknown',))
                    record = select(data)
                    if field == 'unknown_field':
                        record[field] = True
                    else:
                        del record[field]
                    with self.assertRaises(RunnerError):
                        self.gateway(data)

    def test_constructor_rejects_bool_budgets_wrong_types_and_untrusted_authority_labels(self):
        cases = [
            ('config', 'ordinary_budget', True), ('config', 'repair_budget', -1),
            ('config', 'evidence_digest', '0' * 64), ('config', 'complaints', {}),
            ('config', 'work_items', []), ('slot', 'review_budget', False),
            ('slot', 'factfinding_budget', 1.0), ('slot', 'appeals', {}),
            ('slot', 'duplicate_of', 'missing'), ('slot', 'claimant', ' '),
            ('slot', 'evidence_ids', ['missing']), ('slot', 'work_item_id', 'missing'),
            ('item', 'expected_revision', False), ('item', 'audit_budget', True),
            ('item', 'operation', 'EXTERNAL_WRITE'), ('item', 'executor', 'support_authorizer'),
            ('grant', 'max_uses', True), ('grant', 'max_uses', 2),
            ('grant', 'expected_revision', True), ('grant', 'epoch', True),
            ('grant', 'scope', 'REAL_AUTHORITY'), ('grant', 'provenance', 'AUTHENTICATED'),
            ('grant', 'expires_tick', True), ('grant', 'policy_digest', '0' * 64),
            ('grant', 'triage_digest', '0' * 64), ('grant', 'actor', 'outsider'),
            ('grant', 'authorizer', 'reviewer'), ('grant', 'action', 'GRANT_AUTHORITY'),
        ]
        for kind, field, value in cases:
            with self.subTest(kind=kind, field=field, value=value):
                data = triage_fixture()
                record = {'config': data['triage_config'], 'slot': data['triage_config']['complaints'][0],
                          'item': data['triage_config']['work_items'][0], 'grant': data['grants'][0]}[kind]
                record[field] = value
                with self.assertRaises(RunnerError):
                    self.gateway(data)

    def test_constructor_rejects_duplicate_identities_cycles_and_reserve_overcommit(self):
        for kind in ('slot', 'item', 'grant', 'duplicate_budget', 'duplicate_cycle', 'overcommit'):
            with self.subTest(kind=kind):
                data = triage_fixture(('c1', 'duplicate', 'c2'))
                config = data['triage_config']
                if kind == 'slot': config['complaints'].append(deepcopy(config['complaints'][0]))
                elif kind == 'item': config['work_items'].append(deepcopy(config['work_items'][0]))
                elif kind == 'grant': data['grants'].append(deepcopy(data['grants'][0]))
                elif kind == 'duplicate_budget':
                    next(s for s in config['complaints'] if s['id'] == 'duplicate')['review_budget'] = 1
                elif kind == 'duplicate_cycle':
                    root = next(s for s in config['complaints'] if s['id'] == 'c1')
                    root.update(duplicate_of='duplicate', review_budget=0, factfinding_budget=0)
                else: config['ordinary_budget'] = data['policy']['operation_budget']
                with self.assertRaises(RunnerError):
                    self.gateway(data)

    def test_factfinding_cannot_declare_controller_without_pinned_nonempty_evidence(self):
        data = triage_fixture(('unknown',))
        data['grants'][-1]['finding']['evidence_ids'] = []
        with self.assertRaises(RunnerError):
            self.gateway(data)

    def test_recorded_claims_never_upgrade_synthetic_authority_or_controller_evidence(self):
        data, gateway, _ = self.prepared(triage_fixture(('unknown',)))
        finding = gateway.factfind('unknown', 'factfinder', 'find-controller')
        effect = self.repair(gateway, data)
        audited = gateway.audit(effect, 'repair_auditor', 'repair-audit')
        for record in (finding, audited):
            self.assertEqual(record['authority'], 'NONE')
            self.assertEqual(record['controller_closure'], 'SUPPLIED_UNVERIFIED')
            self.assertEqual(record['scope'], SCOPE)
            self.assertEqual(record['provenance'], 'SYNTHETIC_FIXTURE')
        self.assertEqual(effect['scope'], SCOPE)
        self.assertEqual(effect['provenance'], 'SYNTHETIC_FIXTURE')
        self.assertEqual(finding['evidence'], [dict(id='control-source', digest=digest('Evidence',
            next(e for e in data['evidence'] if e['id'] == 'control-source')))])

    def test_revocation_after_review_receipt_blocks_later_repair(self):
        data, gateway, _ = self.prepared()
        receipts = self.repair_receipts(gateway, data)
        gateway.revoke_grant('review-all', 'support_authorizer', 'Withdraw before commit')
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assert_open(gateway, 'c1', 'c2')
        self.assertEqual((gateway.snapshot()['revision'], gateway.snapshot()['value']), (1, '10'))

    def test_review_expiry_is_rechecked_at_commit_not_only_receipt_issuance(self):
        data = triage_fixture()
        next(g for g in data['grants'] if g['id'] == 'review-all')['expires_tick'] = 12
        data, gateway, _ = self.prepared(data)
        receipts = self.repair_receipts(gateway, data)
        self.assertEqual(gateway.snapshot()['tick'], 11)
        self.denied(gateway, lambda: gateway.commit(data['repair'], receipts, 'repair', 'executor', 'repair'))
        self.assert_open(gateway, 'c1', 'c2')
        self.assertEqual(gateway.snapshot()['used_mandates'], ['initial'])

    def test_ordinary_budget_exhaustion_and_duplicate_spam_cannot_block_known_complaint_intake(self):
        data = triage_fixture(('c1', 'duplicate', 'c2'), ordinary=4)
        gateway = self.gateway(data)
        initial = self.initial(gateway, data)
        self.assertEqual(gateway.snapshot()['budgets']['ordinary'], dict(limit=4, used=4))
        self.lodge(gateway, data, initial, ['c1', 'duplicate'])
        before_other = deepcopy(gateway.snapshot()['budgets']['review:c2'])
        for _ in range(20):
            self.denied(gateway, lambda: self.lodge(gateway, data, initial, ['duplicate']))
        self.lodge(gateway, data, initial, ['c2'])
        self.assert_open(gateway, 'c1', 'duplicate', 'c2')
        self.assertEqual(gateway.snapshot()['budgets']['review:c2'], before_other)
        self.assertEqual(gateway.snapshot()['budgets']['ordinary'], dict(limit=4, used=4))
        gateway.review(['c1', 'c2', 'duplicate'], data['repair'], 'reviewer', 'review-all')
        self.assertEqual(gateway.snapshot()['budgets']['review:c2']['used'], 1)

    def test_duplicate_retries_cannot_consume_reserved_appeal_intake(self):
        data = triage_fixture(('c1', 'duplicate', 'c2'), ordinary=4)
        gateway = self.gateway(data)
        initial = self.initial(gateway, data)
        self.lodge(gateway, data, initial)
        for _ in range(20):
            self.denied(gateway, lambda: self.lodge(gateway, data, initial, ['duplicate']))
        gateway.appeal('duplicate', 'outsider', ['source-appeal'], 'Independently retained appeal')
        self.assertEqual(gateway.snapshot()['complaints']['duplicate']['version'], 1)
        self.assertEqual(len(gateway.snapshot()['complaints']['duplicate']['appeals']), 1)
        self.assert_open(gateway, 'c1', 'duplicate', 'c2')

    def test_protected_funds_do_not_manufacture_missing_authorization(self):
        data = triage_fixture()
        data['grants'] = []
        gateway = self.gateway(data)
        effect = self.initial(gateway, data, audit=False)
        self.assertGreater(gateway.snapshot()['budgets']['audit:initial']['limit'], 0)
        made_after_construction = make_grant('late-audit', 'AUDIT', 'auditor', 'support_authorizer',
            data['policy'], data['triage_config'], work_item_id='initial', expected_revision=1)
        self.denied(gateway, lambda: gateway.audit(effect, 'auditor', made_after_construction['id']))
        self.assertEqual(gateway.snapshot()['pending_audit'], effect['id'])
        self.assertEqual(gateway.snapshot()['used_grants'], [])

    def test_known_intake_reservations_are_finite_and_count_toward_total_cap(self):
        data = triage_fixture(('c1', 'duplicate', 'c2'))
        gateway = self.gateway(data)
        budgets = gateway.snapshot()['budgets']
        for identifier in ('c1', 'duplicate', 'c2', 'late'):
            self.assertEqual(budgets['intake:' + identifier], dict(limit=2, used=0))
        self.assertLessEqual(sum(pool['limit'] for pool in budgets.values()), data['policy']['operation_budget'])
        old_without_intake = sum(pool['limit'] for key, pool in budgets.items() if not key.startswith('intake:'))
        data['triage_config']['ordinary_budget'] += data['policy']['operation_budget'] - old_without_intake
        with self.assertRaisesRegex(RunnerError, 'budgets exceed'):
            self.gateway(data)

    def test_malformed_appeal_demand_cannot_consume_valid_pinned_appeal_slot(self):
        data = triage_fixture(ordinary=4)
        gateway = self.gateway(data)
        effect = self.initial(gateway, data)
        self.lodge(gateway, data, effect)
        before = deepcopy(gateway.snapshot()['budgets']['intake:c2'])
        for _ in range(20):
            self.denied(gateway, lambda: gateway.appeal('c2', 'outsider', ['source-v2'], 'Unpinned repeated request'))
        self.assertEqual(gateway.snapshot()['budgets']['intake:c2'], before)
        gateway.appeal('c2', 'outsider', ['source-appeal'], 'Independently retained appeal')
        self.assertEqual(gateway.snapshot()['complaints']['c2']['version'], 1)
        self.assertEqual(gateway.snapshot()['budgets']['intake:c2'], dict(limit=2, used=2))


if __name__ == '__main__':
    unittest.main()
