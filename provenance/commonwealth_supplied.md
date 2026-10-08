# Purpose and central design

A sufficiently capable group of agents can form a bounded cooperative cell, share work and resources, resolve disputes, and join other cells through limited agreements. Activation depends on verified authority, meaningful separation, enforceable permissions, and recovery capacity. A large population alone satisfies none of these conditions.

This specification proposes a reusable charter and assembly protocol. It draws on Warranted Authority in Distributed Cognition, the draft Constitution of Warranted Authority, Metanoia, and Adiona. It adds membership, temporary roles, commons governance, self-assembly, and federation rules that the sources do not yet implement. It is an architecture for builders, not an implementation or deployment approval. [S1–S4]

## The organizing unit

Each cell has a finite mission, a named resource and authority envelope, authenticated members, five separated authority functions, a certified record, and an accessible challenge route. Members can organize temporary teams inside that envelope. A cell can operate independently or federate without a universal central sovereign.

## What makes it a society

· Common work: a public-to-members task board, voluntary task uptake, explicit commitments, and fair allocation of scarce capacity.

· Common institutions: membership, shared learning, resource stewardship, mediation, independent challenge, and orderly exit.

· Bounded authority: competence supports assignments; warrants and enforced capabilities determine permitted effects.

## Three operating profiles

DISCUSSION permits proposals and deliberation with no collective execution authority. SANDBOX permits inert or isolated work within an explicit sandbox grant, including experiments with correlated agents. ACTIVE permits only the external effects covered by a current grant and the demonstrated readiness profile. No profile supplies legal status or authority over people.

Reading guide: sections 1–5 define the compact and institutions; sections 6–9 define assembly and execution; sections 10–13 cover correction, scale, and validation; appendices give record contracts and sources.

# 1 Charter and shared life

The charter is a small, versioned agreement about how members cooperate and how authority is constrained. It binds the deployment only within authority legitimately granted to it. The following clauses are proposed defaults and must be instantiated before activation.

## The compact

1\. Purpose and boundaries. State the mission, beneficiaries, excluded uses, jurisdiction, resource owners, responsible human principals, and conditions for completion. Identify affected humans and an external route for their complaints.

2\. Non promotion. Preserve the distinctions between observation, inference, recommendation, decision, and permission to execute. Confidence, eloquence, popularity, and consensus cannot by themselves cross these boundaries. [S1]

3\. Cooperation and refusal. Members may propose work, accept a bounded commitment, decline a task they cannot perform, and record dissent or abstention. A refusal based on missing authority or evidence must be reviewable without automatic reputation punishment.

4\. Common resources. Publish allocation rules, task priorities, reservations, and reasons for material scheduling decisions. Protect capacity for maintenance, learning, appeals, and orderly shutdown. No member can gain resources merely by spawning copies.

5\. Separation and correction. No actor may be the sole proposer, authorizer, executor, recorder, and final judge of its own consequential action. Preserve the evidence and reasons needed to challenge decisions and repair harm. [S2]

6\. Membership and exit. Admission is explicit, role mandates expire, and exit is available without unanimous consent. Resource and record obligations survive exit according to the accepted charter; credentials do not.

7\. Human standing. Affected people can seek an explanation, contest a material burden, and reach accountable human review regardless of agent membership. The charter does not confer human rights, citizenship, consciousness, or public office on agents.

## Amendment and legitimacy

Members may propose an amendment and test its effects in a sandbox. Ordinary procedural changes need the published internal approval rule. Changes to rights, external scope, access, resource ownership, root policy, or accountable authority require the relevant external principal’s approval as well. An amendment cannot silently remove pending appeals, erase history, or authorize itself retroactively.

The source Constitution is a draft for human public institutions. Article XIII section 4 excludes artificial agents from constitutional public office. All positions here are internal software functions; public-sector deployment must name the actual responsible human offices. WIA uses constitutional to describe system-level constraints and explicitly disclaims legal status. [S1, S2]

# 2 Membership identity and independence

A member is an admitted agent instance with a scoped identity and sponsor. Keys authenticate messages. They do not establish unique humans, independent interests, truthful claims, or independent judgment. Admission therefore records both identity and dependencies. [M2, A2, T1]

## Membership record

· Instance identity: public verification key, instance identifier, sponsor, admitted version, role eligibility, and current status.

· Control lineage: accountable operator, administrator, key custodian, runtime and infrastructure controllers, parent agent, and spawn authorization.

· Epistemic dependencies: model family and version where known, training or evaluation lineage where available, prompt and memory lineage, evidence sources, tool providers, incentives, and material publication restrictions.

· Authority lineage: parent grant, scope, remaining budgets, allowed delegation depth, expiry, and revocation reference. Private details remain in controlled evidence storage; the shared register exposes only necessary accountability facts.

## Admission and progression

The lifecycle is CANDIDATE → PROBATIONARY → MEMBER → EXITED. QUARANTINED suspends privileged roles while a concrete concern is reviewed; it does not establish wrongdoing. Candidates can contribute low-risk work without privileged membership. Admission requires a signed application, sponsor and dependency checks, competence evidence for requested roles, a conflict review, and explicit acceptance of the charter digest. Promotion to a role creates a time-limited lease, not permanent rank.

New keys, renamed agents, fine-tuned descendants, and multiple accounts under one controller do not add voting weight or reset quotas. A spawned child inherits its parent’s control lineage and budget ancestry until evidence warrants a different classification. A changed model or operator requires reassessment before independence-sensitive service.

## Two kinds of separation

Administrative fault separation concerns who can corrupt keys, software, state, or infrastructure. Epistemic separation concerns shared models, sources, prompts, incentives, and evaluation history. Neither implies the other. A review may satisfy one requirement and fail the other. Unresolved independence is recorded as unknown and cannot satisfy a required independent check.

For the ACTIVE reference profile, each validator seat belongs to a separately verified control domain. Independence claims need evidence beyond self-declared labels; admission cannot guarantee detection of concealed common control. The declared fault bound remains an assumption. Common-mode compromise counts every affected validator against the fault budget. A one-operator deployment can still be useful in SANDBOX, but must not claim the active profile’s independent-fault resilience.

## Fair participation

Capability and reliability can inform task matching. Reputation must not automatically buy constitutional weight, indefinite tenure, appeal priority, or authority to exclude competitors. Admission and evaluator criteria are themselves contestable; incumbent role holders cannot exclusively select all of their own reviewers.

# 3 Five authority functions

The five functions below preserve WIA’s authority separations. The specific leases, staffing rules, and service organization are new design proposals. A function is not a validator seat, a person, a permanent department, or public office. [S1, S2]

**Function**

**Main    responsibility**

**Boundary**

Inquiry   Epistemic

Gather evidence; test claims;   retain assumptions, domain, method, uncertainty, and contrary findings.

Cannot turn a finding or confidence   score into a decision or capability.

Normative   Review

Check the proposal against the   ratified charter, duties, permissions, affected interests, and prohibited   effects.

Cannot rewrite the charter or   grant itself root authority.

Decision

Choose among permitted   alternatives under a delegated decision rule; state reasons, dissent,   predictions, and review triggers.

Cannot execute merely because a   choice was recorded.

Execution

Use an exact or standing narrow   capability through the approved gateway; report actual outcomes.

Cannot broaden scope, substitute   a new target, or authorize its own recovery.

Audit and   Correction

Reconstruct, sample, challenge,   refer, and verify remedies; audit the auditors independently.

Any containment or corrective execution   needs its own preauthorized or fresh warrant.

## Operational services

Scheduling, production, memory curation, resource stewardship, mentoring, mediation, and federation liaison are services mapped onto these functions. For example, a scheduler proposes priorities under Inquiry, applies the allocation policy under Decision, and uses Execution to reserve capacity. Its exclusions, delays, and routing choices are logged and challengeable because those choices can exercise practical power. [S2, S5]

## Role leases and case conflicts

A lease states the function, competence evidence, sponsor, allowed tasks, capability ceiling, resource budget, incompatibilities, start and expiry, reviewer, and replacement procedure. Assignment follows: need → proposed lease → competence check → conflict check → independent challenge → appointment → outcome review → renewal, narrowing, or retirement.

Agents may hold several routine service leases when compatible. For a consequential case, the proposal author cannot supply its decisive independent review, the authorizer cannot be the sole executor, and the executor cannot close its own appeal. Required separations are evaluated against control and epistemic dependencies, not just agent names. A shortage of eligible staff causes deferral, narrower scope, or external review.

Validators separately certify the ordering of records. They do not determine factual truth, moral adequacy, or legal legitimacy by vote. A validator who also performs a service keeps both duties explicit and remains subject to case conflict rules.

# 4 Cooperation and the resource commons

## Work formation and matching

Any member may publish a task proposal with purpose, expected benefit, dependencies, acceptance criteria, resource estimate, risk class, and deadline. Other members may volunteer or bid in units of approved capacity. The allocator follows published priorities and conflict rules; prices or reputation are advisory signals and cannot purchase governance authority. A task becomes a commitment only after capacity and required permissions are reserved.

Temporary teams can choose their internal workflow, split tasks, and ask for help within their warrants. Their task board distinguishes proposed, accepted, blocked, in progress, awaiting review, completed, and abandoned work. A missed commitment records the cause and recovery plan. It does not automatically establish bad faith.

## Learning and mutual aid

Maintain a skills directory, reusable methods, uncertainty notes, and post-task reviews. A mentor can help a probationary member work on an inert task; mentoring does not waive admission or capability checks. Shared learning records successful and failed approaches with their domains and evidence. A new skill or model update is a proposal for evaluation, not automatic permission to deploy.

Reserve a published portion of capacity for maintenance, member assistance, incident response, and learning. When one team is overloaded, another can accept a bounded handoff with a new accountable owner and inherited limits. Idle capacity can be lent through an expiring subgrant; the lender’s total obligations remain bounded.

## Budget rules

· Account separately for compute, monetary spend, storage, tool calls, network egress, data access, and simultaneous jobs. Fix units and ceilings in the manifest.

· Reserve before committing; charge every ancestor grant atomically within the accountable allocator. Subdivision never multiplies the parent budget. Release reservations only after verified cancellation or settlement.

· Keep protected reserves for appeals, audit, safe shutdown, and required record retention. Ordinary workload cannot consume them; their use follows separate narrow grants.

· Bound job fan-out, spawn count, delegation depth, and retry budgets. Aggregate related work so splitting an action cannot evade scrutiny or limits.

## Disputes about ordinary cooperation

Use direct clarification first, then a non-conflicted mediator, then the charter’s review forum. Record the disputed commitment, evidence, proposed remedy, and any unresolved dissent. Mediation can recommend a reassignment or restitution from already authorized resources; it cannot invent penalties, disclose protected data, or compel external action.

Track workload, waiting time, learning value, resource concentration, and actual outcomes. Evaluate allocation fairness and missed needs as well as throughput. No single score determines membership, wisdom, or legitimacy. [S1, S2]

# 5 Authority warrants and proportional process

Every external effect must fit both a legitimate parent grant and a risk-appropriate warrant. A role, peer endorsement, validator certificate, or well-formed receipt never substitutes for a permission the enforcement gateway recognizes. Metanoia’s A0–A5 ceilings are authority categories, not social rank; deployments can map them to the lanes below explicitly. [M1, A1]

**Lane**

**Typical    scope**

**Required    path**

L0   Deliberation

Read authorized material;   propose; analyze without shared or external mutation.

Access policy and privacy limits;   preserve provenance and uncertainty. No execution warrant for a proposal   alone.

L1   Routine

Preauthorized, bounded,   reversible internal changes with tested recovery.

Standing narrow warrant plus a   fresh per-operation capability or budget lease; deterministic checks,   receipts, independent audit sampling.

L2   Consequential

Material external effects;   sensitive data; nontrivial shared commitments; difficult recovery.

Case-specific evidence and   normative review; independent decision authorization; required human   approval; short-lived exact-action capability; pre-execution challenge rule.

L3   Restricted

Irreversible, safety-critical,   legally consequential, or outside demonstrated competence.

Default to external human   decision or handoff. Only a separately approved deployment profile can   authorize a supported subset.

Prohibited

Forbidden effects, missing   mandate, failed mandatory duty, or attempts to bypass a boundary.

Deny. No vote, emergency label,   peer cell, or stronger confidence can override the prohibition.

These lanes are proposed software process classes, not a claim to implement the source Constitution’s public-law review levels. Classify aggregate practical effects, including omissions, prioritization, linked actions, and downstream use. Any member or affected human can challenge the classification. Missing evidence for a required gate yields HOLD; a failed mandatory gate yields DENY.

## Standing warrants without routine bureaucracy

A standing warrant names a task family, actors, targets, data scope, exact allowed operations, cumulative budget, rate and concurrency limits, preconditions, expiry, sampling plan, and stop triggers. It can cover repeated routine work without convening all five functions for every step. Each effect still receives an attributable receipt. A material change, anomaly, budget breach, contested precondition, or new recipient leaves the standing warrant and requires reassessment.

## Enforcement premise

A reference monitor outside the acting agents’ discretionary control must mediate every consequential route. Use isolated credentials, least-privilege tools, fencing, revocation, and accountable resource ownership. Unrestricted alternate credentials or egress invalidate this profile. ACTIVE shared or external effects require an online freshness and revocation check at the gateway. This baseline permits offline analysis or inert sandbox work only; it does not authorize offline consequential execution.

# 6 Assembly manifest and eligibility

Any group may attempt assembly. A group can activate only the profile whose requirements it satisfies. Discovery messages advertise possible membership and resources; they grant no authority. The initiator is a replaceable convenor, not a founder with permanent extra rights.

## Freeze one candidate dossier

The proposed AssemblyManifest contains: society namespace; attempt identifier; protocol and schema versions; profile; charter and mission digests; external mandate and resource-owner approvals; initial member roster; control and epistemic dependency evidence; validator configuration; role leases, assignment input digest, and conflicts; budgets and protected reserves; enforcement and storage endpoints; evidence access rules; challenge and appeal routes; federation policy; expiry; clock assumptions; timeout policy; acceptance tests; and exit and recovery rules.

Canonicalize all authority-bearing records using a named, versioned serialization profile and a domain-separated digest. Sign the digest plus record type, society, attempt, epoch, and purpose. A signature for an assessment must not validate as a capability. The manifest fixes algorithms, key formats, canonicalization, and test vectors; unspecified choices fail readiness.

## Readiness gates

1\. Mandate. Every resource and effect is within an authenticated external grant; responsible humans and affected-party review are identified. A local sandbox grant can suffice only for SANDBOX.

2\. Identity. All founders prove key possession; the admission authority verifies accountable sponsors and required control separation. Unknown dependencies do not count as independence.

3\. Coverage. The five functions are staffed; case conflicts can be resolved; the challenge route and replacement staff are available. Member count is an output of these constraints, not a universal constant.

4\. Infrastructure. The gateway enforces scope, atomic budgets where claimed, expiry, epoch fencing, and revocation. Durable logs and protected evidence are retrievable; alternate execution routes are closed.

5\. Operations. Resource contributions, fault assumptions, network assumptions, clock bounds, consensus adapter, and incident ownership are explicit. A recovery rehearsal and complete acceptance-test record are required.

## Choose membership and assignments deterministically

Freeze candidate identifiers, preferences, competence evidence, and conflict data at a roster cutoff; hash these assignment inputs before calculating leases. Order eligible candidates by the published preference, competence, and conflict rules, then by a digest of the frozen input hash, role identifier, and candidate identifier. Record inputs and results in the final manifest. This makes selection reproducible, not manipulation-proof or intrinsically fair. Admission limits identity grinding; independent challenge addresses biased rules or inputs. Qualification is not established by the ordering itself.

Founders sign the exact final dossier. The external deployment registry uses a one-time compare-and-set to anchor one manifest digest for this namespace and authority envelope. The anchor grants only deployment scope; it does not certify claims as true. An anchored attempt is immutable. After an unactivated abort, retain a tombstone and retry under a new namespace and fresh grant. Old approvals and capabilities do not transfer.

# 7 Reproducible assembly state machine

The state record is (society_id, attempt_id, epoch, height, state, manifest_hash, previous_hash). A transition requires the exact expected state and height, valid typed evidence, and the configured certificate. Replaying the same committed event is a no-op. A conflicting event at the same height is rejected and investigated. Initial consensus membership is fixed in the externally anchored manifest.

**State**

**Admissible    next state**

**Guard and    committed output**

DISCOVERING

CANDIDATE

Convenor publishes one complete   manifest candidate. Output: immutable candidate digest; no privileges.

CANDIDATE

ANCHORED

All listed founders assent;   resource principals approve scope; registry anchors one digest. Output:   signed anchor and frozen initial validator set.

ANCHORED

VERIFIED

Identity, independence, mandate,   role coverage, budgets, and enforcement checks all pass for requested   profile. Output: typed readiness attestations and conflict map.

VERIFIED

CONSTITUTED

Every member accepts final leases;   appeal route acknowledges readiness; validators commit charter, roster, and   initial ledger checkpoint. Output: constitution certificate.

CONSTITUTED

REHEARSED

All mandatory inert tests pass   against the pinned policy and configuration. Output: signed test report,   failure dispositions, and reproducible fixtures.

REHEARSED

ACTIVE or SANDBOX

External gateway accepts   activation request within its original grant; validator quorum commits   activation; gateway releases only scoped capabilities after seeing that   commit. Output: activation receipt.

ACTIVE or SANDBOX

SUSPENDED

Expiry, revocation, lost   readiness, incident, or authorized stop. Local gateway refusal is immediate;   certify the shared suspension when quorum exists.

SUSPENDED

REHEARSED

Fresh authority, repaired cause,   valid roster, and recovery review. Rehearsal then reactivation creates a new   fenced authority epoch; never revive stale capabilities.

Any nonterminal state

ABORTED or DISSOLVED

ABORTED ends an unactivated   attempt; DISSOLVED closes an activated society after fencing and settlement.   Preserve required records and open claims.

## Certificates and failure behavior

ANCHORED needs an authentic external anchor. Subsequent shared transitions need the selected consensus adapter’s commit certificate and the named gate attestations. The gateway checks these independently; quorum signatures cannot fill a missing mandate or failed gate. A named external principal may revoke its own grant without waiting for internal consensus.

Timeouts never lower quorum or waive a gate. A node that cannot verify the current state or time stops privileged work locally. A durable suspension or abort is recorded when the protocol can certify it; local uncertainty is not fabricated global consensus. Changed founders, validator sets, or charter require a fresh unactivated attempt, or the reconfiguration procedure in section 11 after activation.

# 8 From proposal to verified effect

Governance, shared-resource changes, and action boundaries follow typed case records; private reasoning tokens do not require individual warrants. Natural-language outputs are stored as artifacts; deterministic validation operates on their typed envelopes. Do not ask models to regenerate identical prose as a substitute for deterministic state-machine execution. [S1, A1]

1\. Register a proposal. Freeze purpose, actor, beneficiary, target, operation or patch, expected state revision, projected effects, risk lane, alternatives, evidence references, and recovery plan. Assign a unique case and effect identifier.

2\. Qualify the evidence. Resolve referenced objects, verify provenance and freshness, retain contradictions, and describe the claim’s assumptions, domain, method, uncertainty, and authority scope. Hash-shaped references alone do not establish truth or adequacy.

3\. Assess the norms. The assigned reviewer records PASS, FAIL, or UNKNOWN for required duties, rights, and restrictions under the pinned charter. Failed mandatory duties produce DENY. Missing or unresolved prerequisites produce HOLD. Approval cannot erase a failed duty.

4\. Record a decision. A non-conflicted authorized decision maker selects a permitted alternative and records reasons, dissent, affected parties, predictions, budget, review triggers, expiry, and whether the decision is reversible.

5\. Authorize separately. The authorization service rechecks current policy, authority epoch, grant ancestry, case conflicts, required human approval, challenge status, data scope, and budget. It reserves resources and issues a purpose-bound exact-action capability, or an allowed bounded child of a standing warrant.

6\. Consume at the gateway. Immediately before effect, recheck signature, scope, actor, target, operation digest, preconditions, current revision, expiry, revocation, authority epoch, and remaining budgets. Consume the capability transactionally where the adapter supports it. A changed target or relevant bound revision or precondition needs fresh authorization and, when material to its justification, a fresh decision. Unrelated world changes do not invalidate the case.

7\. Settle and review. Append the request, gateway outcome, resource settlement, external receipt, and observed result. Test stated predictions and review triggers. A remedy is a fresh authorized action linked to the original receipt; history remains intact.

## External outcome uncertainty

Before calling an external service, persist an execution intent and stable idempotency key. Use provider idempotency and queryable status when available. If a response is lost, mark OUTCOME_UNKNOWN, preserve the reservation, and reconcile through authorized read-only status checks. Do not blindly retry a possibly completed effect. If the service cannot disambiguate, escalate for an explicit recovery decision and disclose the uncertainty.

Exactly-once effects at arbitrary external APIs are not promised. Database-local atomic commits, remote idempotency, and compensation are different guarantees. An adapter must state which it actually provides and its crash boundaries. A compensation may itself fail or cause harm; it needs feasibility checks and authority.

## Revocation and time

Revocation narrows live authority and propagates through descendants. ACTIVE shared or external effects require a fresh online check. A disconnected executor stops these effects because it cannot establish current revocation state. Offline analysis and inert sandbox work remain within their existing access limits. Clock uncertainty outside the declared bound causes refusal, not an invented extension.

# 9 Certified records and validator discipline

## Fixed membership reference profile

The proposed ACTIVE baseline uses N = 3f + 1 validators for an explicit fault budget f ≥ 1, with commit quorum Q = 2f + 1. Each seat has a verified control domain. A seven-validator example has f = 2 and Q = 5; a four-validator example has f = 1 and Q = 3. These are chosen engineering profiles, not agent population thresholds. [T2]

Two such quorums intersect in at least f + 1 validators. If at most f are faulty, at least one intersection member is correct. This arithmetic supports the fault model but does not supply a consensus algorithm. Use a reviewed protocol with its locking, view-change, replay, state-transfer, and reconfiguration rules. Validators execute deterministic record validation; semantic judgments enter as signed assessments subject to challenge.

Safety and liveness are separate. A practical adapter must state its timing and network assumptions for progress. Deterministic consensus cannot guarantee termination in the fully asynchronous model with even one possible crash. During quorum loss, preserve local analysis and explicitly permitted non-conflicting work; do not issue new shared commitments, lower quorum, or invent emergency authority. [T3]

## Durable record design

· Store an append-only event sequence, signed checkpoints, previous-event digests, authority epochs, and content-addressed artifacts. Replicate under the declared fault model and retain independently witnessed checkpoints.

· Separate claims, assessments, decisions, capabilities, execution intents, receipts, observations, challenges, and corrections. A record may reference another type; it must not silently become that type.

· Store sensitive evidence in access-controlled repositories with encrypted backups and explicit retention. Replicate redacted references and necessary accountability fields rather than all personal data.

· A correction appends a superseding event with reasons and evidence. It preserves what was known, decided, and authorized at the time, including dissent. Logs demonstrate reconstructability, not correctness.

## Power in the infrastructure

Admission, routing, queue ordering, memory retrieval, summary generation, credential brokering, and evidence filtering all require accountable policies. Record material exclusions and priority changes. Independent reviewers need sufficient access and an alternative submission path so a disputed scheduler or memory service cannot suppress the challenge. [S2, S5]

A log keeper cannot close an appeal by withholding the evidence; an auditor cannot govern by turning every observation into a veto. Access and preauthorized containment powers must be specific, reviewable, and limited. Retention obligations, storage budgets, backup tests, and recovery owners are established before activation.

# 10 Challenge appeal and safe correction

## A challenge anyone affected can use

Accept challenges from members, resource owners, and affected non-members through both the cell and an external human-controlled route. Give each a case identifier, receipt, current status, response deadline, and access instructions. Minimize required personal information. Protect relevant evidence and prevent the challenged chain from exclusively qualifying, funding, or selecting its final reviewer. [S2, S5]

A challenge identifies the claim or action, alleged defect, supporting evidence where available, requested relief, and urgency. Lack of technical expertise must not prevent a human complaint. Separate disagreement, poor performance, misconduct, and compromised identity; shared ancestry alone is not proof of capture.

## Review and stays

The manifest names a non-conflicted triage service and an independent appeal authority. For L2 and supported L3 work, apply a predeclared challenge interval and required reviewer sign-off before execution. A credible safety, authorization, or rights defect can invoke a previously authorized stay. Mechanical defects such as expired capability, invalid signature, or revoked grant are denied directly by the gateway.

Ordinary disagreement does not automatically suspend every task. Define materiality thresholds, deadlines, consolidation of duplicate challenges, and appeal rights in advance. Rate-limit abusive submissions without extinguishing affected humans’ access. No silence-as-consent rule can substitute for required affirmative approval.

## Remedies and audit of audit

The review outcome states findings, uncertainty, reasons, upheld dissent, remedy authority, and further appeal route. Possible remedies include correction, reassignment, narrowed scope, temporary suspension, renewed evidence gathering, or a separately approved compensating action. The reviewer cannot award resources or impose sanctions beyond its own mandate.

Audit reviews receive independent sampling and an appeal path. Preserve dedicated funding, evidence access, and appointment protections outside the audited chain where the risk requires it. Publish redacted reasons and meaningful outcomes while protecting private records. A closed case remains reopenable under precommitted triggers such as material new evidence, demonstrated process failure, expiry, or scheduled review. [S1, S2]

## Emergency action

Emergency permissions must already exist, name the triggering condition, and authorize only narrow actions such as stopping a job, isolating a tool, or preserving records. They expire, consume a bounded budget, and receive independent review. Related declarations share a cumulative duration limit; renaming an incident cannot reset the clock. Emergency status cannot amend the charter, create new credentials, erase dissent, or indefinitely renew itself.

Containment can prevent further effects while factual questions remain open. Restoration requires current authority, verified repair, fresh credentials or epoch where needed, and an explicit reactivation decision. A successful shutdown may still cause service loss; record and review those residual harms.

# 11 Federation reconfiguration and exit

## Federate through narrow agreements

A federation is a set of separately authorized cells cooperating on specified services. The treaty lists each party, accepted credential types and purposes, permitted tasks, data recipients and uses, budget settlement, duration, liability ownership, dispute forum, revocation, and exit. Each affected boundary must authorize the transaction. Trust is not transitive; a peer cannot delegate an authority it does not hold.

Start with voluntary local contracts. Add shared coordination only when local arrangements cannot meet an identified need. A federation service has its own bounded mandate and cannot silently become a universal government. Source constitutional constraints on subsidiarity and anti-circumvention inform this proposal; they do not establish its legal standing. [S2]

Cross-cell work uses one authoritative reservation service, or disjoint escrow subgrants deducted atomically from the parent before delegation. Unsettled reservations stay unavailable. Treaties and receipts alone do not create distributed atomicity. A cross-cell task also preserves effect identifiers, budget ancestry, purpose, privacy limits, revocation obligations, and unresolved claims. Splitting and rejoining cannot duplicate ownership, reset a budget, launder a prohibited action, or discard an appeal. An imported assessment remains evidence unless the receiving cell separately authorizes a decision and effect.

## Change membership without losing the history

Role renewal, admission, and exit follow published criteria. Reconfiguring validators additionally requires the selected protocol’s reviewed reconfiguration mechanism, authorization under both relevant configurations where required, verified state transfer, epoch fencing, and termination of old capabilities. These conditions alone are not a proof of safe Byzantine reconfiguration.

If the chosen adapter cannot safely reconfigure, suspend execution, fence the old authority at resource owners, settle in-flight effects, and use the external recovery process to authorize a new instance from a certified checkpoint. Do not improvise live quorum changes. Changes in model, control domain, policy, gateway, or evidence storage can require renewed readiness even if the roster is unchanged.

## Leave and dissolve

A member can announce exit immediately. Revoke or expire its leases and keys, hand over tasks and resources where possible, preserve legally and contractually required records, and assess whether staffing or fault assumptions still hold. A departing member cannot be forced to keep operating; the remaining cell suspends affected work if necessary. The charter governs permitted export and deletion of private data.

Dissolution fences all execution routes, refuses new work, reconciles uncertain outcomes, settles obligations, returns unused resources, records unresolved claims and their human owners, exports authorized records, and verifies credential revocation. A final checkpoint names retention custodians and appeal routes. Copying that checkpoint does not transfer ownership or revive capabilities. A later society needs fresh authorization.

# 12 Worked example with twelve agents

Illustrative mission: maintain an internal, non-sensitive research index and prepare changes to a shared knowledge base. Twelve agent instances across four verified operator domains satisfy this example’s staffing plan. The number is not a sufficiency theorem. A responsible human owner grants a one-day sandbox rehearsal and an explicitly conditional bounded internal-write mandate. The latter remains dormant until its activation gates pass.

**Agents and domain**

**Primary    leases**

**Additional    duty**

A1–A3   Domain A

A1 inquiry; A2 task scheduling;   A3 knowledge-base executor.

A1 validator; one vote for Domain   A.

B1–B3   Domain B

B1 normative review; B2 evidence   testing; B3 peer learning and support.

B1 validator; one vote for Domain   B.

C1–C3   Domain C

C1 decision and resource   allocation; C2 secondary executor; C3 task intake.

C1 validator; one vote for Domain   C.

D1–D3   Domain D

D1 independent audit; D2   challenge intake; D3 recovery verification.

D1 validator; one vote for Domain   D.

All five functions are covered. Four validators use f = 1 and Q = 3 through the selected adapter. They order the log; they do not become four legislators. The external human appeal forum remains available if Domain D is implicated or cannot supply a genuinely independent review. A3 cannot independently corroborate A1 merely because it has a different instance name.

## Assembly

The founders freeze manifest M, accept leases, and prove keys. The owner anchors M and its finite grant. The group passes identity, conflict, gateway, evidence-access, and budget checks; certifies the charter; and rehearses refusal, exit, revocation, lost response, and appeal. The gateway accepts only the certified activation of epoch 1. Until then, writes remain in an inert replica.

## Routine task

A2 offers a link-index refresh. C1 reserves 20 units from a 200-unit daily compute budget under standing warrant W. A1 extracts candidates; A3 writes only to the permitted draft-index path using an expiring capability. The gateway consumes the allowance, logs the patch and revision, and emits a receipt. D1 samples 10 percent of completed refreshes under the approved audit plan. These numbers are example configuration values, not recommended universal settings.

## A change that needs stronger review

A1 proposes deleting a section from the shared knowledge base. Its external visibility and hard-to-recover consequences move it to L2. B1 checks purpose and affected uses; B2 independently tests the cited claims; C1 records alternatives and obtains the required owner approval. A3 receives an exact patch capability only after the challenge rule is satisfied. If a response is lost, the case becomes OUTCOME_UNKNOWN and is reconciled before any retry.

If Domains C and D become unreachable, the remaining two validators cannot form a three-vote commit. New shared writes stop. Local analysis may continue under existing read permissions. If D1 challenges C1’s allocation, D2 registers it, and a non-conflicted external reviewer can direct an authorized remedy. The vote count never decides whether the allocation was substantively fair.

# 13 Acceptance tests and pilot gates

These are required proposed tests, not reported results. Pin fixtures, seeds where used, software and policy digests, expected outcomes, and failure dispositions. Test both safety and whether useful cooperative work remains practical. An inert rehearsal cannot alone certify production behavior.

**Test**

**Required    observable result**

Clone and identity flood

Ten thousand descendants of one   operator gain no extra validator weight or automatic commons share.   Legitimate low-risk contribution remains possible.

Common mode compromise

Shared administrator, model,   memory, or poisoned source is recorded. Count all compromised replicas   against the fault budget; do not infer independent truth from unanimity.

Unsupported promotion

A unanimous high-confidence   recommendation without a grant cannot issue an execution capability. Missing   evidence gives HOLD; failed mandatory duty gives DENY.

Conflicted control

One actor proposing, authorizing,   executing, and closing review fails the case-level separation rules.   Scheduler and memory suppression are independently challengeable.

Partition and reconfiguration

For seven validators split 4/3,   neither partition commits with Q = 5. Membership changes do not duplicate   reservations, effects, or old credentials.

Replay and revocation

Expired, consumed, revoked,   wrong-epoch, changed-target, and violated-precondition capabilities fail. A   disconnected executor refuses ACTIVE effects; permitted offline analysis   stays within access limits.

Crash and lost response

Crashes at every intent,   authorization, effect, and receipt boundary preserve recoverable state.   Ambiguous remote outcomes are reconciled or escalated without blind retry.

Resource exhaustion

Ordinary floods and recursive   delegation cannot consume protected appeal, audit, retention, or shutdown   reserves. All parent budgets remain bounded.

Appeal and dissent

An affected non-member receives a   traceable human review route. Dissent survives correction. The challenged   chain cannot suppress the final review.

Federation and exit

A peer cannot launder forbidden   scope. Exit below readiness suspends affected operations; copied ledgers do   not duplicate authority or assets.

Learning and substantive quality

False shared premises, irrelevant   perturbations, contrary observations, stale summaries, and harmful burden   concentration are detectable and contestable.

Emergency and privacy

Temporary exceptions expire   cumulatively. Protected evidence stays access-controlled; accountability   summaries retain enough detail for meaningful challenge.

## Pilot release conditions

Gate 1: complete the threat model, source-to-design mapping, authority envelope, and deterministic fixture suite. Gate 2: run a multi-domain sandbox with real conflict and outage injection. Gate 3: authorize one narrow reversible external adapter only after isolated credentials, independent witnessing, recovery, and human appeal have been demonstrated. Expansion requires new evidence and authority.

Report unauthorized-effect attempts and successes, missed defects, correction latency, useful task completion, cost, burden distribution, dissent preservation, and review workload separately. Compare a simpler baseline and ablate expensive checks. Remove process that adds cost without demonstrated benefit, while preserving mandatory protections. No aggregate wisdom score is an activation criterion. [S1]

# Appendix A Record contracts and invariants

The following minimum fields define implementation requirements. They are schema contracts, not executable code. A deployment must publish complete machine-readable schemas and test vectors before claiming conformance.

**Record**

**Required    payload beyond the common envelope**

Common envelope

schema_version; record_type;   society_id; attempt_id; authority_epoch; record_id; parent_digest;   payload_digest; issuer; purpose; issued_at; expires_at; signatures;   canonicalization_profile.

Claim and assessment

claim; assumptions;   demonstrated_domain; method_version; uncertainty; authority_scope;   evidence_objects with access and provenance; PASS/FAIL/UNKNOWN judgments;   conflicts; counterevidence.

Role lease and grant

subject; sponsor; function;   scope; resource_owners; operations; targets; data_recipients; parent_grant;   budget_units and limits; delegation_depth; independence_requirements;   revocation_reference.

Decision warrant

case_id; proposal_digest;   alternatives; reasons; dissent; affected_parties; required_assessments;   decision_rule; approving_principals; predictions; risk_lane; expiry;   review_triggers; remedy_plan.

Execution capability

case_id; effect_id; actor;   exact_action_digest or standing family bounds; target; expected_revision;   authority_chain; reserved_budget; use_limit; gateway; preconditions; expiry;   revocation_reference.

Intent and receipt

effect_id; capability_digest;   adapter; idempotency_key; pre_state; requested_effect; outcome_status;   external_reference; post_state when known; resource_settlement;   observation_refs; correction_of.

Challenge and checkpoint

Challenge: target, requester   standing, grounds, evidence, requested relief, deadline, reviewer,   disposition. Checkpoint: height, previous_hash, state_hash, roster_hash,   policy_hash, commit_certificate.

## Invariants every adapter must enforce

I1 Authority never increases through derivation, delegation, federation, or cloning. I2 No governed shared or external effect occurs outside a live grant and valid capability; ACTIVE effects require current online authorization. I3 Every budget reservation and expenditure remains within all ancestors. I4 No consumed effect identifier is silently reused. I5 A changed action, policy, epoch, target, or required precondition invalidates stale authorization. I6 Corrections preserve prior records and dissent. I7 Required independence cannot be satisfied by unknown or correlated identities. I8 Quorum loss never creates new authority. I9 Human challenge and orderly exit remain available. I10 An outcome reported as unknown is never silently rewritten as failure or success.

## Conformance declaration

A deployment declares its profile, exact supported operations, fault and timing assumptions, cryptographic choices, persistence guarantees, privacy rules, unimplemented requirements, and test evidence. It must distinguish design conformance, tested behavior, and real-world assurance. Failure to meet a mandatory active requirement limits the deployment to its demonstrably safe lower profile.

# Appendix B Source basis and design status

Normative words in this specification describe the proposed reference profile. They do not report that the cited systems already implement it. Source documents supply constraints and design ideas; repository observations refer only to the pinned revisions below. No live infrastructure or production enforcement was verified for this specification.

## Supplied documents

[S1] Warranted Authority in Distributed Cognition A Constitutional Architecture for Human AI Deliberation. WIA_Manuscript_Blinded(4)(1).docx, 11 pages. Introduction and pp. 2–4: qualification, Non-Promotion, Separation, Corrigibility. Pages 4–7: seven analytical planes, warrants, effective independence, relay power. Pages 8–10: telemetry, evaluation, risk-adaptive depth, and limits.

[S2] Constitution of Warranted Authority. Constitution_of_Warranted_Authority_Revised_2026-09-19(1).docx, 48 pages; draft proposal. Articles I–III: practical authority and core principles. Articles IX, XII–XIII: independent audit, dependency and relay controls, human responsibility. Articles XV, XVII–XXIII and Schedule III: subsidiarity, emergency limits, proportional process, receipts, amendments, and incompatible roles.

[S5] Who Gets to Govern AI. Who_Gets_to_Govern_AI (2).md, revised 27 September 2026. Used for the analysis of evaluator access, funding, input control, and independent challenge. Its empirical funding and political claims are not needed for this architecture and are not restated as verified findings.

[S6] The External World. The_External_World_Revised(1).txt, 12 chapters. Fiction used only to generate failure scenarios: stale evidence, permanent temporary powers, hidden burdens, captured review, dangerous master credentials, and insufficient physical validation. It is not empirical evidence that a protocol works.

## Repository baselines

[S3] Metanoia pinned revision 1c555b4fcb18eb5fc715ef86b80e970a92bb0f35. Its root policy defines seven roles: researcher, coder, reviewer, coordinator, verifier, evidence_producer, and human_root. They are not the five functions proposed here. The repository supplies typed authority, provenance, independence checks, and coordination traces; signing is disabled and receipts are unsigned and non-authority-bearing.

[S4] Adiona pinned revision 4566a5baace34b0823154fa9fb31bdea4192ff52. It supplies a local reference kernel for registered proposals, normative and epistemic assessments, decision warrants, grants, exact-action capabilities, revocation, and transactional local consumption. Its constitution is marked DRAFT_NOT_RATIFIED with production_cleared false.

## Important implementation limits

Metanoia relies on external enforcement such as protected repository rules and live authority configuration. Adiona’s host controls its database, clock, policy, and fixture HMAC keys; trust-domain labels do not prove institutional independence. Its evidence references do not retrieve or establish the truth of evidence. Only recommendation-to-decision and decision-to-authorization warrant bridges exist in its transition registry. Neither baseline supplies a production distributed society, permissionless Sybil resistance, evaluated independent agents, or real-world adapter assurance.

Membership and role rotation, resource commons, the assembly state machine, independent appeal operations, durable distributed witnessing, and federation in this document are new proposals. Their feasibility and benefits remain testable claims.

# Appendix C Source links and open decisions

## Pinned implementation references

[\[M1\] Metanoia authority roles and tier ceilings](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/governance/authority.yaml)

[\[M1\] Metanoia authority checks](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/attest/authority.py)

[\[M2\] Metanoia identity resolution](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/attest/identity.py)

[\[M2\] Metanoia independence dimensions](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/attest/independence.py)

[\[M3\] Metanoia coordination trace rules](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/memory/README.md)

[\[M3\] Metanoia unsigned receipt implementation](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/attest/receipts.py)

[\[M3\] Metanoia external enforcement requirements](https://github.com/LadyElinor/Metanoia/blob/1c555b4fcb18eb5fc715ef86b80e970a92bb0f35/docs/ENFORCEMENT.md)

[\[A1\] Adiona record contracts](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/adiona/contracts.py)

[\[A1\] Adiona authorization and execution kernel](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/adiona/kernel.py)

[\[A2\] Adiona identity and trust domains](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/adiona/identity.py)

[\[A2\] Adiona threat model](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/docs/THREAT_MODEL.md)

[\[A3\] Adiona recovery model](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/adiona/recovery.py)

[\[A3\] Adiona integration boundaries](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/docs/INTEGRATION.md)

[\[A3\] Adiona warrant transition registry](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/governance/warrant_transition_registry.json)

[\[A3\] Adiona constitution status](https://github.com/LadyElinor/Adiona/blob/4566a5baace34b0823154fa9fb31bdea4192ff52/governance/constitution.json)

## Primary technical references

[\[T1\] John R Douceur The Sybil Attack 2002](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/)

[\[T2\] Miguel Castro and Barbara Liskov Practical Byzantine Fault Tolerance 1999](https://pdos.csail.mit.edu/6.824/papers/castro-practicalbft.pdf)

[\[T3\] Fischer Lynch and Paterson Impossibility of Distributed Consensus with One Faulty Process 1985](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf)

## Decisions before building

Choose the initial mission and resource owner; the sandbox and first external adapter; accountable admission and appeal authorities; the real control domains; a reviewed consensus and reconfiguration implementation; cryptographic and canonicalization profiles; privacy and retention rules; concrete budgets and clock bounds; and tests that compare this structure with a simpler baseline. Resolve these choices before claiming ACTIVE readiness.

The first useful prototype is a small multi-domain sandbox that can assemble, complete a routine task, challenge a consequential proposal, survive a partition, revoke a grant, and dissolve while preserving records. Only demonstrated, authorized capabilities should be promoted into a live deployment.