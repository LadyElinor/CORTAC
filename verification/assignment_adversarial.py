from pathlib import Path
import sys, copy, unittest, os
sys.path[:0]=[os.environ.get("WAC_QA_PACKAGE",str(Path(__file__).resolve().parents[1]/'package')),str(Path(__file__).resolve().parent)]
from assignment_probe import base
from wac_offline.solver import solve, verify_assignment
from wac_offline.governance import consequential_ballot, frozen_vote, split_check
from wac_offline.io import InputError, loads

class Adversarial(unittest.TestCase):
 def test_executor_registration(self):
  r=base();r["registered_executor_ids"]=[];self.assertEqual(solve(r)["status"],"INFEASIBLE")
 def test_unknown_party_domain(self):
  for domain in (None,"D0"):
   r=base();r["records"][0].update(domain=domain,domain_verified=False);self.assertNotEqual(solve(r)["status"],"FEASIBLE")
 def test_seat_specific_domain_bound(self):
  for panel, known in [("council","C1"),("appeal","R1")]:
   r=base();a=solve(r)["assignment"];r["distinct_dependencies"]=[{"roles":[panel+"_1","proposer"],"dimensions":["runtime"]}]
   for rec in r["records"]:
    if (rec["id"].startswith("C") if panel=="council" else rec["id"].startswith("R")) and rec["id"]!=known:rec["dependencies"]["runtime"]=None
   self.assertEqual(verify_assignment(r,a),[])
   self.assertEqual(solve(r)["status"],"FEASIBLE")
 def test_proposer_availability(self):
  r=base();a=solve(r)["assignment"];r["records"][0]["capacity"]=0
  self.assertEqual(solve(r)["status"],"INFEASIBLE");self.assertTrue(verify_assignment(r,a))
 def test_joint_search(self):
  r=base();bad=copy.deepcopy(r["records"][1]);bad.update(id="00-evidence-strands-appeal",domain="D5",material_controllers=["owner-D5"],credential="other-credential",process="other-process");r["records"].append(bad)
  out=solve(r);self.assertEqual(out["status"],"FEASIBLE");self.assertEqual(out["assignment"]["epistemic_assessor"],"E")
 def test_cutoff_boundary(self):
  r=base();n=solve(r)["nodes"];self.assertEqual(solve(r,max_nodes=n)["status"],"FEASIBLE");self.assertEqual(solve(r,max_nodes=n-1)["status"],"SEARCH_INCOMPLETE")
 def test_control_ancestors_supplied(self):
  r=base();r["records"][0]["material_controllers"].append("funding-ancestor");r["records"][-1]["material_controllers"].append("funding-ancestor");self.assertEqual(solve(r)["status"],"INFEASIBLE")
 def test_ballot_malformed(self):
  for a in [("abcd","abc",False),(["a","b","c","d"],["a","b","c"],[]),(["","b","c","d"],["","b","c"],False)]:
   try: out=consequential_ballot(*a)
   except InputError: continue
   self.assertFalse(out["structurally_passes"])
 def test_rational_large_exact(self):
  p=10**80+7;self.assertTrue(split_check([1,1],{"a":[p-1,p],"b":[1,p]})["conserved"])
 def test_required_proposer_dimension(self):
  r=base();a=solve(r)["assignment"];r["required_dependencies"]["proposer"]=["runtime"];r["records"][0]["dependencies"]["runtime"]=None
  self.assertEqual(solve(r)["status"],"INFEASIBLE");self.assertTrue(verify_assignment(r,a))
 def test_duplicate_nested_rejected(self):
  with self.assertRaises(InputError):loads("{\"x\":{\"x\":0,\"x\":1}}")

if __name__=="__main__": unittest.main(verbosity=2)
