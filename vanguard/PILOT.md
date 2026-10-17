# First Vanguard integration milestone

Three complete **structural examples** use the same packet contract. They are not
completed independent reviews or scored agent trials. All reviewer identities,
controller declarations and review outputs are fabricated placeholders. No external
action was taken. The retained/closed dispositions are supplied example judgments,
not classifications inferred by software.

| Example | Evidence status | Supplied disposition |
| --- | --- | --- |
| [JPMorgan/Madoff](examples/jpmorgan-madoff-retrospective.json) | Real 2014 FinCEN record; retrospectively authored analysis and placeholder reviews | Retain the narrow historical reporting-control concern |
| [Ignored warning](examples/fictional-failure.json) | Entirely fictional service, warning, log and actors | Retain the fictional concern |
| [Supported decision](examples/fictional-resolved.json) | Entirely fictional documented assessment and correction | Close the fictional concern; no challenge |

## Historical example

The primary record is [FinCEN Matter 2014-1, January 7, 2014](https://www.fincen.gov/system/files/enforcement_action/2020-05-21/JPMorgan_ASSESSMENT_01072014_0.pdf).
Printed page 1 limits the admissions to the civil resolution. Pages 6–7 describe
investment risk reduction, UK reporting and the failure to route relevant concerns
to the U.S. reporting personnel; U.S. SAR filing followed the arrest. The example
preserves the broader hedge-fund risk-reduction explanation rather than attributing
every investment action to knowledge of fraud. It makes no present-day allegation.

The JSON includes short original passages and page locators, one shared origin
group and the retrieved PDF's SHA-256. See the [provenance record](../provenance/vanguard_revision.json).
Whitespace/line wraps are normalized in passages. A hash or three excerpts from
one record are not three independent sources. The actual PDF is not bundled.

The assessment was published years after the conduct. Its cutoff is 2014-01-07
and mode is `RETROSPECTIVE`; relabeling it prospective while retaining that cutoff
fails the chronological gate. It cannot establish an early-warning success.

The draft requests evaluation of routing, receipt, ownership and reasoned
disposition. Its remedy is a proposal for an authorized internal review, not a
claim that the bank currently lacks those controls. It asks for no public release
of confidential customer reports.

## What the exposed controls establish

The 20 fixed controls exercise role coverage, scope/version drift, retained versus
closed concerns, known source echoes, unknown/shared control, ambiguous identity,
uncertain source availability and unresolved material objections. The unit tests
also exercise amendment propagation, CLI exit semantics, strict input handling,
and the OPS1 handoff's digest/case/policy binding and propagation of blockers.

They do not measure substantive source accuracy, causal inference, money-flow
reconciliation, independent review quality, authorization validity, or intervention
outcomes. Neither three narrative examples nor exposed software controls provide
a held-out performance estimate. A separate bounded study must supply genuine
reviewers, independently assessed answers and unknown-to-developer cases before
claims about the fleet's detection or challenge quality are warranted.
