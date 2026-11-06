"""Real disposable Git/command effects with authored decisions, no agent efficacy."""
import json
from pathlib import Path
import subprocess
import tempfile
from . import VERSION
from .journal import Task
from .checks import run
from ..scaffold_v1.wire import canonical


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def fixture(root, code="from pathlib import Path; assert Path('value.txt').read_text() == 'new\\n'"):
    root.mkdir(); git(root, 'init', '-q'); git(root, 'config', 'core.autocrlf', 'false')
    (root/'value.txt').write_text('old\n', encoding='utf-8')
    (root/'.gitignore').write_text('.local/\n__pycache__/\n', encoding='utf-8')
    git(root, 'add', '.'); git(root, '-c', 'user.name=Research fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Fixture base')
    return dict(version=VERSION, id='repository-demo', base_commit=git(root, 'rev-parse', 'HEAD'),
                allowed_paths=['value.txt'], proposer='author', reviewer='reviewer',
                proposer_controller='same-operator', reviewer_controller='same-operator',
                purpose='Exposed file-change conformance example.', parent_receipt=None,
                protected_limits=[dict(id='independent-review', commitment='Independent scrutiny is not established by supplied labels.')],
                checks=[dict(id='content', argv=['{python}', '-c', code], cwd='.', expected_exit=0, timeout_seconds=5)])


def record(status='UNKNOWN'):
    return dict(schema='cortac.decision.record.v1',
                affected_parties=[dict(id='maintainer', interests='Correct file change.', benefits='Checked candidate.',
                                      burdens='Local testing only.', representation='Authored demonstration; no independent representative.')],
                alternatives=[dict(option='Keep old bytes.', less_harmful_analysis='Avoids modification.',
                                   rejection_or_selection_reason='Example asks for new bytes.', evidence_refs=['candidate'])],
                protected_limit_assessments=[dict(limit_id='independent-review', status=status,
                                                 reasons='One supplied operator; independence is unestablished.', evidence_refs=['task'])],
                burden_justification='Bounded local demonstration only.',
                dissent=['Shared control is not independent review.'], dissent_status='RECORDED',
                predictions=['The declared content check will observe the new bytes.'],
                review_triggers=[dict(condition='Bytes or evidence changes.', review_authority='Ordinary maintainer.')],
                remedy_plan=dict(authority='No authority granted by this record.', resources='Local development work.',
                                 steps='Retain failed task and propose a new scoped revision.', evidence_refs=['task']),
                evidence_refs=['candidate', 'task'])


def proposal(task, brief):
    return dict(version=VERSION, brief_id=brief['brief_id'], choice='propose',
                candidate_digest=task.candidate()['candidate_digest'], reason='Propose the observed candidate bytes.')


def review_packet(task, status='UNKNOWN'):
    r = task.report()
    return dict(reviewer='reviewer', candidate_digest=r['candidate_digest'], evidence_digest=r['evidence_digest'], record=record(status))


def main():
    with tempfile.TemporaryDirectory(prefix='cortac-r1-') as temporary:
        parent = Path(temporary); root = parent/'repository'
        spec = fixture(root); task = Task.create(parent/'task.sqlite', root, spec); brief = task.begin()
        (root/'value.txt').write_text('new\n', encoding='utf-8')
        task.decide(canonical(proposal(task, brief)).encode())
        run(task, 'content'); task.review(review_packet(task))
        r = task.report(refresh=True)
        print(json.dumps(dict(schema='cortac.repository-task-demo.v1', authority=r['authority'],
                              external_execution_enabled=False, local_checks_passed=r['local_checks_passed'],
                              supplied_assessments_pass=r['review']['supplied_assessments_pass'],
                              independent_review_established=False, declared_control=r['declared_control'],
                              actual_local_test_process=True, real_model_calls=0, scored_study=False), sort_keys=True))


if __name__ == '__main__':
    main()
