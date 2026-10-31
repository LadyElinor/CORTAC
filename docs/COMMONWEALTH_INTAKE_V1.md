# Commonwealth A1 → Vanguard: read-only intake v1

This separately versioned adapter (`commonwealth-vanguard-intake-1.0.0`) preserves
an A1 input as unverified declarations. It does **not** construct a Vanguard
review, resolve evidence gaps, appoint reviewers, ratify the draft charter or
issue authority. The original A1 and Vanguard contracts remain unchanged.

Implementation belongs beside the receiving Vanguard inspector in CORTAC. There
is no Commonwealth runtime dependency or copied execution engine. The pinned
Commonwealth fixture and executable schema are interoperability references; see
[provenance](../provenance/commonwealth_intake_v1.json).

## Exact field crosswalk

Every present string is retained verbatim at `source_packet.answers.<field>`.
Absent keys remain absent; blank strings remain blank. No enum is translated and
no prose is parsed into a source, claim, principal, controller or mandate. The
target paths below are **review topics**, not generated fields or equivalences.
`record` means `packet.record` in the Vanguard contract.

| A1 answer | Potential Vanguard review topic | Evidence still needed |
| --- | --- | --- |
| `case` | `record.decision.title`; `packet.binding.case_id` | Stable case identity and exact decision scope; a title is not an ID. |
| `assessment` | `record.analysis.concern`; `record.claims[].text` | Typed, versioned claims and supporting sources. |
| `legitimacy` | `record.decision.authority`; `record.analysis.limitations` | Keep the four meanings distinct; the label establishes none of them. |
| `stage` | `record.decision.status` | Hypothesis/proposal/commitment/authorization/execution/outcome remain declarations; no event proof or conversion to `record.mode`. |
| `source_record` | `record.sources[]` | Individual source records, locators, passages, versions, origin groups, availability intervals and original artifact digests. |
| `source_status` | `record.analysis.limitations` | A claim of primary review is not original bytes, provenance verification or a reviewer record. |
| `counterevidence` | `record.analysis.counterargument`; `record.claims[].objections` | Source-linked material objections with IDs, state and reasons; contrary material cannot disappear. |
| `action` | `record.decision.objective`; `record.draft.text` | Exact decision/action and separately authored internal draft. No executable instruction is produced. |
| `proposer` | `context.principals` | Established principal identity and controller declaration; no role inferred. |
| `decision_maker` | `record.decision.authority`; `context.principals` | Identity, jurisdiction and separately established mandate. |
| `authority_basis` | `record.decision.authority`; `record.sources[]` | Actual instrument, scope, validity and review; no mandate object is manufactured. |
| `authority_status` | `record.analysis.limitations` | Claimed/disputed/supported wording remains unverified; no grant follows. |
| `affected_people` | `record.analysis.affected_groups`; `context.party_ids` | Established parties and complete affected population; prose is not a party inventory. |
| `representation` | `record.analysis.limitations` | Selection, constituency and mandate evidence. Agreement does not establish universal representation. |
| `trigger` | `record.analysis.discriminating_test`; `record.decision.status` | Independent trigger observations and exact conditions. |
| `scope` | `record.decision.jurisdiction`; `record.analysis.limitations` | Exact scope and authority instrument; no permission follows. |
| `expiry` | `record.analysis.limitations` | Established validity interval, current revocation status and trusted timing. No expiry date is inferred. |
| `dissent` | `record.claims[].objections`; `record.analysis.counterargument` | Separate source-linked objections and dispositions; retention is not resolution or assent. |
| `reversal` | `record.analysis.remedy`; `record.analysis.correction_route` | Separate remedy authority, delivery and outcome evidence; no OPS1 events are created. |
| `reviewer` | `packet.reviews`; `context.principals` | Seven role outputs, identities, record bindings and controller declarations; one string supplies none of these. |
| `public_language` | `record.sources[]`; `record.analysis.chronology` | Contextualized public record, source identity and uncertain dates. |
| `working_language` | `record.sources[]`; `record.analysis.chronology` | Separate contextualized working record; not replaced by the public or analyst account. |
| `analyst_language` | `record.analysis`; `record.claims[]` | Distinguish interpretation from record content; source-linked claims and re-review remain necessary. |

A1 accepts exactly `schema`, `answers`; the schema is
`warranted-authority-review-1`. The answer keys above are the entire allowlist.
Each value is a string of at most 4,000 characters. Missing answers are allowed
and remain explicit gaps. Canonical ASCII JSON is bounded to 120,000 bytes, as in
A1. The raw A1 CLI file also has that byte limit. The four enum fields retain
the exact A1 options, including their unknown/default values.

## Vanguard requirements not supplied by A1

These are exhaustive schema groups, not a suggestion to fill them with placeholders.
Even a fully populated A1 form does not satisfy any structured group below.

| Group | Exact required Vanguard fields | Required work |
| --- | --- | --- |
| Contract/binding | `packet.schema`, `packet.binding.{case_id,policy_digest,version,predecessor_digest}`, `packet.context_digest`; `context.schema`, `context.expected.{case_id,policy_digest,version,predecessor_digest}` | Separately supply versioned case/policy and predecessor anchors; authenticate them outside this adapter. |
| Decision/clock | `record.mode`, `record.decision.{title,authority,jurisdiction,objective,status,occurred.{earliest,latest}}`; `context.now`, `context.source_cutoff` | Establish decision scope and availability intervals, preserving uncertainty. A1 stage is not Vanguard mode. |
| Sources | `record.sources[].{id,version,origin_group,url,locator,passage,available.{earliest,latest},artifact_digest}`; `context.sources[].{id,version,digest}` | Supply actual source inventory and original artifacts; packet hashes are not original artifact hashes. |
| Claims/objections | `record.claims[].{id,version,subject,identity,kind,text,source_ids,objections}`; each objection `{id,state,reason,source_ids}`; `context.claims[].{id,version,digest}` | Separately establish identity, typing, material objections, references and inventory completeness. Empty objections do not prove absence of dissent. |
| Analysis | `record.analysis.{concern,harm_criterion,affected_groups,benefits,alternatives,chronology,counterargument,remedy,intervention_costs,outcome_measure,discriminating_test,limitations,correction_route}` | Evidence-based analysis including contrary material, costs and alternatives. Text overlap does not establish adequacy. |
| Disposition/draft | `record.disposition`, `record.disposition_reason`, `record.draft.{kind,audience,text}` | Separate reasoned disposition and internal draft. Intake does not choose them. |
| Review/control | `packet.reviews[].{role,principal,record_digest,assessment}`; `context.principals[].{id,controller}`, `context.party_ids` | Independently establish actual reviewers, controllers, conflicts and review of the current complete record. Seven supplied roles are not seven independent confirmations. |

## Permission boundaries

| Operation | Condition | Result / fallback |
| --- | --- | --- |
| Preserve A1 | Closed schema, supported enums and bounded JSON | Intake only; malformed input is rejected. |
| Preserve provenance | Null, or the closed source-context schema with an exact packet digest | Nulls become gaps; mismatched bindings are rejected. No original evidence is synthesized. |
| Inspect a supplied pair | Exact intake, Vanguard packet/context and explicit link digests | Existing Vanguard inspector runs; its blockers remain visible. Relationship and semantic correspondence stay unverified. |
| Execution or appointment | Not implemented | Always `authority: NONE`, `execution_enabled: false`; no token, dispatcher, approval store or urgency override. |

The intake is a new schema, never a Vanguard packet or an A1 result/warrant.
It remains incomplete even when a separately supplied Vanguard record passes
structural inspection. Code consistency is not independent evidence or governance
approval. See the implementation and results sections below for bounds, commands
and tested limitations.

## Closed intake and link schemas

`build_intake(packet, source_context=None)` accepts an A1 **input** and either
null or a source context containing exactly these fields:

| Field | Type / meaning |
| --- | --- |
| `schema` | Exactly `cortac.commonwealth.source_context.v1`. |
| `packet_digest` | Lowercase SHA-256 of the complete canonical A1 input; must match. It is not an original artifact hash. |
| `locator`, `version`, `origin_group` | Bounded nonblank strings, or null for unknown. These describe the supplied packet's context, not an invented underlying source inventory. |
| `event_interval`, `publication_interval` | Null or exactly `{earliest, latest}` in canonical `YYYY-MM-DD`; reversed/invalid intervals rejected. Unknown dates stay null. |
| `scope` | `SYNTHETIC`, `UNESTABLISHED` or `DECLARED_EXTERNAL`; a declaration only. |
| `original_artifact_digest` | Null or a supplied lowercase SHA-256 declaration. The adapter does not have original artifact bytes and does not authenticate this value. Never fill it with the A1 packet digest to disguise missing evidence. |

The output's exact keys are `schema`, `adapter_version`, `source_packet`,
`source_context`, `packet_digest`, `source_context_digest`, `missing_answers`,
`provenance_gaps`, `unsupported_vanguard_requirements`, `status`, `authority`,
`execution_enabled`, `controller_closure`, `source_authentication`,
`original_artifact_verification`, `semantic_assessment`. Its schema is
`cortac.commonwealth.intake.v1`. It always has `INTAKE_REQUIRES_EVIDENCE`,
`authority: NONE`, `execution_enabled: false` and unverified/not-performed labels.
`inspect_intake` recomputes the entire envelope; extra fields, changed derived
values, numeric substitutes for booleans and incompatible versions are rejected.

The `pair` file has exactly `{intake, packet, context, link}`. `packet` and
`context` must be independently supplied Vanguard v1 inputs. `link` has exactly:

- `schema`: `cortac.commonwealth.vanguard_link.v1`.
- `intake_digest`, `packet_digest`, `context_digest`: hashes of those three
  complete objects, including reviews and source context.
- `relationship_basis`: a bounded nonblank caller explanation; not adjudicated.

Each digest is sorted, compact, ASCII JSON with nonfinite numbers rejected,
identical to Vanguard's canonicalization. Input key order/whitespace is not
hashed. Strings are preserved as decoded Unicode, without trimming or semantic
normalization. No raw-byte or signature verification is claimed.

A pair inspection keeps the checked intake, supplied link, Vanguard report and
all target blockers. It always adds unresolved relationship, context/objection
review and independent-evidence/governance obligations, even when the target is
`SUPPLIED_REVIEW_CONSISTENT`. A `SYNTHETIC` source context cannot be linked to a
non-synthetic target. Unknown scope remains an unresolved gap. Renaming a scope
and rebinding all caller records cannot establish authenticity.

There is no inference that matching prose or a caller link identifies the same
case/policy. Vanguard's own exact case/policy/version/predecessor checks still
apply internally. Pairing the supplied Terra fixture with a Vanguard fixture is
explicitly an **unrelated-record byte-binding control**, not a substantive case
conversion. A target's role reviews bind its target record only; they cannot be
treated as having reviewed the intake or its dissent.

No history is stored. Retain prior records externally. Amendments require a new
intake and a new explicitly supplied link; old links fail even if the caller has
rebound the target. Changed target sources/claims/reviews remain subject to
Vanguard's stale-inventory and stale-review checks. Rehashing is not re-review.

Source context is limited to 32,000 canonical bytes and 4,000 characters per text
field; intake to 180,000 bytes; pair-file input to 3 MiB. Each target packet/context
still has Vanguard's individual 1 MiB digest bound and schema limits. JSON depth
is at most 24, nodes at most 30,000, object/list length at most 256. Raw file limits
apply in addition to canonical limits. Duplicate keys, nonfinite values and
non-UTF-8 files are rejected. Limits are local ingress bounds, not a network
denial-of-service claim.

## Commands and outcomes

```sh
python scripts/commonwealth_intake.py intake vanguard/commonwealth/terra-a1-packet.json --source-context vanguard/commonwealth/source-context.json
python scripts/commonwealth_intake.py inspect vanguard/commonwealth/intake.json
python scripts/commonwealth_intake.py pair path/to/explicit-pair.json
python scripts/commonwealth_integration.py
python scripts/commonwealth_integration.py --commonwealth-checkout /path/to/pinned/unfinished-commonwealth
python scripts/verify.py --report .local/verification.json
```

Installed entry point: `python -m wac_offline.commonwealth_intake_v1` with the same
arguments. Files are read locally, output goes to stdout, and no ledger, network,
database, process execution, original-artifact fetch or dispatch occurs in the
adapter. Shell redirection is an explicit caller choice.

| Exit | Interpretation |
| --- | --- |
| 2 | Malformed, changed, incompatible or scope-promoting input rejected. |
| 3 | Valid intake/pair recorded; independent evidence still required. There is no complete-review/authorized-success exit. |
| 0 (control runner only) | Fixed structural expectations matched. Without the optional pinned checkout, the A1 comparison is explicitly `NOT_RUN`. |

The development control runner's checkout option imports the separately supplied
A1 validator after checking its pinned Git revision, clean tracked state and
reference hashes. That is a test-only dependency, absent from the adapter API.
CI supplies the exact pinned checkout and runs that comparison as a required
job step; whether the job itself is a protected merge requirement is not claimed.

## Demonstrated and unresolved properties

See [executed validation](COMMONWEALTH_INTAKE_V1_RESULTS.md). This is exposed,
deterministic contract testing, not held-out research or a live Terra/Relay API
integration. Only the existing Terra-compatible export copied by A1 was used;
the adapter does not directly authenticate Terra or Relay Atlas.

Independently establish original artifacts, provenance, complete inventories,
identities, controller independence, reviewer authorship and substantive responses
to objections before treating an associated review as evidence. Establish actual
mandates, representation, expiry/revocation, correction authority and governance
approval separately. This adapter has no mechanism for enabling execution even
if those conditions are later established. A future operational interface would
need its own authorization, versioned contract and review.
