# PCS Lean proof environment v1

`PCSProofProbe.lean` uses Lean TermElabM/TacticM to serialize actual goals, locals and Expr trees, including type/universe information. `PCSProofWorker.lean` starts each request from one fixed imported environment. The unsafe startup only initializes the interpreter environment; it is not proof evidence. Python accepts typed closed actions, pins compiled module bytes, drops credentials, bounds replay length/heartbeats/output/time and uses Linux prlimit. Final accepted proofs run in a fresh Lean process and audit axioms. The elementary core environment is pinned to Lean 4.28; Mathlib remains separately pinned v4.28.0 but is not claimed as an instantiated retrieval backend.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.

## Expanded implementation v2

V2 retrieves genuinely quantified local premises and their conjunction projections from structured Expr objects. Nine actual actions establish injective function composition and separately held-out predicate transitivity. The public receiver accepts only this controlled typed grammar; errors and resource exhaustion remain unresolved outcomes.

See [v2 reproducible artifacts](../research/lean-learning-v2/SHA256.json).

## Checked action coverage for negation and case splits

The receiver now offers introductions for negated goals, applications of negated local premises, and rewrites using equality projections from conjunctions. Disjunction elimination can assign a fresh accessible name to each branch using the constrained `cases` argument `hypothesis as hN`. The renderer emits `rcases hypothesis with hN | hN`; names are bounded identifiers, never arbitrary tactic text. Existing action encodings remain accepted. Fresh names are chosen from actual local declarations rather than their count.

The two branches remain separate Lean obligations. A regression closes the first branch of `A ∨ B → A` and requires both an open remaining goal and rejection by the independent final verifier. Additional regressions prove equality transitivity with zero, disjunction absorption and contraposition using both symbolic search and the existing pinned graph checkpoint. Invalid names and tactic injection are rejected. Run `PCS_REQUIRE_PROVER=1 python -m pytest -q tests/test_lean_learning_loop.py` with the pinned environment.

These are action-generation improvements, not training gains. Earlier frozen model/RL benchmarks retain their original source and results; their reported solve rates are not recomputed or relabeled. No new model kind, checkpoint promotion, Lean axiom, theorem weakening or scientific authority is introduced.
