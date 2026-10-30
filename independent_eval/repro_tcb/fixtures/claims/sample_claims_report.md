# Sample claims report (independent eval fixture)

Synthetic claims used to exercise the Workstream C traceability auditor.
These are **not** production assurance statements.

- **Claim C12.identity**: Identical-archive replay preserves ZIP SHA-256 across clean directories.
  - commit: HEAD
  - hash: evidence_canonical.zip
  - test: test_reconstruction.py
  - note: supported by reconstruction harness fixtures

- **Claim C13.sha256**: Lean SHA-256 specification is transcription-faithful to FIPS 180-4.
  - theorem: Sha256ProductionAgrees
  - assumption: Sha256Collision
  - commit: HEAD
  - note: implementation is executable-tested; collisions remain assumed

- **Claim C13.os**: The operating system always delivers exact bytes with no TOCTOU.
  - assumption: OS_FILESYSTEM
  - note: intentionally ambiguous — assumption only

- **Claim C14.unsupported**: Every possible PCS package is proven secure against all adversaries.
  - note: no evidence links

- **Claim C14.stale**: Prior campaign accepted the golden package on commit deadbeefdeadbeefdeadbeefdeadbeefdeadbeef.
  - commit: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
  - expected_commit: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
  - test: test_formal_v2_differential.py

- **Claim C14.ambiguous**: Production acceptance always implies Lean acceptance.
  - assumption: ProductionRefinesLean
  - theorem: missing_theorem_that_does_not_exist
  - note: mixed resolved/unresolved links
