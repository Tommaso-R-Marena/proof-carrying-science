# Python ↔ Lean semantic equivalence

## Proved (kernel-checked)

| Link | Theorem |
|---|---|
| Surface model = Python entrypoint | `checkCertificatePy = checkSurface` |
| Surface → core | `checkSurface_implies_checkCertificate` |
| Core ↔ surface (bounded, non-empty) | `checkSurface_iff_checkCertificate` |
| Accept → Derives / Entails4 / ¬mathEstablished | `checkSurface_sound`, `*_entails4`, `*_mathEstablished_false` |
| Derives ↔ core certificate | `derives_iff_core_certificate` |
| Classical vs Entails4 | `classical_entails_atom99_demoΓ` / `not_entails4_atom99_demoΓ` |
| Finding F (Hyp) | `hyp_mathVerified_not_established` |
| Meet lock | `meet_truth_table` + shared `meet_tables.py` |
| JSON object graph → surface | `checkJsonCert_sound`, `checkCertificateJson` |
| Unknown keys / deep formulas | `checkJsonCert_rejects_*` |
| No mathEstablished w/o attestation | `no_math_established_without_attestation` |

## Irreducible boundary

- Byte-string `json.loads` / CPython / OS I/O → typed `JsonCertificate` AST

Catalog: `EQUIVALENCE_BREAKS.md`.
