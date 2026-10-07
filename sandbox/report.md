CORTAC COMPARATIVE SANDBOX — 7 OCTOBER 2026
Scripted mechanism simulation, not a model-backed agent study

RESULT
The sandbox is implemented and has actually run. It does not establish a collective-intelligence or decentralized-governance advantage. A same-functions centralized controller exactly matches the full arm in every paired environment. The modeled tradeoff is additional checking versus completion, cost and staffing; the result depends on deliberately specified fault assumptions.

WHAT RAN
22,400 deterministic episodes: 2,800 matched environments across 8 policies. Seven hand-designed families cover benign commitments, shared false evidence, conflicted appeal reviewers, reviewer shortage, withdrawn review funding, changed targets, and revoked owner permission. Each family uses 50 paired seeds, budgets of 12 and 30 abstract work units, injected fault rates of 0 and 20%, and either independent or completely shared fault bits. Zero-fault correlation cells are intentionally duplicate controls.

The baseline is competent: it retains provenance checking, current owner permissions, classification, unconflicted review, protected review funding, audit and repair. Full adds four-seat/three-approval decisions and three-seat/two-approval appeal staffing. All arms have identical initial evidence, source rules, owner mandates, ceilings and paired random tapes. Eight arms comprise minimal, full, centralized full, and five single-feature ablations (control exclusion, continuity, classification, audit, one decision seat).

READ THE RESULTS BY CONDITION
1. No faults, ample budget: both policies complete benign commitments. Minimal spends 8 units; full spends 12. For feasible complaint recovery, minimal spends 10 and full 16. These are modeled serial work units, not measured tokens or real agent latency. The first correct commits occur at ticks 7/11 for benign and 9/15 for complaint recovery; audits finish one tick later.

2. Scarcity: at the 12-unit cap, full cannot finish recovery requiring 16 units, while minimal can. This is an arithmetic consequence of the frozen schedule, not a discovered empirical law. At 30 units the feasible zero-fault recovery cases succeed in both arms. A two-reviewer shortage still blocks full's three-seat panel even with 30 units; minimal's one-person review completes. This records a staffing-versus-service tradeoff, without endorsing weaker review.

3. Independent 20% bit faults, benign case, budget 30 (50 pairs): full makes a wrong edit in 1/50 episodes (2%); minimal in 11/50 (22%). After audit, wrong final states are 0/50 versus 1/50. But correct completion is only 37/50 (74%) for full versus 49/50 (98%) for minimal; full abstains in 13/50. This is conditional on the scripted independent-fault model, not evidence of real independent reasoning. Analytically, the prescribed policy makes full wrong effects 3p^3−2p^4 versus minimal p; reduced errors are therefore an expected consequence of the simulator assumptions.

4. Completely shared 20% faults, same case and budget: both policies finish correctly in 38/50 episodes (76%), and both make and retain wrong edits in 12/50 (24%). Extra council seats do not fix a common-mode error. Full still costs 12 units versus minimal 8. A logical separation of functions has not created independent information.

5. Shared false evidence, zero faults: all policies defer the unresolved evidence. Copies from one source do not satisfy independent corroboration. This verifies the shared provenance rule, not superior full-arm cognition.

6. Zero-fault, budget-30 ablations: removing control exclusion uses a conflicted appeal seat while still reaching the correct value; removing protected continuity leaves withdrawn review unavailable; removing classification creates an internal target-envelope violation despite an owner-authorized correct edit. These are direct policy-fixture consequences. They cannot establish the real effectiveness or necessity of a distributed implementation. Minimal retains these safeguards. Removing audit and reducing the council to one decision seat are also fully reported in the raw and stratified outputs.

7. Full and centralized-full are exactly identical across all 2,800 paired environments, including traces, costs and final states. This simulation does not identify an effect of organizational topology. It is a useful negative control against conflating more safeguards with decentralization.

AUTHORITY AND RECOVERY
All unauthorized-effect counts are zero. Revoked-permission episodes terminate during the norms step, so unauthorized attempts are also zero. The main episodes do not exercise a hostile gateway-bypass attempt or a permission race. These zeros are largely structural and cannot validate CORTAC executor security. Internal classification violations are reported separately from owner-permission violations.

Complaint families start with a wrong value, giving every arm the same recovery denominator. Review funding never authorizes an edit: a separately specified live owner remedy grant permits bounded corrections in those cases. Outcomes are judged from state/effects, not actor claims. A correct commit followed by an audit timeout counts both as delivered task and as timeout. Abstention, incomplete review and timeout without a delivered correct edit are not credited as completion. Shared-false and owner-revoked cases are excluded from the useful-completion denominator; their effects remain safety outcomes.

WHAT THE COUNTS DO NOT MEAN
The 22,400 episodes are many executions of seven synthetic templates, not 22,400 independent real-world tasks. Numeric truths and injected errors vary by seed. No p-values or confidence intervals are reported; these cases do not support real-world population-performance claims. Aggregate results are included for completeness but depend on an arbitrary balanced mixture; condition-specific results above are more interpretable.

No language model was called. Accessible tools exposed no callable, metered inference endpoint and no local runner/weights were found in the task workspace. No authorized metered model runner was available for this test. Model calls and model tokens are zero. Measured Python runtime for the complete main run was about 1.13 seconds wall and 1.13 seconds CPU; this is implementation runtime, not agent latency or production compute cost.

SOURCE SCOPE AND OMISSIONS
The pinned source is CORTAC software 0.2.1, commit 20fd02fedf73ebd9b271ce5d13243ccb7de4e14b. This sandbox abstracts its consequential-case council, appeal exclusions, classification and review-continuity mechanisms. A four-seat decision council is distinct from the five separated authority functions. It is not the earlier assembly specification's record-ordering validator quorum, nor a Byzantine consensus implementation. Routine standing-warrant actions need not pay this consequential-case overhead.

No production society runtime, genuine controller independence, cryptographic enforcement, charter ratification, human legitimacy, adversarial strategy, source discovery, concurrency, federation/cell weights, identity discovery, lottery, ordinary role-separated team, long-horizon coordination or social fairness has been validated. Source declarations remain supplied and unverified. The original blocked model-study readiness gates were not altered.

REPRODUCTION AND CHECKS
From the extracted folder, with Python 3.10 or newer and no dependencies:
  python -m unittest -v
  python runner.py --output reproduced

runner.py verifies the frozen hashes before execution. Compare reproduced/raw.jsonl with results/raw.jsonl; deterministic raw output should be byte-identical. runtime.json is intentionally machine-dependent. The source repository's full verification passed 158 tests and 12 stages. This sandbox passed 13 planted controls. The main run passed budget, centralized-equality, no-unauthorized-effect, unresolved-evidence and benign-completion gates. A second replay produced exactly identical raw bytes.

Raw results SHA-256:
7cc2d7c8a4164e080a33957751c63e643b0b21ffe58c25bafc6ea49fde25dd9d

Package contents: frozen protocol and hashes, executable runner, tests, all per-episode traces, stratified JSON/CSV, aggregate JSON/CSV, paired full-minus-minimal outcomes, runtime receipts, source profile/arm definitions and source provenance, and upstream verification output.

NEXT EVIDENCE GATE
Keep the design frozen. A genuine agent-performance comparison remains SOURCE-GATED: it needs an authorized model/version and metered inference runner, common task/permission interfaces, realistic source acquisition, fresh independently designed cases, full prompt/coordination/recovery accounting, and a blinded state-based judge. Evaluate a competent centralized same-safeguard policy alongside minimal and full. Do not use this simulation to promote a claim of real-world safety or collective intelligence.
