"""Pure S2 transitions and reports. The host owns time, files and declarations."""
from copy import deepcopy
from pathlib import Path

from . import VERSION
from .source import validate, extends
from ..scaffold_v1.journal import SCOPE
from ..scaffold_v1.wire import exact, integer, label

LANES=('decision','review')
MAX_EVENTS=512


def initial(g):
    exact(g,('version','created_ms','decision_budget','review_budget','jobs',*SCOPE))
    if g['version']!=VERSION or any(type(g[k]) is not type(v) or g[k]!=v for k,v in SCOPE.items()):
        raise ValueError('scope/version mismatch')
    integer(g['created_ms'])
    for lane in LANES: integer(g[lane+'_budget'],32)
    if type(g['jobs']) is not list or not 1 <= len(g['jobs']) <= 16:
        raise ValueError('one to sixteen assignments required')
    jobs={}; paths=set()
    for row in g['jobs']:
        exact(row,('path','decision_deadline_ms','review_deadline_ms','source'))
        validate(row['source']); o=row['source']; identifier=o['assignment']['id']
        if identifier in jobs or row['path'] in paths or type(row['path']) is not str or not Path(row['path']).is_absolute():
            raise ValueError('duplicate assignment or invalid path')
        paths.add(row['path'])
        if len(o['history'])!=1 or o['decision']!='NOT_STARTED' or o['transport']!='NOT_STAGED' or o['review'] or o['pending']:
            raise ValueError('only fresh S1 assignments may be admitted')
        for lane in LANES: integer(row[lane+'_deadline_ms'])
        if not g['created_ms'] < row['decision_deadline_ms'] <= row['review_deadline_ms']:
            raise ValueError('invalid deadline order')
        jobs[identifier]=dict(row,error=None,contaminated=False,decision_claim=None,review_claim=None,
                             decision_observed_ms=None,review_observed_ms=None)
    return dict(genesis=deepcopy(g),clock_ms=g['created_ms'],jobs=deepcopy(jobs),
                used={lane:0 for lane in LANES},cursor={lane:None for lane in LANES},claims={})


def unsettled(job):
    o=job['source']
    if job['error'] or job['contaminated'] or o['pending']: return True
    if job['decision_claim'] is None: return False
    return o['decision'] in ('NOT_STARTED','PENDING') or (
        o['decision']=='PROPOSE' and o['transport'] in ('NOT_STAGED','UNRESOLVED'))


def stale(state,job):
    o=job['source']
    return any(other['source']['instance']==o['instance'] and other['source']['accepted_head'] is not None
               and other['source']['accepted_head']!=o['brief_head'] for other in state['jobs'].values())


def eligibility(state,identifier,lane):
    j=state['jobs'][identifier];o=j['source']
    if j['error']: return 'SOURCE_UNAVAILABLE'
    if j['contaminated']: return 'OUT_OF_BAND_ACTIVITY'
    if j[lane+'_claim'] is not None: return 'ALREADY_RESERVED'
    if state['clock_ms'] >= j[lane+'_deadline_ms']: return 'EXPIRED'
    if lane=='decision':
        if stale(state,j): return 'STALE_BRIEF'
        if o['decision']!='NOT_STARTED': return 'NOT_FRESH'
        if any(other_id!=identifier and other['source']['instance']==o['instance'] and unsettled(other)
               for other_id,other in state['jobs'].items()): return 'INSTANCE_HELD'
    else:
        if o['transport']!='ACCEPTED' or o['pending'] or o['review'] is not None: return 'NOT_READY'
    if state['used'][lane] >= state['genesis'][lane+'_budget']: return 'BUDGET_EXHAUSTED'
    return 'ELIGIBLE'


def choose(state,lane):
    field='controller' if lane=='decision' else 'reviewer_controller'
    domains=sorted({j['source']['assignment'][field] for j in state['jobs'].values()})
    cursor=state['cursor'][lane]
    if cursor is not None:
        i=domains.index(cursor)+1; domains=domains[i:]+domains[:i]
    for domain in domains:
        for identifier,j in state['jobs'].items():
            if j['source']['assignment'][field]==domain and eligibility(state,identifier,lane)=='ELIGIBLE':
                return identifier
    return None


def advance(state,kind,data):
    s=deepcopy(state)
    if kind=='clock':
        exact(data,('now_ms',));integer(data['now_ms'])
        if data['now_ms'] < s['clock_ms']: raise ValueError('clock rollback')
        s['clock_ms']=data['now_ms']
    elif kind=='observation':
        exact(data,('id','source'))
        if data['id'] not in s['jobs']: raise ValueError('unknown assignment')
        j=s['jobs'][data['id']];o=data['source']
        if o is None:
            j['error']='SOURCE_UNAVAILABLE'
        else:
            extends(j['source'],o)
            if (j['decision_claim'] is None and o['decision']!='NOT_STARTED') or (
                    j['review_claim'] is None and o['review'] is not None):
                j['contaminated']=True
            j['source']=o;j['error']=None
            if o['decision'] not in ('NOT_STARTED','PENDING') and j['decision_observed_ms'] is None:
                j['decision_observed_ms']=s['clock_ms']
            if o['review'] is not None and j['review_observed_ms'] is None:
                j['review_observed_ms']=s['clock_ms']
    elif kind=='claim':
        exact(data,('request_id','lane','selected','source_head'))
        label(data['request_id']);lane=data['lane']
        if lane not in LANES or data['request_id'] in s['claims']: raise ValueError('invalid or duplicate claim event')
        selected=choose(s,lane)
        if data['selected']!=selected: raise ValueError('nonconforming scheduling choice')
        if selected is None:
            if data['source_head'] is not None: raise ValueError('no selected source')
        else:
            j=s['jobs'][selected]
            if data['source_head']!=j['source']['history'][-1]: raise ValueError('stale reservation source')
            j[lane+'_claim']=data['request_id'];s['used'][lane]+=1
            s['cursor'][lane]=j['source']['assignment']['controller' if lane=='decision' else 'reviewer_controller']
        s['claims'][data['request_id']]=dict(data,reserved_at_ms=s['clock_ms'],authority='NONE',
            execution_enabled=False,scope='HISTORICAL_SCHEDULING_RESERVATION_ONLY')
    else:
        raise ValueError('unknown scheduler event')
    return s


def report(s,head,events):
    rows=[]
    for identifier,j in s['jobs'].items():
        o=j['source']
        rows.append(dict(id=identifier,decision=o['decision'],transport=o['transport'],
            decision_reservation=j['decision_claim'],review_reservation=j['review_claim'],
            decision_eligibility=eligibility(s,identifier,'decision'),
            review_eligibility=eligibility(s,identifier,'review'),
            instance_held=unsettled(j),source_error=j['error'],out_of_band=j['contaminated'],
            source_head=o['history'][-1],review=o['review'],
            decision_observed_late=None if j['decision_observed_ms'] is None else j['decision_observed_ms']>=j['decision_deadline_ms'],
            review_observed_late=None if j['review_observed_ms'] is None else j['review_observed_ms']>=j['review_deadline_ms']))
    return dict(version=VERSION,**SCOPE,clock_ms=s['clock_ms'],journal_head=head,events=events,
        reservations=dict(s['used']),remaining={lane:s['genesis'][lane+'_budget']-s['used'][lane] for lane in LANES},
        jobs=rows,claims=list(s['claims'].values()),host_inspection_credits='NOT_POOLED_OR_MEASURED',
        synthetic_decision_slots=None,source_authenticity=False,policy_fidelity_verified=False,
        authority_observed=False,live_model_calls='NOT_MEASURED_BY_S2')
