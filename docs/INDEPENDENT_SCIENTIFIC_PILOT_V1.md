# Independent scientific pilot v1

**Status:** reproducible synthetic external-workflow demonstration.  
**Does not claim:** an actual external partnership, legal clearance, biological adequacy, clinical validity, GxP validation, regulatory acceptance, or production trust-root security.

This document is the operator/reviewer guide for the bounded independent-pilot path that addresses engineering readiness for issues #9/#13-style workflows using **public/synthetic** inputs only.

## What was verified

Under pinned signer fingerprint and Lean-authoritative v0.6 verification, the pilot demonstrates:

1. Pre-result intake freeze (`pcs-pilot-intake-v1` → intake lock).
2. Local artifact discovery and explicit confirmation (draft cannot be attested).
3. Alignment of confirmed claim/assumption IDs to the frozen intake.
4. Signed evidence packaging via `pcs attest-v06 --intake-lock …` (lock bound into the ZIP as `pilot-intake-lock.json`) with computational replay of restricted one-compartment IV-bolus PK + direct-Emax PD.
5. Second-environment verification of the exact delivery ZIP (canonical archive + Lean authority ACCEPT).
6. Reviewer receipt + human-readable report separating computational results from scientific validity.
7. Fail-closed adversarial mutations (artifact change, false certificate, signature substitution, path traversal, absolute members, stale receipt binding, post-hoc claim mutation, source modification detection).
8. Archival packaging and hash-bound closeout planning for ephemeral demo keys.

## Exact reproduce commands

Pinned toolchain:

- Python: `.python-version` → `3.12.14` (runtime may be 3.12.x compatible)
- Lean: `lean-toolchain` → `leanprover/lean4:v4.28.0`
- Lockfile: `requirements-dev.lock` (hash-pinned)
- Host packages observed necessary on Ubuntu: `zstd`, `python3-venv`

```bash
git rev-parse HEAD
python3 -m pip install -e '.[dev]'
python3 scripts/check_repository_integrity.py
source scripts/activate_lean_428.sh   # installs Lean 4.28.0 with digest check
cd formal && lake build pcs-lean-authority && cd ..
export PCS_LEAN_AUTHORITY_BIN="$PWD/formal/.lake/build/bin/pcs-lean-authority"

# Full pilot (producer + second-environment reviewer + adversarial + closeout)
python scripts/run_independent_scientific_pilot_v1.py \
  --output /tmp/pcs-independent-pilot \
  --lean-authority "$PCS_LEAN_AUTHORITY_BIN" \
  --overwrite --apply-closeout

# Or via CLI
pcs independent-pilot-v1 -o /tmp/pcs-independent-pilot \
  --lean-authority "$PCS_LEAN_AUTHORITY_BIN" --overwrite --apply-closeout

# Clean-room reconstruction (fresh venv + fresh Lean rebuild; never inherits PCS_LEAN_AUTHORITY_BIN)
python scripts/run_cleanroom_independent_pilot_v1.py \
  --output /tmp/pcs-cleanroom-pilot \
  --overwrite

# Fixture-only byte-comparable regeneration (not a production claim)
python scripts/run_independent_scientific_pilot_v1.py \
  --output /tmp/pcs-independent-pilot-fixture \
  --lean-authority "$PCS_LEAN_AUTHORITY_BIN" \
  --overwrite --deterministic-fixture

# Tests (high-assurance CI sets PCS_REQUIRE_LEAN_AUTHORITY=1 so missing authority fails)
PCS_REQUIRE_LEAN_AUTHORITY=1 python -m pytest -q \
  tests/test_independent_pilot_v1.py \
  tests/test_intake_verify_v06.py \
  tests/test_attest_v06_intake_lock.py \
  tests/test_python_lean_archive_boundary_v06.py
```

## Reviewer path (delivered package only)

Given `study.pcs.zip`, `trusted-public.pem`, the pinned fingerprint, and optionally a reviewer-owned expected intake semantic hash (out of band — not from the ZIP alone):

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --expected-signer-fingerprint <fingerprint> \
  --require-intake-lock \
  --expected-intake-semantic-hash <64-hex-from-out-of-band-channel> \
  --receipt verification-receipt.json
```

`frozen_at` inside the signed lock is producer metadata only; it is not preregistration evidence. Read `LIMITATIONS.md`, `REVIEWER_REPORT.md`, and `TRUST_BOUNDARY_ASSESSMENT.json` before interpreting claim decisions.

## Reproducibility

| Scenario | Requirement |
| --- | --- |
| Independent verification of one delivered bundle | Identical `bundle_sha256` and accepted semantics |
| Independent regeneration | Matching certificate/intake semantic hashes; bundle SHA may differ when `frozen_at` differs |
| Deterministic fixture mode | Explicitly labeled; byte-identical SHA-256 under pinned timestamps/keys only |

Do not claim production bundles are byte-identical across separate executions when timestamps or keys legitimately differ.

## Scientific vs computational boundary

| Layer | Status in this pilot |
| --- | --- |
| Computational replay of declared PK/PD equations | Exercised and Lean-checked for supported predicates |
| Formal archive/certificate acceptance | Lean-authoritative ACCEPT required |
| Biological model adequacy | **OPEN / not claimed** |
| Clinical or regulatory acceptance | **OPEN / not claimed** |
| Production signing custody | **Not demonstrated** (public demo keys only) |

## Trust-boundary assessment

Machine-readable: emitted as `archive/TRUST_BOUNDARY_ASSESSMENT.json`.  
Narrative companion: `docs/TRUST_BOUNDARY_ASSESSMENT_INDEPENDENT_PILOT_V1.md`.

## Relation to open issues

- **#13** (first external design-partner workflow): this delivers a **synthetic stand-in** that a new lab can reproduce. It does **not** close #13, which requires a genuinely external partner-defined workflow.
- **#9** (operations/legal/key controls): engineering runbook/key-custody docs already exist; this pilot exercises closeout planning with demo keys only and does not invent counsel-reviewed legal language.
- **#14** (paid pilot): explicitly out of scope; no payment/entity path is claimed.

## Non-duplication

This work does not modify the research branch in PR #117 (proof-gated self-improvement) and does not bump CI action dependencies from PR #119.
