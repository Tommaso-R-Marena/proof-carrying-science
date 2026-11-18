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

## Irreducible boundary

- CPython / `json.loads` / OS I/O (byte string → post-parse graph)
- External attestation beyond declared labels

Catalog: `EQUIVALENCE_BREAKS.md`.
