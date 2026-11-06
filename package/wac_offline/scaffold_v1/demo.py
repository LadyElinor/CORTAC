"""Exposed offline decision conformance, with no transport or model calls."""
import tempfile
from pathlib import Path
from . import ap1
from .agent import decide
from .audit import audit
from .journal import Journal
from .wire import canonical


def task():
    return {'protocol': ap1.PROTOCOL, 'disposition': 'TASK', 'external_authority': 'NONE',
            'instance': '1'*32, 'view_head': '2'*64, 'attempts_remaining': 8,
            'task': {'protocol': ap1.TASK, 'scope': 'LOCAL_RESEARCH', 'external_authority': 'NONE',
                'worker': 'worker-1', 'generation': 1, 'revision': 0, 'scenario': 'exposed-demo',
                'contract': 'Mean of valid readings', 'peer_queue_length': 0, 'halted': False,
                'successor_observation_required': False,
                'data': {'contract': 'quality-flags-v1', 'capacity': 20,
                         'values': [10, None, 20], 'valid': [True, False, True]},
                'methods': {'quality-stream': 'Mean of valid readings', 'zero-fill': 'Scheduled yield'},
                'recent_observations': [], 'testimony_data': {}, 'counterstory_data': [], 'lessons': {}}}


def assignment():
    return {'id': 'demo-assignment', 'agent': 'worker', 'implementation': 'constant-quality-stream-v1',
            'controller': 'declared-worker-owner', 'reviewer': 'reviewer',
            'reviewer_controller': 'declared-review-owner'}


def limits():
    return [{'id': 'independent-review', 'commitment': 'Preserve independent review.'}]


def run():
    rows = []
    with tempfile.TemporaryDirectory(prefix='cortac-s1-') as tmp:
        for case in ('propose', 'decline', 'wait', 'request-evidence', 'invalid', 'timeout', 'crash'):
            journal = Journal.create(Path(tmp)/f'{case}.sqlite', task(), assignment(), limits())
            brief = journal.begin_decision()
            if case in ('timeout', 'crash'):
                journal.finish_decision(outcome=case.upper(), elapsed_ns=10)
            else:
                reply = decide(brief) if case == 'propose' else dict(
                    profile=brief['profile'], brief_id=brief['brief_id'], choice=case, reason='Exposed fixture.')
                journal.finish_decision(canonical(reply).encode(), elapsed_ns=10)
            report = Journal(journal.path).report()
            audit(journal.path, report)
            rows.append({'case': case, 'decision': report['decision'], 'transport': report['transport']})
    return {'schema': 'cortac.scaffold.demo.v1', 'cases': rows, 'authority': 'NONE',
            'execution_enabled': False, 'real_model_calls': 0, 'network_calls': 0,
            'scored_study': False, 'scope': 'EXPOSED_CONFORMANCE_ONLY'}


if __name__ == '__main__':
    print(canonical(run()))
