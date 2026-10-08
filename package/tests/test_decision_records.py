"""Receipt structure and explicit assessment gates; no moral-truth oracle."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from wac_offline.decision_records import (
    validate_decision_record, validate_protected_limits, require_preserved_limits,
)
from wac_offline.governance import consequential_ballot
from wac_offline.io import InputError

ROOT = Path(__file__).resolve().parents[1]


def receipt():
    return json.loads((ROOT / 'fixtures' / 'decision_record.json').read_text(encoding='utf-8'))


def limits():
    return [{'id': 'independent-review', 'commitment': 'Preserve independent review.'}]


class DecisionRecordTests(unittest.TestCase):
    def test_complete_supplied_record(self):
        record = receipt()
        before = copy.deepcopy(record)
        self.assertTrue(validate_decision_record(record, limits()))
        self.assertEqual(record, before)

    def test_every_required_field_and_unknown_field(self):
        for field in receipt():
            with self.subTest(field=field):
                record = receipt()
                del record[field]
                with self.assertRaises(InputError): validate_decision_record(record)
        record = receipt()
        record['morality_score'] = 100
        with self.assertRaises(InputError): validate_decision_record(record)

    def test_blank_reasons_cannot_stand_for_evidence(self):
        for text in ('', ' ', '\n\t'):
            record = receipt()
            record['burden_justification'] = text
            with self.assertRaises(InputError): validate_decision_record(record)
            record = receipt()
            record['protected_limit_assessments'][0]['evidence_refs'] = [text]
            with self.assertRaises(InputError): validate_decision_record(record)

    def test_empty_or_untyped_material_fields_rejected(self):
        for field in ('affected_parties', 'alternatives', 'protected_limit_assessments',
                      'predictions', 'review_triggers', 'evidence_refs'):
            for value in ([], None, '', {}, True):
                with self.subTest(field=field, value=value):
                    record = receipt()
                    record[field] = value
                    with self.assertRaises(InputError): validate_decision_record(record)

    def test_nested_fields_required(self):
        for field in ('affected_parties', 'alternatives', 'protected_limit_assessments', 'review_triggers'):
            for key in receipt()[field][0]:
                record = receipt()
                del record[field][0][key]
                with self.subTest(field=field, key=key):
                    with self.assertRaises(InputError): validate_decision_record(record)
        for key in receipt()['remedy_plan']:
            record = receipt()
            del record['remedy_plan'][key]
            with self.assertRaises(InputError): validate_decision_record(record)

    def test_duplicate_identity_rejected_even_when_content_differs(self):
        for field in ('affected_parties', 'protected_limit_assessments'):
            record = receipt()
            second = copy.deepcopy(record[field][0])
            second['burdens' if field == 'affected_parties' else 'reasons'] += ' changed'
            record[field].append(second)
            with self.assertRaises(InputError): validate_decision_record(record)

    def test_assessment_inventory_is_exact(self):
        for applied in ([], [{'id': 'other', 'commitment': 'Other limit.'}],
                        limits() + [{'id': 'audit', 'commitment': 'Preserve audit.'}]):
            with self.assertRaises(InputError): validate_decision_record(receipt(), applied)

    def test_dissent_is_explicit_and_consistent(self):
        record = receipt()
        record['dissent'] = []
        with self.assertRaises(InputError): validate_decision_record(record)
        record['dissent_status'] = 'NONE_REPORTED'
        self.assertTrue(validate_decision_record(record))
        record['dissent'] = ['Objection']
        with self.assertRaises(InputError): validate_decision_record(record)

    def test_failed_or_unknown_assessment_cannot_be_outvoted(self):
        for status in ('FAIL', 'UNKNOWN'):
            record = receipt()
            record['protected_limit_assessments'][0]['status'] = status
            self.assertFalse(validate_decision_record(record, limits()))
            result = consequential_ballot(['a', 'b', 'c', 'd'], ['a', 'b', 'c', 'd'], False, record, limits())
            self.assertFalse(result['structurally_passes'])
            self.assertFalse(result['supplied_assessments_pass'])

    def test_ballot_requires_explicit_assessment_and_record(self):
        for kwargs in ({}, {'protected_failure': False}, {'decision_record': receipt()},
                       {'protected_failure': None, 'decision_record': receipt()},
                       {'protected_failure': False, 'decision_record': receipt()}):
            with self.assertRaises(InputError):
                consequential_ballot(['a', 'b', 'c', 'd'], ['a', 'b', 'c'], **kwargs)
        self.assertFalse(consequential_ballot(['a', 'b', 'c', 'd'], ['a', 'b', 'c'],
                                              True, receipt(), limits())['structurally_passes'])

    def test_ballot_cannot_drop_failed_assessment(self):
        record = receipt()
        applied = limits() + [{'id': 'audit', 'commitment': 'Preserve audit.'}]
        failed = copy.deepcopy(record['protected_limit_assessments'][0])
        failed.update(limit_id='audit', status='FAIL')
        record['protected_limit_assessments'].append(failed)
        self.assertFalse(consequential_ballot(['a', 'b', 'c', 'd'], ['a', 'b', 'c', 'd'],
                                              False, record, applied)['structurally_passes'])
        record['protected_limit_assessments'].pop()
        with self.assertRaises(InputError):
            consequential_ballot(['a', 'b', 'c', 'd'], ['a', 'b', 'c', 'd'],
                                 False, record, applied)
        with self.assertRaises(InputError):
            consequential_ballot(['a', 'b', 'c', 'd'], ['a', 'b', 'c'], False, receipt())

    def test_protected_commitments_not_amendable(self):
        for changed in ([], [{'id': 'independent-review', 'commitment': 'Abolish it.'}],
                        [{'id': 'renamed', 'commitment': 'Preserve independent review.'}],
                        limits() + [{'id': 'audit', 'commitment': 'Preserve audit.'}]):
            with self.assertRaises(InputError): require_preserved_limits(limits(), changed)
        require_preserved_limits(limits(), copy.deepcopy(limits()))

    def test_limit_ids_unique_and_text_nonblank(self):
        for invalid in ([{'id': '', 'commitment': 'Text'}],
                        [{'id': 'x', 'commitment': ' '}],
                        [{'id': 'x', 'commitment': 'One'}, {'id': 'x', 'commitment': 'Two'}]):
            with self.assertRaises(InputError): validate_protected_limits(invalid)

    def test_text_truth_is_not_inferred(self):
        record = receipt()
        record['burden_justification'] = 'Unsupported assertion deliberately accepted as supplied text.'
        self.assertTrue(validate_decision_record(record, limits()))

    def test_cli_ballot_complete_fixture(self):
        run = subprocess.run([sys.executable, '-m', 'wac_offline', 'ballot',
                              str(ROOT / 'fixtures' / 'ballot.json')],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['authority'], 'NONE')
        self.assertIs(result['execution_enabled'], False)
        self.assertIs(result['decision_record_complete'], True)


if __name__ == '__main__':
    unittest.main()
