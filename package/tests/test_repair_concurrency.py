"""Independent race and caller-mutation regressions for bounded repair."""
from concurrent.futures import ThreadPoolExecutor
import unittest

from test_registrar_repair import repair_case
from wac_offline.amendments import AmendmentError


def reviewed_case():
    model, submission, original, source, complaint, proposal, approval, procedure, grant = repair_case()
    args = dict(complaint=complaint, proposal=proposal, approval=approval,
                procedure=procedure, grant=grant, reviewer='appeal',
                replacement_authorizer='replacement', replacement_registrar='substitute',
                reason='Independent supplied review', evidence_refs=['review'], now=42)
    return model, args


class RepairConcurrencyTests(unittest.TestCase):
    def test_one_reservation_and_activation_under_competing_calls(self):
        model, args = reviewed_case()
        review = model.review_repair(**args)

        def register(_):
            try:
                return model.register_replacement(review, 42)
            except AmendmentError:
                return None

        with ThreadPoolExecutor(max_workers=8) as workers:
            certificates = [value for value in workers.map(register, range(8)) if value]
        self.assertEqual(len(certificates), 1)

        def activate(_):
            try:
                return model.activate(certificates[0], 45)
            except AmendmentError:
                return None

        with ThreadPoolExecutor(max_workers=8) as workers:
            receipts = [value for value in workers.map(activate, range(8)) if value]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(model.state()['epoch'], 2)
        self.assertEqual(sum(e['kind'] == 'resource_reservation' for e in model.events()), 1)
        self.assertEqual(sum(e['kind'] == 'activation' for e in model.events()), 1)

    def test_caller_edits_cannot_change_stored_repair(self):
        model, args = reviewed_case()
        expected = args['proposal']['new_policy_digest']
        review = model.review_repair(**args)
        args['proposal']['new_policy']['content'] = 'Caller changes reviewed proposal'
        args['approval']['decisionmakers'].clear()
        args['procedure']['mandatory_checks_passed'] = False
        args['grant']['remedy_authorized'] = False
        model.events()[-1]['record']['expires_at'] = 0
        certificate = model.register_replacement(review, 42)
        receipt = model.activate(certificate, 45)
        self.assertEqual(receipt['new_policy_digest'], expected)
        self.assertEqual(receipt['authority'], 'NONE')
        self.assertIs(receipt['execution_enabled'], False)


if __name__ == '__main__':
    unittest.main()
