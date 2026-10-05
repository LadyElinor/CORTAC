"""Run the bundled offline CLI without installation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "package"))
from wac_offline.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
