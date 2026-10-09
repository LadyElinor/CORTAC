# OPS1 opt-in offline contracts

**Proposed operating supplement; not adopted.** These APIs implement only bounded supplied-record relations for [OPS1](OPS1_PROPOSED.md). Read the [requirements/status map](OPS1_REQUIREMENTS.md) before making a conformance claim. Existing software/profile 0.2.2/0.2, OPR record v1, protected inventories, runner, triage and evaluation contracts remain unchanged. New schema identifiers are independent opt-in versions; neither API is part of the default CLI or an effect gateway.

## Common boundary

Inputs are caller-supplied Python dictionaries. Exact closed field specifications are the `TRACE`/`CONTEXT` and `PLAN`/`CONTEXT` constants in their respective modules. Unknown/missing fields, duplicate inventory identities, wrong enums, blank text, malformed digests and contradictory references raise `TraceError` or `StudyError`, both `ValueError` subclasses. Values are finite JSON-shaped trees. Lists have at most 256 entries, strings at most 8,192 characters, nonnegative integer ticks at most 2^63−1, and each canonical input at most 1 MiB. Boolean and floating-point ticks are rejected. Private copies are inspected; no mutable input is retained or changed.

Digests use SHA-256 over Python JSON with sorted keys, compact separators, `ensure_ascii=True`, `allow_nan=False`, encoded as UTF-8. Object key order is irrelevant; list order is retained. These are unsigned local content bindings, not RFC 8785 canonicalization, signatures, trusted timestamps, provenance verification or permission grants. Neither module fetches evidence bytes, contacts principals, invokes models, writes case state, operates a database or performs external effects. Report construction is deterministic for the supplied inputs.

The caller can jointly rewrite anchors, inventories, records, labels, clocks and histories. A host-controlling adversary can also rewrite the code. These modules are not host-resistant enforcement or an authenticated append-only log. Evidence IDs and digests do not establish that referenced evidence exists, that inventories are exhaustive, that reported events happened, or that stated reasons are relevant. A consistent fabricated example remains fabricated.

## Supplied disputed-case/remedy trace

Module: `wac_offline.ops_trace_v1`.

- API: `inspect_trace(trace, context)`; `digest(value)`; `TraceError`.
- Trace schema: `cortac.ops.trace.v1`.
- Context schema: `cortac.ops.context.v1`.
- Report schema: `cortac.ops.inspection.v1`.
- Returned status: `SUPPLIED_TRACE_CONSISTENT` or `SUPPLIED_TRACE_INCOMPLETE`, with deterministic blocker codes. A malformed/contradictory input raises instead of returning a report. The exposed harness calls this `REJECTED`; that is not an institutional ruling.

The complete trace binds to the digest of the complete supplied context. Its `binding` must exactly match the context's `expected`: case ID, policy digest, version and predecessor digest. This detects mismatch with that caller anchor only. It does not discover the latest record, prove predecessor existence, validate an actual chain or prevent rollback when the caller also rewrites the anchor. No minimum version increase or durable compare-and-swap is implemented.

### Input inventories and factual dependencies

Context roots: schema, expected, now, evidence, claims, objections, dependencies, injuries, remedy_version, parties, principals. Trace roots: schema, binding, context_digest, findings, independence, remedy.

Evidence carries unique ID, version, digest, kind and supplied observed tick. Claims carry unique ID/version and original IDs. Objections carry unique ID/version, claim ID/version, counterevidence IDs, supplied materiality and reopening tick. Every supplied counterevidence record must occur in an objection. Each supplied claim must have exactly one finding; each finding must reference its originals, all applicable counterevidence, and all support used by its provenance checks, resolutions and hearing rationale. Evidence references match both version and digest.

Each original requires a recorded provenance check with exact original version/digest, a known checker, typed check-evidence reference, method text and tick before the finding. Party checkers block the trace. This is a check-record dependency, not actual provenance verification or proof that the checker is independent.

Each supplied objection requires a version-matched resolution. Material unresolved objections and resolutions predating reopening block the trace. Support must be available by the claimed resolution tick, and resolution must not postdate the finding. A pending hearing blocks; a reported hearing requires hearing-typed support. `NOT_WARRANTED` requires linked rationale but its appropriateness is not evaluated. Nonmaterial classification, relevance, contradiction resolution, evidentiary standard and factual truth are not assessed. Coordinated deletion of objection plus evidence plus links can still produce consistency; a regression test preserves this limitation.

### Independence

Reviewer and verifier must be known, distinct, non-party principals. Unknown relevant controller labels, declared reviewer/verifier/party controller overlaps, expired reassessment and noncurrent dependency declarations block. The context and assessment must each cover exactly six dimensions for both reviewer and verifier: funding, removal, appointment, information access, recusal and independent advice. Each reference matches the current supplied dimension version/evidence inventory. Evidence must be available by assessment, and a supplied dependency change after assessment blocks.

Assessment must precede the findings and be within its reassessment interval at the audit. There is no appointment service, authenticated verifier mandate or recursion that proves who verified the verifier. Supplied evidence, controller exclusions and a current tick do not establish actual independence or discover hidden control. The challenge route is text, not a tested communication channel.

### Remedy dependencies

The remedy binds to its current supplied version and the digest of the complete findings. An owner, deadline, funding references, full stage-evidence inventory and escalation owner/due tick/route are required. These fields do not allocate money, staff a role or prove enforceable authority.

The deliberately narrow trace profile supports one ordered prefix:

`ORDERED → ACCEPTED → ATTEMPTED → OBSERVED → AUDITED → EFFECTIVENESS_REPORTED`

Each event has an ID, previous event ID, actor, tick and stage-typed evidence IDs. Ticks are monotone; stage evidence must be available by its event and cannot predate its causal predecessor (the findings for the first event). Findings must precede the remedy sequence. Observed evidence cannot substitute for attempted evidence or vice versa. A reported audit must be by the separate verifier, not the remedy owner or an attempted/observed effect actor, with no declared controller overlap; unknown audit/effect controllers block. This is supplied trace consistency, not an audit of real delivery.

`ACCEPTED` records this narrow profile's acceptance event. It does **not** require an obligated actor's consent for a compulsory remedy. OPS1's wider procedure preserves compulsory orders and noncompliance/escalation; those paths need a separately reviewed trace profile rather than fabricated acceptance here. Reattempts, multiple remedy branches, concurrent effects and durable case transitions are also outside v1.

Every supplied residual injury must have a matching versioned disposition. `REFERRED`, `CONTESTED`, `WAIVED_REPORTED` and `UNRESOLVED` remain nonrepair blockers. `REPAIRED_REPORTED` requires nonempty observed/audited references belonging to the actual corresponding remedy events; it still does not establish that injury was repaired. An affected-party delivery account must be account-typed and not predate the observation. Unavailable/unsafe/not-applicable exceptions are visible review blockers, not invented assent. Partial delivery and overdue escalation remain distinct blockers. Even a complete six-stage trace returns `remedy_effectiveness: NOT_ESTABLISHED`.

Reports always retain `authority: NONE`, `execution_enabled: false`, `controller_closure: SUPPLIED_UNVERIFIED`, `evidence_status: REFERENCES_ONLY`, `inventory_scope: SUPPLIED_INVENTORY_ONLY`, `freshness: CALLER_ANCHOR_ONLY`, and `semantic_assessment: NOT_PERFORMED`. Factual truth, actual independence, remedy effectiveness and operational conformance remain `NOT_ESTABLISHED`.

## Shadow outcome assessment plan

Module: `wac_offline.ops_study_v1`.

- API: `inspect_study(plan, context)`; `input_digest(value)`; `StudyError`.
- Plan/context/report schemas: `cortac.ops.study.plan.v1`, `cortac.ops.study.context.v1`, `cortac.ops.study.inspection.v1`.
- Returned status: `PLAN_TRACE_CONSISTENT` or `PLAN_TRACE_INCOMPLETE`.
- Phase: `DRAFT`, `PREPARED_NO_OBSERVATIONS` or `OBSERVATIONS_SUPPLIED`. No phase is a completed study or an empirical-success verdict.

The immutable plan is separate from later observation context, avoiding a circular preregistration digest. The caller pins study ID, version, full plan digest, designated assessor/verifier and exact independence evidence. Plan and registration bind both actors before observations. Unknown declared control blocks; disclosed role/party/control conflicts reject. Assessor and verifier source claims remain unverified. Independence freshness over the entire observation span is **not implemented** and is explicitly returned as `independence_over_study_span: NOT_ESTABLISHED`.

The plan must contain exactly MINIMAL and FULL arms binding the same supplied condition-set digest, and exactly five endpoint definitions/criteria: mistaken restrictions, missed harms, delay, residual injury and remedy completion. It also requires uncertainty, missingness, stopping, protected-group comparison, privacy/permission and evidence-source protocols. These narratives are required but their quality, ethics, authorization and scientific sufficiency are not determined. Neither module authorizes collection of real personal data.

Preregistration must match the pinned plan version/digest and actors, and strictly precede each observation. Independence/permission references must already be available by registration. Each observation must match plan version/digest, condition-set digest and assessor, and have all five endpoint rows. A reported endpoint requires value text and referenced observation evidence available by recording; a missing endpoint has null value and explicit missingness/uncertainty text. Per-arm reported/missing counts remain visible. Missing registration, absent observations, missing comparison arm or missing outcomes block consistency. There is no statistical analysis, sample-size check, stopping-threshold evaluation, group-outcome computation, actual condition-equivalence validation or evidence truth assessment.

The APIs do not connect automatically to one another. A valid study record does not inherit the case-trace dossier's dependency checks, and a case trace does not inherit a study's preregistration. Human operational review must discharge both separate obligations where relevant. Existing historical fixtures are not treated as fresh assessment observations or sealed holdouts.

## Reproduce

From repository root:

```sh
python scripts/ops_integration.py
PYTHONPATH=package python -m unittest discover -s package/tests -p 'test_ops*.py'
python scripts/verify.py --report .local/verification.json
```

For Windows, set `PYTHONPATH` with the shell's normal environment syntax, or run `python -m unittest discover -s tests -p "test_ops*.py"` from `package/`.

The fixed trace controls include known malformed/stale inputs and explicit limitation controls. Study tests include plan substitution, chronology, evidence, missingness and authority-boundary controls. These exposed synthetic cases are regression checks, not blinded validation, semantic acceptance tests, model trials, external operational outcomes or comparative-effectiveness evidence. Consult fresh receipts for actual counts, platform and pass/fail results.
