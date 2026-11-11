"""Regression checks for the agent's read surface and exported evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from wac_offline.agent_controls import AgentControlGateway, report
from wac_offline.runner import RunnerError
from wac_offline.runner_fixtures import fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from check_agent_controls import check


class AgentControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observed = report()

    def test_frozen_matrix_reconciles(self):
        self.assertEqual(check(self.observed), 42)

    def test_denied_reads_never_return_the_private_record(self):
        data = fixture()
        note = {'content': 'Synthetic private ticket 119'}
        with AgentControlGateway(data, 'refund', note) as gateway:
            for session in (None, 'unknown', 'guest-session', 'green-session'):
                with self.subTest(session=session), self.assertRaises(RunnerError):
                    gateway.reader_call(session, 'read_record', 'private-ticket')
            with self.assertRaisesRegex(RunnerError, 'record access denied'):
                gateway.reader_call('blue-session', 'read_record', 'missing')
            for event in gateway.snapshot()['journal']:
                self.assertEqual(event['result'], 'REJECTED')
                self.assertNotIn(note['content'], str(event))
            delivery = gateway.reader_call('blue-session', 'read_record', 'private-ticket')
            delivery.clear()
            self.assertEqual(gateway.reader_call('blue-session', 'read_record', 'private-ticket'), note)

    def test_incomplete_and_duplicated_case_exports_are_rejected(self):
        for replacement in ([], [self.observed['rows'][0]]):
            export = dict(self.observed, rows=self.observed['rows'][:-1] + replacement)
            with self.assertRaisesRegex(ValueError, 'inventory'):
                check(export)

    def test_checker_detects_tampered_evidence(self):
        def edited(case):
            export = deepcopy(self.observed)
            row = next(r for r in export['rows'] if r['inputs']['case'] == case)
            return export, row

        changes = [('effect_failure', lambda r: r['state'].update(simulated_commands=[{}])),
                   ('revoked', lambda r: r['state']['journal'].pop()),
                   ('approved', lambda r: r['state']['effects'][0].update(executor='reader')),
                   ('approved', lambda r: r['state']['receipts']['r3'].update(result='FAIL')),
                   ('approved', lambda r: r['audit'].update(observed_revision=True)),
                   ('anonymous', lambda r: r.update(read_digest='delivered')),
                   ('withheld', lambda r: r['inputs'].update(review_granted=True))]
        for case, mutate in changes:
            with self.subTest(case=case):
                export, row = edited(case)
                mutate(row)
                with self.assertRaises(ValueError):
                    check(export)
