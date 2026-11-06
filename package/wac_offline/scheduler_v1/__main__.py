"""Pull coordinator CLI. Reservations do not run agents or submit proposals."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
from .store import Scheduler
from ..scaffold_v1.wire import MAX_BYTES,parse


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    commands=p.add_subparsers(dest='command',required=True)
    for name in ('new','poll','claim','reservation','report'):
        sub=commands.add_parser(name);sub.add_argument('database')
        if name=='new': sub.add_argument('manifest')
        if name=='claim': sub.add_argument('lane',choices=('decision','review'))
        if name in ('claim','reservation'): sub.add_argument('request_id')
    a=p.parse_args(argv)
    try:
        scheduler=Scheduler(a.database)
        if a.command=='new':
            with Path(a.manifest).open('rb') as f: manifest=parse(f.read(MAX_BYTES+1))
            result=Scheduler.create(a.database,manifest).report()
        elif a.command=='claim': result=scheduler.claim(a.lane,a.request_id)
        elif a.command=='reservation': result=scheduler.reservation(a.request_id)
        else: result=getattr(scheduler,a.command)()
        print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
        return 0
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error):
        print('SCHEDULER_REFUSED: inspect retained state; no new authority.',file=sys.stderr)
        return 2


if __name__=='__main__': raise SystemExit(main())
