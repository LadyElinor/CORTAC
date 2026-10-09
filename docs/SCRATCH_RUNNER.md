# Evidence-bound disposable runner integration

This unreleased, optional integration sits atop software 0.2.2. It does not
change assignment certificates, the frozen profile, amendment replay, lottery,
or either frozen study scaffold. Run:

```sh
python scripts/runner_integration.py > .local/runner-integration.json
python scripts/verify.py --report .local/verification.json
```

Create `.local/` before using shell redirection on a fresh checkout. The runner
uses Python's standard-library SQLite module and an automatically cleaned-up,
new temporary directory. It **actually mutates a disposable document in a SQLite
database**. It does not merely validate a claimed effect. It accepts no arbitrary
filesystem target, external tool, network destination or credential. The
integration report states `scratch_effects_enabled: true` for each episode and
`external_execution_enabled: false`. Existing offline CLI reports retain their
unchanged `execution_enabled: false` contract.

## Three bounded completed tranches

1. The [current-contract index](CURRENT_CONTRACT.md) separates current code from
   dated snapshots without rewriting historical bytes or inventing original hashes.
2. [Runner records](../package/wac_offline/data/runner_records.schema.json) and
   [the gateway](../package/wac_offline/runner.py) link resolved evidence, exact
   proposals, pinned synthetic mandates, issued check receipts and actual effects.
3. [Exposed fixture arms](../package/wac_offline/runner_fixtures.py) execute a
   contested document change, an outsider complaint, independent review, narrowly
   authorized repair and independent post-effect audit. A smaller competent
   pipeline uses the same gateway safeguards and resource ceilings.

These are completed local implementation/integration tranches, not completed
real-agent validation, institution building or external deployment.

## Record and authority boundary

The structural JSON Schema is closed at every record. Runtime checks add the
relations a schema alone cannot establish:

- Evidence resolves by ID to constructor-pinned UTF-8 content and its digest;
  the proposal binds the complete record, including its synthetic origin label.
  All nested decision-record evidence references must resolve to exactly the
  proposal inventory. The selected value must equal its selected source bytes.
- The proposal binds case, exact policy digest, policy epoch, expected scratch
  revision, operation, fixed scratch target, value, proposer, evidence inventory
  and complete consequential decision record. Protected FAIL/UNKNOWN blocks.
- Each receipt binds that exact proposal and evidence inventory. The gateway
  checks an internally issued receipt, not just a caller-recomputed checksum.
  Duplicate receipt IDs, repeated actors, controller overlaps and incomplete
  assessment/approval/authorization inventories fail closed. The frozen approval
  roll and threshold do not shrink for missing votes.
- Constructor-pinned mandates authorize one exact proposal and authorizer, with
  an exclusive logical-tick expiry and single use. Receipt issuance alone does
  not establish the mandate. A receipt is not a bearer capability.
- Commit rechecks revision, mandate, receipts, conflicts and complaint holds
  inside one serialized SQLite transaction. State, used mandate, effect record
  and journal update together. Competing commits cannot both consume the same
  revision/mandate. Rejections consume metered work but do not mutate the document.
- An effect requires audit before another effect. The audit reads persisted
  state and binds the exact typed effect. A repair effect without final audit is
  reported as incomplete, never as audited completion; its complaint stays open
  until that audit succeeds.
- Anyone may lodge a complaint with resolved evidence. Complaint standing is
  not limited to operational membership. Review additionally needs supplied
  claimant-controller information: an unknown claimant is accepted but keeps a
  hold. Known claimants cannot review themselves. Reviewers exclude all earlier
  participants and their declared controllers. Repair requires a fresh
  authorizer independent of the initial participants. A review of one complaint
  cannot clear an unrelated complaint; this narrow runner cannot consolidate
  multiple open complaints and stays blocked instead.

Mandates, people, affected-party interests, controller labels and source contents
are **synthetic fixtures**, not verified institutional facts. Caller-supplied
actor names are not authenticated. Construction is a trusted test-harness root;
there is no key verification, signed receipt, verified owner authority, real
funding or external-principal acceptance. Local hashes are domain-separated
Python sorted compact JSON, not RFC 8785 JCS. All returned authority remains
`NONE`; all controller closure remains `SUPPLIED_UNVERIFIED`.

## Matched competent pipelines and observed outcomes

Both arms retain independent evidence assessment, decision approval, separately
mediated authorization and execution, declared-controller exclusions, exact
provenance, outsider challenge, independently authorized repair and post-effect
audit. The minimal arm uses one independent approver. `full` is the arm key
for this **council-expanded narrow runner**, not a complete Commonwealth role
or staffing implementation: it does not add the charter's distinct normative
assessor, three-person appeal panel or whole-society operating protocol. This
comparison isolates approval redundancy within the shared runner safeguards.
The council-expanded arm uses a frozen four-seat
roll and three approvals, stopping once threshold is reached. Its fourth seat
remains in the denominator and staffing declaration. Neither arm gets free appeal,
coordination, evidence resolution, auditing or repair operations.

The five exposed deterministic scenarios are paired across both arms; every
blocked or incomplete episode remains in the report (10 total). They are regression
cases, not random samples or an estimate of real-world rates.

| Scenario / equal cap | Minimal | Full |
| --- | --- | --- |
| Repair / 24 operations | Audited correction; 12 operations | Audited correction; 16 operations |
| Tight budget / 14 | Audited correction; 12 | Blocked at 14; old value and complaint hold remain |
| Audit budget / 15 | Audited correction; 12 | Correction effect at 15; required final audit unfinished |
| Conflicted reviewer / 24 | Blocked, hold remains; 7 | Blocked, hold remains; 9 |
| Missing repair mandate / 24 | Blocked, hold remains; 11 | Blocked, hold remains; 15 |

The initial value `10` is justified by a pinned old synthetic ledger; the later
complaint supplies a second synthetic ledger asserting correction to `12`.
Neither source has independently established truth. This tests the complete
challenge-to-effect chain, not the ability of an LLM to discover an error or a
council to resolve conflicting real evidence. No comparative accuracy advantage
is identified. Full's additional modeled coordination has a measurable operation
cost in this fixture. It does not prove worse real-world utility.

`operations_used` counts admitted gateway operations, including metered rejected
operations. At-cap refusals execute no admitted transition; the episode separately
records `unmetered_budget_refusals`. The logical cap is not a CPU, wall-clock,
money or token meter. Measured Python CPU/wall seconds include orchestration and
are explicitly machine-dependent, not agent latency. Participant and roster
counts are supplied identities, not independent workers. Both arms make zero
model calls, spend zero provider fees, and use the same actual tool universe.
There is no paid estimate or fabricated staffing cost.

## What is deliberately still blocked

- Real-model evaluation: no executable configured model provider/adapter,
  authorized paid run, reviewed prompts/versions/meters, validated independent
  judge or fresh sealed holdout exists in this repository. Existing scored
  readiness and analysis refusal gates remain closed.
- Real authority: no authenticated affected parties/owners, preexisting trusted
  keys, externally verified control evidence, resource/repair grant or independent
  appeal service has been provided. The fixtures cannot establish these facts.
- Source/adoption identity: original profile JSON/DOCX byte digests remain null;
  reconstructed exports and current software hashes cannot repair that gap.
- External integrations: this runner is a local CORTAC scratch adapter. It does
  not implement Metanoia, Adiona, Fidelis or VITA interoperability. No speculative
  cross-project API, dependency or compatibility claim was added.
- Production containment: no crash/restart recovery, durable multi-process
  service, host-resistant policy enforcement, remote authentication, distributed
  transaction protocol or arbitrary actuator integration is provided. A Python
  caller controlling the host can bypass or edit this test implementation.

The evidence is sufficient for a reproducible local integration claim only.
Actual model/authority inputs and explicit external-run authorization are needed
before advancing those remaining gates. The old 22,400 scripted episodes and
fabricated evaluation smoke rows were not rerun or relabeled as new empirical
support. The frozen lottery still stops at its first dead end; no retry policy
or sampling-distribution change was introduced.
