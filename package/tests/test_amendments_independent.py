"""Independent synthetic adversarial checks; fixture values are not deployment thresholds."""
import unittest
import json
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from wac_offline.amendments import AmendmentReplay, digest, AmendmentError

def fixture():
    actors = ['proposer', 'voter', 'owner', 'registrar', 'reviewer', 'replacement']
    old = {'schema': 'cortac.amendment.policy.v2', 'society_id': 's', 'attempt_id': 'a', 'content': 'old', 'rules': {'actors': [{'id': a, 'domain': a} for a in actors], 'decisionmakers': ['voter'], 'quorum': 1, 'registrars': ['registrar'], 'external_principals': ['owner'], 'appeal_authorities': ['reviewer'], 'replacement_authorities': ['replacement'], 'notice_period': 2, 'challenge_period': 2, 'registrar_deadline': 100}}
    old['protected_limits'] = [{'id': 'independent-review', 'commitment': 'Preserve independent review of consequential amendments.'}]
    old['rules'].update(replacement_registrars=['substitute'], review_deadline=100, repair_deadline=100, repair_resource_limit=10, repair_resource_cost=2)
    old['rules']['actors'].append({'id': 'substitute', 'domain': 'substitute'})
    new = deepcopy(old)
    new['content'] = 'new'
    p = {'schema': 'cortac.amendment.proposal.v2', 'proposal_id': 'p', 'proposer': 'proposer', 'old_policy_digest': digest('Policy', old), 'new_policy_digest': digest('Policy', new), 'expected_epoch': 1, 'new_policy': new, 'submitted_at': 0, 'activate_at': 10, 'expires_at': 100}
    a = {'schema': 'cortac.amendment.approval.v2', 'proposal_digest': digest('Proposal', p), 'decision': 'APPROVE', 'decisionmakers': ['voter'], 'external_principals': ['owner'], 'issued_at': 1, 'reasons': 'supplied', 'evidence_refs': ['fixture']}
    pr = {'schema': 'cortac.amendment.procedure.v2', 'proposal_digest': digest('Proposal', p), 'notice_at': 0, 'review_closed_at': 4, 'conflicts_cleared': True, 'challenge_inventory_complete': True, 'mandatory_checks_passed': True, 'challenges': [], 'evidence_refs': ['fixture']}
    a['decision_record'] = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/decision_record.json').read_text())
    return (old, p, a, pr)

class Adversarial(unittest.TestCase):

    def setUp(self):
        self.old, self.p, self.a, self.pr = fixture()
        self.r = AmendmentReplay(self.old)

    def register(self):
        return self.r.register(self.p, self.a, self.pr, 'registrar', 5)

    def rebind(self):
        self.a['proposal_digest'] = self.pr['proposal_digest'] = digest('Proposal', self.p)

    def test_time_poison(self):
        c = self.register()
        with self.assertRaises(AmendmentError):
            self.r.activate({}, 10 ** 20)
        self.r.activate(c, 10)

    def test_old_quorum(self):
        self.old['rules']['actors'].append({'id': 'voter2', 'domain': 'voter2'})
        self.old['rules']['decisionmakers'].append('voter2')
        self.old['rules']['quorum'] = 2
        self.r = AmendmentReplay(self.old)
        self.p['old_policy_digest'] = digest('Policy', self.old)
        self.rebind()
        with self.assertRaises(AmendmentError):
            self.register()

    def test_principal_cannot_remove_itself(self):
        self.a['external_principals'] = []
        with self.assertRaises(AmendmentError):
            self.register()

    def test_no_silence_approval(self):
        self.a['decision'] = 'HOLD'
        with self.assertRaises(AmendmentError):
            self.register()

    def test_pending_input_challenge(self):
        self.pr['challenges'] = [{'id': 'c', 'disposition': 'OPEN', 'reviewer': 'reviewer', 'reason': 'pending', 'evidence_ref': 'e'}]
        with self.assertRaises(AmendmentError):
            self.register()

    def test_renamed_proposal_challenge(self):
        c = self.register()
        self.r.challenge(c, 'c', 'OPEN', 'affected', 'pending', ['e'], 6)
        self.p['proposal_id'] = 'renamed'
        self.rebind()
        with self.assertRaises(AmendmentError):
            c2 = self.r.register(self.p, self.a, self.pr, 'registrar', 7)
            self.r.activate(c2, 10)

    def test_different_candidate_challenge(self):
        c = self.register()
        self.r.challenge(c, 'c', 'OPEN', 'affected', 'pending', ['e'], 6)
        self.p['new_policy']['content'] = 'third'
        self.p['new_policy_digest'] = digest('Policy', self.p['new_policy'])
        self.rebind()
        with self.assertRaises(AmendmentError):
            c2 = self.r.register(self.p, self.a, self.pr, 'registrar', 7)
            self.r.activate(c2, 10)

    def test_independent_resolution(self):
        c = self.register()
        self.r.challenge(c, 'c', 'OPEN', 'affected', 'pending', ['e'], 6)
        with self.assertRaises(AmendmentError):
            self.r.challenge(c, 'c', 'RESOLVED', 'registrar', 'claimed', ['e'], 7)
        self.r.challenge(c, 'c', 'RESOLVED', 'reviewer', 'resolved', ['e'], 8)
        self.r.activate(c, 10)

    def test_alias_isolation(self):
        c = self.register()
        expected = self.p['new_policy_digest']
        self.p['new_policy']['content'] = 'tampered'
        self.a['decision'] = 'DENY'
        self.old['content'] = 'mutated'
        self.assertEqual(self.r.activate(c, 10)['new_policy_digest'], expected)

    def test_certificate_tamper(self):
        c = self.register()
        c['activate_at'] = 5
        with self.assertRaises(AmendmentError):
            self.r.activate(c, 10)

    def test_replay(self):
        c = self.register()
        self.r.activate(c, 10)
        with self.assertRaises(AmendmentError):
            self.r.activate(c, 11)

    def test_concurrent_activation(self):
        c = self.register()

        def run(_):
            try:
                return self.r.activate(c, 10)['new_epoch']
            except AmendmentError:
                return 'rejected'
        with ThreadPoolExecutor(8) as pool:
            out = list(pool.map(run, range(20)))
        self.assertEqual(out.count(2), 1)
        self.assertEqual(out.count('rejected'), 19)

    def test_early_activation(self):
        c = self.register()
        with self.assertRaises(AmendmentError):
            self.r.activate(c, 9)

    def test_bool_epoch(self):
        self.p['expected_epoch'] = True
        with self.assertRaises(AmendmentError):
            self.rebind()

    def test_wrong_attempt(self):
        self.p['new_policy']['attempt_id'] = 'other'
        self.p['new_policy_digest'] = digest('Policy', self.p['new_policy'])
        self.rebind()
        with self.assertRaises(AmendmentError):
            self.register()
if __name__ == '__main__':
    unittest.main(verbosity=2)
