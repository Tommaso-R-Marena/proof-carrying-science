# Where Python ↔ Lean equivalence breaks (closed vs irreducible)

Exclusive path only.

## Closed (kernel-checked and/or single-source locked)

| Break | Resolution |
|---|---|
| Classical `Entails` explosion | `classical_entails_atom99_demoΓ` vs `¬ Entails4 demoΓ (atom 99)` |
| Finding D abstract `Certificate.valid` | `StructuredCertificate.traceValid` |
| Core LTR loop | `compile_ok`, `derives_iff_core_certificate` |
| Surface WF + claims | `checkSurface` / `checkSurface_iff_checkCertificate` |
| Post-parse JSON object graph | `JsonCert.decodeJsonCert` / `checkJsonCert_sound` / reject unknown keys & deep formulas |
| Python model entrypoints | `checkCertificatePy = checkSurface`; `checkCertificateJson = checkJsonCert` |
| Duplicate meet tables | `meet_tables.py` + `meet_truth_table` |
| Finding F (Hyp / attestation) | `hyp_mathVerified_not_established`; `no_math_established_without_attestation` |

## Irreducible trust boundary

| Boundary | Why |
|---|---|
| **Byte-string `json.loads` / CPython / OS I/O** | Produces the typed `JsonCertificate` AST; Lean checks everything afterward |

## Test locks (66 pytest)

- `test_exhaustive_checker.py` — 6×6 meet, all authorities, andI pairs, JSON/WF mutants, nested chains
- `test_equivalence_breaks.py`, `test_python_lean_differential.py`, `test_security_findings_v1.py`, adversarial
