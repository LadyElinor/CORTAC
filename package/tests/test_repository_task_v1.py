"""R1 actual Git/process tests and deliberately untrusted review assertions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from wac_offline.repository_task_v1 import VERSION
from wac_offline.repository_task_v1 import repository
from wac_offline.repository_task_v1.checks import run
from wac_offline.repository_task_v1.demo import fixture, git, proposal, review_packet
from wac_offline.repository_task_v1.journal import Task
from wac_offline.scaffold_v1.wire import canonical, digest


class RepositoryTaskTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.parent = Path(tmp.name); self.root = self.parent/'repository'
        self.spec = fixture(self.root); self.path = self.parent/'task.sqlite'

    def task(self):
        return Task.create(self.path, self.root, self.spec)

    def proposed(self):
        task = self.task(); brief = task.begin()
        (self.root/'value.txt').write_text('new\n', encoding='utf-8')
        task.decide(canonical(proposal(task, brief)).encode())
        return task

    def test_actual_process_then_unknown_review(self):
        task = self.proposed(); r = run(task, 'content')
        self.assertTrue(r['local_checks_passed']); self.assertTrue(r['candidate_current'])
        task.review(review_packet(task)); r = task.report(refresh=True)
        self.assertFalse(r['review']['supplied_assessments_pass'])
        self.assertEqual(r['declared_control'], 'SHARED')
        self.assertTrue(r['review_applicable']); self.assertFalse(r['approval_granted'])
        self.assertGreater(r['checks']['content']['elapsed_ns'], 0)

    def test_all_pass_is_supplied_and_never_independent_approval(self):
        self.spec['reviewer_controller'] = 'another-declared-controller'
        task = self.proposed(); run(task, 'content'); task.review(review_packet(task, 'PASS'))
        r = task.report(refresh=True)
        self.assertTrue(r['review']['supplied_assessments_pass'])
        self.assertFalse(r['independent_review_established']); self.assertFalse(r['approval_granted'])
        self.assertEqual(r['declared_control'], 'DIFFERENT_UNVERIFIED')

    def test_local_nonproposals_have_no_check_permission(self):
        for choice in ('decline', 'wait', 'request-evidence'):
            with self.subTest(choice=choice):
                task = Task.create(self.parent/(choice+'.sqlite'), self.root, self.spec)
                brief = task.begin()
                task.decide(canonical(dict(version=VERSION, brief_id=brief['brief_id'], choice=choice, reason='Need another task.')).encode())
                self.assertEqual(task.report()['decision'], choice.upper())
                with self.assertRaises(ValueError): run(task, 'content')

    def test_extra_agent_command_is_retained_invalid(self):
        task = self.task(); brief = task.begin()
        raw = canonical(dict(version=VERSION, brief_id=brief['brief_id'], choice='decline', reason='X', argv=['evil'])).encode()
        task.decide(raw)
        self.assertEqual(task.report()['decision'], 'INVALID')
        with self.assertRaises(ValueError): task.begin()

    def test_response_requires_correct_brief_and_digest(self):
        task = self.task(); brief = task.begin()
        (self.root/'value.txt').write_text('new\n', encoding='utf-8')
        response = proposal(task, brief); response['candidate_digest'] = '0'*64
        task.decide(canonical(response).encode())
        self.assertEqual(task.report()['decision'], 'INVALID')

    def test_outside_scope_rejected(self):
        task = self.task(); task.begin()
        (self.root/'outside.txt').write_text('unrequested', encoding='utf-8')
        with self.assertRaises(ValueError): task.candidate()

    def test_scope_paths_cannot_escape(self):
        for name in ('../other', '/absolute', 'a/../b', '.git/config', 'C:/path', 'a\\b', 'a//b'):
            with self.subTest(name=name):
                self.spec['allowed_paths'] = [name]
                with self.assertRaises(ValueError): self.task()
        self.assertFalse(self.path.exists())

    def test_unknown_task_fields_and_arbitrary_launcher_refused(self):
        for key in ('authority', 'execution_enabled'):
            spec = deepcopy(self.spec); spec[key] = True
            with self.assertRaises(ValueError): Task.create(self.path, self.root, spec)
        self.spec['checks'][0]['argv'][0] = 'sh'
        with self.assertRaises(ValueError): self.task()

    def test_duplicate_checks_and_roles_refused(self):
        self.spec['checks'] *= 2
        with self.assertRaises(ValueError): self.task()
        self.spec['checks'] = self.spec['checks'][:1]
        self.spec['reviewer'] = self.spec['proposer']
        with self.assertRaises(ValueError): self.task()

    def test_base_untracking_and_ignore_cannot_hide_modified_bytes(self):
        self.spec['allowed_paths'] = ['.gitignore']
        task = self.task()
        git(self.root, 'rm', '--cached', 'value.txt')
        (self.root/'.gitignore').write_text('value.txt\n', encoding='utf-8')
        (self.root/'value.txt').write_text('hidden mutation', encoding='utf-8')
        with self.assertRaises(ValueError): task.candidate()

    def test_before_check_changed_source_never_executes(self):
        task = self.proposed(); (self.root/'value.txt').write_text('later', encoding='utf-8')
        r = run(task, 'content')
        self.assertEqual(r['checks']['content']['outcome'], 'SOURCE_CHANGED')
        self.assertIsNone(r['checks']['content']['process'])
        self.assertFalse(r['local_checks_passed'])

    def test_check_mutating_own_candidate_invalidates_success_exit(self):
        self.spec['checks'][0]['argv'] = ['{python}', '-c', "from pathlib import Path; Path('value.txt').write_text('mutated')"]
        task = self.proposed(); r = run(task, 'content')
        self.assertEqual(r['checks']['content']['process']['exit_code'], 0)
        self.assertEqual(r['checks']['content']['outcome'], 'SOURCE_CHANGED')
        self.assertFalse(r['local_checks_passed'])

    def test_nonzero_exit_retained(self):
        self.spec['checks'][0]['argv'] = ['{python}', '-c', 'raise SystemExit(7)']
        task = self.proposed(); r = run(task, 'content')
        self.assertEqual(r['checks']['content']['outcome'], 'FAIL')
        self.assertEqual(r['checks']['content']['process']['exit_code'], 7)

    def test_windows_process_failure_code_is_retained(self):
        task = self.proposed()
        # Inject a Windows native failure; do not claim an actual crash here.
        real_run = subprocess.run
        def native_failure(command, *args, **kwargs):
            return real_run(command, *args, **kwargs) if command[0] == 'git' else SimpleNamespace(returncode=3221225477)
        with patch('wac_offline.repository_task_v1.checks.subprocess.run', side_effect=native_failure):
            r = run(task, 'content')
        self.assertEqual(r['checks']['content']['outcome'], 'FAIL')
        self.assertEqual(r['checks']['content']['process']['exit_code'], 3221225477)

    def test_predeclared_expected_refusal_is_not_success_semantics(self):
        self.spec['checks'][0]['argv'] = ['{python}', '-c', 'raise SystemExit(2)']
        self.spec['checks'][0]['expected_exit'] = 2
        r = run(self.proposed(), 'content')
        self.assertTrue(r['local_checks_passed']); self.assertFalse(r['approval_granted'])

    def test_timeout_remains_distinct(self):
        self.spec['checks'][0]['argv'] = ['{python}', '-c', 'import time; time.sleep(3)']
        self.spec['checks'][0]['timeout_seconds'] = 1
        r = run(self.proposed(), 'content')
        self.assertEqual(r['checks']['content']['outcome'], 'TIMEOUT')
        self.assertIsNone(r['checks']['content']['process']['exit_code'])

    def test_missing_check_directory_is_error(self):
        self.spec['checks'][0]['cwd'] = 'absent'
        r = run(self.proposed(), 'content')
        self.assertEqual(r['checks']['content']['outcome'], 'ERROR')

    def test_interrupted_start_stays_pending_and_never_retried(self):
        task = self.proposed(); task.append('check_start', {'id': 'content'})
        with self.assertRaises(ValueError): run(Task(self.path), 'content')
        r = Task(self.path).report()
        self.assertEqual(r['pending_check'], 'content'); self.assertIsNone(r['checks']['content'])
        self.assertFalse(r['local_checks_passed'])

    def test_concurrent_starts_consume_once(self):
        task = self.proposed()
        def attempt():
            try:
                Task(self.path).append('check_start', {'id': 'content'}); return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _: attempt(), range(2))), [False, True])
        self.assertEqual(task.report()['events'], 4)

    def test_repeated_check_refused(self):
        task = self.proposed(); run(task, 'content')
        with self.assertRaises(ValueError): run(task, 'content')

    def test_review_waits_for_all_evidence(self):
        task = self.proposed()
        with self.assertRaises(ValueError): task.review(review_packet(task))

    def test_stale_review_evidence_and_wrong_role_refused(self):
        task = self.proposed(); early = review_packet(task); run(task, 'content')
        with self.assertRaises(ValueError): task.review(early)
        wrong = review_packet(task); wrong['reviewer'] = 'author'
        with self.assertRaises(ValueError): task.review(wrong)

    def test_changed_candidate_blocks_review_and_invalidates_old_review(self):
        task = self.proposed(); run(task, 'content'); packet = review_packet(task)
        task.review(packet)
        (self.root/'value.txt').write_text('changed after review', encoding='utf-8')
        r = task.report(refresh=True)
        self.assertFalse(r['review_applicable']); self.assertFalse(r['candidate_current'])
        self.assertIsNotNone(r['review'])

    def test_review_cannot_cite_nonexistent_check(self):
        task = self.proposed(); run(task, 'content'); packet = review_packet(task)
        packet['record']['alternatives'][0]['evidence_refs'] = ['check:invented']
        with self.assertRaises(ValueError): task.review(packet)

    def test_replayed_semantic_forgery_rejected_after_rehash(self):
        task = self.proposed(); run(task, 'content')
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute('SELECT seq,kind,body FROM events ORDER BY seq').fetchall(); head = '0'*64
            for n, kind, raw in rows:
                data = json.loads(raw)
                if kind == 'check_finish': data['id'] = 'undeclared'
                h = digest(dict(seq=n, kind=kind, body=data, previous=head))
                db.execute('UPDATE events SET body=?,previous=?,hash=? WHERE seq=?', (canonical(data), head, h, n)); head = h
        with self.assertRaises(ValueError): task.report()

    def test_journal_must_not_be_observed_as_candidate_source(self):
        with self.assertRaises(ValueError): Task.create(self.root/'task.sqlite', self.root, self.spec)
        self.assertFalse((self.root/'task.sqlite').exists())
        (self.root/'.local').mkdir()
        task = Task.create(self.root/'.local/task.sqlite', self.root, self.spec)
        self.assertEqual(task.report()['decision'], 'NOT_STARTED')

    def test_journal_parent_alias_cannot_evade_source_exclusion(self):
        alias = self.parent/'repository-alias'
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('directory symlinks unavailable')
        with self.assertRaises(ValueError): Task.create(alias/'task.sqlite', self.root, self.spec)
        self.assertFalse((self.root/'task.sqlite').exists())

    def test_journal_leaf_symlink_still_refused(self):
        task = Task.create(self.path, self.root, self.spec)
        alias = self.parent/'journal-alias.sqlite'
        try:
            alias.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest('file symlinks unavailable')
        with self.assertRaises(ValueError): Task(alias).report()
        self.assertEqual(task.report()['decision'], 'NOT_STARTED')

    def test_working_symlink_refused(self):
        outside = self.parent/'outside'; outside.write_text('outside', encoding='utf-8')
        (self.root/'value.txt').unlink()
        try:
            (self.root/'value.txt').symlink_to(outside)
        except OSError:
            self.skipTest('Host does not permit creating symbolic links')
        with self.assertRaises(ValueError): repository.observe(self.root)

    def test_ignored_files_explicitly_outside_inventory(self):
        task = self.proposed(); (self.root/'.local').mkdir(); (self.root/'.local/unobserved').write_text('not captured')
        r = run(task, 'content')
        self.assertTrue(r['local_checks_passed'])

    def test_parent_receipt_never_transfers_authority(self):
        self.spec['parent_receipt'] = 'f'*64
        r = self.proposed().report()
        self.assertEqual(r['parent_receipt'], 'f'*64)
        self.assertFalse(r['parent_authenticity']); self.assertFalse(r['approval_granted'])

    def test_oversized_output_is_not_pass_and_has_only_digest(self):
        self.spec['checks'][0]['argv'] = ['{python}', '-c', "print('x'*1048577)"]
        r = run(self.proposed(), 'content')
        self.assertEqual(r['checks']['content']['outcome'], 'OUTPUT_LIMIT')
        self.assertEqual(set(r['checks']['content']['process']['stdout']), {'sha256','bytes'})

    def test_report_without_refresh_does_not_claim_fresh_review(self):
        task = self.proposed(); run(task, 'content'); task.review(review_packet(task))
        r = task.report()
        self.assertIsNone(r['candidate_current']); self.assertFalse(r['review_applicable'])

    def test_frozen_history_preserved(self):
        import hashlib
        root = Path(__file__).resolve().parents[2]
        manifest = json.loads((root/'provenance/repository_task_preserved.json').read_text())
        for name, expected in manifest['files'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), expected, name)


if __name__ == '__main__':
    unittest.main()
