"""Exercise the two audited simulation payloads against pinned external source checkouts."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

from check_agent_controls import check, unique_names

NAV2 = '94d1c2a345dda6ff637e6a72c9101d927ee99f19'
WEEVIL_BASELINE = '84904cbea653b98b85d3a012dc3806c62761c884'
WEEVIL = '51a818f0405ca0c6ef27e4b8a192b1649197939c'


def verify_checkout(root, commits, subpath):
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if head not in commits:
        raise ValueError(f'checkout must be at one of {commits}')
    changed = subprocess.check_output(
        ['git', '-C', str(root), 'status', '--porcelain', '--', subpath], text=True)
    if changed.strip():
        raise ValueError(f'checkout contains local changes under {subpath}')
    return head


def nav2_roundtrip(payload, root):
    from rosbags.typesys import Stores, get_types_from_msg, get_typestore

    path = 'nav2_msgs/action/NavigateToPose.action'
    verify_checkout(root, (NAV2,), path)
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


def check_weevil_samples(trace, scenario, revision):
    """Reconcile the persisted rows with the approved scenario and selected producer."""
    metadata = trace['metadata']
    summary = trace['summary']
    duration = scenario.get('duration_s', 2.0)
    dt = scenario.get('timestep_s', 0.001)
    count = max(1, round(duration / dt))
    steps = trace['steps']
    if (revision not in (WEEVIL_BASELINE, WEEVIL) or summary['completed'] is not True or
            metadata['scenario_id'] != scenario['scenario_id'] or metadata['duration_s'] != duration or
            metadata['timestep_s'] != dt or len(steps) != count or type(summary['total_steps']) is not int or
            summary['total_steps'] != count):
        raise ValueError('Lunar Weevil trace does not match the approved run')
    for index, sample in enumerate(steps):
        time_s = sample['time_s']
        if (type(sample['step']) is not int or sample['step'] != index or
                type(time_s) not in (int, float) or
                not math.isclose(time_s, (index + 1) * dt, rel_tol=1e-10, abs_tol=dt * 1e-8)):
            raise ValueError('unexpected simulation sample index or time')
    elapsed = steps[-1]['time_s']
    verified_geometry = revision == WEEVIL
    if verified_geometry:
        if (metadata['sampling_phase'] != 'post_step' or metadata['elapsed_s'] != elapsed or
                metadata['requested_slope_deg'] != scenario['slope_deg'] or
                not math.isclose(metadata['applied_slope_deg'], scenario['slope_deg'], abs_tol=1e-10) or
                metadata['applied_gravity_m_s2'] != [0.0, 0.0, -scenario['gravity_m_s2']]):
            raise ValueError('applied simulation settings differ from the approved scenario')
    return dict(weevil_revision=revision, mujoco=metadata['engine_version'], steps=count,
                simulated_seconds=elapsed, requested_seconds=duration, geometry_readback_verified=verified_geometry)


def weevil_trace(payload, root):
    revision = verify_checkout(root, (WEEVIL_BASELINE, WEEVIL), 'weevil-lunar/simulators')
    # Isolate imports so sequential checks of different pinned checkouts use their own modules.
    program = """import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from simulators.common.scenario_schema import SimulationScenario
from simulators.mujoco.trace_harness import run_trace
path, _ = run_trace(SimulationScenario(**json.load(sys.stdin)), output_root=Path(sys.argv[2]))
print(path)
"""
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run([sys.executable, '-I', '-c', program, str(root / 'weevil-lunar'), directory],
                                input=json.dumps(payload['scenario']), capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('Weevil trace failed: ' + result.stderr)
        path = Path(result.stdout.strip()).resolve()
        if not path.is_relative_to(Path(directory).resolve()):
            raise ValueError('unexpected trace location')
        trace = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_names)
    return check_weevil_samples(trace, payload['scenario'], revision)


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
