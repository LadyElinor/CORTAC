# Proposed repository and release controls (not installed)

As checked on 2026-10-08, GitHub reports `main` unprotected and the repository's
parent-inclusive ruleset listing empty. This is an observation, not an exhaustive
audit of every possible organization or deployment control. This software
revision does not change GitHub security or access settings.

## Scoped main-branch proposal requiring owner approval

Target only `refs/heads/main` in `LadyElinor/CORTAC`:

- Require a pull request with at least one independent approving reviewer.
- Dismiss stale approvals when new changes arrive; require approval after the
  latest push, and require all review conversations resolved.
- Require the branch to be up to date and all four current check contexts:
  - `Verify ubuntu-latest Python 3.10`
  - `Verify ubuntu-latest Python 3.12`
  - `Verify ubuntu-latest Python 3.14`
  - `Verify windows-latest Python 3.12`
- Block force pushes and deletion; apply restrictions to administrators and avoid
  a silent bypass list.

These exact check names were observed in workflow run `37781999630`; reverify
names on the current revision before applying settings. A proposed check that
never runs can unintentionally block every merge. A draft PR or a successful CI
run does not itself establish protected review.

**Solo-maintainer consequence:** mandatory independent approval can lock merges
if no other qualified reviewer has access. Identify an eligible reviewer and a
separately approved emergency-access procedure before enabling these rules.
Do not lower safeguards silently to escape that condition. This document neither
invites collaborators nor grants access.

## Separate production work

Identify the actual owners for review-sensitive paths before adding CODEOWNERS;
a placeholder owner is not independent review. Define protected release tags,
reviewed reproducible artifacts, signer/provenance verification, and deployment
acceptance rules only after the actual release process and authorized people are
known. Credentials, persistent access, security settings and signing operations
require their own approvals; none are implied here.

Inventory every policy, registrar, gateway, capability, storage, credential and
configuration route that can change enforcement. An independent execution
boundary must accept only the approved artifact and close alternate effect
paths, with authenticated principals, durable state and witnessed history.
Hashes alone cannot prove this coverage or that an artifact is running. Repository
protection cannot substitute for deployment separation or repair authority.
