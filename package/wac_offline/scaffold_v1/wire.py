"""Bounded, unambiguous JSON and content hashes; not signatures."""
import hashlib
import json
import math
import re

MAX_BYTES = 2 * 1024 * 1024
TOKEN = re.compile(r'ucp1\.[0-9a-f]{32}\.[0-9a-f]{64}')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError('missing or unknown fields')


def bounded(value):
    pending = [(value, 0)]
    while pending:
        obj, depth = pending.pop()
        if depth > 48:
            raise ValueError('nesting limit')
        if type(obj) is dict:
            if any(type(k) is not str for k in obj):
                raise ValueError('string keys required')
            pending.extend((v, depth + 1) for v in obj.values())
        elif type(obj) is list:
            pending.extend((v, depth + 1) for v in obj)
        elif type(obj) not in (str, int, bool, float, type(None)):
            raise ValueError('JSON values required')
        elif type(obj) is float and not math.isfinite(obj):
            raise ValueError('finite numbers required')
        elif type(obj) is int and abs(obj) > 2**53 - 1:
            raise ValueError('unsafe integer')
    raw = canonical(value)
    if len(raw.encode()) > MAX_BYTES or TOKEN.search(raw):
        raise ValueError('oversized or credential-shaped content')
    return value


def parse(raw):
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError('bounded UTF-8 bytes required')
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    try:
        return bounded(json.loads(raw.decode('utf-8'), object_pairs_hook=pairs))
    except (RecursionError, UnicodeError, OverflowError) as exc:
        raise ValueError('invalid JSON encoding or depth') from exc


def label(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', value):
        raise ValueError('invalid identifier')


def integer(value, maximum=2**53-1):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('invalid counter')
