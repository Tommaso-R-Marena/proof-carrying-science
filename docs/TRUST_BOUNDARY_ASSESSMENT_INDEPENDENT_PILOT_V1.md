# Trust-boundary assessment — independent scientific pilot v1

This assessment accompanies the synthetic independent-pilot demonstration. It separates **kernel-proved** guarantees, **independently tested** properties, and **unproved** environmental assumptions. It does not expand Lean theorems and does not claim production trust-root security, external adoption, biological adequacy, or clinical validity.

## Kernel-proved (Lean-authoritative production boundary)

When `pcs-lean-authority` returns `ACCEPT` on a canonical PCS ZIP:

- Archive/certificate acceptance follows the Lean v0.6/v2 authority path (`docs/LEAN_KERNEL_STATUS.md`, `formal/PCS_FRONTIER_FORMALIZATION_REPORT.md`).
- SHA-256 over certificate-bound digests matches the independently specified FIPS 180-4 construction in Lean.
- Built-in checkers for `pkpd_contract` and `pkpd_reference_match` are replayed inside the authority against committed table bytes.
- Path-unsafe archive members are rejected by the ZIP loader before authority acceptance.

Still **not** kernel-proved: RFC 8032 Ed25519 correctness/unforgeability, OS/Python refinement, arbitrary external validators, continuum PK/PD adequacy, or clinical claims.

## Independently tested (executable regression)

The independent pilot runner, `pcs/intake_verify_v06.py`, and focused tests establish observed fail-closed behavior for:

| Attack / property | Expected behavior |
| --- | --- |
| Changed scientific artifact (`predictions.csv`) | Verification rejects |
| False certificate bytes | Verification rejects |
| Signature substitution (wrong public key / fingerprint pin) | Verification rejects |
| Path-traversal ZIP member (`../escape.txt`) | Load/verify rejects |
| Absolute archive member | Load/verify rejects |
| Stale/mutated reviewer receipt binding | Receipt no longer matches delivered bundle hash |
| Post-hoc claim statement change vs intake lock | Intake lock assertion fails |
| **Malicious producer: substituted signed intake lock** | Independent ZIP verifier rejects (`failed_stage=intake_lock`) |
| **Reviewer-owned expected intake hash mismatch** | Verification rejects; `preregistration_evidence` stays `none` |
| Unexpected source modification vs lab inventory | Hash mismatch detected |
| Second-environment verify of exact delivered bytes | Identical `bundle_sha256` + authoritative ACCEPT |
| Independent regeneration (non-fixture) | Matching certificate/intake semantic hashes; bundle SHA may differ when `frozen_at` differs |
| Deterministic fixture mode (explicitly labeled) | Byte-identical bundle SHA-256 under pinned timestamps/keys |
| Clean-room venv + fresh Lean rebuild | Authoritative stages without inheriting `PCS_LEAN_AUTHORITY_BIN` |

Passing a finite attack suite is **not** a security proof.

### Intake lock: producer vs reviewer

- Producer `attest-v06 --intake-lock` binds `pilot-intake-lock.json` into the signed package and checks consistency before signing.
- That is **not** sufficient. `verify-v06-bundle --require-intake-lock` re-validates the signed member against certificate semantics from received bytes alone (`pcs/intake_verify_v06.py`).
- `frozen_at` is producer-supplied metadata and is **never** treated as preregistration evidence.
- Optional `--expected-intake-semantic-hash` is reviewer-owned and must be supplied out of band; only then is `preregistration_evidence` set to `reviewer_owned_expected_intake_semantic_hash`.

### Reproducibility claims (do not overclaim)

| Mode | What must match | What may differ |
| --- | --- | --- |
| Independent verification of one delivered bundle | `bundle_sha256`, accepted semantics, intake hash | Nothing about the bytes |
| Independent regeneration (production-like) | Certificate semantic hash, intake semantic hash, claim decisions | `frozen_at`, bundle SHA-256, non-semantic metadata |
| Deterministic fixture mode | Bundle SHA-256 (explicit fixture claim only) | N/A under pinned timestamps/keys |

Do **not** claim that production bundles are byte-identical across separate executions when timestamps or cryptographic inputs legitimately differ.

## Unproved environmental assumptions

- Host OS, Python interpreter, `cryptography` wheel, and filesystem integrity.
- Ed25519 unforgeability of any trust anchor.
- That demo keys (public, deterministic seed) could ever be production signers — they must not.
- That automated confirmation in the demo equals authenticated institutional review — it does not.
- Scientific/empirical adequacy of the synthetic PK/PD model.
- Legal/counsel clearance, partner agreements, or paid-engagement readiness (#9/#14).
- That a synthetic pilot demonstrates genuine external adoption.

## Exact-byte Python ↔ Lean correspondence

| Boundary | Status |
| --- | --- |
| Canonical JCS certificate bytes | Covered by frozen v0.6 golden byte contracts and Lean authority decode |
| Canonical ZIP members (STORED) | Lean raw-archive decode when `archive_assurance == lean-decoded-canonical-zip` |
| Python precheck observation transcript | Must exactly cover certificate evidence order before Lean acceptance |
| Native binary / Python runtime semantics | **Unproved** refinement; differential tests elsewhere are observational only |
| Serialized scientific CSV/JSON meaning outside declared checkers | Bound by hashes + declared predicates only |
| Signed intake lock vs certificate statements | Independently tested in the Python verifier path; not a Lean theorem |

## Clean-room / independent build provenance

The clean-room runner (`pcs cleanroom-independent-pilot-v1`):

1. Creates a fresh venv with hash-pinned `requirements-dev.lock`.
2. Copies formal sources into an isolated tree and runs `lake build pcs-lean-authority`.
3. Never inherits ambient `PCS_LEAN_AUTHORITY_BIN`.
4. Records Lean/lake versions, toolchain pin, authority SHA-256, source commit, and lockfile SHA-256 in `CLEANROOM_AUTHORITY_PROVENANCE.json`.

Public CI job `independent-pilot-cleanroom` repeats an independent formal rebuild and runs focused tests with `PCS_REQUIRE_LEAN_AUTHORITY=1` (fail, do not skip).

## Reviewer checklist

1. Pin the producer public-key fingerprint out of band.
2. Optionally pin the expected intake semantic hash out of band (distinct from `frozen_at`).
3. Verify the ZIP with `pcs verify-v06-bundle --require-intake-lock` (and `--expected-intake-semantic-hash` when available).
4. Confirm `authoritative: true` and Lean authority `ACCEPT`.
5. Read `LIMITATIONS.md` and refuse to equate claim PASS with scientific truth.
6. Retain the verification receipt bound to the exact `bundle_sha256`.
