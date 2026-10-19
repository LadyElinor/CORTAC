"""Inspect a local Vanguard review packet. See docs/VANGUARD_OFFLINE_V1.md."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.vanguard_review_v1 import main

if __name__ == '__main__':
    raise SystemExit(main())
