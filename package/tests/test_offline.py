from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from wac_offline.io import InputError, loads, read, report_hash
from wac_offline.profile import validate_profile
from wac_offline.solver import solve, verify_assignment, ALL_ROLES
from wac_offline.governance import rational, split_check, frozen_vote, consequential_ballot
from wac_offline.__main__ import certificate, verify_certificate, founding_proposal

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'inputs' / 'profile.extracted.json'

def fixture(name='feasible'):
    return read(ROOT / 'fixtures' / (name + '.json'))

def byid(roster, ident):
    return next(r for r in roster['records'] if r['id'] == ident)

class ProfileTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual(validate_profile(read(PROFILE))['status'], 'VALID_SUPPORTED_PROFILE')
    def test_duplicate_key_nested(self):
        with self.assertRaises(InputError): loads('{"a":{"x":1,"x":2}}')
    def test_nonfinite_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value), self.assertRaises(InputError): loads(value)
    def test_key_order_irrelevant(self):
        p = read(PROFILE)
        self.assertFalse(validate_profile(dict(reversed(list(p.items()))))['errors'])
    def test_unknown_and_missing_field(self):
        p = read(PROFILE); p['new_required'] = True; del p['roles']['selection']
        codes = {e['code'] for e in validate_profile(p)['errors']}
        self.assertTrue({'UNSUPPORTED_FIELD','MISSING_FIELD'} <= codes)
    def test_template_cannot_activate(self):
        p = read(PROFILE); p['activation']['execution_enabled'] = True
        result = validate_profile(p)
        self.assertTrue(result['errors']); self.assertFalse(result['execution_enabled'])
    def test_bool_not_integer(self):
        p = read(PROFILE); p['governance']['votes_per_unit'] = True
        self.assertTrue(validate_profile(p)['errors'])
    def test_float_not_integer(self):
        p = read(PROFILE); p['governance']['votes_per_unit'] = 1.0
        self.assertTrue(validate_profile(p)['errors'])
    def test_version_and_threshold_changes_fail_closed(self):
        for key, val in [('schema_version','0.3.0'), ('status','RATIFIED')]:
            p = read(PROFILE); p[key] = val
            self.assertTrue(validate_profile(p)['errors'])
        p = read(PROFILE); p['consequential_decision']['approvals_required'] = 2
        self.assertTrue(validate_profile(p)['errors'])

class SolverTests(unittest.TestCase):
    def test_feasible_eight_domain_model(self):
        r = fixture(); result = solve(r)
        self.assertEqual(result['status'], 'SYNTHETICALLY_SATISFIED')
        self.assertEqual(set(result['assignment']), set(ALL_ROLES))
        self.assertEqual(verify_assignment(r,result['assignment']), [])
        self.assertFalse(result['execution_enabled'])
        self.assertEqual(len({x['domain'] for x in r['records']}), 8)
    def test_clone_insufficiency(self):
        result = solve(fixture('clone_insufficiency'))
        self.assertEqual(result['status'],'SYNTHETICALLY_INFEASIBLE')
        self.assertIn('FEWER_THAN_FOUR_ELIGIBLE_COUNCIL_DOMAINS',result['diagnostics'])
    def test_same_controller_fresh_domains_fail(self):
        result = solve(fixture('same_controller_appeals'))
        self.assertEqual(result['status'],'SYNTHETICALLY_INFEASIBLE')
        self.assertEqual(result['evidence_kind'],'EXHAUSTIVE_FINITE_SEARCH')
        self.assertTrue(any('APPEAL_EXCLUDED_INTEREST' in x for x in result['dynamic_rejections']))
    def test_unknown_dimension_and_shortage(self):
        for name in ('unknown_dimensions','reviewer_shortage'):
            self.assertEqual(solve(fixture(name))['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_bounded_search_not_infeasible(self):
        for limit in (0,1,5):
            result = solve(fixture(), limit)
            self.assertEqual(result['status'],'SYNTHETIC_SEARCH_INCOMPLETE')
            self.assertFalse(result['search_exhausted'])
    def test_exhaustion_at_exact_success_node_count(self):
        result = solve(fixture())
        self.assertEqual(solve(fixture(),result['nodes'])['status'],'SYNTHETICALLY_SATISFIED')
        self.assertEqual(solve(fixture(),result['nodes']-1)['status'],'SYNTHETIC_SEARCH_INCOMPLETE')
    def test_joint_backtracking(self):
        result = solve(fixture('joint_backtracking'))
        self.assertEqual(result['status'],'SYNTHETICALLY_SATISFIED')
        self.assertEqual(result['assignment']['epistemic_assessor'],'e')
        self.assertTrue(any('APPEAL_EXCLUDED_INTEREST' in x for x in result['dynamic_rejections']))
    def test_deterministic_against_record_order(self):
        r = fixture(); expected = solve(r); r['records'].reverse()
        self.assertEqual(solve(r),expected)
    def test_unregistered_executor(self):
        for ids in ([], ['p']):
            r = fixture(); r['registered_executor_ids'] = ids
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_no_duplicate_case_identity(self):
        r = fixture(); a = solve(r)['assignment']; a['normative_assessor'] = a['epistemic_assessor']
        self.assertTrue(any('CASE_IDENTITY_REUSE' in x for x in verify_assignment(r,a)))
    def test_four_council_domains_required(self):
        r = fixture(); byid(r,'c4')['domain'] = 'd3'
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_credential_process_separation(self):
        for target, field, other in [('a','credential','e'),('a','process','u'),('x','credential','c1')]:
            r = fixture(); byid(r,target)[field] = byid(r,other)[field]
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_separate_authorizer_entity(self):
        r=fixture(); byid(r,'a')['kind']='agent'
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_assessor_identity_credential_control(self):
        for field in ('credential','domain'):
            r=fixture(); byid(r,'e')[field]=byid(r,'p')[field]
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_auditor_cannot_be_prior_participant(self):
        r=fixture(); r['prior_participant_ids']=['u']
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_appeal_excludes_all_prior_controller_interests(self):
        for prior in ('p','e','n','c1','c4','a','x','u'):
            r=fixture(); byid(r,'r1')['material_controllers'].extend(byid(r,prior)['material_controllers'])
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_appeal_excludes_appellant_opposition_beneficiary(self):
        for key in ('appellant_ids','opposing_party_ids','beneficiary_ids'):
            r=fixture(); r[key]=['r1']
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_appeal_pairwise_control_overlap(self):
        r=fixture(); byid(r,'r2')['material_controllers']+=byid(r,'r1')['material_controllers']
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_unknown_material_control(self):
        for ident in ('r1','p','c1'):
            r=fixture(); byid(r,ident)['material_control_known']=False
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_unknown_domain(self):
        r=fixture(); byid(r,'c1')['domain_verified']=False
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_expiry_and_capacity(self):
        for ident,key,val in [('e','valid_until',1000),('r1','valid_until',2000),('u','capacity',0),('p','capacity',0)]:
            r=fixture(); byid(r,ident)[key]=val
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_explicit_conflict_symmetric(self):
        for a,b in [('e','n'),('n','e'),('r1','p'),('p','r1')]:
            r=fixture(); byid(r,a)['conflicts']=[b]
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_purpose_specific_dependency_conflict(self):
        r=fixture(); r['distinct_dependencies']=[{'roles':['epistemic_assessor','normative_assessor'], 'dimensions':['runtime']}]
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_SATISFIED')
        byid(r,'n')['dependencies']['runtime']=byid(r,'e')['dependencies']['runtime']
        self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
    def test_required_dimensions_cannot_be_silently_removed(self):
        r=fixture(); r['required_dependencies']={}
        with self.assertRaises(InputError): solve(r)
    def test_unknown_schema_and_bool_capacity(self):
        for change in ('unknown','bool','duplicate','false_simulation'):
            r=fixture()
            if change=='unknown': r['ignored']=True
            elif change=='bool': byid(r,'e')['capacity']=True
            elif change=='duplicate': r['records'].append(deepcopy(r['records'][0]))
            else: r['simulation_only']=False
            with self.assertRaises(InputError): solve(r)
    def test_witness_tamper_detected_without_search(self):
        r=fixture(); a=solve(r)['assignment']; a['appeal_1']='c1'
        self.assertTrue(verify_assignment(r,a))
        del a['council_4']; self.assertEqual(verify_assignment(r,a),['ASSIGNMENT_ROLE_SET_MISMATCH'])
    def test_nonuniform_concrete_seat_rule_disables_invalid_symmetry(self):
        r=fixture(); r['distinct_dependencies']=[{'roles':['council_1','proposer'], 'dimensions':['runtime']}]
        byid(r,'c1')['dependencies']['runtime']=byid(r,'p')['dependencies']['runtime']
        result=solve(r)
        self.assertEqual(result['status'],'SYNTHETICALLY_SATISFIED')
        self.assertNotEqual(result['assignment']['council_1'],'c1')
    def test_unknown_excluded_party_domain(self):
        for ident in ('p','r1'):
            r=fixture()
            if ident=='r1': r['opposing_party_ids']=['r1']
            for field,value in [('domain',None),('domain_verified',False)]:
                modified=deepcopy(r); byid(modified,ident)[field]=value
                self.assertEqual(solve(modified)['status'],'SYNTHETICALLY_INFEASIBLE')
                a=solve(fixture())['assignment']
                self.assertTrue(verify_assignment(modified,a))
    def test_seat_specific_required_dimension_does_not_create_false_domain_bound(self):
        for group,role,unknown_ids in [('council','council_1',['c2','c3','c4']),('appeal','appeal_1',['r2','r3'])]:
            r=fixture(); a=solve(r)['assignment']
            r['distinct_dependencies']=[{'roles':[role,'proposer'],'dimensions':['runtime']}]
            for ident in unknown_ids: byid(r,ident)['dependencies']['runtime']=None
            self.assertEqual(verify_assignment(r,a),[])
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_SATISFIED')
    def test_fixed_proposer_required_dimensions_and_qualification(self):
        for variant in ('dimension','qualification'):
            r=fixture(); a=solve(r)['assignment']
            if variant=='dimension':
                r['required_dependencies']['proposer']=['runtime']
                byid(r,'p')['dependencies']['runtime']=None
            else: byid(r,'p')['qualified_roles']=[]
            self.assertEqual(solve(r)['status'],'SYNTHETICALLY_INFEASIBLE')
            self.assertTrue(verify_assignment(r,a))
    def test_bad_search_bounds(self):
        for v in (-1, True, 1.5):
            with self.assertRaises(InputError): solve(fixture(),v)

class GovernanceTests(unittest.TestCase):
    def test_split_exact_thirds(self):
        self.assertTrue(split_check([1,1],{'a':[1,3],'b':[1,3],'c':[1,3]})['conserved'])
        self.assertFalse(split_check([1,1],{'a':[1,3],'b':[1,3]})['conserved'])
    def test_weight_invalid(self):
        for v in ([1,0],[-1,3],[True,1],[0.5,1],[1,False]):
            with self.assertRaises(InputError): rational(v)
    def test_split_preserves_four_fifths(self):
        v=frozen_vote(**fixture('frozen_vote'))
        self.assertEqual(v['cell_denominator'],[5,1]); self.assertEqual(v['cell_yes'],[4,1])
        self.assertTrue(v['both_chambers_pass'])
    def test_abstention_preserves_denominator(self):
        v=fixture('frozen_vote'); v['yes_domains']=['d1','d2','d3']; v['yes_cells']=['a','b','c']
        r=frozen_vote(**v); self.assertFalse(r['both_chambers_pass']); self.assertEqual(r['domain_denominator'],5)
    def test_duplicate_unknown_votes_rejected(self):
        for key,val in [('yes_domains',['d1','d1']),('yes_domains',['unknown']),('yes_cells',['a','a']),('yes_cells',['unknown'])]:
            v=fixture('frozen_vote'); v[key]=val
            with self.assertRaises(InputError): frozen_vote(**v)
    def test_empty_ledger_rejected(self):
        v=fixture('frozen_vote'); v['cell_weights']={}; v['yes_cells']=[]
        with self.assertRaises(InputError): frozen_vote(**v)
    def test_three_approvals_and_all_four_seats(self):
        self.assertTrue(consequential_ballot(['a','b','c','d'],['a','b','c'], False, fixture('decision_record'), fixture('protected_limits'))['structurally_passes'])
        self.assertFalse(consequential_ballot(['a','b','c'],['a','b','c'], False, fixture('decision_record'), fixture('protected_limits'))['structurally_passes'])
        self.assertFalse(consequential_ballot(['a','b','c','d'],['a','b'], False, fixture('decision_record'), fixture('protected_limits'))['structurally_passes'])
        self.assertFalse(consequential_ballot(['a','b','c','d'],['a','b','c','d'],True, fixture('decision_record'), fixture('protected_limits'))['structurally_passes'])
    def test_invalid_identifier_types_rejected(self):
        for seats,yes,flag in [('abcd','abc',False),(['a','b','c','d'],['a','b','c'],[]),(['','b','c','d'],['','b','c'],False)]:
            with self.assertRaises(InputError): consequential_ballot(seats,yes,flag)
        v=fixture('frozen_vote'); v['domain_roll']=[1,2,3,4,5]; v['yes_domains']=[1,2,3,4]
        with self.assertRaises(InputError): frozen_vote(**v)
        with self.assertRaises(InputError): split_check([1,1],{1:[1,1]})
    def test_bool_protected_flag(self):
        with self.assertRaises(InputError): consequential_ballot(['a','b','c','d'],['a','b','c'],0)

class CertificateTests(unittest.TestCase):
    def make(self): return certificate(PROFILE,ROOT/'fixtures'/'feasible.json',100000)
    def test_valid_and_inert(self):
        c=self.make(); r=verify_certificate(PROFILE,ROOT/'fixtures'/'feasible.json',c)
        self.assertEqual(r['status'],'SYNTHETIC_WITNESS_VALID')
        p=founding_proposal(c)
        self.assertIsNone(p['adoption_digest']); self.assertFalse(p['ratified']); self.assertEqual(p['grants'],[])
    def test_body_hash_and_renamed_authority(self):
        c=self.make(); c['authority']='ACTIVE'
        r=verify_certificate(PROFILE,ROOT/'fixtures'/'feasible.json',c)
        self.assertIn('REPORT_BODY_HASH_MISMATCH',r['errors'])
        c['report_body_sha256']=report_hash({k:v for k,v in c.items() if k!='report_body_sha256'})
        self.assertTrue(verify_certificate(PROFILE,ROOT/'fixtures'/'feasible.json',c)['errors'])
    def test_local_input_hash_change(self):
        c=self.make()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'profile.json'; p.write_bytes(PROFILE.read_bytes()+b'\n')
            self.assertIn('LOCAL_INPUT_BYTE_HASH_MISMATCH',verify_certificate(p,ROOT/'fixtures'/'feasible.json',c)['errors'])
    def test_cli_invalid_json_is_structured(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'; p.write_text('{"x":1,"x":2}')
            r=subprocess.run([sys.executable,'-m','wac_offline','validate-profile',str(p)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(r.returncode,2); self.assertEqual(json.loads(r.stdout)['status'],'INVALID_INPUT')
    def test_cli_unsupported_profile_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'; data=read(PROFILE); data['status']='RATIFIED'; p.write_text(json.dumps(data))
            r=subprocess.run([sys.executable,'-m','wac_offline','validate-profile',str(p)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(r.returncode,2); self.assertEqual(json.loads(r.stdout)['status'],'INVALID_OR_UNSUPPORTED_PROFILE')
    def test_cli_limit_is_structured(self):
        r=subprocess.run([sys.executable,'-m','wac_offline','assemble','--profile',str(PROFILE),'--roster',str(ROOT/'fixtures'/'feasible.json'),'--max-nodes','0'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(r.returncode,4); self.assertEqual(json.loads(r.stdout)['status'],'SYNTHETIC_SEARCH_INCOMPLETE')

if __name__=='__main__': unittest.main()
