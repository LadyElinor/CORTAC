"""Adversarial structural tests; these do not adjudicate any real allegation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from wac_offline.opr_records_v1 import inspect_record, RecordError, _intervals
from wac_offline.opr_fixtures_v1 import fixture, control, EXPECTED, integration_report


class OPRRecordTests(unittest.TestCase):
    def setUp(self):
        self.record, self.context = fixture()

    def inspect(self):
        return inspect_record(self.record, self.context)

    def rejects(self):
        with self.assertRaises(RecordError): self.inspect()

    def test_complete_means_structure_only(self):
        r = self.inspect()
        self.assertEqual(r['status'], 'STRUCTURALLY_COMPLETE')
        self.assertEqual(r['authority'], 'NONE')
        self.assertFalse(r['execution_enabled'])
        self.assertEqual(r['semantic_assessment'], 'NOT_PERFORMED')
        self.assertEqual(r['operational_conformance'], 'NOT_ESTABLISHED')
        self.assertEqual(r['context_status'], 'SUPPLIED_UNVERIFIED')
        self.assertEqual(r['evidence_status'], 'REFERENCES_ONLY')

    def test_all_fixed_controls(self):
        r = integration_report()
        self.assertEqual(r['controls'], 18)
        self.assertFalse(r['opr_acceptance_established'])
        self.assertEqual({x['control']: x['observed'] for x in r['rows']}, EXPECTED)

    def test_required_fields(self):
        original = deepcopy(self.record)
        for key in original:
            with self.subTest(key=key):
                self.record = deepcopy(original); del self.record[key]; self.rejects()

    def test_extra_fields_at_every_root(self):
        for key in ['authority', 'execution_enabled', 'reputation_score', 'ideology_label', 'approved']:
            with self.subTest(key=key):
                self.record, self.context = fixture(); self.record[key] = True; self.rejects()

    def test_context_not_extensible_silently(self):
        self.context['ratified'] = True; self.rejects()

    def test_boolean_is_not_integer(self):
        self.context['epoch'] = True; self.record['epoch'] = True; self.rejects()

    def test_negative_ticks(self):
        self.context['now'] = -1; self.rejects()

    def test_float_ticks(self):
        self.context['now'] = 12.0; self.rejects()

    def test_null_and_nonobjects(self):
        for value in (None, [], True, 1):
            with self.subTest(value=value):
                with self.assertRaises(RecordError): inspect_record(value, self.context)

    def test_blank_justification_is_rejected(self):
        self.record['justification']['risk'] = ' \n'; self.rejects()

    def test_nonblank_justification_is_not_semantically_evaluated(self):
        self.record['justification']['risk'] = 'Irrelevant nonsense deliberately accepted as text only.'
        self.assertEqual(self.inspect()['semantic_assessment'], 'NOT_PERFORMED')

    def test_supplied_standard_is_not_truth(self):
        self.assertEqual(self.inspect()['evidence_status'], 'REFERENCES_ONLY')

    def test_epoch_and_version_binding(self):
        for key in ['epoch', 'version']:
            with self.subTest(key=key):
                self.record, self.context = fixture(); self.record[key] += 1; self.rejects()

    def test_policy_digest_binding(self):
        self.record['policy_digest'] = 'b' * 64; self.rejects()

    def test_bad_digest(self):
        self.context['policy_digest'] = self.record['policy_digest'] = 'not-a-hash'; self.rejects()

    def test_target_and_group_binding(self):
        for key in ['target', 'burden_group']:
            with self.subTest(key=key):
                self.record, self.context = fixture(); self.record[key] = 'different'; self.rejects()

    def test_exact_operation_set(self):
        self.record['operations'].append('ban'); self.rejects()

    def test_duplicate_operations(self):
        self.record['operations'].append('contact'); self.rejects()

    def test_missing_evidence(self):
        self.context['evidence'] = self.context['evidence'][1:]; self.rejects()

    def test_changed_evidence_digest(self):
        self.record['evidence_refs'][0]['digest'] = 'b' * 64; self.rejects()

    def test_duplicate_evidence_ids(self):
        self.context['evidence'].append(dict(id='observation', digest='b' * 64, kind='CLAIM')); self.rejects()

    def test_contrary_cannot_drop_reference(self):
        self.record['evidence_refs'] = [x for x in self.record['evidence_refs'] if x['id'] != 'contrary']; self.rejects()

    def test_contrary_handling_must_cover_pinned_inventory(self):
        self.record['contrary'][0]['evidence_id'] = 'observation'; self.rejects()

    def test_duplicate_contrary_dispositions(self):
        other = deepcopy(self.record['contrary'][0]); other['reason'] = 'Another.'
        self.record['contrary'].append(other); self.rejects()

    def test_limits_cannot_be_omitted(self):
        self.context['protected_limits'].append('privacy'); self.rejects()

    def test_known_failed_limit_incomplete(self):
        self.record['limits'][0]['status'] = 'FAILED'
        self.assertIn('PROTECTED_LIMIT_UNSATISFIED', self.inspect()['blockers'])

    def test_unknown_limit_incomplete(self):
        self.record['limits'][0]['status'] = 'UNRESOLVED'
        self.assertIn('PROTECTED_LIMIT_UNSATISFIED', self.inspect()['blockers'])

    def test_limit_reference_must_be_linked(self):
        self.record['limits'][0]['evidence_ids'] = ['missing']; self.rejects()

    def test_unknown_review_controller_never_becomes_verified(self):
        self.context['principals'][3]['controller'] = None
        self.assertIn('INDEPENDENCE_UNKNOWN', self.inspect()['blockers'])

    def test_common_control_between_verifier_and_reviewer(self):
        self.context['principals'][4]['controller'] = self.context['principals'][3]['controller']; self.rejects()

    def test_target_must_be_in_declared_parties(self):
        self.context['parties'].remove('target'); self.rejects()

    def test_verifier_is_party(self):
        self.record['independence']['verifier'] = 'target'; self.rejects()

    def test_verifier_cannot_verify_self(self):
        self.record['independence']['verifier'] = 'reviewer'; self.rejects()

    def test_control_evidence_required(self):
        self.record['independence']['evidence_ids'] = ['observation']; self.rejects()

    def test_conflict_route_required(self):
        self.record['independence']['conflict_route'] = ''; self.rejects()

    def test_dependency_reassessment_due(self):
        self.record['independence']['reassess_at'] = self.context['now']
        self.assertIn('INDEPENDENCE_REASSESSMENT_DUE', self.inspect()['blockers'])

    def test_unknown_principal(self):
        self.record['independence']['reviewer'] = 'unknown'; self.rejects()

    def test_renaming_does_not_reset_burden(self):
        before = self.inspect()
        self.record['case_label'] = self.record['interval']['case_label'] = 'nonpunitive'
        after = self.inspect()
        self.assertEqual(before['cumulative_duration'], after['cumulative_duration'])
        self.assertEqual(before['status'], after['status'])

    def test_repeated_interval_id_rejected(self):
        self.record['interval']['id'] = 'earlier'; self.rejects()

    def test_zero_or_negative_duration(self):
        self.record['interval']['end'] = self.record['interval']['start']; self.rejects()

    def test_zero_burden_units(self):
        self.record['interval']['burden_units'] = 0; self.rejects()

    def test_parallel_burdens_add_while_duration_unions(self):
        self.record, self.context = control('parallel_burden_cap')
        r = self.inspect()
        self.assertEqual((r['cumulative_duration'], r['cumulative_load']), (10, 50))
        self.assertIn('CUMULATIVE_LOAD_EXCEEDED', r['blockers'])

    def test_cumulative_duration_cap(self):
        self.context['duration_limit'] = 19
        self.assertIn('CUMULATIVE_DURATION_EXCEEDED', self.inspect()['blockers'])

    def test_cumulative_heightened_standard(self):
        self.record['justification']['standard'] = 'ARTICULABLE_RISK'
        self.assertIn('HEIGHTENED_FACTUAL_STANDARD_MISSING', self.inspect()['blockers'])

    def test_serious_consequence_requires_supplied_higher_standard(self):
        self.context['serious_duration'] = 20; self.context['serious_load'] = 40
        self.context['history'] = []; self.record['cumulative'] = dict(duration=10, load=10)
        for consequence in ['LONG_EXCLUSION', 'ROLE_LOSS', 'PUBLIC_SERIOUS_FINDING', 'IRREVERSIBLE']:
            with self.subTest(consequence=consequence):
                self.record['justification'].update(consequence=consequence, standard='ARTICULABLE_RISK')
                self.assertIn('HEIGHTENED_FACTUAL_STANDARD_MISSING', self.inspect()['blockers'])

    def test_bad_threshold_configuration(self):
        self.context['serious_load'] = 41; self.rejects()

    def test_grant_wrong_purpose(self):
        self.record['authority_ref'] = 'review'; self.rejects()

    def test_grant_stale_epoch(self):
        self.context['grants'][0]['epoch'] -= 1; self.rejects()

    def test_grant_wrong_scope(self):
        self.context['grants'][0]['operations'] = ['unrelated']; self.rejects()

    def test_restriction_cannot_outlive_supplied_grant(self):
        self.context['grants'][0]['end'] = 19; self.rejects()

    def test_expiry_is_exclusive_at_snapshot(self):
        self.context['now'] = 20
        self.assertIn('RESTRICTION_NOT_CURRENT', self.inspect()['blockers'])

    def test_expired_review_grant(self):
        self.context['grants'][1]['end'] = 12
        self.assertIn('REVIEW_AUTHORITY_NOT_CURRENT', self.inspect()['blockers'])

    def test_revoked_grant(self):
        self.context['grants'][0]['state'] = 'REVOKED'
        self.assertIn('RESTRICTION_AUTHORITY_REVOKED', self.inspect()['blockers'])

    def test_review_empty_reserve_is_not_completion(self):
        self.record['review']['reserved_units'] = 0
        self.assertIn('REVIEW_RESERVE_EMPTY', self.inspect()['blockers'])

    def test_review_deadline_beyond_expiry(self):
        self.record['review']['deadline'] = 21
        self.assertIn('REVIEW_DEADLINE_INVALID', self.inspect()['blockers'])

    def test_delayed_notice_requires_supplied_mandate(self):
        self.record['notice'].update(status='DELAYED', deadline=15); self.rejects()

    def test_delayed_notice_bounded(self):
        self.record['notice'].update(status='DELAYED', deadline=15, authority_ref='notice')
        self.assertEqual(self.inspect()['status'], 'STRUCTURALLY_COMPLETE')

    def test_unbounded_delay(self):
        self.record['notice'].update(status='DELAYED', deadline=19, authority_ref='notice')
        self.assertIn('NOTICE_DELAY_NOT_BOUNDED', self.inspect()['blockers'])

    def test_unknown_notice_delivery_remains_incomplete(self):
        self.record['notice']['status'] = 'UNDELIVERED'
        self.assertIn('NOTICE_UNDELIVERED', self.inspect()['blockers'])

    def test_future_notice_cannot_claim_delivered(self):
        self.record['notice']['deadline'] = 13; self.rejects()

    def test_missing_substitute_route(self):
        self.record['review']['substitute'] = ''; self.rejects()

    def test_open_complaint_never_closed_by_inspection(self):
        self.inspect(); self.assertEqual(self.record['complaints'][0]['status'], 'OPEN')

    def test_correction_incomplete_remains_visible(self):
        self.record['correction']['status'] = 'INCOMPLETE'
        self.assertIn('CORRECTION_REPORTED_INCOMPLETE', self.inspect()['blockers'])

    def test_reported_repair_is_not_proven(self):
        self.record['correction']['status'] = 'REPORTED_COMPLETE'
        self.assertEqual(self.inspect()['operational_conformance'], 'NOT_ESTABLISHED')

    def test_no_input_mutation_or_output_alias(self):
        before = deepcopy((self.record, self.context)); report = self.inspect()
        report['blockers'].append('changed')
        self.assertEqual(before, (self.record, self.context))
        self.assertNotIn('changed', self.inspect()['blockers'])

    def test_context_snapshot_digest_changes(self):
        before = self.inspect(); self.context['now'] = 20; after = self.inspect()
        self.assertEqual(before['record_digest'], after['record_digest'])
        self.assertNotEqual(before['context_digest'], after['context_digest'])

    def test_deterministic_report(self):
        self.assertEqual(self.inspect(), self.inspect())

    def test_interval_arithmetic_against_tick_oracle(self):
        # Finite exhaustive windows; independent per-tick oracle, no model claims.
        for start in range(4):
            for end in range(start + 1, 6):
                rows = [dict(start=0, end=3, burden_units=2), dict(start=start, end=end, burden_units=3)]
                duration, load = _intervals(rows)
                self.assertEqual(duration, len(set(range(3)) | set(range(start, end))))
                self.assertEqual(load, sum(2 * (0 <= t < 3) + 3 * (start <= t < end) for t in range(6)))


if __name__ == '__main__': unittest.main()
