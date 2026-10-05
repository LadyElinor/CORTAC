from pathlib import Path
import sys, json, copy, os
sys.path.insert(0,os.environ.get('WAC_QA_PACKAGE',str(Path(__file__).resolve().parents[1]/'package')))
from wac_offline.solver import *

def rec(i,d,roles,kind='agent'):
 return {'id':i,'kind':kind,'credential':'cred-'+i,'process':'proc-'+i,'domain':d,'domain_verified':True,'material_control_known':True,'material_controllers':['owner-'+d],'qualified_roles':roles,'capacity':1,'valid_until':1000,'dependencies':{k:i+'-'+k for k in DEPENDENCIES},'conflicts':[]}
def base():
 data=[('P','D0',['proposer']),('E','D1',['epistemic_assessor']),('N','D2',['normative_assessor']),('C1','D1',['decision_council']),('C2','D2',['decision_council']),('C3','D3',['decision_council']),('C4','D4',['decision_council']),('A','D3',['authorizer']),('X','D4',['executor']),('U','D1',['outcome_auditor']),('R1','D5',['appeal']),('R2','D6',['appeal']),('R3','D7',['appeal'])]
 return {'schema_version':'wac.offline_roster.v1','simulation_only':True,'case_id':'qa','as_of':1,'appeal_horizon':2,'proposer_id':'P','beneficiary_ids':['P'],'appellant_ids':['P'],'opposing_party_ids':['C4'],'prior_participant_ids':[],'registered_executor_ids':['X'],'records':[rec(i,d,rs,'authorizer_service' if i=='A' else 'agent') for i,d,rs in data],'required_dependencies':{'epistemic_assessor':sorted(DEPENDENCIES)},'distinct_dependencies':[]}
if __name__=='__main__':
 for name,change in [('baseline',lambda r:None),('unregistered_executor',lambda r:r.update(registered_executor_ids=[])),('unknown_proposer_domain',lambda r:r['records'][0].update(domain=None,domain_verified=False)),('unknown_beneficiary_domain',lambda r:r['records'][0].update(domain_verified=False)),('appeal_conflicted_controller',lambda r:r['records'][-1].update(material_controllers=['owner-D0'])),('unknown_material_control',lambda r:r['records'][0].update(material_control_known=False))]:
  r=base(); change(r)
  result=solve(r)
  print(name,result['status'],result['nodes'],result['diagnostics'],result['assignment'])
 print('cutoff',solve(base(),max_nodes=0)['status'])
