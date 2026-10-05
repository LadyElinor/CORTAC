"""Strict local JSON I/O. Report serialization is deliberately NOT RFC 8785 JCS."""
import hashlib
import json
from pathlib import Path

class InputError(ValueError):
    pass

def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InputError(f'duplicate JSON key: {key}')
        out[key] = value
    return out

def _bad_constant(value):
    raise InputError(f'non-finite JSON number: {value}')

def loads(text):
    try:
        return json.loads(text, object_pairs_hook=_unique, parse_constant=_bad_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise InputError(str(exc)) from exc

def read(path):
    return loads(Path(path).read_text(encoding='utf-8'))

def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def report_bytes(value):
    # Reproducible for this implementation's restricted JSON outputs; never JCS.
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')

def report_hash(value):
    return hashlib.sha256(report_bytes(value)).hexdigest()

def write(path, value):
    Path(path).write_bytes(report_bytes(value))
