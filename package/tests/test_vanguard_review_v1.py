"""Structural regressions and explicit limitations for the Vanguard adapter."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from wac_offline.ops_fixtures_v1 import fixture as ops_fixture
from wac_offline.vanguard_fixtures_v1 import controls, fixture, integration_report, rebind
from wac_offline.vanguard_review_v1 import (ReviewError, fingerprint, inspect_review,
                                           inspect_ops_handoff)

ROOT = Path(__file__).resolve().parents[2]


class VanguardReviewTests(unittest.TestCase):
    def test_exposed_controls(self):
        report = integration_report()
        self.assertEqual(report['controls'], 20)
        self.assertTrue(report['all_fixed_structural_outcomes'], report)

    def test_determinism_and_no_mutation(self):
        p, c = fixture()
        original = deepcopy((p, c))
        self.assertEqual(inspect_review(p, c), inspect_review(p, c))
        self.assertEqual((p, c), original)

    def test_source_echoes_are_one_declared_origin(self):
        p, c, _ = controls()['three_records_one_origin']
        self.assertEqual(inspect_review(p, c)['supplied_origin_groups'], 1)

    def test_real_world_authority_never_follows_consistency(self):
        for resolved in (False, True):
            report = inspect_review(*fixture(resolved))
            self.assertEqual(report['authority'], 'NONE')
            self.assertFalse(report['execution_enabled'])
            self.assertEqual(report['semantic_assessment'], 'NOT_PERFORMED')
            self.assertEqual(report['factual_truth'], 'NOT_ESTABLISHED')

    def test_source_replacement_invalidates_entire_review(self):
        p, c = fixture()
        p['record']['sources'][0].update(version=2, passage='Correction reverses the earlier account.')
        c['sources'][0].update(version=2, digest=fingerprint(p['record']['sources'][0]))
        p['context_digest'] = fingerprint(c)
        with self.assertRaisesRegex(ReviewError, 'amendment'):
            inspect_review(p, c)

    def test_claim_removal_invalidates_inventory(self):
        p, c = fixture()
        c['claims'].append(dict(c['claims'][0], id='new-finding'))
        p['context_digest'] = fingerprint(c)
        with self.assertRaisesRegex(ReviewError, 'inventory'):
            inspect_review(p, c)

    def test_joint_rewrite_can_pass_caller_anchors(self):
        p, c = fixture()
        p['record']['claims'][0]['text'] = 'An entirely different, unverified narrative.'
        rebind(p, c)
        self.assertEqual(inspect_review(p, c)['status'], 'SUPPLIED_REVIEW_CONSISTENT')

    def test_strict_input_and_reference_checks(self):
        mutations = [
            lambda p, c: p.update(authority='APPROVED'),
            lambda p, c: p['record']['claims'][0].update(version=True),
            lambda p, c: p['record']['claims'][0].update(version=1.5),
            lambda p, c: p['record']['claims'][0].update(source_ids=['missing']),
            lambda p, c: p['record']['sources'][0].update(locator=' '),
            lambda p, c: p['record']['sources'].append(dict(p['record']['sources'][0], passage='Duplicate ID')),
            lambda p, c: p['reviews'].append(dict(p['reviews'][0], assessment='Duplicate role')),
            lambda p, c: p['reviews'][0].update(principal='missing'),
            lambda p, c: c.update(party_ids=['missing']),
            lambda p, c: c.update(now='2020-1-4'),
            lambda p, c: c.update(now='2019-12-31'),
            lambda p, c: p['record']['decision']['occurred'].update(earliest='2021-01-01'),
            lambda p, c: p['record']['decision'].update(occurred=dict(earliest='2021-01-01', latest='2021-01-02')),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                p, c = fixture()
                mutate(p, c)
                rebind(p, c)
                with self.assertRaises(ReviewError):
                    inspect_review(p, c)

    def test_oversized_or_non_json_input(self):
        for value in (float('nan'), object(), 'x' * 1048577):
            with self.subTest(value=type(value)):
                with self.assertRaises(ReviewError):
                    fingerprint(value)

    def test_all_worked_packets(self):
        examples = sorted((ROOT / 'vanguard' / 'examples').glob('*.json'))
        self.assertEqual(len(examples), 3)
        for path in examples:
            data = json.loads(path.read_text(encoding='utf-8'))
            with self.subTest(path=path.name):
                report = inspect_review(data['packet'], data['context'])
                self.assertEqual(report['status'], 'SUPPLIED_REVIEW_CONSISTENT')

    def test_cli_status_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'packet.json'
            p, c = fixture()
            for contents, expected in [
                (json.dumps(dict(packet=p, context=c)), 0),
                ('{"packet":{},"packet":{},"context":{}}', 2),
                ('[1,2,3]', 2), ('{"broken":', 2),
            ]:
                target.write_text(contents, encoding='utf-8')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/vanguard_review.py'), str(target)],
                                        cwd=folder, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads(result.stdout)['authority'], 'NONE')
            p['record']['claims'][0]['identity'] = 'AMBIGUOUS'
            rebind(p, c)
            target.write_text(json.dumps(dict(packet=p, context=c)), encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/vanguard_review.py'), str(target)],
                                    cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 3)


class VanguardHandoffTests(unittest.TestCase):
    def setUp(self):
        self.p, self.c = fixture()
        self.t, self.o = ops_fixture()
        self.o['expected']['case_id'] = self.c['expected']['case_id']
        self.o['expected']['policy_digest'] = self.c['expected']['policy_digest']
        self.t['binding'] = deepcopy(self.o['expected'])
        self.t['context_digest'] = fingerprint(self.o)

    def link(self):
        return dict(schema='cortac.vanguard.ops_link.v1', packet_digest=fingerprint(self.p),
                    context_digest=fingerprint(self.c), trace_digest=fingerprint(self.t),
                    ops_context_digest=fingerprint(self.o))

    def inspect(self, link=None):
        return inspect_ops_handoff(self.p, self.c, self.t, self.o, self.link() if link is None else link)

    def test_bound_handoff(self):
        report = self.inspect()
        self.assertEqual(report['status'], 'SUPPLIED_HANDOFF_CONSISTENT')
        self.assertEqual(report['authority'], 'NONE')
        self.assertEqual(report['relationship'], 'CALLER_ASSERTED_ONLY')
        self.assertFalse(report['execution_enabled'])

    def test_link_scope_drift(self):
        link = self.link()
        self.p['record']['draft']['audience'] = 'Changed audience'
        rebind(self.p, self.c)
        with self.assertRaisesRegex(ReviewError, 'digest mismatch'):
            self.inspect(link)

    def test_unrelated_case_and_policy(self):
        for key in ('case_id', 'policy_digest'):
            with self.subTest(key=key):
                self.setUp()
                self.o['expected'][key] = 'd'*64
                self.t['binding'] = deepcopy(self.o['expected'])
                self.t['context_digest'] = fingerprint(self.o)
                with self.assertRaisesRegex(ReviewError, 'case or policy'):
                    self.inspect()

    def test_review_hold_propagates(self):
        self.p['record']['claims'][0]['identity'] = 'AMBIGUOUS'
        rebind(self.p, self.c)
        self.assertIn('REVIEW:IDENTITY_AMBIGUOUS', self.inspect()['blockers'])

    def test_remedy_hold_propagates(self):
        self.t['remedy']['residuals'][0]['state'] = 'UNRESOLVED'
        self.assertIn('OPS1:RESIDUAL_INJURY_NOT_REPAIRED', self.inspect()['blockers'])

    def test_closed_concern_does_not_request_remedy(self):
        self.p['record'].update(disposition='CLOSE_CONCERN')
        self.p['record']['draft'].update(kind='NO_CHALLENGE')
        rebind(self.p, self.c)
        self.assertIn('REMEDY_HANDOFF_REQUIRES_RETAINED_CONCERN', self.inspect()['blockers'])

    def test_malformed_ops_wrapped(self):
        self.t['authority'] = 'APPROVED'
        with self.assertRaisesRegex(ReviewError, 'OPS1'):
            self.inspect()


if __name__ == '__main__':
    unittest.main()
