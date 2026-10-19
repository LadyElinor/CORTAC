"""Exposed structural controls; no empirical or institutional acceptance claim."""
from copy import deepcopy
import unittest
from wac_offline.ops_fixtures_v2 import fixture, bind
from wac_offline.ops_trace_v2 import inspect_trace, TraceError, digest, STAGES
from wac_offline.ops_trace_v1 import inspect_trace as inspect_v1, TraceError as V1Error
from wac_offline.ops_fixtures_v1 import fixture as fixture_v1


class RemedyV2Tests(unittest.TestCase):
    def setUp(self):
        self.t, self.c = fixture()

    def inspect(self):
        bind(self.t, self.c)
        return inspect_trace(self.t, self.c)

    def reject(self):
        with self.assertRaises(TraceError):
            self.inspect()

    def test_transition_matrix_against_contract(self):
        # Expected edges are independently listed from the published contract,
        # never imported from the implementation transition table.
        prefixes = {'START': [], 'REFUSED': ['ORDERED', 'REFUSED']}
        prefixes.update({stage: list(STAGES[:i+1]) for i, stage in enumerate(STAGES)})
        allowed = {
            'START': ('ORDERED',),
            'ORDERED': ('ACCEPTED', 'REFUSED', 'ATTEMPTED'),
            'ACCEPTED': ('ATTEMPTED', 'REFUSED'),
            'REFUSED': ('ACCEPTED', 'ATTEMPTED'),
            'ATTEMPTED': ('ATTEMPTED', 'OBSERVED', 'REFUSED'),
            'OBSERVED': ('OBSERVED', 'AUDITED', 'ATTEMPTED'),
            'AUDITED': ('AUDITED', 'OBSERVED', 'ATTEMPTED', 'EFFECTIVENESS_REPORTED'),
            'EFFECTIVENESS_REPORTED': ('ATTEMPTED', 'OBSERVED', 'AUDITED'),
        }
        for state, prefix in prefixes.items():
            for following in (*STAGES, 'REFUSED'):
                with self.subTest(state=state, following=following):
                    self.t, self.c = fixture(prefix + [following])
                    self.t['remedy']['mode'] = 'COMPULSORY_REPORTED'
                    if following in allowed[state]:
                        self.inspect()
                    else:
                        self.reject()

    def test_conflict_survives_new_observation_and_positive_audit(self):
        self.t, self.c = fixture(list(STAGES[:5]) + ['OBSERVED', 'AUDITED', 'EFFECTIVENESS_REPORTED'])
        self.t['remedy']['events'][4]['outcome'] = 'CONTESTED'
        self.assertIn('AUDIT_REPAIR_NOT_ESTABLISHED', self.inspect()['blockers'])

    def test_renamed_duplicate_evidence_rejected(self):
        self.t, self.c = fixture(list(STAGES[:4]) + ['OBSERVED', 'AUDITED', 'EFFECTIVENESS_REPORTED'])
        old = next(e for e in self.c['evidence'] if e['id'] == 'evidence-3')
        new = next(e for e in self.c['evidence'] if e['id'] == 'evidence-4')
        new['digest'] = old['digest']
        self.t['remedy']['events'][4]['evidence_refs'][0]['digest'] = old['digest']
        self.reject()

    def test_fabrication_never_promoted(self):
        r = self.inspect()
        self.assertEqual(r['status'], 'SUPPLIED_TRACE_CONSISTENT')
        self.assertEqual(r['authority'], 'NONE')
        self.assertFalse(r['execution_enabled'])
        for key in ('factual_truth', 'actual_independence', 'remedy_effectiveness', 'operational_conformance'):
            self.assertEqual(r[key], 'NOT_ESTABLISHED')
        self.assertEqual(r['evidence_status'], 'REFERENCES_ONLY')

    def test_resolution_cannot_predate_objection_evidence(self):
        next(e for e in self.c['evidence'] if e['id'] == 'counter')['observed_at'] = 9
        self.t['findings'][0]['resolutions'][0]['evidence_ids'] = ['reason']
        with self.assertRaisesRegex(TraceError, 'evidence postdates use'):
            self.inspect()

    def test_resolution_at_objection_evidence_tick_is_consistent(self):
        next(e for e in self.c['evidence'] if e['id'] == 'counter')['observed_at'] = 8
        self.t['findings'][0]['resolutions'][0]['evidence_ids'] = ['reason']
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_unresolved_status_can_predate_later_objection_evidence(self):
        next(e for e in self.c['evidence'] if e['id'] == 'counter')['observed_at'] = 9
        self.t['findings'][0]['resolutions'][0].update(state='UNRESOLVED', evidence_ids=['reason'])
        self.assertIn('MATERIAL_OBJECTION_UNRESOLVED', self.inspect()['blockers'])

    def test_v1_unchanged_and_versions_not_interchangeable(self):
        t, c = fixture_v1()
        self.assertEqual(inspect_v1(t, c)['status'], 'SUPPLIED_TRACE_CONSISTENT')
        with self.assertRaises(V1Error):
            inspect_v1(self.t, self.c)
        with self.assertRaises(TraceError):
            inspect_trace(t, c)

    def test_no_mutation_and_deterministic(self):
        before = deepcopy((self.t, self.c))
        r = inspect_trace(self.t, self.c)
        self.assertEqual(r, inspect_trace(self.t, self.c))
        self.assertEqual(before, (self.t, self.c))
        self.assertEqual(r['trace_digest'], digest(self.t))
        self.assertEqual(r['context_digest'], digest(self.c))

    def test_repeated_attempts_observations_audits(self):
        stages = list(STAGES[:5]) + ['ATTEMPTED', 'OBSERVED', 'OBSERVED', 'AUDITED', 'AUDITED', 'EFFECTIVENESS_REPORTED']
        self.t, self.c = fixture(stages)
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_failed_audited_attempt_followed_by_retry(self):
        self.t, self.c = fixture(list(STAGES[:5]) + list(STAGES[2:]))
        self.t['remedy']['events'][4]['outcome'] = 'INCOMPLETE_REPORTED'
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')
        self.assertEqual(self.t['remedy']['events'][4]['outcome'], 'INCOMPLETE_REPORTED')

    def test_new_observation_requires_new_audit(self):
        self.t, self.c = fixture(list(STAGES) + ['OBSERVED'])
        r = self.inspect()
        self.assertIn('REMEDY_DELIVERY_TRACE_INCOMPLETE', r['blockers'])
        self.assertIn('RESIDUAL_INJURY_NOT_REPAIRED', r['blockers'])

    def test_old_audit_cannot_cover_new_observation(self):
        self.t, self.c = fixture(list(STAGES) + ['OBSERVED'])
        self.t['remedy']['residuals'][0].update(state='REPAIRED_REPORTED', audit_ids=['event-4'])
        self.reject()

    def test_old_attempt_cannot_close_current_injury(self):
        self.t, self.c = fixture(list(STAGES) + list(STAGES[2:]))
        self.t['remedy']['residuals'][0]['observation_ids'] = ['event-3']
        self.reject()

    def test_unaudited_retry_keeps_incomplete_history(self):
        self.t, self.c = fixture(list(STAGES[:3]) + list(STAGES[2:]))
        self.assertIn('PRIOR_ATTEMPT_TRACE_INCOMPLETE', self.inspect()['blockers'])

    def test_compulsory_without_fabricated_acceptance(self):
        self.t, self.c = fixture(['ORDERED', *STAGES[2:]])
        self.t['remedy']['mode'] = 'COMPULSORY_REPORTED'
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_voluntary_without_acceptance_rejected(self):
        self.t, self.c = fixture(['ORDERED', *STAGES[2:]])
        self.reject()

    def test_refusal_not_completion(self):
        self.t, self.c = fixture(['ORDERED', 'REFUSED'])
        r = self.inspect()
        self.assertIn('REMEDY_REFUSED_ESCALATION_REQUIRED', r['blockers'])
        self.assertEqual(r['remedy_effectiveness'], 'NOT_ESTABLISHED')

    def test_refusal_then_acceptance(self):
        self.t, self.c = fixture(['ORDERED', 'REFUSED', *STAGES[1:]])
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_compulsory_after_refusal(self):
        self.t, self.c = fixture(['ORDERED', 'REFUSED', *STAGES[2:]])
        self.t['remedy']['mode'] = 'COMPULSORY_REPORTED'
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_all_prefixes_incomplete(self):
        for count in range(6):
            self.t, self.c = fixture(STAGES[:count])
            with self.subTest(count=count):
                r = self.inspect()
                self.assertEqual(r['status'], 'SUPPLIED_TRACE_INCOMPLETE')
                self.assertEqual(r['factual_truth'], 'NOT_ESTABLISHED')

    def test_reassessment_refreshes_expiry_without_rewriting_findings(self):
        a = deepcopy(self.t['reassessments'][0])
        self.t['reassessments'][0]['reassess_at'] = 14
        a.update(id='assessment-2', previous_id='assessment-1', checked_at=14)
        self.t['reassessments'].append(a)
        self.t['remedy']['events'][4]['assessment_ref'] = 'assessment-2'
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_cannot_select_older_assessment(self):
        a = deepcopy(self.t['reassessments'][0])
        a.update(id='assessment-2', previous_id='assessment-1', checked_at=14)
        self.t['reassessments'].append(a)
        self.reject()

    def test_current_declared_conflict_remains_blocker(self):
        self.c['dependencies'][0]['status'] = 'CONFLICT'
        self.assertIn('DEPENDENCY_NOT_CURRENT', self.inspect()['blockers'])

    def test_changed_dependency_does_not_retroactively_validate_finding(self):
        self.c['dependencies'][0]['changed_at'] = 3
        self.assertIn('DEPENDENCY_CHANGED_AFTER_ASSESSMENT', self.inspect()['blockers'])

    def test_residual_unresolved_after_all_stages(self):
        self.t['remedy']['residuals'][0]['state'] = 'UNRESOLVED'
        self.assertIn('RESIDUAL_INJURY_NOT_REPAIRED', self.inspect()['blockers'])

    def test_partial_injury_repair_does_not_close_case(self):
        self.c['injuries'].append(dict(id='new-injury', version=2))
        self.t['remedy']['residuals'].append(dict(id='new-injury', version=2, state='CONTESTED', observation_ids=[], audit_ids=[], reason='Still disputed'))
        self.assertIn('RESIDUAL_INJURY_NOT_REPAIRED', self.inspect()['blockers'])

    def test_conflicting_audits_not_overwritten(self):
        self.t, self.c = fixture(list(STAGES[:5]) + ['AUDITED', 'EFFECTIVENESS_REPORTED'])
        self.t['remedy']['events'][4]['outcome'] = 'CONTESTED'
        self.t['remedy']['residuals'][0].update(state='CONTESTED')
        self.assertIn('AUDIT_REPAIR_NOT_ESTABLISHED', self.inspect()['blockers'])

    def test_contradictory_repair_claim_rejected(self):
        self.t['remedy']['events'][4]['outcome'] = 'INCOMPLETE_REPORTED'
        self.reject()

    def test_overdue_incomplete_remedy(self):
        self.t, self.c = fixture(STAGES[:3])
        self.c['now'] = 95
        r = self.inspect()
        self.assertIn('REMEDY_OVERDUE_ESCALATION_REQUIRED', r['blockers'])
        self.assertIn('ESCALATION_DUE', r['blockers'])

    def test_chain_tamper_without_rehash(self):
        self.t['remedy']['events'][2]['reason'] = 'Changed'
        with self.assertRaises(TraceError):
            inspect_trace(self.t, self.c)

    def test_coordinated_rewrite_not_authenticated(self):
        self.t['findings'][0]['reason'] = 'Fabricated irrelevant text'
        self.assertEqual(self.inspect()['factual_truth'], 'NOT_ESTABLISHED')

    def test_omission_from_both_inventories_not_discovered(self):
        self.c['injuries'].clear()
        self.t['remedy']['residuals'].clear()
        self.assertEqual(self.inspect()['inventory_scope'], 'SUPPLIED_INVENTORY_ONLY')

    def test_future_context_not_rebound(self):
        self.c['now'] += 1
        with self.assertRaises(TraceError):
            inspect_trace(self.t, self.c)


def reject_case(name, mutation):
    def test(self):
        mutation(self.t, self.c)
        self.reject()
    setattr(RemedyV2Tests, 'test_reject_' + name, test)


for name, mutation in {
    'unknown_effect_flag': lambda t,c: t.update(execution_enabled=True),
    'bool_tick': lambda t,c: c.update(now=True),
    'duplicate_event_id': lambda t,c: t['remedy']['events'][1].update(id='event-0'),
    'duplicate_evidence': lambda t,c: c['evidence'].append(dict(c['evidence'][0], digest='f'*64)),
    'duplicate_assessment': lambda t,c: t['reassessments'].append(dict(t['reassessments'][0], challenge_route='different')),
    'duplicate_authorization': lambda t,c: c['authorizations'].append(dict(c['authorizations'][0], end=101)),
    'missing_authorization': lambda t,c: t['remedy']['events'][2].update(authorization_ref='absent'),
    'wrong_authorization_actor': lambda t,c: c['authorizations'][0].update(actor='party'),
    'wrong_authorization_scope': lambda t,c: c['authorizations'][0].update(remedy_version=2),
    'wrong_authorization_action': lambda t,c: c['authorizations'][0].update(stages=['ORDERED']),
    'empty_authorization_window': lambda t,c: c['authorizations'][0].update(end=10),
    'unknown_issuer': lambda t,c: c['authorizations'][0].update(issuer='absent'),
    'stale_evidence_version': lambda t,c: t['remedy']['events'][2]['evidence_refs'][0].update(version=2),
    'stale_evidence_digest': lambda t,c: t['remedy']['events'][2]['evidence_refs'][0].update(digest='f'*64),
    'wrong_evidence_kind': lambda t,c: next(e for e in c['evidence'] if e['id']=='evidence-2').update(kind='OBSERVED'),
    'future_evidence': lambda t,c: next(e for e in c['evidence'] if e['id']=='evidence-2').update(observed_at=14),
    'predating_evidence': lambda t,c: next(e for e in c['evidence'] if e['id']=='evidence-2').update(observed_at=1),
    'regressing_time': lambda t,c: t['remedy']['events'][2].update(at=1),
    'forward_target': lambda t,c: t['remedy']['events'][3].update(targets=['event-5']),
    'wrong_attempt_target': lambda t,c: t['remedy']['events'][3].update(targets=['event-1']),
    'missing_audit_coverage': lambda t,c: t['remedy']['events'][4].update(targets=[]),
    'wrong_report_target': lambda t,c: t['remedy']['events'][5].update(targets=['event-3']),
    'missing_assessment': lambda t,c: t['remedy']['events'][4].update(assessment_ref='absent'),
    'expired_audit_assessment': lambda t,c: t['reassessments'][0].update(reassess_at=15),
    'late_audit_assessment': lambda t,c: t['reassessments'][0].update(checked_at=16),
    'broken_assessment_chain': lambda t,c: t['reassessments'][0].update(previous_id='missing'),
    'stale_dependency': lambda t,c: t['reassessments'][0]['dependencies'][0].update(version=2),
    'missing_dimension': lambda t,c: t['reassessments'][0]['dependencies'].pop(),
    'self_review_role': lambda t,c: t['reassessments'][0].update(verifier='owner'),
    'audit_self_authorized_effect': lambda t,c: t['remedy']['events'][4].update(actor='owner', authorization_ref='grant-owner'),
    'stale_injury': lambda t,c: c['injuries'][0].update(version=2),
    'missing_injury_disposition': lambda t,c: t['remedy']['residuals'].clear(),
    'old_account': lambda t,c: next(e for e in c['evidence'] if e['id']=='account').update(observed_at=1),
    'empty_account': lambda t,c: t['remedy']['affected_account'].update(evidence_ids=[]),
    'audit_without_outcome': lambda t,c: t['remedy']['events'][4].update(outcome='NOT_APPLICABLE'),
    'non_audit_claim': lambda t,c: t['remedy']['events'][3].update(outcome='REPAIR_REPORTED'),
    'missing_transition_reason': lambda t,c: t['remedy']['events'][2].update(reason=' '),
}.items():
    reject_case(name, mutation)


def blocker_case(name, mutation, blocker):
    def test(self):
        mutation(self.t, self.c)
        r = self.inspect()
        self.assertIn(blocker, r['blockers'])
        self.assertEqual(r['status'], 'SUPPLIED_TRACE_INCOMPLETE')
        self.assertEqual(r['factual_truth'], 'NOT_ESTABLISHED')
        self.assertEqual(r['authority'], 'NONE')
    setattr(RemedyV2Tests, 'test_block_' + name, test)


for name, mutation, blocker in [
    ('revoked', lambda t,c: c['authorizations'][0].update(state='REVOKED_REPORTED'), 'AUTHORIZATION_NOT_CURRENT'),
    ('expired', lambda t,c: c['authorizations'][0].update(end=12), 'AUTHORIZATION_NOT_CURRENT'),
    ('future_grant', lambda t,c: c['authorizations'][0].update(start=12), 'AUTHORIZATION_NOT_CURRENT'),
    ('party_control', lambda t,c: c['principals'][2].update(controller='controller-party'), 'DECLARED_CONTROL_CONFLICT'),
    ('owner_control', lambda t,c: c['principals'][2].update(controller='controller-owner'), 'REMEDY_AUDIT_CONTROL_CONFLICT'),
    ('unknown_owner_control', lambda t,c: c['principals'][3].update(controller=None), 'REMEDY_AUDIT_INDEPENDENCE_UNKNOWN'),
    ('unknown_reviewer_control', lambda t,c: c['principals'][1].update(controller=None), 'INDEPENDENCE_UNKNOWN'),
    ('expired_latest_assessment', lambda t,c: t['reassessments'][0].update(reassess_at=60), 'INDEPENDENCE_REASSESSMENT_DUE'),
    ('unresolved_objection', lambda t,c: t['findings'][0]['resolutions'][0].update(state='UNRESOLVED'), 'MATERIAL_OBJECTION_UNRESOLVED'),
    ('waiver_not_repair', lambda t,c: t['remedy']['residuals'][0].update(state='WAIVED_REPORTED'), 'RESIDUAL_INJURY_NOT_REPAIRED'),
    ('unsafe_account', lambda t,c: t['remedy']['affected_account'].update(status='UNSAFE', evidence_ids=[]), 'AFFECTED_ACCOUNT_EXCEPTION_REQUIRES_REVIEW'),
]:
    blocker_case(name, mutation, blocker)


if __name__ == '__main__':
    unittest.main()
