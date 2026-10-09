# Bounded complaint triage: opt-in implementation contract

This optional, separately versioned synthetic extension is a local implementation
rule, not an adopted charter amendment or a full Commonwealth appeals service.
The original scratch runner, eight scenarios and sixteen episodes stay unchanged.
The existing software and frozen profile versions stay 0.2.2 and 0.2 respectively.

## Contract fixed before implementation

- Every admitted complaint retains immutable evidence, its own hold, and explicit
  appeal/review state. Duplicate links preserve each record; they are not dismissal.
- A batch repair must carry independent review of every current open hold, bound
  to the exact complaints and proposed effect. Resolving a batch never resolves
  a later complaint or a later version of an appeal.
- Unknown claimant control routes to fact-finding. A missing or inconclusive
  finding leaves the complaint visibly unresolved. Constructor-pinned evidence
  can supply a declared controller, but cannot authenticate anyone or establish
  the truth of an allegation. Controller exclusions are not relaxed.
- Investigation, review and audit require exact bounded constructor-pinned grants.
  Holding a new role does not let an actor grant itself powers. Existing proposal,
  evidence, mandate, independent checks and post-effect audit safeguards remain.
- Finite review/fact-finding reserves belong to constructor-known complaint slots;
  audit reserves belong to constructor-known work items. Ordinary operations and
  repair use separate resources. No borrowing from a protected allocation is
  permitted. A funded audit does not imply a funded or authorized correction.
- Exhaustion means incomplete, retaining unresolved holds and any committed
  effect requiring audit. Rejected attempts are observable and cannot erase
  complaints or turn incomplete work into success.
- Fair allocation is only isolation of reservations among the finite known slots.
  Duplicate labels cannot spend another slot's reservation. This is not Sybil
  resistance, authentication, universal admission, or fairness against unbounded
  unauthenticated outsiders. Admission and each allocation are explicit bounds.
- Revocation, stale authority, replay, later complaints and concurrent operations
  follow a single live gateway's serialized SQLite transaction ordering. Partial
  effects remain auditable. No multi-process persistence or host-resistant boundary
  is claimed.

## Predetermined controls

The new controls must distinguish: overlapping complaints; unknown controller and
inconclusive or conflicted fact-finding; ordinary budget empty with protected
reserve available; protected reserve empty; separate repair budget empty;
duplicate submissions; later complaints; stale/revoked grants; replay; concurrent
commit/revocation; storage rollback; and copy isolation. A single audited repair
may be complete while the overall case still has a separate unresolved complaint.

Structural record validity, resolution of pinned evidence bytes, authorization
within the harness, and the semantic truth of supplied claims are separate tests.
The first three never establish the fourth. All authority remains NONE, controller
closure SUPPLIED_UNVERIFIED, and external execution disabled. There are zero model
calls and zero authenticated external principals. The only effects are actual
mutations of a newly created, automatically cleaned-up SQLite scratch document.

## Compatibility and reproducibility

The legacy compatibility test pins the entire canonical sixteen-episode report,
including inputs, state, evidence, journal and operation counts, to published base
0ad0b4b5fa0242a8cbcafd7afc03ac0922e564a7. Only the pre-existing machine-dependent
CPU and wall durations are excluded from that canonical digest. Legacy source
and historical artifact bytes are separately compared with the base.

See the final delivery report for observed tests, installed-wheel and extracted
archive verification, independent review, and remaining limitations. A passing
local check is not a real-world institutional outcome or a remote CI result.

The aggregate verifier also replays the historical 22,400-episode scripted sandbox
and compares its six deterministic outputs with the frozen hashes. This is a
software reproducibility check, not a new agent experiment. The historical stored
artifacts and their interpretation remain unchanged.

## Python interface and closed inputs

`wac_offline.triage.TriageGateway` is opt-in. Construction accepts the legacy
`policy`, `evidence`, and `mandates`, plus keyword-only `triage_config` and `grants`.
The legacy `ScratchGateway` and its callers do not opt in automatically.

The v1 configuration pins the complete evidence inventory digest, separate
`ordinary_budget` and `repair_budget`, complaint slots, and work items. Each slot
pins ID, claimant label, challenged work item, original evidence/reason, optional
original complaint linkage, finite appeal statements, and fact-finding/review
caps. Each work item pins the proposal digest, revision, operation, mandate,
executor, exact complaint list, and its audit cap. Each complaint also has a protected intake allocation of one lodgement plus
one operation per pinned appeal. The sum of all allocated caps, including these
derived intake caps, must fit inside the policy's operation ceiling. Duplicate slots receive no new
fact-finding/review allocation and share only their constructor-pinned original
complaint account; they cannot redirect charges to another complaint.

`make_grant(...)` is only a record constructor. A grant becomes usable only if its
exact bytes were supplied when the gateway was constructed. It binds policy,
configuration, epoch, expected revision, exclusive logical expiry, action, actor,
authorizer, complaint versions, work item/proposal where applicable, and a pinned
finding where applicable. Grants are single-use; review authorization is rechecked
at repair commit. An emitted receipt never substitutes for a grant.

Public operations are `lodge`, `appeal`, `factfind`, `review`, `commit`, `audit`,
`revoke_grant`, inherited exact-mandate `revoke`, `issue`, and `snapshot`. The
original `challenge` spelling routes to bounded `lodge`, so it does not bypass
slot admission. `review` accepts a canonical sorted list of complaint IDs;
`commit` additionally requires its pinned work-item ID; `audit` additionally
requires its pinned grant ID. Use the context manager to close SQLite before
removing its automatically created temporary directory.

Appeal statements and capacity are constructor-known. An appeal appends evidence
and history, increments that complaint's version, and preserves/reopens its hold.
An audit of an older version can audit the actual scratch effect but cannot close
the newer appeal. Resolution of every initial complaint does not prevent a later
predeclared complaint from retaining its own hold. This is a bounded state machine,
not an independent multi-person adjudication institution or an unlimited appeal
right.

## Resource requirements and exhaustion

A fresh correction needs separate repair capacity for at least one assessment,
`approval_threshold` approvals, one authorization receipt, and one commit:
`approval_threshold + 3` admitted repair operations (four for the one-approver
fixture, six for the three-approver fixture). Admitted rejected attempts consume their selected capacity
and can raise this requirement. Invalid grant/scope routing is rejected against
ordinary capacity, never the requested protected allocation. Review additionally costs one protected review
unit per distinct constructor-pinned original complaint account in the batch;
duplicate aliases in the same batch do not create more units. Each fact-finding
attempt uses that complaint account's separate fact-finding capacity. A final
effect audit needs one unit in that work item's own audit allocation and a valid
independent audit grant. Funds alone never replace the required authorities,
evidence, current revision, independent roles, or absence of an unaudited effect.

An exhausted ordinary account must not consume any of these protected units.
Conversely a funded audit cannot finance the assessment/approval/authorization/
commit pipeline. The logical transaction tick and per-partition charged work
units are distinct: a batch review is one serialized transaction but may charge
several complaint accounts. These counters are neither money nor CPU/time/token
meters. Exhaustion is explicit in the observable incomplete/journal records;
records of failed attempts do not create capacity or dismiss a complaint.

The complete proposed protected transition is validated against a private state
copy at the next logical tick before protected resources are debited. The same
lock covers validation and the actual SQLite transaction. Forged, stale, replayed
or wrong-scope requests therefore cannot spend another slot's protected capacity.
Invalid requests are metered against ordinary work instead. This also protects
known complaint intake before any complaint has been lodged: duplicate floods
cannot consume another slot's lodgement or appeal allocation. At most one
persisted exhaustion marker per finite pool is added, avoiding unlimited journal
growth from repeated over-cap attempts. A known unresolved hold can still block
a batch correction; isolated allocation is not a promise of successful resolution.

Accepted grant revocation blocks future use, including reuse of an issued review
at repair commit. It does not retroactively remove an accepted finding, undo a
committed scratch effect, erase a pending audit, or reverse an audited resolution.
Any later correction still needs its own current pinned work item and authority.
A finding is a supplied outcome bound to its own control-evidence references;
those references need not be the complaint's allegation-evidence references.
