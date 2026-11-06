"""S2 conformance with real pinned loopback submissions; no execution authority."""
from contextlib import ExitStack,contextmanager
import json
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'package'))


def check(value,label):
    if not value:raise ValueError(label)


def main():
    # Reuse the explicit S1 integration's source/version checks and seven cases.
    import scaffold_commonwealth_integration as s1_check
    from contextlib import redirect_stdout
    import io
    with redirect_stdout(io.StringIO()) as log:s1_check.main()
    prior=json.loads(log.getvalue());check(prior['all_checks_passed'],'S1 prerequisites')
    from commonwealth.store import Workshop
    from commonwealth.participant_v1_1.store import Boundary
    from commonwealth.participant_v1.transport import Server,request
    from commonwealth.participant_v1.store import read_credential
    import commonwealth_client_v2.store as c2
    from wac_offline.scaffold_v1 import transport
    from wac_offline.scaffold_v1.journal import Journal
    from wac_offline.scaffold_v1.demo import assignment,limits
    from wac_offline.scaffold_v1.agent import decide
    from wac_offline.scaffold_v1.wire import canonical
    from wac_offline.scheduler_v1.store import Scheduler
    from wac_offline.scheduler_v1.audit import audit

    @contextmanager
    def host(root):
        root.mkdir();workshop=Workshop.create(root/'host.sqlite')
        boundary=Boundary(workshop.path,clock=lambda:1000);boundary.install();boundary.issue(root/'credential',ttl=60)
        token=read_credential(root/'credential');server=Server(boundary)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01});thread.start()
        try:
            code,task=request(server.url,token);check(code==200,'task')
            yield boundary,server.url,token,task
        finally:server.shutdown();thread.join();server.server_close()

    with tempfile.TemporaryDirectory(prefix='cortac-s2-live-') as tmp,ExitStack() as stack:
        root=Path(tmp);hosts={}
        for name in ('host-a','host-b'):hosts[name]=stack.enter_context(host(root/name))
        children={};jobs=[]
        for name,controller,host_id in (('a1','alpha','host-a'),('a2','alpha','host-a'),('b1','beta','host-b')):
            boundary,url,token,task=hosts[host_id]
            a=assignment();a.update(id=name,agent=name,controller=controller,reviewer='review-'+name,reviewer_controller='review-'+controller)
            j=Journal.create(root/(name+'.sqlite'),task,a,limits());children[name]=(j,host_id)
            jobs.append(dict(path=str(j.path),decision_deadline_ms=2000,review_deadline_ms=3000))
        scheduler=Scheduler.create(root/'scheduler.sqlite',dict(jobs=jobs,decision_budget=2,review_budget=1),clock=lambda:1000)
        check(scheduler.claim('decision','d1')['selected']=='a1','first reservation')
        j,host_id=children['a1'];boundary,url,token,_=hosts[host_id]
        b=j.begin_decision();j.finish_decision(canonical(decide(b)).encode(),elapsed_ns=1)
        transport.stage(j,root/'a1-outbox.sqlite',url,token)
        real_request=c2.request
        def drop(*args,**kwargs):
            code,body=real_request(*args,**kwargs);check(code==200,'committed lost reply');return 0,{}
        with patch.object(c2,'request',side_effect=drop):transport.operate(j,token,'submit')
        scheduler.poll();check(scheduler.report()['jobs'][1]['decision_eligibility']=='INSTANCE_HELD','unknown outcome not held')
        check(scheduler.claim('decision','d2')['selected']=='b1','unrelated instance must progress')
        bjob,_=children['b1'];b=bjob.begin_decision();bjob.finish_decision(canonical(dict(profile=b['profile'],brief_id=b['brief_id'],choice='decline',reason='Conformance decline')).encode())
        transport.operate(j,token,'resolve');scheduler.poll()
        check(scheduler.report()['jobs'][0]['instance_held'],'lookup cannot clear uncertainty')
        transport.operate(j,token,'submit');scheduler.poll()
        check(scheduler.report()['jobs'][1]['decision_eligibility']=='STALE_BRIEF','accepted head must stale queued brief')
        check(scheduler.claim('decision','d3')['selected'] is None,'ordinary budget exhausted')
        check(scheduler.claim('review','r1')['selected']=='a1','review reserve unavailable')
        j.review('review-a1',json.loads((ROOT/'package/fixtures/decision_record.json').read_text()))
        scheduler.poll();result=scheduler.report();audit(scheduler.path,result)
        check(result['remaining']==dict(decision=0,review=0),'budget accounting')
        check(boundary.audit()['capabilities'][0]['used']==1,'lost reply duplicated submission')
        check(boundary.audit()['events']==2,'unexpected workshop mutation')
        check(hosts['host-b'][0].audit()['events']==1,'decline changed host')
    print(json.dumps(dict(schema='cortac.scheduler.commonwealth-integration.v1',all_checks_passed=True,
        reservations=result['reservations'],queued_same_instance='STALE_BRIEF',
        lost_reply_server_attempts=1,advisory_review_preserved=True,actual_loopback=True,
        authority='NONE',execution_enabled=False,host_isolation='NOT_TESTED',
        independent_operators=False,real_model_calls=0,scored_study=False,
        commonwealth_commit=prior['commonwealth_commit']),indent=2))


if __name__=='__main__':main()
