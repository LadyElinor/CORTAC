"""Closed task/decision contracts; host-owned checks never come from a proposal."""
from . import VERSION, SCOPE
from .repository import path_name, validate_inventory, HEX, SHA
from ..decision_records import validate_protected_limits
from ..scaffold_v1.wire import bounded, digest, exact, integer, label


def task(value):
    bounded(value)
    exact(value, ('version', 'id', 'base_commit', 'allowed_paths', 'checks', 'proposer',
                  'reviewer', 'proposer_controller', 'reviewer_controller', 'protected_limits',
                  'purpose', 'parent_receipt'))
    if value['version'] != VERSION or type(value['base_commit']) is not str or not HEX.fullmatch(value['base_commit']):
        raise ValueError('unsupported task/base')
    for name in ('id', 'proposer', 'reviewer', 'proposer_controller', 'reviewer_controller'):
        label(value[name])
    if value['proposer'] == value['reviewer']:
        raise ValueError('separate named review role required; control may still overlap')
    paths = value['allowed_paths']
    if type(paths) is not list or not 1 <= len(paths) <= 64 or len(set(paths)) != len(paths):
        raise ValueError('one to 64 unique allowed paths required')
    for name in paths:
        path_name(name)
    if type(value['purpose']) is not str or not value['purpose'].strip() or len(value['purpose']) > 4000:
        raise ValueError('bounded task purpose required')
    if value['parent_receipt'] is not None and (type(value['parent_receipt']) is not str or not SHA.fullmatch(value['parent_receipt'])):
        raise ValueError('parent is an unauthenticated receipt digest, not authority')
    validate_protected_limits(value['protected_limits'])
    checks = value['checks']
    if type(checks) is not list or not 1 <= len(checks) <= 8:
        raise ValueError('one to eight declared checks required')
    seen = set()
    for check in checks:
        exact(check, ('id', 'argv', 'cwd', 'expected_exit', 'timeout_seconds'))
        label(check['id'])
        if check['id'] in seen:
            raise ValueError('duplicate check')
        seen.add(check['id'])
        argv = check['argv']
        if (type(argv) is not list or not 2 <= len(argv) <= 32 or argv[0] != '{python}'
                or any(type(a) is not str or not a or len(a) > 4000 or '\0' in a for a in argv)):
            raise ValueError('bounded host Python argv required')
        if check['cwd'] != '.':
            path_name(check['cwd'])
        integer(check['expected_exit'], 255)
        integer(check['timeout_seconds'], 120)
        if check['timeout_seconds'] == 0:
            raise ValueError('positive timeout required')
    return value


def brief(genesis):
    t = genesis['task']
    # Execution argv stay with the custodian; the participant sees check IDs.
    result = dict(version=VERSION, **SCOPE, task_id=t['id'], base_commit=t['base_commit'],
                  base_inventory=genesis['base'], allowed_paths=t['allowed_paths'], purpose=t['purpose'],
                  checks=[c['id'] for c in t['checks']], protected_limits=t['protected_limits'],
                  choices=['propose', 'decline', 'wait', 'request-evidence'])
    return dict(result, brief_id=digest(result))


def decision(genesis, response):
    bounded(response)
    if type(response) is not dict or response.get('version') != VERSION or response.get('brief_id') != brief(genesis)['brief_id']:
        raise ValueError('decision binding mismatch')
    common = ('version', 'brief_id', 'choice', 'reason')
    if response.get('choice') == 'propose':
        exact(response, (*common, 'candidate_digest'))
        if type(response['candidate_digest']) is not str or not SHA.fullmatch(response['candidate_digest']):
            raise ValueError('candidate digest required')
    else:
        exact(response, common)
        if response['choice'] not in ('decline', 'wait', 'request-evidence'):
            raise ValueError('unsupported repository decision')
    if type(response['reason']) is not str or not response['reason'].strip() or len(response['reason']) > 4000:
        raise ValueError('bounded reason required')
