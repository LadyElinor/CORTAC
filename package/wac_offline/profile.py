"""Fail-closed acceptance of the one reviewed v0.2 design-profile baseline.

This is not a general JSON Schema validator, signed adoption verifier or loader.
Unknown/missing keys, changed types and unsupported values fail closed. Object
key order is irrelevant; arrays retain order. Actual source bytes stay separate.
"""
from pathlib import Path
from .io import read

BASELINE = Path(__file__).parent / 'data' / 'profile_baseline.json'

def validate_profile(profile):
    expected = read(BASELINE)
    errors = []
    def compare(actual, reference, path):
        if type(actual) is not type(reference):
            errors.append({'code': 'TYPE_MISMATCH', 'path': path,
                           'expected_type': type(reference).__name__})
            return
        if isinstance(reference, dict):
            for key in sorted(reference.keys() - actual.keys()):
                errors.append({'code': 'MISSING_FIELD', 'path': f'{path}.{key}'})
            for key in sorted(actual.keys() - reference.keys()):
                errors.append({'code': 'UNSUPPORTED_FIELD', 'path': f'{path}.{key}'})
            for key in sorted(actual.keys() & reference.keys()):
                compare(actual[key], reference[key], f'{path}.{key}')
        elif isinstance(reference, list):
            if len(actual) != len(reference):
                errors.append({'code': 'UNSUPPORTED_ARRAY_LENGTH', 'path': path})
            for i, (a, b) in enumerate(zip(actual, reference)):
                compare(a, b, f'{path}[{i}]')
        elif actual != reference:
            errors.append({'code': 'UNSUPPORTED_VALUE', 'path': path, 'expected': reference})
    compare(profile, expected, '$')
    return {
        'status': 'INVALID_OR_UNSUPPORTED_PROFILE' if errors else 'VALID_SUPPORTED_PROFILE',
        'scope': 'exact_v0.2_baseline_structure_and_values_object_order_agnostic',
        'errors': errors,
        'authority_status': 'UNINITIALIZED_NO_EXECUTION',
        'execution_enabled': False,
        'not_checked': ['original_artifact_byte_identity', 'DOCX_JSON_full_correspondence',
                        'RFC8785_or_signatures', 'runtime_authority', 'mission_readiness'],
    }
