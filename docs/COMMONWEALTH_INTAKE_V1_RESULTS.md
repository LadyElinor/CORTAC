# Commonwealth intake v1: executed validation

Observed on October 31, 2026, Linux, Python 3.12.14. Adapter version:
`commonwealth-vanguard-intake-1.0.0`. The CORTAC base was
`4a83d80c39d20438daedb5fbbce61720a4c921e2`; tests ran with the adapter changes in
the working tree. The independently checked Commonwealth checkout was clean at
`5d268390abca2ba69061c2f667161c0316b12802` (`authority-1.0.0`). See the
[input provenance and hashes](../provenance/commonwealth_intake_v1.json) and
[machine-readable validation receipt](../provenance/commonwealth_intake_validation.json).

| Executed check | Observed result |
| --- | --- |
| CORTAC `python scripts/verify.py --report .local/commonwealth-verification.json` | **622 tests; 23 verification stages passed**, including 33 new adapter regressions and the existing integrity, assignment, review, sandbox, remedy and closed study-gate checks. |
| `python scripts/commonwealth_integration.py --commonwealth-checkout ../unfinished-commonwealth` | **58 A1 comparison controls matched** acceptance/rejection, canonical packet digest and missing-field results against A1's actual validator; **20 existing Vanguard controls** retained their expected outcomes through the new adapter. |
| Commonwealth `python scripts/verify.py` | **403 tests passed**, with packaged JSON and local documentation-link checks. This is the unmodified reference checkout, not a new Commonwealth implementation. |
| `python -m pip wheel --no-deps --no-build-isolation . --wheel-dir .local/wheel` | Wheel built from the changed CORTAC tree without fetching dependencies. |
| Install wheel in a fresh virtual environment with `pip install --no-index --no-deps`; run outside both checkouts | Imported the installed adapter from `site-packages`; preserved `NONE`/false and the incomplete pair result; module CLI returned 3 for a valid intake without provenance; all 20 installed Vanguard controls matched. |
| Repository preservation | Original bundle/evaluation hashes and the frozen OPR baseline pass. Existing A1/Vanguard/OPS1 validators and fixtures remain byte-identical. The new Terra-compatible fixture is byte-identical to A1's pinned export. |

The initial verification stopped at the repository inventory for the three
deliberate documentation/runner/workflow edits. A subsequent test run detected
that the original CI workflow was frozen by the OPR preservation test. The
workflow was restored byte-for-byte and the new cross-project workflow added
separately; no preservation expectation was weakened. The final local run passes.
Only reviewed changed/new paths are reflected in `REPOSITORY_SHA256SUMS`; the
historical inventories are unchanged.

## What the controls demonstrate

- All 23 answer strings, absent/blank fields, four exact enums, public/working/
  analyst contexts, source status, dissent and declared authority survive intake
  without completing an evidence inventory or creating a reviewer.
- Unknown fields/versions, wrong types, malformed/duplicate-key/nonfinite JSON,
  invalid dates, bounds violations and altered authority flags are rejected.
- Missing source provenance remains visible even beside a structurally consistent
  Vanguard record. Supplied original-artifact hashes remain explicitly unverified.
- Stale packet/context/link digests, changed A1 material, stale inventories,
  changed target drafts/reviews and incompatible case/policy/predecessor bindings
  are rejected. Declared synthetic inputs cannot be paired as nonsynthetic cases.
- Vanguard objection, identity, controller, cutoff and missing-review blockers
  propagate. Intake dissent remains present even where the target declares no
  objections. No semantic claim says the target addressed that dissent.
- Read-only APIs leave inputs unchanged; guard tests prohibit network, database,
  process and file access. The CLI creates no files. Intake/inspection envelopes
  are rejected as A1, Vanguard and OPS1 inputs rather than usable effect tokens.
- Authorization-stage labels, expiry/revocation wording and emergency prose do
  not grant authority. Every valid intake/pair remains incomplete and execution
  disabled; malformed CLI input also returns `authority: NONE` and false.

## What remains unestablished

These are authored, exposed development controls. The Terra and Vanguard sample
decisions are unrelated: pairing them tests explicit byte binding, not successful
conversion of one real case. There are no live Terra/Relay API calls, model trials,
original-source authentication, trusted timestamps, actual independent reviews,
established controller independence, verified mandates or governance ratification.

Jointly rewriting caller records and their hashes can still pass structural
inspection. The negative control also preserves Vanguard's acceptance of
nonsensical but nonblank counterargument prose. Both still produce an incomplete
pair with semantic and independent-evidence obligations. A hash mismatch is an
integrity signal; matching hashes do not authenticate people, facts or authority.

No external execution interface exists. The charter remains an unratified draft.
Publication of this branch or a passing CI job does not approve a study, grant
operational authority or establish a protected merge requirement. This receipt
records local execution only; hosted checks are reported separately on the PR.
