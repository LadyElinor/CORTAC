"""Exercise the two audited simulation payloads against pinned external source checkouts."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from check_agent_controls import check, unique_names

NAV2 = '94d1c2a345dda6ff637e6a72c9101d927ee99f19'
WEEVIL = '84904cbea653b98b85d3a012dc3806c62761c884'


def verify_checkout(root, commit, subpath):
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if head != commit:
        raise ValueError(f'checkout must be at {commit}')
    changed = subprocess.check_output(
        ['git', '-C', str(root), 'status', '--porcelain', '--', subpath], text=True)
    if changed.strip():
        raise ValueError(f'checkout contains local changes under {subpath}')


def nav2_roundtrip(payload, root):
    from rosbags.typesys import Stores, get_types_from_msg, get_typestore

    path = 'nav2_msgs/action/NavigateToPose.action'
    verify_checkout(root, NAV2, path)
    goal_definition = (root / path).read_text(encoding='utf-8').split('---')[0]
    store = get_typestore(Stores.ROS2_JAZZY)
    name = 'nav2_msgs/msg/NavigateToPose_Goal'
    store.register(get_types_from_msg(goal_definition, name))

    def message(type_name, values):
        fields = {}
        for field, (_, subtype) in store.fielddefs[type_name][1]:
            value = values[field]
            fields[field] = message(subtype, value) if isinstance(value, dict) else value
        if set(fields) != set(values):
            raise ValueError(f'message fields differ for {type_name}')
        return store.types[type_name](**fields)

    goal = message(name, payload['goal'])
    wire = store.serialize_cdr(goal, name)
    if store.deserialize_cdr(wire, name) != goal:
        raise ValueError('Nav2 goal changed after CDR serialization')
    return dict(nav2_revision=NAV2, serialized_bytes=len(wire), cdr_round_trip=True)


def weevil_trace(payload, root):
    verify_checkout(root, WEEVIL, 'weevil-lunar/simulators')
    sys.path.insert(0, str(root / 'weevil-lunar'))
    from simulators.common.scenario_schema import SimulationScenario
    from simulators.mujoco.trace_harness import run_trace

    scenario = SimulationScenario(**payload['scenario'])
    with tempfile.TemporaryDirectory() as directory:
        path, _ = run_trace(scenario, output_root=Path(directory))
        trace = json.loads(path.read_text(encoding='utf-8'))
    count = len(trace['steps'])
    expected = round(scenario.duration_s / scenario.timestep_s)
    if (not trace['summary']['completed'] or count != expected or
            trace['summary']['total_steps'] != expected or
            abs(trace['steps'][-1]['time_s'] - scenario.duration_s) > scenario.timestep_s / 2):
        raise ValueError('Lunar Weevil trace incomplete')
    return dict(weevil_revision=WEEVIL, mujoco=trace['metadata']['engine_version'],
                steps=count, simulated_seconds=scenario.duration_s)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--nav2', type=Path, required=True, help='Jazzy Navigation2 checkout')
    parser.add_argument('--weevil', type=Path, required=True, help='PerhapsThisBugWillDo checkout')
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'), object_pairs_hook=unique_names)
    check(report)
    commands = {r['inputs']['profile']: r['state']['simulated_commands'][0]
                for r in report['rows'] if r['inputs']['case'] == 'approved'}
    results = dict(nav2=nav2_roundtrip(commands['space_ros'], args.nav2.resolve()),
                   lunar_weevil=weevil_trace(commands['lunar_weevil'], args.weevil.resolve()))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
