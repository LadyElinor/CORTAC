"""Separate chain/reservation recount. Does not replay scheduler eligibility."""
from contextlib import closing
from pathlib import Path
import sqlite3
from ..scaffold_v1.wire import digest,parse


def audit(path,report):
    with closing(sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT * FROM events ORDER BY seq').fetchmany(513)
    if not 1<=len(rows)<=512:raise ValueError('invalid event count')
    head='0'*64;used={'decision':0,'review':0};claims=[];ids=set();reserved=set()
    for expected,(n,kind,raw,previous,h) in enumerate(rows,1):
        body=parse(raw.encode())
        if n!=expected or previous!=head or h!=digest(dict(seq=n,kind=kind,body=body,previous=previous)):
            raise ValueError('chain mismatch')
        head=h
        if n==1:
            if kind!='genesis' or body['execution_enabled'] is not False or body['authority']!='NONE':
                raise ValueError('invalid genesis scope')
            budget={lane:body[lane+'_budget'] for lane in used};clock=body['created_ms']
            jobs={j['source']['assignment']['id']:j for j in body['jobs']}
        elif kind=='clock':
            if type(body['now_ms']) is not int or body['now_ms']<clock:raise ValueError('clock rollback')
            clock=body['now_ms']
        elif kind=='observation':
            if body['id'] not in jobs:raise ValueError('unknown source')
        elif kind=='claim':
            lane=body['lane'];identifier=body['selected'];key=body['request_id']
            if key in ids or lane not in used:raise ValueError('duplicate/unknown reservation')
            ids.add(key)
            if identifier is not None:
                if identifier not in jobs or (lane,identifier) in reserved:raise ValueError('duplicate assignment reservation')
                reserved.add((lane,identifier));used[lane]+=1
            claims.append(dict(body,reserved_at_ms=clock,authority='NONE',execution_enabled=False,
                scope='HISTORICAL_SCHEDULING_RESERVATION_ONLY'))
        else:raise ValueError('unknown event')
    expected=dict(reservations=used,remaining={lane:budget[lane]-used[lane] for lane in used},
        claims=claims,journal_head=head,events=len(rows),clock_ms=clock,authority='NONE',execution_enabled=False)
    if any(expected['remaining'][lane]<0 for lane in used):raise ValueError('overspent reservation budget')
    from ..scaffold_v1.wire import canonical
    if canonical({k:report.get(k) for k in expected})!=canonical(expected):raise ValueError('reservation report mismatch')
    return dict(verified=True,checked_fields=sorted(expected),scope='CHAIN_AND_RESERVATION_COUNTS_ONLY',
        eligibility_replayed=False,source_authenticity=False,authority='NONE')
