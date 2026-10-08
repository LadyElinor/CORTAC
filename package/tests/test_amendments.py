"""Synthetic reference-model tests, not an institutional or live-gateway trial."""
import copy
from concurrent.futures import ThreadPoolExecutor
import unittest
import json
from pathlib import Path

from wac_offline.amendments import AmendmentReplay, AmendmentError, digest, validate_record


def fixture():
    actors = ['proposer', 'decision1', 'decision2', 'registrar', 'owner', 'appeal', 'replacement']
    policy = {'schema': 'cortac.amendment.policy.v2', 'society_id': 'test-cell', 'attempt_id': 'sandbox-1',
              'content': 'Synthetic exact charter and boundary configuration v1; no live authority.',
              'rules': {'actors': [{'id': a, 'domain': a} for a in actors], 'decisionmakers': ['decision1', 'decision2'],
                        'quorum': 2, 'registrars': ['registrar'], 'external_principals': ['owner'],
                        'appeal_authorities': ['appeal'], 'replacement_authorities': ['replacement'],
                        'notice_period': 10, 'challenge_period': 10, 'registrar_deadline': 100}}
    policy['protected_limits'] = [{'id': 'independent-review', 'commitment': 'Preserve independent review of consequential amendments.'}]
    policy['rules'].update(replacement_registrars=['substitute'], review_deadline=100, repair_deadline=100, repair_resource_limit=10, repair_resource_cost=2)
    policy['rules']['actors'].append({'id': 'substitute', 'domain': 'substitute'})
    new = copy.deepcopy(policy)
    new['content'] = 'Synthetic exact charter and boundary configuration v2; no live authority.'
    proposal = {'schema': 'cortac.amendment.proposal.v2', 'proposal_id': 'change-1', 'proposer': 'proposer',
                'old_policy_digest': digest('Policy', policy), 'new_policy_digest': digest('Policy', new),
                'expected_epoch': 1, 'new_policy': new, 'submitted_at': 0, 'activate_at': 30, 'expires_at': 80}
    approval = {'schema': 'cortac.amendment.approval.v2', 'proposal_digest': digest('Proposal', proposal),
                'decision': 'APPROVE', 'decisionmakers': ['decision1', 'decision2'], 'external_principals': ['owner'],
                'issued_at': 20, 'reasons': 'Synthetic fixture decision', 'evidence_refs': ['fixture-approval']}
    procedure = {'schema': 'cortac.amendment.procedure.v2', 'proposal_digest': digest('Proposal', proposal),
                 'notice_at': 0, 'review_closed_at': 20, 'conflicts_cleared': True,
                 'challenge_inventory_complete': True, 'mandatory_checks_passed': True,
                 'challenges': [], 'evidence_refs': ['fixture-notice-and-conflicts']}
    approval['decision_record'] = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/decision_record.json').read_text())
    return policy, proposal, approval, procedure


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.proposal, self.approval, self.procedure = fixture()
        self.model = AmendmentReplay(self.policy)

    def bind(self):
        self.proposal['new_policy_digest'] = digest('Policy', self.proposal['new_policy'])
        self.approval['proposal_digest'] = self.procedure['proposal_digest'] = digest('Proposal', self.proposal)

    def register(self, now=20):
        return self.model.register(self.proposal, self.approval, self.procedure, 'registrar', now)

    def reject(self):
        with self.assertRaises(AmendmentError):
            self.register()

    def test_success_scope_and_epoch_fence(self):
        old = self.model.state()
        cert = self.register()
        self.assertEqual(self.model.state(), old)
        result = self.model.activate(cert, 30)
        self.assertEqual(result['status'], 'SYNTHETICALLY_ACTIVATED')
        self.assertEqual(result['authority'], 'NONE')
        self.assertIs(result['execution_enabled'], False)
        self.assertFalse(self.model.is_current(old['policy_digest'], old['epoch']))
        self.assertTrue(self.model.is_current(result['new_policy_digest'], 2))

    def test_missing_principal(self):
        self.approval['external_principals'] = []
        self.reject()

    def test_new_rules_cannot_self_authorize(self):
        new = self.proposal['new_policy']['rules']
        new['quorum'] = 1
        new['decisionmakers'] = ['proposer']
        new['external_principals'] = ['proposer']
        new['registrars'] = ['proposer']
        self.bind()
        self.approval['decisionmakers'] = ['proposer']
        self.approval['external_principals'] = ['proposer']
        self.reject()

    def test_old_rules_authorize_changed_rules(self):
        self.proposal['new_policy']['rules']['quorum'] = 1
        self.bind()
        cert = self.register()
        self.model.activate(cert, 30)
        self.assertEqual(self.model.state()['epoch'], 2)

    def test_unknown_field_and_bool_epoch_rejected(self):
        for mutation in ('extra', 'epoch'):
            with self.subTest(mutation=mutation):
                p = copy.deepcopy(self.proposal)
                if mutation == 'extra': p['emergency_override'] = True
                else: p['expected_epoch'] = True
                with self.assertRaises(AmendmentError):
                    self.model.register(p, self.approval, self.procedure, 'registrar', 20)

    def test_bool_and_float_quorum_rejected(self):
        for q in (True, 1.0, float('nan'), float('inf')):
            with self.subTest(q=q):
                p = copy.deepcopy(self.policy)
                p['rules']['quorum'] = q
                with self.assertRaises(AmendmentError): AmendmentReplay(p)

    def test_duplicate_vote_rejected(self):
        self.approval['decisionmakers'] = ['decision1', 'decision1']
        self.reject()

    def test_alias_domains_do_not_add_quorum(self):
        self.policy['rules']['actors'][2]['domain'] = 'decision1'
        with self.assertRaises(AmendmentError): AmendmentReplay(self.policy)

    def test_proposer_cannot_supply_decisive_review(self):
        self.proposal['proposer'] = 'decision1'
        self.bind()
        self.reject()

    def test_registrar_conflict_domain(self):
        self.policy['rules']['actors'][3]['domain'] = 'decision1'
        self.model = AmendmentReplay(self.policy)
        self.proposal['old_policy_digest'] = digest('Policy', self.policy)
        self.bind()
        self.reject()

    def test_unauthorized_registrar(self):
        with self.assertRaises(AmendmentError):
            self.model.register(self.proposal, self.approval, self.procedure, 'proposer', 20)

    def test_notice_period_cannot_be_shortened_by_proposal(self):
        self.proposal['new_policy']['rules']['notice_period'] = 0
        self.procedure['review_closed_at'] = 10
        self.bind()
        self.reject()

    def test_unresolved_checks_hold(self):
        for key in ('conflicts_cleared', 'challenge_inventory_complete', 'mandatory_checks_passed'):
            with self.subTest(key=key):
                self.procedure[key] = False
                self.reject()
                self.procedure[key] = True

    def test_pending_challenge_blocks_registration(self):
        self.procedure['challenges'] = [{'id': 'c1', 'disposition': 'OPEN', 'reviewer': 'appeal', 'reason': 'pending', 'evidence_ref': 'fixture'}]
        self.reject()

    def test_independent_resolved_challenge(self):
        self.procedure['challenges'] = [{'id': 'c1', 'disposition': 'RESOLVED', 'reviewer': 'appeal', 'reason': 'reviewed', 'evidence_ref': 'fixture'}]
        self.assertEqual(self.register()['authority'], 'NONE')

    def test_wrong_challenge_reviewer(self):
        self.procedure['challenges'] = [{'id': 'c1', 'disposition': 'RESOLVED', 'reviewer': 'registrar', 'reason': 'reviewed', 'evidence_ref': 'fixture'}]
        self.reject()

    def test_approval_and_procedure_exact_binding(self):
        for record in (self.approval, self.procedure):
            original = record['proposal_digest']
            record['proposal_digest'] = '0' * 64
            self.reject()
            record['proposal_digest'] = original

    def test_exact_new_digest(self):
        self.proposal['new_policy']['content'] += 'changed'
        self.reject()

    def test_wrong_society_or_attempt(self):
        for field in ('society_id', 'attempt_id'):
            old = self.proposal['new_policy'][field]
            self.proposal['new_policy'][field] = 'another'
            self.bind()
            self.reject()
            self.proposal['new_policy'][field] = old

    def test_no_silence_approval(self):
        self.approval['decision'] = 'HOLD'
        self.reject()

    def test_deadline_expiry_no_silent_approval(self):
        self.policy['rules']['registrar_deadline'] = 19
        self.model = AmendmentReplay(self.policy)
        self.proposal['old_policy_digest'] = digest('Policy', self.policy)
        self.bind()
        self.reject()
        self.assertEqual(self.model.state()['epoch'], 1)

    def test_reasoned_refusal_retains_routes(self):
        r = self.model.refuse(self.proposal, 'registrar', 'Missing independent evidence', ['fixture'], 20)
        self.assertEqual(r['deadline'], 100)
        self.assertEqual(r['appeal_authorities'], ['appeal'])
        self.assertEqual(r['replacement_authorities'], ['replacement'])
        self.assertEqual(self.model.state()['epoch'], 1)
        with self.assertRaises(AmendmentError):
            self.model.refuse(self.proposal, 'registrar', '', ['fixture'], 20)

    def test_early_late_and_replayed_activation(self):
        cert = self.register()
        with self.assertRaises(AmendmentError): self.model.activate(cert, 29)
        self.model.activate(cert, 30)
        with self.assertRaises(AmendmentError): self.model.activate(cert, 30)
        other = AmendmentReplay(self.policy)
        cert = other.register(self.proposal, self.approval, self.procedure, 'registrar', 20)
        with self.assertRaises(AmendmentError): other.activate(cert, 81)

    def test_changed_or_fabricated_certificate(self):
        cert = self.register()
        other = AmendmentReplay(self.policy)
        with self.assertRaises(AmendmentError): other.activate(cert, 30)
        for key, value in [('activate_at', 0), ('authority', 'ACTIVE'), ('execution_enabled', True)]:
            modified = copy.deepcopy(cert)
            modified[key] = value
            with self.assertRaises(AmendmentError): self.model.activate(modified, 30)

    def test_deep_copy_freezes_inputs_and_return_values(self):
        cert = self.register()
        expected = cert['new_policy_digest']
        self.proposal['new_policy']['content'] = 'tampered after registration'
        self.approval['decisionmakers'].clear()
        self.procedure['mandatory_checks_passed'] = False
        self.policy['content'] = 'mutated caller original'
        self.model.events()[0]['record']['activate_at'] = 0
        self.model.activate(cert, 30)
        self.assertEqual(self.model.state()['policy_digest'], expected)

    def test_competing_activation_compare_and_set(self):
        first = self.register()
        self.proposal['proposal_id'] = 'change-2'
        self.proposal['new_policy']['content'] = 'competing policy'
        self.bind()
        second = self.register()
        def attempt(cert):
            try: return self.model.activate(cert, 30)['status']
            except AmendmentError: return 'REJECTED'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, [first, second]))
        self.assertEqual(sorted(outcomes), ['REJECTED', 'SYNTHETICALLY_ACTIVATED'])
        self.assertEqual(self.model.state()['epoch'], 2)

    def test_new_challenge_after_registration_blocks_activation(self):
        cert = self.register()
        self.model.challenge(cert, 'new1', 'OPEN', 'affected-nonmember', 'New evidence', ['fixture'], 21)
        with self.assertRaises(AmendmentError): self.model.activate(cert, 30)
        with self.assertRaises(AmendmentError):
            self.model.challenge(cert, 'new1', 'RESOLVED', 'registrar', 'self-review', ['fixture'], 30)
        self.model.challenge(cert, 'new1', 'RESOLVED', 'appeal', 'Independent disposition', ['fixture'], 30)
        self.model.activate(cert, 30)

    def test_new_stay_and_revocation_cannot_be_ignored(self):
        cert = self.register()
        self.model.challenge(cert, 'stay1', 'STAY', 'owner', 'Safety hold', ['fixture'], 21)
        with self.assertRaises(AmendmentError): self.model.activate(cert, 30)
        self.model.challenge(cert, 'stay1', 'RESOLVED', 'appeal', 'Review', ['fixture'], 30)
        self.model.invalidate(cert, 'Approval withdrawn', 30)
        with self.assertRaises(AmendmentError): self.model.activate(cert, 30)

    def test_no_preemptive_resolution(self):
        cert = self.register()
        with self.assertRaises(AmendmentError):
            self.model.challenge(cert, 'future', 'RESOLVED', 'appeal', 'Preapprove', ['fixture'], 21)

    def test_reregistration_cannot_evade_pending_challenge(self):
        cert = self.register()
        self.model.challenge(cert, 'open1', 'OPEN', 'affected', 'Pending challenge', ['fixture'], 21)
        for rename in (False, True):
            if rename:
                self.proposal['proposal_id'] = 'renamed-to-escape'
                self.proposal['new_policy']['content'] += ' changed candidate'
                self.bind()
            with self.assertRaises(AmendmentError): self.register(22)
        self.assertEqual(self.model.state()['epoch'], 1)

    def test_pending_challenge_blocks_all_preexisting_certificates(self):
        cert = self.register()
        self.proposal['proposal_id'] = 'other-candidate'
        self.proposal['new_policy']['content'] += ' other'
        self.bind()
        alternate = self.register()
        self.model.challenge(cert, 'open1', 'OPEN', 'affected', 'Pending', ['fixture'], 21)
        with self.assertRaises(AmendmentError): self.model.activate(alternate, 30)
        self.model.challenge(cert, 'open1', 'RESOLVED', 'appeal', 'Review completed', ['fixture'], 30)
        self.model.activate(alternate, 30)

    def test_reregistration_cannot_evade_revocation(self):
        cert = self.register()
        self.model.invalidate(cert, 'Approval revoked', 21)
        self.proposal['proposal_id'] = 'renamed'
        self.bind()
        with self.assertRaises(AmendmentError): self.register(22)

    def test_invalid_attempt_does_not_advance_clock(self):
        before = self.model.state()
        with self.assertRaises(AmendmentError): self.model.activate({}, 10 ** 20)
        self.assertEqual(self.model.state(), before)
        self.assertEqual(self.model.events(), [])
        cert = self.register()
        with self.assertRaises(AmendmentError): self.model.activate(cert, 10 ** 20)
        self.model.activate(cert, 30)

    def test_new_registration_does_not_reset_challenge_conflict(self):
        # Original registrar is also configured as an appeal actor; it must not
        # review its original challenged case through a different certificate.
        self.policy['rules']['registrars'].append('replacement')
        self.policy['rules']['appeal_authorities'].append('registrar')
        self.model = AmendmentReplay(self.policy)
        self.proposal['old_policy_digest'] = digest('Policy', self.policy)
        self.bind()
        cert = self.register()
        alternate = self.model.register(self.proposal, self.approval, self.procedure, 'replacement', 20)
        self.model.challenge(cert, 'open1', 'OPEN', 'affected', 'Pending', ['fixture'], 21)
        with self.assertRaises(AmendmentError):
            self.model.challenge(alternate, 'open1', 'RESOLVED', 'registrar', 'Self clearance', ['fixture'], 22)

    def test_supplied_procedure_review_preserves_same_proposal_conflict_history(self):
        self.policy['rules']['registrars'].append('substitute')
        self.policy['rules']['appeal_authorities'].append('registrar')
        self.model = AmendmentReplay(self.policy)
        self.proposal['old_policy_digest'] = digest('Policy', self.policy)
        self.bind()
        self.register()
        self.procedure['challenges'] = [{'id': 'same-proposal-case', 'disposition': 'RESOLVED',
                                        'reviewer': 'registrar', 'reason': 'Supplied claim of self-review',
                                        'evidence_ref': 'supplied-review'}]
        before = self.model.events()
        with self.assertRaisesRegex(AmendmentError, 'historically conflicted challenge reviewer'):
            self.model.register(self.proposal, self.approval, self.procedure, 'substitute', 21)
        self.assertEqual(self.model.events(), before)
        self.assertEqual(self.model.state()['epoch'], 1)
        # A genuinely separate declared old-rule reviewer remains usable.
        self.procedure['challenges'][0]['reviewer'] = 'appeal'
        cert = self.model.register(self.proposal, self.approval, self.procedure, 'substitute', 21)
        self.assertEqual(self.model.activate(cert, 30)['new_epoch'], 2)

    def test_regressing_clock_rejected(self):
        cert = self.register()
        with self.assertRaises(AmendmentError): self.model.activate(cert, 19)

    def test_false_epoch_not_current(self):
        self.assertFalse(self.model.is_current(self.model.state()['policy_digest'], True))

    def test_schema_scope_cannot_promote_authority(self):
        cert = self.register()
        for record in (cert, self.model.activate(cert, 30)):
            record['authority'] = 'EXECUTE'
            with self.assertRaises(AmendmentError):
                validate_record('Registration' if 'expected_epoch' in record else 'Activation', record)


if __name__ == '__main__':
    unittest.main()
