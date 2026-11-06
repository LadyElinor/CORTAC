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
