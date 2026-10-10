# PCS controlled formalization v1

The grammar parses typed variables, scope, mathematical operators, nested quantification and constrained function terms. It generates typed IR and receiver-owned Lean. Mixed and/or groupings expose alternative candidates. Unsupported types/names and shadowing are rejected. A trained 4,452-parameter English encoder ranks domain interpretations; it does not replace deterministic checks or certify intended meaning. Eight independent typed meaning labels elaborate correctly; three actual checked declarations round-trip to structured explanations. General Mathlib, English generation, implicit assumptions, universes, human fidelity and pretrained comparisons remain open.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.

## Expanded implementation v2

V2 adds explicit Nat→Nat injectivity/composition lowering and Nat→Prop predicate quantification, with ten independent meaning labels and four actual checked declarations explained. Reserved Lean/type/constant binder names are rejected. Chained implication follows documented right association; parentheses determine scope. The language classifier is reused, not trained to generate unrestricted Lean.

See [v2 reproducible artifacts](../research/lean-learning-v2/SHA256.json).
