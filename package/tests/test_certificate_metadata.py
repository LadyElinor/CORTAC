"""Rehashed scope claims must not bypass the certificate verifier."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from wac_offline.io import report_hash
from wac_offline.__main__ import certificate, verify_certificate

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'inputs/profile.extracted.json'
ROSTER = ROOT / 'fixtures/feasible.json'


def rehash(value):
    value['report_body_sha256'] = report_hash({k:v for k,v in value.items() if k != 'report_body_sha256'})
    return value


class CertificateMetadataTests(unittest.TestCase):
    def setUp(self):
        self.original = certificate(PROFILE, ROSTER, 100000)

    def assert_rejected_cli(self, path, value):
        altered = deepcopy(self.original)
        owner = altered
        for key in path[:-1]: owner = owner[key]
        owner[path[-1]] = value
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)/'certificate.json'
            target.write_text(json.dumps(rehash(altered)), encoding='utf-8')
            result = subprocess.run([sys.executable, '-m', 'wac_offline', 'verify',
                '--profile', str(PROFILE), '--roster', str(ROSTER), '--certificate', str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(json.loads(result.stdout)['status'], 'SYNTHETIC_WITNESS_INVALID')

    def test_rehashed_external_audit_claim_rejected(self):
        self.assert_rejected_cli(('crosscheck', 'external_independent_audit'), True)

    def test_rehashed_ballot_verification_claim_rejected(self):
        self.assert_rejected_cli(('decision_structure', 'actual_ballots_verified'), True)

    def test_rehashed_verified_appeal_capacity_claim_rejected(self):
        self.assert_rejected_cli(('appeal_structure', 'capacity_is_declared_only'), False)

    def test_boolean_and_numeric_types_are_exact(self):
        for path, value in [(('crosscheck','external_independent_audit'), 0),
                            (('crosscheck','witness_checked_by_both'), 1),
                            (('decision_structure','actual_ballots_verified'), 0),
                            (('decision_structure','seats'), 4.0),
                            (('appeal_structure','capacity_is_declared_only'), 1),
                            (('profile_validation','execution_enabled'), 0),
                            (('crosscheck','budget_per_engine'), True)]:
            with self.subTest(path=path): self.assert_rejected_cli(path, value)

    def test_other_scope_and_model_claims_rejected(self):
        mutations = [(('hash_scope',), 'signed_adoption'),
            (('report_serialization',), 'RFC8785'), (('search_method',), 'constitutional_lottery'),
            (('supported_additions',), []), (('crosscheck','shared_component'), 'nothing'),
            (('crosscheck','witness_checked_by_both'), False),
            (('decision_structure','approvals_required'), 2),
            (('appeal_structure','distinct_domains_required'), 2),
            (('profile_validation','not_checked'), []), (('profile_validation','authority_status'), 'ACTIVE'),
            (('case_id',), 'another-case'), (('search_exhausted',), True)]
        for path, value in mutations:
            with self.subTest(path=path): self.assert_rejected_cli(path, value)

    def test_unknown_fields_cannot_add_nested_claims(self):
        for path in [(), ('crosscheck',), ('decision_structure',), ('appeal_structure',), ('profile_validation',)]:
            altered = deepcopy(self.original); target = altered
            for key in path: target = target[key]
            target['real_independence_verified'] = True
            result = verify_certificate(PROFILE, ROSTER, rehash(altered))
            self.assertEqual(result['status'], 'SYNTHETIC_WITNESS_INVALID', path)

    def test_missing_claims_are_rejected(self):
        for path in [('crosscheck','external_independent_audit'), ('decision_structure','actual_ballots_verified'),
                     ('appeal_structure','capacity_is_declared_only'), ('profile_validation','not_checked')]:
            altered = deepcopy(self.original); del altered[path[0]][path[1]]
            self.assertEqual(verify_certificate(PROFILE, ROSTER, rehash(altered))['status'], 'SYNTHETIC_WITNESS_INVALID')

    def test_contradictory_search_metadata_is_rejected(self):
        for path, value in [(('crosscheck','primary_status'), 'SYNTHETICALLY_INFEASIBLE'),
                            (('crosscheck','primary_nodes'), -1),
                            (('crosscheck','budget_per_engine'), 99999),
                            (('nodes',), 0), (('candidate_counts','appeal_1'), True)]:
            with self.subTest(path=path): self.assert_rejected_cli(path, value)

    def test_legacy_report_contract_requires_regeneration(self):
        for version in ('0.2.0', '0.2.1'):
            with self.subTest(version=version):
                old = deepcopy(self.original)
                old['software_version'] = version
                old['supported_additions'] = [
                    'conservative_material_overlap_exclusion_for_assessors',
                    'pairwise_material_control_disjoint_appeal_panel']
                result = verify_certificate(PROFILE, ROSTER, rehash(old))
                self.assertEqual(result['status'], 'SYNTHETIC_WITNESS_INVALID')
                self.assertIn('UNSUPPORTED_REPORT_SOFTWARE_VERSION', result['errors'])
                self.assertIn('INVALID_REPORT_BOUNDARY:supported_additions', result['errors'])
        self.assertEqual(verify_certificate(PROFILE, ROSTER, self.original)['status'], 'SYNTHETIC_WITNESS_VALID')

    def test_current_version_cannot_omit_new_controller_contract(self):
        self.assert_rejected_cli(('supported_additions',), [
            'conservative_material_overlap_exclusion_for_assessors',
            'pairwise_material_control_disjoint_appeal_panel'])


if __name__ == '__main__': unittest.main()
