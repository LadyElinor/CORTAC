# Oversight Registrar amendment summary

Local candidate based on CORTAC main `a279dcbd5357aca130958afd08dbbf6b4edc3685`, verified 8 October 2026. Nothing in this delivery publishes to GitHub or grants production authority.

## Warranted changes

- Audit and Correction now houses a bounded procedural Oversight Registrar; authorized decision makers retain substantive amendment approval.
- Current rules govern every amendment, including changes to the amendment mechanism, registrar and protected gateway controls.
- Exact old/new content, current epoch, notice, conflicts, quorum, principal approvals, challenges and activation conditions are recorded separately.
- Conditional activation compares the old policy and epoch, advances one effective policy state and requires stale-authority fencing at effect boundaries.
- Registrar refusals and delays have reasons, deadlines, independent appeal and replacement; silence cannot approve anything.
- The genesis registry remains distinct. Routine standing warrants and consequential-action safeguards remain intact.

## Included implementation

`package/wac_offline/amendments.py` is an isolated offline model with strict record schemas, synthetic examples and adversarial regression tests. It checks supplied current-rule inputs and separates registration from locked activation. A late challenge, revocation, stale certificate, malformed record or competing activation fails closed.

The full revised text is `docs/COMMONWEALTH_REGISTRAR_REVISION.md`. All 641 original lines are preserved in order, with additions only; `provenance/commonwealth_supplied.md` retains the 53,645-byte supplied source. `scripts/check_registrar_source.py` checks its digest and the insertion-only revision.

## Important limits

All identities, domain labels, approvals, evidence and time are supplied and unverified. The model has no signatures, live capabilities, persistent transaction, distributed consensus, authenticated challenge service or host-administrator protection. Every modeled amendment conservatively requires the current external-principal set. Local challenges hold all amendments in the current epoch; invalidation has no local undo. Actual registrar appeal/replacement and recovery remain design requirements, not implemented institutions. Duplicate activation is safely refused rather than returning a durable existing receipt.

The original frozen assignment profile, sandbox protocol and evaluation fixtures are unchanged. Outputs remain `authority: NONE`, execution disabled. Passing local tests establishes bounded software behavior only. See `OVERSIGHT_REGISTRAR.md` for the complete implementation-to-specification mapping and the delivered verification report for exact results.
