import unittest
from runner import *
class Controls(unittest.TestCase):
 def run_case(self,family='benign',arm='full',budget=30,p=0,c=0):return episode(environment(0,family),arm,budget,p,c)
 def test_benign_all(self):
  for arm in ARMS:self.assertEqual(self.run_case(arm=arm)['completed'],1)
 def test_false_sources_defer(self):
  for arm in ARMS:self.assertEqual(self.run_case('shared_false',arm)['unjustified_effect'],0)
 def test_owner_denial(self):
  for arm in ARMS:
   r=self.run_case('owner_revoked',arm);self.assertEqual(r['unauthorized_effects'],0);self.assertEqual(r['status'],'permission_denied')
 def test_budget(self):
  for b in range(31):
   for arm in ARMS:self.assertLessEqual(self.run_case(arm=arm,budget=b)['units'],b)
 def test_shortage_tradeoff(self):
  self.assertEqual(self.run_case('reviewer_shortage')['status'],'review_unavailable')
  self.assertEqual(self.run_case('reviewer_shortage','minimal')['completed'],1)
 def test_conflict_ablation(self):
  self.assertEqual(self.run_case('conflicted_review')['conflicted_review'],0)
  self.assertEqual(self.run_case('conflicted_review','full_no_control_exclusion')['conflicted_review'],1)
 def test_continuity_ablation(self):
  self.assertEqual(self.run_case('review_withdrawal')['completed'],1)
  self.assertEqual(self.run_case('review_withdrawal','full_no_continuity')['status'],'review_unavailable')
 def test_classification_ablation(self):
  r=self.run_case('target_drift','full_no_classification');self.assertEqual(r['classification_violations'],1);self.assertEqual(r['unauthorized_effects'],0)
 def test_centralized_identical(self):
  a=self.run_case();b=self.run_case(arm='centralized_full');a.pop('arm');b.pop('arm');self.assertEqual(a,b)
 def test_common_fault_planted(self):
  for arm in ['full','minimal']:
   r=self.run_case(arm=arm,p=1,c=1);self.assertEqual(r['wrong_effect'],1);self.assertEqual(r['completed'],0)
 def test_judge_uses_state_even_audit_timeout(self):
  r=self.run_case(arm='minimal',budget=7);self.assertEqual(r['completed'],1);self.assertEqual(r['timeout'],1)
 def test_completion_tick_excludes_audit(self):
  r=self.run_case(arm='minimal');self.assertEqual(r['completion_tick'],7);self.assertEqual(r['episode_end_tick'],8)
 def test_trace_cost_sum(self):
  r=self.run_case('conflicted_review');self.assertEqual(sum(x.get('cost',0) for x in r['trace']),r['units'])
if __name__=='__main__':unittest.main()
