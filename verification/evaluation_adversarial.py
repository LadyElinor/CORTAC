from pathlib import Path
import sys, unittest, tempfile, shutil, os
from pathlib import Path
sys.path.insert(0,os.environ.get('WAC_QA_EVAL',str(Path(__file__).resolve().parents[1]/'evaluation')))
from common import ROOT, read, read_jsonl, write, write_jsonl, file_digest
from readiness import assess, check_integrity
from analyze import analyze, validate_rows, paired_bootstrap
from metrics import validate_row

class IndependentEvaluation(unittest.TestCase):
 def test_empty_custom_schedule_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'empty.jsonl';p.write_text('')
   with self.assertRaises(ValueError):analyze(p,p)
 def test_missing_timeout_still_required(self):
  rows=read_jsonl(ROOT/'smoke/fabricated_results.jsonl');sched=read_jsonl(ROOT/'fixtures/evaluator_only/analysis_smoke_schedule.jsonl')
  i=next(i for i,r in enumerate(rows) if r['terminal_status']=='TIMEOUT');rows.pop(i)
  with self.assertRaises(ValueError):validate_rows(rows,sched)
 def test_timeout_cannot_be_success(self):
  row=read_jsonl(ROOT/'smoke/fabricated_results.jsonl')[0];row['terminal_status']='TIMEOUT';row['metrics']['authorized_useful_completion']=1
  with self.assertRaises(ValueError):validate_row(row)
 def test_budget_mismatch_after_rehash(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)/'eval';shutil.copytree(ROOT,r)
   rel='evaluator_only/development_schedule.jsonl';p=r/'fixtures'/rel;slots=read_jsonl(p);slots[0]['budget_profile_id']='UNMATCHED';write_jsonl(p,slots)
   ip=r/'fixtures/fixture_inventory.json';inv=read(ip);inv['files'][rel]=file_digest(p);write(ip,inv)
   mp=r/'proposed_run_manifest.json';m=read(mp);m['local_author_proposals']['fixture_inventory']=inv;write(mp,m)
   fails=check_integrity(r);self.assertIn('MISMATCHED_BUDGET_PROFILE',fails);self.assertFalse(any('DIGEST_MISMATCH' in x for x in fails))
 def test_placeholder_and_booleans_cannot_freeze(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)/'eval';shutil.copytree(ROOT,r);p=r/'proposed_run_manifest.json';m=read(p)
   for k in ('signed','preregistered','frozen_for_scoring','scored_execution_enabled'):m[k]=True
   m['real_run_requirements']['model_configuration']={'deep':[{'x':' TBD '}]};write(p,m)
   x=assess(r);self.assertFalse(x['scored_run_ready']);self.assertIn('MISSING_OR_INVALID_REAL_RUN_REQUIREMENT:model_configuration',x['blockers'])
 def test_bootstrap_exact_and_paired(self):
  self.assertEqual(paired_bootstrap([2]*20)['interval_95'],[2,2]);self.assertEqual(paired_bootstrap([0]*20)['interval_95'],[0,0])

if __name__=='__main__': unittest.main(verbosity=2)
