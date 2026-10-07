# CORTAC: synthetic governance constraint tools

CORTAC currently implements an **offline reference model**, with two constraint encodings, exact governance arithmetic, and a reproducible domain-first lottery simulator. It does not implement a confederation of agents. “Confederation of Recursive Teleological Agentic Constructs” names the proposed project, not an existing capability.

**Software 0.2.1; Warranted Agent Commonwealth design 0.2.** All controller declarations are supplied and unverified. Every assignment status says `SYNTHETIC`; the profile remains unratified and execution-disabled. No agents, credentials, grants, signatures, appointments, or model-backed scored governance study are produced.

## Run the checks

Python 3.10 or newer; runtime and tests use the standard library. Installation and API keys are unnecessary.

```sh
python scripts/verify.py
python scripts/wac.py assemble --profile package/inputs/profile.extracted.json --roster package/fixtures/feasible.json
python scripts/wac.py verify --profile package/inputs/profile.extracted.json --roster package/fixtures/feasible.json --certificate package/results_v2/assignment.json
python scripts/wac.py lottery --profile package/inputs/profile.extracted.json --roster package/fixtures/feasible.json --roll package/results_v2/lottery_roll.json --seed 0000000000000000000000000000000000000000000000000000000000000000
```

On Windows use `py -3` instead of `python` if necessary. `scripts/verify.py` also works by absolute path from outside the checkout. `--report .local/verification.json` saves a dated local verification receipt.

## Results and exit codes

| Exit | Meaning |
| --- | --- |
| 0 | Supported profile, doubly checked synthetic assignment, complete simulated draw, or passing arithmetic |
| 2 | Invalid/unsupported input, invalid witness, or unknown result status |
| 3 | Synthetic infeasibility concluded by both searches, or failing governance arithmetic |
| 4 | Search incomplete, or lottery dead end; neither establishes infeasibility |
| 5 | Constraint implementations disagree or a complete draw fails a checker |

Assignment statuses are `SYNTHETICALLY_SATISFIED`, `SYNTHETICALLY_INFEASIBLE`, and `SYNTHETIC_SEARCH_INCOMPLETE`. Successful reports bind `controller_closure: SUPPLIED_UNVERIFIED`, synthetic scope, and `authority: NONE`. Verification rejects removed or promoted scope fields even after the body hash is recomputed. These are checks on supported files, not protection against edited screenshots or a modified verifier.

`assemble` runs lexical DFS and a separately encoded unary/binary constraint search with minimum-remaining-values ordering and forward checking. Either search's witness must pass both checkers. A negative report requires both searches to conclude infeasibility; an unresolved search cannot supply that conclusion. The encodings share the roster-shape parser and the written specification. This is implementation diversity, not an external audit or authenticated proof of independence.

The lottery draws uniformly over each current eligible **domain** under its frozen nominee map. Each domain supplies one nominee per role; copies do not add lottery entries. Draws preserve the domain exclusions for council and appeal seats. The simulator records the first dead end and never retries it automatically. Its user-chosen seed, frozen file, and nominations have no authenticated real-world chronology. A complete draw does not appoint anyone. See the [selection contract](docs/LOTTERY.md).

## Completed scripted mechanism sandbox

A [frozen, reproducible sandbox](sandbox/README.md) ran 22,400 scripted episodes with zero model calls. The same-policy centralized and full arms match exactly. Additional checks trade off modeled wrong effects, abstention, cost and staffing under specified fault assumptions; common-mode faults remove the apparent redundancy gain. This does not identify a decentralization or real-agent advantage.

The [claims and evidence gates](docs/EVIDENCE_GATES.md) distinguish five authority functions from council seats, preserve lean routine standing-warrant lanes and consequential safeguards, and specify the model-backed validation needed before stronger claims. The frozen runtime profile is unchanged.

## What remains research plumbing

The evaluation directory contains **exposed development fixtures and fabricated smoke rows**. Its example counts, proposed arm slots, and bootstrap iterations measure the size of that plumbing, not empirical evidence. Most examples vary one structural template. Its intervals are marginal, without multiplicity control; they cannot support a governance-advantage claim. There is no real scored runner, sealed holdout, validated judge, or independently controlled participant trial.

Both commands deliberately refuse with exit 2:

```sh
python evaluation/readiness.py --require-scored-ready
python evaluation/analyze.py --mode scored
```

An ordinary readiness check can exit 0 while reporting `SOURCE_GATED_NO_SCORED_RUN`: it has checked offline file integrity only.

## Components and boundaries

| Path | Purpose |
| --- | --- |
| `package/wac_offline/solver.py` | Original lexical joint case-and-appeal search |
| `package/wac_offline/reference.py` | Separate constraint encoding, checker, and MRV search |
| `package/wac_offline/lottery.py` | Frozen nominations, domain draws, trace, explicit dead ends |
| `package/tests/test_revision.py` | Differential cases, injected faults, lottery and CLI contracts |
| `package/results_v2/` | Current synthetic examples |
| `evaluation/` | Preserved, blocked model-study scaffold |
| `sandbox/` | Frozen scripted mechanism experiment, controls and replay hashes |
| `provenance/` | Initial import identity and revision record |

The [tool contract](package/README.md) describes the declared model. [0.2.1 repair notes](docs/REVISION_0_2_1.md) cover portable fixture bytes, strict nested certificate claims, and bundle upload instructions; [0.2.0 revision notes](docs/REVISION_0_2_0.md) describe the preceding feature revision. `package/results_v2/` retains the compatible 0.2.0 examples. The initial `START_HERE.txt`, `package/results/`, `verification/*results*`, and `docs/verification.json` are historical 0.1.0 records. New code intentionally changes some imported files; current inventories reflect that development. The original inventory is retained at `provenance/initial_BUNDLE_SHA256SUMS`.

Original JSON/DOCX identity fields remain null in the inherited provenance. Their labeled text exports have not been reclassified as authenticated originals. The profile validator still accepts one exact frozen baseline; profile evolution needs a separately versioned contract. Neither constraint encoding discovers missing controlling interests, verifies declarations, or infers cognitive independence.

[Metanoia](https://github.com/LadyElinor/Metanoia) and [Adiona](https://github.com/LadyElinor/Adiona) inform the design; this repository has no adapters or compatibility claim for them. All tools remain offline. Optional `python -m pip install .` installs the `wac-offline` CLI and profile data; installation may fetch the setuptools build dependency.

## Development

Run `python scripts/verify.py` before proposing changes. CI is configured for Linux Python 3.10, 3.12, 3.14 and Windows Python 3.12. Configured jobs are not evidence that this revision has run remotely. See [contributing](CONTRIBUTING.md) and [updating GitHub](docs/UPLOAD.md).

Licensed under the [MIT License](LICENSE). See the [licensing record](docs/LICENSE_DECISION.md) for scope and the owner's selection.
