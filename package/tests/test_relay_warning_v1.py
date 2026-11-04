"""Exposed synthetic controls, not observations of institutional performance."""
import copy
import unittest
from wac_offline.relay_warning_v1 import SCHEMA, WarningError, inspect_warning


def fixture():
    return dict(schema=SCHEMA, case_id='synthetic-warning', decision_digest='0'*64,
        predecessor_digest='1'*64,
        warning=dict(original_digest='2'*64, dissent_digests=['3'*64], recipient='synthetic-recipient',
            delivery='RECEIVED_REPORTED', delivery_evidence=['4'*64],
            response='RESPONSE_REPORTED', response_evidence=['5'*64]),
        combined_review=dict(reviewer='synthetic-reviewer', controller='review-controller',
            decision_controller='decision-controller', access_evidence=['6'*64],
            review_evidence=['7'*64], scope='Synthetic combined transaction, both departments',
            limitations='Declarations and exposed fixtures only'),
        protection=dict(state='PROPOSAL_RECORDED', rationale_evidence=['8'*64],
            authority_evidence=['9'*64], appeal_evidence=['a'*64]),
        attribution=dict(state='UNASSESSED', subject=None, act_evidence=[], knowledge_evidence=[],
            authority_evidence=[], intent_evidence=[], response_opportunity_evidence=[]),
        repair=dict(state='REPAIR_REPORTED', owner_controller='owner', verifier_controller='verifier',
            recipient_evidence=['b'*64], observation_evidence=['c'*64], verification_evidence=['d'*64],
            independence_evidence=['e'*64], residual_injury='Unknown outside synthetic scope'))


class WarningTests(unittest.TestCase):
    def test_all_records_still_require_review(self):
        report = inspect_warning(fixture())
        self.assertEqual(report['gaps'], [])
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')
        self.assertEqual(report['authority'], 'NONE')
        self.assertFalse(report['execution_enabled'])
        self.assertEqual(report['attribution'], 'NOT_DETERMINED')
        self.assertEqual(report['effectiveness'], 'NOT_VERIFIED')
        self.assertEqual(report['controller_closure'], 'SUPPLIED_UNVERIFIED')

    def test_protection_does_not_depend_on_intent(self):
        record = fixture()
        before = inspect_warning(record)
        record['attribution']['state'] = 'REVIEW_RECORDED'
        after = inspect_warning(record)
        self.assertEqual(before['gaps'], after['gaps'])
        self.assertIn('intent_evidence', after['attribution_gaps'])
        self.assertIn('response_opportunity_evidence', after['attribution_gaps'])

    def test_non_delivery_and_received_without_response_are_distinct(self):
        record = fixture()
        record['warning'].update(delivery='NOT_DELIVERED', response='UNKNOWN')
        self.assertIn('WARNING_NOT_DELIVERED', inspect_warning(record)['gaps'])
        record['warning'].update(delivery='RECEIVED_REPORTED', response='NO_RESPONSE_REPORTED')
        gaps = inspect_warning(record)['gaps']
        self.assertIn('WARNING_NO_RESPONSE_REPORTED', gaps)
        self.assertNotIn('WARNING_NOT_DELIVERED', gaps)

    def test_received_is_not_response_or_verified_reading(self):
        record = fixture()
        record['warning']['response_evidence'] = []
        self.assertIn('RESPONSE_EVIDENCE_MISSING', inspect_warning(record)['gaps'])
        record['warning']['delivery_evidence'] = []
        self.assertIn('RECEIPT_EVIDENCE_MISSING', inspect_warning(record)['gaps'])

    def test_inconsistent_warning_flow_is_visible(self):
        record = fixture()
        record['warning']['delivery'] = 'UNKNOWN'
        self.assertIn('RESPONSE_WITHOUT_RECORDED_RECEIPT', inspect_warning(record)['gaps'])

    def test_cross_compartment_review_needs_actual_access_evidence(self):
        record = fixture()
        record['combined_review']['access_evidence'] = []
        self.assertIn('COMBINED_ACCESS_EVIDENCE_MISSING', inspect_warning(record)['gaps'])
        record['combined_review']['controller'] = record['combined_review']['decision_controller']
        self.assertIn('COMBINED_REVIEW_CONTROL_CONFLICT', inspect_warning(record)['gaps'])

    def test_protection_needs_separate_authority_and_appeal(self):
        for key in ('rationale_evidence', 'authority_evidence', 'appeal_evidence'):
            with self.subTest(key=key):
                record = fixture()
                record['protection'][key] = []
                self.assertIn('PROTECTION_' + key.upper() + '_MISSING', inspect_warning(record)['gaps'])

    def test_repair_is_not_order_acceptance_or_another_signature(self):
        for key in ('recipient_evidence', 'observation_evidence', 'verification_evidence', 'independence_evidence'):
            with self.subTest(key=key):
                record = fixture()
                record['repair'][key] = []
                self.assertIn('REPAIR_' + key.upper() + '_MISSING', inspect_warning(record)['gaps'])

    def test_unknown_and_self_verifiers_cannot_disappear(self):
        record = fixture()
        record['repair']['verifier_controller'] = None
        self.assertIn('REPAIR_VERIFIER_CONTROLLER_MISSING', inspect_warning(record)['gaps'])
        record['repair']['verifier_controller'] = 'owner'
        self.assertIn('REPAIR_SELF_VERIFICATION', inspect_warning(record)['gaps'])

    def test_original_decision_controller_cannot_verify_repair(self):
        record = fixture()
        record['repair']['verifier_controller'] = record['combined_review']['decision_controller']
        self.assertIn('REPAIR_ORIGINAL_DECISION_CONTROL_CONFLICT', inspect_warning(record)['gaps'])

    def test_observation_is_not_independent_verification(self):
        record = fixture()
        record['repair']['verification_evidence'] = record['repair']['observation_evidence'][:]
        self.assertIn('REPAIR_VERIFICATION_REUSES_OBSERVATION', inspect_warning(record)['gaps'])

    def test_original_dissent_exoneration_and_predecessor_are_bound(self):
        record = fixture()
        original = inspect_warning(record)['record_digest']
        for field in ('original_digest', 'dissent_digests'):
            revised = copy.deepcopy(record)
            revised['warning'][field] = 'f'*64 if field == 'original_digest' else []
            self.assertNotEqual(original, inspect_warning(revised)['record_digest'])
        record['predecessor_digest'] = 'f'*64
        self.assertNotEqual(original, inspect_warning(record)['record_digest'])
        # No claim text or direction of correction is interpreted as guilt.
        record['repair']['residual_injury'] = 'Exonerating correction remains necessary'
        self.assertEqual(inspect_warning(record)['attribution'], 'NOT_DETERMINED')

    def test_closed_schema_and_bounded_types(self):
        mutations = [lambda r: r.update(authority='GRANTED'),
            lambda r: r.update(schema='cortac.relay.warning.v2'),
            lambda r: r.update(case_id=True),
            lambda r: r.update(decision_digest='x'*64),
            lambda r: r['warning'].update(dissent_digests=['a'*64]*129),
            lambda r: r['warning'].update(dissent_digests=['a'*64]*2),
            lambda r: r['combined_review'].update(scope=' '*2),
            lambda r: r['combined_review'].update(scope='x'*4001)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                record = fixture()
                mutate(record)
                with self.assertRaises(WarningError):
                    inspect_warning(record)

    def test_no_mutation_deterministic_and_canonical(self):
        record = fixture()
        before = copy.deepcopy(record)
        report = inspect_warning(record)
        self.assertEqual(record, before)
        self.assertEqual(report, inspect_warning(dict(reversed(list(record.items())))))


if __name__ == '__main__':
    unittest.main()
