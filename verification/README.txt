VERIFICATION SUMMARY
4 October 2026

Final delivery copy passed:
  55 offline assignment/profile/governance regression tests
  49 evaluation fixture/metrics/analysis/readiness tests
  11 independently authored assignment adversarial tests
   6 independently authored evaluation adversarial tests
 121 passing software checks total

The 27 evaluation file checksums all matched. The supplied assignment witness was rechecked successfully. Both study-readiness and scored-analysis requests correctly exited with code 2. These are software checks, not 121 agent trials or evidence of collective-intelligence performance.

The independent scripts were made portable by resolving sibling paths relative to this verification directory. Only path setup changed; all 17 independent tests were rerun afterward. From the bundle root:
  python3 verification/assignment_adversarial.py
  python3 verification/evaluation_adversarial.py
On Windows use py -3 in place of python3.

See package_tests.txt, evaluation_tests.txt, assignment_results.txt, evaluation_results.txt, witness_check.json, evaluation_checksums.txt and scored_gates.txt for recorded outcomes. Readiness remains explicitly gated; no signed adoption or real-model study was performed.
