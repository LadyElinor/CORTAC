"""Emit observed synthetic agent-control traces as JSON. Read with check_agent_controls.py."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'package'))
from wac_offline.agent_controls import report


if __name__ == '__main__':
    print(json.dumps(report(), sort_keys=True, indent=2))
