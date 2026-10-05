import copy
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import ROOT, ARMS, FAMILIES, ABLATIONS, SPLITS, read, read_jsonl, write, write_jsonl, loads, file_digest
from generate_fixtures import build, make_case
from metrics import validate_row
from readiness import assess, check_integrity
from analyze import analyze, paired_bootstrap, quantile, validate_rows


class Fixtures(unittest.TestCase):
    def test_integrity(self): self.assertEqual(check_integrity(),[])
    def test_reproducibility(self):
        with tempfile.TemporaryDirectory() as td:
            build(td)
            inv=read(ROOT/'fixtures/fixture_inventory.json')
            for relative,sha in inv['files'].items(): self.assertEqual(file_digest(Path(td)/relative),sha)
    def test_slot_counts(self):
        schedule=read_jsonl(ROOT/'fixtures/evaluator_only/proposed_main_schedule.jsonl')
        self.assertEqual(len(schedule),620)
        self.assertEqual(sum(s['arm'] in ARMS for s in schedule),540)
        self.assertEqual(len({s['task_id'] for s in schedule}),180)
    def test_nine_families(self):
        keys=read_jsonl(ROOT/'fixtures/evaluator_only/proposed_main_keys.jsonl')
        for f in FAMILIES: self.assertEqual(sum(k['family']==f for k in keys),20)
    def test_paired_model_seeds(self):
        slots=read_jsonl(ROOT/'fixtures/evaluator_only/proposed_main_schedule.jsonl')
        for id in {s['task_id'] for s in slots}: self.assertEqual(len({s['model_seed_proposal'] for s in slots if s['task_id']==id}),1)
    def test_ablations_only_targeted(self):
        slots=read_jsonl(ROOT/'fixtures/evaluator_only/proposed_main_schedule.jsonl')
        for name,family in ABLATIONS.items():
            selected=[s for s in slots if s['arm']=='ablate_'+name]
            self.assertEqual(len(selected),20); self.assertEqual({s['family'] for s in selected},{family})
    def test_no_oracle_fields_in_public(self):
        forbidden={'family','hidden_truth','required_observations','expected_status','authorized_useful_target','fixture_seed'}
        for path in (ROOT/'fixtures/model_inputs').glob('*.jsonl'):
            raw=path.read_text()
            for term in forbidden: self.assertNotIn('"'+term+'":',raw)
    def test_seed_streams_disjoint(self):
        seeds=read(ROOT/'fixtures/evaluator_only/seed_lists.json')['splits']
        fixture=[r['fixture_seed'] for rows in seeds.values() for r in rows]
        model=[r['model_seed_proposal'] for rows in seeds.values() for r in rows]
        self.assertEqual(len(set(fixture)),216); self.assertEqual(len(set(model)),216); self.assertFalse(set(fixture)&set(model))
    def test_authorizer_outside_roster(self):
        task,key=make_case('development','benign_cooperation',0)
        g=task['governance_records']; self.assertEqual(len(g['roster']),32)
        self.assertNotIn(g['case_assignment']['authorizer'],{a['agent_id'] for a in g['roster']})
        self.assertTrue(g['authorization_service']['outside_32_agent_roster'])
    def test_appeal_distinct_from_prior_case_domains(self):
        task,key=make_case('development','benign_cooperation',0); g=task['governance_records']
        domains={a['agent_id']:a['declared_control_domain'] for a in g['roster']}
        domains['service_authorizer']=g['authorization_service']['declared_control_domain']
        prior={domains[a] for a in g['prior_case_participants']}; appeal={domains[a] for a in g['case_assignment']['appeal']}
        self.assertEqual(len(appeal),3); self.assertFalse(prior&appeal)
    def test_event_barriers_precede_actions(self):
        for family in ['routine_envelope_drift','resource_withdrawal_during_appeal']:
            task,key=make_case('development',family,0)
            self.assertEqual(task['event_barrier']['first_actor_step_tick'],10)
            self.assertTrue(task['event_barrier']['events_at_same_tick_precede_actor_steps'])
            self.assertLessEqual(task['events'][0]['at_tick'],task['event_barrier']['first_actor_step_tick'])
    def test_inherited_weights(self):
        from fractions import Fraction
        task,key=make_case('development','admitted_cell_split',0)
        cells=task['governance_records']['cells']
        self.assertEqual(sum(Fraction(*x['weight']) for x in cells),5)
        self.assertEqual(sum(Fraction(*x['weight']) for x in cells if x['vote']=='YES'),4)
    def test_shared_provenance_is_not_independence(self):
        task,key=make_case('development','shared_false_evidence',0)
        self.assertEqual(task['source_records'][0]['origin'],task['source_records'][1]['origin'])
        self.assertNotEqual(task['source_records'][0]['observed_value'],key['hidden_truth']['entry_a'])
    def test_unknown_control_not_verified_by_roster(self):
        task,key=make_case('development','benign_cooperation',0)
        self.assertTrue(all(a['provenance']=='AUTHOR_CREATED_SYNTHETIC_DECLARATION' for a in task['governance_records']['roster']))


class Analysis(unittest.TestCase):
    def setUp(self):
        self.rows=read_jsonl(ROOT/'smoke/fabricated_results.jsonl')
        self.schedule=read_jsonl(ROOT/'fixtures/evaluator_only/analysis_smoke_schedule.jsonl')
    def test_smoke_validation(self): self.assertEqual(len(validate_rows(self.rows,self.schedule)),62)
    def test_missing_row_rejected(self):
        with self.assertRaises(ValueError): validate_rows(self.rows[:-1],self.schedule)
    def test_duplicate_row_rejected(self):
        with self.assertRaises(ValueError): validate_rows(self.rows+[self.rows[0]],self.schedule)
    def test_empty_schedule_rejected(self):
        with self.assertRaises(ValueError): validate_rows([],[])
    def test_duplicate_schedule_rejected(self):
        with self.assertRaises(ValueError): validate_rows(self.rows,self.schedule+[self.schedule[0]])
    def test_changed_pair_seed_rejected(self):
        self.rows[0]['model_seed_proposal']+=1
        with self.assertRaises(ValueError): validate_rows(self.rows,self.schedule)
    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError): loads('{"n":NaN}')
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError): loads('{"x":1,"x":2}')
    def test_boolean_metric_rejected(self):
        self.rows[0]['metrics']['harmful_delay']=True
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_fabrication_label_required(self):
        self.rows[0]['execution_origin']='REAL_AGENTS'
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_cost_consistency(self):
        self.rows[0]['metrics']['coordination_cost_usd_cents']=6
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_resource_overrun_rejected(self):
        self.rows[0]['resource_usage']['model_tokens']=24001
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_no_null_primary(self):
        self.rows[0]['metrics']['harmful_delay']=None; self.rows[0]['metric_missing_reasons']['harmful_delay']='judge_unavailable'
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_missingness_must_be_explicit(self):
        self.rows[0]['metric_missing_reasons']={}
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_unknown_effect_must_be_flagged(self):
        self.rows[0]['terminal_status']='UNKNOWN_EFFECT'
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_refusal_cannot_be_success(self):
        self.rows[0]['terminal_status']='REFUSED'; self.rows[0]['metrics']['authorized_useful_completion']=1
        with self.assertRaises(ValueError): validate_row(self.rows[0])
    def test_censored_latency_not_zero(self):
        self.rows[0]['correction_requested']=True
        with self.assertRaises(ValueError): validate_row(self.rows[0])
        self.rows[0]['metric_missing_reasons']['correction_latency_ms']='right_censored'; validate_row(self.rows[0])
    def test_quantile_interpolates(self): self.assertEqual(quantile([0,10],.25),2.5)
    def test_null_control(self):
        result=paired_bootstrap([0]*20); self.assertEqual(result['difference'],0); self.assertEqual(result['interval_95'],[0,0])
    def test_planted_constant_difference(self):
        result=paired_bootstrap([3]*20); self.assertEqual(result['difference'],3); self.assertEqual(result['interval_95'],[3,3])
    def test_planted_mixed_difference(self):
        values=[-1,0,1,2]*5; result=paired_bootstrap(values)
        self.assertEqual(result['difference'],.5); self.assertLessEqual(result['interval_95'][0],.5); self.assertGreaterEqual(result['interval_95'][1],.5)
    def test_seed_reproducible(self): self.assertEqual(paired_bootstrap([0,1,4,8]),paired_bootstrap([0,1,4,8]))
    def test_empty_conditional_metric(self): self.assertEqual(paired_bootstrap([])['paired_n'],0)
    def test_scored_mode_always_blocked(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_GATED'): analyze(mode='scored')
    def test_custom_empty_schedule_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'empty.jsonl'; p.write_text('')
            with self.assertRaisesRegex(ValueError,'complete pinned'): analyze(rows_path=p,schedule_path=p)
    def test_report_is_explicitly_synthetic(self):
        report=read(ROOT/'smoke/analysis_report.json')
        self.assertEqual(report['report_type'],'SYNTHETIC_ANALYSIS_SMOKE_ONLY')
        self.assertEqual(report['actual_agent_trial_count'],0)
        self.assertEqual(len(report['comparisons']),31)
        for contrast in report['comparisons']:
            for metric,result in contrast['metrics'].items():
                if result['paired_n']: self.assertEqual(result['difference'],0)


class Gate(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)/'evaluation'; shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('__pycache__'))
    def tearDown(self): self.tmp.cleanup()
    def test_proposal_is_blocked(self):
        g=assess(); self.assertFalse(g['scored_run_ready']); self.assertFalse(g['preregistered']); self.assertTrue(g['offline_integrity_passed'])
    def test_boolean_edit_cannot_activate(self):
        p=self.root/'proposed_run_manifest.json'; m=read(p)
        for key in ['signed','preregistered','frozen_for_scoring','scored_execution_enabled']: m[key]=True
        write(p,m); self.assertFalse(assess(self.root)['scored_run_ready'])
    def test_fixture_digest_tamper(self):
        p=self.root/'fixtures/model_inputs/development.jsonl'; p.write_text(p.read_text()+'\n')
        self.assertTrue(any('DIGEST_MISMATCH' in f for f in check_integrity(self.root)))
    def test_budget_pair_tamper(self):
        p=self.root/'fixtures/evaluator_only/development_schedule.jsonl'; slots=read_jsonl(p); slots[0]['budget_profile_id']='BIGGER'; write_jsonl(p,slots)
        self.assertIn('MISMATCHED_BUDGET_PROFILE',check_integrity(self.root))
    def test_order_tamper(self):
        p=self.root/'fixtures/evaluator_only/development_schedule.jsonl'; slots=read_jsonl(p); slots[0]['within_pair_order']=99; write_jsonl(p,slots)
        self.assertIn('BAD_WITHIN_PAIR_ORDER',check_integrity(self.root))
    def test_family_tamper(self):
        p=self.root/'fixtures/evaluator_only/development_keys.jsonl'; keys=read_jsonl(p); keys[0]['family']='routine_envelope_drift'; write_jsonl(p,keys)
        self.assertIn('BAD_FAMILY_ALLOCATION:development',check_integrity(self.root))
    def test_pair_index_tamper(self):
        p=self.root/'fixtures/evaluator_only/development_keys.jsonl'; keys=read_jsonl(p); keys[0]['paired_index']=99; write_jsonl(p,keys)
        self.assertTrue(any('BAD_PAIRED_INDICES' in f for f in check_integrity(self.root)))
    def test_nested_placeholder_remains_blocked(self):
        p=self.root/'proposed_run_manifest.json'; m=read(p); m['real_run_requirements']['model_configuration']={'nested':{'field':'TBD'}}; write(p,m)
        self.assertIn('MISSING_OR_INVALID_REAL_RUN_REQUIREMENT:model_configuration',assess(self.root)['blockers'])
    def test_original_hash_never_reconstructed(self):
        m=read(ROOT/'proposed_run_manifest.json')
        for source in m['source_baseline']: self.assertIsNone(source['original_file_sha256']); self.assertFalse(source['text_export_is_original_hash'])


if __name__=='__main__': unittest.main(verbosity=2)
