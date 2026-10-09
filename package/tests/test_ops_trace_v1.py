"""Synthetic relation checks, deliberately not truth/independence/effectiveness tests."""
from copy import deepcopy
import unittest
from wac_offline.ops_trace_v1 import TraceError, digest, inspect_trace
from wac_offline.ops_fixtures_v1 import controls, fixture, integration_report


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.t, self.c = fixture()

    def inspect(self):
        self.t['context_digest'] = digest(self.c)
        self.t['remedy']['findings_digest'] = digest(self.t['findings'])
        return inspect_trace(self.t, self.c)

    def reject(self):
        with self.assertRaises(TraceError):
            self.inspect()

    def test_no_mutation(self):
        before = deepcopy((self.t, self.c))
        inspect_trace(self.t, self.c)
        self.assertEqual(before, (self.t, self.c))

    def test_deterministic(self):
        self.assertEqual(inspect_trace(self.t, self.c), inspect_trace(self.t, self.c))

    def test_full_input_digests(self):
        report = self.inspect()
        self.assertEqual(report['trace_digest'], digest(self.t))
        self.assertEqual(report['context_digest'], digest(self.c))
        self.t['findings'][0]['reason'] = 'Another arbitrary text'
        self.assertNotEqual(report['trace_digest'], self.inspect()['trace_digest'])

    def test_no_truth_or_effect_claim(self):
        report = self.inspect()
        self.assertEqual(report['authority'], 'NONE')
        self.assertFalse(report['execution_enabled'])
        for key in ('factual_truth', 'actual_independence', 'remedy_effectiveness', 'operational_conformance'):
            self.assertEqual(report[key], 'NOT_ESTABLISHED')
        self.assertEqual(report['inventory_scope'], 'SUPPLIED_INVENTORY_ONLY')
        self.assertEqual(report['freshness'], 'CALLER_ANCHOR_ONLY')

    def test_changed_context_without_rebinding_rejected(self):
        self.c['now'] += 1
        with self.assertRaises(TraceError):
            inspect_trace(self.t, self.c)

    def test_deleting_objection_and_all_its_links_is_not_detected_as_truth(self):
        self.c['objections'].clear()
        self.c['evidence'] = [e for e in self.c['evidence'] if e['id'] != 'counter']
        self.t['findings'][0]['resolutions'].clear()
        self.t['findings'][0]['evidence_refs'] = [r for r in self.t['findings'][0]['evidence_refs'] if r['id'] != 'counter']
        report = self.inspect()
        self.assertEqual(report['status'], 'SUPPLIED_TRACE_CONSISTENT')
        self.assertEqual(report['inventory_scope'], 'SUPPLIED_INVENTORY_ONLY')

    def test_caller_can_reanchor_old_record_not_anti_rollback(self):
        self.t['binding']['version'] = self.c['expected']['version'] = 1
        self.assertEqual(self.inspect()['status'], 'SUPPLIED_TRACE_CONSISTENT')

    def test_nested_unknown_field(self):
        self.t['remedy']['events'][0]['approved'] = True
        self.reject()

    def test_bool_integer(self):
        self.c['now'] = True
        self.reject()

    def test_float_integer(self):
        self.c['now'] = 20.0
        self.reject()

    def test_integer_bound(self):
        self.c['now'] = 2**63
        self.reject()

    def test_blank_reason(self):
        self.t['findings'][0]['reason'] = ' '
        self.reject()

    def test_text_bound(self):
        self.t['findings'][0]['reason'] = 'x' * 8193
        self.reject()

    def test_duplicate_identity_changed_content(self):
        self.c['evidence'].append(dict(self.c['evidence'][0], digest='d' * 64))
        self.reject()

    def test_duplicate_list_item(self):
        self.c['parties'].append('party')
        self.reject()

    def test_oversized_inventory(self):
        self.c['parties'] = ['p' + str(i) for i in range(257)]
        self.reject()

    def test_evidence_digest_binding(self):
        self.c['evidence'][0]['digest'] = 'd' * 64
        self.reject()

    def test_evidence_version_binding(self):
        self.c['evidence'][0]['version'] += 1
        self.reject()

    def test_future_evidence(self):
        self.c['evidence'][0]['observed_at'] = 21
        self.reject()

    def test_resolution_cannot_use_later_evidence(self):
        self.c['evidence'][3]['observed_at'] = 9
        self.reject()

    def test_independence_before_finding(self):
        self.t['independence']['checked_at'] = 11
        self.reject()

    def test_no_verifier_self_audit_attempt(self):
        self.t['remedy']['events'][2]['actor'] = 'verifier'
        self.reject()

    def test_no_verifier_self_audit_observation(self):
        self.t['remedy']['events'][3]['actor'] = 'verifier'
        self.reject()

    def test_residual_observation_must_match_event(self):
        self.c['evidence'].append(dict(id='unrelated', version=1, digest='d' * 64, kind='OBSERVED', observed_at=1))
        self.t['remedy']['residuals'][0]['observation_ids'] = ['unrelated']
        self.reject()

    def test_residual_audit_must_match_event(self):
        self.c['evidence'].append(dict(id='unrelated', version=1, digest='d' * 64, kind='AUDITED', observed_at=1))
        self.t['remedy']['residuals'][0]['audit_ids'] = ['unrelated']
        self.reject()

    def test_no_remedy_events_no_completion(self):
        self.t['remedy']['events'].clear()
        self.t['remedy']['residuals'][0].update(state='UNRESOLVED', observation_ids=[], audit_ids=[])
        self.t['remedy']['affected_account'].update(status='UNAVAILABLE', evidence_ids=[])
        report = self.inspect()
        self.assertIn('REMEDY_DELIVERY_TRACE_INCOMPLETE', report['blockers'])

    def test_overdue_escalation(self):
        self.t['remedy']['residuals'][0]['state'] = 'REFERRED'
        self.t['remedy']['deadline'] = 20
        self.t['remedy']['escalation']['due_at'] = 20
        blockers = self.inspect()['blockers']
        self.assertIn('REMEDY_OVERDUE_ESCALATION_REQUIRED', blockers)
        self.assertIn('ESCALATION_DUE', blockers)

    def test_waiver_is_not_repair(self):
        self.t['remedy']['residuals'][0]['state'] = 'WAIVED_REPORTED'
        self.assertIn('RESIDUAL_INJURY_NOT_REPAIRED', self.inspect()['blockers'])

    def test_account_exception_not_invented_account(self):
        self.t['remedy']['affected_account'].update(status='UNSAFE', evidence_ids=[])
        self.assertIn('AFFECTED_ACCOUNT_EXCEPTION_REQUIRES_REVIEW', self.inspect()['blockers'])

    def test_unknown_principal(self):
        self.t['remedy']['owner'] = 'unknown'
        self.reject()

    def test_dependency_dimension_missing(self):
        self.c['dependencies'].pop()
        self.reject()

    def test_audit_owner_controller_overlap(self):
        self.c['principals'][3]['controller'] = 'controller-verifier'
        self.assertIn('REMEDY_AUDIT_CONTROL_CONFLICT', self.inspect()['blockers'])

    def test_audit_owner_controller_unknown(self):
        self.c['principals'][3]['controller'] = None
        self.assertIn('REMEDY_AUDIT_INDEPENDENCE_UNKNOWN', self.inspect()['blockers'])

    def test_observation_after_attempt(self):
        next(e for e in self.c['evidence'] if e['id'] == 'observed')['observed_at'] = 1
        self.reject()

    def test_audit_after_observation(self):
        next(e for e in self.c['evidence'] if e['id'] == 'audited')['observed_at'] = 13
        self.reject()

    def test_account_after_observation(self):
        next(e for e in self.c['evidence'] if e['id'] == 'account')['observed_at'] = 13
        self.reject()

    def test_finding_before_remedy(self):
        self.t['findings'][0]['decided_at'] = 18
        self.reject()

    def test_remedy_must_bind_current_finding_content(self):
        self.t['findings'][0]['reason'] = 'Changed decision'
        with self.assertRaises(TraceError):
            inspect_trace(self.t, self.c)

    def test_objection_bound_to_claim_version(self):
        self.c['claims'][0]['version'] = 2
        self.t['findings'][0]['claim_version'] = 2
        self.reject()

    def test_provenance_bound_to_original_version(self):
        self.c['evidence'][0]['version'] = 2
        self.t['findings'][0]['evidence_refs'][0]['version'] = 2
        self.reject()

    def test_integration_controls(self):
        self.assertTrue(integration_report()['all_fixed_structural_outcomes'])


def _control(case):
    def test(self):
        trace, context, expected = deepcopy(case)
        if expected == 'REJECTED':
            with self.assertRaises(TraceError):
                inspect_trace(trace, context)
        else:
            report = inspect_trace(trace, context)
            if expected.startswith('SUPPLIED_'):
                self.assertEqual(report['status'], expected)
            else:
                self.assertIn(expected, report['blockers'])
    return test


for _name, _case in controls().items():
    setattr(TraceTests, 'test_control_' + _name, _control(_case))

if __name__ == '__main__':
    unittest.main()
