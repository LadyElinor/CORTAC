# WAC design 0.2 offline reference tools (software 0.2.0)

**Unsigned design experiments. Authority: NONE. Runtime status: UNINITIALIZED_NO_EXECUTION.**

This standard-library Python package checks a narrow, declared synthetic constraint model derived from the supplied Warranted Agent Commonwealth v0.2 profile and charter. It searches for one feasible case assignment **together with a three-person appeal reserve**, or reports a demonstrated model constraint failure or an incomplete bounded search. It does not create agents, sign anything, install a loader, appoint officials, grant permissions, or make network calls.

## Quick start

Requires Python 3.10+; development verification used Python 3.12.14. No installation or third-party packages needed. Run from this directory:

```sh
python3 -m unittest discover -s tests -v
python3 -m wac_offline validate-profile inputs/profile.extracted.json
python3 -m wac_offline assemble --profile inputs/profile.extracted.json --roster fixtures/feasible.json > current-assignment.json
python3 -m wac_offline verify --profile inputs/profile.extracted.json --roster fixtures/feasible.json --certificate current-assignment.json
python3 -m wac_offline draft-founding --profile inputs/profile.extracted.json --roster fixtures/feasible.json
python3 -m wac_offline assemble --profile inputs/profile.extracted.json --roster fixtures/bounded_search.json --max-nodes 0
python3 -m wac_offline split fixtures/split_exact.json
python3 -m wac_offline vote fixtures/frozen_vote.json
python3 -m wac_offline ballot fixtures/ballot.json
```

All commands print JSON. Exit 0 means a positive supported synthetic result; 2 means invalid or unsupported input/witness, 3 means a negative arithmetic result or dual synthetic infeasibility, 4 means incomplete search or a lottery dead end, and 5 means implementation disagreement. Check both the exit code and the JSON status. Windows PowerShell 5 redirection can produce UTF-16; use `Set-Content -Encoding Ascii` to save the ASCII JSON for later input.

## What the statuses mean

- **SYNTHETICALLY_SATISFIED:** a concrete assignment satisfies both implemented encodings of the finite declared model. Controller closure remains supplied and unverified.
- **SYNTHETICALLY_INFEASIBLE:** both bounded search implementations conclude no assignment in this supplied model. Necessary-condition rejection and completed finite search remain distinct evidence types. This is not a conclusion about all possible real-world rosters.
- **SYNTHETIC_SEARCH_INCOMPLETE:** no accepted witness exists and at least one search did not conclude infeasibility. No infeasibility claim is made.
- **SYNTHETIC_IMPLEMENTATIONS_DISAGREE:** the engines reach conflicting decisive conclusions or a candidate witness fails an encoding. No assignment is accepted.
- **SYNTHETIC_WITNESS_VALID / SYNTHETIC_WITNESS_INVALID:** V2 local byte bindings, mandatory scope fields, and the assignment were rechecked by both encodings. This does not authenticate a report or the inputs.

The primary engine uses lexical DFS with joint case and appeal assignment and conditional panel symmetry reduction. The second engine uses independently written unary/binary constraints, minimum-remaining-values ordering, and forward checking without that symmetry reduction. They share input-shape validation, not eligibility/conflict code. Each gets the requested node budget. A checked witness can settle satisfiability even when the other search ran out of nodes. Both must conclude infeasibility for a negative CLI report. The program is still a bounded reference tool; neither input preprocessing nor wall time is bounded by candidate-expansion counts.

The direct `solver.solve` and `reference.solve_reference` APIs report their own conclusions. The CLI `assemble` combines them. Standalone search results are not V2 certificates. See [revision notes](../docs/REVISION_0_2_0.md).

Search choices do not count as a charter lottery or an appointment. The separate [lottery simulator](../docs/LOTTERY.md) draws domains under a frozen nominee policy, uses recorded test randomness, and reports the first dead end without retries. It establishes no real principal consent, seed chronology, or authority.

## Supported profile validation

`wac_offline/data/profile_baseline.json` is an unmodified text export of the supplied v0.2 JSON content, used as a frozen accepted baseline. The validator recursively requires the baseline's exact field set, JSON types, array order and scalar values; object-key order and whitespace are irrelevant. It rejects duplicate keys, non-finite JSON numbers, missing/unknown fields, unsupported versions, changed rules, floats where integers are expected, and bools masquerading as integers.

This intentionally conservative validator supports **one design-profile baseline**, not arbitrary extensions or every future valid WAC profile. An innocuous prose edit is unsupported too. It is not a general JSON Schema, a signed adoption verifier, a DOCX/JSON semantic correspondence proof, or a production loader. Changing the template's disabled fields is rejected and can never activate anything. Supported arithmetic and staffing behavior are tested independently of accepting the baseline values.

## Synthetic roster contract

See `fixtures/feasible.json` and its reproducible generator `fixtures/generate.py`. The schema identifier is `wac.offline_roster.v1`, a **new implementation proposal, not an adopted v0.2 object schema**. Unknown fields are rejected so they cannot be silently assumed effective.

Records have unique `id`; kind `agent`, `authorizer_service` or `interest`; nonempty credential/process labels; domain and declared domain-verification flag; material-control flag and controller list; qualified-role names; nonnegative integer capacity and expiry; all four recorded dependency dimensions; and an explicit conflict list. No field contains real credentials. Unknown dependency values use JSON null.

- `domain_verified` and `material_control_known` mean **declared true inside a synthetic fixture only**. The program does not verify enrollment, signatures, organizations, credentials, capacity, competence, or any real-world independence.
- `material_controllers` must contain the **complete, transitively closed set of material controlling-interest identifiers**, including indirect administration, appointment/removal, credential/record control and discretionary funding leverage. This implementation compares supplied sets; it does not discover edges or compute graph ancestry. Omitted/false controller facts can invalidate its conclusions. Completeness and freshness at both assignment and appeal horizon are unverified input assumptions.
- Unconditional precommitted funding should not be placed in the material-control set solely because it is funding. Any discretion that does constitute leverage must be represented. The program cannot determine which interpretation is true.
- `valid_until` is an exclusive integer timestamp for role eligibility/credential availability; a role is unavailable at that timestamp. Case roles and fixed proposer are checked at `as_of`; appeal roles at `appeal_horizon`. It is **not a freshness attestation for controller evidence**. All timestamps are synthetic input values, not checked against the host clock.
- `capacity` is the number of presently available synthetic role slots. This package checks one case, uses each identity once, and requires at least one slot. It does not schedule multiple cases or prove a funded continuity guarantee.
- The authorizer must be kind `authorizer_service`. It is a separately credentialed/process-isolated service outside the illustrative 32-agent headcount. This example has 12 simulated agent records plus one service, not a fabricated 32-agent minimum theorem.
- The fixed proposer requires the declared `proposer` qualification, available capacity/current role eligibility, and any configured `required_dependencies.proposer` dimensions.
- `registered_executor_ids` constrains executor choice explicitly.
- `prior_participant_ids` are earlier participants in this same case. They cannot receive new modeled roles, and their material interests remain excluded from appeal. This is a conservative no-reassignment convention, not a complete rotation policy.
- Dependency fields are `model_lineage`, `runtime`, `shared_context`, and `evidence_origin`. Evidence assessors require all four to be known. Values being known does not establish source sufficiency or cognitive independence. `distinct_dependencies` adds proposed mission-specific rules between two concrete role names, including `proposer`; unknown values then fail and equal values conflict. Missing mission policies are not silently supplied.
- Explicit conflicts apply symmetrically. Fixed proposer, beneficiaries, appellant, opposing party, and prior participants require known declared domains for the modeled independence checks. Permitting an unknown-control agent to make an advisory proposal does not make it eligible for this consequential-case witness.

## Constraint coverage

Implemented checks include:

1. Exactly one evidence assessor, one normative assessor, four council members, one separate authorizer service, one registered executor, one outcome auditor, and three fresh appeal reviewers. No case identity reuse, including the proposer.
2. Declared qualifications, capacity, relevant expiry, required dimensions, purpose-specific dependency inequality, and explicit conflicts.
3. Evidence and normative identity/credential/domain separation from proposer and beneficiaries. As an explicit **conservative implementation addition**, any shared material-controller identifier also disqualifies these assessors.
4. Four distinct council domains excluding proposer/beneficiary domains and material control; all four seats remain mandatory. The separate ballot utility checks three of four approvals without shrinking the denominator and rejects a protected-failure override. It does not authenticate votes or establish evidentiary admissibility.
5. Authorizer/executor credential and process separation from every assigned role and proposer; the authorizer is not an ordinary agent. Auditors cannot review their own earlier case work and differ in identity, credential and domain from proposer and executor.
6. Three distinct appeal domains; no prior case participants, their controlling interests, appellant, opponent or beneficiary; no unknown material control. Fresh names or domains do not erase an overlapping controller. Pairwise disjoint material-controller sets within the appeal panel are a **conservative implementation addition**.
7. Exact rational split conservation and frozen domain/cell-weight chamber arithmetic. Abstentions, absences and missing yes votes do not shrink denominators. Duplicate votes and IDs outside frozen rolls are rejected. Ledger/roll authorization, admission, split approval, merger migration, and reapportionment procedures are not verified.

The fixture's eight distinct domain labels are a conditional model witness under the declared assumptions, not a universal minimum domain count or a real independence result. Stricter mission or repository integration requirements may need more domains or different staffing.

## Not implemented or established

No real enrollment/qualification verification; evidence-source resolution; duty or classification policy; model/API integration; authenticated appointment lottery; mission contract; independent external appeal provider; review-continuity funding; signature/JCS implementation; adoption or genesis; grant/capability issuance; actuator enforcement; revocation/commit races; budgets shared across transactions; network dispatch; reconciliation; distributed consensus; production adapter; human approvals; or ACTIVE/SANDBOX readiness. Internal appeal capacity does not satisfy the separately required external route and funded continuity.

All fixture labels are simulated. All report/founding outputs retain `authority: NONE`, `UNINITIALIZED_NO_EXECUTION`, disabled execution, no signatures, no grants, and no adoption digest. The synthetic founding draft is only a checklist and assignment pointer; it is deliberately **not** an adoption payload or signing request.

## Hashes and source provenance

See `inputs/provenance.json`. Original uploaded JSON/DOCX bytes could not be obtained. `profile.extracted.json` and `charter.extracted.txt` are reconstructed **full text exports** read from the supplied Library files. They are useful for this offline implementation and are clearly not original artifact bytes. The DOCX was not edited. The text export is not a visual-layout review.

- Profile text-export local SHA-256: `56c4bc76286a78d32541528c5ab85e0470cec84b627f8ce6f152867a9246031a`
- Charter text-export local SHA-256: `eba8e2c3c8360d9d720585df094f4dd11885a65c1239c8ea7b23681311cf7dfe`
- **Original uploaded JSON and DOCX byte digests: unavailable.** Exact-byte signed adoption remains blocked.

Each report binds the exact *local input bytes it actually used*, including whitespace, by SHA-256. The report-body hash uses a documented Python sorted/indented ASCII JSON encoding. It is **not RFC 8785 JCS**, is not an adoption digest, and supplies no authentication or authority. A hash is not a signature; anyone able to change a report can recompute it. The witness verifier checks bindings and the supported assignment rather than trusting the hash alone. Original WAC adoption requires the complete exact original artifact bytes, RFC 8785 and properly authorized external keys; none is implemented here.

## Reproducible outcomes

`results/fixture_summary.json` records regenerated outcomes. Tests include feasible staffing, clone insufficiency, fresh-name/same-controller appeal rejection, missing dependency data, reviewer shortage, registration, malformed inputs, frozen denominators, exact rational thirds, joint backtracking, and bounded search. They also cover the two QA edge cases: unknown excluded-party domains and concrete-seat dependency rules that narrow only one panel seat.

These are implementation regression results, not the 540+80-trial WAC society evaluation and not empirical evidence of usefulness, safety, or deployment readiness.
