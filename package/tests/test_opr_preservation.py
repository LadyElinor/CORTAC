"""Published baseline and source remain intact across the additive proposal."""
import hashlib
import json
from pathlib import Path
import unittest

from wac_offline.triage_fixtures import integration_report

ROOT = Path(__file__).resolve().parents[2]


class OPRPreservationTests(unittest.TestCase):
    def test_published_baseline_bytes_except_reviewed_integration_files(self):
        allowed = {'README.md', 'docs/CURRENT_CONTRACT.md', 'scripts/verify.py'}
        lines = (ROOT / 'provenance/opr1_baseline_SHA256SUMS').read_text().splitlines()
        self.assertEqual(len(lines), 163)
        self.assertEqual(len(allowed), 3)
        checked = 0
        for line in lines:
            expected, name = line.split('  ', 1)
            if name in allowed: continue
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
            checked += 1
        self.assertEqual(checked, 160)

    def test_all_fifteen_triage_episodes_unchanged(self):
        raw = json.dumps(integration_report(), sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '9462a117a753f118b64de52edb17ff9092a60bb8bbb7143b04d60ccba993fccc')

    def test_exact_source_snapshot_digest(self):
        raw = (ROOT / 'provenance/opr1_source.md').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '16d50f8993920c07988ad4b9c6b676bda6bdc98c2eb93d553a2469586ea7e3dd')
        text = raw.decode()
        self.assertEqual(len([l for l in text.splitlines() if l.startswith('## ') and l[3:4].isdigit()]), 16)
        self.assertEqual(len([l for l in text.split('## 15 Acceptance tests')[1].split('## 16')[0].splitlines()
                              if l.startswith('| ')]) - 2, 19)


if __name__ == '__main__': unittest.main()
