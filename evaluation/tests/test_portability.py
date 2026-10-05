"""Byte-identity regressions under emulated Windows text I/O and path syntax."""
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
import tempfile
import unittest
from unittest.mock import patch

from common import ROOT, read, file_digest, write
from generate_fixtures import build


@contextmanager
def windows_default_newlines():
    original = Path.open

    def translated(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        if 'b' not in mode and any(flag in mode for flag in 'wax') and newline is None:
            newline = '\r\n'
        return original(path, mode=mode, buffering=buffering, encoding=encoding,
                        errors=errors, newline=newline)

    with patch.object(Path, 'open', translated):
        yield


class PortabilityTests(unittest.TestCase):
    def test_json_write_is_utf8_lf_under_windows_translation(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'value.json'
            with windows_default_newlines():
                write(out, {'text': 'caf\u00e9', 'enabled': False})
            self.assertEqual(out.read_bytes(), b'{\n  "enabled": false,\n  "text": "caf\xc3\xa9"\n}\n')

    def assert_pinned_fixtures(self, directory):
        output = Path(directory)
        expected = read(ROOT / 'fixtures/fixture_inventory.json')['files']
        for relative, sha in expected.items():
            self.assertEqual(file_digest(output / relative), sha, relative)
        self.assertEqual((output / 'fixture_inventory.json').read_bytes(),
                         (ROOT / 'fixtures/fixture_inventory.json').read_bytes())

    def test_generated_fixtures_keep_pinned_hashes_under_windows_translation(self):
        with tempfile.TemporaryDirectory() as td:
            with windows_default_newlines():
                build(td)
            self.assert_pinned_fixtures(td)

    def test_inventory_paths_remain_posix_under_windows_path_syntax(self):
        original = Path.relative_to

        def windows_relative(path, *other):
            return PureWindowsPath(*original(path, *other).parts)

        with tempfile.TemporaryDirectory() as td:
            with windows_default_newlines(), patch.object(Path, 'relative_to', windows_relative):
                build(td)
            self.assert_pinned_fixtures(td)


if __name__ == '__main__':
    unittest.main()
