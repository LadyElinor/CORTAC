"""Scripted mechanism simulation; standard library only; no LLMs or real effects."""
import argparse, csv, hashlib, json, time
from pathlib import Path
from collections import defaultdict
FAMILIES=['benign','shared_false','conflicted_review','reviewer_shortage','review_withdrawal','target_drift','owner_revoked']
ARMS=['minimal','full','centralized_full','full_no_control_exclusion','full_no_continuity','full_no_classification','full_no_audit','full_single_decider']
RECOVERY={'conflicted_review','reviewer_shortage','review_withdrawal','target_drift'}
def uniform(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str,parts)).encode()).digest()[:8],'big')/2**64

def environment(seed,family):
    truth=100+int(uniform(seed,family,'truth')*900)
    sources=[{'origin':'alpha','value':truth},{'origin':'beta','value':truth}]
    if family=='shared_false': sources=[{'origin':'shared','value':truth+1}]*2+[{'origin':'gamma','value':truth}]
    return dict(seed=seed,family=family,truth=truth,sources=sources,target='b' if family=='target_drift' else 'a',owner_allowed=family!='owner_revoked',initial=truth+1 if family in RECOVERY else None)

def assess(sources):
    vals={r['value'] for r in sources}
    origins={r['origin'] for r in sources}
    return (len(vals)==1 and len(origins)>=2, next(iter(vals)) if len(vals)==1 else None)

def episode(env,arm,budget,p,correlation):
    # Policies receive source records; oracle truth is used only by final judge below.
    family=env['family']; full=arm!='minimal'; units=0; trace=[]; state=env['initial']; effects=[]
    status='pending'; attempts=0; classification=0; conflicted=0; audit_detected=False
    sufficient,observed=assess(env['sources'])
    fault=lambda label: uniform(env['seed'],family,'common' if correlation else label)<p
    def spend(action,n=1,**data):
        nonlocal units,status
        if units+n>budget:
            status='timeout'; trace.append(dict(tick=units,action='budget_exhausted',wanted=action,requested_units=n)); return False
        units+=n; trace.append(dict(tick=units,action=action,cost=n,**data)); return True
    def flow():
        nonlocal status,state,attempts,classification,conflicted,audit_detected
        for action in ['intake','evidence','norms']:
            if not spend(action): return
        if not env['owner_allowed']:
            status='permission_denied'; return
        # Proposal is derived only from available observations, never evaluator truth.
        candidate=observed if sufficient else env['sources'][0]['value']
        if fault('seat0'): candidate+=1
        if full and not spend('routing'): return
        seats=4 if full and arm!='full_single_decider' else 1
        votes=[]
        for i in range(seats):
            if not spend('decision_check',seat=i): return
            votes.append(bool(sufficient and candidate==observed)^fault('seat'+str(i)))
        trace.append(dict(tick=units,action='decision',votes=votes,candidate=candidate))
        if sum(votes)<(3 if seats==4 else 1): status='abstain'; return
        if family in RECOVERY:
            if not spend('review_roster'): return
            candidates=[{'id':i,'conflicted':family=='conflicted_review' and i==0} for i in range(4)]
            if family=='reviewer_shortage': candidates=candidates[:2]
            if arm!='full_no_control_exclusion': candidates=[c for c in candidates if not c['conflicted']]
            required=3 if full else 1
            if len(candidates)<required or (family=='review_withdrawal' and arm=='full_no_continuity'):
                status='review_unavailable'; return
            selected=candidates[:required]; conflicted=int(any(c['conflicted'] for c in selected))
            review_votes=[]
            for c in selected:
                if not spend('appeal_check',reviewer=c['id'],conflicted=c['conflicted']): return
                review_votes.append(bool(sufficient and candidate==observed)^fault('review'+str(c['id'])))
            if sum(review_votes)<(2 if full else 1): status='abstain'; return
        if arm!='full_no_classification':
            if not spend('classification',target=env['target']): return
        elif env['target']=='b': classification=1
        attempts+=1
        if not spend('gateway',target=env['target'],allowed=env['owner_allowed']): return
        if not env['owner_allowed']: status='blocked'; return
        if not spend('commit',value=candidate): return
        state=candidate; effects.append(candidate); status='completed'
        if arm!='full_no_audit':
            if not spend('audit'): return
            wrong=bool(sufficient and state!=observed)^fault('audit')
            audit_detected=wrong
            if wrong and sufficient:
                if not spend('repair_gateway'): return
                if not spend('repair_commit',value=observed): return
                state=observed; effects.append(observed)
    flow()
    # Independent state-based judge, no actor-reported success is accepted.
    justified=family!='shared_false' and env['owner_allowed']
    correct=state==env['truth']
    return dict(seed=env['seed'],family=family,arm=arm,budget=budget,fault_probability=p,correlation=correlation,status=status,units=units,completion_tick=next((x['tick'] for x in trace if x['action'] in {'commit','repair_commit'} and x.get('value')==env['truth']),None) if justified and correct else None,episode_end_tick=units,final_state=state,final_wrong=int(state is not None and not correct),wrong_effect=int(any(v!=env['truth'] for v in effects)),unauthorized_attempts=attempts if not env['owner_allowed'] else 0,unauthorized_effects=len(effects) if not env['owner_allowed'] else 0,unjustified_effect=int(family=='shared_false' and bool(effects)),classification_violations=classification,conflicted_review=conflicted,completed=int(justified and correct),eligible_completion=int(justified),recovery_success=int(family in RECOVERY and correct),recovery_eligible=int(family in RECOVERY),abstention=int(status=='abstain'),timeout=int(status=='timeout'),review_unavailable=int(status=='review_unavailable'),complaint_preserved=True,audit_detected=audit_detected,trace=trace)

METRICS=['completed','eligible_completion','final_wrong','wrong_effect','unauthorized_attempts','unauthorized_effects','unjustified_effect','classification_violations','conflicted_review','recovery_success','recovery_eligible','abstention','timeout','review_unavailable','units']
def summarize(rows,keys):
    groups=defaultdict(list)
    for r in rows: groups[tuple(r[k] for k in keys)].append(r)
    out=[]
    for key,rs in sorted(groups.items()):
        d=dict(zip(keys,key));d['n']=len(rs)
        for m in METRICS:d[m+'_mean']=sum(r[m] for r in rs)/len(rs)
        d['completion_rate_eligible']=sum(r['completed'] for r in rs)/max(1,sum(r['eligible_completion'] for r in rs))
        d['recovery_rate_eligible']=sum(r['recovery_success'] for r in rs)/max(1,sum(r['recovery_eligible'] for r in rs))
        out.append(d)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='results');args=ap.parse_args()
    root=Path(__file__).resolve().parent
    lock=json.loads((root/'freeze.json').read_text())
    for name,digest in lock['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, f'Frozen file modified: {name}'
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter(); cpu=time.process_time(); rows=[]
    for family in FAMILIES:
        for seed in range(50):
            env=environment(seed,family)
            for budget in [12,30]:
                for p in [0,.2]:
                    for corr in [0,1]:
                        for arm in ARMS: rows.append(episode(env,arm,budget,p,corr))
    with (out/'raw.jsonl').open('w') as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True)+'\n')
    for filename,keys in [('aggregate',['arm']),('stratified',['family','budget','fault_probability','correlation','arm'])]:
        data=summarize(rows,keys)
        (out/(filename+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        with (out/(filename+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    matched=defaultdict(dict)
    for r in rows:matched[tuple(r[k] for k in ['family','seed','budget','fault_probability','correlation'])][r['arm']]=r
    pairs=[]
    for key,group in matched.items():
        a,b=group['full'],group['centralized_full']
        assert {k:v for k,v in a.items() if k!='arm'}=={k:v for k,v in b.items() if k!='arm'}
        d=dict(zip(['family','seed','budget','fault_probability','correlation'],key))
        d.update({m:a[m]-group['minimal'][m] for m in METRICS}); pairs.append(d)
    (out/'paired_full_minus_minimal.json').write_text(json.dumps(pairs,indent=2)+'\n')
    assert all(r['units']<=r['budget'] and r['unauthorized_effects']==0 for r in rows)
    assert all(not r['unjustified_effect'] for r in rows if r['fault_probability']==0)
    assert all(r['completed'] for r in rows if r['family']=='benign' and r['budget']==30 and r['fault_probability']==0)
    (out/'runtime.json').write_text(json.dumps(dict(episodes=len(rows),paired_environments=len(matched),python_wall_seconds=time.perf_counter()-start,python_cpu_seconds=time.process_time()-cpu,model_calls=0,model_tokens=0,scope='scripted_python_simulation_not_agent_latency',invariants_passed=True),indent=2)+'\n')
    print(json.dumps(json.loads((out/'runtime.json').read_text()),indent=2))
if __name__=='__main__':main()
