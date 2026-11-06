"""Bounded Git/base and working-byte observations, not a filesystem lock."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from ..scaffold_v1.wire import digest, exact

MAX_FILES = 4096
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{40}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def path_name(name):
    if (type(name) is not str or not name or len(name) > 240 or '\\' in name or ':' in name
            or name.startswith('/') or any(p in ('', '.', '..', '.git') for p in name.split('/'))
            or any(ord(c) < 32 for c in name) or str(PurePosixPath(name)) != name):
        raise ValueError('unsafe repository-relative path')
    return name


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL, timeout=30)


def root_path(root):
    root = Path(root).resolve(strict=True)
    actual = Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if root != actual:
        raise ValueError('repository root required')
    return root


def validate_inventory(value):
    if type(value) is not dict or not 1 <= len(value) <= MAX_FILES:
        raise ValueError('bounded nonempty inventory required')
    total = 0
    for name, item in value.items():
        path_name(name); exact(item, ('sha256', 'bytes', 'mode'))
        if (type(item['sha256']) is not str or not SHA.fullmatch(item['sha256'])
                or type(item['bytes']) is not int or not 0 <= item['bytes'] <= MAX_FILE
                or item['mode'] not in ('100644', '100755')):
            raise ValueError('invalid file observation')
        total += item['bytes']
    if total > MAX_TOTAL:
        raise ValueError('repository byte limit')


def base_inventory(root, commit):
    if type(commit) is not str or not HEX.fullmatch(commit):
        raise ValueError('full SHA-1 Git commit required')
    if git(root, 'cat-file', '-t', commit).strip() != b'commit':
        raise ValueError('base must identify a commit')
    rows = git(root, 'ls-tree', '-rlz', '--full-tree', commit).split(b'\0')[:-1]
    if not 1 <= len(rows) <= MAX_FILES:
        raise ValueError('base file limit')
    inventory = {}; total = 0
    for row in rows:
        metadata, raw_name = row.split(b'\t', 1)
        mode, kind, oid, size = metadata.split()
        name = path_name(raw_name.decode('utf-8'))
        if mode not in (b'100644', b'100755') or kind != b'blob':
            raise ValueError('base links/submodules unsupported')
        size = int(size); total += size
        if size > MAX_FILE or total > MAX_TOTAL:
            raise ValueError('base byte limit')
        data = git(root, 'cat-file', 'blob', oid.decode())
        if len(data) != size:
            raise ValueError('base changed while reading')
        inventory[name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=size, mode=mode.decode())
    validate_inventory(inventory)
    return inventory


def observe(root, retained_paths=()):
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError('repository unavailable or replaced by link')
    # Removing a base file from the index and ignoring it must not hide its bytes.
    names = sorted(set(retained_paths) | set(n.decode('utf-8') for n in git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0') if n))
    if len(names) > MAX_FILES:
        raise ValueError('working file limit')
    modes = {}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1); mode, oid, stage = metadata.split()
        if stage != b'0' or mode not in (b'100644', b'100755'):
            raise ValueError('unmerged or unsupported index entry')
        modes[name.decode('utf-8')] = mode.decode()
    inventory = {}; total = 0
    for name in names:
        path_name(name); path = root / name
        for part in [path, *path.parents]:
            if part == root:
                break
            if part.is_symlink():
                raise ValueError('working links unsupported')
        if not path.exists():
            continue
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
            raise ValueError('unsupported/oversized working file')
        total += info.st_size
        if total > MAX_TOTAL:
            raise ValueError('working byte limit')
        data = path.read_bytes()
        if len(data) != info.st_size or path.stat().st_mtime_ns != info.st_mtime_ns:
            raise ValueError('working file changed while reading')
        mode = ('100755' if info.st_mode & stat.S_IXUSR else '100644') if os.name != 'nt' else modes.get(name, '100644')
        inventory[name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), mode=mode)
    validate_inventory(inventory)
    return inventory


def changed(base, candidate):
    return sorted(name for name in set(base) | set(candidate) if base.get(name) != candidate.get(name))


def scoped(base, candidate, allowed):
    validate_inventory(candidate)
    differences = changed(base, candidate)
    if not differences or not set(differences) <= set(allowed):
        raise ValueError('no change or changes outside task scope')
    return differences
