# Usability study: ethics review or determination before recruitment (owner decision B1)

**Status: prepared for the owner. No participant has been recruited, contacted or asked. This note
does not decide whether review is required and does not treat the study as exempt.**

## Why a determination is likely to be needed

The study asks people to perform tasks and answer questions, and records their answers, times,
comments, field and career stage, in order to report the results. That is interaction with people to
produce generalisable findings, which is what most institutional rules and national regulations treat
as research with human participants:

* in the United States, the Common Rule (45 CFR 46) covers research involving information obtained
  through interaction with living individuals. Some minimal-risk studies of this kind fall under an
  exemption category, but at most institutions **the institution, not the investigator, decides that a
  study is exempt**, and a submission is required to obtain that decision;
* in the European Union and the United Kingdom, names, field and career stage are personal data
  under the GDPR or the UK GDPR, so a lawful basis, an information notice and a retention rule are
  needed whatever an ethics committee decides;
* other jurisdictions and most universities have equivalent rules. A study run outside an institution
  can be reviewed by an independent review board.

Calling the study "usability testing" or "product evaluation" does not by itself take it out of
scope where the results are to be reported as evidence (criterion C8 of the pilot criteria).

## What the owner needs to settle

1. Under which institution's rules the study runs, and its review body.
2. Submit for review or for an exemption determination, with the materials below.
3. Data protection: who holds the records, where, for how long, and how participants can withdraw.
4. Whether participants are compensated; how they are recruited without pressure (no students or
   staff supervised by the owner).

## Materials for a submission (prepared, to be adapted to the institution's forms)

| Item | File |
| --- | --- |
| protocol: purpose, participants, session, measures, reporting | `STUDY_PROTOCOL.md` |
| tasks and materials (example data only; participants are told not to upload their own) | `tasks.json` |
| questions and scoring key | `questions.json` |
| risk assessment: minimal risk; no sensitive data; no deception; the tool runs on the participant's machine and sends nothing | this note |
| information sheet and consent, draft | `CONSENT_AND_INFORMATION_DRAFT.md` |
| data management: what is recorded, who holds it, retention, withdrawal | `CONSENT_AND_INFORMATION_DRAFT.md`, section "Your data" |
| recruitment text | to be written with the institution's template |

## One dependency on another decision

Task 3 has participants run the stand-alone kernel runner. The version distributed until 2026-11-16
accepted forged proof files (`research/claimcheck_assurance_v1/findings/RUNNER_TAIL_FORGERY.md`). On
2026-11-16 the owner authorised its replacement for preparation and testing; the replacement (receipt
schema v2) refuses anything but the generator's form before starting Lean. Participants only run it
on files the page generated, so the study was not affected either way; the study uses the strict
runner once the owner has reviewed it.
