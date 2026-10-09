"""Report fixed OPR1 structural controls without semantic or operational claims."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.opr_fixtures_v1 import integration_report

if __name__ == '__main__':
    print(json.dumps(integration_report(), indent=2, sort_keys=True))
