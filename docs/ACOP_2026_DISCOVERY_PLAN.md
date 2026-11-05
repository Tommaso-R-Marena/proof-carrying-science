# ACoP 2026 Design-Partner Discovery Plan

**Event:** American Conference on Pharmacometrics (ACoP 2026 / ICoP-US)  
**Dates:** October 11–14, 2026, with vendor workshops beginning October 10  
**Location:** Gaylord National Resort & Convention Center, Oxon Hill / National Harbor, Maryland  
**PCS objective:** problem discovery and design-partner recruitment, not a public product launch.

Official program: https://acop2026.eventscribe.net/

## Why this is the highest-priority near-term channel

The program directly overlaps the first PCS wedge:

- model-informed drug development and ICH M15;
- PK/PD, PBPK, QSP, NONMEM, Monolix, Pumas, and quantitative clinical pharmacology;
- AI/agentic modeling workflows;
- auditable guardrails, provenance, reproducibility, governance, and human review;
- programming/QSP/clinical-pharmacology SIG communities;
- pharma, biotech, consultancies, software vendors, academics, and FDA in one venue.

The first goal is **not** to convince people that formal verification is important. The goal is to learn which computational assurance failures already cost them time, review burden, or confidence.

## Success metrics for the conference

Minimum useful outcome:

- 15 substantive problem interviews;
- 5 people willing to see a 5-minute PCS demo;
- 3 people willing to continue a technical conversation after the conference;
- 1–3 organizations willing to provide a bounded synthetic/de-identified workflow or specification;
- one repeated assurance pain point that appears across multiple organizations.

Do not measure success by cards collected or compliments.

## Highest-priority conversations

### 1. Pharmacometrics consultancies / CRO modeling groups

Potentially the best early design-partner class because they repeatedly hand scientific analyses to clients and may benefit from stronger reproducibility, review, and evidence handoff.

Listen for model QC/reviewer burden, code review and validation, repeatability across client environments, handoff/documentation pain, regulatory package preparation, and discrepancies between model specification and executable implementation.

### 2. Scientific-software vendors

Examples present in the ACoP ecosystem include Certara, Simulations Plus, ICON/NONMEM, PumasAI, InsightRX and other modeling platforms.

Treat these first as **technical discovery / future integration conversations**, not necessarily the easiest first paying customers. Ask where users still need manual assurance around their platforms and which evidence they can already export.

### 3. Pharma / biotech modeling teams

Program participants include major pharmacometrics/QSP organizations across companies such as J&J, AstraZeneca, Pfizer, Sanofi, Lilly, Gilead, BMS, Genentech, Amgen and Regeneron.

These are excellent problem-validation conversations, but procurement can make them slower first customers. Ask for a syntheticized technical follow-up rather than immediately proposing enterprise procurement.

### 4. FDA / academic / standards-oriented scientists

These are **not sales targets** at the conference. Use them to test terminology, the verification-versus-validation boundary, evidence/documentation gaps, misleading claims, and what would make an assurance artifact credible to an independent reviewer.

## Sessions to prioritize

- **Oct. 12, 11:00–12:30 — GenAI in QSP: Agentic Orchestration, Auditable Guardrails and Adaptive Calibration.** Strongest direct overlap with PCS trust/provenance philosophy.
- **Oct. 12, 14:00–15:30 — Choosing the Right Modeling Path within Current Regulatory Frameworks.** Includes ICH M15/MIDD discussion and multiple pharma participants.
- **Oct. 13, 12:30–14:00 — Programming, QSP, and Clinical Pharm SIG lunches.** High-density discovery setting.
- **Oct. 14, 10:30–12:00 — Generative AI tools and agents in Pharmacometrics: Turning Pitfalls into Pathways.** Useful for assurance needs around increasingly automated scientific workflows.
- **Coffee Connect / Meet the SIGs / exhibit-poster periods.** Better for short discovery conversations than interrupting technical sessions.
- Vendor workshops around NONMEM, Monolix, QSP, AI-assisted pharmacometrics and agentic workflows are useful for understanding integration surfaces and existing provenance/QC capabilities.

## Five-minute PCS demo

Do not demo architecture slides first.

1. Start with a restricted PK/PD workflow.
2. Run or show an attestation.
3. Show the claim list and explicit assumptions.
4. Show the signed package and reviewer policy.
5. Change one artifact and show the dependent claim reopen/fail.
6. Alter the human report and show package verification reject it.
7. Show runtime.json and explain that provenance is distinct from correctness.
8. End with the limitations file.

Core sentence:

> PCS turns a consequential computational claim into a replayable evidence package: exact artifacts, explicit assumptions, checks/proofs, provenance, signer identity, and what remains unverified.

Do not say “PCS proves the drug model is correct.”

## Discovery questions

1. Tell me about the last pharmacometric/modeling result that was hard to reproduce or review.
2. What parts of model QC are still manual?
3. How do you show that the implemented model corresponds to the intended equations?
4. What evidence has to survive handoff from modeler to reviewer/client/regulatory team?
5. What mistakes are expensive enough that you maintain independent review procedures for them?
6. When a dataset, model, or script changes, how do you know which conclusions need to be re-reviewed?
7. How do you compare environments/versions between analysts?
8. Which parts of your current stack already solve this well?
9. What would make an assurance certificate useless or untrustworthy to you?
10. Would you be willing to give us one bounded synthetic/de-identified workflow and try to break the output?

## What to record after every conversation

- role / organization type;
- workflow class;
- painful failure mode;
- current workaround;
- frequency;
- consequence/cost;
- buyer or budget owner if known;
- existing tools;
- strongest objection to PCS;
- willingness to share bounded workflow;
- follow-up date;
- exact repeated terminology they use.

Avoid recording sensitive scientific or personal information that is not necessary.

## Post-conference conversion

Within 24–48 hours, follow up only with people who had a concrete problem.

Offer a no-cost or tightly scoped design-partner run on one synthetic/de-identified workflow. They define the claims; PCS returns a replayable evidence package and both sides identify what is useful, missing, or misleading.

Do not ask a large organization to buy enterprise software before the design-partner result exists.

## Sources used to scope this plan

- ACoP 2026 official schedule: https://acop2026.eventscribe.net/agenda.asp
- ACoP 2026 registration/event description: https://acop2026.eventscribe.net/
- FDA MIDD Paired Meeting Program: https://www.fda.gov/drugs/development-resources/model-informed-drug-development-paired-meeting-program
- FDA ICH M15 final guidance page: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/m15-general-principles-model-informed-drug-development
