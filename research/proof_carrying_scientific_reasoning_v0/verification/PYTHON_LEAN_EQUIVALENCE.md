# Python ↔ Lean semantic equivalence (Phase IV)

## What is proved (kernel-checked)

Lean models the **structured schema-v1 checking algorithm** (unique premise IDs, left-to-right step reconstruction, conclusion index) and connects it to the formal calculus:

| Link | Theorem | Module |
|---|---|---|
| Python algorithm = Lean checker | `checkCertificatePy_eq_lean` (rfl) | `PythonCheckerModel` |
| Accept ⇒ Derives | `checkCertificatePy_sound` / `python_accept_implies_derives` | Equivalence |
| Accept ⇒ Entails4 | `python_accept_implies_entails4` | Equivalence |
| Accept ⇒ ¬mathEstablished ∧ unique ids | `checkCertificatePy_*` | PythonCheckerModel |
| Derives (unique ids) ⇒ ∃ accepted cert | `derives_python_complete` | Equivalence |
| Round-trip | `derives_iff_python_certificate` | Equivalence |
| Derives ↔ ProofTerm.interpret | `derives_iff_interpret` | Completeness |
| interpret ⇒ compile accepted by checker | `interpret_checkCertificate` / `compile_ok` | Completeness |

`lake build` reports **no `sorryAx`** on these theorems (only `propext` / `Quot.sound`).

## Trust boundary (explicitly unproved)

- CPython interpreter, bytecode, and GC
- `json.loads` / OS file I/O / schema-v1 JSON surface hardening
- Bit-identical AST between Python source and Lean AST (differential tests cover algorithm behavior)

So: **Python is Lean-checked at the algorithm level**, not at the CPython runtime level.

## Differential harness

`tests/test_python_lean_differential.py` builds hyp / andI / andE1 / andE2 certificates and checks that:

1. Independent checker `check_certificate_v1` accepts them
2. A pure structured LTR reimplementation (Lean `checkStepsLTR` shape) reconstructs the same conclusion formula, support, and declared authority
3. Forged citations are rejected by both paths
