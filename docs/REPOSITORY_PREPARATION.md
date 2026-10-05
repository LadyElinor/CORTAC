# Repository preparation

Prepared for `LadyElinor/CORTAC` on 4 October 2026 UTC from the uploaded `WAC_v02_Offline_Tranches(1).zip`.

The destination metadata identified a public, empty repository with default branch `main`. No remote files, commits, branches, issues, settings, or releases were created or changed during preparation.

## Included changes

- Root README and Windows/macOS/Linux upload instructions.
- A Python package definition and `wac-offline` console entry point, retaining software version 0.1.0 and design version 0.2.
- Packaged JSON baseline data for installed CLI operation.
- Repository-root CLI wrapper and verification runner with explicit expected-failure checks.
- Read-only GitHub Actions workflow with pinned checkout/setup action commits; Linux and Windows jobs configured.
- Git ignore rules and LF checkout rules for hash-bound files.
- Import provenance, a new local verification receipt, and a prepared-repository checksum inventory.

All 80 incoming bundle files are retained byte-for-byte. Their component directories and relative paths are unchanged. No original solver, evaluator, fixture, stored output, or authority gate was modified. Historical component verification records remain historical; `docs/verification.json` is the fresh repository-level check.

## Validation scope

The four provided suites contain 55 offline-tool, 49 evaluation, 11 assignment-adversarial, and 6 evaluation-adversarial tests. Preparation reruns these 121 software tests, verifies the supplied assignment witness, and checks both deliberate exit-2 study refusals. Packaging additionally checks the CLI and frozen baseline from an installed wheel outside the source tree, and verifies the extracted delivery archive.

The fresh JSON receipt records the actual interpreter/platform and commands. Only the locally observed platform is validated by that receipt. Other CI matrix entries remain configured, not observed. No model calls, agent trials, GitHub workflow runs, or deployment validation are claimed.

The package is ready to import as repository content. It remains an offline research scaffold with no license selection, signed adoption, real scored runner, or live enforcement.
