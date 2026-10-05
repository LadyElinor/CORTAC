"""Local-only command line. All commands merely read files and print reports."""
import argparse
import json
import sys
from . import __version__
from .io import InputError, read, report_bytes, report_hash, sha256_file
from .profile import validate_profile
from .solver import solve, verify_assignment
from .governance import frozen_vote, split_check, consequential_ballot

def certificate(profile_path, roster_path, max_nodes):
    validation = validate_profile(read(profile_path))
    if validation['errors']:
        raise InputError('profile rejected: ' + json.dumps(validation['errors']))
    result = solve(read(roster_path), max_nodes)
    result.update({
        'format': 'WAC_OFFLINE_ASSIGNMENT_REPORT_V1', 'software_version': __version__,
        'authority': 'NONE', 'signed': False, 'ratified': False,
        'input_byte_hashes': {'profile_local_bytes_sha256': sha256_file(profile_path),
                              'roster_local_bytes_sha256': sha256_file(roster_path)},
        'hash_scope': 'exact_local_input_bytes_only_no_original_upload_or_adoption_identity_claim',
        'profile_validation': validation,
        'decision_structure': {'seats': 4, 'distinct_domains_required': 4, 'approvals_required': 3,
                               'actual_ballots_verified': False},
        'appeal_structure': {'seats': 3, 'distinct_domains_required': 3, 'approvals_required': 2,
                            'capacity_is_declared_only': True},
        'not_established': ['real_world_independence', 'enrollment_or_credential_authenticity',
                            'dependency_truth_or_completeness', 'qualification_or_capacity_evidence',
                            'duty_or_evidence_sufficiency', 'external_appeal_route', 'review_funding',
                            'uniform_role_lottery_or_appointment', 'signed_adoption', 'ACTIVE_readiness'],
        'report_serialization': 'Python_ASCII_sorted_indented_JSON_v1_NOT_RFC8785_NOT_FOR_ADOPTION',
    })
    result['report_body_sha256'] = report_hash(result)
    return result

def verify_certificate(profile_path, roster_path, cert):
    errors = []
    if not isinstance(cert, dict):
        return {'status': 'INVALID_WITNESS', 'errors': ['REPORT_NOT_OBJECT'], 'authority': 'NONE'}
    body = {k: v for k, v in cert.items() if k != 'report_body_sha256'}
    if cert.get('report_body_sha256') != report_hash(body):
        errors.append('REPORT_BODY_HASH_MISMATCH')
    expected = {'profile_local_bytes_sha256': sha256_file(profile_path),
                'roster_local_bytes_sha256': sha256_file(roster_path)}
    if cert.get('input_byte_hashes') != expected:
        errors.append('LOCAL_INPUT_BYTE_HASH_MISMATCH')
    if validate_profile(read(profile_path))['errors']:
        errors.append('PROFILE_UNSUPPORTED')
    for key, value in {'status': 'FEASIBLE', 'evidence_kind': 'FEASIBLE_ASSIGNMENT',
                       'authority': 'NONE', 'authority_status': 'UNINITIALIZED_NO_EXECUTION',
                       'execution_enabled': False, 'signed': False, 'ratified': False,
                       'simulation_only': True, 'format': 'WAC_OFFLINE_ASSIGNMENT_REPORT_V1'}.items():
        if type(cert.get(key)) is not type(value) or cert.get(key) != value:
            errors.append('INVALID_REPORT_BOUNDARY:' + key)
    errors.extend(verify_assignment(read(roster_path), cert.get('assignment')))
    return {'status': 'INVALID_WITNESS' if errors else 'VALID_SYNTHETIC_ASSIGNMENT_WITNESS',
            'errors': sorted(set(errors)), 'authority': 'NONE',
            'authority_status': 'UNINITIALIZED_NO_EXECUTION', 'execution_enabled': False,
            'verification_scope': 'search_independent_recheck_using_same_declared_constraint_model'}

def founding_proposal(cert):
    return {'format': 'WAC_OFFLINE_FOUNDING_PROPOSAL_V1', 'authority': 'NONE',
            'authority_status': 'UNINITIALIZED_NO_EXECUTION', 'execution_enabled': False,
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
            'note': 'This is not an adoption payload, signature request, grant, appointment or readiness certificate.'}

def main(argv=None):
    parser = argparse.ArgumentParser(description='WAC local-only synthetic assignment reference tools')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('validate-profile'); p.add_argument('profile')
    for command in ('assemble', 'founding-proposal', 'verify'):
        p = sub.add_parser(command)
        p.add_argument('--profile', required=True); p.add_argument('--roster', required=True)
        if command == 'verify':
            p.add_argument('--certificate', required=True)
        else:
            p.add_argument('--max-nodes', type=int, default=100000)
    p = sub.add_parser('vote'); p.add_argument('input')
    p = sub.add_parser('split'); p.add_argument('input')
    p = sub.add_parser('ballot'); p.add_argument('input')
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate-profile':
            result = validate_profile(read(args.profile))
        elif args.command in ('assemble', 'founding-proposal'):
            result = certificate(args.profile, args.roster, args.max_nodes)
            if args.command == 'founding-proposal':
                result = founding_proposal(result)
        elif args.command == 'verify':
            result = verify_certificate(args.profile, args.roster, read(args.certificate))
        elif args.command == 'vote':
            result = frozen_vote(**read(args.input))
        elif args.command == 'split':
            result = split_check(**read(args.input))
        else:
            result = consequential_ballot(**read(args.input))
        sys.stdout.buffer.write(report_bytes(result))
        return 2 if result.get('status') == 'INVALID_OR_UNSUPPORTED_PROFILE' else 0
    except (InputError, OSError, TypeError, ValueError) as exc:
        sys.stdout.buffer.write(report_bytes({'status': 'INVALID_INPUT', 'error': str(exc),
                                            'authority': 'NONE', 'execution_enabled': False}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
