"""Retained-record mutations must fail without changing their journal history."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('r1_retained_replay', ROOT/'scripts/check_repository_self_application.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class RetainedReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT/'provenance/r1_self_application'
        cls.rows = json.loads((cls.root/'journal.json').read_text())
        cls.report = json.loads((cls.root/'final-report.json').read_text())
        cls.manifest = json.loads((cls.root/'manifest.json').read_text())
        cls.state, cls.head, cls.count = replay.replay_rows(cls.rows)

    def validate(self, report):
        replay.validate_report(report, self.state, self.head, self.count)

    def test_both_original_reports_remain_valid(self):
        for root in (self.root, self.root/'repair'):
            with self.subTest(task=root.name):
                rows = json.loads((root/'journal.json').read_text())
                state, head, count = replay.replay_rows(rows)
                replay.validate_report(json.loads((root/'final-report.json').read_text()), state, head, count)
                replay.validate_manifest(json.loads((root/'manifest.json').read_text()))

    def test_five_demonstrated_contradictions_rejected(self):
        probes = json.loads((ROOT/'provenance/r1_replay_audit/baseline.json').read_text())['cases']
        for probe in probes:
            with self.subTest(case=probe['case']):
                if probe['field'] is None:
                    self.validate(self.report)
                    continue
                changed = copy.deepcopy(self.report)
                changed[probe['field']] = probe['value']
                with self.assertRaises(ValueError): self.validate(changed)

    def test_authority_and_authenticity_cannot_be_promoted(self):
        mutations = dict(scope='PRODUCTION', authority='EXECUTE', external_execution_enabled=True,
                         independent_review_established=True, controller_closure='VERIFIED',
                         approval_granted=True, parent_authenticity=True, source_authenticity=True,
                         local_effects='UNLIMITED', declared_control='INDEPENDENT')
        for key, value in mutations.items():
            with self.subTest(field=key):
                changed = copy.deepcopy(self.report); changed[key] = value
                with self.assertRaises(ValueError): self.validate(changed)

    def test_every_required_report_field_and_extra_field(self):
        for key in self.report:
            with self.subTest(missing=key):
                changed = copy.deepcopy(self.report); del changed[key]
                with self.assertRaises(ValueError): self.validate(changed)
        changed = copy.deepcopy(self.report); changed['new_authority'] = 'approved'
        with self.assertRaises(ValueError): self.validate(changed)

    def test_nested_bool_and_float_aliases_refused(self):
        for field, value in [('exit_code', False), ('exit_code', 0.0)]:
            changed = copy.deepcopy(self.report)
            changed['checks']['full-no-skips']['process'][field] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.validate(changed)
        for key, value in [('local_checks_passed', 1), ('review_applicable', 1), ('events', '8')]:
            changed = copy.deepcopy(self.report); changed[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError): self.validate(changed)

    def test_evidence_reference_and_pending_state_cannot_change(self):
        for target in ('reference', 'pending', 'decision', 'task'):
            changed = copy.deepcopy(self.report)
            if target == 'reference': changed['evidence_refs']['task'] = '0'*64
            elif target == 'pending': changed['pending_check'] = 'full-no-skips'
            elif target == 'decision': changed['decision'] = 'DECLINE'
            else: changed['task_id'] = 'different-task'
            with self.subTest(target=target), self.assertRaises(ValueError): self.validate(changed)

    def test_historical_freshness_is_only_a_coherent_supplied_observation(self):
        for current in (True, False, None):
            changed = copy.deepcopy(self.report)
            changed['candidate_current'] = current
            changed['review_applicable'] = bool(current)
            # Deliberately accepted: replay does not authenticate this observation.
            self.validate(changed)
        for current in ('true', 1, 0, [], {}):
            changed = copy.deepcopy(self.report); changed['candidate_current'] = current
            with self.subTest(current=current), self.assertRaises(ValueError): self.validate(changed)
        changed = copy.deepcopy(self.report); changed['candidate_current'] = False
        with self.assertRaises(ValueError): self.validate(changed)

    def test_manifest_closed_scope_and_types(self):
        for key, value in [('scope', 'PRODUCTION'), ('authority', 'EXECUTE'),
                           ('independent_review_established', 0), ('base_commit', 'main'),
                           ('candidate_tree', '../escape'), ('files', []), ('task_id', '')]:
            changed = copy.deepcopy(self.manifest); changed[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError): replay.validate_manifest(changed)
        for key in self.manifest:
            changed = copy.deepcopy(self.manifest); del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError): replay.validate_manifest(changed)
        changed = copy.deepcopy(self.manifest); changed['promoted'] = True
        with self.assertRaises(ValueError): replay.validate_manifest(changed)
        changed = copy.deepcopy(self.manifest); changed['files']['journal.json'] = 'invalid'
        with self.assertRaises(ValueError): replay.validate_manifest(changed)

    def test_exported_events_reject_wrong_shapes_before_sqlite_coercion(self):
        for rows in (None, {}, [], [None], ['event'], self.rows*9):
            with self.subTest(shape=type(rows).__name__), self.assertRaises(ValueError): replay.replay_rows(rows)
        for key, value in [('seq', True), ('seq', '1'), ('seq', 1.0), ('kind', 1),
                           ('body', []), ('hash', None), ('previous', 0)]:
            rows = copy.deepcopy(self.rows); rows[0][key] = value
            with self.subTest(field=key, value=value), self.assertRaises(ValueError): replay.replay_rows(rows)

    def test_original_receipt_bytes_stay_preserved(self):
        for folder in (self.root, self.root/'repair'):
            manifest = json.loads((folder/'manifest.json').read_text())
            for name, sha in manifest['files'].items():
                with self.subTest(folder=folder.name, name=name):
                    self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(), sha)

    def test_report_nonobjects_are_clean_refusals(self):
        for report in (None, [], 'report', 1, True):
            with self.subTest(report=report), self.assertRaises(ValueError): self.validate(report)


if __name__ == '__main__':
    unittest.main()
