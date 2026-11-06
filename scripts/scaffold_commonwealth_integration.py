"""Explicit pinned B1.1/C2 integration; actual loopback, no models or external effects.

Requires C2 installed separately and an exact, clean Commonwealth checkout.
The test host runs here with its own DB; this does NOT demonstrate OS isolation.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'package'))
from wac_offline.scaffold_v1 import ap1, transport
from wac_offline.scaffold_v1.agent import decide
from wac_offline.scaffold_v1.audit import audit
from wac_offline.scaffold_v1.demo import assignment, limits
from wac_offline.scaffold_v1.journal import Journal
from wac_offline.scaffold_v1.wire import canonical


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('commonwealth_checkout',type=Path)
    args=parser.parse_args()
    uc=args.commonwealth_checkout.resolve()
    source=json.loads((ROOT/'provenance/scaffold_sources.json').read_text())
    check(subprocess.check_output(['git','rev-parse','HEAD'],cwd=uc,text=True).strip()==source['commit'],'wrong source commit')
    check(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=uc,text=True).strip(),'dirty source checkout')
    for path, expected in source['files'].items():
        check(hashlib.sha256((uc/path).read_bytes()).hexdigest()==expected,'source digest mismatch')
    import commonwealth_client_v2.store as c2
    import commonwealth_client_v2.wire as c2wire
    import commonwealth_client_v2.transport as c2transport
    for module in (c2,c2wire,c2transport):
        path='client_dist/src/commonwealth_client_v2/'+Path(module.__file__).name
        check(hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()==source['files'][path],'installed C2 differs')
    sys.path.insert(0,str(uc))
    from commonwealth.store import Workshop
    from commonwealth.participant_v1_1.store import Boundary
    from commonwealth.participant_v1.transport import Server, request
    from commonwealth.participant_v1.store import read_credential
    spec=importlib.util.spec_from_file_location('pinned_ap1',uc/'examples/agent_profile_v1/adapter.py')
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)

    @contextmanager
    def host(root):
        workshop=Workshop.create(root/'host.sqlite')
        clock=[1000]
        boundary=Boundary(workshop.path,clock=lambda:clock[0]);boundary.install()
        boundary.issue(root/'credential',ttl=60)
        token=read_credential(root/'credential')
        server=Server(boundary)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01});thread.start()
        try:
            status,task=request(server.url,token);check(status==200,'task fetch')
            yield workshop,boundary,clock,server.url,token,task
        finally:
            server.shutdown();thread.join();server.server_close()

    rows=[]
    with tempfile.TemporaryDirectory(prefix='cortac-s1-b11-') as temporary:
        for case in ('accepted','lost-reply','stage-interrupted','submit-interrupted','stale','expired','outbox-conflict'):
            root=Path(temporary)/case;root.mkdir()
            with host(root) as (workshop,boundary,clock,url,token,task):
                j=Journal.create(root/'journal.sqlite',task,assignment(),limits())
                brief=j.begin_decision()
                check(brief==reference.brief(task,profile=reference.PROFILE_1_1),'AP1 brief mismatch')
                reply=decide(brief)
                check(ap1.interpret(brief,reply)==reference.interpret(brief,reply),'AP1 request mismatch')
                j.finish_decision(canonical(reply).encode(),elapsed_ns=1)
                if case=='stage-interrupted':
                    with patch.object(transport,'_finish',side_effect=RuntimeError('simulated loss after C2 stage')):
                        try: transport.stage(j,root/'outbox.sqlite',url,token)
                        except RuntimeError: pass
                    j=Journal(j.path);transport.recover(j,token)
                    check(j.report()['interrupted_duration_unknown'],'missing interruption')
                else:
                    transport.stage(j,root/'outbox.sqlite',url,token)
                check(boundary.audit()['capabilities'][0]['used']==0,'staging contacted host')
                if case=='stale':
                    # A separate legitimate proposal changes the exact viewed head.
                    other=ap1.interpret(brief,reply);other['request_id']='other-proposal'
                    check(request(url,token,'POST','/proposals',canonical(other).encode())[0]==200,'stale setup')
                if case=='expired': clock[0]=1061
                if case=='outbox-conflict':
                    from contextlib import closing
                    box=c2.Outbox(root/'outbox.sqlite')
                    # Valid C2 state for different bytes is not this assignment's intent.
                    with closing(box.connect()) as db,db:
                        original=json.loads(db.execute('SELECT body FROM intent').fetchone()[0])
                        altered=json.loads(bytes.fromhex(original['raw_hex']))
                        altered['proposal']['purpose']='Different retained purpose'
                        raw=canonical(altered).encode();original['raw_hex']=raw.hex()
                        original['raw_sha256']=hashlib.sha256(raw).hexdigest()
                        db.execute('UPDATE intent SET body=?,digest=?',(canonical(original),c2.fingerprint(original)))
                    try: transport.operate(j,token,'submit')
                    except ValueError: pass
                    else: raise ValueError('conflicting outbox accepted')
                    check(boundary.audit()['capabilities'][0]['used']==0,'conflict sent')
                elif case=='lost-reply':
                    actual=c2.request
                    def lose(*args,**kwargs):
                        status,payload=actual(*args,**kwargs)
                        check(status==200,'lost reply setup')
                        return 0,{}
                    with patch.object(c2,'request',side_effect=lose): transport.operate(j,token,'submit')
                    check(j.report()['transport']=='UNRESOLVED','unknown outcome erased')
                    j=Journal(j.path);transport.operate(j,token,'resolve')
                    check(j.report()['transport']=='UNRESOLVED','lookup promoted to binding receipt')
                    transport.operate(j,token,'submit')
                elif case=='submit-interrupted':
                    with patch.object(transport,'_finish',side_effect=RuntimeError('simulated interruption')):
                        try: transport.operate(j,token,'submit')
                        except RuntimeError: pass
                    j=Journal(j.path);transport.recover(j,token)
                else:
                    transport.operate(j,token,'submit')
                report=j.report();audit(j.path,report)
                server_audit=boundary.audit()
                if case in ('expired','outbox-conflict'):
                    check(report['transport']=='UNRESOLVED','unresolved mislabeled')
                elif case=='stale':
                    check(report['host_receipt']['receipt']['disposition']=='STALE_VIEW','stale receipt lost')
                else:
                    check(report['host_receipt']['receipt']['disposition']=='ACCEPTED','acceptance missing')
                    check(server_audit['capabilities'][0]['used']==1,'duplicate server attempt')
                    check(server_audit['events']==2,'unexpected host event')
                    record=json.loads((ROOT/'package/fixtures/decision_record.json').read_text())
                    j.review('reviewer',record)
                    check(j.report()['host_authority']=='NOT_OBSERVED','advisory promoted')
                    audit(j.path,j.report())
                rows.append(dict(case=case,transport=report['transport'],
                    disposition=report['host_receipt']['receipt']['disposition'] if report['host_receipt'] else None,
                    host_events=server_audit['events'],server_attempts=server_audit['capabilities'][0]['used']))
    print(json.dumps(dict(schema='cortac.scaffold.commonwealth-integration.v1',rows=rows,
        all_checks_passed=True,commonwealth_commit=source['commit'],actual_loopback=True,
        authority='NONE',execution_enabled=False,host_isolation='NOT_TESTED',
        independent_operators=False,real_model_calls=0,scored_study=False),indent=2))


if __name__=='__main__': main()
