# R1 bounded recursive maintenance

CORTAC now admits scoped repository proposals through R1 and has used that
lifecycle to repair its own verification coverage. This is an exposed engineering
exercise with one assistant/operator, not a comparative efficacy experiment.

The [design freeze](REPOSITORY_TASK_V1_DESIGN.md) was committed before R1 was
implemented. It allowed two rounds plus repairs of demonstrated counterexamples:
R1 conformance, followed by one maintenance task. No general self-modification
loop, new governance authority, or automatic merge was introduced.

## Observed sequence

| Step | Source | Observation |
| --- | --- | --- |
| Design | `6023eba` | Contract, checks and stopping rule recorded |
| R1 implementation | `0fcd6e9` | 32 new tests; 657 total tests across 24 stages; installed demo passed |
| Coverage baseline | `0fcd6e9` | A wholly skipped one-test suite was accepted by the console-count verifier |
| R1 maintenance candidate | `8c308a6` | 18 coverage regressions and all 675 tests passed without skips on local Linux |
| Cross-platform counterexample | [Windows CI](https://github.com/LadyElinor/CORTAC/actions/runs/42267648034) | An unignored journal inside candidate source was accepted; existing test failed |
| Linked path repair | `8275b99` | A symlink-parent alias reproduced the bypass; canonical parent resolution fixed it; 34 R1 tests and 677 total tests passed locally without skips |

The Windows short/long parent-path explanation is an inference from the failing
containment check and implementation. A separate Linux symlink-parent control
reproduced the same lexical-versus-resolved-path defect. A `..` parent control
**did not** reproduce it; both outcomes are retained. The repair resolves parent
aliases while preserving refusal of a symlink at the journal filename itself.

Both maintenance tasks were created and begun before their candidate edits.
A wheel installed at a separate path supplied the original R1 custodian, with
`-I` used for its Python entry point. Candidate tests deliberately used candidate
source. This is version separation under one OS owner, not independent custody.
The repair task refers to its predecessor's report digest; it does not erase the
old result, transfer authority, or establish causal efficacy of the scaffold.

A subsequent [Windows run of the path repair](https://github.com/LadyElinor/CORTAC/actions/runs/42268407011)
reached the verifier's 120-second offline-stage limit. It correctly reported
unknown coverage, not a pass; that run does not establish Windows conformance.
As a separate CI maintenance adjustment after the two recorded tasks, the larger
offline suite now has an explicit 240-second ceiling, and timeout diagnostics
retain partial output without inferring test counts. R1's individual task-check
limit remains 120 seconds. The original task receipts and their counts are unchanged.

## Verification coverage contract

`scripts/verify.py` now emits `cortac.repository_verification.v2`. Historical
reports remain unchanged. Five test stages use `scripts/test_receipts.py`, whose
actual `unittest` results supply started-case counts, wholly skipped started
cases, every skip and its reason, failures, errors, expected failures, unexpected
successes, and success status. Discovery floors remain in force. The prior
console-count `tests_run` field now means cases started by unittest.

Empty and wholly skipped suites fail. A process that exits successfully before
writing its fresh receipt has **unknown coverage**, not zero-cost success.
Printed claims such as `Ran 999 tests` cannot satisfy a minimum. Each invocation
has a fresh receipt location; no previous receipt is reused. Module/class setup
skips and skipped subtests are retained without subtracting unstarted cases.
`tests_not_skipped` counts started cases without a whole-case skip; it is not a
line-coverage metric or proof that every subtest/body executed.

Mixed coverage is allowed by default and reported explicitly. Strict verification
also refuses any skipped case, fixture, or subtest:

```sh
python scripts/verify.py --require-no-skips --report .local/verification.json
```

Expected failures remain visible under unittest semantics. Setup errors, ordinary
failures and unexpected successes fail the stage. Non-test JSON/refusal checks
keep their existing contracts. Summed counts cover observed stages only; inspect
`coverage_observed_stages`, `coverage_unknown_stages`, and per-stage receipts when a stage is interrupted.
Test code and the operator share the host and can tamper with the helper or its
results. Structured accounting is not cryptographic attestation or a sandbox.

## Retained records and replay

[The first task](../provenance/r1_self_application/manifest.json) and
[the linked repair](../provenance/r1_self_application/repair/manifest.json) each
retain eight journal events, exact task and candidate inventories, check starts
and finishes, actual process output digests and elapsed nanoseconds, advisory
review, the installed-validator source pin, and supplementary verification
outcomes. The final reports say shared control, independent review unestablished,
no approval, and an UNKNOWN protected-limit assessment.

The baseline observations, initial frozen-CI integration mistake, test-double
repair, and Windows failure are retained. Preflight records are condensed
observations, not full original logs. Supplementary full-suite reports retain
structured outcomes and stream digests; their report-file hashes were observed
separately, not included in the R1 process receipt. Journal outputs retain hashes,
not recoverable console text. Nothing here authenticates an external origin.

With the historical commits fetched, replay without running any candidate check:

```sh
python scripts/check_repository_self_application.py
python scripts/check_repository_self_application.py --evidence provenance/r1_self_application/repair
```

Replay verifies journal links and transition semantics, resolves the original
base and candidate inventories against their Git commits, and verifies the old
installed-validator hashes against its historical source. It uses the current R1
reducer and explicitly reports whether its source matches the historical
validator; the path repair makes that comparison false. This is same-project
replay, not an independent checker. [Three retained mutation controls](../provenance/r1_self_application/replay-controls.json)
refuse an altered chain, an undeclared check even after rehashing, and a substituted
candidate revision. Replay does not freeze all future HEAD files or
claim that an old review applies to the current checkout.

The frozen historical profiles, S1/S2, studies, and original CI workflow remain
unchanged. R1's preservation inventory covers 148 historical files. The separate
R1 workflow adds strict Linux verification, receipt replay and an installed demo.
Further changes should require a demonstrated defect or a separately specified
new task. This tranche stops here; broader autonomy and efficacy remain untested.
