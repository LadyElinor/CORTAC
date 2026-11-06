# S2: compose S1 assignments with bounded scheduling

`cortac.assignment-scheduler.v1` is an opt-in pull coordinator over **1–16 fresh
S1 journals**. It provides deterministic controller rotation, FIFO ordering within
each controller's eligible work, separate decision/review dispatch budgets,
durable reservations, deadline checks and uncertainty-aware instance holds.

It does not run agents, submit proposals, pool host credits, add workshop seats,
discover independence, alter evidence access or issue authority. S1 and C2 remain
the only participant lifecycle/transport path. All S2 outputs retain
`LOCAL_RESEARCH_ONLY`, `authority: NONE` and `execution_enabled: false`.
The [design](ASSIGNMENT_SCHEDULER_V1_DESIGN.md) predates implementation. This is
exposed engineering development, not an efficacy study or sealed preregistration.

## Scheduling contract

Admission freezes assignment order, source genesis, declared controllers,
deadlines and two budgets. Each valid reservation spends one unit in its lane,
even if the participant later declines, fails or does nothing. A request with no
eligible selection spends no dispatch unit but remains recorded. There are no
refunds, identity changes or automatic requeues. Repeating an existing request ID
returns the same historical reservation; changing its lane is refused.

Decision scheduling rotates over lexically ordered **declared controller domains**.
Within a domain it selects the first eligible assignment in admission order.
For admission order A1, A2 (controller A), B1 (controller B), selection is A1, B1,
A2 when all remain eligible. Aliases within A add work but not another domain turn.
Lying about controller relationships defeats this rule; no authenticated Sybil
resistance is claimed. Review uses the same algorithm over assigned reviewer
controllers, which S1 requires to differ from each proposal's declared controller.

Review becomes eligible after an observed accepted proposal with no pending S1
operation. Exhausting decision reservations cannot consume review reservations.
This protects the **dispatch budget**, not physical CPU, storage, reviewer time
or availability. The bounded shared journal and trusted host can still stop both
lanes. No substitute reviewer or review approval is manufactured.

| Source state | Coordinator behavior |
| --- | --- |
| Queued, fresh, before deadline | Eligible if its lane has capacity and instance is not held |
| Reserved decision not yet returned | Hold that workshop instance; never reissue on timeout alone |
| Proposal not submitted or transport unresolved | Hold instance; other instances may progress |
| Accepted host receipt | Mark other queued briefs on that instance stale conservatively; enable assigned review when no operation is pending |
| Decline, wait, evidence request, invalid response, timeout or crash | Preserve the exact local outcome; no automatic retry or evidence delivery |
| Source missing, malformed, truncated or rewritten | Retain last observation, flag unavailable and hold instance |
| Unreserved decision/review activity | Sticky out-of-band flag; do not silently adopt it as scheduled work |
| Review FAIL/UNKNOWN or absent | Report supplied assessment or absence; never convert it into approval |

Multiple S1 assignments may reference one workshop, but they do not become
independently admitted workshop roles. A local instance hold is not a global lock:
other custodians or the host may act outside this coordinator. B1.1 still rejects
stale proposals at the actual submission boundary. A reservation binds the
observed S1 head and may already be stale when received; it is not a capability.

## Deadlines and time

Decision and review deadlines are absolute trusted-host wall-clock milliseconds.
Equality with the deadline is expired. `poll`/`claim` first commit a nondecreasing
clock observation, then read sources. `claim` observes time again under its
selection lock so source I/O or lock contention cannot authorize a late dispatch.
That second clock observation survives a request-ID conflict. Clock rollback
refuses further polling/scheduling; historical reports and reservations remain
readable. A forward clock jump can deny service. There is no secure-time claim.

No participant command is needed for elapsed time to make queued work ineligible.
Expiry is evaluated when the coordinator is next polled; there is no timer daemon
or wall-time SLA. Started work is retained past its deadline, including uncertain
submissions. S2 records whether completion/review was **observed late**, not the
unknown actual completion time. Dispatch counts are not decision-clock slots,
inspection credits, model tokens, money or proof of successful work.

## Run

Create fresh S1 journals using the [S1 interface](AGENT_SCAFFOLD_V1.md). From an
installed CORTAC environment, the following example admits existing `a.sqlite`
and `b.sqlite` with one-minute decision and two-minute review deadlines:

```python
from pathlib import Path
import time
from wac_offline.scheduler_v1.store import Scheduler

now = time.time_ns() // 1_000_000
manifest = {
    "decision_budget": 2,
    "review_budget": 1,
    "jobs": [
        {"path": str(Path(p).resolve()),
         "decision_deadline_ms": now + 60_000,
         "review_deadline_ms": now + 120_000}
        for p in ("a.sqlite", "b.sqlite")
    ],
}
Scheduler.create("team.sqlite", manifest)
```

Or save that manifest as JSON and use `python -m wac_offline.scheduler_v1 new
team.sqlite manifest.json`. New database paths must not exist; source paths must
be absolute. Other commands:

```sh
python -m wac_offline.scheduler_v1 claim team.sqlite decision decision-001
python -m wac_offline.scheduler_v1 reservation team.sqlite decision-001
python -m wac_offline.scheduler_v1 poll team.sqlite
python -m wac_offline.scheduler_v1 claim team.sqlite review review-001
python -m wac_offline.scheduler_v1 report team.sqlite
```

The custodian maps the selected assignment ID to its original S1 journal, obtains
its brief and runs the participant separately. S1/C2 submission remains explicit.
`reservation` recovers a lost scheduling reply without making another selection.
If no assignment was selected, that request ID continues to mean no selection;
a genuinely new scheduling request uses a new ID. Never use new S1/C2 IDs to
bypass uncertain transport. `report` reads the last retained observations;
`poll` refreshes them. Exit 0 means a valid local report/reservation, including
no selection; exit 2 means refusal. Neither means work completed or authorized.

The coordinator does not consume credentials or write S1/host databases. Its own
SQLite journal uses exclusive creation, transactional serialized reservation,
hash linking and full replay. Sources are read in a single read-only transaction
through the pinned S1 reducer. Previously observed source hashes must remain a
prefix of later histories. This detects inconsistent replacement relative to
retained files, not an operator able to rewrite both histories and programs.

Limits: 16 assignments, budgets 0–32 per lane, 512 scheduler events, S1's 128-event
source limit, bounded JSON and trusted local paths. Protect the files; this is not
a sandbox, cross-host lock, production scheduler or control over nonparticipants.
It neither imports CORTAC lottery witnesses as credentials nor converts a
Commonwealth acceptance receipt into an appointment.

## Guarantee map

| Guarantee | Check and counterexample | Remaining assumption |
| --- | --- | --- |
| Controller rotation, FIFO within eligible domain work | Deterministic replay; hand order A1/B1/A2; alias tests; repaired-hash wrong selection refused | Supplied controller names, frozen roster, only this coordinator's reservations |
| Shared dispatch ceilings and separate review budget | Atomic reservations, concurrent different-ID test; review available after decision exhaustion | No reserve of CPU/storage/actual reviewer availability |
| Lost scheduling reply does not allocate twice | Immutable request-ID/lane mapping, concurrent same-ID and restart tests | Local DB not cloned or maliciously rewritten |
| Time cannot silently reopen expired work | Committed clock floor, post-I/O deadline check, rollback and conflicting-ID tests | Host wall clock/storage trusted; pending work intentionally does not auto-expire |
| Unknown submission does not release same-instance work | Real dropped reply holds instance; lookup still unresolved; exact retry resolves | S1/C2 trusted local observations, no global host lock |
| New accepted head cannot silently rebase another brief | Queued same-instance assignment becomes stale | Only observed receipts; host still performs final fresh-head check |
| Source changes are attributable to retained history | Read-only consistent snapshot, prefix checks, rewritten/missing-source tests | Full consistent forgery by common operator remains possible |
| Out-of-band activity remains visible | Sticky contamination flag for decision/review without reservation | Activity outside recorded S1 cannot be discovered |
| Reports preserve accounting and scope | Full S2 replay plus separate `audit.py` chain/reservation recount; altered counts refused | Second implementation checks only listed fields, not eligibility, policy choice, source authenticity or every report row |
| Prior work remains reproducible | 135 baseline file digests, historical tests and replay | Same-project verification, no institutional independence claim |

## Validation commands

```sh
python scripts/verify.py
PYTHONPATH=package python -m wac_offline.scheduler_v1.demo
# Requires the exact Commonwealth checkout and installed C2 documented by S1:
python scripts/scheduler_commonwealth_integration.py /path/to/unfinished-commonwealth
```

The optional integration first repeats S1's seven pinned transport cases. It then
uses two real loopback workshops and three S1 assignments: lose a committed reply,
allow the other instance to progress, retain the hold after lookup, recover with
exact retry, stale the queued same-instance brief, exhaust two decision reservations and
still reserve one advisory review. The accepted proposal consumes one host attempt
and one proposal event. All cases are exposed; controllers share one trusted test
host. No model calls, independent evidence custody or efficacy claim follows.
