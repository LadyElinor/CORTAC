"""S2 hand cases and adverse histories, not a governance efficacy study."""
from contextlib import closing
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from wac_offline.scheduler_v1 import engine,source
from wac_offline.scheduler_v1.store import Scheduler
from wac_offline.scheduler_v1.demo import run
from wac_offline.scheduler_v1.audit import audit
from wac_offline.scaffold_v1 import ap1
from wac_offline.scaffold_v1.agent import decide
from wac_offline.scaffold_v1.demo import task,assignment,limits
from wac_offline.scaffold_v1.journal import Journal
from wac_offline.scaffold_v1.wire import canonical,digest

ROOT=Path(__file__).resolve().parents[2]


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.clock=[1000];self.children={}

    def child(self,identifier,controller,instance=None):
        t=task();t['instance']=instance or f'{len(self.children)+1:032x}'
        a=assignment();a.update(id=identifier,agent=identifier,controller=controller,
            reviewer='review-'+identifier,reviewer_controller='review-'+controller)
        j=Journal.create(self.root/(identifier+'.sqlite'),t,a,limits());self.children[identifier]=j
        return j

    def create(self,decisions=8,reviews=2):
        return Scheduler.create(self.root/'schedule.sqlite',dict(decision_budget=decisions,review_budget=reviews,
            jobs=[dict(path=str(j.path),decision_deadline_ms=2000,review_deadline_ms=3000) for j in self.children.values()]),
            clock=lambda:self.clock[0])

    def finish(self,identifier,choice='decline'):
        j=self.children[identifier];b=j.begin_decision()
        response=decide(b) if choice=='propose' else dict(profile=b['profile'],brief_id=b['brief_id'],choice=choice,reason='Fixture')
        j.finish_decision(canonical(response).encode(),elapsed_ns=2)

    def accept(self,identifier):
        self.finish(identifier,'propose');j=self.children[identifier];s=j.state()
        req=ap1.interpret(s['genesis']['brief'],s['decision']['reply'])
        j.append('intent_bound',dict(outbox=str(self.root/(identifier+'-outbox')),url='http://127.0.0.1:1234',
            credential_digest='9'*64,instance=s['genesis']['brief']['instance'],request_id=req['request_id'],raw_sha256=digest(req)))
        status=dict(version='client-only-2.0.0',state='UNRESOLVED',request_id=req['request_id'],instance=s['genesis']['brief']['instance'],
            operations_started=0,operations_observed=0,latest_observation=None,recorded=None,external_authority='NONE',assurance='Synthetic test observation')
        j.append('operation_start',dict(kind='stage'))
        j.append('operation_finish',dict(status=status,elapsed_ns=1,recovered=False))
        j.append('operation_start',dict(kind='submit'))
        status.update(state='RECORDED',operations_started=1,operations_observed=1,latest_observation='RECORDED',
            recorded=dict(http_status=200,receipt=dict(protocol=ap1.PROTOCOL,disposition='ACCEPTED',external_authority='NONE',
                request_id=req['request_id'],instance=status['instance'],event_seq=2,event_hash='3'*64,proposal_id='propose-2',permits_execution=False)))
        j.append('operation_finish',dict(status=status,elapsed_ns=1,recovered=False))

    def test_hand_rotation(self):
        self.assertEqual(run()['selected'],['alpha-1','beta-1','alpha-2'])

    def test_aliases_do_not_add_domain_turns(self):
        for name,c in [('a1','a'),('a2','a'),('a3','a'),('b1','b'),('b2','b')]:self.child(name,c)
        s=self.create();order=[]
        for n in range(5):
            pick=s.claim('decision',str(n))['selected'];order.append(pick);self.finish(pick)
        self.assertEqual(order,['a1','b1','a2','b2','a3'])

    def test_review_reserve_after_decision_exhaustion(self):
        self.child('a','a');self.child('b','b');s=self.create(decisions=1,reviews=1)
        self.assertEqual(s.claim('decision','d1')['selected'],'a');self.accept('a')
        self.assertIsNone(s.claim('decision','d2')['selected'])
        self.assertEqual(s.claim('review','r1')['selected'],'a')
        record=json.loads((ROOT/'package/fixtures/decision_record.json').read_text())
        record['protected_limit_assessments'][0]['status']='UNKNOWN'
        self.children['a'].review('review-a',record);s.poll()
        report=s.report();self.assertEqual(report['remaining'],dict(decision=0,review=0))
        self.assertFalse(report['jobs'][0]['review']['supplied_assessments_pass'])
        self.assertFalse(report['execution_enabled'])

    def test_same_id_is_idempotent_and_lane_conflict_refused(self):
        self.child('a','a');self.child('b','b');s=self.create()
        first=s.claim('decision','same');self.assertEqual(s.claim('decision','same'),first)
        self.assertEqual(s.reservation('same'),first)
        with self.assertRaises(ValueError):s.claim('review','same')
        self.assertEqual(s.report()['reservations']['decision'],1)

    def test_concurrent_same_id_reserves_once(self):
        self.child('a','a');self.child('b','b');s=self.create()
        def claim(_):return Scheduler(s.path,clock=lambda:1000).claim('decision','same')
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,range(2)))
        self.assertEqual(results[0],results[1]);self.assertEqual(s.report()['reservations']['decision'],1)

    def test_shared_budget_serializes_different_claims(self):
        self.child('a','a');self.child('b','b');s=self.create(decisions=1)
        def claim(n):return Scheduler(s.path,clock=lambda:1000).claim('decision',str(n))['selected']
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,range(2)))
        self.assertEqual(sum(v is not None for v in results),1)

    def test_passive_expiry_and_rollback(self):
        self.child('a','a');s=self.create();self.clock[0]=2000
        self.assertIsNone(s.claim('decision','late')['selected'])
        self.assertEqual(s.report()['jobs'][0]['decision_eligibility'],'EXPIRED')
        self.clock[0]=1999
        with self.assertRaises(ValueError):s.claim('decision','rollback')
        self.assertEqual(s.report()['clock_ms'],2000)

    def test_started_work_not_reissued_after_deadline(self):
        self.child('a','a');s=self.create();s.claim('decision','d')
        self.clock[0]=2500;s.poll()
        self.assertTrue(s.report()['jobs'][0]['instance_held'])
        self.finish('a');s.poll()
        self.assertTrue(s.report()['jobs'][0]['decision_observed_late'])
        self.assertEqual(s.report()['reservations']['decision'],1)

    def test_unsubmitted_proposal_blocks_same_instance_only(self):
        self.child('a','a','1'*32);self.child('b','b','1'*32);self.child('c','c','2'*32)
        s=self.create();self.assertEqual(s.claim('decision','one')['selected'],'a');self.finish('a','propose')
        self.assertEqual(s.claim('decision','two')['selected'],'c')
        self.assertEqual(s.report()['jobs'][1]['decision_eligibility'],'INSTANCE_HELD')

    def test_pending_transport_blocks_even_with_cached_acceptance(self):
        self.child('a','a','1'*32);self.child('b','b','1'*32);s=self.create()
        s.claim('decision','one');self.accept('a')
        self.children['a'].append('operation_start',dict(kind='inspect'));s.poll()
        self.assertTrue(s.report()['jobs'][0]['instance_held'])
        self.assertIsNone(s.claim('review','r')['selected'])

    def test_accepted_head_invalidates_queued_brief(self):
        self.child('a','a','1'*32);self.child('b','b','1'*32);s=self.create()
        s.claim('decision','one');self.accept('a');s.poll()
        self.assertEqual(s.report()['jobs'][1]['decision_eligibility'],'STALE_BRIEF')
        self.assertIsNone(s.claim('decision','two')['selected'])

    def test_missing_source_does_not_block_other_instances(self):
        a=self.child('a','a');self.child('b','b');s=self.create()
        a.path.rename(self.root/'retained.sqlite')
        self.assertEqual(s.claim('decision','d')['selected'],'b')
        self.assertEqual(s.report()['jobs'][0]['source_error'],'SOURCE_UNAVAILABLE')

    def test_out_of_band_activity_stays_visible(self):
        self.child('a','a');s=self.create();self.finish('a');s.poll()
        self.assertTrue(s.report()['jobs'][0]['out_of_band'])
        self.assertIsNone(s.claim('decision','d')['selected'])

    def test_source_rewrite_with_valid_hashes_refused(self):
        j=self.child('a','a');s=self.create();s.claim('decision','d');self.finish('a');s.poll()
        with closing(sqlite3.connect(j.path)) as db,db:
            rows=db.execute('SELECT * FROM events ORDER BY seq').fetchall();head='0'*64
            for n,k,raw,_,_ in rows:
                body=json.loads(raw)
                if k=='decision_finish':body['reply']['reason']='Rewritten after observation'
                h=digest(dict(seq=n,kind=k,body=body,previous=head))
                db.execute('UPDATE events SET body=?,previous=?,hash=? WHERE seq=?',(canonical(body),head,h,n));head=h
        s.poll();self.assertEqual(s.report()['jobs'][0]['source_error'],'SOURCE_UNAVAILABLE')

    def test_duplicate_admission_and_nonfresh_source(self):
        j=self.child('a','a');s=self.create()
        manifest=dict(decision_budget=1,review_budget=1,jobs=[dict(path=str(j.path),decision_deadline_ms=2000,review_deadline_ms=3000)]*2)
        with self.assertRaises(ValueError):Scheduler.create(self.root/'duplicate',manifest,clock=lambda:1000)
        self.finish('a')
        manifest['jobs']=manifest['jobs'][:1]
        with self.assertRaises(ValueError):Scheduler.create(self.root/'old',manifest,clock=lambda:1000)

    def test_restart_preserves_reservations(self):
        self.child('a','a');s=self.create();r=s.claim('decision','d')
        restarted=Scheduler(s.path,clock=lambda:1100)
        self.assertEqual(restarted.reservation('d'),r)
        self.assertEqual(restarted.claim('decision','d'),r)

    def test_clock_floor_persists_before_source_error(self):
        j=self.child('a','a');s=self.create();j.path.unlink();self.clock[0]=1500;s.poll()
        self.clock[0]=1400
        with self.assertRaises(ValueError):s.poll()
        self.assertEqual(s.report()['clock_ms'],1500)

    def test_forged_selection_and_scope_refused(self):
        self.child('a','a');self.child('b','b');s=self.create()
        with self.assertRaises(ValueError):s._append('claim',dict(request_id='fake',lane='decision',selected='b',source_head='0'*64))
        g=deepcopy(s._snapshot()[0]['genesis']);g['execution_enabled']=0
        with self.assertRaises(ValueError):engine.initial(g)

    def test_review_expiry_does_not_erase_acceptance(self):
        self.child('a','a');s=self.create();s.claim('decision','d');self.accept('a');self.clock[0]=3000
        self.assertIsNone(s.claim('review','r')['selected'])
        row=s.report()['jobs'][0];self.assertEqual(row['transport'],'ACCEPTED')
        self.assertEqual(row['review_eligibility'],'EXPIRED');self.assertIsNone(row['review'])

    def test_source_projection_same_head_cannot_change(self):
        j=self.child('a','a');old=source.capture(j.path);new=deepcopy(old);new['decision']='DECLINE'
        with self.assertRaises(ValueError):source.extends(old,new)

    def test_scheduler_never_changes_child_bytes(self):
        j=self.child('a','a');original=j.path.read_bytes();s=self.create();s.claim('decision','d');s.poll();s.report()
        self.assertEqual(j.path.read_bytes(),original)

    def test_deadline_rechecked_after_source_io(self):
        from unittest.mock import patch
        self.child('a','a');s=self.create();original=source.capture
        def slow(path):
            result=original(path);self.clock[0]=2000;return result
        with patch.object(source,'capture',side_effect=slow):
            self.assertIsNone(s.claim('decision','d')['selected'])
        self.assertEqual(s.report()['clock_ms'],2000)

    def test_second_clock_floor_survives_request_conflict(self):
        from unittest.mock import patch
        self.child('a','a');s=self.create();s.claim('decision','d');original=source.capture
        def slow(path):
            result=original(path);self.clock[0]=1800;return result
        with patch.object(source,'capture',side_effect=slow):
            with self.assertRaises(ValueError):s.claim('review','d')
        self.assertEqual(s.report()['clock_ms'],1800)
        self.clock[0]=1700
        with self.assertRaises(ValueError):s.poll()

    def test_slow_observation_reports_late_without_claiming_finish_time(self):
        from unittest.mock import patch
        self.child('a','a');s=self.create();s.claim('decision','d');self.finish('a')
        original=source.capture
        def slow(path):
            result=original(path);self.clock[0]=2001;return result
        with patch.object(source,'capture',side_effect=slow):s.poll()
        self.assertTrue(s.report()['jobs'][0]['decision_observed_late'])

    def test_unreserved_review_is_not_silently_adopted(self):
        self.child('a','a');s=self.create();s.claim('decision','d');self.accept('a')
        record=json.loads((ROOT/'package/fixtures/decision_record.json').read_text())
        self.children['a'].review('review-a',record);s.poll()
        self.assertTrue(s.report()['jobs'][0]['out_of_band'])
        self.assertIsNone(s.claim('review','r')['selected'])

    def test_independent_reservation_recount(self):
        self.child('a','a');s=self.create();s.claim('decision','d');report=s.report()
        self.assertTrue(audit(s.path,report)['verified'])
        report['remaining']['review']+=1
        with self.assertRaises(ValueError):audit(s.path,report)

    def test_repaired_hash_scheduler_choice_is_still_refused(self):
        self.child('a','a');self.child('b','b');s=self.create();s.claim('decision','d')
        with closing(sqlite3.connect(s.path)) as db,db:
            n,k,raw,previous,_=db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            data=json.loads(raw);data['selected']='b';data['source_head']=source.capture(self.children['b'].path)['history'][-1]
            h=digest(dict(seq=n,kind=k,body=data,previous=previous))
            db.execute('UPDATE events SET body=?,hash=? WHERE seq=?',(canonical(data),h,n))
        with self.assertRaises(ValueError):s.report()

    def test_preservation(self):
        m=json.loads((ROOT/'provenance/scheduler_preserved.json').read_text())
        for path,h in m['files'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),h,path)


if __name__=='__main__':unittest.main()
