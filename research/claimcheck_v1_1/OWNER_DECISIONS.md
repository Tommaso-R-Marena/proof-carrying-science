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
| C2 | Make the ClaimCheck jobs required | **supported in principle** | `offline-and-kernel`, `meaning-theorems` (and, if PR 216 is admitted, `proofs-and-refinement`) | add them to the ruleset's required checks (a repository setting only the owner can change) |
| C3 | The stand-alone kernel runner accepted forged proof files | 2026-11-16: **authorised for preparation and testing**: replace the runner and the served copy with the tested strict runner; reject the reported forgery before Lean; keep accepting generated files; make the negative controls mandatory tests | done on this branch: `claimcheck_kernel_runner.py` (receipt schema v2) refuses anything but the generator's form before Lean starts; `runner_negative_controls.py`, `tests/test_runner_strict.py`, `check_live_v11.py` (real kernel); README and REPORT corrected; finding `claimcheck_assurance_v1/findings/RUNNER_TAIL_FORGERY.md` (research branch) keeps the vulnerable runner as evidence | owner review of the corrected runner and its tests. Recorded results were not affected |

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
| E2 | Follow-up (proposal) | 2026-11-16: further spending needs separate approval **and** a reliable way to enforce or monitor the budget | restate P1 to P3 with the non-aliasing precondition, drop the encoder; a hard stop would have to be enforced by someone able to cancel, since the prompt cap was not | a budget mechanism, then approve or decline |

## F. Further integration, pilots, release

* 2026-11-16: the three PRs (ClaimCheck core, assurance research, site) stay **separate drafts**
  until the corrected runner and its tests have been reviewed; no merge, no deployment, no change to
  protected admission files, no retained-source tag. Refreshed admission and qualification evidence
  is prepared for the owner's separate review once the runner correction is complete.
* 2026-11-16: next formal target: the canonical claims-part parser and renderer
  (`../claimcheck_assurance_v1/HANDOFF.md`).

* External pilot: only after A to D and after criteria C1 to C9 are met; then the owner's authorisation (C10).
* Deployment of the page: not requested; not before D and C3 are decided.
* Any change to the trusted base (a faster checker path, another Lean version): separate review;
  none is proposed.
