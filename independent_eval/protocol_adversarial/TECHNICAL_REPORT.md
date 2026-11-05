# Technical report — Independent Protocol & Adversarial Evaluation

## Scope

Tasks 1–6 under `independent_eval/protocol_adversarial/`, evaluating PCS as a black box.

## Method

1. Independent Rust JCS reference (no PCS imports).
2. Differential vectors vs PCS Python `canonicalize_jcs` / `jcs_sha256`.
3. Deterministic adversarial corpus (≥150) with **attempted** `verify_package_zip_end_to_end_v06` for each case.
4. ZIP loader differential vs stdlib `zipfile`.
5. Intake chronology distinguishing hash integrity, signatures, and reviewer-owned expected hashes.
6. Dual-reviewer policy overlays that must not alter PCS validity.
7. Bounded CPU/RSS measurements on large/nested inputs.

## Campaign results (observed)

- Adversarial corpus: **151** verify-attempted cases; **10** positive accepted; **141** negatives rejected after attempted verify; **0** false accepts; **0** not_attempted.
- Added mutation families beyond byte-flip/extra-member baselines: truncated and bit-flipped Ed25519 signature fields; swapped `public_key_fingerprint` vs signer; member rename that breaks inventory lock; duplicated critical members with conflicting bytes; empty certificate / signature / normalized-index bytes (in-archive empty-transcript analogue).
- UTF-8 overlong encodings and weird ZIP timestamps were **not** added: they are not present as existing adversarial harness patterns (ZIP timestamp weirdness remains out of scope for this deepening).

## Most consequential remaining weaknesses (ranked)

1. Cross-language JCS number canonicalization edge cases can desynchronize independent verifiers.
2. Downstream policy consumers may confuse computational PASS with scientific acceptance.
3. Archive ambiguities (duplicates, compression modes) require explicit high-assurance STORED canonical rules — already partially enforced, but differentials remain educational for reviewers.
4. Chronology/preregistration requires out-of-band reviewer commitments; producer timestamps alone are insufficient (by design, but easy to misunderstand).

## Proposed follow-ups for Codex/Aristotle (do not implement here)

- Publish a frozen cross-language JCS number corpus with expected spellings.
- Document reviewer-policy non-authority explicitly in receipt schemas.
- Consider Lean-side statements about what intake locks do *not* prove regarding wall-clock preregistration.
