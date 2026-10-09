"""Synthetic structural controls, never evidence that either study arm works."""
from copy import deepcopy
import hashlib
import json
import unittest

from wac_offline.ops_study_v1 import (
    ARMS, CONTEXT_VERSION, ENDPOINTS, VERSION, StudyError, input_digest, inspect_study,
)


def fixture():
    """Return fresh synthetic plan/context examples for repository tests."""
    independence = dict(id='control-reference', digest='a' * 64)
    permission = dict(id='permission-reference', digest='b' * 64)
    source = dict(id='outcome-reference', digest='c' * 64)
    plan = dict(schema=VERSION, study_id='synthetic-shadow-study', version=1,
        condition_set_digest='d' * 64,
        arms=[dict(id=arm, condition_set_digest='d' * 64,
                   procedure=arm + ' supplied offline procedure label') for arm in ARMS],
        endpoints=[dict(id=e, definition=e + ' supplied definition',
                        criterion=e + ' supplied preregistered criterion') for e in ENDPOINTS],
        assessment=dict(assessor='assessor', verifier='verifier',
                        independence_evidence_refs=[deepcopy(independence)]),
        uncertainty_protocol='Report uncertainty per endpoint without upgrading unknowns.',
        missingness_protocol='Record missing endpoints with an explicit reason.',
        stopping_criteria='Stop at supplied safety threshold; preserve adverse outcomes.',
        protected_group_comparison_protocol='Use preregistered group comparisons and disclose small cells.',
        privacy_permission_protocol='Use only permissioned deidentified supplied snapshots.',
        privacy_permission_evidence_refs=[deepcopy(permission)],
        evidence_source_requirements=[dict(id='declared-source', requirement='Supplied references only.')])
    digest = input_digest(plan)
    context = dict(schema=CONTEXT_VERSION, expected_study_id=plan['study_id'],
        expected_plan_version=1, expected_plan_digest=digest, now=10,
        designated_assessor='assessor', designated_verifier='verifier',
        principals=[dict(id=p, controller=p + '-control')
                    for p in ('party', 'assessor', 'verifier')], parties=['party'],
        expected_independence_evidence_refs=[deepcopy(independence)],
        evidence=[dict(**ref, kind=kind, source_id='declared-source', available_at=at)
                  for ref, kind, at in ((independence, 'INDEPENDENCE', 0),
                    (permission, 'PRIVACY_PERMISSION', 0), (source, 'OBSERVATION', 2))],
        preregistration=dict(plan_digest=digest, plan_version=1, registered_at=1,
            assessor='assessor', verifier='verifier',
            independence_evidence_refs=[deepcopy(independence)]),
        observations=[dict(id=arm + '-snapshot', plan_digest=digest, plan_version=1,
            arm=arm, condition_set_digest=plan['condition_set_digest'], observed_at=2,
            recorded_at=3, assessor='assessor',
            outcomes=[dict(endpoint=e, state='REPORTED', value='Synthetic supplied value',
                uncertainty='Unknown; no statistical estimate.', missingness='None declared.',
                evidence_refs=[deepcopy(source)]) for e in ENDPOINTS]) for arm in ARMS])
    return plan, context


class OPSStudyTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.context = fixture()

    def inspect(self):
        return inspect_study(self.plan, self.context)

    def rejects(self):
        with self.assertRaises(StudyError):
            self.inspect()

    def repin(self):
        """Synthetic coordinated rewrite, intentionally NOT trusted registration."""
        digest = input_digest(self.plan)
        self.context['expected_plan_digest'] = digest
        if self.context['preregistration'] is not None:
            self.context['preregistration']['plan_digest'] = digest
        for item in self.context['observations']:
            item['plan_digest'] = digest

    def test_consistent_is_never_a_completed_or_valid_study(self):
        report = self.inspect()
        self.assertEqual(report['status'], 'PLAN_TRACE_CONSISTENT')
        self.assertEqual(report['phase'], 'OBSERVATIONS_SUPPLIED')
        self.assertEqual(report['observation_count'], 2)
        self.assertEqual(report['authority'], 'NONE')
        self.assertIs(report['execution_enabled'], False)
        for key in ('study_validity', 'study_completion', 'empirical_superiority', 'independence_over_study_span'):
            self.assertEqual(report[key], 'NOT_ESTABLISHED')
        self.assertEqual(report['input_status'], 'ALL_SUPPLIED_UNVERIFIED')
        self.assertEqual(report['caller_pins_status'], 'SUPPLIED_UNAUTHENTICATED')
        for key in ('independence_status', 'context_status', 'controller_closure',
                    'preregistration_status', 'privacy_permission_status'):
            self.assertEqual(report[key], 'SUPPLIED_UNVERIFIED')
        self.assertEqual(report['chronology_status'], 'SUPPLIED_LOGICAL_TICKS_UNVERIFIED')
        self.assertEqual(report['evidence_status'], 'REFERENCES_ONLY_UNVERIFIED')
        for key in ('semantic_assessment', 'statistical_analysis', 'stopping_assessment'):
            self.assertEqual(report[key], 'NOT_PERFORMED')

    def test_empty_plan_never_completes(self):
        self.plan = {}; self.rejects()

    def test_draft_and_prepared_without_observations_are_incomplete(self):
        self.context['observations'] = []
        for registration, phase in ((self.context['preregistration'], 'PREPARED_NO_OBSERVATIONS'),
                                    (None, 'DRAFT')):
            self.context['preregistration'] = registration
            report = self.inspect()
            self.assertEqual(report['phase'], phase)
            self.assertEqual(report['status'], 'PLAN_TRACE_INCOMPLETE')
            self.assertEqual(report['observation_count'], 0)
            self.assertIn('OBSERVATIONS_ABSENT', report['blockers'])
            self.assertEqual(report['study_completion'], 'NOT_ESTABLISHED')

    def test_observations_without_preregistration_rejected(self):
        self.context['preregistration'] = None; self.rejects()

    def test_missing_root_fields(self):
        for root in ('plan', 'context'):
            self.setUp()
            for key in list(getattr(self, root)):
                with self.subTest(root=root, key=key):
                    self.setUp(); del getattr(self, root)[key]; self.rejects()

    def test_unknown_fields_at_every_object(self):
        def paths(value, path=()):
            if type(value) is dict:
                yield path
                for key, item in value.items():
                    yield from paths(item, path + (key,))
            elif type(value) is list:
                for index, item in enumerate(value):
                    yield from paths(item, path + (index,))
        for root in ('plan', 'context'):
            self.setUp()
            for path in list(paths(getattr(self, root))):
                with self.subTest(root=root, path=path):
                    self.setUp(); target = getattr(self, root)
                    for part in path: target = target[part]
                    target['execution_enabled'] = True; self.rejects()

    def test_nonobject_roots_and_wrong_nested_shapes(self):
        for value in (None, [], True, 1, 'plan'):
            for root in ('plan', 'context'):
                self.setUp(); setattr(self, root, value); self.rejects()
        for key, value in (('arms', {}), ('endpoints', ()), ('assessment', []),
                           ('stopping_criteria', None), ('uncertainty_protocol', 3)):
            self.setUp(); self.plan[key] = value; self.rejects()

    def test_schema_version_and_namespace_closed(self):
        for root in ('plan', 'context'):
            for schema in ('cortac.ops.context.v1', 'cortac.ops.study.plan.v2', 'unknown'):
                self.setUp(); getattr(self, root)['schema'] = schema; self.rejects()

    def test_bool_float_negative_or_zero_version_rejected(self):
        for value in (True, 1.0, -1, 0):
            self.setUp(); self.plan['version'] = value; self.repin(); self.rejects()

    def test_time_types_strict(self):
        for value in (True, 10.0, -1, None, 2 ** 63):
            self.context['now'] = value; self.rejects()

    def test_digest_format_strict(self):
        for value in ('A' * 64, 'a' * 63, 'a' * 65, 'not-a-digest', 0):
            self.context['expected_plan_digest'] = value; self.rejects()

    def test_blank_required_protocols_rejected(self):
        for key in ('uncertainty_protocol', 'missingness_protocol', 'stopping_criteria',
                    'protected_group_comparison_protocol', 'privacy_permission_protocol'):
            self.setUp(); self.plan[key] = ' \n'; self.rejects()

    def test_pinned_identity_version_digest(self):
        for key, value in (('expected_study_id', 'substitution'), ('expected_plan_version', 2),
                           ('expected_plan_digest', 'f' * 64)):
            self.setUp(); self.context[key] = value; self.rejects()

    def test_arm_inventory_and_equal_conditions(self):
        for mode in ('remove', 'duplicate_id', 'condition'):
            self.setUp()
            if mode == 'remove': self.plan['arms'].pop()
            elif mode == 'duplicate_id': self.plan['arms'][1]['id'] = 'MINIMAL'
            else: self.plan['arms'][1]['condition_set_digest'] = 'e' * 64
            self.repin(); self.rejects()

    def test_endpoint_inventory_cannot_hide_harms(self):
        for endpoint in ENDPOINTS:
            self.setUp()
            self.plan['endpoints'] = [e for e in self.plan['endpoints'] if e['id'] != endpoint]
            self.repin(); self.rejects()
            self.setUp()
            self.context['observations'][0]['outcomes'] = [
                e for e in self.context['observations'][0]['outcomes'] if e['endpoint'] != endpoint]
            self.rejects()

    def test_duplicate_identifiers_cannot_replace_endpoints_or_sources(self):
        for path in (('plan', 'endpoints'), ('plan', 'arms'), ('context', 'evidence'),
                     ('context', 'principals'), ('context', 'observations')):
            self.setUp(); values = getattr(self, path[0])[path[1]]
            item = deepcopy(values[0])
            if 'digest' in item: item['digest'] = 'f' * 64
            elif 'definition' in item: item['definition'] = 'Changed duplicate.'
            elif 'procedure' in item: item['procedure'] = 'Changed duplicate.'
            elif 'controller' in item: item['controller'] = 'another-controller'
            else: item['recorded_at'] = 4
            values.append(item); self.repin(); self.rejects()

    def test_preregistration_strictly_before_observation(self):
        for value in (2, 3, 11):
            self.context['preregistration']['registered_at'] = value; self.rejects()

    def test_future_or_backwards_observation_rejected(self):
        for key, value in (('observed_at', 1), ('recorded_at', 1), ('recorded_at', 11)):
            self.setUp(); self.context['observations'][0][key] = value; self.rejects()

    def test_plan_change_cannot_reuse_preregistration(self):
        self.plan['endpoints'][0]['criterion'] = 'Post-hoc easier criterion.'
        digest = input_digest(self.plan)
        self.context['expected_plan_digest'] = digest
        for item in self.context['observations']: item['plan_digest'] = digest
        self.rejects()

    def test_plan_version_change_cannot_reuse_preregistration(self):
        self.plan['version'] = self.context['expected_plan_version'] = 2
        self.repin(); self.rejects()

    def test_observation_bindings_all_checked(self):
        for key, value in (('plan_digest', 'f' * 64), ('plan_version', 2),
                           ('condition_set_digest', 'f' * 64), ('assessor', 'replacement')):
            self.setUp(); self.context['observations'][0][key] = value; self.rejects()

    def test_preregistered_assessor_and_verifier_cannot_change(self):
        for key in ('assessor', 'verifier'):
            self.setUp(); self.context['preregistration'][key] = 'replacement'; self.rejects()
            self.setUp(); self.context['designated_' + key] = 'replacement'; self.rejects()

    def test_role_and_party_overlap_rejected(self):
        for key, value in (('assessor', 'verifier'), ('assessor', 'party'), ('verifier', 'party')):
            self.setUp(); self.plan['assessment'][key] = value
            self.context['designated_' + key] = value
            self.context['preregistration'][key] = value
            self.repin(); self.rejects()

    def test_common_control_and_unknown_participant_rejected(self):
        for actor, other in ((1, 0), (2, 0), (1, 2)):
            self.setUp()
            self.context['principals'][actor]['controller'] = self.context['principals'][other]['controller']
            self.rejects()
        self.setUp(); self.context['parties'].append('unknown-party'); self.rejects()

    def test_unknown_controller_is_incomplete_never_verified(self):
        for index in range(3):
            self.setUp(); self.context['principals'][index]['controller'] = None
            report = self.inspect()
            self.assertIn('INDEPENDENCE_CONTROLLER_UNKNOWN', report['blockers'])
            self.assertEqual(report['status'], 'PLAN_TRACE_INCOMPLETE')
            self.assertEqual(report['independence_status'], 'SUPPLIED_UNVERIFIED')

    def test_pinned_and_preregistered_control_evidence_cannot_change(self):
        for refs in (self.context['expected_independence_evidence_refs'],
                     self.context['preregistration']['independence_evidence_refs']):
            old = refs[0]['digest']; refs[0]['digest'] = 'f' * 64
            self.rejects(); refs[0]['digest'] = old

    def test_missing_changed_or_wrong_kind_evidence_rejected(self):
        for index in range(3):
            for mode in ('missing', 'digest', 'kind'):
                self.setUp()
                if mode == 'missing': self.context['evidence'].pop(index)
                elif mode == 'digest': self.context['evidence'][index]['digest'] = 'f' * 64
                else: self.context['evidence'][index]['kind'] = (
                    'INDEPENDENCE' if index else 'OBSERVATION')
                self.rejects()

    def test_evidence_cannot_appear_after_record_it_supports(self):
        for index, at in ((0, 2), (1, 2), (2, 4), (2, 11)):
            self.setUp(); self.context['evidence'][index]['available_at'] = at; self.rejects()

    def test_unregistered_source_rejected_and_absent_source_visible(self):
        self.context['evidence'][0]['source_id'] = 'unregistered'; self.rejects()
        self.setUp()
        self.plan['evidence_source_requirements'].append(dict(id='absent', requirement='Required source.'))
        self.repin()
        self.assertIn('REQUIRED_EVIDENCE_SOURCE_ABSENT', self.inspect()['blockers'])

    def test_missingness_visible_for_every_endpoint(self):
        for endpoint in ENDPOINTS:
            self.setUp()
            outcome = next(x for x in self.context['observations'][0]['outcomes'] if x['endpoint'] == endpoint)
            outcome.update(state='MISSING', value=None, missingness='Source unavailable.', evidence_refs=[])
            report = self.inspect()
            self.assertEqual(report['status'], 'PLAN_TRACE_INCOMPLETE')
            self.assertIn('MISSING_OUTCOMES_DECLARED', report['blockers'])
            self.assertEqual(report['supplied_outcome_inventory']['MINIMAL'][endpoint], dict(reported=0, missing=1))

    def test_missing_outcome_cannot_contain_value(self):
        self.context['observations'][0]['outcomes'][0]['state'] = 'MISSING'; self.rejects()

    def test_reported_outcome_requires_value_evidence_uncertainty_and_missingness(self):
        for key, value in (('value', None), ('evidence_refs', []), ('uncertainty', ''), ('missingness', '')):
            self.setUp(); self.context['observations'][0]['outcomes'][0][key] = value; self.rejects()

    def test_no_reported_outcomes_cannot_count_as_a_study(self):
        for observation in self.context['observations']:
            for outcome in observation['outcomes']:
                outcome.update(state='MISSING', value=None, evidence_refs=[], missingness='Unavailable.')
        report = self.inspect()
        self.assertIn('REPORTED_OUTCOMES_ABSENT', report['blockers'])
        self.assertEqual(report['study_completion'], 'NOT_ESTABLISHED')

    def test_one_arm_cannot_be_a_complete_comparison(self):
        self.context['observations'].pop()
        report = self.inspect()
        self.assertIn('COMPARISON_ARM_OBSERVATIONS_ABSENT', report['blockers'])
        self.assertEqual(report['status'], 'PLAN_TRACE_INCOMPLETE')

    def test_full_inputs_sha256_and_canonical_encoding(self):
        report = self.inspect()
        for value, key in ((self.plan, 'plan_digest'), (self.context, 'context_digest')):
            expected = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                ensure_ascii=True, allow_nan=False).encode('utf-8')).hexdigest()
            self.assertEqual(report[key], expected)
        self.plan = dict(reversed(list(self.plan.items())))
        self.assertEqual(report, self.inspect())
        self.context['now'] += 1
        self.assertNotEqual(report['context_digest'], self.inspect()['context_digest'])
        self.plan['privacy_permission_protocol'] += ' Supplied detail.'
        self.repin()
        self.assertNotEqual(report['plan_digest'], self.inspect()['plan_digest'])

    def test_no_mutation_or_returned_aliases(self):
        before = deepcopy((self.plan, self.context))
        report = self.inspect()
        self.assertEqual(before, (self.plan, self.context))
        saved = deepcopy(report)
        self.plan['arms'][0]['procedure'] = 'Changed later.'
        self.context['observations'].clear()
        self.assertEqual(report, saved)
        report['supplied_outcome_inventory']['FULL']['delay']['reported'] = 900
        self.assertEqual(self.plan['arms'][1], before[0]['arms'][1])

    def test_coordinated_supplied_rewrite_is_not_authenticated_history(self):
        self.plan['endpoints'][0]['criterion'] = 'All supplied pins can be fabricated together.'
        self.repin()
        report = self.inspect()
        self.assertEqual(report['status'], 'PLAN_TRACE_CONSISTENT')
        self.assertEqual(report['caller_pins_status'], 'SUPPLIED_UNAUTHENTICATED')
        self.assertEqual(report['preregistration_status'], 'SUPPLIED_UNVERIFIED')

    def test_prose_and_values_not_semantically_adjudicated(self):
        self.plan['stopping_criteria'] = 'Deliberately meaningless supplied prose.'
        self.context['observations'][0]['outcomes'][0]['value'] = 'Unsupported claim of superiority.'
        self.repin()
        report = self.inspect()
        self.assertEqual(report['semantic_assessment'], 'NOT_PERFORMED')
        self.assertEqual(report['empirical_superiority'], 'NOT_ESTABLISHED')

    def test_bounded_text_lists_and_full_json(self):
        self.plan['uncertainty_protocol'] = 'x' * 8193; self.rejects()
        self.setUp(); self.context['parties'] = ['p' + str(n) for n in range(257)]; self.rejects()
        self.setUp()
        self.plan['evidence_source_requirements'] = [
            dict(id=str(n), requirement='x' * 8192) for n in range(140)]
        self.rejects()

    def test_invalid_or_recursive_digest_input_normalized(self):
        recursive = []; recursive.append(recursive)
        for value in (recursive, {'value': float('nan')}, {'value': object()}):
            with self.assertRaises(StudyError): input_digest(value)
        self.plan['assessment'] = self.plan; self.rejects()


if __name__ == '__main__':
    unittest.main()
