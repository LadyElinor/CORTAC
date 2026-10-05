"""Exact arithmetic on frozen, synthetic rolls; no ballots or signatures verified."""
from fractions import Fraction
from .io import InputError

def _ids(value, label, nonempty=False):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise InputError(label + ' must be a list of nonempty string IDs')
    if len(value) != len(set(value)) or (nonempty and not value):
        raise InputError(label + ' must contain unique IDs' + (' and be nonempty' if nonempty else ''))


def rational(pair):
    if not isinstance(pair, list) or len(pair) != 2 or any(type(v) is not int for v in pair):
        raise InputError('weight must be [integer numerator, integer denominator]')
    if pair[0] < 0 or pair[1] <= 0:
        raise InputError('weight must be nonnegative with positive denominator')
    return Fraction(*pair)

def split_check(predecessor, successors):
    if not isinstance(successors, dict) or not successors:
        raise InputError('successors must be a nonempty unique-ID map')
    _ids(list(successors), 'successor keys', nonempty=True)
    p = rational(predecessor)
    total = sum((rational(v) for v in successors.values()), Fraction())
    return {'conserved': p == total, 'predecessor': [p.numerator, p.denominator],
            'successor_total': [total.numerator, total.denominator]}

def frozen_vote(domain_roll, yes_domains, cell_weights, yes_cells, threshold):
    _ids(domain_roll, 'domain roll', nonempty=True)
    _ids(yes_domains, 'yes domains')
    _ids(yes_cells, 'yes cells')
    if not isinstance(domain_roll, list) or not domain_roll or len(domain_roll) != len(set(domain_roll)):
        raise InputError('frozen domain roll must contain unique domains and cannot be empty')
    if not isinstance(yes_domains, list) or len(yes_domains) != len(set(yes_domains)):
        raise InputError('each domain has at most one yes vote')
    if not set(yes_domains) <= set(domain_roll):
        raise InputError('yes domain outside frozen roll')
    if not isinstance(cell_weights, dict) or not cell_weights:
        raise InputError('nonempty frozen cell weight ledger required')
    if not isinstance(yes_cells, list) or len(yes_cells) != len(set(yes_cells)) or not set(yes_cells) <= set(cell_weights):
        raise InputError('yes cells must be unique members of frozen ledger')
    _ids(list(cell_weights), 'cell weight keys', nonempty=True)
    t = rational(threshold)
    if not 0 < t <= 1:
        raise InputError('threshold must be in (0,1]')
    weights = {k: rational(v) for k, v in cell_weights.items()}
    total = sum(weights.values(), Fraction())
    if total <= 0:
        raise InputError('total frozen cell weight must be positive')
    yes = sum((weights[k] for k in yes_cells), Fraction())
    required = (len(domain_roll) * t.numerator + t.denominator - 1) // t.denominator
    domain_pass = len(yes_domains) >= required
    cell_pass = yes >= total * t
    return {'domain_denominator': len(domain_roll), 'domain_yes': len(yes_domains),
            'required_domain_yes': required, 'cell_denominator': [total.numerator, total.denominator],
            'cell_yes': [yes.numerator, yes.denominator], 'domain_pass': domain_pass,
            'cell_pass': cell_pass, 'both_chambers_pass': domain_pass and cell_pass,
            'scope': 'arithmetic_only_no_vote_authorization_or_roll_verification'}

def consequential_ballot(seat_ids, yes_ids, protected_failure=False):
    if not isinstance(seat_ids, list) or not isinstance(yes_ids, list) or type(protected_failure) is not bool:
        raise InputError('ballot requires seat and yes lists plus boolean protected_failure')
    if any(not isinstance(x, str) or not x for x in seat_ids + yes_ids):
        raise InputError('ballot identities must be nonempty strings')
    if len(seat_ids) != 4 or len(set(seat_ids)) != 4:
        return {'structurally_passes': False, 'reason': 'FOUR_DISTINCT_ASSIGNED_SEATS_REQUIRED'}
    if len(set(yes_ids)) != len(yes_ids) or not set(yes_ids) <= set(seat_ids):
        return {'structurally_passes': False, 'reason': 'INVALID_BALLOT_MEMBERSHIP'}
    return {'structurally_passes': not protected_failure and len(yes_ids) >= 3,
            'approvals': len(yes_ids), 'required': 3, 'seats': 4,
            'protected_failure': protected_failure,
            'scope': 'count_only_requires_separate_assignment_and_authority_checks'}
