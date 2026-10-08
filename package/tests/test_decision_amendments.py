"""Integration checks for supplied protected commitments and decision receipts."""
import copy
import unittest

from test_amendments import fixture
from wac_offline.amendments import AmendmentReplay, AmendmentError, SCHEMA, digest
from wac_offline.decision_records import DECISION_RECORD_SCHEMA, PROTECTED_LIMITS_SCHEMA


class DecisionAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.proposal, self.approval, self.procedure = fixture()
        self.replay = AmendmentReplay(self.policy)

    def rebind(self):
        self.proposal['new_policy_digest'] = digest('Policy', self.proposal['new_policy'])
        self.approval['proposal_digest'] = self.procedure['proposal_digest'] = digest('Proposal', self.proposal)

    def register(self):
        return self.replay.register(self.proposal, self.approval, self.procedure, 'registrar', 20)

    def test_schema_contracts_match_runtime(self):
        self.assertEqual(SCHEMA['$defs']['Policy']['properties']['protected_limits'], PROTECTED_LIMITS_SCHEMA)
        self.assertEqual(SCHEMA['$defs']['Approval']['properties']['decision_record'], {'$ref': '#/$defs/DecisionRecord'})
        self.assertEqual(SCHEMA['$defs']['DecisionRecord'], DECISION_RECORD_SCHEMA)

    def test_no_record_and_no_inventory_rejected(self):
        del self.approval['decision_record']
        with self.assertRaises(AmendmentError): self.register()
        del self.policy['protected_limits']
        with self.assertRaises(AmendmentError): AmendmentReplay(self.policy)

    def test_every_required_receipt_field_enforced(self):
        original = copy.deepcopy(self.approval['decision_record'])
        for field in original:
            self.approval['decision_record'] = copy.deepcopy(original)
            del self.approval['decision_record'][field]
            with self.subTest(field=field):
                with self.assertRaises(AmendmentError): self.register()
        self.assertEqual(self.replay.events(), [])

    def test_fail_or_unknown_not_authorized_by_unanimous_approval(self):
        for status in ('FAIL', 'UNKNOWN'):
            self.approval['decision_record']['protected_limit_assessments'][0]['status'] = status
            with self.assertRaises(AmendmentError): self.register()
        self.assertEqual(self.replay.state()['epoch'], 1)

    def test_cannot_rewrite_or_rename_supplied_protected_limit(self):
        for field, value in (('commitment', 'Abolish independent review.'), ('id', 'new-limit')):
            self.proposal['new_policy'] = copy.deepcopy(self.policy)
            self.proposal['new_policy']['protected_limits'][0][field] = value
            self.rebind()
            with self.subTest(field=field):
                with self.assertRaises(AmendmentError): self.register()

    def test_cannot_add_limit_in_ordinary_amendment(self):
        self.proposal['new_policy']['protected_limits'].append({'id': 'new', 'commitment': 'New commitment.'})
        self.rebind()
        with self.assertRaises(AmendmentError): self.register()

    def test_approval_cannot_substitute_its_own_inventory(self):
        self.approval['decision_record']['protected_limit_assessments'][0]['limit_id'] = 'unrelated'
        with self.assertRaises(AmendmentError): self.register()

    def test_opaque_content_still_needs_external_substantive_review(self):
        # Deliberate boundary witness: structure cannot understand contradiction.
        self.proposal['new_policy']['content'] = 'Abolish independent review.'
        self.rebind()
        cert = self.register()
        out = self.replay.activate(cert, 30)
        self.assertEqual(out['authority'], 'NONE')
        self.assertIs(out['execution_enabled'], False)


if __name__ == '__main__':
    unittest.main()
