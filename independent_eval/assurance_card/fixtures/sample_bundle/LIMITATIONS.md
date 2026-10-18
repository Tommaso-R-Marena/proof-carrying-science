# PCS Assurance Scope and Limitations (fixture)

**Subject:** synthetic-assurance-card-demo

This fixture LIMITATIONS.md accompanies the offline Assurance Card sample
bundle. It is not a regulatory certification.

## Claim assessments

- **C_REPLAY — COMPUTATIONALLY_SUPPORTED:** Predictions match the declared analytic model within tolerance.
- **C_INTEGRITY — SIGNATURE_OK:** Artifact digests match the committed package hashes (fixture label).
- **C_BIOLOGY — OPEN:** The model is biologically adequate for clinical use.

## Explicit assumptions

- **A_MODEL:** The declared equation is the computational model under test; biological adequacy is not claimed.

## This package does not by itself establish

- biological or mechanistic adequacy of the declared model.
- clinical safety, efficacy, or patient-level predictive validity.
- regulatory approval, acceptance, certification, or GxP validation.
- security proofs or merge readiness.

## Interpretation rule

A computationally supported claim means only that the represented checks
succeeded under stated assumptions. Formal/computational assurance and
empirical scientific validation remain distinct. A computational PASS from
`pcs verify` is not empirical adequacy; the Assurance Card never certifies
science.
