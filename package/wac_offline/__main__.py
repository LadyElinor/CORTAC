"""Local synthetic tools. No authority, keys, network, agents, or appointments."""
import argparse
import json
import sys
from . import __version__
from .io import InputError, read, report_bytes, report_hash, sha256_file
from .profile import validate_profile
from .solver import solve, verify_assignment
from .reference import solve_reference, verify_reference
from .governance import frozen_vote, split_check, consequential_ballot
from .lottery import freeze_roll, simulate

SAT = 'SYNTHETICALLY_SATISFIED'
UNSAT = 'SYNTHETICALLY_INFEASIBLE'
INCOMPLETE = 'SYNTHETIC_SEARCH_INCOMPLETE'
BOUNDARY = {'authority': 'NONE', 'authority_status': 'UNINITIALIZED_NO_EXECUTION',
            'execution_enabled': False, 'simulation_only': True,
            'controller_closure': 'SUPPLIED_UNVERIFIED',
            'scope': 'declared_synthetic_finite_constraint_model_only'}
LIMITATIONS = ['real_world_independence', 'enrollment_or_credential_authenticity',
               'dependency_truth_or_completeness', 'qualification_or_capacity_evidence',
               'duty_or_evidence_sufficiency', 'external_appeal_route', 'review_funding',
               'uniform_role_lottery_or_appointment', 'signed_adoption', 'ACTIVE_readiness']


def hashes(profile_path, roster_path):
    return {'profile_local_bytes_sha256': sha256_file(profile_path),
            'roster_local_bytes_sha256': sha256_file(roster_path)}


def check_profile(path):
    validation = validate_profile(read(path))
    if validation['errors']:
        raise InputError('profile rejected: ' + json.dumps(validation['errors']))
    return validation


def certificate(profile_path, roster_path, max_nodes):
    validation = check_profile(profile_path)
    roster = read(roster_path)
    primary = solve(roster, max_nodes)
    secondary = solve_reference(roster, max_nodes)
    result = dict(primary)
    decisive = {SAT, UNSAT}
    disagreement = (primary['status'] in decisive and secondary['status'] in decisive and
                    primary['status'] != secondary['status'])
    witness = primary['assignment'] or secondary['assignment']
    errors = [] if witness is None else verify_assignment(roster, witness) + verify_reference(roster, witness)
    if disagreement or errors:
        result.update(status='SYNTHETIC_IMPLEMENTATIONS_DISAGREE', assignment=None,
                      evidence_kind='NO_ACCEPTED_RESULT', diagnostics=['ENCODING_DISAGREEMENT', *errors])
    elif witness is not None:
        # A concrete witness checked by both encodings settles satisfiability even
        # if one bounded search failed to find it. It does not settle input truth.
        result.update(status=SAT, assignment=witness, evidence_kind='SYNTHETIC_ASSIGNMENT',
                      search_exhausted=False, diagnostics=[])
    elif primary['status'] == UNSAT and secondary['status'] == UNSAT:
        result.update(status=UNSAT)
    else:
        result.update(status=INCOMPLETE, evidence_kind='DUAL_CONCLUSION_UNAVAILABLE',
                      search_exhausted=False, diagnostics=['AT_LEAST_ONE_SEARCH_INCOMPLETE'])
    result.update({**BOUNDARY, 'format': 'WAC_OFFLINE_ASSIGNMENT_REPORT_V2',
        'software_version': __version__, 'signed': False, 'ratified': False,
        'input_byte_hashes': hashes(profile_path, roster_path),
        'hash_scope': 'exact_local_input_bytes_only_no_original_upload_or_adoption_identity_claim',
        'profile_validation': validation,
        'search_method': 'two_bounded_encodings_lexical_DFS_and_MRV_forward_checking_not_role_lottery',
        'crosscheck': {'primary_status': primary['status'], 'reference_status': secondary['status'],
                      'primary_nodes': primary['nodes'], 'reference_nodes': secondary['nodes'],
                      'budget_per_engine': max_nodes, 'witness_checked_by_both': witness is not None and not errors,
                      'shared_component': 'roster_shape_validator', 'external_independent_audit': False},
        'decision_structure': {'seats': 4, 'distinct_domains_required': 4, 'approvals_required': 3,
                               'actual_ballots_verified': False},
        'appeal_structure': {'seats': 3, 'distinct_domains_required': 3, 'approvals_required': 2,
                            'capacity_is_declared_only': True},
        'not_established': list(LIMITATIONS),
        'report_serialization': 'Python_ASCII_sorted_indented_JSON_v1_NOT_RFC8785_NOT_FOR_ADOPTION',
    })
    result['report_body_sha256'] = report_hash(result)
    return result


def verify_certificate(profile_path, roster_path, cert):
    errors = []
    if not isinstance(cert, dict):
        return {**BOUNDARY, 'status': 'SYNTHETIC_WITNESS_INVALID', 'errors': ['REPORT_NOT_OBJECT']}
    body = {k: v for k, v in cert.items() if k != 'report_body_sha256'}
    if cert.get('report_body_sha256') != report_hash(body):
        errors.append('REPORT_BODY_HASH_MISMATCH')
    if cert.get('input_byte_hashes') != hashes(profile_path, roster_path):
        errors.append('LOCAL_INPUT_BYTE_HASH_MISMATCH')
    if validate_profile(read(profile_path))['errors']:
        errors.append('PROFILE_UNSUPPORTED')
    expected = {**BOUNDARY, 'status': SAT, 'evidence_kind': 'SYNTHETIC_ASSIGNMENT',
                'signed': False, 'ratified': False, 'format': 'WAC_OFFLINE_ASSIGNMENT_REPORT_V2',
                'not_established': LIMITATIONS}
    for key, value in expected.items():
        if type(cert.get(key)) is not type(value) or cert.get(key) != value:
            errors.append('INVALID_REPORT_BOUNDARY:' + key)
    roster = read(roster_path)
    errors.extend('PRIMARY:' + e for e in verify_assignment(roster, cert.get('assignment')))
    errors.extend('REFERENCE:' + e for e in verify_reference(roster, cert.get('assignment')))
    return {**BOUNDARY, 'status': 'SYNTHETIC_WITNESS_INVALID' if errors else 'SYNTHETIC_WITNESS_VALID',
            'errors': sorted(set(errors)),
            'verification_scope': 'two_constraint_encodings_shared_shape_parser_unverified_input_truth',
            'external_independent_audit': False}


def founding_proposal(cert):
    return {**BOUNDARY, 'format': 'WAC_SYNTHETIC_FOUNDING_DRAFT_V2',
            'status': 'SYNTHETIC_FOUNDING_DRAFT' if cert['status'] == SAT else cert['status'],
            'signed': False, 'ratified': False, 'adoption_manifest': None,
            'adoption_digest': None, 'genesis_receipt': None, 'grants': [],
            'assignment_report_body_sha256': cert['report_body_sha256'],
            'assignment_status': cert['status'], 'proposed_assignment': cert['assignment'],
            'proposal_only': True,
            'missing_before_any_real_adoption': ['exact_original_charter_and_profile_bytes',
                'complete_mission_manifest', 'legitimate_founder_and_resource_principal_choices',
                'verified_independent_enrollment_qualification_dependencies_and_capacity',
                'adopted_uniform_domain_selection_rules_and_procedure',
                'external_review_route_and_funded_continuity',
                'externally_authorized_keys_and_RFC8785_signature_implementation',
                'reviewed_enforcement_and_applicable_acceptance_tests',
                'independent_mode_specific_attestations'],
            'note': 'Synthetic worksheet only. Not an adoption payload, signature request, grant, appointment or readiness certificate.'}


def exit_code(result):
    status = result.get('status')
    if status in {SAT, 'SYNTHETIC_WITNESS_VALID', 'VALID_SUPPORTED_PROFILE',
                  'SYNTHETIC_FOUNDING_DRAFT', 'SYNTHETIC_ARITHMETIC_PASSES',
                  'SYNTHETIC_LOTTERY_ROLL_FROZEN', 'SYNTHETIC_LOTTERY_COMPLETE'}:
        return 0
    if status in {UNSAT, 'SYNTHETIC_ARITHMETIC_FAILS'}:
        return 3
    if status in {INCOMPLETE, 'SYNTHETIC_LOTTERY_DEAD_END'}:
        return 4
    if status == 'SYNTHETIC_IMPLEMENTATIONS_DISAGREE':
        return 5
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('validate-profile'); p.add_argument('profile')
    for command in ('assemble', 'draft-founding', 'founding-proposal', 'verify', 'prepare-lottery', 'lottery'):
        p = sub.add_parser(command)
        p.add_argument('--profile', required=True); p.add_argument('--roster', required=True)
        if command == 'verify':
            p.add_argument('--certificate', required=True)
        elif command == 'prepare-lottery':
            p.add_argument('--nominations', required=True)
        elif command == 'lottery':
            p.add_argument('--roll', required=True); p.add_argument('--seed', required=True)
        else:
            p.add_argument('--max-nodes', type=int, default=100000)
    p = sub.add_parser('vote'); p.add_argument('input')
    p = sub.add_parser('split'); p.add_argument('input')
    p = sub.add_parser('ballot'); p.add_argument('input')
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate-profile':
            result = validate_profile(read(args.profile))
        elif args.command in ('assemble', 'draft-founding', 'founding-proposal'):
            result = certificate(args.profile, args.roster, args.max_nodes)
            if args.command != 'assemble':
                result = founding_proposal(result)
        elif args.command == 'verify':
            result = verify_certificate(args.profile, args.roster, read(args.certificate))
        elif args.command in ('prepare-lottery', 'lottery'):
            check_profile(args.profile)
            roster = read(args.roster)
            inputs = hashes(args.profile, args.roster)
            if args.command == 'prepare-lottery':
                result = freeze_roll(roster, read(args.nominations), inputs)
            else:
                result = simulate(roster, read(args.roll), args.seed, inputs)
        else:
            func, flag = {'vote': (frozen_vote, 'both_chambers_pass'),
                          'split': (split_check, 'conserved'),
                          'ballot': (consequential_ballot, 'structurally_passes')}[args.command]
            result = func(**read(args.input))
            result.update({**BOUNDARY, 'status': 'SYNTHETIC_ARITHMETIC_PASSES' if result[flag]
                           else 'SYNTHETIC_ARITHMETIC_FAILS'})
        sys.stdout.buffer.write(report_bytes(result))
        return exit_code(result)
    except (InputError, OSError, TypeError, ValueError) as exc:
        sys.stdout.buffer.write(report_bytes({**BOUNDARY, 'status': 'INVALID_INPUT', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
