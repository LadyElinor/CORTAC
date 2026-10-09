# OPR 1 offline supplied record contract

**Optional proposed extension, record v1. Not an adopted amendment or full OPR conformance implementation.**

This document describes [opr_records_v1.py](../package/wac_offline/opr_records_v1.py), [its supplied fixtures](../package/wac_offline/opr_fixtures_v1.py), and [its structural tests](../package/tests/test_opr_records_v1.py). Read the [proposed amendment](OPR1_PROPOSED.md), [19-case requirements map](OPR1_REQUIREMENTS.md), and [current-contract index](CURRENT_CONTRACT.md) for the larger normative and deployment boundaries. Existing software/profile versions, grants, receipts and protected inventories are unchanged.

## API and outputs

```python
from wac_offline.opr_records_v1 import inspect_record, RecordError
from wac_offline.opr_fixtures_v1 import fixture

record, context = fixture()  # Fabricated supplied inputs, not facts or authority.
report = inspect_record(record, context)
```

`inspect_record(record, context)` accepts two closed Python dictionaries. `VERSION` is `cortac.opr.record.v1`; `CONTEXT_VERSION` is `cortac.opr.context.v1`. It raises `RecordError`, a `ValueError` subclass, for malformed or inconsistent supplied inputs. A returned report has status `STRUCTURALLY_COMPLETE` when its implemented blocker list is empty, or `STRUCTURALLY_INCOMPLETE` otherwise. Neither is an approval. The integration harness labels a caught `RecordError` as `REJECTED`; that is a harness observation, not a returned inspection status or an institutional rejection.

The report contains schema `cortac.opr.inspection.v1`, status, blockers, calculated cumulative duration/load, `record_digest`, and `context_digest`, together with these fixed boundaries:

- `authority: NONE`; `execution_enabled: false`.
- `controller_closure: SUPPLIED_UNVERIFIED`; `context_status: SUPPLIED_UNVERIFIED`.
- `evidence_status: REFERENCES_ONLY`; `semantic_assessment: NOT_PERFORMED`.
- `operational_conformance: NOT_ESTABLISHED`.
- `scope: OFFLINE_SUPPLIED_RECORD_STRUCTURE_ONLY`.

No mutable input is retained and no input is changed. A private JSON copy is inspected. Each digest is SHA-256 over its respective complete copied input using Python JSON with sorted keys, compact separators, `ensure_ascii=True`, and `allow_nan=False`. List order remains part of the digest even where scope comparison uses sets. These are unsigned local hashes, not signatures, authenticated chronology, RFC 8785 canonicalization, or grants usable by another gateway. Changing the context changes its digest even if the record is unchanged. A controlling caller can edit inputs, reports, or the program; this is not host-resistant enforcement.

There is no action API, database, network operation, effect, persistent case state, permission grant, reserve debit, complaint transition or real-world evidence query. Integer ticks are supplied logical values with no wall-clock authority. Concurrent inspection is not an atomic external check-and-act protocol.

## Closed input shapes

The executable `RECORD` and `CONTEXT` specifications in the module are the exact field inventory. Every object requires exactly its listed keys; omitted and unknown keys are rejected recursively. Text must be a nonblank string. Digests must be 64 lowercase hexadecimal characters. Integers must be nonnegative actual Python integers; booleans and floats are rejected. Lists reject equal duplicate entries; indexed inventories also reject repeated IDs with different content. Nullable controller declarations accept only `None` or nonblank text. No input field may assert an extra execution, approval, ratification or conformance flag.

### Context

Required root fields are `schema`, `policy_digest`, `epoch`, `now`, `version`, `target`, `burden_group`, `operations`, `duration_limit`, `load_limit`, `serious_duration`, `serious_load`, `history`, `evidence`, `protected_limits`, `principals`, `parties`, and `grants`.

- `operations`, `protected_limits`, and `parties` are nonempty lists of text.
- `history` is a possibly empty list of intervals. An interval has `id`, `case_label`, `start`, `end`, `burden_units`, and a nonempty `operations` list.
- `evidence` is a nonempty inventory of `id`, `digest`, and `kind`. Kind is `OBSERVATION`, `CLAIM`, `INFERENCE`, `CONTRARY`, or `CONTROL`. No evidence bytes are supplied or fetched by this API.
- `principals` is a nonempty inventory of `id` and nullable `controller` labels. The same declaration may describe multiple parties; only the specified reviewer/verifier exclusions are enforced.
- `grants` is a nonempty inventory of `id`, `purpose`, `policy_digest`, `epoch`, `version`, `target`, `operations`, `start`, `end`, `issuer`, and `state`. Purpose is `RESTRICTION`, `REVIEW`, or `NOTICE_DELAY`; state is `CURRENT` or `REVOKED`. These are caller-supplied grant-shaped records, not authenticated permissions. There is no beneficiary, signature, grant ancestry, or independently trusted issuer root.

### Record

Required root fields are `schema`, `case_id`, `case_label`, `policy_digest`, `epoch`, `version`, `target`, `burden_group`, `operations`, `interval`, `cumulative`, `justification`, `evidence_refs`, `contrary`, `limits`, `independence`, `notice`, `review`, `authority_ref`, `continuity`, `stopping_conditions`, `complaints`, and `correction`.

- `interval` has the same interval shape as history. `cumulative` contains nonnegative `duration` and `load` assertions, which must equal the computed values.
- `justification` requires nonblank `conduct`, `rule`, `risk`, `urgency`, `alternatives`, `burdens`, `epistemic`, `normative`, and `dissent`, plus `consequence` and `standard`. Consequence is `TEMPORARY`, `LONG_EXCLUSION`, `ROLE_LOSS`, `PUBLIC_SERIOUS_FINDING`, or `IRREVERSIBLE`; standard is `ARTICULABLE_RISK` or `CLEAR_AND_CONVINCING`.
- `evidence_refs` is a nonempty list of `id` and `digest` pairs.
- `contrary` is a possibly empty list of `evidence_id`, `disposition` (`ADDRESSED` or `UNRESOLVED`), and nonblank `reason`.
- `limits` is a nonempty list of `id`, `status` (`SATISFIED`, `FAILED`, or `UNRESOLVED`), `reason`, and nonempty `evidence_ids`.
- `independence` contains `reviewer`, `verifier`, nonempty `evidence_ids`, `conflict_route`, and integer `reassess_at`.
- `notice` contains `status` (`DELIVERED`, `DELAYED`, or `UNDELIVERED`), `summary`, `authority_ref`, integer `deadline`, and `reason`.
- `review` contains `route`, `substitute`, integer `deadline`, `authority_ref`, and integer `reserved_units`. Routes are nonblank narratives, not live or tested channels.
- `complaints` is a possibly empty list of unique `id`, integer `version`, and `status` (`OPEN` or `RESOLVED`) declarations.
- `correction` contains nonblank `decision`, `attempted_effect`, `observed_effect`, and `audit` narratives, and `status` (`NOT_REQUESTED`, `INCOMPLETE`, or `REPORTED_COMPLETE`).

## Implemented relations and arithmetic

The record must match context policy digest, epoch, version, target and burden group. Operation sets must match exactly; the current interval has that same scope and case label. Each record evidence reference must match a context evidence ID and digest. All context evidence typed `CONTRARY` must have exactly one disposition and a linked record reference; other context evidence need not all be referenced. Limit IDs must exactly equal the supplied protected-limit inventory, and their evidence IDs must link. This establishes reference consistency only, not content resolution, provenance or truth.

The context target must name an existing principal included in the supplied parties list. The completeness of that parties list is not discovered. The reviewer and verifier must be different known principals and neither can be a party. Their supplied controllers must not overlap each other or any party's supplied controller. Any unknown controller among the listed parties, reviewer or verifier produces an incomplete status. Independence evidence must link to `CONTROL`-typed context evidence. A nonblank conflict route is required, and reassessment due at or before `now` is a blocker. The verifier field supplies the recorded verification owner; the code does not verify the owner's independence, evidence quality or mandate in the world, discover omitted parties, or analyze dependency change triggers.

History interval IDs must be unique and the current interval ID must be new. Every interval has positive duration and positive burden units. Historical operations must be a subset of supplied context operations. All supplied history plus the current interval is aggregated regardless of case labels:

- Duration is the length of the union of half-open intervals `[start, end)`, so parallel time is not counted twice.
- Load is the sum of `(end - start) * burden_units` across intervals, so simultaneous burdens add.

Both calculations cover entire supplied intervals, including future portions; they are not elapsed-to-`now` measurements. Ticks are logical integers; burden units are positive supplied weights, not moral severity scores. Units and history membership are caller supplied. The context operation set defines one supplied burden-group scope; the completeness and equivalence of its history must be independently warranted outside this module. A changed label cannot reset included history, but omitted actual history and undisclosed equivalent replacement restrictions are not discovered. The program does not determine whether two real restrictions belong to one burden group or whether assigned burden units capture actual harm.

Declared serious thresholds must not exceed their corresponding hard limits. A hard duration/load limit is exceeded only at `>`; the heightened standard is required at `>=` the serious duration or load threshold, or whenever consequence is not `TEMPORARY`. The code requires the `CLEAR_AND_CONVINCING` enum in those cases. It neither assesses whether that standard is met nor discovers a serious consequence mislabeled `TEMPORARY`. No malicious-intent finding is inferred.

Referenced restriction/review grants must exist, match purpose and context policy/epoch/version/target, match operation scope, have a known issuer and have a positive time window. Current time outside `[start, end)` or supplied revoked state produces blockers. The restriction interval must lie within the supplied restriction-grant window. The current interval itself must contain `now`.

Review requires a positive asserted reserve count and a future deadline no later than the restriction and review-grant ends. A delayed notice requires a matching `NOTICE_DELAY` record and a future deadline no later than the restriction end, notice-grant end and review deadline. Non-delayed notice must use `NOT_APPLICABLE` as its authority reference. Claimed delivered notice cannot have a future delivery tick; undelivered notice is incomplete. Actual delivery is not observed.

Protected limits not asserted satisfied and contrary evidence asserted unresolved produce blockers. An open complaint does not independently block inspection and is never resolved by inspection. Correction asserted `INCOMPLETE` produces a blocker; `REPORTED_COMPLETE` is retained as a declaration without proof. There is no cross-record lifecycle or complaint-version transition validation.

## Returned blocker codes

- `RESTRICTION_AUTHORITY_REVOKED`, `REVIEW_AUTHORITY_REVOKED`, `NOTICE_DELAY_AUTHORITY_REVOKED`.
- `RESTRICTION_AUTHORITY_NOT_CURRENT`, `REVIEW_AUTHORITY_NOT_CURRENT`, `NOTICE_DELAY_AUTHORITY_NOT_CURRENT`.
- `RESTRICTION_NOT_CURRENT`, `CUMULATIVE_DURATION_EXCEEDED`, `CUMULATIVE_LOAD_EXCEEDED`, `HEIGHTENED_FACTUAL_STANDARD_MISSING`.
- `INDEPENDENCE_UNKNOWN`, `INDEPENDENCE_REASSESSMENT_DUE`, `PROTECTED_LIMIT_UNSATISFIED`, `CONTRARY_EVIDENCE_UNRESOLVED`.
- `REVIEW_RESERVE_EMPTY`, `REVIEW_DEADLINE_INVALID`, `NOTICE_DELAY_NOT_BOUNDED`, `NOTICE_UNDELIVERED`, `CORRECTION_REPORTED_INCOMPLETE`.

Malformed or contradictory structure raises before a report is returned. Blocker absence means only the narrower implemented conditions above did not block this supplied snapshot.

## Deliberate section 14 gaps

This is a subset of the amendment's required record inventory, not an executable schema for all of section 14. In particular it lacks structured charter identity and jurisdiction; structured uncertainty and strongest-objection assessment; response and representation records; principal approvals; grant beneficiary and ancestry; protected allocation ownership, isolation and debit beyond the asserted reserve count; exact linked effect and audit records; and complaint-version transition checks. Some topics can appear as opaque text, which does not implement their structured obligations.

There is no policy, evidence, controller or grant authentication. Digests are not authentication. No factual, normative, moral, legal or semantic judgment is performed. An `ADDRESSED` contrary-evidence entry is only a supplied claim: irrelevant nonblank reasons are accepted as text. The fixed semantic oracles required in the proposal, including irrelevant-justification failure, decisive contrary-evidence sensitivity, viewpoint swaps and paired legitimate-risk discrimination, are deliberately unimplemented. The tests explicitly preserve this limitation rather than calling arbitrary text a substantive success.

Broader admission receipts, reasons/status and standing/priority/nonadmission challenges remain a future contract. Real resource isolation, safe expiry, remedies, independent appeals, institutional correction and full OPR conformance also remain unimplemented here.

## Reproduce the bounded checks

```sh
python scripts/opr_integration.py
PYTHONPATH=package python -m unittest discover -s package/tests -p 'test_opr_records_v1.py'
```

The integration script compares exposed synthetic controls with a fixed `EXPECTED` mapping; the test module additionally checks malformed input, scope/reference relations, supplied conflict exclusions, cumulative arithmetic, notice and review bounds, immutable inspection, and non-promotion of semantic claims. The exhaustive small-window interval oracle independently compares the arithmetic with per-tick sets and sums. Consult the actual fresh test receipt for observed counts and results; this contract does not assert a final run count or remote CI result.

These controls use no models or authenticated external principals and cannot establish that the 19 normative acceptance cases pass. Existing frozen scenarios remain separate historical baselines. Installing this module, inspecting a record or passing tests does not adopt the amendment, rewrite protected commitments, or authorize external effects.
