# Independent scientific pilot — implementation report (review hardening)

## Scope

Synthetic independent-assurance pilot on branch `feature/independent-scientific-pilot-c8bb` (PR #120).
Does **not** claim external adoption, biological adequacy, clinical validity, or production security.

## Source-level findings

1. **Producer-only intake checks were insufficient.** `attest_v06(..., intake_lock=...)` binds and checks the lock before signing, but a malicious producer can substitute `pilot-intake-lock.json` and resign the package manifest. Reviewer-side enforcement is now in `pcs/intake_verify_v06.py`, wired into ZIP/directory verifiers.
2. **Identical bundle SHA across regenerations was not a general property.** With intake locks bound into the ZIP, dynamic `frozen_at` changes package bytes. Observed: regeneration bundle SHAs differ when `frozen_at` differs; certificate/intake semantic hashes match. Byte-identical regeneration is only claimed under `--deterministic-fixture`.
3. **Clean-room previously could inherit `PCS_LEAN_AUTHORITY_BIN`.** It now rebuilds Lean from a fresh formal checkout by default and records provenance.

## Measured hashes (this environment)

| Item | Value |
| --- | --- |
| Commit | `b512b96952ff53701cf5c43c6b0355c44cc5cd34` |
| Authority SHA-256 | `3fd286e68299ad399b59078618045cdaedac3bd0d55305d074005ade16317b49` |
| Intake semantic hash | `ab9fec8d50a28c2d432f68ecc8d5fa01e7e3f4867bc061ba289b37947b3a14cd` |
| Certificate semantic hash | `dc6c4d4204eb7829cc1ea4aa2ff9fc451ff6b25e0db0669e88765812fced5483` |
| Regen bundle A | `ad3a9f1822686020ed9d23a8ef204ca9cef80f0301a9747c73a6502d55908a6b` |
| Regen bundle B | `d06460c9a961495b6f0ccec8b6a7b390bec57af68e757e8087890e253350472e` |
| Fixture bundle SHA | `ee126671a27f677b2dd9e317ff9c0e58851f7a8810f135fdbd72f4804edab358` |
| Clean-room authority SHA | `3fd286e68299ad399b59078618045cdaedac3bd0d55305d074005ade16317b49` |
| requirements-dev.lock SHA | `b1f321c05fdfad0631f4eaae93b32fb9044d77d2b1d3a081b66477b1e784d644` |
| Lean toolchain pin | `leanprover/lean4:v4.28.0` |

## Regression results

- Focused: `tests/test_intake_verify_v06.py`, `test_attest_v06_intake_lock.py`, `test_python_lean_archive_boundary_v06.py`, `test_independent_pilot_v1.py` → **20 passed**
- Broader related: + `test_pilot_intake.py`, `test_pilot_closeout.py`, `test_lean_authority_v06.py` → **40 passed**
- `PCS_REQUIRE_LEAN_AUTHORITY=1` without compiled authority → **fails** (does not skip)

## Commands

```bash
source scripts/activate_lean_428.sh
cd formal && lake build pcs-lean-authority && cd ..
PCS_REQUIRE_LEAN_AUTHORITY=1 python3 -m pytest -q \
  tests/test_intake_verify_v06.py \
  tests/test_attest_v06_intake_lock.py \
  tests/test_python_lean_archive_boundary_v06.py \
  tests/test_independent_pilot_v1.py
python3 scripts/run_cleanroom_independent_pilot_v1.py -o /tmp/pcs-cleanroom --overwrite
```

## Limitations

- Demo keys only; not production trust roots.
- Finite adversarial suite is not a security proof.
- Public CI `independent-pilot-cleanroom` must still pass on GitHub for merge readiness.
- PR remains draft until required checks and independent review of security/reproducibility claims.
