"""Lifecycle counterexamples: local consistency is not evidence authenticity."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from wac_offline.scaffold_v1 import ap1, transport
from wac_offline.scaffold_v1.agent import decide
from wac_offline.scaffold_v1.audit import audit
from wac_offline.scaffold_v1.demo import assignment, limits, run, task
from wac_offline.scaffold_v1.journal import Journal
from wac_offline.scaffold_v1.wire import canonical, digest, parse

ROOT = Path(__file__).resolve().parents[2]
TOKEN = 'ucp1.'+'a'*32+'.'+'b'*64


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.j = Journal.create(self.root/'journal.sqlite', task(), assignment(), limits())

    def propose(self):
        b = self.j.begin_decision()
        self.j.finish_decision(canonical(decide(b)).encode(), elapsed_ns=7)

    def bind(self):
        self.propose()
        s = self.j.state()
        request = ap1.interpret(s['genesis']['brief'], s['decision']['reply'])
        self.j.append('intent_bound', dict(outbox=str(self.root/'outbox.sqlite'),
            url='http://127.0.0.1:12345', credential_digest=hashlib.sha256(TOKEN.encode()).hexdigest(),
            instance=task()['instance'], request_id=request['request_id'], raw_sha256=digest(request)))

    def status(self, accepted=False):
        binding = self.j.state()['binding']
        receipt = dict(protocol=ap1.PROTOCOL, disposition='ACCEPTED', external_authority='NONE',
            request_id=binding['request_id'], instance=binding['instance'], event_seq=2,
            event_hash='3'*64, proposal_id='propose-2', permits_execution=False)
        return dict(version='client-only-2.0.0', state='RECORDED' if accepted else 'UNRESOLVED',
                    request_id=binding['request_id'], instance=binding['instance'],
                    operations_started=int(accepted), operations_observed=int(accepted),
                    latest_observation='RECORDED' if accepted else None,
                    recorded={'http_status': 200, 'receipt': receipt} if accepted else None,
                    external_authority='NONE', assurance='Synthetic conformance observation')

    def accepted(self):
        self.bind()
        self.j.append('operation_start', {'kind': 'stage'})
        self.j.append('operation_finish', {'status': self.status(), 'elapsed_ns': 2, 'recovered': False})
        self.j.append('operation_start', {'kind': 'submit'})
        self.j.append('operation_finish', {'status': self.status(True), 'elapsed_ns': 3, 'recovered': False})

    def test_offline_demo_partition(self):
        result = run()
        self.assertEqual([r['decision'] for r in result['cases']],
                         ['PROPOSE','DECLINE','WAIT','REQUEST-EVIDENCE','INVALID','TIMEOUT','CRASH'])
        self.assertEqual(result['network_calls'], 0)

    def test_projection_discards_private_fields(self):
        t = task(); t['task']['private'] = {'secret': 'not-public'}
        t['task']['lessons'] = {'a': {'scope': 'test', 'private': 'hidden'}}
        other = Journal.create(self.root/'other', t, assignment(), limits())
        self.assertNotIn('private', canonical(other.state()))
        self.assertNotIn('hidden', canonical(other.state()))

    def test_no_overwrite_or_duplicate_decisions(self):
        with self.assertRaises(FileExistsError):
            Journal.create(self.j.path, task(), assignment(), limits())
        self.propose()
        for action in (self.j.begin_decision, lambda: self.j.finish_decision(outcome='TIMEOUT')):
            with self.assertRaises(ValueError): action()

    def test_invalid_and_wrong_brief_are_not_abstention(self):
        b = self.j.begin_decision(); reply = decide(b); reply['brief_id'] = '0'*64
        self.j.finish_decision(canonical(reply).encode(), elapsed_ns=1)
        self.assertEqual(self.j.report()['decision'], 'INVALID')

    def test_duplicate_json_and_credential_redaction(self):
        self.j.begin_decision()
        raw = ('{"a":1,"a":2,"secret":"'+TOKEN+'"}').encode()
        self.j.finish_decision(raw, elapsed_ns=1)
        self.assertEqual(self.j.report()['decision'], 'INVALID')
        self.assertNotIn(TOKEN.encode(), self.j.path.read_bytes())
        self.assertEqual(self.j.state()['decision']['response_sha256'], hashlib.sha256(raw).hexdigest())

    def test_json_bounds(self):
        for raw in (b'{"a":1,"\\u0061":2}', b'[NaN]', b'[1e999]', b'['*80+b'0'+b']'*80,
                    b'{"x":9007199254740993}', b'\xff', b' '* (2*1024*1024+1)):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError): parse(raw)

    def test_unknown_and_execution_events_refused(self):
        self.propose()
        for event in ('execute', 'approve', 'append-workshop', 'revoke-vote'):
            with self.assertRaises(ValueError): self.j.append(event, {})
        self.assertFalse(self.j.report()['execution_enabled'])

    def test_replay_and_independent_counts(self):
        self.accepted()
        report = Journal(self.j.path).report()
        self.assertEqual(report['elapsed_ns_observed'], 12)
        self.assertTrue(audit(self.j.path, report)['verified'])
        for field, value in [('decision', 'DECLINE'), ('operations_started', 3),
                             ('authority', 'EXECUTE'), ('elapsed_ns_observed', 99)]:
            altered = dict(report); altered[field] = value
            with self.assertRaises(ValueError): audit(self.j.path, altered)

    def test_journal_tampering_and_repaired_hash_semantics(self):
        self.propose()
        with sqlite3.connect(self.j.path) as db:
            db.execute("UPDATE events SET hash=? WHERE seq=3", ('0'*64,))
        with self.assertRaises(ValueError): self.j.report()
        with sqlite3.connect(self.j.path) as db:
            n,k,raw,prev,_ = db.execute('SELECT * FROM events WHERE seq=3').fetchone()
            body = json.loads(raw); body['reply']['brief_id'] = '0'*64
            h = digest(dict(seq=n,kind=k,body=body,previous=prev))
            db.execute('UPDATE events SET body=?,hash=? WHERE seq=3', (canonical(body), h))
        with self.assertRaises(ValueError): self.j.report()

    def test_interrupted_decision_is_visible(self):
        self.j.begin_decision()
        self.assertEqual(Journal(self.j.path).report()['decision'], 'INTERRUPTED_OR_PENDING')
        self.j.finish_decision(outcome='CRASH', elapsed_ns=4)
        self.assertEqual(self.j.report()['decision'], 'CRASH')

    def test_receipt_cannot_grant_authority(self):
        self.bind(); self.j.append('operation_start', {'kind': 'stage'})
        status = self.status(True); status['recorded']['receipt']['permits_execution'] = True
        with self.assertRaises(ValueError):
            self.j.append('operation_finish', dict(status=status, elapsed_ns=1, recovered=False))
        self.assertEqual(self.j.report()['pending_operation'], 'stage')

    def test_conflicting_request_and_forged_counts_refused(self):
        self.bind(); self.j.append('operation_start', {'kind': 'stage'})
        for key, value in [('request_id','other'),('operations_started',True),('operations_observed',2)]:
            status=self.status(); status[key]=value
            with self.assertRaises(ValueError):
                self.j.append('operation_finish', dict(status=status, elapsed_ns=1, recovered=False))

    def test_review_links_decision_and_preserves_dissent_without_authority(self):
        self.accepted()
        record=json.loads((ROOT/'package/fixtures/decision_record.json').read_text())
        for status in ('FAIL','UNKNOWN'):
            record['protected_limit_assessments'][0]['status']=status
            from wac_offline.decision_records import validate_decision_record
            self.assertFalse(validate_decision_record(record, limits()))
        with self.assertRaises(ValueError): self.j.review('worker', record)
        self.j.review('reviewer', record)
        self.assertFalse(self.j.report()['advisory_review']['supplied_assessments_pass'])
        self.assertEqual(self.j.report()['advisory_review']['record']['dissent'], record['dissent'])
        self.assertEqual(self.j.report()['host_authority'], 'NOT_OBSERVED')
        audit(self.j.path, self.j.report())

    def test_declared_controller_conflict(self):
        a=assignment(); a['reviewer_controller']=a['controller']
        with self.assertRaises(ValueError): Journal.create(self.root/'conflict',task(),a,limits())

    def test_no_stage_for_decline_and_no_missing_outbox_recovery(self):
        b=self.j.begin_decision()
        self.j.finish_decision(canonical(dict(profile=b['profile'], brief_id=b['brief_id'], choice='decline', reason='No.')).encode())
        with self.assertRaises(ValueError): transport.stage(self.j,self.root/'outbox','http://127.0.0.1:123',TOKEN)
        self.assertIsNone(self.j.state()['binding'])

    def test_missing_client_fails_before_binding(self):
        self.propose()
        with patch.object(transport,'client',side_effect=ValueError('unavailable')):
            with self.assertRaises(ValueError): transport.stage(self.j,self.root/'outbox','http://127.0.0.1:123',TOKEN)
        self.assertIsNone(self.j.state()['binding'])

    def test_interrupted_stage_cannot_restage_missing_file(self):
        self.bind(); self.j.append('operation_start', {'kind':'stage'})
        with self.assertRaises(ValueError): transport.recover(self.j,TOKEN)
        self.assertEqual(self.j.report()['pending_operation'],'stage')
        with self.assertRaises(ValueError): self.j.append('operation_start',{'kind':'stage'})

    def test_wrong_credential_and_remote_endpoint(self):
        self.bind()
        with self.assertRaises(ValueError): transport.operate(self.j,TOKEN[:-1]+'c','submit')
        for url in ('https://127.0.0.1:3','http://example.com:3','http://127.0.0.1:3/a'):
            with self.assertRaises(ValueError): transport.check_endpoint(url)

    def test_model_policy_not_attested(self):
        # A conforming different method is allowed despite the declared implementation label.
        b=self.j.begin_decision(); d=decide(b); d['method']='zero-fill'
        self.j.finish_decision(canonical(d).encode())
        self.assertFalse(self.j.report()['policy_fidelity_verified'])

    def test_scope_types_and_incomplete_rebuilt_brief_refused(self):
        from wac_offline.scaffold_v1.journal import initial
        g=self.j.state()['genesis']; g['execution_enabled']=0
        with self.assertRaises(ValueError): initial(g)
        g=self.j.state()['genesis']; del g['brief']['work']['worker']
        g['brief']['brief_id']=digest({k:v for k,v in g['brief'].items() if k!='brief_id'})
        with self.assertRaises(ValueError): initial(g)

    def test_stage_and_empty_recovery_cannot_invent_receipt(self):
        self.bind();self.j.append('operation_start',{'kind':'stage'})
        with self.assertRaises(ValueError):
            self.j.append('operation_finish',dict(status=self.status(True),elapsed_ns=0,recovered=False))
        with self.assertRaises(ValueError):
            self.j.append('operation_finish',dict(status=None,elapsed_ns=None,recovered=True))

    def test_review_before_acceptance_refused(self):
        self.propose()
        record=json.loads((ROOT/'package/fixtures/decision_record.json').read_text())
        with self.assertRaises(ValueError): self.j.review('reviewer',record)

    def test_budget_reserves_finish_slot(self):
        self.bind();self.j.append('operation_start',{'kind':'stage'})
        with patch('wac_offline.scaffold_v1.journal.MAX_EVENTS',6):
            self.j.append('operation_finish',dict(status=self.status(),elapsed_ns=1,recovered=False))
            with self.assertRaises(ValueError): self.j.append('operation_start',{'kind':'inspect'})
        self.assertIsNone(self.j.report()['pending_operation'])

    def test_cli_and_agent_process_exchange(self):
        import subprocess,sys,os
        env=dict(os.environ,PYTHONPATH=str(ROOT/'package'))
        brief=self.j.begin_decision()
        agent=subprocess.run([sys.executable,'-m','wac_offline.scaffold_v1.agent'],
            input=canonical(brief).encode(),capture_output=True,env=env,check=True)
        response=self.root/'response.json'; response.write_bytes(agent.stdout)
        subprocess.run([sys.executable,'-m','wac_offline.scaffold_v1','decision',str(self.j.path),
            '--response',str(response),'--elapsed-ns','7'],capture_output=True,env=env,check=True)
        report=subprocess.run([sys.executable,'-m','wac_offline.scaffold_v1','report',str(self.j.path)],
            capture_output=True,env=env,check=True)
        self.assertEqual(json.loads(report.stdout)['decision'],'PROPOSE')

    def test_concurrent_starts_admit_one(self):
        from concurrent.futures import ThreadPoolExecutor
        def start(_):
            try: Journal(self.j.path).begin_decision(); return True
            except ValueError: return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(start,range(2))),1)
        self.assertEqual(self.j.report()['decision_attempts'],1)

    def test_historical_files_preserved(self):
        manifest=json.loads((ROOT/'provenance/scaffold_preserved.json').read_text())
        self.assertEqual(len(manifest['files']),120)
        for path, expected in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)


if __name__ == '__main__': unittest.main()
