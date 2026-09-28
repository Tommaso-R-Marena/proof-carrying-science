# v0.5 Founding Verdict

**STATUS: DESIGN-PARTNER ALPHA CANDIDATE — FORMAL KERNEL BUILD STILL OPEN**

## Current repository inventory

- 86 Python tests are present.
- 25 targeted adversarial attacks are encoded.
- These inventory counts are **not** promoted to execution claims while hosted runners remain unavailable.

## Last retained full execution evidence

- 44/44 automated Python tests passed in the last retained full local/reference run before later provenance/refinement/security additions.
- 16/16 targeted foundational attacks were rejected with 0 false accepts in that finite campaign.
- A prior revision stated 49/49 tests passing, but no retained machine-readable execution log distinguishes that run from later inventory edits; PCS therefore does not use 49/49 as an authoritative current claim.
- The newly added ZIP namespace guard has been directly exercised against duplicate members and namespace/path aliases, but the full updated suite remains pending.

## Implemented architecture

- Package signatures bind the certificate, human-readable report, signatures, public-key copy, artifacts, runtime provenance, limitations statement, and delivered files.
- Signer identity can be pinned by Ed25519 public-key fingerprint.
- Reviewer acceptance policy remains external to the producer bundle.
- Restricted one-compartment IV-bolus PK + direct Emax PD contracts and analytic replay exist on the synthetic reference case.
- ZIP extraction fails closed on path traversal, symlinks, excessive sizes, duplicate member names, non-canonical aliases, and file/parent namespace collisions.
- Publication firewall remains active; constituent unpublished research is not imported as a dependency.

## Still open

- a successful full 66-test / 23-attack execution from the current commit;
- successful Lean 4.16 build of the formal kernel;
- executable-to-Lean refinement theorem;
- production signing-key custody/revocation/transparency infrastructure;
- first external design-partner workflow;
- first paid pilot;
- GxP or regulator-specific validation.

No claim of biological truth, clinical validity, regulatory acceptance, or arbitrary-program correctness is made.

See `results/EXECUTION_LEDGER.md` for the authoritative evidence/inventory distinction.

## New launch hardening in current inventory

Current source now includes executable JSON Schema validation, strict duplicate-key JSON parsing, pre-result pilot claim/assumption locks bound into signed packages, final bundle re-verification before attestation succeeds, safe signing-key generation defaults, and a browser-only pilot intake builder. None of these additions are promoted to executed PASS status until the full current suite runs from one recorded commit.
