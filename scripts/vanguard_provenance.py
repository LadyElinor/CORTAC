"""Inspect local provenance inputs. See docs/VANGUARD_PROVENANCE_V1.md."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.vanguard_provenance_v1 import main

if __name__ == '__main__':
    raise SystemExit(main())
