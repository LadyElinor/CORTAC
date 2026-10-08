"""Deterministic finite CSP witness search over declared synthetic dependencies.

No network calls, key material, signatures, live agents, grants or state changes.
Search jointly includes fresh appeal reserve. This is NOT the uniform lottery.
"""
from collections import Counter
from .io import InputError

CASE_ROLES = ('epistemic_assessor', 'normative_assessor', 'council_1', 'council_2',
              'council_3', 'council_4', 'authorizer', 'executor', 'outcome_auditor')
APPEAL_ROLES = ('appeal_1', 'appeal_2', 'appeal_3')
ALL_ROLES = CASE_ROLES + APPEAL_ROLES
DEPENDENCIES = {'model_lineage', 'runtime', 'shared_context', 'evidence_origin'}
ROSTER_KEYS = {'schema_version', 'simulation_only', 'case_id', 'as_of', 'appeal_horizon',
               'proposer_id', 'beneficiary_ids', 'appellant_ids', 'opposing_party_ids',
               'prior_participant_ids', 'registered_executor_ids', 'records',
               'required_dependencies', 'distinct_dependencies'}
RECORD_KEYS = {'id', 'kind', 'credential', 'process', 'domain', 'domain_verified',
               'material_control_known', 'material_controllers', 'qualified_roles',
               'capacity', 'valid_until', 'dependencies', 'conflicts'}


def role_kind(role):
    if role.startswith('council_'):
        return 'decision_council'
    if role.startswith('appeal_'):
        return 'appeal'
    return role


def _strings(value, label, empty=True):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise InputError(f'{label}: expected string list')
    if len(value) != len(set(value)) or (not empty and not value):
        raise InputError(f'{label}: expected unique values' + (' and nonempty' if not empty else ''))


def validate_roster(roster):
    if not isinstance(roster, dict) or set(roster) != ROSTER_KEYS:
        raise InputError('roster fields must exactly match offline_roster.v1 contract')
    if roster['schema_version'] != 'wac.offline_roster.v1' or roster['simulation_only'] is not True:
        raise InputError('only explicit synthetic offline_roster.v1 is supported')
    for key in ('case_id', 'proposer_id'):
        if not isinstance(roster[key], str) or not roster[key]:
            raise InputError(f'{key} must be a nonempty string')
    for key in ('as_of', 'appeal_horizon'):
        if type(roster[key]) is not int or roster[key] < 0:
            raise InputError(f'{key} must be a nonnegative integer timestamp')
    if roster['appeal_horizon'] < roster['as_of']:
        raise InputError('appeal horizon cannot precede case as_of')
    if not isinstance(roster['records'], list) or not roster['records']:
        raise InputError('nonempty records required')
    records = {}
    allowed_roles = {role_kind(r) for r in ALL_ROLES} | {'proposer'}
    for rec in roster['records']:
        if not isinstance(rec, dict) or set(rec) != RECORD_KEYS:
            raise InputError('record fields must exactly match offline_roster.v1 contract')
        for key in ('id', 'credential', 'process'):
            if not isinstance(rec[key], str) or not rec[key]:
                raise InputError(f'record {key} must be a nonempty string')
        if rec['id'] in records:
            raise InputError('duplicate record identity')
        records[rec['id']] = rec
        if rec['kind'] not in ('agent', 'authorizer_service', 'interest'):
            raise InputError('unsupported record kind')
        if rec['domain'] is not None and (not isinstance(rec['domain'], str) or not rec['domain']):
            raise InputError('domain must be a nonempty string or null')
        for key in ('domain_verified', 'material_control_known'):
            if type(rec[key]) is not bool:
                raise InputError(f'{key} must be boolean')
        for key in ('capacity', 'valid_until'):
            if type(rec[key]) is not int or rec[key] < 0:
                raise InputError(f'{key} must be a nonnegative integer')
        for key in ('material_controllers', 'qualified_roles', 'conflicts'):
            _strings(rec[key], key)
        if not set(rec['qualified_roles']) <= allowed_roles:
            raise InputError('unknown qualification role')
        if rec['material_control_known'] and not rec['material_controllers']:
            raise InputError('known material-control closure must name at least one controlling interest')
        if not isinstance(rec['dependencies'], dict) or set(rec['dependencies']) != DEPENDENCIES:
            raise InputError('dependencies must record all four supported dimensions')
        if any(v is not None and (not isinstance(v, str) or not v) for v in rec['dependencies'].values()):
            raise InputError('dependency values must be nonempty strings or null')
    for key in ('beneficiary_ids', 'appellant_ids', 'opposing_party_ids', 'prior_participant_ids', 'registered_executor_ids'):
        _strings(roster[key], key)
        if not set(roster[key]) <= set(records):
            raise InputError(f'{key} names unknown record')
    if roster['proposer_id'] not in records:
        raise InputError('proposer names unknown record')
    for rec in records.values():
        if not set(rec['conflicts']) <= set(records):
            raise InputError('conflicts name unknown record')
    req = roster['required_dependencies']
    if not isinstance(req, dict) or not set(req) <= allowed_roles:
        raise InputError('unsupported required dependency role')
    for role, dims in req.items():
        _strings(dims, 'required dependencies')
        if not set(dims) <= DEPENDENCIES:
            raise InputError('unsupported required dependency dimension')
    # Baseline records every evidence dimension; UNKNOWN never meets a required one.
    if set(req.get('epistemic_assessor', [])) != DEPENDENCIES:
        raise InputError('epistemic assessor must require all four recorded dimensions')
    if not isinstance(roster['distinct_dependencies'], list):
        raise InputError('distinct_dependencies must be a list')
    for rule in roster['distinct_dependencies']:
        if not isinstance(rule, dict) or set(rule) != {'roles', 'dimensions'}:
            raise InputError('invalid purpose-specific distinct dependency rule')
        _strings(rule['roles'], 'distinct roles', empty=False)
        _strings(rule['dimensions'], 'distinct dimensions', empty=False)
        if len(rule['roles']) != 2 or not set(rule['roles']) <= set(ALL_ROLES) | {'proposer'}:
            raise InputError('distinct rule must name two concrete roles or proposer')
        if not set(rule['dimensions']) <= DEPENDENCIES:
            raise InputError('unsupported distinct dependency dimension')
    return records


def _controllers(rec):
    return set(rec['material_controllers'])


def _overlap(a, b):
    return bool(_controllers(a) & _controllers(b))


def _declared_conflict(a, b):
    return b['id'] in a['conflicts'] or a['id'] in b['conflicts']


def _eligible(rec, role, roster):
    reasons = []
    kind = role_kind(role)
    if rec['kind'] != ('authorizer_service' if role == 'authorizer' else 'agent'):
        reasons.append('WRONG_ENTITY_KIND')
    if kind not in rec['qualified_roles']:
        reasons.append('UNQUALIFIED')
    if role == 'executor' and rec['id'] not in roster['registered_executor_ids']:
        reasons.append('UNREGISTERED_EXECUTOR')
    if rec['id'] in roster['prior_participant_ids']:
        reasons.append('PRIOR_CASE_PARTICIPATION')
    if rec['capacity'] < 1:
        reasons.append('NO_CAPACITY')
    at = roster['appeal_horizon'] if role in APPEAL_ROLES else roster['as_of']
    if rec['valid_until'] <= at:
        reasons.append('EXPIRED')
    if not rec['domain_verified'] or not rec['domain']:
        reasons.append('UNKNOWN_CONTROL_DOMAIN')
    if not rec['material_control_known']:
        reasons.append('UNKNOWN_MATERIAL_CONTROL')
    required = set(roster['required_dependencies'].get(kind, []))
    for rule in roster['distinct_dependencies']:
        if role in rule['roles']:
            required.update(rule['dimensions'])
    if any(rec['dependencies'][dim] is None for dim in required):
        reasons.append('UNKNOWN_REQUIRED_DIMENSION')
    return reasons


def _conflicts(role, rec, assigned, roster, records):
    """One shared, independently callable relation for search and witness checking."""
    reasons = []
    proposer = records[roster['proposer_id']]
    beneficiaries = [records[x] for x in roster['beneficiary_ids']]
    prior = [records[x] for x in roster['prior_participant_ids']]
    selected = [(r, records[x]) for r, x in assigned.items()]
    if rec['id'] == proposer['id'] or any(rec['id'] == a['id'] for _, a in selected):
        reasons.append('CASE_IDENTITY_REUSE')
    if any(_declared_conflict(rec, a) for a in [proposer] + beneficiaries + prior + [a for _, a in selected]):
        reasons.append('DECLARED_CONFLICT')
    if role in ('epistemic_assessor', 'normative_assessor'):
        for party in [proposer] + beneficiaries:
            if any(rec[k] == party[k] for k in ('id', 'credential', 'domain')) or _overlap(rec, party):
                reasons.append('ASSESSOR_PROPOSER_BENEFICIARY_CONFLICT')
    if role.startswith('council_'):
        for party in [proposer] + beneficiaries:
            if rec['domain'] == party['domain'] or _overlap(rec, party):
                reasons.append('COUNCIL_PROPOSER_BENEFICIARY_CONTROL')
        council = [a for r, a in selected if r.startswith('council_')]
        if any(rec['domain'] == a['domain'] for a in council):
            reasons.append('COUNCIL_DOMAIN_REUSE')
        if any(_overlap(rec, a) for a in council):
            reasons.append('COUNCIL_MATERIAL_CONTROL_REUSE')
    # Service and executor credentials/processes must differ from every case role,
    # not only whichever roles happened to be visited earlier in the DFS.
    for other_role, other in [('proposer', proposer)] + selected:
        if role in ('authorizer', 'executor') or other_role in ('authorizer', 'executor'):
            if rec['credential'] == other['credential'] or rec['process'] == other['process']:
                reasons.append('AUTHORIZATION_EXECUTION_NOT_SEPARATE')
    if role == 'outcome_auditor':
        if rec['id'] in roster['prior_participant_ids']:
            reasons.append('AUDITOR_PRIOR_CASE_WORK')
        for party in [proposer] + [a for r, a in selected if r == 'executor']:
            if any(rec[k] == party[k] for k in ('id', 'credential', 'domain')) or _overlap(rec, party):
                reasons.append('AUDITOR_PROPOSER_EXECUTOR_CONFLICT')
    if role in APPEAL_ROLES:
        excluded_ids = {roster['proposer_id'], *roster['prior_participant_ids'],
                        *roster['beneficiary_ids'], *roster['appellant_ids'],
                        *roster['opposing_party_ids']}
        excluded_ids.update(x for r, x in assigned.items() if r in CASE_ROLES)
        for ident in excluded_ids:
            excluded = records[ident]
            if not excluded['material_control_known']:
                reasons.append('UNKNOWN_EXCLUDED_MATERIAL_CONTROL')
            if (rec['id'] == ident or rec['domain'] == excluded['domain'] or
                    rec['credential'] == excluded['credential'] or _overlap(rec, excluded)):
                reasons.append('APPEAL_EXCLUDED_INTEREST')
            if _declared_conflict(rec, excluded):
                reasons.append('APPEAL_DECLARED_CONFLICT')
        for r, other in selected:
            if r in APPEAL_ROLES and (rec['domain'] == other['domain'] or _overlap(rec, other)):
                reasons.append('APPEAL_DOMAIN_OR_CONTROL_REUSE')
    assignment_records = {'proposer': proposer, **dict(selected), role: rec}
    for rule in roster['distinct_dependencies']:
        first, second = rule['roles']
        if first in assignment_records and second in assignment_records:
            a, b = assignment_records[first], assignment_records[second]
            for dim in rule['dimensions']:
                if a['dependencies'][dim] is None or b['dependencies'][dim] is None:
                    reasons.append('UNKNOWN_REQUIRED_DIMENSION')
                elif a['dependencies'][dim] == b['dependencies'][dim]:
                    reasons.append('PURPOSE_SPECIFIC_DEPENDENCY_CONFLICT')
    return sorted(set(reasons))


def _fixed_party_errors(roster, records):
    excluded = {roster['proposer_id'], *roster['beneficiary_ids'],
                *roster['appellant_ids'], *roster['opposing_party_ids'],
                *roster['prior_participant_ids']}
    errors = [f'UNKNOWN_REQUIRED_PARTY_DOMAIN:{ident}' for ident in sorted(excluded)
              if not records[ident]['domain_verified'] or not records[ident]['domain']]
    proposer = records[roster['proposer_id']]
    if 'proposer' not in proposer['qualified_roles']:
        errors.append('FIXED_PROPOSER_UNQUALIFIED')
    for dim in roster['required_dependencies'].get('proposer', []):
        if proposer['dependencies'][dim] is None:
            errors.append('PROPOSER_UNKNOWN_REQUIRED_DIMENSION:' + dim)
    return errors


def verify_assignment(roster, assignment):
    records = validate_roster(roster)
    if not isinstance(assignment, dict) or set(assignment) != set(ALL_ROLES):
        return ['ASSIGNMENT_ROLE_SET_MISMATCH']
    errors, visited = _fixed_party_errors(roster, records), {}
    proposer = records[roster['proposer_id']]
    if proposer['kind'] != 'agent' or proposer['capacity'] < 1 or proposer['valid_until'] <= roster['as_of']:
        errors.append('FIXED_PROPOSER_UNAVAILABLE')
    for role in ALL_ROLES:
        ident = assignment[role]
        if not isinstance(ident, str) or ident not in records:
            errors.append(f'{role}:UNKNOWN_IDENTITY')
            continue
        rec = records[ident]
        errors.extend(f'{role}:{x}' for x in _eligible(rec, role, roster))
        errors.extend(f'{role}:{x}' for x in _conflicts(role, rec, visited, roster, records))
        visited[role] = ident
    return sorted(set(errors))


def solve(roster, max_nodes=100000):
    if type(max_nodes) is not int or max_nodes < 0:
        raise InputError('max_nodes must be a nonnegative integer')
    records = validate_roster(roster)
    static = Counter()
    candidates = {}
    for role in ALL_ROLES:
        candidates[role] = []
        for ident in sorted(records):
            reasons = _eligible(records[ident], role, roster)
            if reasons:
                static.update(f'{role}:{x}' for x in reasons)
            else:
                candidates[role].append(ident)
    base = {
        'authority_status': 'UNINITIALIZED_NO_EXECUTION', 'execution_enabled': False,
        'simulation_only': True, 'case_id': roster['case_id'],
        'authority': 'NONE', 'controller_closure': 'SUPPLIED_UNVERIFIED',
        'search_method': 'deterministic_lexicographic_joint_case_and_appeal_DFS_not_role_lottery',
        'scope': 'declared_synthetic_finite_constraint_model_only',
        'candidate_counts': {r: len(v) for r, v in candidates.items()},
        'static_rejections': dict(sorted(static.items())),
        'max_nodes': max_nodes,
        'supported_additions': ['conservative_material_overlap_exclusion_for_assessors',
                                'pairwise_material_control_disjoint_appeal_panel',
                                'pairwise_material_control_disjoint_council',
                                'auditor_proposer_executor_material_control_separation'],
    }
    necessary = _fixed_party_errors(roster, records)
    proposer = records[roster['proposer_id']]
    if proposer['kind'] != 'agent' or proposer['capacity'] < 1 or proposer['valid_until'] <= roster['as_of']:
        necessary.append('FIXED_PROPOSER_UNAVAILABLE')
    for role in ALL_ROLES:
        if not candidates[role]:
            necessary.append(f'NO_ELIGIBLE_CANDIDATE:{role}')
    if len({records[x]['domain'] for role in ALL_ROLES if role.startswith('council_') for x in candidates[role]}) < 4:
        necessary.append('FEWER_THAN_FOUR_ELIGIBLE_COUNCIL_DOMAINS')
    if len({records[x]['domain'] for role in APPEAL_ROLES for x in candidates[role]}) < 3:
        necessary.append('FEWER_THAN_THREE_ELIGIBLE_APPEAL_DOMAINS')
    if necessary:
        return {**base, 'status': 'SYNTHETICALLY_INFEASIBLE', 'evidence_kind': 'NECESSARY_CONDITION_FAILURE',
                'nodes': 0, 'search_exhausted': False, 'diagnostics': necessary,
                'assignment': None, 'dynamic_rejections': {}}
    nodes, incomplete, dynamic = 0, False, Counter()
    def visit(index, assigned):
        nonlocal nodes, incomplete
        if index == len(ALL_ROLES):
            return dict(assigned)
        role = ALL_ROLES[index]
        for ident in candidates[role]:
            # Interchangeable panel seats: eliminate only equivalent permutations.
            previous = ('council_' + str(int(role[-1]) - 1)) if role.startswith('council_') and role != 'council_1' else None
            if role.startswith('appeal_') and role != 'appeal_1':
                previous = 'appeal_' + str(int(role[-1]) - 1)
            # Mission rules can refer to concrete seats, destroying interchangeability.
            symmetric = not any(role in r['roles'] or previous in r['roles'] for r in roster['distinct_dependencies'])
            if previous and symmetric and ident <= assigned[previous]:
                continue
            if nodes >= max_nodes:
                incomplete = True
                return None
            nodes += 1
            reasons = _conflicts(role, records[ident], assigned, roster, records)
            if reasons:
                dynamic.update(f'{role}:{x}' for x in reasons)
                continue
            assigned[role] = ident
            result = visit(index + 1, assigned)
            del assigned[role]
            if result is not None or incomplete:
                return result
        return None
    assignment = visit(0, {})
    if assignment is not None:
        errors = verify_assignment(roster, assignment)
        if errors:
            raise RuntimeError('internal witness verification failed: ' + repr(errors))
        status, evidence, diagnostics = 'SYNTHETICALLY_SATISFIED', 'SYNTHETIC_ASSIGNMENT', []
    elif incomplete:
        status, evidence, diagnostics = 'SYNTHETIC_SEARCH_INCOMPLETE', 'BOUND_REACHED_NO_PROOF', ['NODE_BUDGET_EXHAUSTED']
    else:
        status, evidence, diagnostics = 'SYNTHETICALLY_INFEASIBLE', 'EXHAUSTIVE_FINITE_SEARCH', ['NO_ASSIGNMENT_IN_DECLARED_FINITE_MODEL']
    return {**base, 'status': status, 'evidence_kind': evidence, 'nodes': nodes,
            'search_exhausted': assignment is None and not incomplete,
            'assignment': assignment, 'diagnostics': diagnostics,
            'dynamic_rejections': dict(sorted(dynamic.items()))}
