# Where Python ↔ Lean equivalence breaks (closed vs irreducible)

Exclusive path only. Status after Phase IV++.

## Closed (kernel-checked and/or single-source locked)

| Break | Resolution |
|---|---|
| Classical `Entails` explosion | `classical_entails_atom99_demoΓ` vs `¬ Entails4 demoΓ (atom 99)` |
| Finding D abstract `Certificate.valid` | `StructuredCertificate.traceValid` + surface/core soundness |
| Core LTR loop | `compile_ok`, `derives_iff_core_certificate` |
| **JSON-shaped surface WF** | Lean `checkSurface` / `checkCertificatePy`: schema, sizes, step ids, claims, math_established reject; `checkSurface_iff_checkCertificate` |
| **`checkCertificatePy` was bare rfl** | Now `:= checkSurface` (full surface model) |
| **Duplicate meet tables** | Single source `python/scientific_reasoning/meet_tables.py`; Lean `meet_truth_table` |
| **Finding F (Hyp path)** | `hyp_mathVerified_not_established`: declared mathVerified ∧ ¬mathEstablished |

## Irreducible trust boundary (not claimed)

| Boundary | Why it remains |
|---|---|
| **`json.loads` / CPython / OS I/O** | Bytes → AST is outside the Lean object language; surface model starts at the post-parse graph |
| **External math attestation** | Labels never become `mathEstablished` without an out-of-band attestation channel (policy) |

## Test locks

- `tests/test_equivalence_breaks.py` — meet lock, WF rejects, Finding F behavior
- `tests/test_python_lean_differential.py` — LTR ↔ v1 accept path
- `adversarial/test_mutations_v1.py` — forged citations
