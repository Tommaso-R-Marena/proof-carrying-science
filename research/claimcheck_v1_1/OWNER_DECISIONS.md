# Decisions that are the owner's

Nothing below has been decided, approved or assumed. Each item says what is proposed, where the
exact text is, and what happens on yes or no. Until an item is decided, the related work stays as
it is.

## A. Prospective evaluation (blocks any measurement of v1.1 on new papers)

| # | Decision | Exact material | If approved | If not |
| --- | --- | --- | --- | --- |
| A1 | Approve, amend or reject the protocol | [`prospective/PROTOCOL_DRAFT.md`](prospective/PROTOCOL_DRAFT.md) | it is frozen by digest; software freeze; then the run of its section 6 | nothing prospective is run |
| A2 | Approve, amend or reject the thresholds and the three readiness levels | [`prospective/criteria.json`](prospective/criteria.json) | frozen with A1; never changed afterwards | as A1 |
| A3 | Approve the sampling queries and the three scientific contexts (or add the fourth) | [`prospective/queries.json`](prospective/queries.json) | frozen with A1 | as A1 |
| A4 | Name two independent adjudicators and a third for disagreements, or say that none are available | [`adjudication/INSTRUCTIONS_FOR_ADJUDICATORS.md`](adjudication/INSTRUCTIONS_FOR_ADJUDICATORS.md), package in [`adjudication/v1_discrepancies/package/`](adjudication/v1_discrepancies/package/) | they receive the blinded package; criterion C9 can be met | the evaluation can still run on provisional labels, is reported as not independently adjudicated, and cannot support a pilot |
| A5 | Model access for about 120 proposer calls: free tiers over several days, or a paid tier | protocol section 13 | calls are made once, cached | arms that cannot run are reported as not run |

Points in A1 and A2 that deserve a second look, because I chose them and they are judgement calls:

* the primary arm is the union of both models' proposals;
* 60 papers in three contexts is the smallest sample that can meet the criteria at all;
* coverage floor 25 % (development results were 24 % and 31 %, so this may well fail);
* a criterion that cannot be evaluated counts as not met;
* provisional AI-assisted labels are used to plant errors and as a fallback.

## B. Usability study

| # | Decision | Exact material |
| --- | --- | --- |
| B1 | Whether the study needs ethics review at your institution, and who recruits | [`usability/STUDY_PROTOCOL.md`](usability/STUDY_PROTOCOL.md) |
| B2 | Approve the tasks, the four critical scope questions and their scoring key | [`usability/questions.json`](usability/questions.json), [`usability/tasks.json`](usability/tasks.json) |

No session has been run and none will be simulated.

## C. Source admission and CI in this repository

See [`../../docs/integration/claimcheck/ADMISSION_PROPOSAL.md`](../../docs/integration/claimcheck/ADMISSION_PROPOSAL.md)
for the census of added files and the exact proposed successor steps. In short:

| # | Decision | Owner-held action |
| --- | --- | --- |
| C1 | Admit `research/claimcheck_v1/**`, `research/claimcheck_v1_1/**`, the path-scoped workflow and the admission documents | review; create the retained-source tag at the commit named in the proposal; approve the successor manifest (V23) and the two compiled-in digests |
| C2 | Make the ClaimCheck jobs required | add `offline-and-kernel` and `meaning-theorems` to the branch ruleset's required checks (a repository setting) |

No protected file in this repository has been edited: not the manifest, not `reconcile.py`, not any
existing workflow. `source-policy` and `verified-public-integration` stay red until C1 is decided.

## D. Website (companion PR)

In the site repository, `docs/governance/CLAIMCHECK_PROPOSALS.md`: the reading-help successor
(fresh evidence and manifest are in the branch; the verifier change is a patch, not applied), the
frozen-`public/` rule of the reconciliation gate, and wiring the page's tests into the release gate.

## E. Further integration, pilots, release

* External pilot: only after A to D and after criteria C1 to C9 are met; then your authorisation (C10).
* Deployment of the page: not requested. Not before D is decided.
* Any change to the trusted base (a faster checker path for larger tables, a different Lean
  version): separate review; none is proposed now.
