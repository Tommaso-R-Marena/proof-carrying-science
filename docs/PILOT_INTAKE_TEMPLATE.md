# Pilot Intake Template

Use one copy per external workflow. This is an engineering intake record, not a legal agreement.

## Pilot identity

- PCS pilot ID:
- Partner / organization:
- Technical owner:
- Independent reviewer:
- Intake date:
- Target closeout date:
- PCS version / commit:
- Authorized signer fingerprint:

## Bounded workflow

Describe the workflow boundary in one paragraph. Identify the exact starting artifacts, transformations in scope, and final outputs in scope.

**Out of scope:** list systems, data, code, downstream decisions, or scientific questions that PCS is not evaluating.

## Reviewer-defined claims

Claims should be falsifiable, scoped, and phrased so a reviewer can tell what evidence would discharge them.

| Claim ID | Claim | Assurance class | Required evidence/check | Acceptance status(es) |
|---|---|---|---|---|
| C1 |  | computational/formal/empirical/mixed |  |  |

Do not include “the model is correct” or “the drug is safe” as an undifferentiated claim.

## Explicit assumptions

| Assumption ID | Statement | Claims depending on it | Owner/reviewer |
|---|---|---|---|
| A1 |  |  |  |

## Artifact inventory

| Artifact ID | Description | Data classification | Source owner | Transfer permitted? | Expected hash if known |
|---|---|---|---|---|---|
|  |  | public/synthetic/de-identified/confidential/restricted |  |  |  |

Do not accept PHI, credentials, export-controlled data, or other restricted material without an explicit reviewed agreement and appropriate infrastructure.

## Runtime / execution context

- Partner runtime supplied? yes/no
- Container or environment lockfile supplied? yes/no
- PCS runtime snapshot required? yes/no
- Cross-environment replay required? yes/no
- Environment differences that should fail reviewer policy:

A runtime match is provenance evidence, not proof of scientific correctness.

## Data handling

- Approved transfer channel:
- PCS workspace:
- People authorized to access:
- Retention period:
- Required deletion date:
- Permission to retain final signed evidence bundle:
- Permission to use anonymized lessons learned:
- Permission for public case study: yes/no, separate written approval required

## Acceptance policy

The reviewer, not the producer, owns final acceptance criteria.

- External policy file:
- Signature required: yes/no
- Pinned signer fingerprint:
- Required claims and allowed statuses:
- Any manual review gates:

## Delivery

Expected deliverables:

- certificate.json
- report.html
- LIMITATIONS.md
- runtime.json
- package_manifest.json
- package_signature.json when signed
- signer public key or agreed public-key location
- deterministic evidence ZIP
- bundle SHA-256
- reviewer replay instructions

## Closeout

- Reviewer independently verified bundle: yes/no
- Reviewer policy result:
- Open/failed claims:
- False-positive concerns:
- False-negative concerns:
- Manual assurance steps worth automating:
- Missing adapters:
- Data deletion/retention completed:
- Follow-up commercial/research decision:
