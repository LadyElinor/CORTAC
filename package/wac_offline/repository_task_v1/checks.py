"""Explicit custodian checks. This runner is not an OS or network sandbox."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from . import repository
from ..scaffold_v1.wire import digest


def stream_receipt(handle):
    handle.flush(); handle.seek(0); h = hashlib.sha256(); size = 0
    for chunk in iter(lambda: handle.read(65536), b''):
        h.update(chunk); size += len(chunk)
    return dict(sha256=h.hexdigest(), bytes=size)


def observe(root, retained_paths):
    try:
        return digest(repository.observe(root, retained_paths))
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError):
        return None


def run(task, check_id):
    # Commit before source I/O or invoking a process. Interrupted starts cannot
    # be reused; retain their task and create no hidden retry.
    s = task.append('check_start', dict(id=check_id))
    root = Path(s['genesis']['root'])
    spec = next(c for c in s['genesis']['task']['checks'] if c['id'] == check_id)
    started = time.perf_counter_ns(); before = observe(root, s['genesis']['base']); process = None
    if before == digest(s['proposal']):
        cwd = root if spec['cwd'] == '.' else root / spec['cwd']
        safe_cwd = cwd.is_dir() and cwd.resolve().is_relative_to(root)
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            status = 'ERROR'; code = None
            if safe_cwd:
                try:
                    result = subprocess.run([sys.executable, *spec['argv'][1:]], cwd=cwd,
                                            stdout=stdout, stderr=stderr, timeout=spec['timeout_seconds'], shell=False)
                    status = 'EXITED'; code = result.returncode
                except subprocess.TimeoutExpired:
                    status = 'TIMEOUT'
                except OSError:
                    pass
            process = dict(status=status, exit_code=code, stdout=stream_receipt(stdout), stderr=stream_receipt(stderr))
    after = observe(root, s['genesis']['base'])
    task.append('check_finish', dict(id=check_id, before=before, after=after,
                                    process=process, elapsed_ns=time.perf_counter_ns()-started))
    return task.report(refresh=True)
