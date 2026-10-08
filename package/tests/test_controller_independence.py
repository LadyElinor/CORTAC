"""Declared material control must not be hidden by fresh domain labels.

These are finite synthetic-input checks, not proof of real-world independence
or completeness of supplied material-control closures.
"""
from copy import deepcopy
from itertools import combinations, permutations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from wac_offline.__main__ import certificate, hashes
from wac_offline.io import read, report_hash
from wac_offline.reference import ConstraintTable, solve_reference, verify_reference
from wac_offline.solver import solve, validate_roster, verify_assignment


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'inputs/profile.extracted.json'
ROSTER = ROOT / 'fixtures/feasible.json'
SAT = 'SYNTHETICALLY_SATISFIED'
UNSAT = 'SYNTHETICALLY_INFEASIBLE'
COUNCIL_IDS = ('c1', 'c2', 'c3', 'c4')
COUNCIL_ROLES = ('council_1', 'council_2', 'council_3', 'council_4')
COMMON_CONTROLLER = 'synthetic-common-administrative-principal'


def records(roster):
    return {rec['id']: rec for rec in roster['records']}


def overlap_cases():
    """Replacement and additive reproductions, including the fixed proposer."""
    for additive in (False, True):
        suffix = 'additive' if additive else 'replacement'
        roster = read(ROSTER)
        for ident in COUNCIL_IDS:
            rec = records(roster)[ident]
            rec['material_controllers'] = (
                rec['material_controllers'] if additive else []) + [COMMON_CONTROLLER]
        yield 'council_' + suffix, roster
        for party in ('p', 'x'):
            roster = read(ROSTER)
            by_id = records(roster)
            auditor = by_id['u']
            auditor['material_controllers'] = sorted(set(
                (auditor['material_controllers'] if additive else []) +
                by_id[party]['material_controllers']))
            yield 'auditor_' + party + '_' + suffix, roster


class ControllerIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.base = read(ROSTER)
        self.witness = solve(self.base)['assignment']

    def assert_scope(self, result):
        self.assertEqual(result['authority'], 'NONE')
        self.assertIs(result['execution_enabled'], False)
        self.assertIs(result['simulation_only'], True)
        self.assertEqual(result['controller_closure'], 'SUPPLIED_UNVERIFIED')
        self.assertEqual(result['scope'], 'declared_synthetic_finite_constraint_model_only')

    def assert_satisfied(self, roster):
        validate_roster(roster)
        results = [engine(roster) for engine in (solve, solve_reference)]
        for result in results:
            self.assertEqual(result['status'], SAT, result)
            self.assert_scope(result)
            for verifier in (verify_assignment, verify_reference):
                self.assertEqual(verifier(roster, result['assignment']), [])
        return results

    def assert_rejected(self, roster):
        # Rejection is a semantic constraint failure, not a shape/parser error.
        validate_roster(roster)
        for engine in (solve, solve_reference):
            result = engine(roster)
            self.assertEqual(result['status'], UNSAT, result)
            self.assertIsNone(result['assignment'])
            self.assert_scope(result)
        for verifier in (verify_assignment, verify_reference):
            self.assertTrue(verifier(roster, self.witness), verifier.__name__)

    def test_original_positive_control(self):
        self.assert_satisfied(self.base)

    def test_replacement_and_additive_overlaps_rejected(self):
        for name, roster in overlap_cases():
            with self.subTest(case=name):
                self.assert_rejected(roster)

    def test_every_council_pair_rejected_without_relabeling_domains(self):
        for first, second in combinations(COUNCIL_IDS, 2):
            for additive in (False, True):
                with self.subTest(pair=(first, second), additive=additive):
                    roster = deepcopy(self.base)
                    by_id = records(roster)
                    for ident in (first, second):
                        rec = by_id[ident]
                        rec['material_controllers'] = (
                            rec['material_controllers'] if additive else []) + [COMMON_CONTROLLER]
                    self.assertEqual(len({by_id[i]['domain'] for i in COUNCIL_IDS}), 4)
                    self.assert_rejected(roster)
                    for verifier in (verify_assignment, verify_reference):
                        self.assertTrue(any('COUNCIL_MATERIAL_CONTROL_REUSE' in e
                                            for e in verifier(roster, self.witness)))

    def test_council_overlap_rejected_in_every_seat_permutation(self):
        roster = deepcopy(self.base)
        by_id = records(roster)
        for ident in ('c1', 'c4'):
            by_id[ident]['material_controllers'].append(COMMON_CONTROLLER)
        for council in permutations(COUNCIL_IDS):
            assignment = {**self.witness, **dict(zip(COUNCIL_ROLES, council))}
            with self.subTest(council=council):
                for verifier in (verify_assignment, verify_reference):
                    self.assertTrue(any('COUNCIL_MATERIAL_CONTROL_REUSE' in e
                                        for e in verifier(roster, assignment)))

    def test_auditor_conflicts_are_reported_for_both_fixed_and_selected_parties(self):
        for party, reference_reason in [('p', 'AUDITOR_PROPOSER_SEPARATION'),
                                         ('x', 'AUDITOR_EXECUTOR_SEPARATION')]:
            with self.subTest(party=party):
                roster = deepcopy(self.base)
                by_id = records(roster)
                by_id['u']['material_controllers'] += by_id[party]['material_controllers']
                self.assertNotEqual(by_id['u']['domain'], by_id[party]['domain'])
                self.assertTrue(any('AUDITOR_PROPOSER_EXECUTOR_CONFLICT' in e
                                    for e in verify_assignment(roster, self.witness)))
                self.assertTrue(any(reference_reason in e
                                    for e in verify_reference(roster, self.witness)))

    def test_existing_domain_and_appeal_negative_controls(self):
        for target, source, field in [('c2', 'c1', 'domain'), ('u', 'x', 'domain'),
                                      ('r1', 'x', 'material_controllers'),
                                      ('r2', 'r1', 'material_controllers')]:
            with self.subTest(target=target, source=source, field=field):
                roster = deepcopy(self.base)
                by_id = records(roster)
                by_id[target][field] = deepcopy(by_id[source][field])
                self.assert_rejected(roster)

    def test_distinct_additional_controllers_are_allowed(self):
        roster = deepcopy(self.base)
        for rec in roster['records']:
            rec['material_controllers'].append('synthetic-extra-controller-' + rec['id'])
        self.assert_satisfied(roster)

    def test_unconstrained_cross_role_overlap_is_not_globally_rejected(self):
        roster = deepcopy(self.base)
        by_id = records(roster)
        by_id['u']['material_controllers'] += by_id['n']['material_controllers']
        self.assert_satisfied(roster)

    def test_conflicting_unused_council_candidate_does_not_poison_roster(self):
        roster = deepcopy(self.base)
        extra = deepcopy(records(roster)['c1'])
        extra.update(id='00-conflicting-council', credential='synthetic-extra-credential',
                     process='synthetic-extra-process', domain='synthetic-extra-domain',
                     material_controllers=[records(roster)[i]['material_controllers'][0]
                                           for i in COUNCIL_IDS])
        roster['records'].append(extra)
        for result in self.assert_satisfied(roster):
            self.assertNotIn(extra['id'], result['assignment'].values())

    def test_independent_auditor_alternative_is_selected(self):
        for party in ('p', 'x'):
            with self.subTest(party=party):
                roster = deepcopy(self.base)
                by_id = records(roster)
                extra = deepcopy(by_id['u'])
                extra.update(id='z-independent-auditor', credential='synthetic-extra-credential',
                             process='synthetic-extra-process')
                roster['records'].append(extra)
                by_id['u']['material_controllers'] += by_id[party]['material_controllers']
                for result in self.assert_satisfied(roster):
                    self.assertEqual(result['assignment']['outcome_auditor'], extra['id'])

    def test_reference_checks_do_not_depend_on_primary_relations(self):
        with patch('wac_offline.solver._conflicts', side_effect=AssertionError('shared conflict')), \
             patch('wac_offline.solver._eligible', side_effect=AssertionError('shared eligibility')), \
             patch('wac_offline.solver._overlap', side_effect=AssertionError('shared controller relation')):
            for name, roster in overlap_cases():
                with self.subTest(case=name):
                    self.assertEqual(solve_reference(roster)['status'], UNSAT)
                    self.assertTrue(verify_reference(roster, self.witness))

    def test_primary_checks_do_not_depend_on_reference_relations(self):
        with patch.object(ConstraintTable, 'unary_errors', side_effect=AssertionError('shared unary')), \
             patch.object(ConstraintTable, 'pair_errors', side_effect=AssertionError('shared pair')):
            for name, roster in overlap_cases():
                with self.subTest(case=name):
                    self.assertEqual(solve(roster)['status'], UNSAT)
                    self.assertTrue(verify_assignment(roster, self.witness))


class ControllerCertificateTests(unittest.TestCase):
    def command(self, command, roster_path, certificate_path=None):
        args = [sys.executable, '-m', 'wac_offline', command,
                '--profile', str(PROFILE), '--roster', str(roster_path)]
        if certificate_path is not None:
            args += ['--certificate', str(certificate_path)]
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_cli_assembly_rejects_controller_overlaps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'roster.json'
            for name, roster in overlap_cases():
                with self.subTest(case=name):
                    path.write_text(json.dumps(roster), encoding='utf-8')
                    code, result = self.command('assemble', path)
                    self.assertEqual(code, 3, result)
                    self.assertEqual(result['status'], UNSAT)
                    self.assertIsNone(result['assignment'])
                    self.assertEqual(result['crosscheck']['primary_status'], UNSAT)
                    self.assertEqual(result['crosscheck']['reference_status'], UNSAT)
                    self.assertEqual(result['authority'], 'NONE')
                    self.assertIs(result['execution_enabled'], False)
                    self.assertEqual(result['controller_closure'], 'SUPPLIED_UNVERIFIED')

    def test_rebound_and_rehashed_certificate_cannot_hide_controller_conflicts(self):
        original = certificate(PROFILE, ROSTER, 100000)
        with tempfile.TemporaryDirectory() as directory:
            roster_path = Path(directory) / 'roster.json'
            cert_path = Path(directory) / 'certificate.json'
            for name, roster in overlap_cases():
                with self.subTest(case=name):
                    roster_path.write_text(json.dumps(roster), encoding='utf-8')
                    altered = deepcopy(original)
                    altered['input_byte_hashes'] = hashes(PROFILE, roster_path)
                    altered['report_body_sha256'] = report_hash({
                        key: value for key, value in altered.items() if key != 'report_body_sha256'})
                    cert_path.write_text(json.dumps(altered), encoding='utf-8')
                    code, result = self.command('verify', roster_path, cert_path)
                    self.assertEqual(code, 2, result)
                    self.assertEqual(result['status'], 'SYNTHETIC_WITNESS_INVALID')
                    self.assertTrue(any(e.startswith('PRIMARY:') for e in result['errors']))
                    self.assertTrue(any(e.startswith('REFERENCE:') for e in result['errors']))
                    self.assertNotIn('REPORT_BODY_HASH_MISMATCH', result['errors'])
                    self.assertNotIn('LOCAL_INPUT_BYTE_HASH_MISMATCH', result['errors'])
                    self.assertEqual(result['authority'], 'NONE')
                    self.assertIs(result['execution_enabled'], False)
                    self.assertEqual(result['controller_closure'], 'SUPPLIED_UNVERIFIED')

    def test_cli_positive_control_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            code, result = self.command('assemble', ROSTER)
            self.assertEqual(code, 0, result)
            self.assertEqual(result['status'], SAT)
            cert_path = Path(directory) / 'certificate.json'
            cert_path.write_text(json.dumps(result), encoding='utf-8')
            code, result = self.command('verify', ROSTER, cert_path)
            self.assertEqual(code, 0, result)
            self.assertEqual(result['status'], 'SYNTHETIC_WITNESS_VALID')
            self.assertEqual(result['errors'], [])


if __name__ == '__main__':
    unittest.main()
