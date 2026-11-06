# R1 retained-report audit

Baseline: `ef4062cd878d12288f5f55dad5a225d88c8ba6a1`. This follow-up begins after
the bounded self-application tranche, under a new request to continue. It is a
local engineering audit, not a preregistered efficacy study or independent review.

## Demonstrated gap

The [retained probe](../provenance/r1_replay_audit/baseline.json) copies the first
historical task, changes only its final report, and updates the enclosing manifest
hash. The unchanged control passes. Five contradictory reports also passed:
external execution enabled; wrong evidence digest; invented parent receipt;
passing outcomes relabeled unsuccessful; and an event count supplied as a float.
Journal events and historical source bytes were unchanged in every case.

## Frozen repair scope

Before editing implementation, R1 task `r1-replay-report-audit` declared exact
allowed files and four checks: new report regressions, strict full verification,
and replay of both original historical tasks. A separately installed baseline
build supplies the custodian; controller declarations remain shared/unverified.

Factor the existing runtime report projection into one deterministic function.
Require every retained report field to equal that projection with strict JSON
types, while treating historical `candidate_current` as an unauthenticated
observation. Check its type and its relation to `review_applicable`; do not infer
past or current freshness from journal arithmetic. Validate closed manifest and
exported-event shapes before their use. Preserve all original receipts unchanged.

Controls cover each demonstrated gap, promoted scope/authenticity fields, missing
or extra fields, nested numeric aliases, malformed event arrays, manifest scope,
and coherent historical freshness variants. A coherent freshness claim may pass
structural validation without becoming verified. Stop after this contract repair,
regressions and CI; no additional execution or governance powers are introduced.

## Retained result and checking contract

All four declared checks passed: 11 new regression tests, the full 689-test
suite with zero skips, and both original historical replays. The repeated CLI
controls now accept the unchanged report and refuse all five contradictions.
The original task and repair artifacts remain byte-for-byte unchanged.

The [audit receipt](../provenance/r1_replay_audit/manifest.json) retains the task's
12 events, original installed-validator pin, candidate commit, observations,
and shared-controller UNKNOWN review. Its `design_commit` identifies the original
R1 profile design; the follow-up's specific scope is the task recorded in genesis.
The candidate was checked before these publication records were added. As before,
supplementary verification-report hashes are separate observations, not part of
the process-output receipt or independent custody.

| Claimed check | Concrete counterexample | Remaining assumption |
| --- | --- | --- |
| Complete report agrees with journal projection | Changed evidence/parent/outcome fields or missing/extra fields | Shared runtime projection and checker can share defects |
| JSON types remain distinct | Float event count, boolean exit code, numeric success flag | Standard JSON encoding, not semantic authentication |
| Authority remains unpromoted | Changed execution, independence, authenticity or scope fields | Operator can rewrite code, journal and report together |
| Exported input has a supported shape | Nonobject events, noninteger sequences, invalid manifest fields | Supported local artifact format only |
| Historical freshness is not promoted | Coherent true/false/null freshness variants remain structurally admissible | Replay cannot establish the truth of a past observation |

`report_projection_valid: true` means the complete report is structurally
consistent. `historical_freshness_verified: false` remains explicit. Comparing
current repository bytes, authenticating external custody, or judging the truth
of review prose requires separate evidence. Replay grants no approval.

```sh
python scripts/check_repository_self_application.py --evidence provenance/r1_replay_audit
```

This uses the current R1 reducer, not an independent implementation. The recorded
installed validator remains pinned to the pre-edit build. CI replays all three
retained tasks without rerunning their candidate commands.
