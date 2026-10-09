# Current contract and historical records

The software version is **0.2.2**; the frozen Warranted Agent Commonwealth design
profile is **0.2**. These versions describe different things. This index adds no
new ratification or production claim. The optional unreleased scratch runner
is indexed separately below.

## Current reading order

- [Package contract](../package/README.md): supported profile, roster, assignment,
  arithmetic and output boundaries. Assignment certificates use the V2 format,
  but the current verifier requires software 0.2.2 and all four supported
  additions. Regenerate 0.2.0/0.2.1 certificates; do not relabel them.
- [0.2.2 migration](REVISION_0_2_2.md): supplied-controller checks, consequential
  decision records and bounded complaint/repair contracts.
- [Lottery contract](LOTTERY.md): frozen nominations and domain-first simulated
  selection, including explicit dead ends.
- [Registrar model](OVERSIGHT_REGISTRAR.md) and
  [amended assembly specification](COMMONWEALTH_REGISTRAR_REVISION.md): distinguish
  the offline replay subset from institutional design requirements. Neither is
  an operational registry or authority grant.
- [Disposable runner integration](SCRATCH_RUNNER.md): strict evidence/mandate/receipt
  linkage and actual scratch-database effects; no external execution or real authority.
- [Opt-in bounded complaint triage](COMPLAINT_TRIAGE.md): separate complaint state,
  declared-controller fact-finding and isolated review/audit reserves.
- [OPR 1 proposed amendment](OPR1_PROPOSED.md), [requirements map](OPR1_REQUIREMENTS.md), and
  [opt-in supplied-record contract](OPR1_RECORDS_V1.md): a separately versioned
  proposed extension with structural snapshot inspection only; no adoption,
  semantic acceptance, full OPR conformance, or authority to restrict anyone.
- [OPS1 proposed operating supplement](OPS1_PROPOSED.md), [status map](OPS1_REQUIREMENTS.md),
  and [opt-in trace/study contracts](OPS1_OFFLINE_V1.md): separately versioned supplied
  dependency checks plus human operating procedures; no adoption or outcome certification.
- [Evidence gates](EVIDENCE_GATES.md): warranted scripted-sandbox interpretations
  and requirements for stronger claims.
- [Current synthetic examples](../package/results_v2/): examples rather than a
  receipt for the latest test run. Run `python scripts/verify.py` from the
  repository root; use `--report .local/verification.json` for a new local receipt.

All controller declarations remain supplied and unverified. Outputs retain
`authority: NONE`; external execution remains disabled. The new disposable
scratch runner performs explicitly labeled local database effects; the frozen
profile and existing offline CLI remain execution-disabled. The exact accepted profile
baseline is unchanged, and passing tests do not authenticate its source or
establish real-world independence, safety or readiness.

## Historical and frozen records

- [Initial entry point](../START_HERE.txt), [original package results](../package/results/),
  `verification/*results*`, and [original verification receipt](verification.json)
  describe the imported software 0.1.0 snapshot.
- [0.2.0 notes](REVISION_0_2_0.md), [0.2.1 notes](REVISION_0_2_1.md),
  [0.2.0 receipt](verification_0_2_0.json) and
  [0.2.1 receipt](verification_0_2_1.json) describe earlier revisions.
  Their historical acceptance rules and test counts are not current contracts.
- [Registrar change summary](REGISTRAR_CHANGE_SUMMARY.md) records its dated
  candidate scope; consult the current registrar and 0.2.2 documents above for
  the subsequently strengthened replay contract.
- [Evaluation scaffold](../evaluation/README.md) remains frozen and source-gated:
  216 exposed examples, 620 proposed arm slots (540 main plus 80 ablation),
  62 fabricated smoke rows, and 10,000 bootstrap resamples. These unchanged
  historical counts are neither current regression-test counts nor observations
  from agent trials. Ordinary readiness success checks offline integrity;
  scored readiness and scored analysis deliberately refuse.
- [Scripted sandbox](../sandbox/README.md) is a separate frozen mechanism rehearsal.
  Its scripted episodes are not model-backed evaluation trials.

Do not rewrite historical records to match current code. Saved receipts describe
what was checked at their recorded revision; a fresh run is needed to establish
current check outcomes.

## Original-source provenance remains unknown

[Source provenance](../package/inputs/provenance.json) records reconstructed
Library text exports. The original uploaded profile JSON and charter DOCX bytes
were unavailable; both original-artifact SHA-256 fields remain null and adoption
identity is not established. Export hashes cannot substitute for those unknown
original-byte identities. The frozen accepted baseline does not cure this gap.

[Import provenance](../provenance/import.json) identifies the imported ZIP and
[initial inventory](../provenance/initial_BUNDLE_SHA256SUMS). That archive identity
is distinct from the unavailable original JSON/DOCX identities. Checksum
inventories detect byte changes; they are not signatures, authorization or
empirical evidence. See [contributing](../CONTRIBUTING.md) for integrity handling.
