# Trust-boundary assessment — independent scientific pilot v1

This assessment accompanies the synthetic independent-pilot demonstration. It separates **kernel-proved** guarantees, **independently tested** properties, and **unproved** environmental assumptions. It does not expand Lean theorems and does not claim production trust-root security.

## Kernel-proved (Lean-authoritative production boundary)

When `pcs-lean-authority` returns `ACCEPT` on a canonical PCS ZIP:

- Archive/certificate acceptance follows the Lean v0.6/v2 authority path (`docs/LEAN_KERNEL_STATUS.md`, `formal/PCS_FRONTIER_FORMALIZATION_REPORT.md`).
- SHA-256 over certificate-bound digests matches the independently specified FIPS 180-4 construction in Lean.
- Built-in checkers for `pkpd_contract` and `pkpd_reference_match` are replayed inside the authority against committed table bytes.
- Path-unsafe archive members are rejected by the ZIP loader before authority acceptance.

Still **not** kernel-proved: RFC 8032 Ed25519 correctness/unforgeability, OS/Python refinement, arbitrary external validators, continuum PK/PD adequacy, or clinical claims.

## Independently tested (executable regression)

The independent pilot runner and `tests/test_independent_pilot_v1.py` establish observed fail-closed behavior for:

| Attack / property | Expected behavior |
| --- | --- |
| Changed scientific artifact (`predictions.csv`) | Verification rejects |
| False certificate bytes | Verification rejects |
| Signature substitution (wrong public key / fingerprint pin) | Verification rejects |
| Path-traversal ZIP member (`../escape.txt`) | Load/verify rejects |
| Absolute archive member | Load/verify rejects |
| Stale/mutated reviewer receipt binding | Receipt no longer matches delivered bundle hash |
| Post-hoc claim statement change vs intake lock | Intake lock assertion fails |
| Unexpected source modification vs lab inventory | Hash mismatch detected |
| Second-environment verify of exact bytes | Authoritative ACCEPT |
| Clean-room venv reconstruction | Same authoritative stages with hash-pinned deps |

Passing a finite attack suite is **not** a security proof.

## Unproved environmental assumptions

- Host OS, Python interpreter, `cryptography` wheel, and filesystem integrity.
- Ed25519 unforgeability of any trust anchor.
- That demo keys (public, deterministic seed) could ever be production signers — they must not.
- That automated confirmation in the demo equals authenticated institutional review — it does not.
- Scientific/empirical adequacy of the synthetic PK/PD model.
- Legal/counsel clearance, partner agreements, or paid-engagement readiness (#9/#14).

## Exact-byte Python ↔ Lean correspondence

| Boundary | Status |
| --- | --- |
| Canonical JCS certificate bytes | Covered by frozen v0.6 golden byte contracts and Lean authority decode |
| Canonical ZIP members (STORED) | Lean raw-archive decode when `archive_assurance == lean-decoded-canonical-zip` |
| Python precheck observation transcript | Must exactly cover certificate evidence order before Lean acceptance |
| Native binary / Python runtime semantics | **Unproved** refinement; differential tests elsewhere are observational only |
| Serialized scientific CSV/JSON meaning outside declared checkers | Bound by hashes + declared predicates only |

## Reviewer checklist

1. Pin the producer public-key fingerprint out of band.
2. Verify the ZIP with `pcs verify-v06-bundle` requiring signature + fingerprint.
3. Confirm `authoritative: true` and Lean authority `ACCEPT`.
4. Read `LIMITATIONS.md` and refuse to equate claim PASS with scientific truth.
5. Retain the verification receipt bound to the exact `bundle_sha256`.
