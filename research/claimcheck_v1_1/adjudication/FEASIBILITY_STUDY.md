# Human-adjudication feasibility study: prepared, not conducted

**Status (2026-11-19).** Prepared only. Nobody has been contacted or recruited, no package has been
sent, and no human judgement exists. What the study would produce are development-set findings:
they enter no criterion, and protocol draft 3 stays unapproved. Running any step below needs the
owner's authorisations listed in "Before anything is sent".

The study is parts A and B of the feasibility study in
[`../prospective/DECISION_PACKAGE.md`](../prospective/DECISION_PACKAGE.md), section 14. Part C, the
kernel resource profile, was run on 2026-11-19 (section 16 of the package). This file turns parts A
and B into steps.

## What it measures, and the decisions it informs

| Quantity | Why it matters | Go / no-go rule (package, section 14) |
| --- | --- | --- |
| minutes per paper per adjudicator, on the full-protocol package | sets 60 versus 120 papers and the number of adjudicators | median ≤ 60 min: 120 papers; 60 to 90: 120 only with six adjudicators; > 90: 60 papers |
| agreement on the class T / F / N / A (raw, and Cohen's κ) | whether the labels can carry C1 to C3 | κ ≥ 0.6 and A share ≤ 10 %; **stop** if A > 20 % or κ < 0.4 |
| A share (ambiguous numbers) | the protocol allows at most 20 % | as above |
| disagreement share and resolver minutes | the resolver's budget | reported |
| problems with the instructions or the sheet | revise before the prospective run | reported |
| ICC of coverage and of planted-error detection (part B) | checks the ICC floor of 0.25 | reported beside the floor |

## What already exists

* **Round 1 package**, `v1_discrepancies/package/`: 3 papers and 30 numbers, of which 6 are of
  interest (the apparent v1 discrepancies and related numbers) and 24 are controls, in a seeded
  random order. It holds no system output.
  * Built by `python -m research.claimcheck_v1_1.adjudication.build_package v1-discrepancies --out <dir>`.
  * Checked by `python -m research.claimcheck_v1_1.adjudication.check_blinding <dir>/package`.
  * The key is in `v1_discrepancies/KEY_DO_NOT_SEND/` and is never sent.
* **Instructions:** [`INSTRUCTIONS_FOR_ADJUDICATORS.md`](INSTRUCTIONS_FOR_ADJUDICATORS.md).
* **Roles, qualifications, independence, workload, blinding, records:**
  [`RECRUITMENT_AND_ADJUDICATION_PLAN.md`](RECRUITMENT_AND_ADJUDICATION_PLAN.md), sections 1 to 8.
  Section 9 proposes round 1 as a pilot of the procedure.
* **Analysis:** [`agreement.py`](agreement.py) computes the quantities above from returned sheets and
  time logs. Its test uses synthetic sheets only.

## Not built yet (needs no people)

* **Round 2 package:** the full-protocol package on the six held-out v1 papers. The planted-error
  copies are not adjudicated; their labels are carried over (protocol 7). `build_package.py`
  builds only round 1 today. A `heldout-full` mode is needed, and `check_blinding.py` must pass on
  its output. It should be built after round 1, so that the instructions can first be revised.

## Before anything is sent (owner decisions)

1. **Ethics.** Decide, with your institution, whether the adjudication pilot needs a determination
   (records and data handling: plan, section 8). The usability study has its own determination
   (`../usability/ETHICS_DETERMINATION.md`); it does not cover adjudicators.
2. **Recruitment:** two adjudicators and a resolver (plan, section 10), each with the written
   independence confirmation of plan section 3.
3. **Time:** 12 to 19 person-hours in all: 5.5 to 8.75 h per adjudicator and 1.1 to 1.9 h for the
   resolver (package, section 14).

## Procedure (once authorised)

1. Send each adjudicator only the `package/` directory of round 1, the instructions and the
   independence form.
2. Adjudicators work alone. For each paper they fill `sheet.csv` (the class and the fields beside
   it) and keep a time log, `time_log.csv`, with the columns `paper,minutes_reading,minutes_classifying,notes`.
3. Compute with `agreement.py`: raw agreement and κ on the class, the A share, the disagreements
   for the resolver, and minutes per paper.
4. The resolver settles the disagreements and records minutes per item.
5. Revise the instructions if needed. Build round 2, and repeat steps 1 to 4 on it.
6. Report the results apart from any prospective result, against the rules in the table above.

## Limits

* Round 1's 30 numbers test the procedure; κ on 30 numbers has a wide interval. Estimates for the
  go / no-go rules come from round 2.
* The papers are development material (they were read while v1.1 was designed). Their adjudication
  says nothing about prospective performance.
* The AI-assisted labels in the key are not human judgements and are not used to score the
  adjudicators.
