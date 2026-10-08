"""Two fully fabricated, bounded offline repair timelines; no external effects."""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'package'))
from wac_offline.amendments import AmendmentReplay, AmendmentError, digest


def case(invalidation=False):
    data = json.loads((ROOT / 'package/fixtures/amendment_example.json').read_text(encoding='utf-8'))
    policy, proposal, approval, procedure = (data[k] for k in ('policy', 'proposal', 'approval', 'procedure'))
    if not invalidation:
        policy['rules']['registrar_deadline'] = 19
        proposal['old_policy_digest'] = digest('Policy', policy)
        approval['proposal_digest'] = procedure['proposal_digest'] = digest('Proposal', proposal)
    replay = AmendmentReplay(policy)
    submitted = replay.submit(proposal, 'registrar', 0)
    if invalidation:
        legacy = replay.register(proposal, approval, procedure, 'registrar', 20)
        source = replay.invalidate(legacy, 'Supplied withdrawal of original approval', 21, ['fabricated-revocation'])
    else:
        try:
            replay.register(proposal, approval, procedure, 'registrar', 20)
        except AmendmentError as exc:
            if 'registrar deadline exceeded' not in str(exc):
                raise
        else:
            raise AssertionError('Deadline incorrectly approved registration')
        source = replay.events()[-1]['record']
    complaint = replay.complain(submitted, 'outsider-appeal', 'affected-nonmember',
                               'Supplied complaint requesting bounded independent review.',
                               ['fabricated-complaint'], 21, source)
    repaired = deepcopy(proposal)
    repaired.update(proposal_id='fresh-scoped-repair', submitted_at=22, activate_at=45)
    repaired['new_policy']['content'] += ' Exact independently reviewed synthetic correction.'
    repaired['new_policy_digest'] = digest('Policy', repaired['new_policy'])
    pd = digest('Proposal', repaired)
    approval.update(proposal_digest=pd, issued_at=42, reasons='Fresh old-rule affirmative decision.',
                    evidence_refs=['fabricated-fresh-approval'])
    procedure.update(proposal_digest=pd, notice_at=22, review_closed_at=42,
                     evidence_refs=['fabricated-fresh-notice-and-review'])
    grant = {'schema': 'cortac.amendment.resource-remedy-grant.v2', 'grant_id': 'one-case-grant',
             'complaint_digest': digest('Complaint', complaint), 'source_digest': complaint['source_digest'],
             'repair_proposal_digest': pd, 'old_policy_digest': repaired['old_policy_digest'], 'expected_epoch': 1,
             'remedy': 'REPAIR_INVALIDATION' if invalidation else 'REPLACE_REGISTRATION',
             'remedy_authorized': True, 'external_principals': ['owner'], 'resource_units': 2,
             'resource_purpose': 'SINGLE_CASE_REGISTRAR_REVIEW', 'issued_at': 42, 'expires_at': 80,
             'reason': 'Supplied old-principal remedy authorization plus finite case support.',
             'evidence_refs': ['fabricated-exact-remedy-grant'], 'authority': 'NONE', 'execution_enabled': False}
    unrelated = replay.complain(submitted, 'unrelated-case', 'other-affected-outsider',
                                'A distinct unresolved concern.', ['fabricated-unrelated-evidence'], 22)
    def review():
        return replay.review_repair(complaint, repaired, approval, procedure, grant,
                                    'appeal', 'replacement', 'substitute',
                                    'Supplied independent review and case-specific appointment.',
                                    ['fabricated-review-evidence'], 42)
    try:
        review()
    except AmendmentError as exc:
        if 'complaint unresolved' not in str(exc):
            raise
        unrelated_preserved = True
    else:
        raise AssertionError('Unrelated complaint was erased or bypassed')
    replay.resolve_complaint(unrelated, 'appeal', 'Independent disposition of this separate concern.',
                             ['fabricated-separate-disposition'], 42)
    reviewed = review()
    replacement = replay.register_replacement(reviewed, 42)
    if invalidation:
        try:
            replay.activate(legacy, 45)
        except AmendmentError:
            pass
        else:
            raise AssertionError('Historical certificate revived')
    result = replay.activate(replacement, 45)
    return {'source': source, 'complaint': complaint, 'review': reviewed,
            'replacement_registration': replacement, 'activation': result,
            'unrelated_hold_preserved': unrelated_preserved, 'state': replay.state(),
            'events': replay.events()}


def main():
    withholding = case()
    invalidation = case(invalidation=True)
    print(json.dumps({'example': 'FABRICATED_OFFLINE_CONTESTED_FIXTURE',
                      'replacement_activated': withholding['state']['epoch'] == 2,
                      'invalidation_repaired': invalidation['state']['epoch'] == 2,
                      'unrelated_hold_preserved': all(c['unrelated_hold_preserved'] for c in (withholding, invalidation)),
                      'authority': 'NONE', 'execution_enabled': False,
                      'controller_closure': 'SUPPLIED_UNVERIFIED',
                      'withholding': withholding, 'invalidation': invalidation}, indent=2))


if __name__ == '__main__':
    main()
