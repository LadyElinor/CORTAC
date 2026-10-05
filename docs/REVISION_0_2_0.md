# Software 0.2.0: narrower claims and two constraint encodings

Prepared against GitHub commit `b710938c303d6365e31245d22843cd5a9014b4ec`. All 93 base files were checked against the remote tree's blob identities before editing. The repository owner authorized publication of this revision and selected the MIT license. See `LICENSE` and `docs/LICENSE_DECISION.md`.

## Changes

- Assignment report V2 carries synthetic status names and mandatory unverified-input scope. The verifier rejects a missing or promoted scope even when the report hash has been recomputed.
- Semantic failures now have nonzero process exits. Unknown status values fail closed. A failed search cannot become a successful founding worksheet. `draft-founding` is the preferred command; `founding-proposal` remains an alias producing the same explicitly synthetic draft.
- `reference.py` independently expresses eligibility and separation as unary and unordered binary constraints. It checks complete assignments and searches with minimum-remaining-values ordering and forward checking. It does not call the first implementation's eligibility, conflict, search, or witness functions.
- `assemble` invokes both bounded searches. A witness from either must satisfy both checkers. A negative report requires both searches to conclude infeasibility. Decisive disagreement returns exit 5; missing conclusions return exit 4.
- A domain-first simulator consumes frozen domain nominations and a recorded seed, traces each draw, checks complete results twice, and stops explicitly on dead ends.
- The owner-selected MIT license is included in the repository and package metadata.
- The root description identifies an offline reference model. Evaluation counts are no longer presented as progress toward a demonstrated governance advantage.

## Compatibility

This is a deliberate pre-1.0 CLI/report contract change. Design version 0.2 and its profile bytes do not change. API `solve` now returns scoped status names. Old report V1 files remain historical and fail the current `verify` command; regenerate a V2 report with `assemble`. No compatibility flag restores exit-zero failures or silently promotes a V1 witness.

| Earlier status | Current status |
| --- | --- |
| FEASIBLE | SYNTHETICALLY_SATISFIED |
| INFEASIBLE | SYNTHETICALLY_INFEASIBLE |
| SEARCH_INCOMPLETE | SYNTHETIC_SEARCH_INCOMPLETE |
| VALID_SYNTHETIC_ASSIGNMENT_WITNESS | SYNTHETIC_WITNESS_VALID |
| INVALID_WITNESS | SYNTHETIC_WITNESS_INVALID |

The two search budgets count different internal operations. `--max-nodes N` allocates N candidate expansions to each engine; their counts are not comparable performance measurements. Input validation, unary construction, and pair filtering consume additional time. Both searches can take exponential work in a generalized constraint problem; neither is a scalable CP/SAT backend, a wall-time limit, or a denial-of-service boundary. Use bounded trusted test inputs.

## Validation and what it cannot show

New regression coverage compares both implementations on the imported assignment fixtures, 200 seeded structural mutations, all 144 council/appeal permutations of the base witness, and every role/record substitution. The suite injects faults into the original conflict helper and confirms that the second encoding detects them. It checks budget cutoffs, invalid scope, nonzero exits, nominations, deterministic draws, exact rejection sampling, copy-invariant domain entries, and explicit dead ends.

These cases are implementation checks, not an independent proof, a complete model checker, or an empirical governance study. Both encodings were developed in the same project, read the same written contract, and share the strict roster-shape parser. An omitted requirement can be omitted from both. Controller closure is still wholly supplied input.

The original 121 tests remain, with status/exit expectations migrated where needed. The new software suite adds 25 tests. No new evaluation fixtures, trial arms, statistical significance claims, model calls, or live agent trials were added. Dated executed results belong in `docs/verification_0_2_0.json`; `docs/verification.json` records the initial import.

## Deliberately unresolved

Original source-artifact provenance, real controller/dependency verification, cognitive independence, full profile evolution, external audits, scalable solving, study isolation, multiplicity policy, and Metanoia/Adiona adapters remain open. This revision does not clear adoption or scored-study gates.
