# Vanguard decision review: opt-in contract v1

Vanguard contributes a decision-centered research workflow to CORTAC. This
integration implements local inspection of supplied review packets and an explicit
link to the existing OPS1 v1 remedy inspector. The seven role assignments are
instructions for future bounded research runs, not seven deployed agents.

The software/profile versions and frozen assignment contract remain unchanged.
This is a proposed, separately versioned extension. Its charter is unratified.

## Entry points

From the checkout, with Python 3.10+ and no dependencies or credentials:

```sh
python scripts/vanguard_review.py vanguard/examples/jpmorgan-madoff-retrospective.json
python scripts/vanguard_review.py vanguard/examples/fictional-failure.json
python scripts/vanguard_review.py vanguard/examples/fictional-resolved.json
python scripts/vanguard_integration.py
python scripts/verify.py --report .local/verification.json
```

The installed package supports `python -m wac_offline.vanguard_review_v1 FILE`.
Example files and role instructions live in the repository, not wheel package data.
No network retrieval, model calls, monitoring, publication, contacts, payments or
remote system effects occur. The existing `wac-offline` CLI is unchanged.

| Inspection exit | Meaning |
| --- | --- |
| 0 | `SUPPLIED_REVIEW_CONSISTENT`: supplied structure and dependencies pass |
| 2 | `REJECTED`: malformed, stale, unsupported or contradictory input |
| 3 | `SUPPLIED_REVIEW_INCOMPLETE`: explicit blockers remain |

Integration controls return 0 when all fixed expected outcomes match, otherwise 1.
A consistent packet may recommend retaining **or closing** a concern. The checker
does not choose that recommendation, judge the prose, or establish that it is right.

## CORTAC mapping

| Vanguard artifact | CORTAC boundary | Implemented here |
| --- | --- | --- |
| Decision card and claim/source ledger | Epistemic record | Exact source/claim inventory, version and digest checks |
| Harm criterion, benefits and alternatives | Normative assessment | Required narrative fields; meaning remains for review |
| Seven role outputs and disposition | Supplied review | Role coverage, record bindings and limited declared-controller checks |
| Internal challenge draft | Proposed decision/action | Bound content and audience; no authorization grant or sender |
| Separate remedy trace | OPS1 delivery and correction | Explicit case/policy/digest link and both inspectors' blockers |
| Amendment/correction | Audit and correction | Prior reviews and handoff links become stale after content changes |

Relay graph relationships can seed a claim ledger, but graph centrality or a path
does not establish an instruction, knowledge, causation or guilt. There is no
automatic graph import or conversion of historical allegations into findings.

## Source and workflow

- [Charter text export](../vanguard/CHARTER_SOURCE.md) preserves the supplied
  draft in its source order. Its planned tests remain historical plans, not a
  claim that all those capabilities are now implemented.
- [Provenance](../provenance/vanguard_revision.json) identifies the source version,
  export hash and historical document hash. The export is not original artifact
  bytes, a signature or authority. Personal account metadata is omitted.
- [Role instructions](../vanguard/ROLE_PROMPTS.md) define scope and review duties.
- [Pilot notes](../vanguard/PILOT.md) distinguish the historical example, fictional
  controls and remaining semantic evaluation work.

Register the decision, competing explanations, source cutoff and harm criterion
before collecting evidence. Preserve original locators and uncertain dates. Freeze
the complete record, obtain role reviews of that version, then inspect it. A
correction requires new source/claim versions and fresh reviews of the changed
record. Maintain the prior packet externally; this inspector has no persistence.

## Closed record schema

The executable schema constants in
[`vanguard_review_v1.py`](../package/wac_offline/vanguard_review_v1.py) and the
three examples define exact field names. Unknown fields are rejected at every
level. Lists have at most 256 items; strings are nonblank and at most 8192
characters; versions are positive integers (not booleans or floats); digests are
lowercase SHA-256. Canonical JSON digest inputs and CLI files are bounded to 1 MiB.
Duplicate JSON object keys are rejected by the CLI.

| Object | Required contents |
| --- | --- |
| File | `packet`, `context` |
| Packet | Schema, case/policy/version/predecessor binding, context digest, record, role reviews |
| Context | Schema, expected binding, review date, source cutoff, source/claim reference inventories, principals and party IDs |
| Record | Mode, decision card, sources, claims, analysis, disposition and reason, internal draft |
| Source | ID/version, declared origin group, URL, locator, passage, availability interval, original artifact digest |
| Claim | ID/version, subject, identity status, claim type, text, source IDs, material objections |
| Objection | ID, open/resolved-reported state, reason and source IDs |
| Review | One of seven roles, declared principal, complete record digest, assessment |

Digests use sorted compact ASCII JSON with nonfinite values rejected, shared with
OPS1. Source and claim anchors hash each complete object, including its ID/version.
Role reviews bind the entire `record`, including the draft audience and text.
The packet digest additionally binds reviews, context and policy/version.
The policy digest identifies supplied policy bytes; it does not ratify them.

Dates are canonical `YYYY-MM-DD` strings. Intervals preserve uncertainty: use the
first and last possible day, not an invented exact date. The source interval's
latest date must be on or before the cutoff to pass. A `PROSPECTIVE` packet must
have a cutoff no later than the decision's earliest date; retrospective and
synthetic decisions must end no later than the supplied review date. These are
caller declarations, not verified historical availability or trusted timestamps.
The checker does not infer causal chronology from narrative text.

Every claim and objection references known source IDs. Open material objections,
ambiguous subject identities, requested additional evidence, missing role reviews,
and out-of-cutoff sources produce an incomplete result. Unknown/stale references,
inventory changes and obsolete review digests are rejected. Closing a concern
requires `NO_CHALLENGE` as the draft kind. All objections in this minimal schema
are material; nonmaterial disagreements remain in narrative fields.

For this pilot, drafter, counterargument reviewer and auditor must declare distinct
principals and controllers, separate from any declared parties. Unknown controllers
hold the packet. Other roles can be shared. This local rule is narrower than real
independence or full CORTAC appointment/conflict review. No agent appointments are
created, and seven role outputs never count as seven independent confirmations.

Origin counts use caller labels only. Three reports assigned one origin count as
one group. Identical artifact digests assigned multiple origins trigger a blocker.
Different bytes can still copy the same source; fabricated origin labels can pass.
There is no automated source-independence judgment, confidence score or vote.

## OPS1 remedy handoff

The Python API `inspect_ops_handoff(packet, context, trace, ops_context, link)`
calls both inspectors without mutating records. `link` has schema
`cortac.vanguard.ops_link.v1` and exactly four canonical digests:
`packet_digest`, `context_digest`, `trace_digest`, `ops_context_digest`.
The case ID and policy digest must match across both records; each stream retains
its own version and predecessor. Vanguard dates and OPS1 logical ticks are separate
clocks and are **not** compared.

The handoff is consistent only if both records are consistent and the concern is
retained. Blockers are prefixed `REVIEW:` or `OPS1:`; a closed or evidence-seeking
concern cannot pass as a retained-concern remedy handoff. Malformed OPS1 records
become `ReviewError`. There is no implicit creation of OPS1 findings, remedies,
authorization records or completed delivery events. The relationship is explicitly
`CALLER_ASSERTED_ONLY`: matching identifiers cannot establish semantic equivalence.

The adapter targets main's OPS1 **v1** API. It neither imports nor merges the
separate `codex/ops-remedy-v2` work. A v2 trace requires its own versioned adapter;
passing one to this adapter is rejected by the v1 inspector.

## Interpretation limits and next gate

All reports have `authority: NONE`, `execution_enabled: false`, and
`controller_closure: SUPPLIED_UNVERIFIED`. Evidence, authorship, original artifact
hashes, identity resolution, completeness and review narratives are caller supplied.
The inspector does not fetch sources or authenticate reviewers. Jointly rewriting
the packet, inventories and review bindings can pass; fixture `rebind` deliberately
demonstrates this and must not substitute for actual re-review.

The controls include a nonsensical but nonblank counterargument that passes. This
is an intentional demonstration of the semantic boundary. Passing fixtures do not
establish claim accuracy, false-allegation rates, causation, remedy effectiveness,
independent governance or readiness for autonomous challenges. Genuine source
review, adjudication and prospective holdout evaluation remain human/research work.

Before a live pilot, specify a decision stream, authorized source inventory,
responsible human, resource budget, correction route and completion criteria.
External action needs a separate existing authority covering the exact action.
This component implements no approval store, dispatch gateway or urgency override.
