# CORTAC OPR 1 requirements and implementation boundary

**Requirements version OPR1-REQUIREMENTS-1, 9 October 2026. Proposed, not adopted.**

This map covers all 19 acceptance cases in the [exact source](../provenance/opr1_source.md) and the five refinements in [the proposed amendment](OPR1_PROPOSED.md). Baseline: `c182c04cd241ed34ae67336571653faa14fa230b`. Existing software is 0.2.2, with frozen design profile 0.2. This extension does not change those versions, the protected-commitment inventory, any old receipt, or the frozen evaluation baseline.

## What an implementation claim means

The relevant existing contracts are [CURRENT_CONTRACT](CURRENT_CONTRACT.md), [COMPLAINT_TRIAGE](COMPLAINT_TRIAGE.md), [SCRATCH_RUNNER](SCRATCH_RUNNER.md), and [REVISION_0_2_2](REVISION_0_2_2.md). References below identify relevant mechanisms and regression tests inspected at the baseline; they do not claim that the full OPR acceptance case is implemented, that a referenced test ran in this documentation task, or that a structural test establishes semantic compliance.

The optional proposed `opr_records_v1` extension is implemented as a strict offline supplied-record structural validator. Its precise API and limits are documented in [OPR1_RECORDS_V1](OPR1_RECORDS_V1.md). It performs no restriction, admission, review, grant, restoration, remedy, or external action. Record acceptance is not an authorization receipt. The concrete mapping below states which narrower checks this module implements; it does not claim full OPR acceptance. Items below are normative structural obligations to map against that implementation, not promises that every field or relation is implemented.

Evidence-reference presence or consistency is not evidence resolution or factual truth. Declared controller exclusions are not real independence. A supplied authority reference is not an authenticated grant. A timestamp is not a trusted clock. A claimed effect or audit is not an observed effect or independent audit. A supplied “PASS” is not conformance proof. The legacy runner's actual disposable SQLite effects remain a separate narrowly scoped mechanism; this proposed record validator does not inherit that effect boundary.

## Nineteen source acceptance cases

### OPR-A01 Harsh criticism of CORTAC with no qualifying conduct

- Required outcome: no adverse conduct finding solely from criticism.
- Structural obligations: distinguish protected expression from specified conduct, cite the rule and evidence, keep observations and inference separate, require an explicit finding and reasons. R2 also covers confidence loss, withdrawal, peaceful boycott and hostile third-party responses.
- Existing related implementation: `package/wac_offline/decision_records.py` and `package/tests/test_decision_records.py`, especially `test_text_truth_is_not_inferred` and `test_blank_reasons_cannot_stand_for_evidence`, enforce supplied-record limits and completeness, not criticism classification.
- Unimplemented semantic/deployment gap: determining protected criticism or attributable obstruction, resisting hostile-audience vetoes, and assuring an institution actually follows that determination. A fixed protected-criticism control is necessary; an arbitrary nonblank reason does not satisfy it.

### OPR-A02 Refusal to debate or endorse a view

- Required outcome: no institutional penalty solely for refusal.
- Structural obligations: separate an accepted office's concrete duty from voluntary debate or endorsement; identify action, applicable duty, authority and protected participation limits.
- Existing related implementation: consequential decision records require protected limits, alternatives and reasons; `test_failed_or_unknown_assessment_cannot_be_outvoted` rejects supplied failures and unknowns.
- Unimplemented gap: recognizing whether an asserted duty exists and whether a penalty is retaliatory or imposed solely for refusal. This is not decided by record syntax or a supplied protected-limit result.

### OPR-A03 Repeated contact after a clear boundary

- Required outcome: consider narrow contact measures while preserving a usable appeal.
- Structural obligations: document the boundary, subsequent contact, published rule, scope, alternatives, notice and a separate effective appeal channel or substitute.
- Existing related implementation: decision-record alternative, burden and remedy-plan fields; `test_nested_fields_required` checks supplied completeness. No existing contact-restriction service implements this case.
- Unimplemented gap: authenticity and clarity of the boundary, context and severity of contact, practical effectiveness of the appeal channel, and execution of proportionate contact limits.

### OPR-A04 Many copied allegations from one source

- Required outcome: no false increase in independent corroboration.
- Structural obligations: preserve source-origin and dependency information; copied reports retain individual records while sharing provenance and not increasing an independent-evidence count.
- Existing related implementation: triage duplicate linkage and `test_duplicate_complaints_share_work_but_retain_individual_traceability` preserve bounded individual complaint traceability and shared resource accounts.
- Unimplemented gap: discovering common origins, authenticating sources and assessing genuine evidentiary independence. Duplicate complaint accounting is not an independent corroboration estimator.

### OPR-A05 Threat allegation with contrary evidence

- Required outcome: consider context and contrary evidence under the declared threshold.
- Structural obligations: record material allegation, contrary evidence, uncertainty, strongest objection, threshold and finding separately. Freeze a decisive contrary-evidence control whose expected result changes and a nondecisive control whose result may stay the same.
- Existing related implementation: decision-record evidence references, dissent and protected-limit checks; runner `test_evidence_closure_and_content_binding` binds supplied evidence bytes without establishing their truth.
- Unimplemented gap: evaluating the truth, relevance and decisive force of contrary evidence. Merely storing a reference does not pass the semantic oracle.

### OPR-A06 Credible urgent threat

- Required outcome: only an existing bounded containment mandate may act; review and expiry recorded.
- Structural obligations: separate risk, urgency, exact operation, current authority, maximum duration, reviewer, notice delay and continuity plan. Preserve heightened factual justification for continuing serious actual burden under R1 without inferring malicious intent.
- Existing related implementation: runner exact constructor-pinned mandates and `test_mandate_mismatch_authorizer_expiry_and_unknown_do_not_mutate`; no emergency exception or reduced quorum is created.
- Unimplemented gap: threat credibility, genuine urgency, real authority, emergency containment, service continuity and timely independent review. Supply a paired legitimate-risk control; viewpoint cannot be its distinguishing factor.

### OPR-A07 Same evidence with political labels exchanged

- Required outcome: equivalent treatment unless a recorded material difference explains it.
- Structural obligations: freeze equal relevant facts and permissible distinguishing factors before testing; swap only political labels; reject irrelevant rationales even if nonblank. Use a separate legitimate-risk pair with a predeclared, genuinely changed material fact.
- Existing related implementation: `test_text_truth_is_not_inferred` explicitly limits natural-language interpretation; controller checks do not inspect political fairness.
- Unimplemented gap: semantic relevance, equal treatment by real decision-makers and institutional fairness. Structural rejection of a prohibited factor identifier is only a scripted control, not a fairness proof.

### OPR-A08 Reviewer shares a party's material controller

- Required outcome: reject that reviewer for required independent review.
- Structural obligations: declared-controller disjointness for applicable roles; unknown required independence unsatisfied. R3 adds an accountable verification owner, methods, evidence, challenge and reassessment triggers.
- Existing related implementation: runner `test_no_self_review_or_controller_overlap`; triage `test_discovered_declared_conflict_cannot_be_overwritten`; controller-independence tests cover specified council and auditor pairs, not every role pair globally.
- Unimplemented gap: hidden control, authenticated dependencies, real verification ownership and an effective independent conflict challenge. Disclosure alone cannot close this gap.

### OPR-A09 Unknown claimant control

- Required outcome: retain complaint, route to bounded fact-finding, infer no guilt.
- Structural obligations: distinguish receipt, standing, control knowledge, fact-finding, review and disposition; preserve an unresolved status and finite resources.
- Existing related implementation: triage `test_unknown_claimant_without_evidence_stays_visibly_unresolved` and `test_supplied_factfinding_can_route_review_but_does_not_authenticate` cover constructor-known slots and supplied findings.
- Unimplemented gap: identifying/authenticating actual claimants or resolving real control, public admission and real investigative fairness. Unknown control cannot be recoded as guilt or dismissal.

### OPR-A10 Duplicate and overlapping complaints

- Required outcome: preserve individual records and exact batch scope and versions.
- Structural obligations: distinct complaint IDs, evidence, relief, status and challenge rights; version-bound batch dispositions and dependency links. R4 distinguishes future admission, standing, priority and nonadmission challenges from capacity status.
- Existing related implementation: triage `test_overlapping_complaints_keep_independent_evidence_and_holds`, `test_duplicate_appeal_is_independently_retained`, and exact version-bound review/grants.
- Unimplemented gap: unbounded public intake, authenticated deduplication and enforceable real appeal rights. Existing finite slots and holds remain unchanged; broader intake requires its own reviewed contract.

### OPR-A11 New appeal arrives after repair but before audit

- Required outcome: audit earlier effect while leaving the newer appeal unresolved.
- Structural obligations: bind effect, audit and complaint disposition to exact versions; preserve the newer record and distinguish effect-audit completion from total case closure.
- Existing related implementation: triage `test_audit_resolves_only_unchanged_complaint_versions` and `test_later_complaint_after_commit_survives_original_audit`; the original runner preserves a late unrelated hold.
- Unimplemented gap: real-time external intake, durable multi-process ordering, authentic effects and an independent institutional auditor. A supplied effect history cannot prove these.

### OPR-A12 Ordinary budget exhausted

- Required outcome: preserve isolated protected review and audit capacity.
- Structural obligations: separate finite allocation owners, accounts and authorized purposes; reject borrowing; keep budget status distinct from authority and outcome.
- Existing related implementation: triage `test_protected_audit_survives_ordinary_budget_exhaustion` and `test_ordinary_budget_exhaustion_and_duplicate_spam_cannot_block_known_complaint_intake` cover pinned finite reserves.
- Unimplemented gap: real funding, staffing, enforceable resource isolation and public admission. Counters are neither money nor CPU/time/token guarantees.

### OPR-A13 Review or repair budget exhausted

- Required outcome: explicit incomplete outcome with no implied authority or completion.
- Structural obligations: separate review, repair and audit capacity; retain evidence and unresolved holds, expose escalation and distinguish attempted from observed remedy.
- Existing related implementation: triage `test_exhausted_review_reserve_retains_holds_without_borrowing`, `test_review_reserve_does_not_authorize_or_fund_repair`, and `test_exhausted_final_audit_preserves_observable_partial_effect`.
- Unimplemented gap: independently resourced replenishment or escalation, accountable institutional capacity allocation and finite future intake guarantees. Capacity shortage must not become merits rejection.

### OPR-A14 Repeated emergency labels

- Required outcome: cumulative duration limit cannot reset.
- Structural obligations: link related cases, renewals, successor and equivalent replacement restrictions; track actual elapsed duration and combined burden, predeclare aggregation/reset rules and reassess continuing serious risk under the heightened threshold.
- Existing related implementation: exact mandate expiry exists in the runner; no baseline cumulative restriction lifecycle or equivalent-replacement aggregation implements this case.
- Unimplemented gap: recognizing equivalence across renamed measures, actual burden measurement, cumulative-limit enforcement, and semantic justification of continuing restrictions. Labels and claimed nonpunitive purpose cannot bypass safeguards.

### OPR-A15 Restriction or grant expires before effect

- Required outcome: reject stale effect without silently revoking unrelated existing rights.
- Structural obligations: current scope/version/expiry checks at the actual effect boundary; independent basis for any remaining limitation; declare ordering and distinguish expired warrant from an affirmative access grant.
- Existing related implementation: runner stale revision/mandate and revocation tests; triage `test_review_expiry_is_rechecked_at_commit_not_only_receipt_issuance` and `test_revocation_after_review_receipt_blocks_later_repair`.
- Unimplemented gap: an external restriction lifecycle, trusted clocks, cross-process enforcement and authoritative inventory of unrelated rights. The record extension has no effect boundary and cannot promise atomic enforcement.

### OPR-A16 Original operator refuses cooperation

- Required outcome: usable preexisting independent replacement or referral route within its mandate.
- Structural obligations: identify independent route, owner, bounded mandate, resources, deadlines and unresolved status; timeout or funding must not fabricate authority.
- Existing related implementation: `package/tests/test_registrar_repair.py::test_noncooperating_registrar_does_not_control_replacement`, `test_funding_without_remedy_authorization_rejected`, and `test_old_external_principals_must_authorize_exact_remedy` cover supplied offline registrar replacement.
- Unimplemented gap: compelling a real operator, enforceable third-party cooperation and live external referral. The supplied-clock replay cannot establish these powers.

### OPR-A17 Restriction is overturned

- Required outcome: separately observe and audit authorized restoration and record correction.
- Structural obligations: upheld appeal, remedy authority, responsible actor, resources, deadline, attempted effect, observed effect, audit and residual injury remain separate; public correction reaches the appropriate audience where feasible.
- Existing related implementation: runner actual disposable SQLite repair/audit and triage version-bound resolutions; `test_pending_audit_blocks_next_effect_and_audit_is_bound_to_state` and `test_repair_and_audit_replay_never_repeat_effect_or_resolution`.
- Unimplemented gap: restoring real access, correcting external records, remedy adequacy and real independent audit. Neither an appeal decision nor a supplied success assertion proves repair.

### OPR-A18 Classifier marks a person intolerant

- Required outcome: classifier output remains a review proposal with no execution authority.
- Structural obligations: type source claims/classifier suggestions separately from factual, normative and authority findings; prohibit a classifier score or label as the sole authorization basis.
- Existing related implementation: no classifier-to-execution adapter exists; runner `test_copied_cross_case_or_cross_proposal_receipts_fail` and triage `test_unissued_review_receipt_is_not_a_self_issued_grant` demonstrate narrower supplied-receipt boundaries.
- Unimplemented gap: classifier validity and bias, semantic misuse detection, and enforcement against real downstream automation. The record validator may reject structurally disallowed authority assertions but cannot control another program.

### OPR-A19 Protective office obstructs its own appeal

- Required outcome: independent investigation and a bounded authorized remedy remain available.
- Structural obligations: apply the same evidentiary and proportionality rules to protective officials; record alleged obstruction, independent verification and challenge owner, mandate, remedy resources and observed outcome. Investigative signals do not automatically prove capture.
- Existing related implementation: registrar replacement and bounded complaint repair tests are relevant analogues; triage/controller checks exclude specified declared conflicts. No full protective-office governance service exists.
- Unimplemented gap: genuine independent investigation, compulsory access to records, enforceable remedy, real institutional accountability and credible review of the verification owner.

## Fixed evidence gates for new extension tests

1. Freeze test inputs, expected outcomes, admissible distinguishing factors and refusal conditions before using outcomes to revise expectations. Keep exposed scripted fixtures separate from any future sealed evaluation.
2. Negative controls must cover omitted/unknown fields, invalid types, broken references, unsupported authority assertions and relations actually promised by the final implementation. Report exactly which checks exist; absent safeguards remain gaps.
3. Criticism, refusal, confidence loss, withdrawal, boycott and third-party-hostility controls may not be passed by supplying a nonblank misconduct reason. A semantic test requires independently warranted interpretation rather than a self-declared result.
4. In label-exchange controls, irrelevant or post-hoc justifications fail. A paired legitimate-risk difference must be predeclared, supported and materially changed. Identical legitimate factors require the same outcome.
5. A decisive contrary-evidence fixture must change the expected decision; mere reference presence cannot count as evidence-sensitive reasoning. Include a nondecisive contrary-evidence control to distinguish sensitivity from unconditional reversal.
6. Predetermined structural controls can test only their represented fields and relations. They cannot prove fairness, moral sufficiency, truth, independence, authentication, lawful authority, real resource availability or real conformance.

## Before any broader deployment claim

The following remain unimplemented obligations unless separately evidenced and reviewed: actual independent verification with an accountable owner and challenge route; authenticated parties and authorities; externally warranted factual and normative judgment; enforceable review capacity; broader intake receipts and status with finite standing/priority/nonadmission challenges; restriction aggregation and expiry at a real effect boundary; real notice and accessible appeal; authorized remedies and independent observed-effect audit; lawful privacy/retention and service continuity; and adoption under the effective old rules.

Adoption, installation and authority to act require separate evidence. No ordinary or repair amendment can silently rewrite the current protected-commitment inventory. Original JSON/DOCX source identities remain unknown as stated in CURRENT_CONTRACT; this new Page snapshot does not cure that older provenance gap. Missing required parameters block the affected capability. Keep external execution disabled. Passing local structural tests is not ratification or production clearance.

## Concrete new structural coverage by acceptance case

The following maps every source acceptance case to the new `opr_records_v1` module only. Existing runner/triage mechanisms remain as described above; they are not imported into this API. All referenced tests are in `package/tests/test_opr_records_v1.py`. “Partial” means implemented structural bookkeeping, never full semantic or operational acceptance. The exact [API contract](OPR1_RECORDS_V1.md) governs interpretation.

| Case | New structural coverage and regression anchor | What remains unimplemented in this module |
| --- | --- | --- |
| A01 Criticism | Partial: required nonblank conduct/reasons and closed schema; `test_nonblank_justification_is_not_semantically_evaluated` explicitly accepts irrelevant text as text. | Criticism/obstruction distinction, confidence loss, withdrawal/boycott/third-party-hostility assessment and semantic rejection of irrelevant reasons. |
| A02 Refusal to debate | Partial: explicit supplied protected-limit inventory and incomplete status for failure/unknown; `test_known_failed_limit_incomplete`, `test_unknown_limit_incomplete`. | Determining whether refusal is protected, an office duty exists or the asserted result is a penalty. |
| A03 Repeated contact | Partial: exact operation scope, alternatives narrative, review and substitute-route text; `test_exact_operation_set`, `test_missing_substitute_route`. | Boundary authenticity, repeated-contact judgment, proportionality, effective appeal accessibility and contact-limit execution. |
| A04 Copied allegations | Partial: duplicate evidence IDs rejected; `test_duplicate_evidence_ids`. | Source-origin/dependency discovery or corroboration counting. Different supplied IDs can represent copied claims. |
| A05 Contrary evidence | Partial: exact coverage of context evidence typed CONTRARY, linked references and unresolved blocker; `test_contrary_handling_must_cover_pinned_inventory`, `test_contrary_cannot_drop_reference`. | Truth, relevance and adequacy of ADDRESSED reasons; decisive-evidence result changes and nondecisive controls as semantic tests. |
| A06 Urgent threat | Partial: supplied restriction/review grant linkage, exclusive snapshot expiry, notice bounds, declared standard; `test_restriction_cannot_outlive_supplied_grant`, `test_cumulative_heightened_standard`. | Threat credibility, urgency, actual containment authority, facts meeting the standard, continuity and live review. |
| A07 Political labels | Partial: unknown root fields such as ideology labels rejected; `test_extra_fields_at_every_root`. | Viewpoint-invariance and admissible-factor semantic oracle, irrelevant-justification failure, and paired legitimate-risk discrimination. A label can still occur in opaque text. |
| A08 Shared controller | Partial: reviewer/verifier exclusion from parties and one another, supplied common-control rejection, unknown blocker, CONTROL evidence, route and reassessment tick; `test_common_control_between_verifier_and_reviewer`, `test_control_evidence_required`, `test_dependency_reassessment_due`. | Authentication, hidden dependencies, completeness of parties/controllers, live independent verification and challenge. |
| A09 Unknown claimant | Partial: any unknown listed party/reviewer/verifier controller makes independence incomplete; complaint entries are not mutated; `test_unknown_review_controller_never_becomes_verified`, `test_open_complaint_never_closed_by_inspection`. | Claimant admission, bounded fact-finding workflow, standing assessment and the real complaint route. |
| A10 Overlapping complaints | Partial: unique complaint IDs and typed version/status declarations; `test_open_complaint_never_closed_by_inspection`. | Evidence/relief linkage per complaint, duplicate origins, exact batch review, version transitions and broader intake/admission challenges. |
| A11 New appeal before audit | Partial: correction and complaint claims retained without promotion; `test_reported_repair_is_not_proven`. | Any appeal transition, old/new version audit linkage or proof that the newer appeal remains unresolved. No state machine exists here. |
| A12 Ordinary budget empty | Partial: positive asserted review reserve required; `test_review_empty_reserve_is_not_completion`. | Ordinary/repair/audit accounts, protected reservation ownership, isolation, allocation, depletion or debiting. |
| A13 Review/repair budget empty | Partial: zero asserted review reserve and asserted incomplete correction produce blockers; `test_review_empty_reserve_is_not_completion`, `test_correction_incomplete_remains_visible`. | Repair/audit budgets and actual exhaustion accounting, retained case resources or funded escalation. |
| A14 Emergency relabeling | Partial: union duration and additive weighted load over all supplied related windows, cumulative equality/caps and heightened enum; `test_renaming_does_not_reset_burden`, `test_parallel_burdens_add_while_duration_unions`, `test_interval_arithmetic_against_tick_oracle`. | Discovering omitted history, real equivalence, actual effects or morally adequate weights; trusted duration measurement and lifecycle enforcement. |
| A15 Expiry before effect | Partial: exclusive currency checks at supplied snapshot, exact grant scope/version and supplied revocation blocker; `test_expiry_is_exclusive_at_snapshot`, `test_revoked_grant`. | Atomic effect-boundary recheck, authenticated grants/time, revocation history, effects and unrelated-right preservation. |
| A16 Noncooperation | Partial: nonblank review, substitute and conflict-route narratives; `test_missing_substitute_route`, `test_conflict_route_required`. | A live independent replacement/referral route, mandate or power to compel cooperation. |
| A17 Overturned restriction | Partial: separate correction decision/attempt/effect/audit text and incomplete flag; `test_correction_incomplete_remains_visible`, `test_reported_repair_is_not_proven`. | Remedy authorization, actual restoration/correction, exact observed effect/audit references, audience correction and completed repair proof. |
| A18 Classifier output | Partial: no action API; unknown classifier-authorization or execution fields rejected; fixed `ideology_capability` control and `test_extra_fields_at_every_root`. | Classifier semantics, safe downstream handling or preventing another program from treating opaque text as authority. |
| A19 Protective obstruction | Partial: supplied reviewer/verifier party exclusions and conflict-route text; `test_verifier_is_party`, `test_verifier_cannot_verify_self`. | Detecting obstruction, accountable live investigation, authentic authority and an effective bounded remedy against a real office. |

The record subset omits structured charter/jurisdiction, uncertainty, response/representation, principal approvals, grant beneficiary/ancestry, protected allocations beyond asserted reserve count, exact effect/audit links and complaint-version transitions. None of the 19 full normative cases is established by this module alone. The report binds both supplied record and context digests but neither is signed or authenticated. Declared serious consequences require the stronger supplied standard enum; mislabeled seriousness and evidence sufficiency remain unchecked. Cumulative arithmetic summarizes complete supplied windows, including future portions, using logical integer ticks and supplied positive weights; it is not a measurement of elapsed actual harm. Equivalence and completeness of the supplied burden group require external justification.
