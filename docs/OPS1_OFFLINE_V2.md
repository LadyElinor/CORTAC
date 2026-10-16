# OPS1 opt-in remedy trace v2

Proposed experimental representation, not adopted. Software remains 0.2.2;
governance remains unratified and execution-disabled. No production adapter.

## API and compatibility

`wac_offline.ops_trace_v2.inspect_trace(trace, context)` returns a deterministic
supplied-record report or raises its `TraceError` (`ValueError`). `digest(value)`
uses the same unsigned bounded JSON convention as v1. Schema identifiers are
`cortac.ops.trace.v2`, `cortac.ops.context.v2`, and `cortac.ops.inspection.v2`.
Importing v2 is explicit; no CLI, gateway, study or amendment API opts in.
The original v1 modules, schemas, six-stage contract and fixtures are unchanged.
No implicit conversion of v1 evidence into v2 authorization is provided.

The exact closed schemas are `TRACE` and `CONTEXT` in
[ops_trace_v2.py](../package/wac_offline/ops_trace_v2.py). v2 retains the v1
findings, provenance, objections, hearings, supplied principal/controller,
dependency, funding, injury-version and input-size checks. The implementation
keeps those checks locally isolated from the unchanged v1 implementation;
future common fixes must be reviewed for both versions. Bounds remain 256 items
per list, 8,192 characters per text, 1 MiB per canonical input and integer ticks
in [0, 2^63−1]. Unknown fields and boolean/float ticks reject. Inputs are copied.

## Explicit transitions and causal links

The initial state is START. Only the following edges are allowed:

| From | Permitted next stage |
| --- | --- |
| START | ORDERED |
| ORDERED | ACCEPTED, REFUSED, ATTEMPTED* |
| ACCEPTED | ATTEMPTED, REFUSED |
| REFUSED | ACCEPTED, ATTEMPTED* |
| ATTEMPTED | ATTEMPTED, OBSERVED, REFUSED |
| OBSERVED | OBSERVED, AUDITED, ATTEMPTED |
| AUDITED | AUDITED, OBSERVED, ATTEMPTED, EFFECTIVENESS_REPORTED |
| EFFECTIVENESS_REPORTED | ATTEMPTED, OBSERVED, AUDITED |

`*` Requires remedy mode `COMPULSORY_REPORTED`; `VOLUNTARY_REPORTED` requires
acceptance before the first attempt or an attempt following refusal. A compulsory
label is not a determination that an order is lawful or enforceable. REFUSED
requires refusal-kind evidence, preserves history, and when terminal produces
an escalation blocker. Acceptance is not fabricated for compulsory paths.

Each event contains `id`, `stage`, `previous_id`, `previous_digest`, `at`, `actor`,
`reason`, `evidence_refs`, `targets`, `authorization_ref`, `assessment_ref`, and
`outcome`. The first previous ID is NONE and its digest binds the complete
findings; subsequent links bind the immediately preceding complete event.
Event IDs are unique and NONE is reserved. Ticks cannot regress. These links
allow separate recomputation of supplied causal consistency, not authentication.

Order targets are empty; acceptance, refusal and attempts target their immediate
predecessor. Every observation targets the current attempt. Each audit targets
**all** observations of that attempt available in the event prefix. A reported
effectiveness event targets all current covering audits. Forward, absent, wrong
kind or stale targets reject. All event evidence references carry ID, version and
digest, have stage-matching kinds, and must be available by the event and no
earlier than its predecessor. Evidence IDs and same-kind content digests cannot
be reused across events, including under a different evidence ID.

A retry resets current observation/audit scope. A new observation invalidates
prior audit coverage until a new covering audit is supplied. Earlier records are
retained. An attempt abandoned without observation and current audit coverage
produces `PRIOR_ATTEMPT_TRACE_INCOMPLETE`, even if a later attempt is fully
reported. This is a deliberately conservative trace profile, not a rule that a
real repair must wait for this inspector. A failed but observed/audited attempt
can be followed by a newly observed/audited retry.

Audit outcome must be `REPAIR_REPORTED`, `INCOMPLETE_REPORTED` or `CONTESTED`;
other stages require `NOT_APPLICABLE`. A later positive audit does not erase an
earlier conflicting audit of the same attempt, even after another observation.
Such histories retain `AUDIT_REPAIR_NOT_ESTABLISHED`. A new attempt is separately
scoped; this does not resolve a complaint about the earlier attempt. The tool
checks declared contradictions only, not conflicts hidden inside evidence text.

## Supplied authorization references

Context adds `authorizations`: unique ID, exact case/policy/version/predecessor
`binding`, remedy ID/version, actor, issuer, stage scope, start/end ticks, and state
`CURRENT_REPORTED` or `REVOKED_REPORTED`. Known actor and issuer, exact remedy
and case scope, and a nonempty half-open time interval are required. Every event
must reference a matching actor/action authorization. Missing or mismatched
references reject. Revoked or out-of-window declarations block consistency.

These are **grant-shaped supplied records**, not credentials or permissions.
No issuer mandate, ancestry, signature, beneficiary authentication or revocation
service is supplied. No record invokes the complaint gateway, reserves resources,
changes a protected inventory, adopts an amendment or authorizes an effect.
Current versus revoked describes the supplied snapshot; timed revocation history
and historical grant replacement are outside this profile.

## Reassessment and reviewer separation

Trace adds a chronological `reassessments` list. Each record has all original
independence fields plus a unique ID and `previous_id` (INITIAL for the first).
INITIAL is reserved. Records retain the designated reviewer/verifier, all six
dependency dimensions with exact current supplied versions/evidence, assessment
and exclusive expiry ticks, evidence links and a challenge route. No record
appoints a replacement reviewer or verifier.

The original independence assessment must cover the findings. Every audit must
explicitly reference the latest reassessment available at its tick and fall
within its validity window. The latest assessment must also remain unexpired
at context `now`, otherwise the report remains incomplete. A later assessment
cannot repair a historically expired audit. Equal ticks use supplied list order,
which is digest-bound, not externally authenticated time.

All v1 reviewer/verifier/party exclusions remain. Audit actors must be the
separate verifier and cannot be remedy owner or any supplied attempt/observation
actor. Declared controller overlaps and unknown relevant controllers block;
noncurrent dependency declarations also block. Reassessment records cannot
turn undisclosed dependence into actual independence.

This profile uses one supplied dependency inventory. A dependency change after
the original assessment still blocks the original findings. To represent
changed dependency versions or replacement reviewers, supply a new findings
snapshot and caller anchor; v2 does not retroactively rewrite old findings or
validate a cross-snapshot dependency history. Dynamic dependency timelines,
multiple verifier appointments and independent appointment authentication remain
future separately reviewed work.

## Injuries, incomplete repair and closure boundaries

Residual IDs/versions must exactly match every supplied injury. Observation and
audit fields now reference **event IDs**, not v1 evidence IDs, within the current
attempt and current audit coverage. `REPAIRED_REPORTED` requires both kinds of
links and linked audits with repair-reported outcomes. A contradictory linked
audit rejects that disposition. Other dispositions, including referral, waiver,
and contest, remain nonrepair blockers. Additional injuries cannot disappear
through a version mismatch or missing disposition. A supplied affected account
must be available and no earlier than the latest observation; exceptions remain
visible blockers. Incomplete histories retain deadline/escalation checks.

There is no case closure operation. Partial injury reporting is supported while
other injuries remain incomplete; formal partial-objective closure, appeal
transitions, new complaint admission and multi-remedy/concurrent branches are
not implemented. As required by [complaint triage](COMPLAINT_TRIAGE.md), an older
repair cannot close a newer complaint or appeal. Here that boundary is maintained
by **not writing complaint state at all**, not by claiming an implemented bridge.
Existing [OPR records](OPR1_RECORDS_V1.md) and amendment old-rule/quorum/protected
inventory checks remain separate. No v2 report substitutes for any of them.

## Status and non-promotion

Malformed/contradictory input raises; otherwise status is
`SUPPLIED_TRACE_CONSISTENT` or `SUPPLIED_TRACE_INCOMPLETE` with ordered blockers.
Every returned report, including complete fabricated examples, retains:

- `authority: NONE`, `execution_enabled: false`;
- `controller_closure: SUPPLIED_UNVERIFIED`, `evidence_status: REFERENCES_ONLY`;
- `inventory_scope: SUPPLIED_INVENTORY_ONLY`, `freshness: CALLER_ANCHOR_ONLY`;
- `semantic_assessment: NOT_PERFORMED`;
- factual truth, actual independence, remedy effectiveness and operational
  conformance: `NOT_ESTABLISHED`.

No evidence bytes are fetched, no signatures checked, no models called and no
external effects performed. The caller can fabricate all records, jointly
rewrite all hashes and anchors, omit an injury from both inventories or conceal
a conflict. Structural consistency cannot detect those omissions or establish
truth, lawful authorization, institutional adoption, real repair or effectiveness.

## Reproduce

```sh
PYTHONPATH=package python -m unittest discover -s package/tests -p 'test_ops*.py'
python scripts/verify.py --report .local/ops-v2-verification.json
```

[Tests](../package/tests/test_ops_trace_v2.py) include retries, repeated
observations/audits, refusal and compulsory paths, stale scope, incomplete repair,
conflicting audits, missing authorization, controller conflicts and deliberate
fabrication/coordinated omission controls. [Fixtures](../package/wac_offline/ops_fixtures_v2.py)
are exposed synthetic records, not observed remedies or sealed validation data.
See the delivery receipt for actual counts and failures.
