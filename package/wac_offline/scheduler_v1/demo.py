"""Hand-computable three-assignment rotation; exposed conformance only."""
from pathlib import Path
import tempfile
from .store import Scheduler
from ..scaffold_v1.demo import task,assignment,limits
from ..scaffold_v1.journal import Journal
from ..scaffold_v1.wire import canonical


def run():
    with tempfile.TemporaryDirectory(prefix='cortac-s2-') as directory:
        root=Path(directory);jobs=[];children={};now=[1000]
        for i,(identifier,controller) in enumerate((('alpha-1','alpha'),('alpha-2','alpha'),('beta-1','beta')),1):
            t=task();t['instance']=f'{i:032x}'
            a=assignment();a.update(id=identifier,agent=identifier,controller=controller,
                reviewer='review-'+identifier,reviewer_controller='review-'+controller)
            child=Journal.create(root/(identifier+'.sqlite'),t,a,limits());children[identifier]=child
            jobs.append(dict(path=str(child.path),decision_deadline_ms=2000,review_deadline_ms=3000))
        coordinator=Scheduler.create(root/'scheduler.sqlite',dict(jobs=jobs,decision_budget=3,review_budget=1),clock=lambda:now[0])
        selected=[]
        for n in range(3):
            chosen=coordinator.claim('decision','dispatch-'+str(n))['selected'];selected.append(chosen)
            child=children[chosen];b=child.begin_decision()
            child.finish_decision(canonical(dict(profile=b['profile'],brief_id=b['brief_id'],choice='decline',
                reason='Conformance decline; no host call.')).encode(),elapsed_ns=1)
        coordinator.poll()
        if selected!=['alpha-1','beta-1','alpha-2']: raise ValueError('rotation differs from hand calculation')
        result=coordinator.report()
        return dict(schema='cortac.scheduler.demo.v1',selected=selected,reservations=result['reservations'],
            remaining=result['remaining'],authority='NONE',execution_enabled=False,network_calls=0,
            real_model_calls=0,scored_study=False,scope='EXPOSED_CONFORMANCE_ONLY')


if __name__=='__main__': print(canonical(run()))
