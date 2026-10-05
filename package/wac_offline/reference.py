"""Second constraint encoding: unary domains and unordered binary constraints.

Only the input-shape validator is shared with solver.py. No search, eligibility,
conflict, symmetry, or witness-checking function from that module is used here.
This is implementation diversity within one project, not an external audit.
"""
from itertools import combinations

from .io import InputError
from .solver import validate_roster

ROLES = ('epistemic_assessor', 'normative_assessor', 'council_1', 'council_2',
         'council_3', 'council_4', 'authorizer', 'executor', 'outcome_auditor',
         'appeal_1', 'appeal_2', 'appeal_3')
COUNCIL = frozenset(ROLES[2:6])
APPEAL = frozenset(ROLES[9:])
ASSESSORS = frozenset(ROLES[:2])
SEPARATE = frozenset(('authorizer', 'executor'))


def clashes(a, b):
    return b['id'] in a['conflicts'] or a['id'] in b['conflicts']


def shared_control(a, b):
    return not set(a['material_controllers']).isdisjoint(b['material_controllers'])


class ConstraintTable:
    """Compile a validated roster into unary candidate sets and binary tests.

    Pair tests are evaluated lazily; construction does not materialize a
    Cartesian product of all candidate pairs. Fixed-party checks still cost
    work for every candidate and supplied party.
    """
    def __init__(self, roster):
        self.records = validate_roster(roster)
        self.roster = roster
        self.proposer = self.records[roster['proposer_id']]
        self.parties = {roster['proposer_id'], *roster['beneficiary_ids'],
                        *roster['appellant_ids'], *roster['opposing_party_ids'],
                        *roster['prior_participant_ids']}
        self.fixed_errors = []
        for ident in sorted(self.parties):
            rec = self.records[ident]
            if rec['domain'] is None or not rec['domain_verified']:
                self.fixed_errors.append('PARTY_DOMAIN:' + ident)
        p = self.proposer
        if (p['kind'] != 'agent' or p['capacity'] == 0 or
                p['valid_until'] <= roster['as_of'] or 'proposer' not in p['qualified_roles']):
            self.fixed_errors.append('PROPOSER_UNAVAILABLE')
        if any(p['dependencies'][d] is None
               for d in roster['required_dependencies'].get('proposer', [])):
            self.fixed_errors.append('PROPOSER_DEPENDENCY_UNKNOWN')
        self.domains = {role: tuple(i for i in sorted(self.records)
                                   if not self.unary_errors(role, i)) for role in ROLES}

    def unary_errors(self, role, ident):
        r, a = self.roster, self.records[ident]
        p = self.proposer
        errors = []
        kind = 'decision_council' if role in COUNCIL else 'appeal' if role in APPEAL else role
        if a['kind'] != ('authorizer_service' if role == 'authorizer' else 'agent'):
            errors.append('ENTITY_KIND')
        if kind not in a['qualified_roles']:
            errors.append('QUALIFICATION')
        if role == 'executor' and ident not in r['registered_executor_ids']:
            errors.append('EXECUTOR_REGISTRATION')
        if ident in r['prior_participant_ids'] or ident == p['id']:
            errors.append('FIXED_IDENTITY_REUSE')
        horizon = r['appeal_horizon'] if role in APPEAL else r['as_of']
        if a['capacity'] == 0 or a['valid_until'] <= horizon:
            errors.append('AVAILABILITY')
        if a['domain'] is None or not a['domain_verified'] or not a['material_control_known']:
            errors.append('UNKNOWN_CONTROL')
        dims = set(r['required_dependencies'].get(kind, []))
        for rule in r['distinct_dependencies']:
            if role in rule['roles']:
                dims.update(rule['dimensions'])
        if any(a['dependencies'][d] is None for d in dims):
            errors.append('DEPENDENCY_UNKNOWN')
        fixed_conflicts = {p['id'], *r['beneficiary_ids'], *r['prior_participant_ids']}
        if any(clashes(a, self.records[i]) for i in fixed_conflicts):
            errors.append('FIXED_DECLARED_CONFLICT')
        if role in ASSESSORS | COUNCIL:
            for i in {p['id'], *r['beneficiary_ids']}:
                b = self.records[i]
                if a['domain'] == b['domain'] or shared_control(a, b):
                    errors.append('PARTY_CONTROL')
                if role in ASSESSORS and (a['id'] == b['id'] or a['credential'] == b['credential']):
                    errors.append('ASSESSOR_PARTY_IDENTITY')
        if role in SEPARATE and (a['credential'] == p['credential'] or a['process'] == p['process']):
            errors.append('SERVICE_PROPOSER_SEPARATION')
        if role == 'outcome_auditor' and any(a[k] == p[k] for k in ('id', 'credential', 'domain')):
            errors.append('AUDITOR_PROPOSER_SEPARATION')
        if role in APPEAL:
            for i in self.parties:
                b = self.records[i]
                if not b['material_control_known']:
                    errors.append('PARTY_CONTROL_UNKNOWN')
                if (any(a[k] == b[k] for k in ('id', 'credential', 'domain')) or
                        shared_control(a, b) or clashes(a, b)):
                    errors.append('APPEAL_FIXED_PARTY')
        for rule in r['distinct_dependencies']:
            if set(rule['roles']) == {role, 'proposer'}:
                if any(a['dependencies'][d] is None or p['dependencies'][d] is None or
                       a['dependencies'][d] == p['dependencies'][d] for d in rule['dimensions']):
                    errors.append('PROPOSER_DISTINCT_DEPENDENCY')
        return sorted(set(errors))

    def pair_errors(self, left, first, right, second):
        a, b = self.records[first], self.records[second]
        errors = []
        if first == second:
            errors.append('IDENTITY_REUSE')
        if clashes(a, b):
            errors.append('DECLARED_CONFLICT')
        if left in COUNCIL and right in COUNCIL and a['domain'] == b['domain']:
            errors.append('COUNCIL_DOMAIN_REUSE')
        if ({left, right} & SEPARATE) and (a['credential'] == b['credential'] or a['process'] == b['process']):
            errors.append('SERVICE_SEPARATION')
        if {left, right} == {'outcome_auditor', 'executor'}:
            if any(a[k] == b[k] for k in ('id', 'credential', 'domain')):
                errors.append('AUDITOR_EXECUTOR_SEPARATION')
        if left in APPEAL and right in APPEAL:
            if a['domain'] == b['domain'] or shared_control(a, b):
                errors.append('APPEAL_PANEL_CONTROL')
        elif left in APPEAL or right in APPEAL:
            if (any(a[k] == b[k] for k in ('id', 'credential', 'domain')) or shared_control(a, b)):
                errors.append('APPEAL_CASE_CONTROL')
        for rule in self.roster['distinct_dependencies']:
            if set(rule['roles']) == {left, right}:
                if any(a['dependencies'][d] is None or b['dependencies'][d] is None or
                       a['dependencies'][d] == b['dependencies'][d] for d in rule['dimensions']):
                    errors.append('DISTINCT_DEPENDENCY')
        return sorted(set(errors))

    def compatible(self, role, ident, assignment):
        return all(not self.pair_errors(role, ident, other, value)
                   for other, value in assignment.items())


def verify_reference(roster, assignment):
    table = ConstraintTable(roster)
    if not isinstance(assignment, dict) or set(assignment) != set(ROLES):
        return ['ROLE_SET']
    errors = list(table.fixed_errors)
    for role, ident in assignment.items():
        if not isinstance(ident, str) or ident not in table.records:
            errors.append('UNKNOWN_IDENTITY:' + role)
        else:
            errors.extend(role + ':' + e for e in table.unary_errors(role, ident))
    if any(e.startswith('UNKNOWN_IDENTITY:') for e in errors):
        return sorted(set(errors))
    for left, right in combinations(ROLES, 2):
        errors.extend(left + '/' + right + ':' + e
                      for e in table.pair_errors(left, assignment[left], right, assignment[right]))
    return sorted(set(errors))


def solve_reference(roster, max_nodes=100000):
    """MRV/forward-checking search; no lexical panel symmetry reduction."""
    if type(max_nodes) is not int or max_nodes < 0:
        raise InputError('max_nodes must be a nonnegative integer')
    table = ConstraintTable(roster)
    nodes = 0
    interrupted = False

    def search(domains, assigned):
        nonlocal nodes, interrupted
        if not domains:
            return dict(assigned)
        role = min(domains, key=lambda k: (len(domains[k]), k))
        if not domains[role]:
            return None
        for ident in domains[role]:
            if nodes == max_nodes:
                interrupted = True
                return None
            nodes += 1
            remaining = {r: tuple(i for i in ids if not table.pair_errors(role, ident, r, i))
                         for r, ids in domains.items() if r != role}
            if any(not ids for ids in remaining.values()):
                continue
            result = search(remaining, {**assigned, role: ident})
            if result is not None or interrupted:
                return result
        return None

    result = None if table.fixed_errors else search(table.domains, {})
    status = ('SYNTHETICALLY_SATISFIED' if result is not None else
              'SYNTHETIC_SEARCH_INCOMPLETE' if interrupted else 'SYNTHETICALLY_INFEASIBLE')
    return {'status': status, 'assignment': result, 'nodes': nodes, 'max_nodes': max_nodes,
            'authority': 'NONE', 'execution_enabled': False, 'simulation_only': True,
            'scope': 'declared_synthetic_finite_constraint_model_only',
            'method': 'separate_unary_binary_encoding_MRV_forward_checking',
            'shared_component': 'roster_shape_validator_only',
            'controller_closure': 'SUPPLIED_UNVERIFIED',
            'diagnostics': table.fixed_errors}
