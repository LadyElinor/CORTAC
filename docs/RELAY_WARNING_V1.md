# Relay warning review v1 (proposal only)

The opt-in `wac_offline.relay_warning_v1.inspect_warning` inspector records gaps
between an original warning, its delivery, the combined institutional effect,
a protective proposal and a separately recorded attribution review. Its schema
is `cortac.relay.warning.v1`. It changes no prior schema, OPS1 trace, Vanguard
packet, decision record, profile, charter, or authority boundary.

## Lessons and implementation

Relay Atlas's governance synthesis and Editions 34–35 motivate this supplement.
These are design lessons, not new findings against any real person or institution.
The regression fixtures are entirely synthetic; no allegations or private Atlas
records are copied into this repository.

- **Correction and blame are separate decisions.** Missing evidence of individual
  intent is reported under `attribution_gaps`, not imported into the protective
  proposal's requirements. Conversely a protective proposal supplies no intent,
  misconduct or fraud finding. A proposal still needs its own rationale, existing
  authority and appeal route. Missing authority cannot be cured by urgency.
- **Delivery failure differs from an unanswered warning.** `NOT_DELIVERED`,
  `UNKNOWN`, `RECEIVED_REPORTED` and `NO_RESPONSE_REPORTED` remain distinct.
  Reported receipt needs an evidence reference; it does not prove reading,
  understanding or deliberate disregard. A response without recorded receipt is
  flagged for reconciliation, not classified as deception.
- **Review the combined effect.** The combined review declares its scope and
  limitations, actual access evidence and review evidence. Unknown controllers or
  a shared decision/reviewer controller remain gaps. Different controller labels
  do not establish practical independence. Legitimate privacy or security
  compartmentalization is not evidence of wrongdoing; no access is granted here.
- **A remedy must reach people.** Reported repair needs recipient, observation,
  verification and independence evidence separately. Self-verification, original-decision control conflicts and direct
  reuse of the observation as its verification are flagged. Different digests
  still may derive from the same source. The tool never counts them as independent
  corroboration or treats a second signature as a verified outcome.
- **Preserve warnings, dissent and exonerating corrections alike.** Original
  warning and dissent digests are included in the canonical record digest, with
  exact decision and predecessor digests. Direction of a correction is not
  interpreted as culpability. Association, graph connectivity, source counts and
  normalized addresses are deliberately not attribution inputs.

## Contract and use

`SHAPE` in the module is the executable closed schema. All fields are required,
including explicit unknown/unassessed states and empty evidence lists. Text must
be nonblank and at most 4,000 characters; lists hold at most 128 unique lowercase
SHA256 artifact references. Canonical ASCII JSON is limited to 200,000 bytes.
Unknown keys, versions, malformed digests and wrong types raise `WarningError`.
This API accepts Python dictionaries, not JSON files: any caller adding a JSON
loader must reject duplicate keys before calling it.

An exposed example is `fixture()` in `package/tests/test_relay_warning_v1.py`.
Call `inspect_warning(record)` without changing the supplied record. Output always
contains `status: REVIEW_REQUIRED`, `authority: NONE`, `execution_enabled: false`,
`controller_closure: SUPPLIED_UNVERIFIED`, `attribution: NOT_DETERMINED` and
`effectiveness: NOT_VERIFIED`, including when both gap lists are empty. No score,
legal determination, operational permission or completion certificate is emitted.
`UNASSESSED` attribution is permitted; `REVIEW_RECORDED` requires separate subject,
act, knowledge, authority, intent and fair response-opportunity references as
recording prerequisites, not universally applicable legal offense elements.

A `NOT_ASSESSED` repair is not a repaired outcome. A `REPAIR_REPORTED` record only
checks reference presence and obvious reuse/conflicts. `residual_injury` remains
verbatim, uninterpreted text. No prose value, including “none”, proves closure.

## Relationship to existing controls

Use this supplement to expose warning-routing and combined-review gaps before
relying on a decision. Continue to use OPS1 for versioned findings, chronology,
provenance, dependency changes, affected accounts, deadlines, remedy stages and
residual injury; use Vanguard for its source inventory and review roles. This
supplement neither translates into those records nor asserts that they were
completed. No new controller, reviewer appointment, temporary hold, mandate,
appeal route or execution token is generated.

Evidence artifacts and prior versions must be retained under an existing lawful
retention/access policy. The caller must independently establish that referenced
bytes exist, match their digests, are current, relate to this exact case/decision,
and substantiate the declared role. This inspector does not fetch artifacts,
authenticate people, prove source independence, enforce append-only history,
validate predecessor chains, establish timing, or verify the scope's completeness.
A fabricated or jointly rewritten packet can remain structurally consistent.
A deployed institution needs those independent controls; this is an offline
review aid, not production authorization.

## Verification

Run the exposed controls and full existing suite:

```
PYTHONPATH=package python -m unittest discover -s package/tests -p test_relay_warning_v1.py -v
python scripts/verify.py --report .local/relay-warning-verification.json
```

The controls cover delivery failure versus receipt without response, missing
access and protective authority, attribution independence, self-verification,
missing recipient observations, digest reuse, preserved dissent/predecessor,
malformed/oversized inputs and immutable, canonical output. Passing them is
regression evidence only, not independent field validation or policy ratification.
