"""Freeze every deterministic v1 integration byte across optional triage development."""
import hashlib
import json
import unittest

from wac_offline.runner_fixtures import integration_report


class LegacyTriageCompatibility(unittest.TestCase):
    def test_all_sixteen_legacy_episodes_are_unchanged(self):
        report = integration_report()
        self.assertEqual((report['episodes'], report['scenarios']), (16, 8))
        # Only pre-existing machine-dependent durations are removed. Everything
        # else, including complete inputs, traces, accounting and outcomes, is
        # frozen against remote commit 0ad0b4b5fa0242a8cbcafd7afc03ac0922e564a7.
        for row in report['rows']:
            del row['costs']['cpu_seconds']
            del row['costs']['wall_seconds']
        canonical = json.dumps(report, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=True, allow_nan=False).encode('utf-8')
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                         '1feeaeec638ec9faefaa06283a6d098097b482c4ad89da788ca53dd1f249aefb')


if __name__ == '__main__':
    unittest.main()
