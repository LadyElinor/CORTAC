# Vanguard pinned provenance: optional contract v1

This additive, separately versioned inspector compares unchanged Vanguard v1
packets with a separately supplied, digest-pinned inventory and local artifact
bytes. It preserves Vanguard v1, OPS1 v1, software 0.2.2 and profile 0.2. It has
no network, model, authentication, approval, dispatch or external-action API.

## Frozen design and acceptance conditions

Starting revision: `4a83d80c39d20438daedb5fbbce61720a4c921e2`.
The baseline was inspected before implementation. A fresh local run of
`python scripts/verify.py --report .local/baseline-verification.json` passed
**589 tests in 22 stages**. The earlier draft PR reports 582; that historical
count is not substituted for the current local observation.

The following expectations were specified before writing this extension:

| Control | Required outcome |
| --- | --- |
| Unchanged fixture, separate correct pin, matching artifact bytes, in-date inventory | Conditional consistency |
| Joint rewrite of source, caller anchors and role bindings | Reject against the unchanged inventory pin |
| Claim-only rewrite with unchanged sources | Can pass source-only scope; reject with a frozen record/context commitment |
| Changed source digest, version, passage, locator, URL, availability or origin label | Reject against pinned descriptor |
| Inventory and packet rewritten together, external pin held fixed | Reject pin mismatch |
| Missing inventory, pin, artifact bytes or evaluation date | Incomplete, never positive; no fallback to v1 success |
| Altered artifact bytes while declared digest stays unchanged | Reject byte-hash mismatch |
| Expired inventory or source | Incomplete under the separately supplied evaluation date |
| Different bytes derived from one origin, already mislabeled in the pin | Can pass; independence remains unestablished |
| Fabrication already present in a matching pinned inventory | Can pass; truth remains unestablished |
| Vanguard or OPS1 blocker | Propagate; never grant authority or execution |

These are exposed deterministic software controls, not independent evidence,
reviewer authentication, institutional approval or held-out pilot observations.

## Trust boundary

The expected inventory SHA-256 and evaluation date must come from an operator
channel controlled separately from the packet author. The inventory must have
been established using independently acquired evidence and reviewed provenance.
Supplying those arguments separately is an interface boundary, **not proof that
the actors or channels are independent**. A caller who can replace both inventory
and expected digest can still manufacture a consistent result. The API cannot
establish how the pin was obtained, custody, signer identity or genuine freshness.

Never derive the accepted pin from the candidate inventory during operational
inspection. Freeze it before packet submission. Fixture builders do derive pins
from synthetic inputs to exercise code; this is explicitly not trust enrollment.

Source-only pinning protects the exact source descriptors and artifact bytes.
It does not freeze claim text, claim-to-source links, interpretation, disposition,
review prose or the draft. The optional frozen review-input commitment binds the
complete record and context; changed claims or context then require a separately
reviewed replacement inventory/pin. Role outputs themselves are not included in
that commitment and remain unauthenticated. Neither mode establishes that an
excerpt appears in the artifact, that it supports a claim, or that the material
is true. Provenance references are retained strings, not fetched or authenticated.

## Entry points and exit semantics

```sh
python scripts/vanguard_provenance.py packet.json --inventory inventory.json \
  --inventory-sha256 OPERATOR_HELD_CANONICAL_SHA256 --as-of YYYY-MM-DD \
  --artifact-map operator-artifacts.json
python scripts/vanguard_provenance_controls.py
python scripts/verify.py --report .local/verification.json
```

The installed entry point is `python -m wac_offline.vanguard_provenance_v1`.
The existing `wac-offline` and Vanguard v1 CLIs are unchanged. See the fully
[synthetic runnable bundle](../vanguard/provenance_examples/README.md).

| Exit | Status | Interpretation |
| --- | --- | --- |
| 0 | `PINNED_PROVENANCE_CONSISTENT` | All required comparisons match under the supplied pin/date |
| 2 | `REJECTED` | Malformed input, wrong pin, altered binding or wrong artifact bytes |
| 3 | `PINNED_PROVENANCE_INCOMPLETE` | Missing inputs, expired evidence or Vanguard blockers |

Missing inventory, pin, date or artifact bytes cannot inherit Vanguard's positive
v1 status. An absent inventory/map/artifact path is a hold; malformed or unreadable
inputs are rejected. Argument syntax errors use argparse exit 2. Successful or
incomplete reports include the unchanged v1 report, evaluated date, inventory pin,
matched source IDs and verified raw artifact digests. All emitted inspection
reports retain `authority: NONE`, `execution_enabled: false`, unverified control,
and explicit non-authentication/non-adjudication fields. A Python caller must
handle `ReviewError` as rejection, never as permission to bypass the check.

## Closed inventory schema

`INVENTORY` and `ANCHOR` in
[`vanguard_provenance_v1.py`](../package/wac_offline/vanguard_provenance_v1.py)
define the exact schema. Unknown fields, duplicate identities, invalid dates,
noninteger versions, duplicate list items and malformed digests are rejected.
Vanguard's existing bounds apply: 256 list items, 8192-character nonblank text,
canonical dates and at most 1 MiB of canonical JSON per JSON object/file.

| Field | Meaning |
| --- | --- |
| `schema` | `cortac.vanguard.source_inventory.v1` |
| `id`, `version` | Inventory identity and positive version; bound by its external pin |
| `binding` | Exact existing case, policy, packet version and predecessor binding |
| `source_cutoff` | Must equal the unchanged review context's cutoff |
| `established_on`, `valid_until` | Declared inventory validity, inclusive end date |
| `sources` | Exact source ID set; no omissions or additions |
| Each source `id`, `version`, `digest` | Version and canonical digest of the entire Vanguard source descriptor |
| Each source `artifact_digest`, `origin_group`, `available` | Must exactly match that descriptor |
| Each source `provenance_refs` | Nonempty provenance/custody references protected by the inventory pin |
| Each source `valid_until` | Per-source expiration; inclusive and no earlier than availability |
| `review_input_commitment` | Empty for source-only scope, or one object with complete `record_digest` and `context_digest` |

The inventory and descriptor pins use the existing OPS1 canonical digest:
sorted compact ASCII JSON with nonfinite values rejected. They are **not** the
hash of prettified JSON file bytes. Artifact digests are SHA-256 over exact raw
bytes, with no text, newline, encoding or document normalization. Hash equality
assumes SHA-256 collision/second-preimage resistance; it cannot certify origin.

`artifacts` in the Python API maps raw artifact SHA-256 strings to `bytes`.
The CLI's separately supplied operator map maps those digests to local filenames,
resolved relative to the map's directory unless absolute. Packet URLs, locators
and provenance strings are never fetched or interpreted as file paths. Limits
are 16 MiB per unique artifact, 64 MiB total and 256 entries. Missing bytes hold;
wrong bytes, unexpected artifacts and nonregular/oversized files reject. Repeated
excerpts sharing a digest use one artifact. Larger originals require a separately
scoped contract change, not silent truncation or hashing an excerpt in their place.

Inventory establishment must follow the cutoff and all source availability;
review/establishment dates cannot be after `as_of`. Expired sources or inventories
hold. This detects declared version drift and expiration relative to the supplied
clock/pin. It cannot discover unpublished corrections, intervening revocation,
newer inventories or deliberately backdated but internally plausible timestamps.
An old unexpired pin can be replayed: currentness and rollback prevention require
the independent pin registry described below.

## OPS1 compatibility

`inspect_provenance(packet, context, inventory, *, expected_inventory_digest,
as_of, artifacts)` is additive. Missing optional arguments produce holds.
`inspect_pinned_ops_handoff(packet, context, trace, ops_context, link, inventory,
*, expected_inventory_digest, as_of, artifacts)` adds provenance checking to the
existing v1 handoff without changing either v1 contract. It consumes the raw
inputs and recomputes reports, rather than accepting an unbound cached success.

Its separate schema is `cortac.vanguard.provenance_ops_handoff.v1`; status is
`PINNED_HANDOFF_CONSISTENT` or `PINNED_HANDOFF_INCOMPLETE`. Contradictions reject.
Existing Vanguard/OPS1 blockers are preserved, and provenance blockers gain a
`PROVENANCE:` prefix. Existing packet/context/trace/link digest checks remain in
force. Relationship remains `CALLER_ASSERTED_ONLY`. This wrapper creates no OPS1
finding, remedy, authorization, appointment or execution instruction. Applications
that opt into this contract must gate on the **outer** status; an inner v1 success
does not discharge a provenance hold. Existing users remain on v1 unless they opt in.

## Genuine held-out pilot prerequisites

1. Name a responsible human, bounded decision stream, authorized sources, budget,
   correction route and stopping criteria. External action remains outside scope.
2. Have a separate custodian acquire original bytes and provenance records,
   resolve derivation/origin groups, and record unresolved origin uncertainty.
   Verify retrieval/version/availability facts independently of the packet author.
3. Freeze the inventory, pin distribution, expiration policy and evaluation clock
   before submission. Protect replacement and revocation records; prevent rollback
   using an external current-pin registry. This stateless checker has no registry.
4. Verify reviewer identity, control and conflicts independently. A human evidence
   review must assess quotation fidelity, source relevance, competing explanations
   and disposition; passing this code cannot supply those judgments.
5. Preregister outcomes, comparator, error definitions, missing-data handling and
   stopping rules. An independent evaluator must retain unseen cases and answer
   keys until the implementation and predictions are frozen. Exposed fixtures and
   the retrospective example cannot be relabeled as holdouts.
6. Record immutable inputs, pins, code revision, runtime, results and amendments;
   score structural detection separately from factual or governance judgments.

No genuine independent inventory, authenticated reviewers or sealed pilot data
were supplied for this development task. Those gates remain open prerequisites.

## Observed development verification

On October 22, 2026 (America/Indiana/Indianapolis), the local Linux/Python 3.12.14
run passed **620 tests across 23 verification stages**, including 31 new regression
tests and a stage evaluating 23 exposed provenance controls. The prior baseline
passed 589 tests in 22 stages. These counts describe software checks, not agents,
independent reviewers or case-detection performance.

- `python scripts/verify.py --report .local/provenance-verification.json`: passed.
- New Python sources parse using Python 3.10 syntax rules. Other interpreter/OS
  executions require their own CI observations; syntax parsing is not that test.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir .local/wheels .`:
  passed. The wheel installed with `--no-index --no-deps` into a fresh virtual
  environment. From a temporary directory outside the checkout, with `PYTHONPATH`
  removed, the installed provenance CLI, all 23 provenance controls, existing
  Vanguard CLI and existing profile CLI passed; module paths resolved to the
  virtual environment's `site-packages`.
- Existing Vanguard/OPS1 implementations, contracts and regression files remain
  unchanged. The frozen CI workflow and original checksum inventories are also
  unchanged; only reviewed integration paths/new files update the repository index.
- An initial full-suite run rejected an added CI smoke command because the
  workflow is byte-frozen by the OPR preservation tests. That edit was removed;
  no preservation test or baseline checksum was relaxed. Installed-package checks
  were performed separately. The subsequent full suite passed.

The new optional contract has no independent-custody receipt, authentication
claim, genuine held-out result or institutional approval. Its positive guarantees
remain the conditional comparisons described above.
