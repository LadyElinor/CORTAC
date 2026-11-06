"""Actual child suites challenge verifier coverage; console text is not evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('coverage_verifier', ROOT / 'scripts/verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
from test_receipts import validate_receipt
sys.path.pop(0)


class VerifierCoverageTests(unittest.TestCase):
    def step(self, code, *, strict=False, minimum=1, direct=False):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'test_sample.py'
            path.write_text('import unittest\n' + textwrap.dedent(code), encoding='utf-8')
            args = [str(path)] if direct else ['-m', 'unittest', 'discover', '-s', temporary, '-v']
            return verify.run_step('coverage-fixture', args, '', minimum_tests=minimum, require_no_skips=strict)

    def test_actual_success_and_direct_script(self):
        for direct in (False, True):
            with self.subTest(direct=direct):
                r = self.step('''
                    class T(unittest.TestCase):
                        def test_ok(self): self.assertEqual(2+2, 4)
                ''', direct=direct)
                self.assertTrue(r['passed'], r)
                self.assertEqual(r['coverage']['tests_not_skipped'], 1)
                self.assertEqual(r['coverage']['skipped'], [])

    def test_whole_suite_skipped_fails(self):
        r = self.step('''
            @unittest.skip('unavailable')
            class T(unittest.TestCase):
                def test_never(self): raise AssertionError('should never execute')
        ''')
        self.assertFalse(r['passed'])
        self.assertEqual(r['tests_run'], 1)
        self.assertEqual(r['coverage']['tests_not_skipped'], 0)

    def test_empty_suite_fails_even_with_zero_floor(self):
        r = self.step('', minimum=0)
        self.assertFalse(r['passed'])
        self.assertEqual(r['tests_run'], 0)

    def test_mixed_skips_are_reported_or_strictly_refused(self):
        code = '''
            class T(unittest.TestCase):
                def test_ok(self): pass
                @unittest.skip('optional tool missing')
                def test_skipped(self): pass
        '''
        for strict in (False, True):
            with self.subTest(strict=strict):
                r = self.step(code, strict=strict)
                self.assertEqual(r['passed'], not strict)
                self.assertEqual(r['tests_run'], 2)
                self.assertEqual(r['coverage']['tests_not_skipped'], 1)
                self.assertEqual(r['coverage']['skipped'][0]['reason'], 'optional tool missing')

    def test_class_setup_skip_does_not_subtract_unstarted_cases(self):
        r = self.step('''
            class T(unittest.TestCase):
                @classmethod
                def setUpClass(cls): raise unittest.SkipTest('class unavailable')
                def test_never(self): pass
        ''')
        self.assertFalse(r['passed'])
        self.assertEqual(r['tests_run'], 0)
        self.assertEqual(r['coverage']['tests_not_skipped'], 0)
        self.assertEqual(len(r['coverage']['skipped']), 1)

    def test_module_setup_skip_is_retained(self):
        r = self.step('''
            def setUpModule(): raise unittest.SkipTest('module unavailable')
            class T(unittest.TestCase):
                def test_never(self): pass
        ''')
        self.assertFalse(r['passed'])
        self.assertEqual(r['tests_run'], 0)
        self.assertEqual(r['coverage']['skipped_started'], 0)
        self.assertEqual(len(r['coverage']['skipped']), 1)

    def test_subtest_skip_is_partial_not_whole_case(self):
        code = '''
            class T(unittest.TestCase):
                def test_part(self):
                    with self.subTest(part='optional'): self.skipTest('subcase unavailable')
                    with self.subTest(part='required'): self.assertTrue(True)
        '''
        for strict in (False, True):
            r = self.step(code, strict=strict)
            self.assertEqual(r['passed'], not strict)
            self.assertEqual(r['coverage']['tests_not_skipped'], 1)
            self.assertEqual(r['coverage']['skipped_started'], 0)
            self.assertEqual(len(r['coverage']['skipped']), 1)

    def test_failures_and_errors_separate(self):
        r = self.step('''
            class T(unittest.TestCase):
                def test_failure(self): self.fail('expected fixture failure')
                def test_error(self): raise RuntimeError('expected fixture error')
        ''')
        self.assertFalse(r['passed'])
        self.assertEqual(len(r['coverage']['failures']), 1)
        self.assertEqual(len(r['coverage']['errors']), 1)
        self.assertEqual(r['tests_run'], 2)

    def test_expected_failure_is_explicit(self):
        r = self.step('''
            class T(unittest.TestCase):
                @unittest.expectedFailure
                def test_expected(self): self.fail('known')
        ''')
        self.assertTrue(r['passed'])
        self.assertEqual(len(r['coverage']['expected_failures']), 1)

    def test_unexpected_success_fails(self):
        r = self.step('''
            class T(unittest.TestCase):
                @unittest.expectedFailure
                def test_unexpected(self): pass
        ''')
        self.assertFalse(r['passed'])
        self.assertEqual(len(r['coverage']['unexpected_successes']), 1)

    def test_import_error_retains_unittest_failure(self):
        r = self.step("raise RuntimeError('cannot import fixture')\n")
        self.assertFalse(r['passed'])
        self.assertEqual(len(r['coverage']['errors']), 1)

    def test_console_spoof_cannot_satisfy_minimum(self):
        r = self.step('''
            import sys
            print('Ran 999 tests in 0.001s', file=sys.stderr)
            class T(unittest.TestCase):
                def test_one(self): pass
        ''', minimum=2)
        self.assertFalse(r['passed'])
        self.assertEqual(r['tests_run'], 1)

    def test_early_success_exit_has_unknown_coverage(self):
        r = self.step('import os\nos._exit(0)\n')
        self.assertFalse(r['passed'])
        self.assertEqual(r['exit_code'], 0)
        self.assertIsNone(r['tests_run'])
        self.assertIsNone(r['coverage'])

    def test_timeout_has_unknown_coverage(self):
        with mock.patch.object(verify.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', 120)):
            r = verify.run_step('timeout', ['-m', 'unittest', 'discover'], '', minimum_tests=1)
        self.assertFalse(r['passed'])
        self.assertIsNone(r['tests_run'])
        self.assertIsNone(r['coverage'])

    def test_declared_timeout_retains_partial_output_without_inventing_counts(self):
        error = subprocess.TimeoutExpired('fixture', 240, output=b'partial output', stderr=b'last started case')
        with mock.patch.object(verify.subprocess, 'run', side_effect=error) as run:
            r = verify.run_step('timeout', ['-m', 'unittest', 'discover'], '', minimum_tests=1, timeout_seconds=240)
        self.assertEqual(run.call_args.kwargs['timeout'], 240)
        self.assertEqual(r['timeout_seconds'], 240)
        self.assertEqual(r['stdout'], 'partial output')
        self.assertEqual(r['stderr'], 'last started case')
        self.assertFalse(r['passed'])
        self.assertIsNone(r['tests_run'])
        self.assertIsNone(r['coverage'])

    def test_expected_refusal_non_test_stage_unchanged(self):
        r = verify.run_step('refusal', ['-c', "import json,sys; print(json.dumps({'ready':False}));sys.exit(2)"], '', expected_exit=2, json_checks={'ready': False})
        self.assertTrue(r['passed'])
        self.assertIsNone(r['coverage'])

    def test_repeated_stage_uses_fresh_receipt(self):
        good = self.step('class T(unittest.TestCase):\n def test_ok(self): pass\n')
        bad = self.step('import os\nos._exit(0)\n')
        self.assertTrue(good['passed'])
        self.assertFalse(bad['passed'])
        self.assertIsNone(bad['coverage'])

    def test_receipt_counter_and_success_shapes(self):
        valid = self.step('class T(unittest.TestCase):\n def test_ok(self): pass\n')['coverage']
        for key, value in [('tests_run', '1'), ('tests_run', True), ('tests_not_skipped', 2),
                           ('successful', False), ('skipped', ['bad']), ('errors', ['an error']),
                           ('schema', 'unknown')]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(valid); changed[key] = value
                with self.assertRaises(ValueError): validate_receipt(changed)

    def test_malformed_receipt_fails_without_console_fallback(self):
        def malformed(command, **kwargs):
            Path(command[command.index('--receipt')+1]).write_text('{broken', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, '', 'Ran 999 tests in 0.001s')
        with mock.patch.object(verify.subprocess, 'run', side_effect=malformed):
            r = verify.run_step('bad-receipt', ['-m', 'unittest', 'discover'], '', minimum_tests=1)
        self.assertFalse(r['passed'])
        self.assertIsNone(r['tests_run'])


if __name__ == '__main__':
    unittest.main()
