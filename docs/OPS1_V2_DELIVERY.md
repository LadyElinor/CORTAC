# OPS1 remedy v2 candidate delivery receipt

16 October 2026. Base: `59a0e671347f1d0c5a2106da4c596a903766a849`.
Branch: `codex/ops-remedy-v2`. Proposed, opt-in, unratified, authority NONE.

## Inspected baseline and changes

Inspected OPS1 requirements/API contract, v1 schemas/implementation/fixtures/tests,
complaint triage contract, OPR1 record contract, amendment implementation and
schema references, contributor rules and repository verification workflow.
Main was at the supplied October 9 commit at checkout. No existing local work
was overwritten. Original v1 implementation and tests remain byte-identical.

Added a separate v2 module and synthetic fixtures/tests. Events bind the preceding
record digest and explicit causal targets. Current-attempt scope prevents stale
observations/audits from completing later repairs. Authorization-shaped references
bind case, policy, remedy, actor, action and time. Linked reassessments cannot
appoint roles or retroactively cure expired audits. Unresolved injuries, unknown
controllers, conflicting audits and incomplete prior attempts remain visible.

The [v2 contract](OPS1_OFFLINE_V2.md) states the exact transition table, input
fields, compatibility boundary and unsupported processes. No complaint state,
protected inventory, amendment rule, software version, default CLI or external
execution path changed.

## Observed local verification

Linux, Python 3.12.14. Exposed synthetic regression tests only.

- Baseline `PYTHONPATH=package python -m unittest discover -s package/tests -p 'test_ops*_v1.py'`: **110 passed**.
- Final OPS run `PYTHONPATH=package python -m unittest discover -s package/tests -p 'test_ops*.py'`: **189 passed**, comprising the original 110 and 79 v2 tests. The transition-matrix test covers 56 state/stage pairs within one test; these are not additional independent experiments.
- Initial full `python scripts/verify.py --report .local/ops-v2-verification.json`: **640 tests, 21 verification stages passed** before the last three focused controls were added. Final rerun `python scripts/verify.py --report .local/ops-v2-final-verification.json`: **643 tests, all 21 stages passed**, including repository integrity checks, complaint/amendment regressions, frozen sandbox replay and deliberately closed study gates.

The first v2-only run had one test error: the compatibility test caught the v2
TraceError class when calling v1, which correctly raised its own TraceError.
The test now catches the appropriate v1 class. No v1 implementation change was
needed. Subsequent OPS tests passed. Review also led to explicit preservation of
a contested audit across additional observations and rejection of renamed
same-kind evidence with reused content digests; focused controls cover both.

Tests demonstrate that fully fabricated consistent histories remain references
only, incomplete histories cannot become structurally complete, coordinated
rewrites do not establish truth, and omission from both supplied inventories is
not discovered. No factual verification, real independent review, actual remedy,
external principal, model trial or institutional adoption occurred.

## Remaining bounds

One remedy and one fixed reviewer/verifier/dependency inventory per supplied
snapshot; no multi-remedy concurrency, dynamic appointment history, formal
partial-objective closure or complaint/appeal state transitions. Changed
dependency versions require fresh findings rather than repairing history in
place. Grants, controllers, clocks, evidence and predecessor anchors remain
unauthenticated caller assertions. Positive structure never establishes actual
independence, remedy effectiveness, normative validity or execution authority.

Remote CI and other Python/platform combinations are not claimed as verified.
