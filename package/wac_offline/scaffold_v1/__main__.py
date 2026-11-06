"""File-based custodian CLI. Agent programs receive only the brief command output."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .journal import Journal
from .wire import MAX_BYTES, exact, parse
from . import transport


def read(path, limit=MAX_BYTES):
    with Path(path).open('rb') as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input exceeds bound')
    return raw


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='command', required=True)
    new = subs.add_parser('new')
    new.add_argument('journal'); new.add_argument('task'); new.add_argument('assignment')
    for name in ('brief', 'begin', 'report', 'decision', 'stage', 'submit', 'resolve', 'inspect', 'recover', 'review'):
        sub = subs.add_parser(name); sub.add_argument('journal')
        if name == 'decision':
            group = sub.add_mutually_exclusive_group(required=True)
            group.add_argument('--response'); group.add_argument('--outcome', choices=('TIMEOUT', 'CRASH'))
            sub.add_argument('--elapsed-ns', type=int, required=True)
        if name == 'stage':
            sub.add_argument('outbox'); sub.add_argument('url')
        if name in ('stage', 'submit', 'resolve', 'inspect', 'recover'):
            sub.add_argument('credential_file')
        if name == 'review':
            sub.add_argument('reviewer'); sub.add_argument('record')
    args = p.parse_args(argv)
    try:
        journal = Journal(args.journal)
        if args.command == 'new':
            assignment = parse(read(args.assignment))
            exact(assignment, ('assignment', 'protected_limits'))
            journal = Journal.create(args.journal, parse(read(args.task)), **assignment)
            result = journal.report()
        elif args.command == 'brief':
            result = journal.state()['genesis']['brief']
        elif args.command == 'begin':
            result = journal.begin_decision()
        elif args.command == 'decision':
            journal.finish_decision(read(args.response) if args.response else None,
                                    outcome='RESPONSE' if args.response else args.outcome,
                                    elapsed_ns=args.elapsed_ns)
            result = journal.report()
        elif args.command == 'review':
            journal.review(args.reviewer, parse(read(args.record)))
            result = journal.report()
        elif args.command == 'report':
            result = journal.report()
        else:
            token = read(args.credential_file, 256).decode('ascii').strip()
            if args.command == 'stage':
                result = transport.stage(journal, args.outbox, args.url, token)
            elif args.command == 'recover':
                result = transport.recover(journal, token)
            else:
                result = transport.operate(journal, token, args.command)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        if result.get('transport') == 'UNRESOLVED':
            return 3
        return 0
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error):
        print('REFUSED_OR_UNRESOLVED: inspect the retained journal/outbox; do not replace uncertain intent.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
