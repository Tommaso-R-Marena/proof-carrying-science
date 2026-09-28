# Pilot Operations Runbook — v0.4

## Objective

Complete one bounded external computational-biopharma assurance engagement without overstating what PCS proves.

## Intake gate

Accept a pilot only when all of the following are true:

- the workflow boundary can be stated in one paragraph;
- the partner can name 3–10 concrete computational claims;
- data may legally and contractually be provided for the agreed purpose;
- the pilot does not require PCS to certify clinical validity, regulatory acceptance, or arbitrary unsupported code;
- all constituent PCS research used in the pilot is clean-room, synthetic, public, or otherwise cleared for the engagement.

## Before receiving artifacts

1. Assign a pilot identifier such as `PCS-PILOT-0001`.
2. Record the partner contact and approved data-transfer path.
3. Freeze the initial claim inventory and assumptions.
4. Record which files are expected and which are explicitly out of scope.
5. Create a dedicated private workspace with least-privilege access.

## Assurance execution

1. Hash the received source artifacts before transformation.
2. Create the PCS manifest and machine-readable predicates.
3. Run `pcs certify` or `pcs attest`.
4. Independently replay with `pcs verify`.
5. Run the relevant adversarial tests.
6. Review all OPEN / FAILED claims manually; never suppress them to make the report look cleaner.
7. Generate `report.html`.
8. Sign the final certificate with the pilot signing key.
9. Create the deterministic evidence ZIP.
10. Verify the ZIP from a clean temporary directory with `pcs verify-bundle --require-signature`.

## Required delivery package

- `certificate.json`
- `signature.json`
- signer public key or an agreed public-key location
- `report.html`
- packaged source artifacts that the agreement permits PCS to redistribute back to the partner
- deterministic evidence ZIP
- SHA-256 of the ZIP
- a one-page limitations statement

## Partner review

A reviewer who did not produce the original workflow should be able to answer:

- What exact claims were evaluated?
- Under what assumptions?
- Which exact artifacts support the claims?
- Which checks were replayed?
- Which claims passed, failed, or remain open?
- What does the certificate explicitly *not* establish?

## Closeout

- obtain partner feedback;
- record manual work that should become an adapter;
- record false-positive/false-negative concerns;
- archive the signed bundle and public-key fingerprint;
- delete or retain partner data only according to the governing agreement;
- do not reuse partner artifacts for research, demos, or model training without explicit permission.
