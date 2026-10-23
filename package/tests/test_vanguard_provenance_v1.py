"""Conditional provenance guarantees and deliberate epistemic limitation controls."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from wac_offline.ops_fixtures_v1 import fixture as ops_fixture
from wac_offline.vanguard_fixtures_v1 import rebind
from wac_offline.vanguard_provenance_fixtures_v1 import (
    controls, fixture, freeze_synthetic_inventory, integration_report,
)
from wac_offline.vanguard_provenance_v1 import inspect_provenance, inspect_pinned_ops_handoff
from wac_offline.vanguard_review_v1 import ReviewError, fingerprint, inspect_review, inspect_ops_handoff

ROOT = Path(__file__).resolve().parents[2]
OK = 'PINNED_PROVENANCE_CONSISTENT'


class ProvenanceTests(unittest.TestCase):
    def test_committed_example_uses_fixed_pin_and_exact_bytes(self):
        folder = ROOT / 'vanguard/provenance_examples'
        supplied = json.loads((folder / 'packet.json').read_text(encoding='utf-8'))
        inventory = json.loads((folder / 'inventory.json').read_text(encoding='utf-8'))
        pin = (folder / 'expected_inventory_digest.txt').read_text(encoding='utf-8').strip()
        self.assertEqual(pin, 'a3c241c8cb104d766d4dc312565d6ce83ec340f4591e1cf0dcf1ca00259230aa')
        canonical = json.dumps(inventory, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        self.assertEqual(sha256(canonical).hexdigest(), pin)
        mapping = json.loads((folder / 'artifact-map.json').read_text(encoding='utf-8'))
        artifacts = {k: (folder / v).read_bytes() for k, v in mapping.items()}
        for key, raw in artifacts.items():
            self.assertEqual(sha256(raw).hexdigest(), key)
        report = inspect_provenance(**supplied, inventory=inventory,
                                    expected_inventory_digest=pin, as_of='2020-01-04', artifacts=artifacts)
        self.assertEqual(report['status'], OK)

    def test_fixed_controls(self):
        report = integration_report()
        self.assertEqual(report['controls'], 23)
        self.assertTrue(report['all_fixed_structural_outcomes'], report)

    def test_determinism_and_no_mutation(self):
        case = fixture(frozen_review=True)
        original = deepcopy(case)
        report = inspect_provenance(**case)
        self.assertEqual(report, inspect_provenance(**case))
        self.assertEqual(case, original)
        self.assertEqual(report['verified_artifact_digests'], list(case['artifacts']))
        self.assertEqual(report['commitment_scope'], 'FROZEN_REVIEW_INPUT')

    def test_no_authority_authentication_or_independence_for_any_control(self):
        for name, (case, _) in controls().items():
            with self.subTest(control=name):
                try:
                    report = inspect_provenance(**case)
                except ReviewError:
                    continue
                self.assertEqual(report['authority'], 'NONE')
                self.assertFalse(report['execution_enabled'])
                self.assertEqual(report['controller_closure'], 'SUPPLIED_UNVERIFIED')
                for key in ('authentication', 'factual_truth', 'actual_independence', 'institutional_approval'):
                    self.assertEqual(report[key], 'NOT_ESTABLISHED')

    def test_claim_joint_rewrite_needs_review_input_commitment(self):
        for frozen in (False, True):
            with self.subTest(frozen=frozen):
                case = fixture(frozen_review=frozen)
                old_pin = case['expected_inventory_digest']
                case['packet']['record']['claims'][0]['text'] = 'Reversed conclusion, newly rebound.'
                rebind(case['packet'], case['context'])
                self.assertEqual(inspect_review(case['packet'], case['context'])['status'],
                                 'SUPPLIED_REVIEW_CONSISTENT')
                if frozen:
                    with self.assertRaisesRegex(ReviewError, 'PINNED_REVIEW_INPUT_MISMATCH'):
                        inspect_provenance(**case)
                else:
                    self.assertEqual(inspect_provenance(**case)['status'], OK)
                self.assertEqual(old_pin, case['expected_inventory_digest'])

    def test_every_source_binding_field_is_protected_after_joint_rebind(self):
        replacements = dict(id='new-id', version=2, origin_group='new-origin',
                            url='urn:replacement', locator='A different page', passage='Different words',
                            available=dict(earliest='2020-01-01', latest='2020-01-02'),
                            artifact_digest='a'*64)
        for key, value in replacements.items():
            with self.subTest(field=key):
                case = fixture()
                case['packet']['record']['sources'][0][key] = value
                if key == 'id':
                    case['packet']['record']['claims'][0]['source_ids'] = [value]
                rebind(case['packet'], case['context'])
                self.assertEqual(inspect_review(case['packet'], case['context'])['status'],
                                 'SUPPLIED_REVIEW_CONSISTENT')
                with self.assertRaisesRegex(ReviewError, 'PINNED_SOURCE_'):
                    inspect_provenance(**case)

    def test_joint_inventory_rewrite_cannot_replace_external_pin(self):
        case, _ = controls()['inventory_joint_rewrite_fixed_pin_detected']
        with self.assertRaisesRegex(ReviewError, 'INVENTORY_PIN_MISMATCH'):
            inspect_provenance(**case)

    def test_exact_source_inventory_rejects_omissions_and_additions(self):
        for extra in (False, True):
            case = fixture()
            source = deepcopy(case['packet']['record']['sources'][0])
            source['id'] = 'extra'
            case['packet']['record']['sources'].append(source)
            rebind(case['packet'], case['context'])
            if not extra:
                freeze_synthetic_inventory(case)
                case['packet']['record']['sources'].pop()
                rebind(case['packet'], case['context'])
            with self.assertRaisesRegex(ReviewError, 'PINNED_SOURCE_INVENTORY_MISMATCH'):
                inspect_provenance(**case)

    def test_same_artifact_is_hashed_once_and_does_not_add_an_origin(self):
        case = fixture()
        source = deepcopy(case['packet']['record']['sources'][0])
        source['id'] = 'echo'
        case['packet']['record']['sources'].append(source)
        rebind(case['packet'], case['context'])
        freeze_synthetic_inventory(case)
        report = inspect_provenance(**case)
        self.assertEqual(report['status'], OK)
        self.assertEqual(len(report['verified_artifact_digests']), 1)
        self.assertEqual(report['inventory_origin_groups'], 1)

    def test_coordinated_derivatives_preexisting_in_pin_remain_unidentified(self):
        case, _ = controls()['different_bytes_derivative_before_pin_limitation']
        report = inspect_provenance(**case)
        self.assertEqual(report['status'], OK)
        self.assertEqual(report['inventory_origin_groups'], 2)
        self.assertEqual(report['actual_independence'], 'NOT_ESTABLISHED')

    def test_preexisting_false_excerpt_and_replacement_pin_are_not_detectable(self):
        case, _ = controls()['replacement_of_pin_itself_limitation']
        # The changed passage is not present in the unchanged raw artifact bytes.
        self.assertNotIn(case['packet']['record']['sources'][0]['passage'].encode(),
                         next(iter(case['artifacts'].values())))
        report = inspect_provenance(**case)
        self.assertEqual(report['status'], OK)
        self.assertEqual(report['semantic_assessment'], 'NOT_PERFORMED')

    def test_raw_bytes_required_and_not_just_caller_digest_string(self):
        case = fixture()
        key = next(iter(case['artifacts']))
        case['artifacts'][key] = b'changed bytes'
        with self.assertRaisesRegex(ReviewError, 'ARTIFACT_BYTES_MISMATCH'):
            inspect_provenance(**case)
        case['artifacts'] = {}
        self.assertIn('ARTIFACT_UNAVAILABLE:' + key, inspect_provenance(**case)['blockers'])

    def test_each_missing_anchor_holds_without_fallback(self):
        for key, expected in [('inventory', 'INVENTORY_UNAVAILABLE'),
                              ('expected_inventory_digest', 'INVENTORY_PIN_UNAVAILABLE'),
                              ('as_of', 'EVALUATION_DATE_UNAVAILABLE')]:
            with self.subTest(key=key):
                case = fixture()
                case[key] = None
                report = inspect_provenance(**case)
                self.assertEqual(report['status'], 'PINNED_PROVENANCE_INCOMPLETE')
                self.assertIn(expected, report['blockers'])
                self.assertEqual(report['review']['status'], 'SUPPLIED_REVIEW_CONSISTENT')

    def test_expiry_is_inclusive_and_uses_external_as_of(self):
        case = fixture()
        case['as_of'] = '2020-01-31'
        self.assertEqual(inspect_provenance(**case)['status'], OK)
        case['as_of'] = '2020-02-01'
        report = inspect_provenance(**case)
        self.assertIn('INVENTORY_EXPIRED', report['blockers'])
        self.assertIn('SOURCE_EXPIRED:log', report['blockers'])
        self.assertEqual(case['context']['now'], '2020-01-04')

    def test_no_latest_version_or_revocation_or_trusted_clock_claim(self):
        # Replaying a previously pinned snapshot within its validity still passes.
        case = fixture()
        report = inspect_provenance(**case)
        self.assertEqual(report['status'], OK)
        self.assertEqual(report['freshness'], 'RELATIVE_TO_SUPPLIED_DATE_AND_PIN_ONLY')
        self.assertEqual(report['pin_custody'], 'EXTERNAL_PREREQUISITE_NOT_VERIFIED')

    def test_frozen_input_covers_context_and_draft_but_not_review_authorship(self):
        for target in ('draft', 'context'):
            case = fixture(frozen_review=True)
            if target == 'draft':
                case['packet']['record']['draft']['audience'] = 'Changed audience'
            else:
                case['context']['principals'][0]['controller'] = 'different-controller'
            rebind(case['packet'], case['context'])
            with self.assertRaisesRegex(ReviewError, 'PINNED_REVIEW_INPUT_MISMATCH'):
                inspect_provenance(**case)
        case = fixture(frozen_review=True)
        case['packet']['reviews'][0]['assessment'] = 'Fabricated replacement review.'
        self.assertEqual(inspect_provenance(**case)['status'], OK)

    def test_invalid_inventory_even_when_digest_matches(self):
        mutations = [
            lambda i: i.update(authority='APPROVED'),
            lambda i: i.update(version=True),
            lambda i: i.update(version=1.0),
            lambda i: i.update(schema='cortac.vanguard.source_inventory.v2'),
            lambda i: i.update(established_on='2020-1-4'),
            lambda i: i.update(established_on='2020-02-01'),
            lambda i: i.update(valid_until='2020-01-03'),
            lambda i: i.update(established_on='2020-01-02'),
            lambda i: i['sources'][0].update(valid_until='2020-01-01'),
            lambda i: i['sources'][0].update(provenance_refs=[]),
            lambda i: i['sources'][0].update(provenance_refs=[' ']),
            lambda i: i['sources'][0].update(digest='A'*64),
            lambda i: i['sources'].append(dict(i['sources'][0], version=2)),
            lambda i: i.update(review_input_commitment=[
                dict(record_digest='a'*64, context_digest='b'*64),
                dict(record_digest='c'*64, context_digest='d'*64)]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                case = fixture()
                mutate(case['inventory'])
                case['expected_inventory_digest'] = fingerprint(case['inventory'])
                with self.assertRaises(ReviewError):
                    inspect_provenance(**case)

    def test_invalid_pin_and_date(self):
        for key, values in [('expected_inventory_digest', ['', True, 'A'*64, 'a'*63]),
                             ('as_of', ['', True, '2020-1-4', '2020-02-30', '2020-01-03'])]:
            for value in values:
                with self.subTest(key=key, value=value):
                    case = fixture()
                    case[key] = value
                    with self.assertRaises(ReviewError):
                        inspect_provenance(**case)

    def test_artifact_map_types_and_limits(self):
        case = fixture()
        key = next(iter(case['artifacts']))
        for bad in ([], {key: 'text'}, {key: bytearray(b'bytes')}, {'a'*64: b'extra'}):
            with self.subTest(bad=type(bad)):
                with self.assertRaises(ReviewError):
                    inspect_provenance(**dict(case, artifacts=bad))
        module = 'wac_offline.vanguard_provenance_v1.'
        for limit in ('MAX_ARTIFACT_BYTES', 'MAX_TOTAL_ARTIFACT_BYTES'):
            with patch(module + limit, 1):
                with self.assertRaises(ReviewError):
                    inspect_provenance(**case)

    def test_existing_review_contract_is_unchanged(self):
        case = fixture()
        before = inspect_review(case['packet'], case['context'])
        inspect_provenance(**case)
        self.assertEqual(inspect_review(case['packet'], case['context']), before)
        self.assertEqual(before['schema'], 'cortac.vanguard.inspection.v1')
        self.assertEqual(before['inventory_scope'], 'SUPPLIED_INVENTORY_ONLY')


class PinnedHandoffTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture()
        self.t, self.o = ops_fixture()
        self.o['expected'].update({k: self.case['context']['expected'][k]
                                   for k in ('case_id', 'policy_digest')})
        self.t['binding'] = deepcopy(self.o['expected'])
        self.t['context_digest'] = fingerprint(self.o)

    def link(self):
        return dict(schema='cortac.vanguard.ops_link.v1',
                    packet_digest=fingerprint(self.case['packet']),
                    context_digest=fingerprint(self.case['context']),
                    trace_digest=fingerprint(self.t), ops_context_digest=fingerprint(self.o))

    def inspect(self):
        return inspect_pinned_ops_handoff(**self.case, trace=self.t, ops_context=self.o, link=self.link())

    def test_handoff_and_existing_contract_compatibility(self):
        original = deepcopy((self.case, self.t, self.o))
        baseline = inspect_ops_handoff(self.case['packet'], self.case['context'], self.t, self.o, self.link())
        report = self.inspect()
        self.assertEqual(report['status'], 'PINNED_HANDOFF_CONSISTENT')
        self.assertEqual(report['handoff'], baseline)
        self.assertEqual((self.case, self.t, self.o), original)
        self.assertEqual(report['authority'], 'NONE')
        self.assertFalse(report['execution_enabled'])

    def test_absent_pin_cannot_inherit_successful_v1_handoff(self):
        self.case['expected_inventory_digest'] = None
        report = self.inspect()
        self.assertEqual(report['handoff']['status'], 'SUPPLIED_HANDOFF_CONSISTENT')
        self.assertEqual(report['status'], 'PINNED_HANDOFF_INCOMPLETE')
        self.assertIn('PROVENANCE:INVENTORY_PIN_UNAVAILABLE', report['blockers'])

    def test_remedy_and_review_holds_propagate(self):
        self.t['remedy']['residuals'][0]['state'] = 'UNRESOLVED'
        self.case['context']['principals'][6]['controller'] = None
        rebind(self.case['packet'], self.case['context'])
        report = self.inspect()
        self.assertIn('OPS1:RESIDUAL_INJURY_NOT_REPAIRED', report['blockers'])
        self.assertIn('REVIEW:REVIEW_CONTROL_UNKNOWN', report['blockers'])
        self.assertEqual(report['status'], 'PINNED_HANDOFF_INCOMPLETE')

    def test_changed_pin_bound_input_rejected_before_handoff(self):
        self.case = fixture(frozen_review=True)
        self.case['packet']['record']['claims'][0]['text'] = 'Changed claim'
        rebind(self.case['packet'], self.case['context'])
        with self.assertRaisesRegex(ReviewError, 'PINNED_REVIEW_INPUT_MISMATCH'):
            self.inspect()

    def test_stale_handoff_link_rejected(self):
        link = self.link()
        self.t['remedy']['residuals'][0]['state'] = 'UNRESOLVED'
        with self.assertRaisesRegex(ReviewError, 'handoff digest mismatch'):
            inspect_pinned_ops_handoff(**self.case, trace=self.t, ops_context=self.o, link=link)


class ProvenanceCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.case = fixture()
        self.packet = self.folder / 'packet.json'
        self.inventory = self.folder / 'inventory.json'
        self.mapping = self.folder / 'artifacts.json'
        self.packet.write_text(json.dumps({k: self.case[k] for k in ('packet', 'context')}), encoding='utf-8')
        self.inventory.write_text(json.dumps(self.case['inventory']), encoding='utf-8')
        key, raw = next(iter(self.case['artifacts'].items()))
        (self.folder / 'artifact.bin').write_bytes(raw)
        self.mapping.write_text(json.dumps({key: 'artifact.bin'}), encoding='utf-8')
        self.args = [str(self.packet), '--inventory', str(self.inventory),
                     '--inventory-sha256', self.case['expected_inventory_digest'],
                     '--as-of', self.case['as_of'], '--artifact-map', str(self.mapping)]

    def run_cli(self, expected, args=None):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/vanguard_provenance.py'),
                                 *(self.args if args is None else args)], cwd=self.folder,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report['authority'], 'NONE')
        self.assertFalse(report['execution_enabled'])
        return report

    def test_valid_and_missing_arguments_have_distinct_exits(self):
        self.assertEqual(self.run_cli(0)['status'], OK)
        report = self.run_cli(3, [str(self.packet)])
        self.assertIn('INVENTORY_PIN_UNAVAILABLE', report['blockers'])

    def test_missing_inventory_map_and_artifact_are_holds(self):
        for target in (self.inventory, self.mapping, self.folder / 'artifact.bin'):
            raw = target.read_bytes()
            target.unlink()
            self.run_cli(3)
            target.write_bytes(raw)

    def test_changed_artifact_bytes_are_rejected(self):
        (self.folder / 'artifact.bin').write_bytes(b'altered')
        self.assertIn('ARTIFACT_BYTES_MISMATCH', self.run_cli(2)['reason'])

    def test_duplicate_keys_nonfinite_unknown_and_oversized_json(self):
        raw = self.packet.read_bytes()
        for content in ('{"packet":{},"packet":{},"context":{}}', '{"value":NaN}',
                        '[1,2,3]', '{"packet":', '"' + 'x'*1048577 + '"'):
            with self.subTest(size=len(content)):
                self.packet.write_text(content, encoding='utf-8')
                self.run_cli(2)
        self.packet.write_bytes(raw)
        self.inventory.write_text('{"id":"first","id":"second"}', encoding='utf-8')
        self.assertEqual(self.run_cli(2)['reason'], 'DUPLICATE_JSON_KEY')

    def test_unpinned_inventory_does_not_trigger_artifact_reads(self):
        self.mapping.write_text('invalid JSON', encoding='utf-8')
        args = self.args[:]
        at = args.index('--inventory-sha256')
        del args[at:at+2]
        self.assertIn('INVENTORY_PIN_UNAVAILABLE', self.run_cli(3, args)['blockers'])

    def test_bad_pin_rejected_before_artifact_access(self):
        self.mapping.write_text('invalid JSON', encoding='utf-8')
        args = self.args[:]
        args[args.index('--inventory-sha256')+1] = 'a'*64
        self.assertEqual(self.run_cli(2, args)['reason'], 'INVENTORY_PIN_MISMATCH')


if __name__ == '__main__':
    unittest.main()
