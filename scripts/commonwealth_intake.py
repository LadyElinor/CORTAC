"""Read-only Commonwealth A1 intake and explicit Vanguard pair inspection."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.commonwealth_intake_v1 import main

if __name__ == '__main__':
    raise SystemExit(main())
