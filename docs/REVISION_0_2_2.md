# 0.2.2: declared independence and contestable offline correction

This revision addresses verified omissions at `c44c07bdcc3aea35e9afb856f51014e7b3b053c9`.
It strengthens executable **supplied-input** contracts. It does not establish
hidden control, authenticate an institution, ratify a constitutional draft, or
enable execution. All outputs remain synthetic with `authority: NONE` and
`execution_enabled: false`.

## Independence

Both independent constraint implementations now reject shared declared material
controllers between council seats and between the outcome auditor and the
proposer or executor. Distinct domain labels cannot override an explicitly
shared material controller for these pairs. The tests include additive controller
sets, each council pair, alternate candidates, both assignment verifiers and
certificate verification. Unrelated role pairs are not globally prohibited.
These conservative additions leave the frozen profile bytes unchanged.

Old assignment certificates must be regenerated: the current verifier requires
software 0.2.2 and the strengthened additions contract. Agreement between the
implementations is still not proof that their requirements are complete.

## Decision records and protected commitments

A consequential ballot now requires an explicit boolean `protected_failure`, a
separate declared `protected_limits` inventory, and a complete `decision_record`.
There is no default assertion of no protected failure. Every listed protected
limit needs exactly one assessment; `FAIL` or `UNKNOWN` cannot be outvoted.
Omitting a failing assessment while retaining that limit in the inventory fails.

The receipt requires affected parties, interests, benefits, burdens and
representation; alternatives with less-harm analysis and reasons; protected-limit
assessments with evidence references; burden justification; explicit dissent or
none-reported status; predictions; review triggers and who can require review;
and a remedy plan naming authority, resources and steps. One alternative suffices
for structural completeness. This does not prove that a serious comparison,
adequate representation, or a morally or legally sufficient assessment occurred.

Amendment policies carry a nonempty supplied protected-commitment inventory.
Ordinary and repair amendments must preserve its ID-to-commitment mapping.
Approval receipts are checked against the effective policy inventory, rather than
an inventory invented by the proposed replacement. Missing records, altered
commitments, incomplete assessments, failure and uncertainty fail closed.
The initial commitments are supplied test inputs, not authenticated higher law.
No particular constitutional draft is silently made binding. Arbitrary natural
language content remains opaque: text contradicting a preserved commitment is
not detected by this structural check. An independently authorized substantive
reviewer must judge that conflict and the truth and sufficiency of evidence.

## Complaint, replacement and repair

The versioned amendment record contract and bounded workflow are documented in
[Oversight Registrar](OVERSIGHT_REGISTRAR.md). They model a complete local
contested-case path with old-rule independent review, explicit supplied scoped remedy
permission and declared finite resource backing, replacement despite the original
registrar's withholding, and activation-time rechecks. A timeout does not approve
anything. A stale, missing or exhausted mandate does not become an emergency
exception. Historical refusal, challenge and invalidation evidence is retained.

Repair in this contract addresses one exact source. Multiple simultaneous
invalidations remain fail-closed; collective recovery needs a separately designed
and authorized mandate. No unrelated cause is erased to make a repair pass.
Run `python scripts/contested_amendment_demo.py` for the fabricated outsider
complaint, withholding, scoped replacement and single-source invalidation paths.

This is a one-process supplied-clock simulation. It cannot force an absent human
reviewer, operator, resource provider or real external principal to cooperate.
Protected funding and a data record do not create a real legal power or resource.

## Migration and remaining deployment gates

Amendment records migrate explicitly to v2; v1 records are rejected rather than
silently defaulting missing safeguards. Regenerate proposals and all bound
approval/procedure/certificate digests from the complete new record contract.
Never relabel old approvals as fresh approval. The old examples and original
provenance remain historical records; only current examples and inventories are
regenerated for this software revision.

The executable model still cannot establish complete protected-component
coverage, deployment identity, durable/crash-safe state, authenticated clocks or
signatures, hidden-controller independence, evidence availability, enforceable
resource reservation, or independently controlled effects. These are production
acceptance gates, not a passing synthetic test's implied result. Protected source
review is separately described in [repository protections](REPOSITORY_PROTECTIONS.md)
and requires the owner's action-time approval. No GitHub security setting is
changed by this revision.
