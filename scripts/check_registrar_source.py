"""Check source provenance and insertion-only specification revision."""
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    provenance = json.loads((ROOT / 'provenance/registrar_revision.json').read_text(encoding='utf-8'))
    original = (ROOT / 'provenance/commonwealth_supplied.md').read_bytes()
    revised = (ROOT / 'docs/COMMONWEALTH_REGISTRAR_REVISION.md').read_text(encoding='utf-8')
    source = provenance['source']
    assert len(original) == source['bytes'], 'source byte count changed'
    assert hashlib.sha256(original).hexdigest() == source['sha256'], 'source digest changed'
    old_lines = original.decode('utf-8').splitlines()
    assert len(old_lines) == source['lines'], 'source line count changed'
    changes = SequenceMatcher(None, old_lines, revised.splitlines(), autojunk=False).get_opcodes()
    assert all(kind in ('equal', 'insert') for kind, *_ in changes), 'original source removed or rewritten'
    print(json.dumps({'source_bytes': len(original), 'source_lines': len(old_lines),
                      'insertion_only_revision': True, 'source_sha256': source['sha256']}))


if __name__ == '__main__':
    main()
