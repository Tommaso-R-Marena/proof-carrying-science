# Formal status (Lean 4)

## Toolchain

- `lean-toolchain`: `leanprover/lean4:v4.28.0`
- Mathlib pin: `v4.28.0` (lakefile)
- Namespace: `PcsCausal` (project-specific)

## Policy

- No `sorry` / `admit` in promoted theorems.
- No unauthorized axioms.
- Incomplete results are recorded as blockers, not claimed complete.

## Theorem inventory

| Statement | File | Status |
|-----------|------|--------|
| Digraph edges stay in vertex set | `Basic.lean` | proved |
| Mutilation preserves vertices | `Graph.lean` | proved |
| Mutilation edges ⊆ original | `Graph.lean` | proved |
| Intervened nodes have no incoming edges after mutilation | `Graph.lean` | proved |
| FinitePMF event probability nonnegative | `Probability.lean` | proved |
| Conditional masses nonnegative when defined | `Probability.lean` | proved |
| Witness ⇒ target not a function of observation (abstract) | `NonIdent.lean` `nonidentifiable_of_witness` | proved |
| Backdoor soundness for SCMs | `Identification.lean` | **BLOCKER** — open |
| Concrete SCM ↔ Python checker bridge | — | **BLOCKER** — open |

## Axiom audit (recorded 2026-10-18)

`lake build` succeeded (3108 jobs). From `results/lean_axioms.txt`:

| Theorem | Axioms |
|---------|--------|
| `nonidentifiable_of_witness` | **none** |
| `Digraph.mutilate_no_incoming` | `propext`, `Quot.sound` |
| `FinitePMF.eventProb_univ` | `propext`, `Classical.choice`, `Quot.sound` |
| `FinitePMF.condition_zero_event` | `propext`, `Classical.choice`, `Quot.sound` |

No `sorry` / `admit` in promoted theorems.

## Computational complements (not Lean proofs)

- Exact finite backdoor recovery: `tests/test_scm_intervention.py`
- Witness verifier: `tests/test_nonident.py`
- Adversarial graphical suite: `tests/test_identification.py`
