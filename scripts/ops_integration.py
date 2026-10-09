"""Report exposed OPS1 supplied-trace controls, not institutional outcomes."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.ops_fixtures_v1 import integration_report

if __name__ == '__main__':
    report = integration_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report['all_fixed_structural_outcomes'] else 1)
