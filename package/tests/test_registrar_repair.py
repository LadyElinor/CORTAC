"""Synthetic case repair regression tests, never an institutional authorization."""
import copy
import unittest
from test_amendments import fixture
from wac_offline.amendments import AmendmentReplay, AmendmentError, digest, validate_record


def repair_case(source_kind='Invalidation'):
    policy, original, old_approval, old_procedure = fixture()
    if source_kind == 'Refusal':
        policy['rules']['registrar_deadline'] = 19
        original['old_policy_digest'] = digest('Policy', policy)
        old_approval['proposal_digest'] = old_procedure['proposal_digest'] = digest('Proposal', original)
    model = AmendmentReplay(policy)
    submission = model.submit(original, 'registrar', 0)
    certificate = None
    if source_kind == 'Invalidation':
        certificate = model.register(original, old_approval, old_procedure, 'registrar', 20)
        source = model.invalidate(certificate, 'Supplied approval revocation', 21, ['revocation-evidence'])
    elif source_kind == 'Refusal':
        try:
            model.register(original, old_approval, old_procedure, 'registrar', 20)
        except AmendmentError:
            pass
        source = model.events()[-1]['record']
    else:
        source = submission
    complaint = model.complain(submission, 'outsider-case', 'affected-nonmember',
                               'Independent review requested', ['complaint-evidence'], 21,
                               None if source_kind == 'Submission' else source)
    proposal = copy.deepcopy(original)
    proposal.update(proposal_id='fresh-repair', submitted_at=22, activate_at=45)
    proposal['new_policy']['content'] += ' Exact repaired proposal.'
    proposal['new_policy_digest'] = digest('Policy', proposal['new_policy'])
    approval, procedure = copy.deepcopy((old_approval, old_procedure))
    pd = digest('Proposal', proposal)
    approval.update(proposal_digest=pd, issued_at=42, reasons='Fresh affirmative repair decision', evidence_refs=['fresh-decision'])
    procedure.update(proposal_digest=pd, notice_at=22, review_closed_at=42, evidence_refs=['fresh-notice-and-review'])
    grant = {'schema': 'cortac.amendment.resource-remedy-grant.v2', 'grant_id': 'bounded-grant',
             'complaint_digest': digest('Complaint', complaint), 'source_digest': complaint['source_digest'],
             'repair_proposal_digest': pd, 'old_policy_digest': proposal['old_policy_digest'], 'expected_epoch': 1,
             'remedy': 'REPAIR_INVALIDATION' if source_kind == 'Invalidation' else 'REPLACE_REGISTRATION',
             'remedy_authorized': True, 'external_principals': ['owner'], 'resource_units': 2,
             'resource_purpose': 'SINGLE_CASE_REGISTRAR_REVIEW', 'issued_at': 42, 'expires_at': 80,
             'reason': 'Supplied old-principal authorization for this exact remedy and finite support.',
             'evidence_refs': ['supplied-old-principal-grant'], 'authority': 'NONE', 'execution_enabled': False}
    return model, submission, certificate, source, complaint, proposal, approval, procedure, grant


class RegistrarRepairTests(unittest.TestCase):
    def setUp(self):
        (self.model, self.submission, self.old_certificate, self.source, self.complaint,
         self.proposal, self.approval, self.procedure, self.grant) = repair_case()

    def review(self, **overrides):
        values = dict(complaint=self.complaint, proposal=self.proposal, approval=self.approval,
                      procedure=self.procedure, grant=self.grant, reviewer='appeal',
                      replacement_authorizer='replacement', replacement_registrar='substitute',
                      reason='Independent supplied reasoned decision', evidence_refs=['independent-review-evidence'], now=42)
        values.update(overrides)
        return self.model.review_repair(**values)

    def assertUnchangedFailure(self, fn):
        state, events = self.model.state(), self.model.events()
        with self.assertRaises(AmendmentError): fn()
        self.assertEqual(self.model.state(), state)
        self.assertEqual(self.model.events(), events)

    def test_invalidation_repair_uses_fresh_certificate_and_advances_epoch(self):
        review = self.review()
        cert = self.model.register_replacement(review, 42)
        self.assertNotEqual(cert['approval_digest'], self.old_certificate['approval_digest'])
        self.assertUnchangedFailure(lambda: self.model.activate(self.old_certificate, 45))
        receipt = self.model.activate(cert, 45)
        self.assertEqual(receipt['new_epoch'], 2)
        self.assertEqual(receipt['authority'], 'NONE')
        self.assertFalse(receipt['execution_enabled'])
        self.assertUnchangedFailure(lambda: self.model.activate(self.old_certificate, 45))

    def test_late_register_records_reasoned_refusal(self):
        model, submission, _, source, *_ = repair_case('Refusal')
        self.assertEqual(source['schema'], 'cortac.amendment.refusal.v2')
        self.assertEqual(source['deadline'], 19)
        self.assertEqual(source['replacement_authorities'], ['replacement'])
        self.assertEqual(model.state()['epoch'], 1)

    def test_noncooperating_registrar_does_not_control_replacement(self):
        (self.model, self.submission, _, self.source, self.complaint,
         self.proposal, self.approval, self.procedure, self.grant) = repair_case('Refusal')
        review = self.review()
        self.assertEqual(review['replacement_registrar'], 'substitute')
        cert = self.model.register_replacement(review, 42)
        self.assertEqual(self.model.activate(cert, 45)['new_epoch'], 2)

    def test_pre_registration_complaint_supported(self):
        model, submission, _, source, complaint, *_ = repair_case('Submission')
        self.assertEqual(source, submission)
        self.assertEqual(complaint['source_kind'], 'Submission')
        self.assertFalse(any(e['kind'] == 'registration' for e in model.events()))

    def test_tick_records_deadline_and_no_silent_approval(self):
        policy, p, _, _ = fixture()
        policy['rules']['registrar_deadline'] = 19
        p['old_policy_digest'] = digest('Policy', policy)
        model = AmendmentReplay(policy)
        model.submit(p, 'registrar', 0)
        records = model.tick(20)
        self.assertEqual(records[0]['kind'], 'refusal')
        self.assertEqual(model.tick(21), [])
        self.assertEqual(model.state()['epoch'], 1)

    def test_expired_stay_is_escalation_required(self):
        # Explicit ticks do not remove or resolve holds, even far after deadlines.
        self.model.challenge(self.old_certificate, 'stay', 'STAY', 'outsider', 'Safety concern', ['e'], 22)
        records = self.model.tick(123)
        self.assertTrue(any(e['kind'] == 'challenge' and e['record']['disposition'] == 'ESCALATION_REQUIRED' for e in records))
        self.assertUnchangedFailure(lambda: self.model.activate(self.old_certificate, 123))
        self.assertEqual(self.model.state()['epoch'], 1)

    def test_expired_complaint_remains_hold(self):
        records = self.model.tick(122)
        self.assertTrue(any(e['kind'] == 'complaint' and e['record']['disposition'] == 'ESCALATION_REQUIRED' for e in records))
        self.assertUnchangedFailure(lambda: self.review(now=122))

    def test_funding_without_remedy_authorization_rejected(self):
        self.grant['remedy_authorized'] = False
        self.assertUnchangedFailure(self.review)

    def test_old_external_principals_must_authorize_exact_remedy(self):
        self.grant['external_principals'] = ['replacement']
        self.assertUnchangedFailure(self.review)

    def test_wrong_source_or_complaint_grant_cannot_be_used(self):
        for field in ('source_digest', 'complaint_digest', 'repair_proposal_digest', 'old_policy_digest'):
            old = self.grant[field]
            self.grant[field] = '0' * 64
            self.assertUnchangedFailure(self.review)
            self.grant[field] = old

    def test_insufficient_excess_or_expired_grant_rejected(self):
        for field, bad in [('resource_units', 1), ('resource_units', 11), ('expires_at', 41), ('expires_at', 200)]:
            old = self.grant[field]
            self.grant[field] = bad
            self.assertUnchangedFailure(self.review)
            self.grant[field] = old

    def test_missing_nonempty_reason_evidence_rejected(self):
        self.assertUnchangedFailure(lambda: self.review(reason=''))
        self.assertUnchangedFailure(lambda: self.review(reason='   '))
        self.assertUnchangedFailure(lambda: self.review(evidence_refs=['\t ']))
        self.assertUnchangedFailure(lambda: self.review(evidence_refs=[]))

    def test_approval_procedure_must_postdate_revocation(self):
        for record, field in [(self.approval, 'issued_at'), (self.procedure, 'notice_at'), (self.procedure, 'review_closed_at')]:
            old = record[field]
            record[field] = 21
            self.assertUnchangedFailure(self.review)
            record[field] = old

    def test_review_and_appointment_cannot_act_as_substitute(self):
        for kwargs in [dict(reviewer='registrar'), dict(replacement_authorizer='registrar'), dict(replacement_registrar='replacement')]:
            self.assertUnchangedFailure(lambda: self.review(**kwargs))

    def test_unrelated_challenge_preserved_until_independent_resolution(self):
        self.model.challenge(self.old_certificate, 'unrelated', 'STAY', 'outsider', 'Different concern', ['other'], 22)
        self.assertUnchangedFailure(self.review)
        self.model.challenge(self.old_certificate, 'unrelated', 'RESOLVED', 'appeal', 'Independent disposition', ['review'], 42)
        cert = self.model.register_replacement(self.review(), 42)
        self.model.activate(cert, 45)

    def test_new_invalidation_after_review_blocks_activation(self):
        cert = self.model.register_replacement(self.review(), 42)
        second = self.model.invalidate(self.old_certificate, 'New revocation', 43, ['new-evidence'])
        self.assertNotEqual(digest('Invalidation', second), digest('Invalidation', self.source))
        self.assertUnchangedFailure(lambda: self.model.activate(cert, 45))

    def test_same_time_same_reason_invalidation_is_new_revision(self):
        # Repeated source content must not be covered by an earlier exemption.
        fresh = self.model.invalidate(self.old_certificate, self.source['reason'], 21, self.source['evidence_refs'])
        self.assertNotEqual(digest('Invalidation', fresh), digest('Invalidation', self.source))
        self.assertUnchangedFailure(self.review)

    def test_reopened_complaint_blocks_bound_review(self):
        review = self.review()
        self.model.complain(self.submission, self.complaint['complaint_id'], 'outsider', 'Reopened with fresh evidence', ['new'], 43, self.source)
        self.assertUnchangedFailure(lambda: self.model.register_replacement(review, 43))

    def test_unrelated_complaint_after_registration_blocks_activation(self):
        cert = self.model.register_replacement(self.review(), 42)
        self.model.complain(self.submission, 'other', 'outsider', 'Unrelated concern', ['different'], 43)
        self.assertUnchangedFailure(lambda: self.model.activate(cert, 45))

    def test_single_case_grant_cannot_be_double_spent(self):
        review = self.review()
        self.model.register_replacement(review, 42)
        self.assertUnchangedFailure(lambda: self.model.register_replacement(review, 42))

    def test_changed_grant_id_binding_rejected(self):
        self.review()
        self.grant['resource_units'] = 3
        self.assertUnchangedFailure(self.review)

    def test_expired_repair_never_activates(self):
        self.grant['expires_at'] = 45
        cert = self.model.register_replacement(self.review(), 42)
        self.assertUnchangedFailure(lambda: self.model.activate(cert, 46))

    def test_reason_evidence_tampering_does_not_match_local_review(self):
        review = self.review()
        for field, value in [('reason', 'Altered'), ('evidence_refs', ['other'])]:
            altered = copy.deepcopy(review)
            altered[field] = value
            self.assertUnchangedFailure(lambda: self.model.register_replacement(altered, 42))

    def test_tampered_source_not_accepted_as_complaint(self):
        bad = copy.deepcopy(self.source)
        bad['reason'] = 'Other reason'
        self.assertUnchangedFailure(lambda: self.model.complain(self.submission, 'case2', 'outsider', 'Reason', ['e'], 22, bad))

    def test_protected_limits_preserved_in_repair(self):
        self.proposal['new_policy']['protected_limits'][0]['commitment'] = 'No review'
        self.proposal['new_policy_digest'] = digest('Policy', self.proposal['new_policy'])
        pd = digest('Proposal', self.proposal)
        self.approval['proposal_digest'] = self.procedure['proposal_digest'] = self.grant['repair_proposal_digest'] = pd
        self.assertUnchangedFailure(self.review)

    def test_missing_or_failed_substantive_assessment_rejected(self):
        for status in ('FAIL', 'UNKNOWN'):
            self.approval['decision_record']['protected_limit_assessments'][0]['status'] = status
            self.assertUnchangedFailure(self.review)

    def test_intervening_resolved_hold_does_not_restore_old_review(self):
        review = self.review()
        self.model.challenge(self.old_certificate, 'new', 'OPEN', 'outsider', 'New concern', ['e'], 43)
        self.model.challenge(self.old_certificate, 'new', 'RESOLVED', 'appeal', 'Reviewed', ['e2'], 43)
        self.assertUnchangedFailure(lambda: self.model.register_replacement(review, 43))
        fresh = self.review(now=43)
        cert = self.model.register_replacement(fresh, 43)
        self.model.activate(cert, 45)

    def test_escalated_complaint_requires_new_revision_grant_and_review(self):
        self.model.tick(122)
        self.complaint = self.model.complain(self.submission, 'outsider-case', 'affected-nonmember',
                                              'Escalated request with new evidence', ['new-evidence'], 122, self.source)
        self.proposal.update(submitted_at=123, activate_at=146, expires_at=200)
        pd = digest('Proposal', self.proposal)
        self.approval.update(proposal_digest=pd, issued_at=143)
        self.procedure.update(proposal_digest=pd, notice_at=123, review_closed_at=143)
        self.grant.update(grant_id='renewed-case-grant', complaint_digest=digest('Complaint', self.complaint),
                          repair_proposal_digest=pd, issued_at=143, expires_at=200)
        fresh = self.review(now=143)
        cert = self.model.register_replacement(fresh, 143)
        self.assertEqual(self.model.activate(cert, 146)['new_epoch'], 2)

    def test_unknown_approval_actor_is_reasoned_nonmutating_failure(self):
        self.approval['decisionmakers'] = ['unrecognized']
        self.assertUnchangedFailure(self.review)

    def test_strict_scope_and_old_v1_records_rejected(self):
        review = self.review()
        review['authority'] = 'ACTIVE'
        with self.assertRaises(AmendmentError): validate_record('RepairReview', review)
        self.proposal['schema'] = 'cortac.amendment.proposal.v1'
        with self.assertRaises(AmendmentError): digest('Proposal', self.proposal)

    def test_invalid_late_attempt_does_not_append_refusal_or_poison_clock(self):
        policy, p, a, pr = fixture()
        policy['rules']['registrar_deadline'] = 19
        p['old_policy_digest'] = digest('Policy', policy)
        a['proposal_digest'] = pr['proposal_digest'] = digest('Proposal', p)
        model = AmendmentReplay(policy)
        a['decision'] = 'DENY'
        with self.assertRaises(AmendmentError): model.register(p, a, pr, 'registrar', 20)
        self.assertEqual(model.events(), [])
        model.submit(p, 'registrar', 1)


if __name__ == '__main__':
    unittest.main()
