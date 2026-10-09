"""Run separately versioned bounded complaint controls, never a scored study."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.triage_fixtures import integration_report

if __name__ == '__main__':
    print(json.dumps(integration_report(), indent=2, sort_keys=True))
