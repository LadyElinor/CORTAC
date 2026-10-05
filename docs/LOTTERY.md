# Synthetic domain-first selection

The WAC 0.2 profile requires a frozen eligibility roll and seed procedure, a uniform domain draw with one entry per eligible domain, and a qualified delegate nominated by each selected domain. It does not supply an authenticated randomness source or a complete policy for failed draws. This simulator provides one explicit **experimental** policy. It does not ratify that policy or authenticate any declaration.

## Frozen inputs

Use the unchanged profile, a supported synthetic roster, and a nomination map. The map names all twelve concrete roles and, for each role, exactly one qualified candidate for each domain passing the independently encoded unary eligibility checks. A domain cannot be silently omitted. `package/fixtures/lottery_nominations.json` is a synthetic example.

For this experiment, each domain precommits its nominee for every role before the seed is supplied. This is a concrete choice for the otherwise unspecified delegate procedure. The nomination file represents those choices; the program does not impersonate or authenticate a principal. It does not select a delegate by counting copies.

```sh
python scripts/wac.py prepare-lottery --profile package/inputs/profile.extracted.json --roster package/fixtures/feasible.json --nominations package/fixtures/lottery_nominations.json
```

The output binds exact local profile/roster byte hashes, role order, nominations, seed procedure, and the no-redraw rule. Its hash uses the package's non-JCS report serialization. It proves no chronology or authenticity. A caller can rewrite the file and recompute a hash.

To save the roll with Windows PowerShell 5, pipe this ASCII JSON output to `Set-Content -Encoding Ascii frozen-roll.json`; ordinary `>` may produce UTF-16. Check `$LASTEXITCODE` before using the file. On a UTF-8 shell, normal redirection is suitable.

## One attempt

`lottery --roll frozen-roll.json --seed <64 lowercase hex characters>` checks the complete supported frozen contract against current input bytes. The all-zero seed in the root README is a repeatable test vector, not acceptable public entropy for real appointments.

The twelve-role order is fixed and included in the roll. At each role:

1. Filter the frozen nominees against already drawn roles using the second constraint encoding.
2. Give each remaining domain one entry, sorted by domain ID for reproducibility.
3. Draw an index with rejection sampling from a SHA-256 counter stream keyed by the supplied 256-bit seed.
4. Record the eligible domains, selected domain, nominee, conditional probability, and random words consumed.

The sampler rejects the uneven tail instead of using biased modulo reduction. Its uniformity statement is conditional on uniform source words; a seeded hash stream is a reproducible simulation, not a proven random beacon. Tests exhaust an 8-bit sampler's accepted words and check equal counts for each index, including the rejection branch.

Council domains and appeal domains cannot repeat within their respective panels. Case/appeal control exclusions apply throughout. Other roles may reuse a domain where the constraint model allows it. A complete draw must pass **both** assignment checkers.

## Dead ends and limits

A role with no remaining nominees ends the attempt with `SYNTHETIC_LOTTERY_DEAD_END`, exit 4. The partial trace is retained and `assignment` is null. There is no automatic redraw, backtracking, seed search, or fallback to a favored delegate. The joint-backtracking fixture has a feasible assignment but can still produce a dead-end lottery draw; that behavior is tested.

Each eligible domain has probability 1/k at a particular draw under the frozen inputs and current prefix. This does **not** make complete assignments uniformly distributed. Nor does it equalize each domain's eventual appointment probability if someone repeatedly retries failures and retains only successful attempts. Any real retry policy would need separate adoption and analysis.

Adding copies leaves draw chances unchanged **when the eligible domain set and frozen nominees remain the same**. Tests add fifty council copies and compare the entire trace over twenty seeds. New qualifications or changed nominations can legitimately change eligibility; no broader clone-invariance claim is made.

The simulator cannot establish verified controller closure, real competence, funded appeal continuity, impartial seed selection, genuine principal nominations, or constitutional appointment authority. Authentication, chronology, and any failed-draw recovery policy remain unimplemented.
