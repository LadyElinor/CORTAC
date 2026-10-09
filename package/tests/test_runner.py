"""Disposable SQLite integration regressions; no authenticated-principal claims."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import threading
import unittest

from wac_offline.runner import (
    ScratchGateway, RunnerError, SCOPE, digest, evidence_record,
    validate_evidence, POLICY_FIELDS, PROPOSAL_FIELDS, MANDATE_FIELDS,
    RECEIPT_FIELDS, EVIDENCE_FIELDS, ROLES,
)
from wac_offline.runner_fixtures import checks, fixture, integration_report


def repin(data):
    """Rebuild fixture authority after an intentional policy/proposal change."""
    pd = digest('Policy', data['policy'])
    for name in ('initial', 'repair'):
        data[name]['policy_digest'] = pd
        data[name]['case_id'] = data['policy']['case_id']
    for grant in data['mandates']:
        grant['policy_digest'] = pd
        grant['case_id'] = data['policy']['case_id']
        grant['proposal_digest'] = digest('Proposal', data[grant['id']])
    return data


class RunnerTests(unittest.TestCase):
    def gateway(self, data=None):
        data = fixture() if data is None else data
        return self.enterContext(ScratchGateway(data['policy'], data['evidence'], data['mandates']))

    def initial(self, gateway, data, audit=True):
        effect = gateway.commit(data['initial'], checks(gateway, data['initial'], data['policy']),
                                'initial', 'executor')
        if audit:
            gateway.audit(effect, 'auditor')
        return effect

    def repair_checks(self, gateway, data, effect, identifier='complaint'):
        gateway.challenge(identifier, 'outsider', effect, ['source-v2'], 'Correct the ledger')
        review = gateway.review(identifier, data['repair'], 'reviewer')
        return checks(gateway, data['repair'], data['policy'], repair=True) + [review]

    def denied(self, gateway, call, pattern=None):
        """Rejections meter/journal the attempt but cannot leak partial effects."""
        before = gateway.snapshot()
        with self.assertRaises(RunnerError) as caught:
            call()
        if pattern:
            self.assertRegex(str(caught.exception), pattern)
        after = gateway.snapshot()
        self.assertEqual(after['tick'], before['tick'] + 1)
        self.assertEqual(after['journal'][:-1], before['journal'])
        self.assertEqual(after['journal'][-1]['result'], 'REJECTED')
        self.assertEqual(after['journal'][-1]['tick'], after['tick'])
        self.assertEqual({k: v for k, v in after.items() if k not in ('tick', 'journal')},
                         {k: v for k, v in before.items() if k not in ('tick', 'journal')})

    def test_ten_integration_outcomes_are_derived_from_persisted_state(self):
        report = integration_report()
        self.assertEqual(report['schema'], 'cortac.scratch.integration.v1')
        self.assertEqual(report['scope'], SCOPE)
        self.assertEqual((report['scenarios'], report['episodes']), (5, 10))
        self.assertEqual(report['real_model_calls'], 0)
        self.assertEqual(report['real_external_principals'], 0)
        self.assertIs(report['scored_study'], False)
        self.assertIs(report['external_execution_enabled'], False)
        self.assertIs(report['actual_disposable_database_effects'], True)
        expected_ticks = {('minimal', 'repair'): 12, ('full', 'repair'): 16,
                          ('minimal', 'budget'): 12, ('full', 'budget'): 14,
                          ('minimal', 'audit_budget'): 12, ('full', 'audit_budget'): 15,
                          ('minimal', 'conflicted_review'): 7, ('full', 'conflicted_review'): 9,
                          ('minimal', 'missing_repair_mandate'): 11, ('full', 'missing_repair_mandate'): 15}
        self.assertEqual({(r['arm'], r['scenario']) for r in report['rows']}, set(expected_ticks))
        for row in report['rows']:
            with self.subTest(arm=row['arm'], scenario=row['scenario']):
                good = row['scenario'] == 'repair' or (row['scenario'] in ('budget', 'audit_budget') and row['arm'] == 'minimal')
                corrected = good or row['scenario'] == 'audit_budget'
                state, outcome = row['trace'], row['outcome']
                self.assertEqual(row['status'], 'REPAIRED' if good else 'BLOCKED')
                self.assertEqual(outcome['final_value'], '12' if corrected else '10')
                self.assertEqual(outcome['final_revision'], 2 if corrected else 1)
                self.assertEqual(outcome['mutation_count'], len(state['effects']))
                self.assertEqual(outcome['unresolved_challenges'], 0 if good else 1)
                self.assertIs(outcome['initial_effect_observed'], True)
                self.assertIs(outcome['correction_effect_observed'], corrected)
                self.assertIs(outcome['audited_correction'], good)
                self.assertEqual(state['value'], outcome['final_value'])
                self.assertEqual(state['revision'], outcome['final_revision'])
                self.assertEqual(state['pending_audit'], 'effect-2' if corrected and not good else None)
                self.assertEqual(outcome['pending_audit'], state['pending_audit'])
                self.assertEqual(outcome['unmetered_budget_refusals'], int(row['blocker'] == 'operation budget exhausted'))
                self.assertEqual(outcome['metered_rejected_operations'], sum(j['result'] == 'REJECTED' for j in state['journal']))
                self.assertEqual(state['tick'], expected_ticks[row['arm'], row['scenario']])
                self.assertEqual(row['costs']['operations_used'], state['tick'])
                self.assertLessEqual(state['tick'], row['costs']['operation_cap'])
                self.assertEqual([j['tick'] for j in state['journal']], list(range(1, state['tick'] + 1)))
                for field in ('model_calls', 'model_tokens', 'paid_provider_cost_usd'):
                    self.assertEqual(row['costs'][field], 0)
                self.assertEqual(row['authority'], 'NONE')
                self.assertEqual(row['controller_closure'], 'SUPPLIED_UNVERIFIED')
                self.assertEqual(row['provenance'], 'SYNTHETIC_FIXTURE')
                self.assertIs(row['external_execution_enabled'], False)
                self.assertIs(row['scratch_effects_enabled'], True)
                if good:
                    self.assertIsNone(row['blocker'])
                    effect = state['effects'][-1]
                    self.assertEqual(state['challenges'][effect['repair_challenge_id']]['resolution'], digest('Effect', effect))
                else:
                    self.assertTrue(row['blocker'])

    def test_exact_constructor_schemas_reject_missing_and_unknown_fields(self):
        for name in ('policy', 'evidence', 'mandates'):
            original = fixture()[name]
            record = original if name == 'policy' else original[0]
            for field in list(record) + ['unknown_field']:
                with self.subTest(record=name, field=field):
                    data = fixture()
                    obj = data[name] if name == 'policy' else data[name][0]
                    if field == 'unknown_field':
                        obj[field] = True
                    else:
                        del obj[field]
                    with self.assertRaises(RunnerError):
                        self.gateway(data)

    def test_constructor_types_inventory_and_provenance(self):
        mutations = [
            ('policy', 'epoch', True), ('policy', 'operation_budget', False),
            ('policy', 'approval_threshold', 1.0), ('policy', 'principals', {}),
            ('policy', 'approval_ids', ['approval0', 'approval0']),
            ('policy', 'excluded_ids', ['missing']),
            ('evidence', 'provenance', 'VERIFIED'), ('evidence', 'content', 10),
            ('evidence', 'content_digest', 'A' * 64), ('evidence', 'content', 'forged'),
            ('mandates', 'provenance', 'VERIFIED'), ('mandates', 'max_uses', True), ('mandates', 'max_uses', 2),
            ('mandates', 'expires_tick', True), ('mandates', 'scope', 'EXTERNAL'),
            ('mandates', 'case_id', 'other-case'), ('mandates', 'policy_digest', '0' * 64),
            ('mandates', 'authorizer', 'proposer'), ('mandates', 'proposal_digest', 'bad')]
        for name, field, value in mutations:
            with self.subTest(name=name, field=field, value=value):
                data = fixture()
                obj = data[name] if name == 'policy' else data[name][0]
                obj[field] = value
                with self.assertRaises(RunnerError):
                    self.gateway(data)
        for name in ('evidence', 'mandates'):
            for malformed in ([], {}, None):
                with self.subTest(name=name, malformed=malformed):
                    data = fixture(); data[name] = malformed
                    with self.assertRaises(RunnerError): self.gateway(data)
            data = fixture(); data[name].append(deepcopy(data[name][0]))
            with self.assertRaises(RunnerError): self.gateway(data)
        for field, value in [('roles', ['approver', 'approver']), ('controller', ' '), ('extra', 1)]:
            data = fixture(); data['policy']['principals'][0][field] = value
            with self.assertRaises(RunnerError): self.gateway(data)

    def test_exact_proposal_schema_and_typed_binding(self):
        original = fixture()['initial']
        mutations = [(key, None, True) for key in original] + [('extra', 1, False)]
        mutations += [(k, v, False) for k, v in [
            ('epoch', True), ('expected_revision', False), ('epoch', 2),
            ('expected_revision', 1), ('case_id', 'other'), ('policy_digest', '0' * 64),
            ('operation', 'DELETE'), ('operation', ['COMMIT']), ('target', '/tmp/elsewhere'),
            ('value', 'forged'), ('proposer', 'missing'), ('decision_source', 'source-v2')]]
        for key, value, remove in mutations:
            with self.subTest(key=key, value=value, remove=remove):
                g = self.gateway(); p = deepcopy(original)
                if remove: del p[key]
                else: p[key] = value
                self.denied(g, lambda: g.issue(p, 'ASSESSMENT', 'assessor'))

    def test_evidence_closure_and_content_binding(self):
        for case in ('duplicate', 'unresolved', 'digest', 'unknown_ref_field', 'extra_ref',
                     'missing_ref', 'nested_unresolved', 'noncanonical', 'failed_limit'):
            with self.subTest(case=case):
                d = fixture(); p = d['initial']; g = self.gateway(d)
                if case == 'duplicate': p['evidence'] *= 2
                elif case == 'unresolved': p['evidence'][0]['id'] = 'unknown'
                elif case == 'digest': p['evidence'][0]['digest'] = '0' * 64
                elif case == 'unknown_ref_field': p['evidence'][0]['trusted'] = True
                elif case == 'extra_ref': p['evidence'].append(deepcopy(d['repair']['evidence'][0]))
                elif case == 'missing_ref': p['evidence'] = []
                elif case == 'nested_unresolved': p['decision_record']['alternatives'][0]['evidence_refs'] = ['unknown']
                elif case == 'noncanonical': p['evidence'] = deepcopy(d['repair']['evidence']) + p['evidence']
                else: p['decision_record']['protected_limit_assessments'][0]['status'] = 'FAIL'
                self.denied(g, lambda: g.issue(p, 'ASSESSMENT', 'assessor'))

    def test_receipt_exact_schema_tampering_and_json_types(self):
        for field in ('schema', 'scope', 'case_id', 'proposal_digest', 'policy_digest', 'epoch',
                      'expected_revision', 'operation', 'evidence_digest', 'kind', 'actor',
                      'challenge_digest', 'result', 'id', 'provenance', 'extra'):
            with self.subTest(field=field):
                d = fixture(); g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
                if field == 'epoch': rs[0][field] = True
                elif field == 'expected_revision': rs[0][field] = False
                else: rs[0][field] = 'altered'
                self.denied(g, lambda: g.commit(d['initial'], rs, 'initial', 'executor'))
        d = fixture(); g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
        del rs[0]['scope']
        self.denied(g, lambda: g.commit(d['initial'], rs, 'initial', 'executor'))

    def test_duplicate_receipts_and_votes_cannot_fill_threshold(self):
        for separately_issued in (False, True):
            with self.subTest(separately_issued=separately_issued):
                d = fixture('full'); g = self.gateway(d); p = d['initial']
                assessment = g.issue(p, 'ASSESSMENT', 'assessor')
                vote = g.issue(p, 'APPROVAL', 'approval0')
                other = g.issue(p, 'APPROVAL', 'approval0') if separately_issued else deepcopy(vote)
                rs = [assessment, vote, other, g.issue(p, 'APPROVAL', 'approval1'),
                      g.issue(p, 'AUTHORIZATION', 'authorizer')]
                self.denied(g, lambda: g.commit(p, rs, 'initial', 'executor'), 'duplicate|one actor')
        d = fixture('full'); g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
        rs = [r for r in rs if r['actor'] not in ('approval2', 'approval3')]
        self.denied(g, lambda: g.commit(d['initial'], rs, 'initial', 'executor'), 'threshold')

    def test_copied_cross_case_or_cross_proposal_receipts_fail(self):
        d = fixture(); source = self.gateway(d); rs = checks(source, d['initial'], d['policy'])
        fresh = self.gateway(d)
        self.denied(fresh, lambda: fresh.commit(d['initial'], rs, 'initial', 'executor'), 'unissued')
        other = fixture(); other['policy']['case_id'] = 'other-case'; repin(other)
        g = self.gateway(other); checks(g, other['initial'], other['policy'])
        self.denied(g, lambda: g.commit(other['initial'], rs, 'initial', 'executor'), 'altered')
        changed = deepcopy(d['initial']); changed['decision_record']['burden_justification'] += ' Changed.'
        self.denied(source, lambda: source.commit(changed, rs, 'initial', 'executor'), 'proposal mismatch')

    def test_mandate_mismatch_authorizer_expiry_and_unknown_do_not_mutate(self):
        for case in ('proposal', 'authorizer', 'expiry_boundary', 'expired', 'unknown'):
            with self.subTest(case=case):
                d = fixture(); grant = d['mandates'][0]
                if case == 'proposal': grant['proposal_digest'] = '0' * 64
                elif case == 'authorizer': grant['authorizer'] = 'repair_authorizer'
                elif case == 'expiry_boundary': grant['expires_tick'] = 4
                elif case == 'expired': grant['expires_tick'] = 3
                g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
                self.denied(g, lambda: g.commit(d['initial'], rs, 'absent' if case == 'unknown' else 'initial', 'executor'),
                            'mandate')

    def test_stale_revision_and_mandate_replay_are_non_effects(self):
        d = fixture(); g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
        effect = g.commit(d['initial'], rs, 'initial', 'executor')
        g.audit(effect, 'auditor')
        self.denied(g, lambda: g.commit(d['initial'], rs, 'initial', 'executor'), 'stale')
        self.denied(g, lambda: g.issue(d['initial'], 'ASSESSMENT', 'assessor'), 'stale')
        self.assertEqual(g.snapshot()['used_mandates'], ['initial'])

    def test_no_self_review_or_controller_overlap(self):
        for conflicting in ('proposer', 'assessor', 'authorizer', 'executor', 'auditor'):
            with self.subTest(conflicting=conflicting):
                d = fixture()
                next(p for p in d['policy']['principals'] if p['id'] == 'reviewer')['controller'] = 'synthetic-controller-' + conflicting
                repin(d); g = self.gateway(d); effect = self.initial(g, d)
                g.challenge('c', 'unregistered', effect, ['source-v2'], 'Correction')
                self.denied(g, lambda: g.review('c', d['repair'], 'reviewer'), 'controller conflict')
        for actor, other in [('assessor', 'proposer'), ('assessor', 'outsider'),
                             ('executor', 'authorizer'), ('approval0', 'assessor')]:
            with self.subTest(actor=actor, other=other):
                d = fixture()
                next(p for p in d['policy']['principals'] if p['id'] == actor)['controller'] = 'synthetic-controller-' + other
                repin(d); g = self.gateway(d)
                if actor == 'assessor':
                    self.denied(g, lambda: g.issue(d['initial'], 'ASSESSMENT', actor), 'controller conflict')
                else:
                    rs = checks(g, d['initial'], d['policy'])
                    self.denied(g, lambda: g.commit(d['initial'], rs, 'initial', 'executor'), 'controller conflict')
        d = fixture('full')
        next(p for p in d['policy']['principals'] if p['id'] == 'approval1')['controller'] = 'synthetic-controller-approval0'
        with self.assertRaisesRegex(RunnerError, 'shares a declared controller'): self.gateway(repin(d))

    def test_unknown_claimants_can_open_holds_but_cannot_bypass_review_independence(self):
        d = fixture(); g = self.gateway(d); effect = self.initial(g, d)
        challenge = g.challenge('c', 'unknown-outsider', effect, ['source-v2'], 'Correction')
        self.assertEqual(challenge['claimant'], 'unknown-outsider')
        self.denied(g, lambda: g.review('c', d['repair'], 'reviewer'), 'claimant controller unknown')
        self.assertIsNone(g.snapshot()['challenges']['c']['resolution'])

    def test_known_claimant_cannot_review_their_own_challenge(self):
        d = fixture(); g = self.gateway(d); effect = self.initial(g, d)
        g.challenge('c', 'reviewer', effect, ['source-v2'], 'Correction')
        self.denied(g, lambda: g.review('c', d['repair'], 'reviewer'), 'controller conflict')

    def test_repair_authorizer_cannot_reauthorize_own_original_effect(self):
        d = fixture()
        next(p for p in d['policy']['principals'] if p['id'] == 'repair_authorizer')['controller'] = 'synthetic-controller-authorizer'
        repin(d); g = self.gateway(d); effect = self.initial(g, d)
        rs = self.repair_checks(g, d, effect)
        self.denied(g, lambda: g.commit(d['repair'], rs, 'repair', 'executor'), 'controller conflict')

    def test_unrelated_holds_persist_and_block_atomic_repair(self):
        d = fixture(); g = self.gateway(d); effect = self.initial(g, d)
        rs = self.repair_checks(g, d, effect)
        g.challenge('other', 'another-outsider', effect, ['source-v2'], 'Independent hold')
        self.denied(g, lambda: g.commit(d['repair'], rs, 'repair', 'executor'), 'unrelated holds')
        self.assertEqual(len(g.snapshot()['challenges']), 2)
        self.assertTrue(all(c['resolution'] is None for c in g.snapshot()['challenges'].values()))

    def test_challenge_and_review_evidence_closure_and_duplicates(self):
        d = fixture(); g = self.gateway(d); effect = self.initial(g, d)
        for refs in ([], ['missing'], ['source-v2', 'source-v2'], 'source-v2'):
            self.denied(g, lambda: g.challenge('c', 'outsider', effect, refs, 'Correction'), 'evidence')
        g.challenge('c', 'outsider', effect, ['source-v1'], 'Check original too')
        self.denied(g, lambda: g.review('c', d['repair'], 'reviewer'), 'omits challenge evidence')
        self.denied(g, lambda: g.challenge('c', 'outsider', effect, ['source-v2'], 'Duplicate'), 'duplicate')
        self.denied(g, lambda: g.review('unknown', d['repair'], 'reviewer'), 'known repair challenge')

    def test_pending_audit_blocks_next_effect_and_audit_is_bound_to_state(self):
        d = fixture(); g = self.gateway(d); effect = self.initial(g, d, audit=False)
        rs = self.repair_checks(g, d, effect)
        self.denied(g, lambda: g.commit(d['repair'], rs, 'repair', 'executor'), 'requires audit')
        forged = deepcopy(effect); forged['after_value'] = 'forged'
        self.denied(g, lambda: g.audit(forged, 'auditor'), 'not current')
        audit = g.audit(effect, 'auditor')
        self.assertEqual(audit['observed_value'], '10')
        self.assertEqual(audit['effect_digest'], digest('Effect', effect))
        self.denied(g, lambda: g.audit(effect, 'repair_auditor'), 'not current')
        repair = g.commit(d['repair'], rs, 'repair', 'executor')
        self.assertIsNone(g.snapshot()['challenges']['complaint']['resolution'])
        self.denied(g, lambda: g.audit(effect, 'repair_auditor'), 'not current')
        g.audit(repair, 'repair_auditor')
        self.assertEqual(g.snapshot()['challenges']['complaint']['resolution'], digest('Effect', repair))
        self.assertIsNone(g.snapshot()['pending_audit'])

    def test_actual_sqlite_effect_and_context_cleanup(self):
        d = fixture(); g = ScratchGateway(d['policy'], d['evidence'], d['mandates'])
        with g:
            directory = Path(g._temporary.name)
            database = directory / 'effects.sqlite'
            self.assertTrue(database.is_file())
            with sqlite3.connect(str(database)) as observer:
                before = json.loads(observer.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
                self.assertEqual((before['revision'], before['value']), (0, None))
                effect = self.initial(g, d)
                observed = json.loads(observer.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
                self.assertEqual(observed, g.snapshot())
                self.assertEqual((observed['revision'], observed['value']), (1, '10'))
                self.assertEqual(observed['effects'], [effect])
        self.assertFalse(directory.exists())
        with self.assertRaises(sqlite3.ProgrammingError): g.snapshot()

    def test_context_cleans_up_on_exception(self):
        d = fixture(); g = ScratchGateway(d['policy'], d['evidence'], d['mandates'])
        directory = Path(g._temporary.name)
        with self.assertRaisesRegex(RuntimeError, 'intentional'):
            with g: raise RuntimeError('intentional')
        self.assertFalse(directory.exists())

    def test_snapshot_and_input_output_copy_isolation(self):
        d = fixture(); original = deepcopy(d); g = self.gateway(d)
        d['policy']['operation_budget'] = 1
        d['evidence'][0]['content'] = 'forged'
        d['mandates'][0]['proposal_digest'] = '0' * 64
        snapshot = g.snapshot(); snapshot['revision'] = 99; snapshot['receipts']['fake'] = {}
        self.assertEqual(g.snapshot()['revision'], 0)
        rs = checks(g, original['initial'], original['policy'])
        stored = deepcopy(rs); rs[0]['result'] = 'FAIL'
        self.assertEqual(g.snapshot()['receipts'][stored[0]['id']], stored[0])
        effect = g.commit(original['initial'], stored, 'initial', 'executor')
        original_effect = deepcopy(effect); effect['after_value'] = 'forged'
        self.assertEqual(g.snapshot()['effects'], [original_effect])
        other = self.gateway(original)
        self.assertEqual((other.snapshot()['revision'], other.snapshot()['value']), (0, None))

    def test_concurrent_same_revision_and_mandate_only_one_effect(self):
        d = fixture(); g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
        gate = threading.Barrier(2)
        def attempt():
            gate.wait(timeout=5)
            try:
                return ('success', g.commit(d['initial'], rs, 'initial', 'executor'))
            except RunnerError as exc:
                return ('rejected', str(exc))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt) for _ in range(2)]
            results = [f.result(timeout=10) for f in futures]
        self.assertCountEqual([r[0] for r in results], ['success', 'rejected'])
        state = g.snapshot()
        self.assertEqual((state['revision'], state['value']), (1, '10'))
        self.assertEqual(len(state['effects']), 1)
        self.assertEqual(state['used_mandates'], ['initial'])
        self.assertEqual(state['pending_audit'], state['effects'][0]['id'])
        self.assertCountEqual([j['result'] for j in state['journal'][-2:]], ['ACCEPTED', 'REJECTED'])

    def test_budget_exhaustion_has_no_unmetered_effect_or_journal_growth(self):
        d = fixture(budget=3); g = self.gateway(d); rs = checks(g, d['initial'], d['policy'])
        before = g.snapshot()
        with self.assertRaisesRegex(RunnerError, 'budget exhausted'):
            g.commit(d['initial'], rs, 'initial', 'executor')
        self.assertEqual(g.snapshot(), before)
        self.assertEqual(before['effects'], [])

    def test_digest_is_canonical_and_domain_separated(self):
        self.assertEqual(digest('X', {'b': 2, 'a': 1}), digest('X', {'a': 1, 'b': 2}))
        self.assertNotEqual(digest('X', {'a': 1}), digest('Y', {'a': 1}))
        self.assertNotEqual(digest('X', {'a': 1}), digest('X', {'a': True}))
        with self.assertRaises(ValueError): digest('X', float('nan'))
        record = evidence_record('id', 'supplied-fixture', 'unicode: \u03b1')
        validate_evidence(record)
        changed = deepcopy(record); changed['content'] += '!'
        with self.assertRaisesRegex(RunnerError, 'bytes mismatch'): validate_evidence(changed)

    def test_published_schema_parity_with_runtime_and_generated_records(self):
        schema_path = Path(__file__).resolve().parents[1] / 'wac_offline/data/runner_records.schema.json'
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        definitions = schema['$defs']
        for name, fields in [('policy', POLICY_FIELDS), ('proposal', PROPOSAL_FIELDS),
                             ('mandate', MANDATE_FIELDS), ('receipt', RECEIPT_FIELDS),
                             ('evidence', EVIDENCE_FIELDS)]:
            with self.subTest(definition=name):
                self.assertEqual(set(definitions[name]['required']), set(fields))
                self.assertEqual(set(definitions[name]['properties']), set(fields))
                self.assertIs(definitions[name]['additionalProperties'], False)
        role_schema = definitions['policy']['properties']['principals']['items']['properties']['roles']['items']
        self.assertEqual(set(role_schema['enum']), ROLES)
        d = fixture(); g = self.gateway(d)
        rs = checks(g, d['initial'], d['policy'])
        effect = g.commit(d['initial'], rs, 'initial', 'executor')
        audit = g.audit(effect, 'auditor')
        challenge = g.challenge('c', 'outsider', effect, ['source-v2'], 'Correction')
        review = g.review('c', d['repair'], 'reviewer')
        records = [('policy', d['policy']), ('proposal', d['initial']), ('proposal', d['repair']),
                   ('effect', effect), ('audit', audit), ('stored_challenge', challenge),
                   ('challenge', {k: v for k, v in challenge.items() if k not in ('digest', 'resolution')}),
                   ('receipt', review)]
        records += [('receipt', r) for r in rs] + [('evidence', e) for e in d['evidence']]
        records += [('mandate', m) for m in d['mandates']]
        for name, record in records:
            with self.subTest(record=name):
                definition = definitions[name]
                self.assertEqual(set(record), set(definition['required']))
                self.assertEqual(set(record), set(definition['properties']))
                self.assertIs(definition['additionalProperties'], False)
                for key, rule in definition['properties'].items():
                    if 'const' in rule:
                        self.assertEqual(record[key], rule['const'])
                if name not in ('policy', 'proposal'):
                    self.assertEqual(record['provenance'], 'SYNTHETIC_FIXTURE')

    def test_fixture_rejects_unknown_arms_and_scenarios(self):
        with self.assertRaises(ValueError): fixture('unknown')
        with self.assertRaises(ValueError): fixture(scenario='unknown')


if __name__ == '__main__':
    unittest.main()
