"""Replay the frozen scripted experiment; no agent-performance claim."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def main():
    frozen = json.loads((ROOT / "freeze.json").read_text(encoding="utf-8"))
    for name, digest in frozen["sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Frozen file modified: " + name)
    expected = json.loads((ROOT / "expected_outputs.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="cortac-sandbox-") as folder:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env.pop("PYTHONOPTIMIZE", None)
        subprocess.run([sys.executable, str(ROOT / "runner.py"), "--output", folder],
                       check=True, env=env, timeout=120)
        output = Path(folder)
        for name, digest in expected["sha256"].items():
            data = (output / name).read_bytes().replace(b"\r\n", b"\n")
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("Replay differs from observed output: " + name)
        receipt = json.loads((output / "runtime.json").read_text(encoding="utf-8"))
        for key, value in {"episodes": expected["episodes"],
                           "paired_environments": expected["paired_environments"],
                           "model_calls": 0, "model_tokens": 0,
                           "invariants_passed": True}.items():
            if type(receipt.get(key)) is not type(value) or receipt[key] != value:
                raise ValueError("Unexpected runtime receipt: " + key)
    print("PASS: frozen inputs and six deterministic outputs; scripted simulation only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
