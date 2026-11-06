"""Verify repository integrity, tests, witness, and deliberately closed study gates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import tempfile

from test_receipts import validate_receipt

ROOT = Path(__file__).resolve().parents[1]


def checksum_inventory(relative: str) -> dict:
    inventory = ROOT / relative
    base = inventory.parent.resolve()
    checked = 0
    errors = []
    seen = set()
    try:
        lines = inventory.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise ValueError("empty checksum inventory")
        for number, line in enumerate(lines, 1):
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if not match:
                raise ValueError(f"invalid checksum record on line {number}")
            expected, name = match.groups()
            rel = PurePosixPath(name)
            if rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name:
                raise ValueError(f"unsafe inventory path: {name}")
            if name in seen:
                raise ValueError(f"duplicate inventory path: {name}")
            seen.add(name)
            target = (base / name).resolve()
            if not target.is_relative_to(base):
                raise ValueError(f"inventory path escapes root: {name}")
            if not target.is_file():
                errors.append("MISSING:" + name)
                continue
            checked += 1
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                errors.append("HASH_MISMATCH:" + name)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    return {"name": relative, "passed": not errors, "files_checked": checked, "errors": errors}


def run_step(name, args, cwd, *, expected_exit=0, json_checks=None, minimum_tests=None,
             require_no_skips=False):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "package")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["WAC_QA_PACKAGE"] = str(ROOT / "package")
    env["WAC_QA_EVAL"] = str(ROOT / "evaluation")
    observed = dict(name=name, command=["python", *args], cwd=cwd or ".",
                    expected_exit_code=expected_exit, tests_run=None, coverage=None)
    with tempfile.TemporaryDirectory(prefix="cortac-test-receipt-") as temporary:
        receipt = Path(temporary) / "result.json"
        command = [sys.executable, *args]
        if minimum_tests is not None:
            command = [sys.executable, str(ROOT / "scripts/test_receipts.py"),
                       "--receipt", str(receipt), "--", *args]
            observed["test_runner"] = "scripts/test_receipts.py"
        try:
            run = subprocess.run(command, cwd=ROOT / cwd, env=env, capture_output=True,
                                 text=True, encoding="utf-8", timeout=120)
            errors = []
            if run.returncode != expected_exit:
                errors.append(f"exit {run.returncode}; expected {expected_exit}")
            if minimum_tests is not None:
                try:
                    coverage = validate_receipt(json.loads(receipt.read_text(encoding="utf-8")))
                    observed["coverage"] = coverage
                    observed["tests_run"] = coverage["tests_run"]
                    if coverage["tests_run"] < minimum_tests:
                        errors.append(f"only {coverage['tests_run']} tests started; expected at least {minimum_tests}")
                    if coverage["tests_not_skipped"] == 0:
                        errors.append("no started test cases without a whole-case skip")
                    if not coverage["successful"]:
                        errors.append("unittest result unsuccessful")
                    if require_no_skips and coverage["skipped"]:
                        errors.append("strict coverage requires no skips")
                except (OSError, ValueError, TypeError) as exc:
                    errors.append("missing or invalid test receipt: " + str(exc))
            if json_checks:
                try:
                    result = json.loads(run.stdout)
                    for key, expected in json_checks.items():
                        if type(result.get(key)) is not type(expected) or result[key] != expected:
                            errors.append(f"unexpected JSON field: {key}")
                except (ValueError, TypeError) as exc:
                    errors.append("invalid JSON output: " + str(exc))
            return dict(observed, exit_code=run.returncode, passed=not errors, errors=errors,
                        stdout=run.stdout, stderr=run.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            # No completed receipt: unknown coverage, never fabricated zero work.
            return dict(observed, passed=False, errors=[str(exc)])


def git_state():
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=10)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        return {"revision": head.stdout.strip() if head.returncode == 0 else None,
                "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None}
    except (OSError, subprocess.TimeoutExpired):
        return {"revision": None, "dirty": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Optional JSON report; .local/ is ignored by Git")
    parser.add_argument("--require-no-skips", action="store_true", help="Fail any test stage with skipped cases, fixtures, or subtests")
    args = parser.parse_args()
    checks = [checksum_inventory("BUNDLE_SHA256SUMS"), checksum_inventory("evaluation/SHA256SUMS")]
    if (ROOT / "REPOSITORY_SHA256SUMS").exists():
        checks.append(checksum_inventory("REPOSITORY_SHA256SUMS"))
    # Do not run code after a failed delivered-integrity gate.
    if all(item["passed"] for item in checks):
        cases = [
            ("offline", ["-m", "unittest", "discover", "-s", "tests", "-v"], "package", {"minimum_tests": 458}),
            ("repository_task_demo", ["-m", "wac_offline.repository_task_v1.demo"], "", {"json_checks": {
                "schema": "cortac.repository-task-demo.v1", "authority": "NONE", "external_execution_enabled": False,
                "local_checks_passed": True, "supplied_assessments_pass": False,
                "independent_review_established": False, "real_model_calls": 0, "scored_study": False}}),
            ("scheduler_decision_demo", ["-m", "wac_offline.scheduler_v1.demo"], "", {"json_checks": {
                "schema": "cortac.scheduler.demo.v1", "authority": "NONE", "execution_enabled": False,
                "real_model_calls": 0, "network_calls": 0, "scored_study": False}}),
            ("scaffold_decision_demo", ["-m", "wac_offline.scaffold_v1.demo"], "", {"json_checks": {
                "schema": "cortac.scaffold.demo.v1", "authority": "NONE", "execution_enabled": False,
                "real_model_calls": 0, "network_calls": 0, "scored_study": False}}),
            ("registrar_source", ["scripts/check_registrar_source.py"], "", {"json_checks": {"insertion_only_revision": True}}),
            ("amendment_demo", ["scripts/amendment_demo.py"], "", {"json_checks": {"authority": "NONE", "execution_enabled": False, "old_authority_is_current": False}}),
            ("contested_amendment_demo", ["scripts/contested_amendment_demo.py"], "", {"json_checks": {"authority": "NONE", "execution_enabled": False, "replacement_activated": True, "invalidation_repaired": True, "unrelated_hold_preserved": True}}),
            ("scratch_runner_integration", ["scripts/runner_integration.py"], "", {"json_checks": {
                "schema": "cortac.scratch.integration.v1", "episodes": 16, "scenarios": 8,
                "real_model_calls": 0, "real_external_principals": 0, "scored_study": False,
                "external_execution_enabled": False, "actual_disposable_database_effects": True}}),
            ("bounded_complaint_triage", ["scripts/triage_integration.py"], "", {"json_checks": {
                "schema": "cortac.scratch.triage.integration.v1", "episodes": 15, "authority": "NONE",
                "controller_closure": "SUPPLIED_UNVERIFIED", "real_model_calls": 0,
                "real_external_principals": 0, "scored_study": False,
                "external_execution_enabled": False, "all_expected_outcomes": True}}),
            ("opr_structural_controls", ["scripts/opr_integration.py"], "", {"json_checks": {
                "schema": "cortac.opr.controls.v1", "controls": 18,
                "all_fixed_structural_outcomes": True, "authority": "NONE",
                "execution_enabled": False, "controller_closure": "SUPPLIED_UNVERIFIED",
                "semantic_assessment": "NOT_PERFORMED", "opr_acceptance_established": False}}),
            ("ops_supplied_trace_controls", ["scripts/ops_integration.py"], "", {"json_checks": {
                "schema": "cortac.ops.controls.v1", "controls": 29,
                "all_fixed_structural_outcomes": True, "authority": "NONE",
                "execution_enabled": False, "real_model_calls": 0,
                "real_external_principals": 0, "semantic_assessment": "NOT_PERFORMED",
                "empirical_success_established": False, "synthetic_inputs": True}}),
            ("sandbox_controls", ["-m", "unittest", "discover", "-s", "sandbox", "-p", "test_runner.py", "-v"], "", {"minimum_tests": 13}),
            ("sandbox_replay", ["sandbox/verify_replay.py"], "", {}),
            ("evaluation", ["-m", "unittest", "discover", "-s", "tests", "-v"], "evaluation", {"minimum_tests": 52}),
            ("assignment_adversarial", ["verification/assignment_adversarial.py"], "", {"minimum_tests": 11}),
            ("evaluation_adversarial", ["verification/evaluation_adversarial.py"], "", {"minimum_tests": 6}),
            ("witness", ["scripts/wac.py", "verify", "--profile", "package/inputs/profile.extracted.json",
                         "--roster", "package/fixtures/feasible.json", "--certificate", "package/results_v2/assignment.json"], "",
             {"json_checks": {"status": "SYNTHETIC_WITNESS_VALID", "authority": "NONE", "execution_enabled": False}}),
            ("lottery", ["scripts/wac.py", "lottery", "--profile", "package/inputs/profile.extracted.json",
                         "--roster", "package/fixtures/feasible.json", "--roll", "package/results_v2/lottery_roll.json",
                         "--seed", "0" * 64], "",
             {"json_checks": {"status": "SYNTHETIC_LOTTERY_COMPLETE", "authority": "NONE", "execution_enabled": False}}),
            ("readiness", ["evaluation/readiness.py"], "",
             {"json_checks": {"verdict": "SOURCE_GATED_NO_SCORED_RUN", "offline_integrity_passed": True, "scored_run_ready": False}}),
            ("scored_readiness_refusal", ["evaluation/readiness.py", "--require-scored-ready"], "",
             {"expected_exit": 2, "json_checks": {"scored_run_ready": False, "offline_integrity_passed": True}}),
            ("scored_analysis_refusal", ["evaluation/analyze.py", "--mode", "scored"], "", {"expected_exit": 2}),
        ]
        for name, command, cwd, kwargs in cases:
            item = run_step(name, command, cwd, require_no_skips=args.require_no_skips, **kwargs)
            # An argparse/usage error must not masquerade as the scored gate.
            if name == "scored_analysis_refusal" and "SOURCE_GATED" not in item.get("stderr", "") + item.get("stdout", ""):
                item["passed"] = False
                item["errors"].append("scored refusal reason missing")
            checks.append(item)
            print(("PASS" if item["passed"] else "FAIL") + " " + name, flush=True)
    passed = all(item["passed"] for item in checks)
    report = {"schema": "cortac.repository_verification.v2", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python_version": platform.python_version(), "platform": platform.system(),
              "git": git_state(), "passed": passed, "tests_run": sum(item.get("tests_run") or 0 for item in checks),
              "tests_not_skipped": sum((item.get("coverage") or {}).get("tests_not_skipped", 0) for item in checks),
              "skips": sum(len((item.get("coverage") or {}).get("skipped", [])) for item in checks),
              "coverage_observed_stages": sum(item.get("coverage") is not None for item in checks),
              "require_no_skips": args.require_no_skips,
              "checks": checks, "real_model_calls": 0, "agent_trials": 0, "github_actions_run_verified": False,
              "scope": "Local repository software checks only; no authority or study-readiness claim"}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{'PASS' if passed else 'FAIL'}: {report['tests_run']} tests; {report['skips']} skips; {len(checks)} verification stages")
    if not passed:
        for item in checks:
            if not item["passed"]:
                print(json.dumps(item, indent=2), file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
