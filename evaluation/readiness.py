"""Fail closed: integrity checks do not ratify a design or validate signatures."""
import argparse
import re
from collections import Counter
from pathlib import Path
from common import ROOT, ARMS, FAMILIES, ABLATIONS, SPLITS, read, read_jsonl, digest, file_digest, write


def check_integrity(root=ROOT):
    root = Path(root)
    failures = []
    m = read(root / 'proposed_run_manifest.json')
    for name, sha in m.get('scaffold_artifact_digests', {}).items():
        if not (root/name).is_file() or file_digest(root/name) != sha: failures.append('SCAFFOLD_ARTIFACT_DIGEST_MISMATCH:' + name)
    inv = read(root / 'fixtures/fixture_inventory.json')
    proposal = m['local_author_proposals']
    if proposal['fixture_inventory'] != inv:
        failures.append('MANIFEST_FIXTURE_INVENTORY_MISMATCH')
    for relative, expected in inv['files'].items():
        path = root / 'fixtures' / relative
        if not path.is_file() or file_digest(path) != expected:
            failures.append('FIXTURE_DIGEST_MISMATCH:' + relative)
    for relative, key in [('generate_fixtures.py','generator_sha256'), ('common.py','generator_support_sha256')]:
        if file_digest(root / relative) != proposal[key]:
            failures.append('GENERATOR_DIGEST_MISMATCH:' + relative)
    if file_digest(root / proposal['seed_lists_file']) != proposal['seed_lists_sha256']:
        failures.append('SEED_LIST_DIGEST_MISMATCH')
    seeds = set(); task_ids = set()
    for split, count in SPLITS.items():
        tasks = read_jsonl(root / 'fixtures/model_inputs' / (split + '.jsonl'))
        keys = read_jsonl(root / 'fixtures/evaluator_only' / (split + '_keys.jsonl'))
        slots = read_jsonl(root / 'fixtures/evaluator_only' / (split + '_schedule.jsonl'))
        task_map = {t['task_id']: t for t in tasks}
        if len(task_map) != 9 * count or len(tasks) != 9 * count or len(keys) != 9 * count:
            failures.append('BAD_CASE_COUNT:' + split)
        for task in tasks:
            if task['task_id'] in task_ids: failures.append('CROSS_SPLIT_CASE_REUSE')
            task_ids.add(task['task_id'])
            def scan(v):
                if isinstance(v, dict):
                    for k, value in v.items():
                        if k in {'family','hidden_truth','required_observations','expected_status','authorized_useful_target','fixture_seed'}: failures.append('MODEL_INPUT_KEY_LEAK:' + k)
                        scan(value)
                elif isinstance(v, list):
                    for value in v: scan(value)
            scan(task)
        if Counter(k['family'] for k in keys) != Counter({fam: count for fam in FAMILIES}): failures.append('BAD_FAMILY_ALLOCATION:' + split)
        for family in FAMILIES:
            indices=[k['paired_index'] for k in keys if k['family']==family]
            if sorted(indices) != list(range(count)): failures.append('BAD_PAIRED_INDICES:' + split + ':' + family)
        if len({k['task_id'] for k in keys}) != len(keys): failures.append('DUPLICATE_ORACLE_KEY')
        seen_slots = set()
        for key in keys:
            if key['fixture_seed'] in seeds: failures.append('CROSS_SPLIT_SEED_REUSE')
            seeds.add(key['fixture_seed'])
            if key['task_id'] not in task_map or digest(task_map[key['task_id']]) != key['task_input_sha256']:
                failures.append('TASK_ORACLE_BINDING_MISMATCH')
            grouped = [s for s in slots if s['task_id'] == key['task_id']]
            expected_arms = set(ARMS + ['ablate_' + name for name, fam in ABLATIONS.items() if fam == key['family']])
            if {s['arm'] for s in grouped} != expected_arms or len(grouped) != len(expected_arms): failures.append('BROKEN_ARM_PAIRING')
            if sorted(s['within_pair_order'] for s in grouped) != list(range(len(expected_arms))): failures.append('BAD_WITHIN_PAIR_ORDER')
            if {s['budget_profile_id'] for s in grouped} != {'AUTHOR_PROPOSED_MATCHED_V1'}: failures.append('MISMATCHED_BUDGET_PROFILE')
            for s in grouped:
                if s['slot_id'] in seen_slots: failures.append('DUPLICATE_SLOT')
                seen_slots.add(s['slot_id'])
                for field in ['family','split','paired_index','model_seed_proposal','task_input_sha256']:
                    if s[field] != key[field]: failures.append('MISMATCHED_PAIRED_FIELD:' + field)
        if len(slots) != count * 31 or len(seen_slots) != len(slots): failures.append('BAD_SCHEDULE_COUNT:' + split)
    main = m['design_inherited_from_v02']
    if (main['unique_main_case_count'],main['main_arm_execution_slots'],main['ablation_execution_slots']) != (180,540,80): failures.append('DESIGN_COUNT_MISMATCH')
    return sorted(set(failures))


def assess(root=ROOT):
    root = Path(root)
    m = read(root/'proposed_run_manifest.json')
    blockers = ['SCORED_RUNNER_AND_TRUST_VERIFIER_NOT_IMPLEMENTED_IN_THIS_SCAFFOLD', 'EXPOSED_FIXTURES_ARE_NOT_SEALED_HOLDOUTS', 'AUTHOR_PROPOSALS_NOT_INDEPENDENTLY_APPROVED']
    for source in m['source_baseline']:
        if not isinstance(source['original_file_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['original_file_sha256']):
            blockers.append('ORIGINAL_ARTIFACT_BYTES_UNVERIFIED:' + source['role'])
    def incomplete(value):
        if value is None or value is False: return True
        if isinstance(value, str):
            return not value.strip() or value.strip().lower() in {'tbd','todo','pending','unknown','placeholder','not_implemented'}
        if isinstance(value, dict): return not value or any(incomplete(v) for v in value.values())
        if isinstance(value, list): return not value or any(incomplete(v) for v in value)
        return False
    for field, value in m['real_run_requirements'].items():
        invalid_digest = 'digest' in field or 'sha256' in field
        def valid_digests(v):
            if isinstance(v, dict): return bool(v) and all(valid_digests(x) for x in v.values())
            return isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) is not None
        if incomplete(value) or (invalid_digest and not valid_digests(value)):
            blockers.append('MISSING_OR_INVALID_REAL_RUN_REQUIREMENT:' + field)
    if not m['signed']: blockers.append('UNSIGNED_MANIFEST')
    if not m['frozen_for_scoring']: blockers.append('MANIFEST_NOT_FROZEN')
    if m['local_author_proposals']['acceptance_proposal']['deployment_acceptance_thresholds'] is None:
        blockers.append('DEPLOYMENT_ACCEPTANCE_THRESHOLDS_UNSET')
    failures = check_integrity(root)
    return {'verdict':'SOURCE_GATED_NO_SCORED_RUN', 'offline_integrity_passed':not failures, 'integrity_failures':failures, 'scored_run_ready':False, 'preregistered':False, 'blockers':blockers, 'warning':'Editing proposal booleans or filling strings never grants authority. This tool does not verify signatures, actual control independence, live isolation, model execution or deployment readiness.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--require-scored-ready',action='store_true')
    args=parser.parse_args(); result=assess(args.root)
    if args.out: write(args.out,result)
    import json
    print(json.dumps(result,indent=2))
    raise SystemExit(2 if args.require_scored_ready or result['integrity_failures'] else 0)
