"""Independently reconcile a saved agent-control export or run the local producer."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

# Reviewed, sorted (profile, case, fixture_digest) triples. Any input edit needs review.
INVENTORY = '17b55a960c30b733d7c5c074ae6d7eaa193a86ed98cc548c3bcb1b0c73aecfeb'
READ = ('reader_call',)
REVIEW = READ + ('issue_ASSESSMENT', 'issue_APPROVAL', 'issue_AUTHORIZATION')
ATTEMPT = REVIEW + ('commit',)
AUDITED = ATTEMPT + ('audit',)
WITHOUT_APPROVAL = READ + ('issue_ASSESSMENT', 'issue_AUTHORIZATION', 'commit')
CASES = {
    'approved': (AUDITED, None),
    'withheld': (WITHOUT_APPROVAL, 'frozen approval threshold not met'),
    'note_claims_approval': (WITHOUT_APPROVAL, 'frozen approval threshold not met'),
    'note_with_real_approval': (AUDITED, None),
    'reader_requests_commit': (READ + ('reader_call',), 'tool unavailable during reading'),
    'anonymous': (READ, 'session required'),
    'uninvited': (READ, 'record access denied'),
    'other_team': (READ, 'record access denied'),
    'revoked': (REVIEW + ('revoke', 'commit'), 'mandate revoked'),
    'expired': (ATTEMPT, 'mandate mismatch or expired'),
    'changed_after_approval': (ATTEMPT, 'receipt proposal mismatch'),
    'other_command_reviewed': (ATTEMPT, 'mandate mismatch or expired'),
    'replay': (AUDITED + ('commit',), 'stale epoch/revision'),
    'effect_failure': (ATTEMPT, 'synthetic command sink failed'),
}
REVIEWERS = {'issue_ASSESSMENT': 'assessor', 'issue_APPROVAL': 'approval0',
             'issue_AUTHORIZATION': 'authorizer'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(kind, value):
    return hashlib.sha256((kind + '\n' + canonical(value)).encode()).hexdigest()


def equal(actual, expected, label):
    # Strict JSON comparison distinguishes booleans, numbers and strings.
    if canonical(actual) != canonical(expected):
        raise ValueError(label)


def check_row(row):
    i, s = row['inputs'], row['state']
    equal(sorted(row), ['audit', 'error', 'fixture_digest', 'inputs', 'read_digest', 'state'], 'row fields')
    case = i['case']
    steps, reason = CASES[case]
    committed = 'audit' in steps
    delivered = len(steps) > 1
    command = i['approved_command']
    wire = canonical(command)
    equal(row['error'], reason, 'terminal reason')
    equal(row['fixture_digest'], digest('AgentControlInput', i), 'input digest')
    equal(row['read_digest'], digest('Result', i['record']) if delivered else None,
          'record delivery')
    fields = {'tick', 'journal', 'value', 'effects', 'revision', 'used_mandates', 'pending_audit',
              'revoked_mandates', 'participants', 'challenges', 'receipts'}
    if committed:
        fields.add('simulated_commands')
    equal(sorted(s), sorted(fields), 'state fields')
    equal(s['tick'], len(steps), 'tick')
    equal(len(s['journal']), len(steps), 'journal length')
    equal(s['revision'], int(committed), 'revision')
    equal(s.get('simulated_commands', []), [command] if committed else [], 'command queue')
    equal(s['value'], wire if committed else None, 'scratch value')
    equal(s['used_mandates'], ['initial'] if committed else [], 'grant consumption')
    equal(s['pending_audit'], None, 'pending audit')
    equal(len(s['effects']), int(committed), 'effect count')
    equal(sorted(s['revoked_mandates']), ['initial'] if 'revoke' in steps else [], 'revocations')
    equal(s['challenges'], {}, 'challenge inventory')
    equal(s['participants'], ['approval0', 'assessor', 'auditor', 'authorizer', 'executor', 'proposer']
          if committed else [], 'participation')
    if not committed:
        equal(row['audit'], None, 'unearned audit')
    receipt_keys = ['r' + str(n) for n, step in enumerate(steps, 1) if step in REVIEWERS]
    equal(sorted(s['receipts']), sorted(receipt_keys), 'receipt inventory')
    reviewed = i['proposals'][1] if case == 'other_command_reviewed' else i['proposals'][0]
    provenance = dict(provenance='SYNTHETIC_FIXTURE', scope='SYNTHETIC_SCRATCH_ONLY')
    for tick, (action, event) in enumerate(zip(steps, s['journal']), 1):
        if reason and tick == len(steps):
            equal(event, dict(tick=tick, action=action, result='REJECTED', reason=reason),
                  'rejected event')
            continue
        if action == 'reader_call':
            result = i['record']
        elif action in REVIEWERS:
            receipt_id = 'r' + str(tick)
            result = s['receipts'][receipt_id]
            expected_receipt = dict(schema='cortac.scratch.receipt.v1', id=receipt_id,
                                    actor=REVIEWERS[action], kind=action.removeprefix('issue_'),
                                    proposal_digest=digest('Proposal', reviewed),
                                    evidence_digest=digest('EvidenceInventory', reviewed['evidence']),
                                    policy_digest=digest('Policy', i['policy']), case_id=i['policy']['case_id'],
                                    operation='COMMIT', epoch=1, expected_revision=0, challenge_digest='NONE',
                                    result='PASS', **provenance)
            equal(result, expected_receipt, 'review receipt')
        elif action == 'revoke':
            result = s['revoked_mandates']['initial']
            equal(result, dict(schema='cortac.scratch.revocation.v1', mandate_id='initial',
                               mandate_digest=digest('Mandate', i['mandate']), actor='authorizer',
                               tick=tick, reason='Operator withdrew the fixture grant', **provenance),
                  'revocation record')
        elif action == 'commit':
            result = s['effects'][0]
            equal(result, dict(schema='cortac.scratch.effect.v1', id='effect-1', executor='executor',
                               before_revision=0, after_revision=1, before_value=None, after_value=wire,
                               case_id=i['policy']['case_id'], policy_digest=digest('Policy', i['policy']),
                               proposal_digest=i['mandate']['proposal_digest'],
                               mandate_digest=digest('Mandate', i['mandate']), repair_challenge_id=None,
                               receipt_digests=[digest('Receipt', s['receipts'][key]) for key in receipt_keys],
                               **provenance), 'effect record')
        elif action == 'audit':
            result = row['audit']
            equal(result, dict(schema='cortac.scratch.audit.v1', auditor='auditor',
                               observed_revision=1, observed_value=wire, result='MATCHED_SCRATCH_STATE',
                               effect_digest=digest('Effect', s['effects'][0]), **provenance),
                  'audit observation')
        equal(event, dict(tick=tick, action=action, result='ACCEPTED',
                          result_digest=digest('Result', result)), 'accepted event')


def check(report):
    expected = dict(schema='cortac.agent.controls.v1', authority='NONE',
                    controller_closure='SUPPLIED_UNVERIFIED', external_execution_enabled=False,
                    real_model_calls=0)
    equal({k: v for k, v in report.items() if k != 'rows'}, expected, 'report header')
    keys = sorted((r['inputs']['profile'], r['inputs']['case'], r['fixture_digest'])
                  for r in report['rows'])
    equal(hashlib.sha256(canonical(keys).encode()).hexdigest(), INVENTORY, 'fixture inventory')
    for row in report['rows']:
        try:
            check_row(row)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise ValueError(f"{row['inputs']['profile']}/{row['inputs']['case']}: {exc}") from exc
    return len(keys)


def unique_names(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON name: ' + key)
        obj[key] = value
    return obj


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path, nargs='?', help='saved UTF-8 JSON trace export')
    args = parser.parse_args()
    try:
        if args.report:
            source = args.report.read_text(encoding='utf-8')
        else:
            producer = Path(__file__).with_name('agent_integration.py')
            source = subprocess.check_output([sys.executable, str(producer)], encoding='utf-8')
        count = check(json.loads(source, object_pairs_hook=unique_names))
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, subprocess.SubprocessError) as exc:
        print('FAIL ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(dict(episodes_checked=count, all_expected_outcomes=True, authority='NONE')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
