"""Run declared unittest suites and retain structured coverage observations.

CoverageResult adapts the MIT-licensed Unfinished Commonwealth M1 helper at
0302f350d7936050967e6e16b65e81a0c6a915ec. This is same-host accounting,
not authentication against test code or an operator that rewrites the runner.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

SCHEMA = 'cortac.unittest.receipt.v1'


class CoverageResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skipped_started = 0
        self.active_test = None

    def startTest(self, test):
        self.active_test = test
        super().startTest(test)

    def stopTest(self, test):
        self.active_test = None
        super().stopTest(test)

    def addSkip(self, test, reason):
        # Module/class setup skips do not start a case; a skipped subtest is
        # not a wholly skipped started case. Retain all three kinds below.
        if test is self.active_test:
            self.skipped_started += 1
        super().addSkip(test, reason)


def validate_receipt(value):
    fields = {'schema', 'tests_run', 'tests_not_skipped', 'skipped_started',
              'skipped', 'failures', 'errors', 'expected_failures',
              'unexpected_successes', 'successful'}
    if type(value) is not dict or set(value) != fields or value['schema'] != SCHEMA:
        raise ValueError('unsupported test receipt')
    for key in ('tests_run', 'tests_not_skipped', 'skipped_started'):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError('invalid coverage counter: ' + key)
    if value['tests_not_skipped'] + value['skipped_started'] != value['tests_run']:
        raise ValueError('contradictory test partition')
    for key in ('failures', 'errors', 'expected_failures', 'unexpected_successes'):
        if type(value[key]) is not list or any(type(x) is not str or not x for x in value[key]):
            raise ValueError('invalid outcome list: ' + key)
    skips = value['skipped']
    if type(skips) is not list or any(type(x) is not dict or set(x) != {'test', 'reason'}
            or type(x['test']) is not str or not x['test'] or type(x['reason']) is not str for x in skips):
        raise ValueError('invalid skip list')
    if value['skipped_started'] > len(skips):
        raise ValueError('missing skip outcomes')
    success = not (value['failures'] or value['errors'] or value['unexpected_successes'])
    if type(value['successful']) is not bool or value['successful'] != success:
        raise ValueError('contradictory success flag')
    return value


def load_suite(args):
    loader = unittest.TestLoader()
    if args[:3] == ['-m', 'unittest', 'discover']:
        parser = argparse.ArgumentParser()
        parser.add_argument('-s', '--start-directory', default='.')
        parser.add_argument('-p', '--pattern', default='test*.py')
        parser.add_argument('-t', '--top-level-directory')
        parser.add_argument('-v', '--verbose', action='store_true')
        options = parser.parse_args(args[3:])
        return loader.discover(options.start_directory, options.pattern, options.top_level_directory)
    if len(args) == 1 and Path(args[0]).is_file() and Path(args[0]).suffix == '.py':
        path = Path(args[0]).resolve()
        return loader.discover(str(path.parent), pattern=path.name)
    raise ValueError('unsupported unittest stage command')


def main():
    if len(sys.argv) < 5 or sys.argv[1] != '--receipt' or sys.argv[3] != '--':
        raise ValueError('expected --receipt PATH -- UNITTEST_COMMAND')
    destination = Path(sys.argv[2])
    # A fresh destination prevents a previous invocation from supplying results.
    if destination.exists():
        raise ValueError('receipt destination already exists')
    suite = load_suite(sys.argv[4:])
    result = unittest.TextTestRunner(verbosity=2, resultclass=CoverageResult).run(suite)
    receipt = dict(schema=SCHEMA, tests_run=result.testsRun,
                   tests_not_skipped=result.testsRun-result.skipped_started,
                   skipped_started=result.skipped_started,
                   skipped=[dict(test=test.id(), reason=reason) for test, reason in result.skipped],
                   failures=[test.id() for test, _ in result.failures],
                   errors=[test.id() for test, _ in result.errors],
                   expected_failures=[test.id() for test, _ in result.expectedFailures],
                   unexpected_successes=[test.id() for test in result.unexpectedSuccesses],
                   successful=result.wasSuccessful())
    validate_receipt(receipt)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, sort_keys=True)
        stream.write('\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
