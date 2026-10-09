# CORTAC OPS 1 requirements and implementation boundary

**Requirements version OPS1-REQUIREMENTS-1, 9 October 2026. Proposed only. No ratification, activation, or external authority.**

This map separates the institutional duties in [OPS1_PROPOSED](OPS1_PROPOSED.md) from existing proposal language, narrower software checks, and evidence still needed. It supplements [OPR1_REQUIREMENTS](OPR1_REQUIREMENTS.md), which remains the OPR acceptance-case map. OPS 1 does not imply that OPR 1 lacked evidence, independence, response, outcome-reporting, or remedy principles.

## Status vocabulary

- **Existing proposed duty:** already stated in OPR 1; not a claim of ratification or operational compliance.
- **OPS 1 proposed procedure:** normative operating detail added here; not self-executing.
- **Implemented structural subset:** an inspected offline supplied-input relation check, described narrowly below. It cannot establish the truth or completeness of its inputs.
- **Semantic or institutional gap:** factual, practical, or outcome evidence not established by supplied-record validation.
- **Not run:** no independent outcome study, real case process, consultation, hearing, remedy, or external action was conducted by creating this extension. Offline unit tests are a separate activity.

The opt-in [trace inspector](../package/wac_offline/ops_trace_v1.py) checks supplied context, evidence and objection links, declared independence currency, and a narrow remedy-stage profile. The separate [study inspector](../package/wac_offline/ops_study_v1.py) checks supplied plan, preregistration and observation relationships. The [offline API contract](OPS1_OFFLINE_V1.md) defines their exact accepted inputs. Neither has an execution adapter. Record acceptance is not a decision, grant, empirical finding, or conformance certificate.

## Requirements map

| Requirement | Existing proposed basis | OPS 1 addition | Implemented subset and remaining boundary |
| --- | --- | --- | --- |
| OPS-R01 Existing roles and bounded context | OPR 1 §§7, 14, 16 | Name authorized owners; bind current case, rule, evidence and review versions; preserve history and finite limits | Trace binding checks exact caller-supplied case, policy digest, version, predecessor digest and context digest; closed bounded schemas reject unknown fields. No authenticated history, actual role appointment, charter/jurisdiction verification or anti-rollback guarantee. |
| OPS-R02 Originals and provenance | OPR 1 §§4.2–4.3, 14 | Inspect originals and context; distinguish derivatives; verify source claims and common origins | Every supplied claim has original evidence IDs and a matching provenance-check inventory bound to each original's supplied version and digest, linked before the finding. Evidence versions/digests and supplied timing are checked. No bytes are fetched or authenticated; original status, completeness and independence of origins remain supplied. |
| OPS-R03 Counterevidence and contradictions | OPR 1 §§4.2, 4.5–4.8 and §15 R5 | Bounded counterevidence search; current claim and objection versions; substantive reconciliation or unresolved consequence | Exact supplied claim/finding and objection/resolution inventories; counterevidence assignment; objections bound to the current claim version; version and support links; blockers for supplied material unresolved or reopened objections. No discovery, sufficient-search, materiality, relevance, or truthful-resolution assessment. |
| OPS-R04 Response and warranted hearing | OPR 1 §§4.7, 8 | Determine whether an interactive hearing is needed and record its effect; preserve safe alternatives | Supplied hearing evidence links are checked; pending hearings block a complete trace; a reported held hearing requires evidence of kind HEARING. No notice delivery, hearing service, need determination, accommodation or fair-response assessment. |
| OPS-R05 Practical independence | OPR 1 §§7.2–7.6, 13.2 | Verify funding, appointment/removal, access, recusal and independent advice against actual arrangements | Reviewer and verifier each need all six declared dependency dimensions; role/controller exclusions and dependency evidence links are checked. Their actual arrangements, hidden controllers, access and advice quality remain unverified. |
| OPS-R06 Independence reassessment | OPR 1 §§7.5–7.6 | Link material change to the affected determination and reassess before further reliance | Declared dependency versions must match; changed-after-assessment, noncurrent dependency and due reassessment produce blockers. Assessment must precede findings and be current at the supplied remedy audit. No change discovery, trusted time, substantive reassessment or live replacement. |
| OPS-R07 Policy consultation | OPR 1 §§5.3–5.5, 16 | Material-change triggers; published problem, options, burdens and criteria; input from affected outsiders | Proposed operating duty only. No consultation schema, outreach, representative participation, or adoption process implemented. |
| OPS-R08 Consultation response and appeal separation | OPR 1 §§8, 12, 16 | Answer material input; reconsult major revisions; preserve individual appeal and separate ratification | Proposed operating duty only. No implementation of response relevance, meaningful consideration, consent or lawful adoption. |
| OPS-R09 Independent shadow assessment | OPR 1 §§13.5, 15 and R5 | Nonempty preregistered study with an independent assessor, initially without operational effects | Study plan/context pins, designated roles, supplied controller exclusions, evidence sources and preregistration links are checked. Missing registration or observations remain incomplete. No actual study, authenticated preregistration, or independence throughout a study is established. |
| OPS-R10 Comparator and outcomes | OPR 1 §§6, 13.5, 15 | Minimal and full processes in matching declared conditions; separate errors, harms, delay and repair | Exactly MINIMAL/FULL arms bind one supplied condition-set digest; five fixed endpoint names and supplied observation links are checked. No matched-case allocation, denominators, sample adequacy, content of conditions, outcome meaning or comparison statistics are validated. |
| OPS-R11 Uncertainty and stopping | OPR 1 §§4.2, 6.5, 13.5, 15 | Prespecify uncertainty, missingness, reference disagreement, stopping and reporting; protect fresh validation | Nonblank protocols and per-outcome uncertainty/missingness are required; missing outcomes remain visible. No uncertainty calculation, actual stop assessment, untouched holdout, sampling plan, completion window or empirical success is established. |
| OPS-R12 Comparable reasons and precedent | OPR 1 §§5, 6.5, 12.7, 14–15 | Version-sensitive comparisons, justified departure, privacy and reconsideration of bad precedent | Proposed operating duty only. No comparable-case search, relevance evaluator, fairness classifier, privacy enforcement or precedent correction service. |
| OPS-R13 Remedy specification and stages | OPR 1 §§11.2–11.3, 12.3–12.6 | Separate order/recommendation, acceptance, attempt, observation, audit and reported effectiveness; name owner, deadline and resources | Narrow six-stage prefix profile binds the complete supplied findings digest and checks actors, previous-event links, evidence chronology and kinds; the audit actor and declared controller must be separate from the owner/effect actors. Funding references, owner and escalation fields required. No authenticated authority, verified funding or actual effect. See profile limits below. |
| OPS-R14 Affected account and residual injury | OPR 1 §§5.3, 12.5, 12.7, 13.5 | Hear actual repair experience, retain disagreement and qualify partial effectiveness | Supplied injury/residual inventories and versions match; reported repair requires observation and audit evidence within the remedy's event scope; other residual states block completion. Account exceptions remain review blockers. No judgment of adequacy, consent, truth or actual repair. |
| OPS-R15 Remedy follow-through and exact closure | OPR 1 §§10.4, 11.5, 12.4–12.7 | Follow failures and deadlines; use existing escalation; correct affected audience; close only resolved objectives/versions | Incomplete remedies and overdue escalation are reported using supplied times. Remedy and injury versions are checked. No real follow-up, complaint-disposition state machine, newer-appeal closure control, audience correction, or enforced escalation. |
| OPS-R16 Separate adoption and execution | OPR 1 §§7.1, 9, 14, 16 | Preserve old amendment rules, protected inventory, quorum, opt-in and activation gates | Outputs retain authority NONE and execution disabled. No authenticated grant, appointment, ratification, live authority check or institutional enforcement is implemented. |

## Local structural tests and observed result

On 9 October 2026 at approximately 14:41 UTC, the following local command passed **110 tests: 70 trace tests and 40 study tests**. The trace suite includes **29 exposed synthetic controls**; these overlap its test count and are not additional independent cases:

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=package python -m unittest discover -s package/tests -p 'test_ops*_v1.py'`

The inspected test sources are [test_ops_trace_v1.py](../package/tests/test_ops_trace_v1.py), [ops_fixtures_v1.py](../package/wac_offline/ops_fixtures_v1.py), and [test_ops_study_v1.py](../package/tests/test_ops_study_v1.py). This is a result for the working-tree files inspected during this task, not a signed release receipt or an outcome evaluation. Representative trace mappings follow; all generated control tests use the prefix `test_control_`.

| Implemented relation | Named tests or controls | Limit |
| --- | --- | --- |
| Whole-input and caller binding | `test_full_input_digests`, `test_changed_context_without_rebinding_rejected`; controls `caller_head_mismatch`, `caller_policy_mismatch` | Supplied pins and digests are unsigned; no trusted head or archive. |
| Evidence versions and supplied timing | `test_evidence_digest_binding`, `test_evidence_version_binding`, `test_future_evidence`, `test_resolution_cannot_use_later_evidence` | No source bytes or trusted clock are resolved. |
| Complete supplied objection linkage | `test_objection_bound_to_claim_version`; controls `missing_counterevidence`, `deleted_objection_only`, `stale_claim_version`, `stale_objection_version`, `unresolved_material_objection`, `reopened_objection` | Cannot find evidence or objections omitted consistently from the entire supplied snapshot. |
| Provenance and hearing relationships | `test_provenance_bound_to_original_version`; controls `missing_original_check`, `provenance_after_finding`, `hearing_pending` | A record of verification or hearing does not prove the activity occurred or was adequate. |
| Required dependency dimensions and currency | `test_dependency_dimension_missing`, `test_independence_before_finding`; controls `expired_independence`, `changed_dependency`, `unknown_dependency`, `stale_dependency_version` | Checks declared change/status/time; no actual reassessment. |
| Reviewer/verifier exclusions | Controls `same_reviewer_verifier`, `unknown_controller`, `verifier_party_control` | Supplied controllers only; not real independence. |
| Remedy phase links and audit separation | Controls `missing_observation_phase`, `observation_wrong_evidence`, `broken_event_chain`, `audit_by_remedy_owner`; `test_no_verifier_self_audit_attempt`, `test_no_verifier_self_audit_observation`, `test_audit_owner_controller_overlap`, `test_audit_owner_controller_unknown` | Narrow fixed-order profile and supplied controllers; no actual effect or audit and no broad lifecycle support. |
| Remedy findings binding and causal order | `test_remedy_must_bind_current_finding_content`, `test_finding_before_remedy`, `test_observation_after_attempt`, `test_audit_after_observation`, `test_account_after_observation` | Supplied evidence times cannot precede the relevant preceding phase. Timing and effects remain unauthenticated. |
| Exact residual scope and incomplete repair | `test_residual_observation_must_match_event`, `test_residual_audit_must_match_event`, `test_waiver_is_not_repair`; controls `new_residual_version`, `stale_remedy_version`, `residual_referral`, `residual_repair_without_audit` | No complaint/appeal transition system or judgment of injury. |
| Missing account, delivery and due escalation | `test_account_exception_not_invented_account`, `test_no_remedy_events_no_completion`, `test_overdue_escalation` | Incomplete reporting only; no account retrieval, follow-up or escalation action. |
| Strict boundary and input safety | `test_no_mutation`, `test_nested_unknown_field`, `test_bool_integer`, `test_text_bound`, `test_oversized_inventory`, `test_no_truth_or_effect_claim`; control `unsupported_effect_flag` | In-memory structural checks, not control of downstream users or programs. |

### Tests that deliberately preserve limitations

`test_deleting_objection_and_all_its_links_is_not_detected_as_truth` demonstrates that coordinated omission from the trace and context can pass. `test_caller_can_reanchor_old_record_not_anti_rollback` demonstrates that the caller can supply a different historical anchor. The `consistent_fabrication` and `irrelevant_nonblank_reason` controls deliberately remain structurally consistent. These are limitation-preservation tests, not examples of verified facts or acceptable reasoning. Changing these controls into claimed factual or semantic successes would reverse their intended meaning.

### Trace profile limits beyond semantics

The trace schema requires supplied original-kind references and a single exact remedy-stage prefix: ORDERED, ACCEPTED, ATTEMPTED, OBSERVED, AUDITED, EFFECTIVENESS_REPORTED. It cannot represent all legitimate missing-original investigations, recommendations, refusal sequences, repeated attempts, multiple audits, compulsory remedies without an acceptance event, or partial-objective closure. A valid institutional duty does not wait for voluntary acceptance merely because this experimental profile includes that stage. Such cases require a separately reviewed representation; rejection by this inspector is not a merits decision.

The schema has no explicit remedy authority/grant field, normative completion-criteria evaluator, appointment machinery, complaint-disposition transitions, consultation record, or precedent system. A predecessor digest is just a supplied anchor. No authenticated event log, durable state machine, anti-rollback protection, discovery of omitted history, or evidence resolver is supplied.

## Study inspector scope

`inspect_study(plan, context)` checks exactly two named arms with a common condition-set digest; five named endpoint definitions and criteria; designated assessor and verifier and declared-controller exclusions; declared source inventory; typed evidence references and their supplied availability times; plan identity/version/digest; supplied preregistration before observation; and per-observation plan, assessor, condition, timestamp and endpoint bindings.

A REPORTED outcome needs a non-null bounded text value and observation-evidence reference. A MISSING outcome must have a null value. The inspector counts supplied reported/missing entries by arm and endpoint; it performs no statistics and does not interpret text values. Unknown controllers, absent required sources, missing preregistration, absent observations, absent arm coverage or declared missing outcomes remain visible blockers.

A plan with no observations remains DRAFT or PREPARED_NO_OBSERVATIONS and incomplete. Even PLAN_TRACE_CONSISTENT with OBSERVATIONS_SUPPLIED explicitly leaves study validity, completion and empirical superiority unestablished. Registration, time, evidence and privacy permission remain supplied and unverified. The inspector does not enforce stopping decisions or verify actual independence across the observation period.

The 40 study tests passed in the combined local run above. Representative mappings follow. No independent outcome study has been run.

| Implemented study relation | Named tests | Limit |
| --- | --- | --- |
| Empty plan and observation absence | `test_empty_plan_never_completes`, `test_draft_and_prepared_without_observations_are_incomplete`, `test_consistent_is_never_a_completed_or_valid_study` | Even a complete supplied trace does not establish study completion or validity. |
| Arm and endpoint inventory | `test_arm_inventory_and_equal_conditions`, `test_endpoint_inventory_cannot_hide_harms`, `test_one_arm_cannot_be_a_complete_comparison` | Same digest does not prove equivalent real conditions; five field names do not validate the measures. |
| Preregistration and evidence timing | `test_preregistration_strictly_before_observation`, `test_plan_change_cannot_reuse_preregistration`, `test_observation_bindings_all_checked`, `test_evidence_cannot_appear_after_record_it_supports` | Caller-provided logical chronology, not an authenticated external registration. |
| Declared independent assessment | `test_role_and_party_overlap_rejected`, `test_common_control_and_unknown_participant_rejected`, `test_unknown_controller_is_incomplete_never_verified`, `test_pinned_and_preregistered_control_evidence_cannot_change` | No actual independence verification or reassessment across the study period. |
| Missing outcomes and sources | `test_missingness_visible_for_every_endpoint`, `test_missing_outcome_cannot_contain_value`, `test_reported_outcome_requires_value_evidence_uncertainty_and_missingness`, `test_unregistered_source_rejected_and_absent_source_visible` | Counts of supplied entries only; no evidence resolution, missingness correction or statistics. |
| Explicit nonclaims | `test_coordinated_supplied_rewrite_is_not_authenticated_history`, `test_prose_and_values_not_semantically_adjudicated` | Coordinated rewrites and irrelevant but nonblank content can remain structurally consistent. |

### Inspected code identities

These SHA-256 values identify the files at the combined run. They are byte identities, not signatures, authentication, or a guarantee about subsequent edits.

| File | SHA-256 |
| --- | --- |
| `package/wac_offline/ops_trace_v1.py` | `b5c59662271e9ff470bd9f18bffa4e8f423b527aea6551c585edc45a5641742c` |
| `package/wac_offline/ops_fixtures_v1.py` | `64ab4e2c53fa13d620b37c961e0ce4bc9b8faf9c345f44b15c4ebf6fd2ba383d` |
| `package/wac_offline/ops_study_v1.py` | `61a53d5b90b7ef0f7a9672b0012ca024a4196cfb25e0e2aea7503806f6de7664` |
| `package/tests/test_ops_trace_v1.py` | `be0d078eb7cd1a631954d1d6779d539b32ae13bca0028fc16e2a3acf2eed0fd8` |
| `package/tests/test_ops_study_v1.py` | `5f2d532e4381f95b93ae1e19564ca840a73bb8e58ee994cf6f29ff2a288a971e` |

## Evidence needed beyond the inspectors

**Disputed facts and hearing:** inspect actual sources and context; test provenance and dependence claims; assess the strongest counterevidence; hear material factual and credibility disputes where warranted; give reasoned findings under the applicable threshold. Reference syntax and resolution enums cannot perform this work.

**Independence:** verify the actual financial, appointment, removal, access, advice, recusal and replacement arrangements, plus relevant changes. The verification owner and challenge route must themselves be independent for their tasks. Supplied declarations are not investigative findings.

**Consultation and comparisons:** establish that affected outsiders had usable access, material input changed or was answered in the reasoning, comparable cases were selected fairly, and private information was protected. These are evidence-bearing activities, not database completeness conditions.

**Outcome assessment:** preregister and conduct the bounded independent shadow study in OPS 1 section 4. Report case provenance, sampling rationale, comparator conditions, separately defined outcomes and denominators, uncertainty, deviations, and stopping decisions. Regression fixtures, synthetic demonstrations, and an empty plan cannot establish reduced mistaken restrictions, fewer missed harms, faster fair decisions, or successful repair. A shadow recommendation is not an observed institutional effect.

**Remedies:** establish authority and actual resources, attempted and observed effects, an independent audit, affected-party feedback or explicit missing-feedback status, residual injury, and version-specific closure scope. Distinguish an order from a recommendation; refusal or lack of enforcement power cannot be hidden by a completed instruction record.

## Current release and claim limits

- This map and both inspectors provide no conformance certificate.
- OPS 1 remains proposed and unratified; existing OPR 1 and frozen evaluation records remain separately identified.
- The inspectors perform no adjudication, restriction, hearing, consultation, appointment, payment, grant, restoration, external communication, or remedy.
- No independent outcome study has been run and no improvement in real institutional outcomes is asserted.
- Verified primary design references and their limited relevance appear in [OPS1_PROPOSED](OPS1_PROPOSED.md#design-sources-and-limits). Their publication does not confer CORTAC authority or validate this adaptation.
