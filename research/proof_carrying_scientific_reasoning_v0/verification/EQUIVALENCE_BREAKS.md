# Where Python ↔ Lean equivalence breaks (and what we did)

Living catalog for Phase IV+. Exclusive path only.

## Fixed / kernel-separated

| Break | Symptom | Fix |
|---|---|---|
| **Classical `Entails` explosion** | Inconsistent `demoΓ` classically entails atom 99 | Proved `classical_entails_atom99_demoΓ` **and** `¬ Entails4 demoΓ (atom 99)`. Do not advertise paraconsistency via classical `Entails`. |
| **Finding D abstract `Certificate.valid`** | Steps ignored | Prefer `StructuredCertificate.traceValid` (`∃ j, checkCertificate = some j`) + `traceValid_implies_derives` / `traceValid_implies_entails4`. |
| **Core LTR loop** | hyp/andI/andE reconstruction | Covered by `compile_ok`, `derives_iff_python_certificate`, differential harness. |

## Still broken / trust-boundary (not claimed)

| Break | Where it fails | Status |
|---|---|---|
| **JSON surface ≠ Lean AST** | `check_certificate_v1.parse_certificate_json`, unknown keys, bool-as-int, size limits, `step.id == index` | Unproved. Lean starts at `StructuredCertificate`. Differential tests cover WF rejects on Python only. |
| **`checkCertificatePy = checkCertificate` is rfl** | `PythonCheckerModel.lean` | Models the **structured algorithm**, not CPython/`json.loads`. Documented in `PYTHON_LEAN_EQUIVALENCE.md`. |
| **Duplicate `meet` tables** | `v1.RANK/TIE` vs `authority._RANK/_TIE` | Independent checker must not import evaluator libs; **exhaustive cross-check test** must keep them locked. |
| **Declared `mathVerified`** | Hyp copies declared authority; `math_established` forced false | Finding F — policy. Accept ≠ math attestation. |
| **No JSON→`StructuredCertificate` decoder in Lean** | Production path is Python `check()` | Future: Lean decoder + `decode_ok → checkCertificate`. |

## Test locks

- `tests/test_equivalence_breaks.py` — classical vs Entails4 story in Python terms; meet lock; WF rejects; andE-on-atom reject.
- `tests/test_python_lean_differential.py` — accept-path LTR ↔ v1.
- `adversarial/test_mutations_v1.py` — forged citations / claim escalation.
