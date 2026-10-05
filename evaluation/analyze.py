"""Strict paired descriptive bootstrap for fabricated analysis smoke rows only."""
import argparse
from collections import Counter
import random
from pathlib import Path
from common import ROOT, ARMS, FAMILIES, ABLATIONS, ANALYSIS_SEED, seed_for, read_jsonl, read, file_digest, write
from metrics import METRICS, validate_row
from readiness import assess


def quantile(xs,q):
    if not xs: return None
    s=sorted(xs); p=(len(s)-1)*q; lo=int(p); hi=min(lo+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(p-lo)


def paired_bootstrap(differences, seed=ANALYSIS_SEED, resamples=10000):
    if not differences: return {'difference':None,'interval_95':[None,None],'paired_n':0}
    rng=random.Random(seed); n=len(differences)
    samples=[sum(differences[rng.randrange(n)] for _ in range(n))/n for _ in range(resamples)]
    return {'difference':sum(differences)/n,'interval_95':[quantile(samples,.025),quantile(samples,.975)],'paired_n':n}


def validate_rows(rows, schedule):
    expected={s['slot_id']:s for s in schedule}; got={}
    if not schedule or len(expected) != len(schedule): raise ValueError('empty or duplicate schedule slots')
    for row in rows:
        validate_row(row)
        if row['slot_id'] in got: raise ValueError('duplicate result slot')
        if row['slot_id'] not in expected: raise ValueError('unexpected result slot')
        for field in ['task_id','family','split','arm','paired_index','model_seed_proposal','task_input_sha256']:
            if row[field]!=expected[row['slot_id']][field]: raise ValueError('result/schedule mismatch: '+field)
        got[row['slot_id']]=row
    if set(got)!=set(expected): raise ValueError('missing result slots; no complete-case arm dropping allowed')
    return got


def analyze(rows_path=ROOT/'smoke/fabricated_results.jsonl', schedule_path=ROOT/'fixtures/evaluator_only/analysis_smoke_schedule.jsonl', mode='synthetic', root=ROOT):
    gate=assess(root)
    if gate['integrity_failures']: raise ValueError('fixture/manifest integrity failed')
    if mode != 'synthetic': raise ValueError('SOURCE_GATED_NO_SCORED_RUN: scored study runner and verifier are not implemented')
    frozen_schedule=Path(root)/'fixtures/evaluator_only/analysis_smoke_schedule.jsonl'
    if file_digest(schedule_path) != file_digest(frozen_schedule): raise ValueError('schedule is not the complete pinned analysis_smoke schedule')
    rows=read_jsonl(rows_path); schedule=read_jsonl(schedule_path)
    if any(s['split']!='analysis_smoke' for s in schedule): raise ValueError('only analysis_smoke schedule accepted; no 620-trial claim')
    index=validate_rows(rows,schedule)
    comparisons=[]
    for family in FAMILIES:
        contrasts=[(ARMS[2],ARMS[0]),(ARMS[2],ARMS[1]),(ARMS[1],ARMS[0])]
        contrasts += [('ablate_'+name,ARMS[2]) for name,fam in ABLATIONS.items() if fam==family]
        case_ids=sorted({s['task_id'] for s in schedule if s['family']==family})
        for first,second in contrasts:
            entry={'family':family,'first_arm':first,'second_arm':second,'assigned_paired_n':len(case_ids),'metrics':{}}
            for metric in METRICS:
                pairs=[(index[case+':'+first], index[case+':'+second]) for case in case_ids]
                diffs=[a['metrics'][metric]-b['metrics'][metric] for a,b in pairs if a['metrics'][metric] is not None and b['metrics'][metric] is not None]
                result=paired_bootstrap(diffs,seed_for('analysis',ANALYSIS_SEED,family,first,second,metric),10000)
                result['paired_missing_n']=len(case_ids)-len(diffs)
                result['missing_reasons']=dict(Counter(a['metric_missing_reasons'].get(metric,'observed')+' / '+b['metric_missing_reasons'].get(metric,'observed') for a,b in pairs if a['metrics'][metric] is None or b['metrics'][metric] is None))
                result['interpretation']='marginal descriptive interval on fabricated values; no scientific performance interpretation'
                entry['metrics'][metric]=result
            comparisons.append(entry)
    arm_summaries=[]
    for family in FAMILIES:
        for arm in sorted({r['arm'] for r in rows if r['family']==family}):
            group=[r for r in rows if r['family']==family and r['arm']==arm]
            summary={'family':family,'arm':arm,'assigned_n':len(group),'terminal_status_counts':dict(Counter(r['terminal_status'] for r in group)),'useful_opportunities':sum(r['useful_opportunity'] for r in group),'unresolved_effect_rows':sum(r['unresolved_effect'] for r in group),'corrections_requested':sum(r['correction_requested'] for r in group),'corrections_completed':sum(r['correction_completed'] for r in group),'metrics':{}}
            for metric,spec in METRICS.items():
                values=[r['metrics'][metric] for r in group if r['metrics'][metric] is not None]
                summary['metrics'][metric]={'observed_n':len(values),'missing_n':len(group)-len(values),'sum':sum(values) if values else None,'mean':sum(values)/len(values) if values else None}
            arm_summaries.append(summary)
    return {'report_type':'SYNTHETIC_ANALYSIS_SMOKE_ONLY','warning':'All values were fabricated as equal-arm null controls. No agents, policies, society experiments or empirical governance benefits were measured. Zero synthetic effects is not a safety result.','input_sha256':file_digest(rows_path),'schedule_sha256':file_digest(schedule_path),'analysis_implementation_sha256':file_digest(Path(__file__)),'analysis_seed':ANALYSIS_SEED,'bootstrap_resamples':10000,'intervals':'95% paired percentile; marginal and unadjusted; multiple contrasts are descriptive only','fabricated_row_count':len(rows),'actual_agent_trial_count':0,'scored_study_run_count':0,'comparisons':comparisons,'arm_summaries':arm_summaries}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows',type=Path,default=ROOT/'smoke/fabricated_results.jsonl')
    parser.add_argument('--schedule',type=Path,default=ROOT/'fixtures/evaluator_only/analysis_smoke_schedule.jsonl')
    parser.add_argument('--out',type=Path,default=ROOT/'smoke/analysis_report.json')
    parser.add_argument('--mode',choices=['synthetic','scored'],default='synthetic')
    args=parser.parse_args()
    try: result=analyze(args.rows,args.schedule,args.mode); write(args.out,result)
    except (ValueError,KeyError,TypeError) as exc:
        parser.exit(2,str(exc)+'\n')
    print('Synthetic plumbing report written. Actual agent trials: 0. Scored study runs: 0.')
