"""Synthetic mandate revocation is local, metered, and transaction-ordered."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3
import threading
import unittest

from wac_offline.runner import RunnerError, SCOPE, ScratchGateway, digest
from wac_offline.runner_fixtures import checks, fixture


def repin(data):
    """Bind fixture proposals and grants after changing the principal inventory."""
    policy_digest = digest('Policy', data['policy'])
    for name in ('initial', 'repair'):
        data[name]['policy_digest'] = policy_digest
    for grant in data['mandates']:
        grant['policy_digest'] = policy_digest
        grant['proposal_digest'] = digest('Proposal', data[grant['id']])


class RunnerRevocationTests(unittest.TestCase):
    def gateway(self, data=None):
        data = fixture() if data is None else data
        gateway = ScratchGateway(data['policy'], data['evidence'], data['mandates'])
        self.addCleanup(gateway.close)
        return gateway

    def denied(self, gateway, call, pattern=None):
        before = gateway.snapshot()
        with self.assertRaises(RunnerError) as caught:
            call()
        if pattern is not None:
            self.assertRegex(str(caught.exception), pattern)
        after = gateway.snapshot()
        self.assertEqual(after['tick'], before['tick'] + 1)
        self.assertEqual(after['journal'][:-1], before['journal'])
        self.assertEqual(after['journal'][-1]['tick'], after['tick'])
        self.assertEqual(after['journal'][-1]['result'], 'REJECTED')
        self.assertEqual({k: v for k, v in after.items() if k not in ('tick', 'journal')},
                         {k: v for k, v in before.items() if k not in ('tick', 'journal')})

    def test_revocation_record_is_bound_to_exact_pinned_mandate(self):
        data = fixture()
        gateway = self.gateway(data)
        self.assertEqual(gateway.snapshot()['revoked_mandates'], {})
        before = gateway.snapshot()
        record = gateway.revoke('initial', 'authorizer', 'Withdraw scratch authorization')
        expected = dict(schema='cortac.scratch.revocation.v1', mandate_id='initial',
                        mandate_digest=digest('Mandate', data['mandates'][0]),
                        actor='authorizer', reason='Withdraw scratch authorization',
                        tick=1, scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
        self.assertEqual(record, expected)
        after = gateway.snapshot()
        self.assertEqual(after['revoked_mandates'], {'initial': expected})
        self.assertEqual(after['tick'], 1)
        self.assertEqual(after['journal'], [dict(tick=1, action='revoke', result='ACCEPTED',
                                               result_digest=digest('Result', expected))])
        for key in before.keys() - {'tick', 'journal', 'revoked_mandates'}:
            self.assertEqual(after[key], before[key], key)

    def test_only_exact_authorizer_may_revoke_even_same_controller_alias(self):
        data = fixture(budget=40)
        controller = next(p['controller'] for p in data['policy']['principals']
                          if p['id'] == 'authorizer')
        data['policy']['principals'].append(dict(id='fresh_authorizer_label',
                                                controller=controller, roles=['authorizer']))
        repin(data)
        gateway = self.gateway(data)
        for actor in ('repair_authorizer', 'fresh_authorizer_label', 'executor', 'outsider',
                      'missing', '', ' ', None, True, [], {}):
            with self.subTest(actor=actor):
                self.denied(gateway, lambda: gateway.revoke('initial', actor, 'Withdraw'))
        gateway.revoke('initial', 'authorizer', 'Exact original authorizer')
        self.assertEqual(set(gateway.snapshot()['revoked_mandates']), {'initial'})

    def test_invalid_and_unknown_revocations_change_only_meter_and_journal(self):
        gateway = self.gateway(fixture(budget=40))
        for mandate_id in ('missing', '', ' ', None, True, 1, [], {}):
            with self.subTest(mandate_id=mandate_id):
                self.denied(gateway, lambda: gateway.revoke(mandate_id, 'authorizer', 'Withdraw'))
        for reason in ('', ' \n\t', None, True, 1, [], {}):
            with self.subTest(reason=reason):
                self.denied(gateway, lambda: gateway.revoke('initial', 'authorizer', reason))
        self.assertTrue(all(j['action'] == 'revoke' for j in gateway.snapshot()['journal']))

    def test_duplicate_is_rejected_and_original_revocation_cannot_be_overwritten(self):
        gateway = self.gateway()
        record = gateway.revoke('initial', 'authorizer', 'Original irreversible withdrawal')
        self.denied(gateway, lambda: gateway.revoke('initial', 'authorizer', 'Replacement reason'),
                    'already revoked')
        self.assertEqual(gateway.snapshot()['revoked_mandates']['initial'], record)
        gateway.revoke('repair', 'repair_authorizer', 'Independent grant withdrawal')
        self.assertEqual(set(gateway.snapshot()['revoked_mandates']), {'initial', 'repair'})

    def test_revoke_first_blocks_both_existing_and_fresh_receipts(self):
        data = fixture()
        gateway = self.gateway(data)
        old_receipts = checks(gateway, data['initial'], data['policy'])
        record = gateway.revoke('initial', 'authorizer', 'Withdraw before commit')
        self.denied(gateway, lambda: gateway.commit(data['initial'], old_receipts,
                                                  'initial', 'executor'), 'revoked')
        fresh_receipts = checks(gateway, data['initial'], data['policy'])
        self.assertTrue(set(r['id'] for r in old_receipts).isdisjoint(
            r['id'] for r in fresh_receipts))
        self.denied(gateway, lambda: gateway.commit(data['initial'], fresh_receipts,
                                                  'initial', 'executor'), 'revoked')
        state = gateway.snapshot()
        self.assertEqual(state['revision'], 0)
        self.assertIsNone(state['value'])
        self.assertEqual(state['effects'], [])
        self.assertEqual(state['used_mandates'], [])
        self.assertIsNone(state['pending_audit'])
        self.assertEqual(state['revoked_mandates'], {'initial': record})

    def test_commit_first_keeps_effect_consumption_and_pending_audit(self):
        data = fixture()
        gateway = self.gateway(data)
        receipts = checks(gateway, data['initial'], data['policy'])
        effect = gateway.commit(data['initial'], receipts, 'initial', 'executor')
        before = gateway.snapshot()
        record = gateway.revoke('initial', 'authorizer', 'Withdraw after commit')
        after = gateway.snapshot()
        for key in before.keys() - {'tick', 'journal', 'revoked_mandates'}:
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(after['effects'], [effect])
        self.assertEqual(after['used_mandates'], ['initial'])
        self.assertEqual(after['pending_audit'], effect['id'])
        self.assertEqual(after['value'], data['initial']['value'])
        self.assertEqual(after['revision'], 1)
        self.assertEqual(after['revoked_mandates'], {'initial': record})
        gateway.audit(effect, 'auditor')
        self.assertIsNone(gateway.snapshot()['pending_audit'])
        self.assertEqual(gateway.snapshot()['revoked_mandates'], {'initial': record})

    def test_two_thread_commit_revoke_race_follows_persisted_journal_order(self):
        data = fixture()
        gateway = self.gateway(data)
        receipts = checks(gateway, data['initial'], data['policy'])
        initial_tick = gateway.snapshot()['tick']
        barrier = threading.Barrier(2)

        def run(action):
            barrier.wait(timeout=10)
            try:
                if action == 'commit':
                    result = gateway.commit(data['initial'], receipts, 'initial', 'executor')
                else:
                    result = gateway.revoke('initial', 'authorizer', 'Concurrent withdrawal')
                return 'ACCEPTED', result
            except RunnerError as exc:
                return 'REJECTED', str(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {action: pool.submit(run, action) for action in ('commit', 'revoke')}
            outcomes = {action: future.result(timeout=15) for action, future in futures.items()}
        state = gateway.snapshot()
        ordered = state['journal'][-2:]
        self.assertEqual([j['tick'] for j in ordered], [initial_tick + 1, initial_tick + 2])
        self.assertEqual({j['action'] for j in ordered}, {'commit', 'revoke'})
        for entry in ordered:
            self.assertEqual(entry['result'], outcomes[entry['action']][0])
        self.assertEqual(outcomes['revoke'][0], 'ACCEPTED')
        self.assertEqual(state['revoked_mandates'], {'initial': outcomes['revoke'][1]})
        if ordered[0]['action'] == 'revoke':
            self.assertEqual(outcomes['commit'][0], 'REJECTED')
            self.assertRegex(outcomes['commit'][1], 'revoked')
            self.assertEqual(state['effects'], [])
            self.assertEqual(state['used_mandates'], [])
            self.assertEqual(state['revision'], 0)
            self.assertIsNone(state['value'])
            self.assertIsNone(state['pending_audit'])
        else:
            self.assertEqual(outcomes['commit'][0], 'ACCEPTED')
            effect = outcomes['commit'][1]
            self.assertEqual(state['effects'], [effect])
            self.assertEqual(state['used_mandates'], ['initial'])
            self.assertEqual(state['revision'], 1)
            self.assertEqual(state['value'], data['initial']['value'])
            self.assertEqual(state['pending_audit'], effect['id'])

    def test_revocation_budget_is_metered_and_exhaustion_is_nonmutating(self):
        gateway = self.gateway(fixture(budget=2))
        self.denied(gateway, lambda: gateway.revoke('initial', 'repair_authorizer', 'Wrong actor'))
        gateway.revoke('initial', 'authorizer', 'Final permitted operation')
        before = gateway.snapshot()
        self.assertEqual(before['tick'], 2)
        with self.assertRaisesRegex(RunnerError, 'budget exhausted'):
            gateway.revoke('repair', 'repair_authorizer', 'Over budget')
        self.assertEqual(gateway.snapshot(), before)

    def test_failed_sqlite_write_cannot_publish_partial_revocation(self):
        gateway = self.gateway()
        before = gateway.snapshot()
        gateway._db.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON state "
                            "BEGIN SELECT RAISE(ABORT, 'injected storage failure'); END")
        gateway._db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            gateway.revoke('initial', 'authorizer', 'Attempt during failed storage')
        self.assertEqual(gateway.snapshot(), before)
        gateway._db.execute('DROP TRIGGER reject_update')
        gateway._db.commit()
        record = gateway.revoke('initial', 'authorizer', 'Retry after storage recovery')
        self.assertEqual(record['tick'], 1)
        self.assertEqual(gateway.snapshot()['revoked_mandates'], {'initial': record})

    def test_constructor_return_and_snapshot_revocation_copy_isolation(self):
        data = fixture()
        original_grant = deepcopy(data['mandates'][0])
        gateway = self.gateway(data)
        data['mandates'][0]['authorizer'] = 'repair_authorizer'
        data['mandates'][0]['proposal_digest'] = '0' * 64
        self.denied(gateway, lambda: gateway.revoke('initial', 'repair_authorizer', 'Changed input'))
        record = gateway.revoke('initial', 'authorizer', 'Pinned grant')
        expected = deepcopy(record)
        self.assertEqual(record['mandate_digest'], digest('Mandate', original_grant))
        record['reason'] = 'Tampered return'
        record['actor'] = 'repair_authorizer'
        snapshot = gateway.snapshot()
        snapshot['revoked_mandates']['initial']['reason'] = 'Tampered snapshot'
        snapshot['revoked_mandates'].clear()
        snapshot['journal'].clear()
        self.assertEqual(gateway.snapshot()['revoked_mandates'], {'initial': expected})
        receipts = checks(gateway, data['initial'], data['policy'])
        self.denied(gateway, lambda: gateway.commit(data['initial'], receipts, 'initial', 'executor'),
                    'revoked')


if __name__ == '__main__':
    unittest.main()
