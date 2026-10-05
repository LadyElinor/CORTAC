"""Differential, mutation, CLI-contract, and lottery checks for software 0.2.0."""
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import json
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from wac_offline.io import InputError, read, report_hash
from wac_offline.solver import solve, verify_assignment, ALL_ROLES
from wac_offline.reference import ConstraintTable, solve_reference, verify_reference
from wac_offline.__main__ import certificate, verify_certificate, exit_code, hashes
from wac_offline.lottery import freeze_roll, simulate, uniform_index, SeedStream

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'inputs/profile.extracted.json'
SAT, UNSAT, INCOMPLETE = 'SYNTHETICALLY_SATISFIED', 'SYNTHETICALLY_INFEASIBLE', 'SYNTHETIC_SEARCH_INCOMPLETE'


def fixture(name='feasible'):
    return read(ROOT / ('fixtures/' + name + '.json'))


def byid(r, ident):
    return next(a for a in r['records'] if a['id'] == ident)


def nominations(r):
    # Test helper only. Real simulated inputs supply an explicit nomination map.
    t = ConstraintTable(r)
    out = {}
    for role in ALL_ROLES:
        out[role] = {}
        for ident in reversed(t.domains[role]):
            out[role][t.records[ident]['domain']] = ident
    return out


class ReferenceTests(unittest.TestCase):
    def compare(self, r):
        a, b = solve(r, 50000), solve_reference(r, 50000)
        self.assertNotEqual(a['status'], INCOMPLETE, 'test case exceeded primary budget')
        self.assertNotEqual(b['status'], INCOMPLETE, 'test case exceeded reference budget')
        self.assertEqual(a['status'], b['status'])
        for result in (a, b):
            if result['assignment'] is not None:
                self.assertEqual(verify_assignment(r, result['assignment']), [])
                self.assertEqual(verify_reference(r, result['assignment']), [])

    def test_all_imported_assignment_fixtures(self):
        for name in ('feasible', 'clone_insufficiency', 'same_controller_appeals',
                     'unknown_dimensions', 'reviewer_shortage', 'joint_backtracking'):
            with self.subTest(name=name):
                self.compare(fixture(name))

    def test_reference_does_not_call_primary_constraints_or_search(self):
        with patch('wac_offline.solver._conflicts', side_effect=AssertionError('shared conflict')), \
             patch('wac_offline.solver._eligible', side_effect=AssertionError('shared eligibility')), \
             patch('wac_offline.solver.solve', side_effect=AssertionError('shared search')), \
             patch('wac_offline.solver.verify_assignment', side_effect=AssertionError('shared verifier')):
            result = solve_reference(fixture())
            self.assertEqual(result['status'], SAT)
            self.assertEqual(verify_reference(fixture(), result['assignment']), [])

    def test_independent_check_catches_shared_relation_fault(self):
        r = fixture()
        byid(r, 'e')['credential'] = byid(r, 'p')['credential']
        with patch('wac_offline.solver._conflicts', return_value=[]):
            a = solve(r)
            self.assertEqual(a['status'], SAT)
            self.assertEqual(verify_assignment(r, a['assignment']), [])
            self.assertTrue(verify_reference(r, a['assignment']))

    def test_report_rejects_implementation_disagreement(self):
        with patch('wac_offline.solver._conflicts', return_value=['INJECTED_FALSE_REJECTION']):
            c = certificate(PROFILE, ROOT/'fixtures/feasible.json', 10000)
        self.assertEqual(c['status'], 'SYNTHETIC_IMPLEMENTATIONS_DISAGREE')
        self.assertEqual(exit_code(c), 5)
        self.assertIsNone(c['assignment'])

    def test_all_144_panel_permutations(self):
        r = fixture(); a = solve(r)['assignment']
        for council in permutations(['c1', 'c2', 'c3', 'c4']):
            for appeal in permutations(['r1', 'r2', 'r3']):
                candidate = {**a, **dict(zip(ALL_ROLES[2:6], council)), **dict(zip(ALL_ROLES[9:], appeal))}
                self.assertEqual(verify_assignment(r, candidate), [])
                self.assertEqual(verify_reference(r, candidate), [])

    def test_every_role_identity_substitution(self):
        r = fixture(); a = solve(r)['assignment']
        for role in ALL_ROLES:
            for record in r['records']:
                changed = {**a, role: record['id']}
                self.assertEqual(bool(verify_assignment(r, changed)), bool(verify_reference(r, changed)),
                                 (role, record['id']))

    def test_200_seeded_structural_mutations(self):
        rng = random.Random(20261005)
        counts = {SAT: 0, UNSAT: 0}
        for index in range(200):
            r = fixture()
            if index % 4 == 0:
                extra = deepcopy(byid(r, 'e'))
                extra.update(id='extra', credential='extra-credential', process='extra-process',
                             domain='extra-domain', material_controllers=['extra-owner'],
                             qualified_roles=['epistemic_assessor', 'normative_assessor', 'outcome_auditor'])
                r['records'].append(extra)
            for _ in range(1 + index % 3):
                a, b = rng.sample(r['records'], 2)
                choice = rng.randrange(9)
                if choice < 3:
                    key = ('domain', 'credential', 'process')[choice]; a[key] = b[key]
                elif choice == 3:
                    a['material_controllers'] = sorted(set(a['material_controllers'] + b['material_controllers']))
                elif choice == 4:
                    a['conflicts'] = sorted(set(a['conflicts'] + [b['id']]))
                elif choice == 5:
                    a['capacity'] = rng.randrange(2)
                elif choice == 6:
                    a['valid_until'] = rng.choice([1000, 1500, 2000, 999999])
                elif choice == 7:
                    role1, role2 = rng.sample(list(ALL_ROLES) + ['proposer'], 2)
                    r['distinct_dependencies'].append({'roles': [role1, role2], 'dimensions': ['runtime']})
                    if rng.randrange(2):
                        a['dependencies']['runtime'] = None
                else:
                    r[rng.choice(['opposing_party_ids', 'prior_participant_ids', 'beneficiary_ids'])] = [a['id']]
            with self.subTest(index=index):
                self.compare(r)
                counts[solve_reference(r)['status']] += 1
        self.assertGreater(counts[SAT], 10)
        self.assertGreater(counts[UNSAT], 10)

    def test_unknown_fixed_controller_and_seat_specific_dimension(self):
        for field in ('material_control_known', 'domain_verified'):
            r = fixture(); byid(r, 'p')[field] = False; self.compare(r)
        for group, ids in [('council', ['c2', 'c3', 'c4']), ('appeal', ['r2', 'r3'])]:
            r = fixture()
            r['distinct_dependencies'] = [{'roles': [group+'_1', 'proposer'], 'dimensions': ['runtime']}]
            for ident in ids: byid(r, ident)['dependencies']['runtime'] = None
            self.compare(r)

    def test_reference_budget_boundary(self):
        r = fixture(); complete = solve_reference(r)
        self.assertEqual(solve_reference(r, complete['nodes'])['status'], SAT)
        self.assertEqual(solve_reference(r, complete['nodes']-1)['status'], INCOMPLETE)
        self.assertEqual(solve_reference(r, 0)['status'], INCOMPLETE)
        for invalid in (-1, True, 1.5):
            with self.assertRaises(InputError): solve_reference(r, invalid)


class LotteryTests(unittest.TestCase):
    def freeze(self, r, picks=None):
        return freeze_roll(r, nominations(r) if picks is None else picks, {'test_only': 'bytes'})

    def run_draw(self, r, frozen=None, seed='00'*32):
        return simulate(r, self.freeze(r) if frozen is None else frozen, seed, {'test_only': 'bytes'})

    def test_seeded_replay_and_complete_trace(self):
        r = fixture(); out = self.run_draw(r)
        self.assertEqual(out, self.run_draw(r))
        self.assertEqual(out['status'], 'SYNTHETIC_LOTTERY_COMPLETE')
        self.assertEqual(len(out['trace']), 12)
        self.assertEqual(verify_reference(r, out['assignment']), [])
        self.assertEqual(out['redraws'], 0)

    def test_draws_council_and_appeal_without_replacement(self):
        for seed in range(20):
            out = self.run_draw(fixture(), seed=f'{seed:064x}')
            for group, count in [('council', 4), ('appeal', 3)]:
                domains = [e['selected_domain'] for e in out['trace'] if e['role'].startswith(group)]
                self.assertEqual(len(set(domains)), count)

    def test_fifty_copies_do_not_change_domain_draws(self):
        r = fixture(); frozen = self.freeze(r)
        many = deepcopy(r)
        for i in range(50):
            rec = deepcopy(byid(many, 'c1'))
            rec.update(id=f'copy-{i}', credential=f'copy-credential-{i}', process=f'copy-process-{i}')
            many['records'].append(rec)
        other = self.freeze(many, frozen['nominations'])
        for seed in range(20):
            before = self.run_draw(r, frozen, f'{seed:064x}')
            after = self.run_draw(many, other, f'{seed:064x}')
            self.assertEqual(before['trace'], after['trace'])

    def test_exact_rejection_sampler_counts(self):
        # Exhaust the accepted portion of an 8-bit uniform source, not a
        # statistical p-value based on a chosen pseudorandom seed.
        for size in (1, 2, 3, 5, 7, 13):
            limit = 256 - 256 % size
            counts = [0] * size
            for word in range(limit):
                counts[uniform_index(size, lambda w=word: w, bits=8)] += 1
            self.assertEqual(len(set(counts)), 1)
        words = iter([255, 254])  # For 3 choices, 255 must be rejected.
        self.assertEqual(uniform_index(3, lambda: next(words), bits=8), 2)

    def test_invalid_nomination_missing_extra_unqualified(self):
        r = fixture()
        for change in ('missing', 'extra', 'wrong'):
            p = nominations(r)
            if change == 'missing': del p['council_1']['d1']
            elif change == 'extra': p['council_1']['invented'] = 'c1'
            else: p['council_1']['d1'] = 'p'
            with self.assertRaises(InputError): self.freeze(r, p)

    def test_changed_roll_or_bytes_rejected_even_after_rehash(self):
        r = fixture(); frozen = self.freeze(r)
        for key, value in [('authority', 'ACTIVE'), ('role_order', list(reversed(ALL_ROLES))),
                           ('seed_procedure', 'pick-favorite'), ('simulation_only', 1), ('execution_enabled', 0)]:
            altered = deepcopy(frozen); altered[key] = value
            altered['roll_body_sha256'] = report_hash({k:v for k,v in altered.items() if k != 'roll_body_sha256'})
            with self.assertRaises(InputError): self.run_draw(r, altered)
        with self.assertRaises(InputError): simulate(r, frozen, '00'*32, {'test_only': 'changed'})

    def test_dead_end_is_not_infeasible_and_has_no_retry(self):
        r = fixture('joint_backtracking')
        self.assertEqual(solve_reference(r)['status'], SAT)
        out = self.run_draw(r, seed='00'*32)
        # This pinned seed chooses the d5 evidence nominee and strands appeals.
        self.assertEqual(out['status'], 'SYNTHETIC_LOTTERY_DEAD_END')
        self.assertIsNone(out['assignment'])
        self.assertEqual(out['redraws'], 0)
        self.assertEqual(exit_code(out), 4)

    def test_seed_validation(self):
        for value in ('', 'a', 'G'*64, '00'*31, None, 0):
            with self.assertRaises(InputError): SeedStream(value)
        self.assertNotEqual(SeedStream('00'*32).word(), SeedStream('01'*32).word())

    def test_dual_verification_failure_cannot_complete(self):
        with patch('wac_offline.lottery.verify_assignment', return_value=['injected']):
            out = self.run_draw(fixture())
        self.assertEqual(out['status'], 'SYNTHETIC_IMPLEMENTATIONS_DISAGREE')
        self.assertIsNone(out['assignment'])
        self.assertEqual(exit_code(out), 5)


class ReportAndExitTests(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, '-m', 'wac_offline', *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True)

    def test_exit_mapping_unknown_fails_closed(self):
        for status, expected in [(SAT, 0), (UNSAT, 3), (INCOMPLETE, 4),
                                 ('SYNTHETIC_WITNESS_INVALID', 2), ('UNRECOGNIZED', 2),
                                 ('SYNTHETIC_IMPLEMENTATIONS_DISAGREE', 5)]:
            self.assertEqual(exit_code({'status': status}), expected)
        self.assertEqual(exit_code({}), 2)

    def test_infeasible_and_incomplete_cli_nonzero(self):
        for name, budget, code, status in [('clone_insufficiency', 100000, 3, UNSAT),
                                          ('feasible', 0, 4, INCOMPLETE), ('feasible', 10000, 0, SAT)]:
            p = self.command('assemble', '--profile', PROFILE, '--roster', ROOT/f'fixtures/{name}.json', '--max-nodes', budget)
            self.assertEqual(p.returncode, code, p.stderr)
            self.assertEqual(json.loads(p.stdout)['status'], status)

    def test_invalid_and_legacy_witness_exit_two(self):
        p = self.command('verify', '--profile', PROFILE, '--roster', ROOT/'fixtures/feasible.json',
                         '--certificate', ROOT/'results/feasible.json')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)['status'], 'SYNTHETIC_WITNESS_INVALID')

    def test_scope_fields_cannot_be_stripped_or_promoted(self):
        c = certificate(PROFILE, ROOT/'fixtures/feasible.json', 10000)
        for key, value in [('controller_closure', 'VERIFIED'), ('scope', 'real_world'),
                           ('status', 'FEASIBLE'), ('not_established', []), ('simulation_only', False)]:
            altered = deepcopy(c); altered[key] = value
            altered['report_body_sha256'] = report_hash({k:v for k,v in altered.items() if k != 'report_body_sha256'})
            out = verify_certificate(PROFILE, ROOT/'fixtures/feasible.json', altered)
            self.assertEqual(out['status'], 'SYNTHETIC_WITNESS_INVALID')

    def test_negative_governance_exit_three(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'split.json'; p.write_text(json.dumps({'predecessor': [1,1], 'successors': {'s': [2,1]}}))
            out = self.command('split', p)
            self.assertEqual(out.returncode, 3)
            self.assertEqual(json.loads(out.stdout)['status'], 'SYNTHETIC_ARITHMETIC_FAILS')

    def test_failed_assignment_cannot_become_successful_draft(self):
        out = self.command('draft-founding', '--profile', PROFILE, '--roster', ROOT/'fixtures/clone_insufficiency.json')
        self.assertEqual(out.returncode, 3)
        self.assertIsNone(json.loads(out.stdout)['proposed_assignment'])

    def test_cli_lottery_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'nominations.json'; p.write_text(json.dumps(nominations(fixture())))
            frozen = self.command('prepare-lottery', '--profile', PROFILE, '--roster', ROOT/'fixtures/feasible.json', '--nominations', p)
            self.assertEqual(frozen.returncode, 0, frozen.stdout)
            roll = Path(d)/'roll.json'; roll.write_text(frozen.stdout)
            draw = self.command('lottery', '--profile', PROFILE, '--roster', ROOT/'fixtures/feasible.json', '--roll', roll, '--seed', '00'*32)
            self.assertEqual(draw.returncode, 0, draw.stdout)
            self.assertEqual(json.loads(draw.stdout)['status'], 'SYNTHETIC_LOTTERY_COMPLETE')


if __name__ == '__main__':
    unittest.main()
