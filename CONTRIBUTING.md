# Contributing

Keep changes scoped to the offline tools and their documented contracts. Design authority, implemented constraints, and observed evaluation results are different claims.

1. Make a branch and describe the concrete behavior being changed.
2. Preserve synthetic status names, nonzero semantic-failure exits, `controller_closure: SUPPLIED_UNVERIFIED`, `authority: NONE`, disabled execution, and the distinction between fabricated smoke data and observations.
3. Use repository-relative paths and Python 3.10-compatible standard-library code for runtime tools.
4. Run `python scripts/verify.py`. New behavior needs a regression check when it changes interpretation, authority boundaries, or outputs.
5. Test an installed wheel outside the checkout when changing packaging or packaged data.
6. Include the command, observed result, and limitations in the pull request. A passing CI job does not establish branch protection or study authorization.

## Reporting correctness failures

A solver/checker disagreement (CLI exit 5) is one bug signal, not the only one.
Two encodings can share a mistake. Report an invalid accepted witness, a valid
roster incorrectly rejected, or an unauthorized scratch effect even when no
encoding disagreement occurs. Include the exact inputs, command and observed
versus expected result; preserve failing evidence rather than refreshing it away.

## Integrity and generated files

`BUNDLE_SHA256SUMS` covers the current bytes at the original component paths. Its initial values are preserved separately. `evaluation/SHA256SUMS` retains the unchanged evaluation inventory. `REPOSITORY_SHA256SUMS`, when present in a release archive, additionally covers the prepared repository. They detect changed bytes; they are not signatures.

The initial import was unchanged. Software 0.2.0 intentionally revises the offline code; the initial inventory remains in `provenance/initial_BUNDLE_SHA256SUMS`. Intentional development changes require reviewing and updating all affected generated hashes and reports. Evaluation provenance has interlocking file hashes: follow its README's generation sequence, then refresh its checksum index and the bundle/repository inventories. Never refresh checksums to hide an unexplained mismatch or to turn a blocked study into a ready one. Keep the original ZIP identity and initial inventory digest in `provenance/import.json` as historical provenance.

Byte-based checks depend on LF line endings. `.gitattributes` preserves those on Windows. Preserve UTF-8 when editing files. Use `.local/` for new run reports; committed component result files document the imported snapshot unless deliberately regenerated and reviewed.

The current profile validator supports one exact baseline structure and value set. Changing that baseline is a contract change, not merely a permissive parser tweak. Its accepted profile remains a design template.

## Licensing

This project uses the MIT license in `LICENSE`. Contributions should be available under those terms. Preserve copyright and third-party notices; do not assume that linked repositories or other people's material are relicensed by this project. See `docs/LICENSE_DECISION.md`.
