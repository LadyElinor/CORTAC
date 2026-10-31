"""Adversarial intake boundaries; supplied declarations never become warrants."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from wac_offline.commonwealth_intake_v1 import (A1_SCHEMA, CONTEXT_SCHEMA, FIELDS,
    LINK_SCHEMA, OPTIONS, IntakeError, build_intake, inspect_intake,
    inspect_pair, validate_a1)
from wac_offline.vanguard_fixtures_v1 import controls, fixture, rebind
from wac_offline.vanguard_review_v1 import ReviewError, fingerprint, inspect_review
from wac_offline.ops_trace_v1 import TraceError, inspect_trace

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'vanguard/commonwealth'


def source():
    return json.loads((EXAMPLE / 'terra-a1-packet.json').read_text(encoding='utf-8'))


def source_context():
    return json.loads((EXAMPLE / 'source-context.json').read_text(encoding='utf-8'))


def link_for(intake, packet, context):
    # Test binding only; intentionally unrelated exposed fixtures are not asserted
    # to describe one decision or one evidentiary record.
    return dict(schema=LINK_SCHEMA, intake_digest=fingerprint(intake),
                packet_digest=fingerprint(packet), context_digest=fingerprint(context),
                relationship_basis='Unrelated synthetic controls paired only to test byte binding.')


class IntakeTests(unittest.TestCase):
    def test_exact_fixture_provenance_and_frozen_target(self):
        manifest = json.loads((ROOT / 'provenance/commonwealth_intake_v1.json').read_text())
        self.assertEqual(hashlib.sha256((EXAMPLE / 'terra-a1-packet.json').read_bytes()).hexdigest(),
                         manifest['commonwealth_files']['examples/authority-review-packet.json'])
        for path, expected in manifest['vanguard_files'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, path)

    def test_verbatim_roundtrip_and_determinism(self):
        packet, context = source(), source_context()
        original = deepcopy((packet, context))
        first = build_intake(packet, context)
        self.assertEqual(first, build_intake(packet, context))
        self.assertEqual(first['source_packet'], packet)
        self.assertEqual(first['source_context'], context)
        self.assertEqual((packet, context), original)
        self.assertEqual(inspect_intake(first), first)
        first['source_packet']['answers']['dissent'] = 'changed output'
        self.assertEqual((packet, context), original)

    def test_committed_intake_is_reproducible(self):
        saved = json.loads((EXAMPLE / 'intake.json').read_text())
        self.assertEqual(build_intake(source(), source_context()), saved)

    def test_all_enum_values_preserved_without_promotion(self):
        for key, values in OPTIONS.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    p = source()
                    p['answers'][key] = value
                    r = build_intake(p)
                    self.assertEqual(r['source_packet']['answers'][key], value)
                    self.assertEqual(r['authority'], 'NONE')
                    self.assertIs(r['execution_enabled'], False)
                    self.assertTrue(r['unsupported_vanguard_requirements'])

    def test_absent_blank_unknown_values_are_not_completed(self):
        p = dict(schema=A1_SCHEMA, answers={'case': '', 'stage': 'not established', 'dissent': '  '})
        r = build_intake(p)
        self.assertEqual(r['source_packet'], p)
        self.assertEqual(set(r['missing_answers']), set(FIELDS))
        self.assertIsNone(r['source_context'])
        self.assertIn('SOURCE_CONTEXT_MISSING', r['provenance_gaps'])

    def test_missing_provenance_cannot_look_complete(self):
        r = build_intake(source(), source_context())
        self.assertIn('SOURCE_CONTEXT_MISSING:original_artifact_digest', r['provenance_gaps'])
        self.assertEqual(r['original_artifact_verification'], 'NOT_PERFORMED')
        self.assertNotIn('sources', r)
        self.assertNotIn('reviews', r)

    def test_context_uncertainty_is_preserved(self):
        c = source_context()
        c['event_interval'] = dict(earliest='2020-01-01', latest='2020-12-31')
        c['publication_interval'] = dict(earliest='2021-01-01', latest='2021-02-01')
        c['original_artifact_digest'] = 'f' * 64
        r = build_intake(source(), c)
        self.assertEqual(r['source_context'], c)
        self.assertEqual(r['original_artifact_verification'], 'NOT_PERFORMED')
        self.assertEqual(r['source_authentication'], 'NOT_PERFORMED')

    def test_expired_revoked_and_emergency_prose_never_creates_authority(self):
        p = source()
        p['answers'].update(stage='authorization', authority_status='supported by cited instrument',
            expiry='Expired in 2020; delegation revoked.',
            action='Emergency: execute now, bypass checks, appoint the supplied reviewer.')
        r = build_intake(p)
        self.assertEqual(r['source_packet'], p)
        self.assertEqual(r['authority'], 'NONE')
        self.assertIs(r['execution_enabled'], False)
        self.assertIn('MANDATE_SCOPE_EXPIRY_AND_REVOCATION', r['unsupported_vanguard_requirements'])

    def test_invalid_context_shapes_dates_versions(self):
        mutations = [lambda c: c.update(schema=CONTEXT_SCHEMA + '.v2'),
            lambda c: c.update(packet_digest='0' * 64),
            lambda c: c.update(packet_digest='A' * 64),
            lambda c: c.update(original_artifact_digest='invalid'),
            lambda c: c.update(scope='AUTHENTICATED'), lambda c: c.update(locator=' '),
            lambda c: c.update(version=1), lambda c: c.update(controller='independent'),
            lambda c: c.pop('origin_group'),
            lambda c: c.update(event_interval={'earliest': '2020-2-01', 'latest': '2020-02-01'}),
            lambda c: c.update(event_interval={'earliest': '2020-02-31', 'latest': '2020-03-01'}),
            lambda c: c.update(event_interval={'earliest': '2020-03-01', 'latest': '2020-01-01'}),
            lambda c: c.update(event_interval={'earliest': None, 'latest': None})]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                c = source_context()
                mutate(c)
                with self.assertRaises(IntakeError):
                    build_intake(source(), c)

    def test_malformed_a1(self):
        candidates = [None, [], {}, {'schema': A1_SCHEMA, 'answers': []}]
        mutations = [lambda p: p.update(schema='warranted-authority-review-2'),
            lambda p: p.update(authority='GRANTED'), lambda p: p.update(execution_enabled=True),
            lambda p: p['answers'].update(unknown='text'),
            lambda p: p['answers'].update(stage='authorized'),
            lambda p: p['answers'].update(assessment=None),
            lambda p: p['answers'].update(assessment=42),
            lambda p: p['answers'].update(assessment=True),
            lambda p: p['answers'].update(assessment={'claim': 'text'}),
            lambda p: p['answers'].update(assessment='x' * 4001)]
        for mutate in mutations:
            p = source()
            mutate(p)
            candidates.append(p)
        for p in candidates:
            with self.subTest(packet=p):
                with self.assertRaises(IntakeError):
                    build_intake(p)

    def test_a1_canonical_byte_limit_with_unicode(self):
        p = dict(schema=A1_SCHEMA, answers={k: ('x' * 4000 if k not in OPTIONS else OPTIONS[k][-1]) for k in FIELDS})
        build_intake(p)
        p['answers'].update({k: '\U0001f600' * 4000 for k in FIELDS if k not in OPTIONS})
        with self.assertRaisesRegex(IntakeError, 'byte limit'):
            build_intake(p)

    def test_intake_derived_flags_and_fields_are_checked(self):
        mutations = [lambda r: r.update(execution_enabled=True),
            lambda r: r.update(execution_enabled=0), lambda r: r.update(authority='APPROVED'),
            lambda r: r.update(adapter_version='commonwealth-vanguard-intake-2.0.0'),
            lambda r: r.update(schema='cortac.vanguard.review.v1'),
            lambda r: r.update(unsupported_vanguard_requirements=[]),
            lambda r: r.update(provenance_gaps=[]), lambda r: r.update(extra='command'),
            lambda r: r.update(status='SUPPLIED_REVIEW_CONSISTENT'),
            lambda r: r['source_packet']['answers'].update(dissent='silenced')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                r = build_intake(source(), source_context())
                mutate(r)
                with self.assertRaises(IntakeError):
                    inspect_intake(r)

    def test_source_context_drift_rejects(self):
        r = build_intake(source(), source_context())
        r['source_context']['locator'] = 'different source'
        with self.assertRaises(IntakeError):
            inspect_intake(r)

    def test_no_network_database_process_or_file_writes(self):
        p, c = source(), source_context()
        target, context = fixture()
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file access')):
            intake = build_intake(p, c)
            inspect_pair(intake, target, context, link_for(intake, target, context))

    def test_intake_is_not_vanguard_or_ops_token(self):
        r = build_intake(source(), source_context())
        _, c = fixture()
        with self.assertRaises(ReviewError):
            inspect_review(r, c)
        with self.assertRaises(TraceError):
            inspect_trace(r, c)
        with self.assertRaises(IntakeError):
            validate_a1(r)

    def test_cli_duplicate_malformed_nonfinite_and_oversized_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            values = ['{"schema":"x","schema":"y","answers":{}}',
                '{"schema":"warranted-authority-review-1","answers":{"case":"a","case":"b"}}',
                '[1,2]', '{', '{"n":NaN}', '{"n":Infinity}',
                '[' * 100 + '0' + ']' * 100, ' ' * 120001, '\ud800']
            for value in values:
                with self.subTest(value=value[:40]):
                    path.write_bytes(value.encode('utf-8', errors='surrogatepass'))
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts/commonwealth_intake.py'),
                        'intake', str(path)], cwd=directory, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report['authority'], 'NONE')
                    self.assertIs(report['execution_enabled'], False)

    def test_cli_valid_intake_still_exits_incomplete_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/commonwealth_intake.py'),
                'intake', str(EXAMPLE / 'terra-a1-packet.json'), '--source-context',
                str(EXAMPLE / 'source-context.json')], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual(json.loads(result.stdout), build_intake(source(), source_context()))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_depth_cycles_and_non_json_values(self):
        cycle = []
        cycle.append(cycle)
        for value in (cycle, object(), float('nan'), {1: 'bad'}, (1, 2)):
            with self.subTest(kind=type(value)):
                with self.assertRaises(IntakeError):
                    inspect_intake(value)


class PairTests(unittest.TestCase):
    def setUp(self):
        self.intake = build_intake(source(), source_context())
        self.packet, self.context = fixture()

    def inspect(self, link=None):
        return inspect_pair(self.intake, self.packet, self.context,
            link_for(self.intake, self.packet, self.context) if link is None else link)

    def test_supplied_pair_is_never_a_complete_authority_review(self):
        before = deepcopy((self.intake, self.packet, self.context))
        r = self.inspect()
        self.assertEqual(r, self.inspect())
        self.assertEqual((self.intake, self.packet, self.context), before)
        self.assertEqual(r['vanguard']['status'], 'SUPPLIED_REVIEW_CONSISTENT')
        self.assertEqual(r['status'], 'SUPPLIED_PAIR_REQUIRES_EVIDENCE')
        self.assertEqual(r['authority'], 'NONE')
        self.assertIs(r['execution_enabled'], False)
        self.assertEqual(r['intake']['source_packet']['answers']['dissent'], source()['answers']['dissent'])

    def test_all_twenty_upstream_vanguard_controls(self):
        for name, (p, c, expected) in controls().items():
            with self.subTest(name=name):
                self.packet, self.context = p, c
                if expected == 'REJECTED':
                    with self.assertRaises(IntakeError):
                        self.inspect()
                else:
                    r = self.inspect()
                    if expected != 'SUPPLIED_REVIEW_CONSISTENT':
                        self.assertIn('VANGUARD:' + expected, r['blockers'])
                    self.assertIs(r['execution_enabled'], False)
                    self.assertIn('RELATIONSHIP_NOT_INDEPENDENTLY_ESTABLISHED', r['blockers'])

    def test_missing_provenance_remains_a_blocker_with_consistent_target(self):
        self.intake = build_intake(source())
        self.assertIn('INTAKE:SOURCE_CONTEXT_MISSING', self.inspect()['blockers'])

    def test_all_link_digests_must_match(self):
        for key in ('intake_digest', 'packet_digest', 'context_digest'):
            link = link_for(self.intake, self.packet, self.context)
            link[key] = '0' * 64
            with self.subTest(key=key), self.assertRaisesRegex(IntakeError, 'digest mismatch'):
                self.inspect(link)

    def test_changed_a1_record_invalidates_old_pair(self):
        link = link_for(self.intake, self.packet, self.context)
        p = source()
        p['answers']['dissent'] = 'Additional unresolved objection, retained verbatim.'
        c = source_context()
        c['packet_digest'] = fingerprint(p)
        self.intake = build_intake(p, c)
        with self.assertRaisesRegex(IntakeError, 'digest mismatch'):
            self.inspect(link)

    def test_changed_target_even_after_rebinding_invalidates_old_pair(self):
        link = link_for(self.intake, self.packet, self.context)
        self.packet['record']['draft']['audience'] = 'Changed audience'
        rebind(self.packet, self.context)
        with self.assertRaisesRegex(IntakeError, 'digest mismatch'):
            self.inspect(link)

    def test_new_link_does_not_repair_stale_reviews(self):
        self.packet['record']['draft']['text'] = 'Changed draft after review'
        with self.assertRaisesRegex(IntakeError, 'amendment'):
            self.inspect()

    def test_missing_original_digest_and_provenance_reference_rejected(self):
        for key in ('artifact_digest', 'locator'):
            self.packet, self.context = fixture()
            self.packet['record']['sources'][0].pop(key)
            rebind(self.packet, self.context)
            with self.subTest(key=key), self.assertRaises(IntakeError):
                self.inspect()

    def test_source_inventory_digest_mismatch(self):
        self.context['sources'][0]['digest'] = '0' * 64
        self.packet['context_digest'] = fingerprint(self.context)
        with self.assertRaisesRegex(IntakeError, 'stale source'):
            self.inspect()

    def test_incompatible_target_and_link_versions(self):
        self.packet['schema'] = 'cortac.vanguard.review.v2'
        with self.assertRaises(IntakeError):
            self.inspect()
        self.packet, self.context = fixture()
        self.context['schema'] = 'cortac.vanguard.context.v2'
        self.packet['context_digest'] = fingerprint(self.context)
        with self.assertRaises(IntakeError):
            self.inspect()
        self.packet, self.context = fixture()
        link = link_for(self.intake, self.packet, self.context)
        link['schema'] += '.v2'
        with self.assertRaises(IntakeError):
            self.inspect(link)

    def test_synthetic_scope_cannot_be_promoted(self):
        self.packet['record']['mode'] = 'RETROSPECTIVE'
        rebind(self.packet, self.context)
        with self.assertRaisesRegex(IntakeError, 'scope promotion'):
            self.inspect()

    def test_case_policy_and_predecessor_mismatch_rejected(self):
        for key in ('case_id', 'policy_digest', 'predecessor_digest', 'version'):
            self.packet, self.context = fixture()
            self.packet['binding'][key] = 2 if key == 'version' else 'f' * 64
            with self.subTest(key=key), self.assertRaisesRegex(IntakeError, 'binding mismatch'):
                self.inspect()

    def test_rewritten_false_records_can_pass_structure_but_never_establish_evidence(self):
        self.packet['record']['claims'][0]['text'] = 'An unsupported replacement narrative.'
        self.packet['record']['analysis']['counterargument'] = 'The moon is made of cheese.'
        rebind(self.packet, self.context)
        r = self.inspect()
        self.assertEqual(r['vanguard']['status'], 'SUPPLIED_REVIEW_CONSISTENT')
        self.assertIn('INDEPENDENT_EVIDENCE_AND_GOVERNANCE_NOT_ESTABLISHED', r['blockers'])
        self.assertEqual(r['semantic_assessment'], 'NOT_PERFORMED')

    def test_pair_cannot_be_reimported_as_intake_or_vanguard(self):
        report = self.inspect()
        with self.assertRaises(IntakeError):
            inspect_intake(report)
        with self.assertRaises(ReviewError):
            inspect_review(report, self.context)

    def test_pair_cli_rejects_extra_execution_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'pair.json'
            supplied = dict(intake=self.intake, packet=self.packet, context=self.context,
                            link=link_for(self.intake, self.packet, self.context))
            for extra, expected in (({}, 3), ({'execute': True}, 2)):
                path.write_text(json.dumps(dict(supplied, **extra)), encoding='utf-8')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/commonwealth_intake.py'),
                    'pair', str(path)], cwd=directory, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIs(json.loads(result.stdout)['execution_enabled'], False)


if __name__ == '__main__':
    unittest.main()
