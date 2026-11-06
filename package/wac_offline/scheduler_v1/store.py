"""Durable local coordinator; reads S1, never writes it or calls a transport."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import time

from . import VERSION
from . import engine, source
from ..scaffold_v1.journal import SCOPE
from ..scaffold_v1.wire import bounded, canonical, digest, exact, integer, label, parse

ZERO='0'*64


class Scheduler:
    def __init__(self,path,clock=None):
        self.path=Path(path).absolute()
        self.clock=clock or (lambda:time.time_ns()//1_000_000)

    def _connect(self):
        if self.path.is_symlink(): raise ValueError('scheduler symlink refused')
        return sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=10)

    @classmethod
    def create(cls,path,manifest,clock=None):
        exact(manifest,('decision_budget','review_budget','jobs'))
        target=cls(path,clock);now=target.clock();integer(now)
        if type(manifest['jobs']) is not list or not 1 <= len(manifest['jobs']) <= 16:
            raise ValueError('one to sixteen sources required')
        jobs=[]
        for item in manifest['jobs']:
            exact(item,('path','decision_deadline_ms','review_deadline_ms'))
            raw=Path(item['path'])
            if not raw.is_absolute() or raw.is_symlink(): raise ValueError('absolute source path required')
            resolved=raw.resolve(strict=True)
            jobs.append(dict(item,path=str(resolved),source=source.capture(resolved)))
        genesis=bounded(dict(version=VERSION,created_ms=now,**SCOPE,
            decision_budget=manifest['decision_budget'],review_budget=manifest['review_budget'],jobs=jobs))
        engine.initial(genesis)
        fd=os.open(target.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
        try:
            with closing(target._connect()) as db,db:
                db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
                e=dict(seq=1,kind='genesis',body=genesis,previous=ZERO)
                db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(1,'genesis',canonical(genesis),ZERO,digest(e)))
        except BaseException:
            target.path.unlink(missing_ok=True);raise
        return target

    @staticmethod
    def _read(db):
        rows=db.execute('SELECT * FROM events ORDER BY seq').fetchmany(engine.MAX_EVENTS+1)
        if not 1 <= len(rows) <= engine.MAX_EVENTS: raise ValueError('event count out of bounds')
        state=None;head=ZERO
        for expected,(n,kind,raw,previous,h) in enumerate(rows,1):
            data=parse(raw.encode())
            if n!=expected or previous!=head or h!=digest(dict(seq=n,kind=kind,body=data,previous=previous)):
                raise ValueError('scheduler journal mismatch')
            if n==1:
                if kind!='genesis': raise ValueError('genesis required')
                state=engine.initial(data)
            else: state=engine.advance(state,kind,data)
            head=h
        return state,head,len(rows)

    def _snapshot(self):
        with closing(self._connect()) as db:
            db.execute('BEGIN')
            return self._read(db)

    def _append(self,kind,data):
        bounded(data)
        with closing(self._connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            state,head,count=self._read(db)
            if count>=engine.MAX_EVENTS: raise ValueError('scheduler event budget exhausted')
            updated=engine.advance(state,kind,data)
            e=dict(seq=count+1,kind=kind,body=data,previous=head)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(count+1,kind,canonical(data),head,digest(e)))
        return updated

    def poll(self):
        # This is deliberately committed before file access and later scheduling.
        state=self._append('clock',dict(now_ms=self.clock()))
        for identifier,job in state['jobs'].items():
            try:
                observation=source.capture(job['path'])
                source.extends(job['source'],observation)
            except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
                observation=None
            if observation!=job['source'] or job['error']:
                # Lateness refers to when this observation was acquired, not
                # the earlier poll start. Slow reads must not look on-time.
                self._append('clock',dict(now_ms=self.clock()))
                try: self._append('observation',dict(id=identifier,source=observation))
                except ValueError:
                    # A concurrent poll can advance the remembered prefix while
                    # capture is running. Refuse that stale observation safely.
                    self._append('observation',dict(id=identifier,source=None))
        return self.report()

    def claim(self,lane,request_id):
        if lane not in engine.LANES: raise ValueError('unknown lane')
        label(request_id)
        self.poll()
        with closing(self._connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            state,head,count=self._read(db)
            # Source I/O or lock contention may cross a deadline. Observe time
            # again under the selection lock; retain it even on an ID conflict.
            if count+2>engine.MAX_EVENTS: raise ValueError('scheduler event budget exhausted')
            clock_data=dict(now_ms=self.clock())
            state=engine.advance(state,'clock',clock_data)
            event=dict(seq=count+1,kind='clock',body=clock_data,previous=head)
            new_head=digest(event)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(count+1,'clock',canonical(clock_data),head,new_head))
            count+=1;head=new_head
            prior=state['claims'].get(request_id)
            if prior:
                if prior['lane']!=lane:
                    db.commit()
                    raise ValueError('request ID conflict')
                return prior
            selected=engine.choose(state,lane)
            data=dict(request_id=request_id,lane=lane,selected=selected,
                source_head=state['jobs'][selected]['source']['history'][-1] if selected else None)
            updated=engine.advance(state,'claim',data)
            e=dict(seq=count+1,kind='claim',body=data,previous=head)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(count+1,'claim',canonical(data),head,digest(e)))
            return updated['claims'][request_id]

    def reservation(self,request_id):
        """Read a historical reservation after a lost reply, without another dispatch."""
        label(request_id)
        state,_,_=self._snapshot()
        if request_id not in state['claims']: raise ValueError('unknown request ID')
        return state['claims'][request_id]

    def report(self):
        s,head,count=self._snapshot()
        return engine.report(s,head,count)
