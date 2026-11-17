# Decisions that are the owner's

Register as of 2026-11-16. The **Owner's decision** columns record what the owner wrote on
2026-11-15 and 2026-11-16; nothing else in this file has been decided, approved or assumed. Each item
says what is proposed, where the exact text is, and what remains to be done. Until an item is
decided, the related work stays as it is.

## A. Prospective evaluation

| # | Question | Owner's decision (2026-11-15) | Current material | What remains |
| --- | --- | --- | --- | --- |
| A1 | Protocol | **amend before approval**; 2026-11-16: **continue preparing** the revised protocol, including the 120-paper design and its statistical and computational costs; do not approve, freeze, sample, inspect or run | [`prospective/PROTOCOL_DRAFT.md`](prospective/PROTOCOL_DRAFT.md) draft 2 with section 10a (120-paper design and its costs) and section 13; every change in [`prospective/AMENDMENTS_DRAFT_2.md`](prospective/AMENDMENTS_DRAFT_2.md) | owner's review of draft 2; approval freezes it by digest |
| A2 | Thresholds and readiness levels | **amend before approval** | [`prospective/criteria.json`](prospective/criteria.json) draft 2 | choose: ICC floor (0.25 proposed), 60 or 120 papers (120 recommended), wording level for detection (empty; 20 % suggested), C2c threshold (50 %) |
| A3 | Sampling queries and contexts | **amend before approval** | [`prospective/queries.json`](prospective/queries.json) (unchanged); screening limit now 300 per context; one paper per author group | approval with A1 |
| A4 | Independent adjudicators | **not yet arranged** | [`adjudication/RECRUITMENT_AND_ADJUDICATION_PLAN.md`](adjudication/RECRUITMENT_AND_ADJUDICATION_PLAN.md); blinded package `adjudication/v1_discrepancies/package/` passes `check_blinding.py` | recruit; optionally send the preliminary package (section 9 of the plan) |
| A5 | Model access and costs | **pending cost and availability review** | [`prospective/MODEL_ACCESS.md`](prospective/MODEL_ACCESS.md): both identifiers listed on 2026-11-15; quotas unverifiable without use; Gemini price not readable from the listing | choose configuration F (free) or P (capped paid, 15 USD proposed); authorise any paid use; confirm or change model identifiers |
| A6 | Decoy rule | 2026-11-16: **retain the existing rule**; correct any wording that presents its local 2 % density as a universal soundness or false-confirmation guarantee; document the scope and assumptions of the proved 2/51 bound, including several supporting reading sets; alternatives may be compared on development data; the frozen prospective evaluation software is not to change without approval | `claimcheck_assurance_v1/formal/ClaimCheckAssurance/Selection.lean`; wording corrected 2026-11-16 in `README.md` rule 6, `policy.py`, the `CONFIRMATION` statement in `verify.py`, `REPORT.md` limitation 4 and the site's `docs/CLAIM_CHECK_V1.md` | nothing required; a comparison of the alternative rules on development data is optional |

Nothing prospective has been sampled, retrieved, inspected, labelled or scored.

## B. Usability study

| # | Question | Owner's decision | Material | What remains |
| --- | --- | --- | --- | --- |
| B1 | Ethics review and recruitment | **prepare, do not recruit yet** | [`usability/ETHICS_DETERMINATION.md`](usability/ETHICS_DETERMINATION.md), [`usability/CONSENT_AND_INFORMATION_DRAFT.md`](usability/CONSENT_AND_INFORMATION_DRAFT.md) | obtain the institution's determination before any recruitment; the study is not treated as exempt |
| B2 | Tasks, scope questions, scoring | **prepare** | [`usability/STUDY_PROTOCOL.md`](usability/STUDY_PROTOCOL.md), `tasks.json`, `questions.json` (scoring key) | approval with B1 |

No session has been run and none will be simulated.

## C. Source admission and CI in this repository

| # | Question | Owner's decision | Material | What remains (owner-held) |
| --- | --- | --- | --- | --- |
| C1 | Admit `research/claimcheck_v1/**`, `research/claimcheck_v1_1/**`, the workflow and the admission documents | **supported in principle, not yet approved** | [`../../docs/integration/claimcheck/ADMISSION_PROPOSAL.md`](../../docs/integration/claimcheck/ADMISSION_PROPOSAL.md), the census, the dry run, the patch; audit [`../../docs/integration/claimcheck/ADMISSION_AUDIT.md`](../../docs/integration/claimcheck/ADMISSION_AUDIT.md) | review; fix the admitted commit; create and push the retained-source tag; approve the successor manifest and control changes |
| C2 | Make the ClaimCheck jobs required | **supported in principle**; 2026-11-17: recommendation revised | the workflow was path-filtered, so its jobs could not be required without leaving unrelated pull requests pending; it now runs on every pull request with an always-reporting aggregate `claimcheck-required` (`99637e67`, tested by `governance/test_required_check.py`); [`../../docs/integration/claimcheck/REQUIRED_CHECKS.md`](../../docs/integration/claimcheck/REQUIRED_CHECKS.md) also flags six core jobs that are skipped (= passing) on every pull request | after C1, require only `claimcheck-required`; confirm none of the always-skipped jobs is required |
| C3 | The stand-alone kernel runner accepted forged proof files | 2026-11-16: **authorised for preparation and testing**: replace the runner and the served copy with the tested strict runner; reject the reported forgery before Lean; keep accepting generated files; make the negative controls mandatory tests | done on this branch (`d5a36975`, `2de4f872`, canonical grammar `39ce953c`): `claimcheck_kernel_runner.py` (receipt schema v2) refuses anything but the generator's form, one spelling per value, before Lean starts; `runner_negative_controls.py`, `tests/test_runner_strict.py`, `check_live_v11.py` (real kernel); README and REPORT corrected; finding `claimcheck_assurance_v1/findings/RUNNER_TAIL_FORGERY.md` (research branch) keeps the vulnerable runner as evidence | owner review of the corrected runner and its tests. Recorded results were not affected. 2026-11-17: an independent security review found no bypass of the grammar and seven issues around it; the runner fixes are in `52b5e182` (receipt lists each claim's settings and flags those the page never writes; safe `lean` lookup; fail-closed; ASCII output; memory cap option), runner SHA-256 `831bbaba…`: [`../../docs/integration/claimcheck/SECURITY_REVIEW_C3_D4.md`](../../docs/integration/claimcheck/SECURITY_REVIEW_C3_D4.md) |
| C4 | The v1.1 replay did not bind the claim to the sentence (found 2026-11-17) | **fixed on this branch for review** (`1d2f80ef`): reported value must be the printed literal; variants those the statistic requires; frozen v1 replayer unchanged | `tests/test_binding_offline.py`; 0 violations on the 302 committed receipts | review; revert if rejected |

No protected file has been edited: not the manifest, not `reconcile.py`, not any existing workflow.

## D. Website (companion PR)

| # | Protected file | Owner's decision | Material | What remains |
| --- | --- | --- | --- | --- |
| D1 | `scripts/verify_browser_ui_sources.mjs` | **supported in principle, not yet approved** | site `docs/governance/CLAIMCHECK_PROPOSALS.md`, patch 01 and dry run | approve patch 01 |
| D2 | `scripts/check_reconciled_prs.py` | **supported in principle, not yet approved** | patch 02, dry run, census | approve patch 02; create the retained commit and push its tag |
| D3 | `package.json` (`ci:zero-minutes`) | **supported in principle, not yet approved** | patch 03 and dry run | approve patch 03; optionally require `claim-check-page` |
| D4 | The page served the affected runner | 2026-11-16: authorised with C3 | site branch, companion commit: served copy and pinned digest replaced from this runner; the page accepts only v2 receipts and says what a kernel run does and does not establish | owner review; no deployment |

## E. External verification service (Aristotle)

| # | Question | Owner's decision | Facts | What remains |
| --- | --- | --- | --- | --- |
| E1 | Feasibility experiment, up to 50 credits | **authorised (cumulative)**; 2026-11-16: the run exceeded the allowance; **no further run** | one run: **92 credits billed**, the allowance exceeded by about 42 promotional credits; no paid charge; balance 408, expiring 2026-11-29 ([`../claimcheck_assurance_v1/c/ARISTOTLE_RESULTS.md`](../claimcheck_assurance_v1/c/ARISTOTLE_RESULTS.md)). Reported properties, unresolved obligations and the counterexample are kept; no C proof artifact was returned, so none is claimed to be replayable | nothing |
| E2 | Follow-up | 2026-11-17: up to 100 promotional credits authorised **only** with a genuine, enforceable limit; **not started**: the tools offer no per-run budget and cancellation depends on a session that usage limits suspended during the first run and twice since | decoder redesigned so the aliasing hazard cannot be expressed (`c/DESIGN_DECODER_V2.md`); continuation prepared (`c/ARISTOTLE_PROMPT_V2.md`, upload digests); balance 407.8, 0 paid, expiring 2026-11-29 | configure a credit check-in in the Aristotle web app, submit from the web app, or accept supervised cancellation; then send the prepared continuation |

## F. Further integration, pilots, release

* 2026-11-16: the three PRs (ClaimCheck core, assurance research, site) stay **separate drafts**
  until the corrected runner and its tests have been reviewed; no merge, no deployment, no change to
  protected admission files, no retained-source tag. Refreshed admission and qualification evidence
  is prepared for the owner's separate review once the runner correction is complete.
* 2026-11-16: next formal target: the canonical claims-part parser and renderer
  (`../claimcheck_assurance_v1/HANDOFF.md`). Done on the research branch: `Claims.lean` (round trip,
  canonicity, injectivity, one meaning one text, batch iff claims; kernel-checked) and a conformance
  test of the runner's parser against it (7,248 inputs, no disagreement; a test, not a proof).

## G. Refreshed evidence for the owner's separate review (2026-11-16)

Nothing here is approved, applied or tagged.

| For | Refreshed at | What | Result |
| --- | --- | --- | --- |
| C1 core admission | `39ce953c` | census `../../docs/integration/claimcheck/ADMISSION_CENSUS.json`; dry run `dry-run.json`; patch; audit `ADMISSION_AUDIT.md/.json` | 1,982 added files, none existing changed; gate with the successor passes on 10,025 files and 72 PRs; five negative controls rejected; audit all clear (no credential, no generated file, modes 100644, licences in order, frozen digests verify, protected paths unchanged). Valid only for that commit; to be regenerated at the commit the owner fixes |
| D1-D3 site gates | site `5538f1b` | site `docs/governance/claimcheck-proposals/`: census (42 files: 36 added, 6 modified) and dry runs of patches 01, 02, 03, all reproducible by script | all as expected: 01 patched verifier accepts, 22 tests pass, 5 alterations rejected; 02 successor passes, 6 controls rejected; 03 complete gate runs 11 claim-check tests, 8 alterations rejected (incl. a non-strict served runner and a v1 receipt shown again) |
| reading-help re-qualification | site branch head | all-pages browser run repeated on the changed page | byte-identical to the recorded evidence (`all-pages-browser.json`, sha256 `e161824d…`); the successor check passes |

* External pilot: only after A to D and after criteria C1 to C9 are met; then the owner's authorisation (C10).
* Deployment of the page: not requested; not before D and C3 are decided.
* Any change to the trusted base (a faster checker path, another Lean version): separate review;
  none is proposed.

The complete package of decisions, each with its exact change, tests, implications and the
consequences of approval or rejection: [`../../docs/integration/claimcheck/OWNER_AUTHORIZATION.md`](../../docs/integration/claimcheck/OWNER_AUTHORIZATION.md).
The prospective decisions (A1-A5) with recommendations: [`prospective/DECISION_PACKAGE.md`](prospective/DECISION_PACKAGE.md).
