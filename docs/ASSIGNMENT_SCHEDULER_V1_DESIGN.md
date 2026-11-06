# S2: bounded scheduling of S1 assignments

Baseline: CORTAC S1 `f8c9db317b4aae56cd6203878a73022113f6b211`.
Recorded before implementation; exposed engineering design, not preregistration.
S1 and all historical experiment code/results remain unchanged.

S2 is a local, proposal-only coordinator over 1–16 pre-created, fresh S1 journals.
It does not create workshop identities, combine C2 bearers, invoke agents, submit
proposals, alter evidence access, or issue execution grants. It reads each source
through a single read-only SQLite snapshot and the pinned S1 replay function.
Imported metadata is an observation, not authentication or policy-fidelity proof.

Admission freezes the roster, source genesis, controller declarations, ordering,
decision/review deadlines and two separate dispatch budgets. Decisions rotate
round-robin across declared controller domains, FIFO within each domain; review
rotates across assigned reviewer domains. Multiple aliases in a declared domain
do not buy additional domain turns. Declarations are unverified. Domains with no
eligible work are skipped. Budgets count local scheduling reservations, not CPU,
tokens, host attempts, inspection credits, simulated world ticks, or success.

Decision and review capacity are separate. An accepted proposal with no pending
S1 operation becomes eligible for its assigned advisory reviewer. Exhausting
decision capacity cannot spend review capacity. Review absence/error remains
visible. No reviewer is replaced, appointed or deemed independent by a scheduler.

Only one unsettled assignment per workshop instance may be dispatched through
this coordinator. A started decision, unsubmitted proposal, unresolved transport
or pending operation holds that instance; elapsed time cannot clear uncertainty
or authorize resubmission. Other instances may progress. Observed accepted host
events invalidate queued briefs for the same instance conservatively; no silent
refresh/rebase occurs. This is local coordination, not a global lock on a host.

Scheduling requests bind an immutable request ID and lane. Repeating the same
request returns its historical reservation, never an additional dispatch. A
reservation is not a capability and may be stale when received. The host always
checks the actual proposal. No queued/unfinished work is reported as completed.

Trusted wall-clock milliseconds advance on explicit poll/claim calls. Commit the
clock observation before source I/O/selection; rollback refuses scheduling.
Deadlines expire queued work even when participants do nothing. Started work
stays outstanding past its deadline; no automatic lease expiry or retry. This
is a pull coordinator, not a timer daemon or timing-SLA claim. Clock and storage
remain host-controlled. Deadline expiry is distinct from observed late completion.

Source extensions must retain the previously observed source head at its sequence.
Unavailable, truncated, rewritten or unexpectedly advanced unleased source work
is recorded as a source problem and cannot make a fresh dispatch eligible. A
later restored authentic-looking source may be observed again, but detected
out-of-band activity is not silently adopted as authorized scheduling.

S2 has its own bounded SQLite hash journal and replay, separate from S1. Reports
show reservations, remaining budgets, outstanding decisions/transport, stale or
expired queued work, reviewer availability, advisory assessments and lateness
separately. No correctness, peer-harm or retaliation inference from these counts.

Acceptance: hand-computable controller rotation and FIFO; clone aliases; reserved
review after ordinary exhaustion; concurrent/idempotent claims; restart; passive
expiry; late work; rollback; source rewrite; missing files; out-of-band actions;
unknown transport blocks same-instance work but not other instances; accepted
head invalidates queued briefs; scope and report tampering; real pinned B1.1/C2
integration; preservation of S1 and the existing historical files. All observations
are exposed conformance cases, with no model calls or independent efficacy claim.
