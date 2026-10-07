# Frozen mechanism sandbox (7 October 2026)

**SCRIPTED MECHANISM SIMULATION. No model calls, real agents, external actions,
controller authentication, or deployment-safety validation.** This is separate
from the blocked model-study scaffold in `evaluation/`.

The original frozen runner, tests, protocol, source references, result report and
independent review are preserved byte-for-byte. The report describes the original
standalone delivery package, which included raw traces and receipts. This compact
repository copy instead regenerates all outputs; it does not include those large
generated files or the original package inventory. Statements such as “no source
repository files are changed” in the frozen protocol describe that original run,
not this later repository integration. The pinned baseline is software 0.2.1,
commit `20fd02fedf73ebd9b271ce5d13243ccb7de4e14b`.

From the repository root, Python 3.10+ with no dependencies:

```sh
python -m unittest discover -s sandbox -p test_runner.py -v
python sandbox/runner.py --output .local/sandbox-results
python sandbox/verify_replay.py
python scripts/verify.py
```

The runner rechecks its frozen input hashes. `verify_replay.py` checks them with
explicit exceptions (also under Python optimization), runs all 22,400 episodes
in a temporary directory, then checks all six deterministic output hashes,
episode/environment counts and the zero-model-call receipt. Runtime seconds are
machine-dependent and excluded from equality checks. The runner is preserved,
including native-platform output line endings: replay hashes normalize only CRLF
to LF, including CSV row endings. On LF systems raw JSONL is byte-identical to
the original raw output (`7cc2d7c8a4164e080a33957751c63e643b0b21ffe58c25bafc6ea49fde25dd9d`).

The 13 planted controls and complete deterministic replay are included in
repository verification/CI. `expected_outputs.json` records observed output
hashes from the completed run; it is a regression oracle, not a preregistered
prediction. Do not tune this frozen experiment after inspecting its results.
A changed mechanism requires a separately labeled protocol revision and review.

See [original report](report.md), [review](independent_review.txt),
[frozen protocol](protocol.md), and [claims and evidence gates](../docs/EVIDENCE_GATES.md).
