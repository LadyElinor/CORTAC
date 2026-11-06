# S1: a proposal-only agent lifecycle for CORTAC

S1 (`cortac.agent-scaffold.v1`) adapts CORTAC into a usable **single-assignment
lifecycle scaffold**. An independently written process consumes a credential-free
AP1.1 brief and returns one JSON decision. A trusted custodian records the result,
stages an immutable proposal through the optional C2 client, explicitly submits
or reconciles it, and retains an advisory CORTAC review. Host authority is always
`NOT_OBSERVED`: neither the transport nor this review can approve or execute work.

This is local research software. The existing CORTAC software/profile versions,
frozen solvers, scratch runner, study fixtures and historical results are unchanged.
The [design](AGENT_SCAFFOLD_V1_DESIGN.md) was committed before implementation.
The implementation was developed by the same operator; the second accounting
implementation is not independent institutional review.

## The three machines

| Machine | Contract |
| --- | --- |
| Decision | One assignment, one started attempt. A valid propose/decline/wait/request-evidence, invalid response, timeout, crash, or interrupted/pending attempt remain distinct. |
| Transport | One immutable outbox binding. Stage begins unresolved. Explicit submit uses the same bytes, endpoint, capability and ID. C2 lookup alone cannot finish recovery. Recorded can mean refusal. |
| Authority | No host approval or execution endpoint. The host retains its existing gates. A supplied CORTAC review is linked advice, not a host event, mandate or warrant. |

Local SQLite events are hash-linked and replayed before reporting or appending.
There is no mutable snapshot. Each external client operation is preceded by a
committed local start. Journaling and C2 storage are separate transactions; a crash
between them remains visible and is reconciled against the original outbox.
S1 never writes the workshop DB. Local host receipts remain nested observations,
not signatures or evidence of a currently valid permission.

## Use the file-based interface

After installing this repository, run `python -m wac_offline.scaffold_v1 --help`.
From a checkout, prefix the commands with `PYTHONPATH=package` on POSIX, or set
the equivalent environment variable on Windows. An operator supplies a B1.1 task
JSON obtained through its existing interface and an assignment file:

```json
{
  "assignment": {
    "id": "review-001",
    "agent": "proposer-a",
    "implementation": "constant-quality-stream-v1",
    "controller": "declared-a",
    "reviewer": "reviewer-b",
    "reviewer_controller": "declared-b"
  },
  "protected_limits": [
    {"id": "independent-review", "commitment": "Preserve independent review."}
  ]
}
```

These names are operator-supplied declarations, not authenticated identities.
The agent and assigned reviewer must have different IDs and declared controllers.
This does not discover shared ownership or demonstrate actual independence.

```sh
python -m wac_offline.scaffold_v1 new session.sqlite task.json assignment.json
python -m wac_offline.scaffold_v1 begin session.sqlite > brief.json
python -m wac_offline.scaffold_v1.agent < brief.json > decision.json
python -m wac_offline.scaffold_v1 decision session.sqlite --response decision.json --elapsed-ns 0
python -m wac_offline.scaffold_v1 report session.sqlite
```

Replace the example agent command with a separately operated program. S1 does not
launch arbitrary commands, enforce their OS access policy, or time them itself.
`--elapsed-ns` is the custodian's observation; zero in this example is a placeholder,
not a latency result. `--outcome TIMEOUT` or `--outcome CRASH` records a custodian
observation instead of a response. A started attempt with no finish is retained
as interrupted/pending. Invalid responses retain only a byte digest, never their
raw potentially secret content. Invalid classification and reported runtime
outcomes are not independently reproduced from that digest.

The included agent always proposes `quality-stream` when available; it is a
conformance policy with uncalibrated forecasts, not an efficacy result. A declared
implementation name is not verified against its response. The agent module needs
only the brief; give it no session DB, credential file, host tools or network
submission access. Separate OS controls are an operator prerequisite, not provided
or tested by S1. Same-user processes can bypass these conventions.

## Optional C2 submission

Build/install the separately reviewed `unfinished-commonwealth-client` 2.0.0 wheel
from Commonwealth commit `3688dcdfa70b27531c8f0d3bd315a88736c87655`, following its C2
packaging instructions. S1 does not download it or import the full workshop.
The pinned [source record](../provenance/scaffold_sources.json) lists exact hashes
and attribution for the AP1 port and tested C2 files. C2 is not bundled. Its private
`Outbox._read` API is pinned deliberately to compare exact retained intent bytes;
an upgrade requires a new compatibility review. Version text alone is not source
attestation. AP1's Assembly role and optional Assembly checkpoint are not supported.

```sh
python -m wac_offline.scaffold_v1 stage session.sqlite intent.sqlite http://127.0.0.1:PORT credential.txt
python -m wac_offline.scaffold_v1 submit session.sqlite credential.txt
python -m wac_offline.scaffold_v1 resolve session.sqlite credential.txt
python -m wac_offline.scaffold_v1 report session.sqlite
```

Use the actual supplied port. Stage performs no network call and deliberately
reports unresolved (exit 3). Resolve is one lookup, not a hidden second POST. If
needed, explicit `submit` reconciles using the retained bytes. Expired or revoked
credentials cannot be renewed through S1. A fresh task after a definitive stale
refusal requires a new assignment; an unresolved old intent must not be bypassed.

If a local operation start lacks its finish, `recover session.sqlite credential.txt`
reads and validates the original C2 outbox locally, with no network. The interrupted
duration is unknown. A matching outbox may be adopted only for the already retained
binding. A missing/corrupt outbox, even after an interrupted stage, stays unresolved
and requires operator inspection. No new ID, token, file or request is invented.
`inspect` records a fresh local C2 observation when no operation is pending.

CLI exit 0 means a local report/disposition, including declines and recorded host
refusals; 3 means transport remains unresolved; 2 means refused or uncertain work
needs inspection. None means authority, correct output or production readiness.
Bearer-shaped strings are rejected in retained JSON, but this is not a general
secret scrubber. Protect both local databases and their parent directories.

After acceptance, optional `review session.sqlite reviewer-b review.json` accepts
the existing `cortac.decision.record.v1` contract with the exact configured limit
inventory. Dissent remains intact. FAIL/UNKNOWN remain visible; PASS is only the
supplied assessment. No review changes a host proposal, resets costs or grants
authority. S1 does not synthesize missing evidence, representation or mandates.

## Guarantee, check, counterexample, remaining assumption

| Guarantee | Check | Counterexample / positive case | Remaining assumption |
| --- | --- | --- | --- |
| Bounded credential-free exchange | AP1.1 projection, closed decision schema, duplicate-key/depth/size/numeric checks | Hidden task fields omitted; wrong brief/extra actions/credential strings refused | Prose can leak data; OS access and provider behavior are outside S1 |
| One accountable decision attempt | Replay of start/finish and seven distinct dispositions | Duplicate decision refused; unfinished attempt survives restart | Caller supplies timeout/crash and elapsed time; policy code is not attested |
| Intent immutability | Exact request bytes, instance, ID, endpoint and credential digest | Consistent but different C2 outbox refused before sending | Custodian/filesystem remain trusted; path races against owner not prevented |
| Uncertain effects stay uncertain | Committed operation starts, explicit C2 recovery | Lost response → lookup still unresolved → exact retry, one proposal | C2 and trusted host deduplication; no global exactly-once guarantee |
| No authority promotion | Proposal-only bridge, receipt checks, separate advisory record | Execution events and authority-claiming receipts refused; review leaves host authority unobserved | A forged consistent receipt can still be supplied by a trusted-host attacker |
| Review is attributed and scoped | Assigned reviewer, declared-controller separation, exact limit inventory, decision digest | Wrong reviewer refused; FAIL/UNKNOWN and dissent preserved | Names, controller relations, evidence and judgment are supplied/unverified |
| Persistent accounting | Full lifecycle replay; separate chain/count implementation in `audit.py` | Altered journal/report counters refused, including repaired-hash semantic test | Auditor checks chain/counts only, not every transition, policy, source or host event |
| Costs not conflated | Decision/runtime observations, transport starts/finishes, unknown durations | Interrupted call not treated as zero elapsed; stage does not consume host attempt | No shared scheduler, synthetic slot charge, token or financial measurement |
| Historical compatibility | 120 baseline file digests plus original suites | Historical hashes and sandbox replay | Same-project check, not external custody or sealed evaluation |

Runtime boundary: one assignment/current workshop worker, maximum 128 local events,
bounded JSON, literal loopback transport. N credentials do not create N independent
workers, seats or votes. Multi-agent admission, shared scheduling, prospective
evaluation and independent evidence custody require separate designs. Adversarial
G2/E1 resource-denial mechanisms are not operational powers in S1. No CORTAC
assignment witness is converted into a Commonwealth credential or approval.

## Reproduce

```sh
python scripts/verify.py
PYTHONPATH=package python -m wac_offline.scaffold_v1.demo
# Requires the pinned clean checkout and separately installed exact C2 client:
python scripts/scaffold_commonwealth_integration.py /path/to/unfinished-commonwealth
```

The explicit integration checks AP1 port equality against the pinned source and
seven actual loopback cases: acceptance, lost reply, interruption after C2 stage,
interruption after C2 submit, stale head, expired capability, and conflicting
outbox. Interrupted stages use injected exceptions and fresh object instances,
not power-loss experiments. Accepted recovery cases retain one server attempt
and one proposal event. Expiry and conflicting intent remain unresolved without
submitting a proposal. The new hosted workflow repeats this on its exact checkout;
only a completed run is CI evidence. Zero model calls or scored trials occur.
