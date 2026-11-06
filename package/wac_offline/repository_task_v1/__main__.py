"""Local repository-task custodian CLI; no automatic mutation, submission or merge."""
import argparse
from pathlib import Path
import sqlite3
import subprocess
import sys
from .journal import Task
from .checks import run
from ..scaffold_v1.wire import MAX_BYTES, canonical, parse


def read(path):
    with Path(path).open('rb') as handle:
        return handle.read(MAX_BYTES+1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('new', 'begin', 'candidate', 'decide', 'check', 'review', 'report'):
        sub = commands.add_parser(name); sub.add_argument('journal')
        if name == 'new':
            sub.add_argument('repository'); sub.add_argument('task')
        if name in ('decide', 'review'):
            sub.add_argument('response')
        if name == 'check':
            sub.add_argument('check_id')
    args = parser.parse_args(argv)
    try:
        task = Task(args.journal)
        if args.command == 'new':
            task = Task.create(args.journal, args.repository, parse(read(args.task)))
            result = task.report()
        elif args.command in ('begin', 'candidate'):
            result = getattr(task, args.command)()
        elif args.command == 'decide':
            task.decide(read(args.response)); result = task.report(refresh=True)
        elif args.command == 'review':
            task.review(parse(read(args.response))); result = task.report(refresh=True)
        elif args.command == 'check':
            result = run(task, args.check_id)
        else:
            result = task.report(refresh=True)
        print(canonical(result))
        if result.get('decision') == 'INVALID':
            return 2
        if args.command == 'check' and result['checks'][args.check_id]['outcome'] != 'PASS':
            return 3
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError):
        print('REPOSITORY_TASK_REFUSED: retain the journal; no approval or authority.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
