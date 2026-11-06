# R1: repository tasks with observed evidence and advisory review

R1 (`cortac.repository-task.v1`) is a separate, opt-in local custodian lifecycle.
It accepts a repository maintenance task without turning it into an AP1 arithmetic
proposal. S1/S2 remain unchanged; S2 does **not** schedule R1 tasks.
The [design](REPOSITORY_TASK_V1_DESIGN.md) bounds this tranche and its
[retained self-application](R1_SELF_APPLICATION.md).

The host declares the base commit, exact allowed paths, proposer/reviewer labels,
protected limits and Python check commands. A participant supplies one JSON
proposal, decline, wait or evidence request. It cannot supply test commands,
authorize a merge, alter the review inventory or create independent operators.
Shared-controller roles are permitted and reported as `SHARED`; different supplied
labels mean `DIFFERENT_UNVERIFIED`. Independence and approval stay false even when
all supplied assessments say PASS.

## Local use

Install the package, or set `PYTHONPATH=package` from the checkout. For a complete
example using a disposable Git repository and an actual local test process:

```sh
python -m wac_offline.repository_task_v1.demo
python -m wac_offline.repository_task_v1 --help
```

A host task JSON contains `version`, `id`, `base_commit` (full SHA-1 commit),
`allowed_paths` (1–64 exact repository-relative paths), `checks` (1–8),
`proposer`, `reviewer`, `proposer_controller`, `reviewer_controller`,
`protected_limits`, `purpose`, and `parent_receipt` (null or an unauthenticated
prior-report digest). Each check declares `id`, `argv` beginning with `{python}`,
`cwd` (`.` or a relative directory), `expected_exit` and `timeout_seconds` (1–120).
See the [demo task](../package/wac_offline/repository_task_v1/demo.py).

```sh
python -m wac_offline.repository_task_v1 new task.sqlite /path/to/repository task.json
python -m wac_offline.repository_task_v1 begin task.sqlite > brief.json
# A separately operated participant may inspect an authorized disposable copy.
# The custodian observes the proposed files; R1 does not write or apply patches.
python -m wac_offline.repository_task_v1 candidate task.sqlite
python -m wac_offline.repository_task_v1 decide task.sqlite decision.json
python -m wac_offline.repository_task_v1 check task.sqlite check-id
python -m wac_offline.repository_task_v1 report task.sqlite
python -m wac_offline.repository_task_v1 review task.sqlite review.json
```

A proposal has exactly `version`, `brief_id`, `choice: propose`, `reason` and the
observed `candidate_digest`. Other choices have no candidate digest. The brief
contains base file hashes and declared check IDs; execution argv and local paths
stay in the custodian's journal. Missing code/context must be obtained through the
operator's authorized interface; the brief alone is not the complete repository.
There is no provider invocation, credential handling, automatic patch application,
network transport, Git commit, push or merge in R1.

Review JSON contains `reviewer`, `candidate_digest`, `evidence_digest`, and a
`cortac.decision.record.v1` record. All declared check observations must exist.
References inside the record must resolve to `task`, `candidate`, or an observed
`check:ID`; their bound digests appear in the report. This checks resolution and
binding, not whether the cited evidence supports the prose or assessment.

Exit 0 means a supported local operation, including declines or an advisory
UNKNOWN review. Exit 2 means invalid/refused input; an invalid decision remains
journaled by byte digest. Exit 3 means an observed check did not match its declared
successful condition. None means authority, correct semantics or readiness.

## What persists

The SQLite journal uses exclusive creation, hash links and deterministic replay
before every mutation. One participant attempt is admitted. Each declared check
can start once, and only one check is pending at a time. An interrupted start
remains pending through restart and cannot be retried automatically. Keep the
journal; investigate before beginning a new task. A `parent_receipt` reference
neither resolves uncertainty nor transfers authority.

Every executed check records observed exit (including native Windows failure
codes), elapsed nanoseconds and stdout/stderr byte counts and SHA-256 digests.
Raw output is not placed in the journal. FAIL, TIMEOUT, ERROR, OUTPUT_LIMIT,
SOURCE_CHANGED and SOURCE_UNAVAILABLE remain distinct. Source is re-observed
before and after checks and before review. Different current bytes invalidate
review applicability even if an earlier check exited 0. Historical outcomes
remain intact. A report without source refresh makes no freshness claim.

`local_checks_passed` describes retained exit/source observations, not present
correctness. Read it with `candidate_current`. `review_applicable` means the
record still addresses the observed bytes, not that its judgments are true.
Matching an expected exit 2 can test a refusal; it is not a successful execution
of the rejected operation. No overall governance score is produced.

## Boundaries

| Guarantee | Concrete check | Remaining assumption |
| --- | --- | --- |
| Only scoped candidate changes | Full admitted base inventory versus tracked/nonignored new bytes; retained base paths cannot be hidden by untracking and ignore rules | Git/base/root and host remain trusted; ignored new files and external dependencies are outside the inventory |
| Candidate/evidence binding | Pre/post observations, exact response digest, review evidence head and resolved references | Snapshot reads are not atomic locks; change-and-restore between observations can be invisible |
| No duplicate check after uncertainty | Serialized start, one pending check, restart/concurrency controls | The custodian can still act outside R1; no OS enforcement or global exactly-once claim |
| Failure remains distinct | Actual subprocess controls, timeout, source mutation and output-limit checks | Exit status and supplied judgments cannot establish test adequacy or source authenticity |
| No self-certification of independence | Shared-control report; fabricated all-PASS control still grants no approval | Names/controllers and all prose remain supplied; no independent custodian or reviewer is established |
| Historical preservation | Digests for frozen modules/studies and the unchanged older suites | Same-project checks, not external custody |

Bounds: 4,096 source files, 8 MiB per file, 64 MiB total, 64 journal events,
bounded JSON, 1 MiB per output stream for a passing result. The output limit is
checked after process completion; it is not a live disk quota. Check timeouts
apply to the launched process, not a guaranteed kill of every descendant. The
subprocess inherits the host's environment and permissions. Do not give untrusted
candidate tests secrets or production access; R1 itself supplies no sandbox.
Git symlinks, submodules, unmerged entries and unsafe paths are refused. On Windows,
executable mode is taken from Git's index; Unix observations use the file mode.
The journal must be outside the repository or under an ignored path. Parent
paths are resolved before containment checks, including directory aliases; the
journal filename itself remains subject to symlink refusal.

For self-application, run the validator from a separately installed frozen build
and run candidate checks explicitly. That separates source locations; it does not
create independent control or protection from a common OS owner. The operator can
rewrite tools, records, sources and hashes together. External execution remains
disabled; only local journal writes and explicitly requested local test processes
are implemented. Scored-study and production gates remain closed.
