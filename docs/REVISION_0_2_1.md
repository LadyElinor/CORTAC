# Software 0.2.1: portability and certificate verification repair

This narrow repair follows inspection of commit `f2c9c29ef09d199e55f76c3f6c5a7b7d0b2cd882` (software 0.2.0). The MIT license, design 0.2, constraint encodings, synthetic status meanings, lottery simulator, and closed study gates are unchanged.

## Portable fixture generation

`evaluation/common.py` now writes JSON as UTF-8 bytes with LF line endings. `generate_fixtures.py` stores inventory paths using POSIX separators. This avoids both Windows text-mode newline translation and platform-dependent inventory keys. No committed fixture bytes or expected fixture hashes were changed.

Three portability regressions check Unicode encoding and regenerate all fixtures under Windows newline emulation, including a separate Windows path-syntax emulation. The pinned `seed_lists.json` SHA-256 remains `5c1c4a92160e866f89a29d7a378596131ef9cb8fa63966898bbadb3714ff775c`. These are Linux-hosted emulations, not native Windows execution.

## Closed certificate metadata contract

Verification now requires exact types and supported values for every scope-bearing V2 field, including the nested cross-check, decision, appeal and profile-validation claims. Unknown and missing fields are rejected. Recomputing the report hash cannot make an external-audit claim, verified-ballot claim, or verified appeal-capacity claim acceptable. Nine regression tests include the three reported mutations, bool/integer ambiguity, missing and extra fields, other contradictory claims, and compatibility with honest 0.2.0 and 0.2.1 certificates.

Search telemetry must have the expected types and internally consistent counters/statuses. It remains unauthenticated diagnostic data: verification does not replay either search or authenticate who produced a report. Both constraint implementations recheck the assignment. Controller declarations and input truth remain unverified.

## Consistent delivery instructions

`UPLOAD.md` now describes the complete Git bundle actually delivered. The nonexistent patch and incorrect no-history description have been removed. The outer `PUSH_TO_GITHUB.txt` is copied from those same instructions. Import and push use ordinary fast-forward checks without resetting or force-pushing.

## Validation scope

The full gate requires 158 tests across four suites and 12 verification stages, including both deliberate scored-study refusals. `verification_0_2_1.json` records the observed local run. The existing CI matrix includes Windows Python 3.12; a successful native Windows run must be observed separately after publication. No real-agent performance, external audit, live authority, or scored study is claimed.
