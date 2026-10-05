"""Domain-first lottery simulation with frozen nominations and no silent redraw.

The freeze is a byte commitment, not authenticated evidence of chronology.
The seeded stream is reproducible test randomness, not a public random beacon.
"""
import hashlib
import re

from .io import InputError, report_hash, report_bytes
from .reference import ConstraintTable, ROLES, verify_reference
from .solver import verify_assignment

FREEZE_FORMAT = 'CORTAC_SYNTHETIC_LOTTERY_ROLL_V1'
POLICY = 'fixed_role_order_domain_first_frozen_nominee_no_redraw_v1'


def uniform_index(size, next_word, bits=256):
    """Reject the uneven tail; conditional on uniform words, indices are uniform."""
    if type(size) is not int or not 0 < size <= 1 << bits:
        raise InputError('invalid domain count for random word size')
    limit = (1 << bits) - ((1 << bits) % size)
    while True:
        word = next_word()
        if type(word) is not int or not 0 <= word < 1 << bits:
            raise InputError('random word outside declared range')
        if word < limit:
            return word % size


class SeedStream:
    def __init__(self, seed):
        if not isinstance(seed, str) or re.fullmatch('[0-9a-f]{64}', seed) is None:
            raise InputError('seed must be exactly 64 lowercase hexadecimal characters')
        self.seed = bytes.fromhex(seed)
        self.counter = 0

    def word(self):
        data = b'CORTAC_SYNTHETIC_LOTTERY_V1\x00' + self.seed + self.counter.to_bytes(8, 'big')
        self.counter += 1
        return int.from_bytes(hashlib.sha256(data).digest(), 'big')


def freeze_roll(roster, nominations, input_byte_hashes):
    table = ConstraintTable(roster)
    if table.fixed_errors:
        raise InputError('fixed parties invalid: ' + repr(table.fixed_errors))
    if not isinstance(nominations, dict) or set(nominations) != set(ROLES):
        raise InputError('nominations must name every concrete role exactly once')
    roll = {}
    for role in ROLES:
        groups = {}
        for ident in table.domains[role]:
            domain = table.records[ident]['domain']
            groups.setdefault(domain, []).append(ident)
        nominees = nominations[role]
        if not isinstance(nominees, dict) or set(nominees) != set(groups):
            raise InputError('nomination domains must equal the unary-eligible domain roll: ' + role)
        for domain, ident in nominees.items():
            if not isinstance(ident, str) or ident not in groups[domain]:
                raise InputError('nominee is not qualified and unconflicted: ' + role + '/' + domain)
        roll[role] = {domain: nominees[domain] for domain in sorted(nominees)}
    body = {'format': FREEZE_FORMAT, 'status': 'SYNTHETIC_LOTTERY_ROLL_FROZEN',
            'policy': POLICY, 'role_order': list(ROLES), 'nominations': roll,
            'input_byte_hashes': input_byte_hashes,
            'authority': 'NONE', 'simulation_only': True, 'execution_enabled': False,
            'controller_closure': 'SUPPLIED_UNVERIFIED',
            'scope': 'declared_synthetic_domain_draw_only_no_appointment',
            'seed_procedure': 'user_supplied_256_bit_seed_SHA256_counter_rejection_sampling',
            'chronology_verified': False, 'seed_unpredictability_verified': False,
            'delegate_rule': 'each_domain_supplies_one_nominee_per_role_before_simulated_draw',
            'restart_rule': 'none_report_first_dead_end_no_automatic_redraw',
            'serialization': 'Python_ASCII_sorted_indented_JSON_v1_NOT_RFC8785'}
    body['roll_body_sha256'] = report_hash(body)
    return body


def simulate(roster, frozen, seed, input_byte_hashes):
    if not isinstance(frozen, dict):
        raise InputError('frozen roll must be an object')
    expected = freeze_roll(roster, frozen.get('nominations'), input_byte_hashes)
    # JSON bytes distinguish booleans and integers; Python equality does not.
    if report_bytes(frozen) != report_bytes(expected):
        raise InputError('frozen roll differs from the complete supported contract or local inputs')
    table, stream = ConstraintTable(roster), SeedStream(seed)
    assigned, trace = {}, []
    for role in ROLES:
        nominees = frozen['nominations'][role]
        domains = [d for d in sorted(nominees) if table.compatible(role, nominees[d], assigned)]
        if not domains:
            trace.append({'role': role, 'eligible_domains': [], 'selected_domain': None, 'nominee': None})
            break
        before = stream.counter
        index = uniform_index(len(domains), stream.word)
        domain = domains[index]
        ident = nominees[domain]
        assigned[role] = ident
        trace.append({'role': role, 'eligible_domains': domains, 'selected_domain': domain,
                      'nominee': ident, 'domain_probability': [1, len(domains)],
                      'random_words_used': stream.counter - before})
    complete = len(assigned) == len(ROLES)
    errors = (verify_assignment(roster, assigned) + verify_reference(roster, assigned)) if complete else []
    status = ('SYNTHETIC_IMPLEMENTATIONS_DISAGREE' if errors else
              'SYNTHETIC_LOTTERY_COMPLETE' if complete else 'SYNTHETIC_LOTTERY_DEAD_END')
    result = {'format': 'CORTAC_SYNTHETIC_LOTTERY_REPORT_V1', 'status': status,
              'authority': 'NONE', 'execution_enabled': False, 'simulation_only': True,
              'scope': 'declared_synthetic_domain_draw_only_no_appointment',
              'controller_closure': 'SUPPLIED_UNVERIFIED',
              'seed': seed, 'policy': POLICY, 'roll_body_sha256': frozen['roll_body_sha256'],
              'input_byte_hashes': input_byte_hashes, 'trace': trace,
              'partial_assignment': assigned, 'assignment': assigned if complete and not errors else None,
              'errors': errors, 'redraws': 0, 'random_words_used': stream.counter,
              'no_inference_of_infeasibility_from_dead_end': True,
              'uniformity_scope': 'one_entry_per_currently_eligible_domain_at_each_draw_only',
              'not_established': ['uniform_distribution_over_complete_assignments',
                  'real_controller_closure', 'authenticated_domain_nominations',
                  'freeze_before_unpredictable_seed', 'public_randomness', 'appointment_authority']}
    result['report_body_sha256'] = report_hash(result)
    return result
