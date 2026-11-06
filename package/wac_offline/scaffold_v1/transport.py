"""Optional pinned C2 bridge, invoked only by the trusted local custodian."""
from contextlib import closing
import hashlib
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from . import ap1
from .wire import canonical, digest


def check_endpoint(url):
    if type(url) is not str:
        raise ValueError('literal loopback endpoint required')
    p = urlsplit(url)
    if (p.scheme != 'http' or p.hostname != '127.0.0.1' or not p.port
            or p.netloc != '127.0.0.1:' + str(p.port) or p.path or p.query or p.fragment):
        raise ValueError('literal loopback endpoint required')
    return url


def client():
    try:
        from commonwealth_client_v2 import VERSION
        from commonwealth_client_v2.store import Outbox
    except ImportError as exc:
        raise ValueError('install the separately reviewed Commonwealth C2 wheel first') from exc
    if VERSION != 'client-only-2.0.0':
        raise ValueError('unsupported C2 version')
    return Outbox


def credentials(token):
    if type(token) is not str or not re.fullmatch(r'ucp1\.[0-9a-f]{32}\.[0-9a-f]{64}', token):
        raise ValueError('invalid credential')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def request_bytes(state):
    decision = state['decision']
    if not decision or decision['outcome'] != 'VALID' or decision['reply']['choice'] != 'propose':
        raise ValueError('a valid proposal is required')
    return canonical(ap1.interpret(state['genesis']['brief'], state['decision']['reply'])).encode()


def _matched_outbox(state, token):
    binding = state['binding']
    if not binding or credentials(token) != binding['credential_digest']:
        raise ValueError('original capability required')
    path = Path(binding['outbox'])
    if path.is_symlink() or not path.is_file():
        raise ValueError('retained outbox missing or unsafe; no automatic restaging')
    box = client()(path)
    # Pinned C2 private read API: needed because public status omits request bytes.
    # No writes to client tables; the version and exact source are separately checked.
    with closing(box.connect()) as db:
        db.execute('BEGIN')
        intent, raw, _ = box._read(db)
    if (intent['url'] != binding['url'] or intent['credential_digest'] != binding['credential_digest']
            or intent['instance'] != binding['instance'] or intent['request_id'] != binding['request_id']
            or intent['raw_sha256'] != binding['raw_sha256'] or raw != request_bytes(state)):
        raise ValueError('outbox differs from retained intent')
    return box


def _finish(journal, status, start, recovered=False):
    journal.append('operation_finish', dict(status=status, recovered=recovered,
                   elapsed_ns=None if recovered else max(0, time.monotonic_ns()-start)))
    return journal.report()


def stage(journal, outbox, url, token):
    state = journal.state()
    raw = request_bytes(state)
    if raw == b'null':
        raise ValueError('non-proposal cannot be staged')
    path = Path(outbox).absolute()
    if path.exists() or path.is_symlink() or path == journal.path:
        raise ValueError('new outbox path required')
    binding = dict(outbox=str(path), url=check_endpoint(url), credential_digest=credentials(token),
                   instance=state['genesis']['brief']['instance'],
                   request_id=ap1.interpret(state['genesis']['brief'], state['decision']['reply'])['request_id'],
                   raw_sha256=hashlib.sha256(raw).hexdigest())
    Outbox = client()  # refuse missing prerequisite before committing intent
    if state['binding'] is None:
        journal.append('intent_bound', binding)
    elif state['binding'] != binding:
        raise ValueError('assignment already binds another intent')
    # If a prior stage began, even an absent file cannot justify replacing it.
    journal.append('operation_start', {'kind': 'stage'})
    start = time.monotonic_ns()
    brief = state['genesis']['brief']
    task = dict(protocol=ap1.PROTOCOL, disposition='TASK', external_authority='NONE',
                instance=brief['instance'], view_head=brief['view_head'])
    status = Outbox.stage(path, url, token, task, raw)
    return _finish(journal, status, start)


def operate(journal, token, kind):
    if kind not in ('submit', 'resolve', 'inspect'):
        raise ValueError('unsupported operation')
    state = journal.state()
    if state['pending']:
        raise ValueError('inspect interrupted operation with recover first')
    box = _matched_outbox(state, token)
    journal.append('operation_start', {'kind': kind})
    start = time.monotonic_ns()
    status = box.status() if kind == 'inspect' else box.operate(token, 'retry' if kind == 'submit' else 'resolve')
    return _finish(journal, status, start)


def recover(journal, token):
    """Local inspection only. No network request and no new outbox or identity."""
    state = journal.state()
    if not state['pending']:
        raise ValueError('no interrupted operation')
    box = _matched_outbox(state, token)
    return _finish(journal, box.status(), 0, recovered=True)
