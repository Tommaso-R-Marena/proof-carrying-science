# PCS Lean proof environment v1

`PCSProofProbe.lean` uses Lean TermElabM/TacticM to serialize actual goals, locals and Expr trees, including type/universe information. `PCSProofWorker.lean` starts each request from one fixed imported environment. The unsafe startup only initializes the interpreter environment; it is not proof evidence. Python accepts typed closed actions, pins compiled module bytes, drops credentials, bounds replay length/heartbeats/output/time and uses Linux prlimit. Final accepted proofs run in a fresh Lean process and audit axioms. The elementary core environment is pinned to Lean 4.28; Mathlib remains separately pinned v4.28.0 but is not claimed as an instantiated retrieval backend.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.

## Expanded implementation v2

V2 retrieves genuinely quantified local premises and their conjunction projections from structured Expr objects. Nine actual actions establish injective function composition and separately held-out predicate transitivity. The public receiver accepts only this controlled typed grammar; errors and resource exhaustion remain unresolved outcomes.

See [v2 reproducible artifacts](../research/lean-learning-v2/SHA256.json).
