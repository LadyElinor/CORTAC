"""Rebuild strictly synthetic fixture rosters. Names label simulations, not agents."""
from copy import deepcopy
from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wac_offline.io import write

ROOT = Path(__file__).parent
DIMS = ('model_lineage', 'runtime', 'shared_context', 'evidence_origin')
def record(ident, domain, roles, kind='agent'):
    return {'id': ident, 'kind': kind, 'credential': 'synthetic-credential-' + ident,
            'process': 'synthetic-process-' + ident, 'domain': domain, 'domain_verified': True,
            'material_control_known': True, 'material_controllers': ['synthetic-controller-' + domain],
            'qualified_roles': roles, 'capacity': 1, 'valid_until': 999999,
            'dependencies': {d: 'synthetic-' + d + '-' + domain for d in DIMS}, 'conflicts': []}

def feasible():
    records = [record('p', 'd0', ['proposer']),
               record('e', 'd1', ['epistemic_assessor']),
               record('n', 'd2', ['normative_assessor'])]
    records += [record('c' + str(i), 'd' + str(i), ['decision_council']) for i in range(1, 5)]
    records += [record('a', 'd3', ['authorizer'], 'authorizer_service'),
                record('x', 'd4', ['executor']), record('u', 'd1', ['outcome_auditor'])]
    records += [record('r' + str(i), 'd' + str(i+4), ['appeal']) for i in range(1, 4)]
    return {'schema_version': 'wac.offline_roster.v1', 'simulation_only': True,
            'case_id': 'synthetic-case-001', 'as_of': 1000, 'appeal_horizon': 2000,
            'proposer_id': 'p', 'beneficiary_ids': ['p'], 'appellant_ids': ['p'],
            'opposing_party_ids': [], 'prior_participant_ids': [],
            'registered_executor_ids': ['x'], 'records': records,
            'required_dependencies': {'epistemic_assessor': list(DIMS)},
            'distinct_dependencies': []}

def main():
    base = feasible(); write(ROOT / 'feasible.json', base)
    clones = deepcopy(base)
    for rec in clones['records']:
        rec['domain'] = 'clone-domain'
        rec['material_controllers'] = ['clone-controller']
    write(ROOT / 'clone_insufficiency.json', clones)
    same = deepcopy(base)
    for rec in same['records']:
        if 'appeal' in rec['qualified_roles']:
            rec['material_controllers'].append('synthetic-controller-d1')
    write(ROOT / 'same_controller_appeals.json', same)
    unknown = deepcopy(base)
    next(r for r in unknown['records'] if r['id'] == 'e')['dependencies']['runtime'] = None
    write(ROOT / 'unknown_dimensions.json', unknown)
    shortage = deepcopy(base)
    next(r for r in shortage['records'] if r['id'] == 'r3')['capacity'] = 0
    write(ROOT / 'reviewer_shortage.json', shortage)
    backtrack = deepcopy(base)
    # Lexicographically first evidence candidate uses a reserved appeal domain.
    backtrack['records'].append(record('00-e-strands-appeal', 'd5', ['epistemic_assessor']))
    write(ROOT / 'joint_backtracking.json', backtrack)
    bound = deepcopy(base); write(ROOT / 'bounded_search.json', bound)
    write(ROOT / 'split_exact.json', {'predecessor': [1, 1], 'successors': {f's{i}': [1, 3] for i in range(3)}})
    write(ROOT / 'frozen_vote.json', {'domain_roll': ['d1', 'd2', 'd3', 'd4', 'd5'],
        'yes_domains': ['d1', 'd2', 'd3', 'd4'],
        'cell_weights': {'a': [1,1], 'b': [1,1], 'c': [1,1], 'd': [1,1],
                         'e1': [1,3], 'e2': [1,3], 'e3': [1,3]},
        'yes_cells': ['a','b','c','d'], 'threshold': [3,4]})
    write(ROOT / 'ballot.json', {'seat_ids': ['c1','c2','c3','c4'], 'yes_ids': ['c1','c2','c3'], 'protected_failure': False, 'protected_limits': json.loads((ROOT / 'protected_limits.json').read_text(encoding='utf-8')), 'decision_record': json.loads((ROOT / 'decision_record.json').read_text(encoding='utf-8'))})

if __name__ == '__main__': main()
