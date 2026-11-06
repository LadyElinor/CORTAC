# S1: agent lifecycle scaffold design

Baseline: CORTAC `9eb2a14` on main. This design precedes implementation and
conformance results. It is exposed engineering development, not preregistration
or an efficacy experiment. Existing research reducers and outputs stay frozen.

S1 is a separately versioned, durable, single-assignment lifecycle coordinator.
It accepts a credential-free Commonwealth AP1.1 workshop brief, records one
bounded agent decision (or invalid/timeout/crash), stages a proposal through the
optional separately installed C2 client, and records transport observations.
Only a trusted custodian supplies the endpoint and credential. No participant
can append workshop events, invoke keeper operations, or acquire execution power.

Three states stay separate: decision disposition, C2 transport disposition, and
host authority (always NOT_OBSERVED by this interface). Local observations cannot
be substituted for host receipts. An optional CORTAC supplied decision record is
an advisory review, not a host approval. It must be attributed to the assigned
reviewer with a different declared controller; these declarations remain unverified.

The local SQLite journal uses exclusive creation, BEGIN IMMEDIATE, exact event
schemas, SHA-256 linking and deterministic replay before append/report. It has
an immutable genesis, bounded events, and no mutable snapshot as a second source
of truth. Network work is never done inside a journal transaction. Operation
starts commit before calls; interrupted operations remain visible. One retained
outbox binding per assignment is immutable. Stage recovery may adopt ONLY an
existing C2 outbox matching endpoint, credential digest, instance, request ID and
exact original request bytes. Missing/corrupt ambiguous state is not restaged.

AP1.1 compatibility is pinned to unfinished-commonwealth `3688dcd`. A small
attributed port of its brief projection and decision validation removes host/C2
imports. The C2 transport itself is optional, never copied into this distribution.
Default tests and a deterministic demo run offline. A separately invoked pinned
checkout integration tests real B1.1 loopback/C2 behavior; it is trusted-host
evidence, not isolation or deployment evidence.

No agent code executes inside the custodian. External programs exchange JSON
files/stdin using a public brief; S1 does not launch arbitrary subprocesses.
Timeout/crash are caller-observed labels, not an attestation of runtime behavior.
No model calls, shared decision-clock scheduler, multiple admitted proposers,
production service, cross-project warrant conversion or external effects are
introduced. Waiting/evidence requests remain explicit local outcomes.

Acceptance: successful propose/decline/wait/evidence request; malformed, duplicate
JSON and wrong-brief decisions; timeout distinct from abstention; restart/replay;
tampered journal and repaired-hash semantic contradictions; stage interruption;
lost reply and exact retry; stale-view refusal; missing/expired credentials;
conflicting outbox; reviewer mismatch; review FAIL/UNKNOWN; attempts and measured
elapsed time separate from synthetic slots; no new authority. Preserve historical
files by digest and run repository checks plus installed-package smoke checks.

Each guarantee will map to a check, a counterexample and its residual assumption.
Accounting consistency, fixed-policy fidelity and external evidence authenticity
remain separate. No improvement in governance effectiveness is claimed.
