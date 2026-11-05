# Bugs and specification ambiguities — Workstream A

Observed during independent evaluation. These are **not** silent production patches.

## Ambiguities / findings

1. **JCS number spelling edge cases** — Independent Rust `f64` stringification may disagree with PCS Python `repr`-based ECMAScript spelling for some scientific/large magnitudes. Recorded in `results/jcs_differential.json` disagreements; treat as specification-surface risk for cross-language verifiers.
2. **Duplicate ZIP member names** — stdlib `zipfile` accepts duplicates; PCS package load may reject or last-write depending on loader stage. Differential cases capture acceptance asymmetry. Corpus family `duplicate_conflict_*` also exercises conflicting bytes for critical control members.
3. **Producer `frozen_at` vs preregistration** — Without reviewer-owned `expected_intake_semantic_hash`, a future/forged `frozen_at` does not constitute preregistration evidence (confirmed when `intake_verify_v06` is present; on older main without that module, chronology harness records unavailability).
4. **Reviewer policy confusion** — A permissive consumer policy can incorrectly infer scientific acceptance from computational PASS. PCS validity itself does not change; the hazard is downstream interpretation.
5. **Fingerprint vs signer key confusion** — Cases `swapped_fingerprint_*` and `wrong_signer_key_honest_fingerprint` confirm PCS rejects when the signature-record fingerprint or the provided public key disagree with the pinned expected fingerprint / cryptographic signer.

## Corpus campaign counts (observed)

- `case_count`: **151**
- `positive_accepted`: **10**
- `negatives_rejected_after_attempted_verify`: **141**
- `false_accepts`: **[]**
- `not_attempted`: **[]**

## False accepts

Campaign `results/adversarial_corpus.json` must list `false_accepts: []`. Any non-empty list is a high-priority defect report with minimal reproducible ZIP retained under `fixtures/adversarial/corpus/`.
