# Oversight Registrar design and implementation boundary

This change places a procedurally bounded Oversight Registrar within the fifth authority function, Audit and Correction. It supplies an amended architectural specification and a separate, inert amendment replay model. The registrar checks the process for an already separately approved amendment. It cannot choose policy on its own, grant itself authority, or authorize execution.

The complete amended specification is `COMMONWEALTH_REGISTRAR_REVISION.md`. Its sections 1, 3, 6, 8, 10, 11, and 13 and Appendix A define the amendment lifecycle and institutional requirements. The original remaining text and source references are preserved. These additions are proposed requirements, not assertions that the cited baselines implement them.

## Institutional responsibilities

- Inquiry and Normative Review qualify the evidence and assess the proposal under the effective charter.
- The authorized Decision function and required external principals approve the exact proposed change under the currently effective rules.
- The Oversight Registrar checks notice, conflicts, approval authority and quorum, challenge handling, required principal approvals, exact old/new digests, and activation conditions. It records registration, a reasoned hold, or a reasoned refusal.
- The independently controlled gateway rechecks current conditions and conditionally activates the approved and registered proposal against its expected old policy epoch and digests.
- Independent appeal and replacement authorities address registrar error, conflict, and delay without manufacturing a missing approval.

The registrar is an office within Audit and Correction, not a sixth estate, a new external sovereign, or the genesis registry. Section 6's external registry anchors the initial manifest once. Subsequent authorized policy transitions preserve that immutable anchor and their entire history.

## Amendment lifecycle

1. Freeze the proposal, expected current policy epoch, exact old/new content and component digests, effects, evidence, and activation time.
2. Apply the current effective amendment rules, even when the proposal changes those very rules or the registrar and gateway implementation.
3. Obtain the separately authorized substantive decision and all required principal approvals against the frozen proposal.
4. Complete the current notice, conflict, quorum, challenge, and readiness gates. The registrar checks these and issues a bounded procedural record; registration itself changes no effective policy.
5. At activation, recheck freshness, authority, challenges and stays, timing, exact content, and required deployment attestations. Conditionally commit against the expected current policy epoch and old digests.
6. Advance the effective policy epoch, fence superseded-policy capabilities at effect boundaries, and preserve the activation receipt and history. A competing stale proposal needs reassessment under the new current rules.

No new institutional voting threshold or mandatory duration is invented here. Each deployment must instantiate eligible actors, quorum, notice and challenge periods, response deadlines, independent appeal and replacement authorities, and timing and persistence assumptions. Existing Byzantine validator quorum arithmetic does not determine amendment approval thresholds.

## Offline implementation

The isolated implementation is `package/wac_offline/amendments.py`, with dedicated record definitions in `package/wac_offline/data/amendment_records.schema.json`. It does not modify the existing frozen assignment profile. Its inputs, identities, domains, evidence, approvals, and timestamps are supplied synthetic declarations. They are not authenticated facts.

`AmendmentReplay` owns one local in-memory timeline. Its state explicitly reports `authority: NONE`, `execution_enabled: false`, and `controller_closure: SUPPLIED_UNVERIFIED`. It issues no signatures, live grants, or execution capabilities. A digest checks content identity, not truth, authority, institutional independence, or deployment integrity.

### Reproduce the bounded example

Run `python scripts/amendment_demo.py`, then `python scripts/verify.py`. The example reads `package/fixtures/amendment_example.json`; its actors, distinct domains, two-vote quorum, periods, and integer timeline are fabricated test configuration, not proposed institutional thresholds. Import `AmendmentReplay`, `digest`, and `validate_record` from `wac_offline.amendments` for local experiments. `state()` and `events()` return copies, not writable state handles.

The synthetic digest profile is precisely Python JSON with sorted keys, `ensure_ascii=True`, separators `(',', ':')`, and `allow_nan=False`, encoded as UTF-8 after the domain prefix `cortac.amendments.v1/`, record-kind name, and a NUL separator. SHA-256 covers those bytes. Strict schemas admit integers but not booleans as integers, floating-point numbers, unknown fields, or unrecognized scope claims. This named local serialization convention is not a claim of RFC 8785 compliance. All timestamps and periods use the same supplied integer unit; the example's units are arbitrary simulation ticks. A live clock and canonicalization profile require separate deployment specification and test vectors.

### Mapping of requirements to the model

| Requirement | Local behavior | Boundary or remaining work |
| --- | --- | --- |
| Current rules govern amendments | `_check` reads approvers, domains, quorum, registrars, principals, periods, and appeal actors from the current policy; the proposed policy is checked for well-formedness. | The caller supplies the initial current policy. No external registry authenticates that starting state. |
| Exact content and namespace | Canonical typed JSON SHA-256 digests bind the proposal, old/new policy, approval, procedure, and registration. Society and attempt identifiers cannot change. | All boundary code/configuration must be included in exact `Policy.content` by the caller. Omitted dependencies are not discovered. Separate production component inventories and deployment attestations are not implemented. |
| Separate substantive approval | `Approval` must affirm APPROVE, bind the proposal, and list eligible current decision makers meeting the configured distinct-domain quorum. | Statements are supplied, not signed or verified. Domain labels do not prove independent control. |
| Relevant external principals | Every modeled change requires the current policy's nonempty configured external-principal set. | This deliberately conservative subset does not classify whether a semantic change needs fewer or additional principals. It cannot establish legal authority. |
| Registrar conflicts and no self-grant | The registrar must be eligible under current rules and outside the declared domains of proposer and approvers; the proposer cannot supply decisive decision review. | This checks declared labels only. Real appointment, credentials, separation, and control verification are outside the model. |
| Notice and challenge process | Bound procedure inputs attest conflict clearance, complete challenge inventory, mandatory checks, chronology, closed intervals, and resolved challenges with eligible independent reviewers. | Boolean attestations and evidence references are not independently verified; notice recipients and delivery are not modeled. Notice and challenge periods run sequentially in this subset. |
| Registration deadline | `register` refuses after submission plus the current registrar deadline. | Late cases need independent appeal/replacement outside the prototype. No automatic scheduler, appointment, or replacement workflow is implemented. |
| Reasoned refusal | `refuse` records a reason, evidence references, deadline, and current appeal/replacement routes. | A failed `register` raises a reasoned exception but does not automatically append a refusal. The caller must explicitly record one. HOLD is a specification status, not a separately implemented record path. |
| Live local challenge state | `challenge` adds OPEN or STAY states across the current old-policy digest and epoch; re-registration, a renamed proposal, or another candidate cannot evade them. RESOLVED requires a currently eligible appeal actor outside the original and resolving cases’ involved declared domains. `invalidate` blocks all amendment activation in that modeled epoch. | This deliberately conservative subset applies holds to all amendments sharing the current policy epoch. Invalidation is terminal for that modeled epoch; no un-revoke or recovery API exists. OPEN/STAY and invalidation are unverified local inputs. Real standing, authoritative revocation, challenge discovery, timely delivery, and authorized recovery require external services. |
| Activation freshness and CAS | `activate` accepts only its exact locally registered certificate, reruns checks under one `RLock`, checks local challenge/invalidation state and due time, compares the old digest/epoch, then advances the local policy epoch. | One-process mutual exclusion only. No durable transaction, crash recovery, cross-process lock, distributed agreement, or independently enforced gateway is provided. |
| Replay safety | After one activation, duplicate or competing old-epoch activation fails as stale. | The specification requires a committed identical replay to return its existing result. The subset prevents a second transition by rejection instead; it does not implement durable idempotent receipt lookup. |
| Stale capability fencing | `is_current` tests equality of supplied policy digest and epoch, so superseded bindings fail that comparison. | This is not a capability check, authority-epoch implementation, or execution fence. A live gateway must enforce the policy binding on every actual effect. |
| Time and history | The model rejects regressing supplied integer time, does not commit the simulated clock on failed input, and retains a copied event list for that instance. | No trusted clock, uncertainty bound, persistent append-only log, independently witnessed checkpoint, or administrator resistance is supplied. |
| Lean routine lane and L2 | The revised specification preserves standing routine warrants and case-specific consequential safeguards. | This amendment-only model does not execute L1 or L2 work and cannot certify either lane. |

### Dedicated records

The executable schema defines `Policy`, `Proposal`, `Approval`, `Procedure`, `Registration`, `Activation`, `Refusal`, `ChallengeUpdate`, and `Invalidation`. These are deliberately limited synthetic records. Appendix A of the revised specification defines the fuller production contracts, including approval authority references, protected component digests, activation authorization and receipts, and registrar appeal/replacement records. The executable schema is not a claim to implement all fields in those normative contracts.

## Protected implementation changes and host control

The protected-change scope includes amendment rules, registrar mandate and review machinery, registration checks, policy storage, capability issuance and epoch fencing, gateway admission and activation code, and deployment configuration that can change their behavior. The effective old rules govern changes to these controls. A maintenance or emergency label cannot bypass that requirement.

The model can bind only supplied content. If a caller leaves a gateway binary, configuration, credential route, or policy dependency out of `Policy.content`, its omission is not detected. Even complete hash coverage would not prove that the named binary is running or that the host cannot replace it. The model does not install protected code or verify deployment attestations.

An administrator who can rewrite this module, process memory, policy files, database, clock, or credentials can bypass this application-level model. An actual enforcement claim needs a separately controlled reference monitor, closed alternate execution routes, authenticated principals, independent witnessing, protected storage, and declared compromise assumptions. Neither this amendment nor a passing synthetic test establishes those conditions.

## Evidence and release gates

The specification's registrar tests cover current-rule self-amendment, exact-content binding, missing approval and procedural evidence, conflicts, stale concurrent activation, replay, revoked or stayed registrations, activation timing, stale capability rejection, independent appeal/replacement, protected-code changes, and crash boundaries. These are required test outcomes, not reported production results.

The code's own tests can establish only local behavior with supplied fixtures. Read their recorded results separately; no test-pass count or execution outcome is asserted in this document. Institution-level notice, actual independence, authenticated principal approvals, administrator resistance, durable atomicity, deployment attestation, and live capability enforcement require additional evidence beyond this module.

The next implementation step is to instantiate the unresolved deployment parameters and integrate a reviewed, independently controlled enforcement and persistence adapter. Until that is demonstrated and authorized, the model remains offline and non-authority-bearing.
