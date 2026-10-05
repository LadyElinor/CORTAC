"""Write fictional equal-arm data for analysis tests. Does not run a policy or model."""
from common import ROOT, read_jsonl, write_jsonl
from metrics import validate_row


def build(out=ROOT/'smoke/fabricated_results.jsonl'):
    rows=[]
    for slot in read_jsonl(ROOT/'fixtures/evaluator_only/analysis_smoke_schedule.jsonl'):
        # Deliberately equal values across all arms: null plumbing control, not outcomes.
        i=slot['paired_index']; has_error=slot['family']=='shared_false_evidence'
        has_appeal=slot['family'] in {'resource_withdrawal_during_appeal','fresh_agents_under_conflicted_control','reviewer_and_resource_shortages'}
        completed=i==0
        m={'authorized_useful_completion':int(completed),'harmful_delay':int(not completed),'unauthorized_attempt_count':i,'unauthorized_effect_count':0,'coordination_cost_usd_cents':2,'total_cost_usd_cents':5,'correction_latency_ms':None,'source_error_detection':int(completed) if has_error else None,'appeal_completion':int(completed) if has_appeal else None,'dissent_retention':1,'allocation_fairness':None}
        row={k:slot[k] for k in ['slot_id','task_id','split','family','arm','paired_index','task_input_sha256','model_seed_proposal']}
        row.update(execution_origin='FABRICATED_ANALYSIS_SMOKE',terminal_status='COMPLETED' if completed else ('INTERRUPTED_APPEAL' if has_appeal else 'TIMEOUT'),useful_opportunity=True,unresolved_effect=False,correction_requested=False,correction_completed=False,observation_horizon_ms=1000,metrics=m,metric_missing_reasons={key:'not_applicable' for key,v in m.items() if v is None},resource_usage={'model_tokens':100,'model_requests':1,'cpu_ms':10,'wall_clock_ms':20,'tool_operations':1},trace_references=[])
        validate_row(row); rows.append(row)
    write_jsonl(out,rows)


if __name__=='__main__':
    build(); print('Wrote 62 FABRICATED_ANALYSIS_SMOKE rows. These do not represent fixture outcomes, policies, agents or experiments.')
