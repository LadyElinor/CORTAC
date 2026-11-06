"""Read-only, transaction-consistent observations of the pinned S1 contract."""
from contextlib import closing
from pathlib import Path
import sqlite3

from ..scaffold_v1.journal import Journal
from ..scaffold_v1.wire import digest, exact, integer
from ..scaffold_v1.ap1 import HEAD, INSTANCE, matches

FIELDS = ('assignment', 'instance', 'brief_head', 'history', 'decision', 'transport',
          'pending', 'accepted_head', 'review')


def validate(value):
    exact(value, FIELDS)
    exact(value['assignment'], ('id','agent','implementation','controller','reviewer','reviewer_controller'))
    from ..scaffold_v1.wire import label
    for name in value['assignment'].values(): label(name)
    a=value['assignment']
    if a['agent']==a['reviewer'] or a['controller']==a['reviewer_controller']:
        raise ValueError('declared review conflict')
    if not matches(INSTANCE,value['instance']) or not matches(HEAD,value['brief_head']):
        raise ValueError('invalid workshop binding')
    history=value['history']
    if type(history) is not list or not 1 <= len(history) <= 128 or any(not matches(HEAD,h) for h in history):
        raise ValueError('invalid source history')
    if value['decision'] not in ('NOT_STARTED','PENDING','PROPOSE','DECLINE','WAIT','REQUEST-EVIDENCE','INVALID','TIMEOUT','CRASH'):
        raise ValueError('invalid decision observation')
    if value['transport'] not in ('NOT_STAGED','UNRESOLVED','ACCEPTED','REFUSED') or type(value['pending']) is not bool:
        raise ValueError('invalid transport observation')
    if value['transport']=='ACCEPTED':
        if not matches(HEAD,value['accepted_head']): raise ValueError('accepted head required')
    elif value['accepted_head'] is not None:
        raise ValueError('no accepted head')
    if value['transport']!='NOT_STAGED' and value['decision']!='PROPOSE':
        raise ValueError('transport without proposal')
    if value['review'] is not None:
        exact(value['review'],('record_digest','supplied_assessments_pass'))
        if (value['transport']!='ACCEPTED' or not matches(HEAD,value['review']['record_digest'])
                or type(value['review']['supplied_assessments_pass']) is not bool):
            raise ValueError('invalid advisory review observation')


def capture(path):
    path=Path(path).absolute()
    if path.is_symlink() or not path.is_file(): raise ValueError('source missing or unsafe')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=10)) as db:
        db.execute('BEGIN')
        s,head,count=Journal._read(db)
        history=[r[0] for r in db.execute('SELECT hash FROM events ORDER BY seq')]
    d=s['decision']; b=s['genesis']['brief']; t=s['transport']
    decision=('PENDING' if s['decision_started'] else 'NOT_STARTED') if d is None else (
        d['reply']['choice'].upper() if d['outcome']=='VALID' else d['outcome'])
    state='NOT_STAGED' if s['binding'] is None else 'UNRESOLVED'
    accepted=None
    if t and t['state']=='RECORDED':
        state='ACCEPTED' if t['recorded']['receipt']['disposition']=='ACCEPTED' else 'REFUSED'
        if state=='ACCEPTED': accepted=t['recorded']['receipt']['event_hash']
    result=dict(assignment=s['genesis']['assignment'],instance=b['instance'],brief_head=b['view_head'],
        history=history,decision=decision,transport=state,pending=s['pending'] is not None,
        accepted_head=accepted,review=None if s['review'] is None else dict(
            record_digest=digest(s['review']),supplied_assessments_pass=s['review']['supplied_assessments_pass']))
    validate(result)
    return result


def extends(old,new):
    validate(new)
    if any(old[k]!=new[k] for k in ('assignment','instance','brief_head')):
        raise ValueError('source identity changed')
    if new['history'][:len(old['history'])]!=old['history']:
        raise ValueError('source history rewritten or truncated')
    if new['history']==old['history'] and new!=old:
        raise ValueError('same history with changed projection')
