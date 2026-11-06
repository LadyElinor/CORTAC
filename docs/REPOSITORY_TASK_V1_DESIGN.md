# R1: bounded repository tasks and a two-round self-application

Baseline: CORTAC `ea7a72456e00bd2b80aa4ccd9ae97262aedc3562`.
Motivation: Commonwealth M1 (`0302f350d7936050967e6e16b65e81a0c6a915ec`)
demonstrated that S1/S2 cannot admit repository patches, and that supplied
all-PASS reviews do not establish truthful or independent judgment.

This design is recorded before R1 implementation. It is exposed engineering,
not sealed preregistration, a model-backed efficacy trial, or an institutional
independence claim. One assistant/operator performs this work.

## Separate contract

Add an opt-in `cortac.repository-task.v1` profile. Preserve S1, S2, their source
pins, and the frozen solvers/studies. R1 must not masquerade as an AP1 workshop
proposal, become a new S2 admission type, or manufacture controller independence.

A host-owned task declares a Git base, exact allowed paths, named proposer and
reviewer with supplied controller declarations, protected limits, and a bounded
list of local check commands before the participant decides. Same-controller
roles remain admissible as explicitly shared-control research, never independent
review. A credential-free brief permits one propose, decline, wait or evidence
request. A proposal binds an observed candidate file inventory and changed paths.
It carries no executable command or merge permission. Only the host task chooses
the local test commands; running a check is an explicit custodian operation.

The repository observer compares actual regular file bytes against the named
base and refuses out-of-scope changes, unsafe paths, links and unsupported Git
entries. The recorded inventory includes tracked and nonignored new files;
ignored files, environment, tools, external services and common-host races are
outside its custody. Before and after each check, re-observe candidate bytes.
Mutation invalidates the check even if the process exits successfully. These
are observations, not a continuous filesystem lock or OS sandbox.

## Lifecycle and evidence

Use a bounded SQLite hash-linked journal with full deterministic replay. Retain
decision starts and invalid responses, check starts and observed finishes,
failures, timeouts, changed candidates, and advisory review. A missing finish
stays pending; do not silently retry or convert interruption into zero cost.
Each declared check runs at most once per task. A new revision needs a new task
and retains its predecessor's receipt as a reference, not transferred authority.

Tests run locally under the custodian's existing OS permissions; no network,
filesystem, process-tree or resource isolation is claimed. Record command,
candidate binding, observed exit, elapsed time and output digests separately.
Matching an expected exit is not proof of adequate tests or correct semantics.
Scope remains LOCAL_RESEARCH_ONLY, authority NONE, external execution disabled.
R1 explicitly performs local journal and test-process effects only.

An advisory record must bind the task, candidate and exact retained check-evidence
head. Check the declared reviewer and exact protected-limit inventory. Source
changes and additional evidence make earlier review inapplicable. Report local
check outcomes, supplied assessments, declared control overlap, and unestablished
independence separately. Even a complete all-PASS review cannot produce approval,
verified independence, an execution capability or an automated merge.

## Fixed validation and recursive stopping rule

Round 1: implement R1; exercise valid proposals and nonproposal outcomes, scope
escape, source changes before/during checks, stale evidence, wrong review role,
shared controller, fabricated all-PASS review, concurrent/duplicate starts,
interruption, failures, timeouts and journal tampering. Run an installed demo
outside the checkout. Preserve historical files and all original verification.

Round 2: use the implemented R1 lifecycle prospectively on one bounded CORTAC
maintenance issue. Investigate whether the current verifier's discovered-test
count can treat wholly skipped testing as success. Retain the baseline outcome,
including failure to reproduce a prediction. If demonstrated, add explicit
coverage accounting using real unittest results, preserving optional mixed
coverage and historical stage contracts. Declare the task and checks before
editing that verifier. Retain all observed failures and unknown review status.

Stop after these two rounds and necessary repairs to demonstrated counterexamples.
Do not tune trials to demonstrate agent efficacy, add general autonomous command
execution, or expand into new governance powers. Publish code, tests, receipts,
trust assumptions and ordinary reviewable PRs; do not merge them automatically.
