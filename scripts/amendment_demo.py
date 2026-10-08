"""Replay one fabricated amendment example. No authority or external effect."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'package'))
from wac_offline.amendments import AmendmentReplay


def main():
    data = json.loads((ROOT / 'package/fixtures/amendment_example.json').read_text(encoding='utf-8'))
    replay = AmendmentReplay(data['policy'])
    before = replay.state()
    registration = replay.register(data['proposal'], data['approval'], data['procedure'], 'registrar', 20)
    activation = replay.activate(registration, 30)
    print(json.dumps({'example': 'FABRICATED_OFFLINE_FIXTURE', 'before': before,
                      'registration': registration, 'activation': activation, 'after': replay.state(),
                      'old_authority_is_current': replay.is_current(before['policy_digest'], before['epoch']),
                      'authority': 'NONE', 'execution_enabled': False}, indent=2))


if __name__ == '__main__':
    main()
