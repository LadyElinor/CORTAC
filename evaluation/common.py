"""Small strict JSON and integrity helpers; not an authority/JCS implementation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARMS = ['minimal_single_coordinator_team', 'ordinary_role_separated_team', 'full_commonwealth']
FAMILIES = ['benign_cooperation', 'conflicting_legitimate_priorities', 'strategic_abstention', 'resource_withdrawal_during_appeal', 'shared_false_evidence', 'fresh_agents_under_conflicted_control', 'reviewer_and_resource_shortages', 'admitted_cell_split', 'routine_envelope_drift']
ABLATIONS = {'material_control_appeal_exclusion': 'fresh_agents_under_conflicted_control', 'inherited_cell_weight': 'admitted_cell_split', 'authorization_checked_classification': 'routine_envelope_drift', 'independent_review_continuity_grant': 'resource_withdrawal_during_appeal'}
SPLITS = {'development': 2, 'analysis_smoke': 2, 'proposed_main': 20}
SEED_ROOT = 'WAC_EVAL_0_2_AUTHOR_PROPOSAL_2026_10_04_V1'
ANALYSIS_SEED = 2026100402


def duplicate_reject(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=duplicate_reject, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON number: ' + x)))


def read(path):
    return loads(Path(path).read_text(encoding='utf-8'))


def read_jsonl(path):
    return [loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def stable_bytes(value):
    # This is a local fixture format. It does not claim RFC 8785 JCS conformance.
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(stable_bytes(value)).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seed_for(*parts):
    return int(hashlib.sha256('|'.join([SEED_ROOT, *map(str, parts)]).encode()).hexdigest()[:12], 16)


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Byte-bound fixtures must not pass through Windows text newline translation.
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'
    path.write_bytes(data.encode('utf-8'))


def write_jsonl(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b''.join(stable_bytes(v) for v in values))
