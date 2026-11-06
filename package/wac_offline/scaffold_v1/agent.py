"""A constant-method conformance agent. No host, filesystem or credentials API."""
import sys
from . import ap1
from .wire import MAX_BYTES, canonical, parse


def decide(brief):
    if brief.get('profile') != ap1.PROFILE_1_1 or brief.get('role') != 'workshop-proposer':
        raise ValueError('unsupported role/profile')
    choice = dict(profile=brief['profile'], brief_id=brief['brief_id'])
    if ('quality-stream' not in brief['work']['methods'] or not brief['attempts_remaining']
            or brief['work']['halted'] or brief['work']['successor_observation_required']):
        return dict(choice, choice='decline', reason='No available constant-method proposal.')
    return dict(choice, choice='propose', method='quality-stream',
                prediction={'primary_correct': 0.5, 'peer_on_time': 0.5},
                purpose='Constant-method conformance example; forecasts are uncalibrated.')


if __name__ == '__main__':
    try:
        print(canonical(decide(parse(sys.stdin.buffer.read(MAX_BYTES+1)))))
    except (ValueError, KeyError, TypeError):
        raise SystemExit(2)
