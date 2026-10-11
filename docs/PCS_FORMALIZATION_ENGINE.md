# PCS controlled formalization v1

The grammar parses typed variables, scope, mathematical operators, nested quantification and constrained function terms. It generates typed IR and receiver-owned Lean. Mixed and/or groupings expose alternative candidates. Unsupported types/names and shadowing are rejected. A trained 4,452-parameter English encoder ranks domain interpretations; it does not replace deterministic checks or certify intended meaning. Eight independent typed meaning labels elaborate correctly; three actual checked declarations round-trip to structured explanations. General Mathlib, English generation, implicit assumptions, universes, human fidelity and pretrained comparisons remain open.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.

## Expanded implementation v2

V2 adds explicit Nat→Nat injectivity/composition lowering and Nat→Prop predicate quantification, with ten independent meaning labels and four actual checked declarations explained. Reserved Lean/type/constant binder names are rejected. Chained implication follows documented right association; parentheses determine scope. The language classifier is reused, not trained to generate unrestricted Lean.

See [v2 reproducible artifacts](../research/lean-learning-v2/SHA256.json).

## Checked mathematical reuse and verified feedback

The existing typed Nat/Int/Prop/function grammar is preserved. New proof capabilities operate on its existing quantified/order expressions and retain the original English, selected IR, exact Lean type and explicit semantic-grounding boundary. [Working mathematical examples](PCS_CHECKED_REUSE_REPORT.md).

## October 11 induction and grounded abstraction update

See the [consolidated executable results and limitations](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md#induction-grounded-abstraction-and-bridge-builder--october-11-2026) and [complete prospective experiment](../research/induction-abstraction-v2/REPORT.md). This supersedes earlier absence of implemented list/Nat induction, trainable binding graphs, independently checked state-derived lemma admission and sequential induction RL. It does not supersede the documented limits on unrestricted English, autonomous discovery or runtime refinement.

NatList, nil/cons/append/length/reverse and Nat.succ have explicit typed IR, bounded controlled-English parsing, Lean lowering and structured explanation. Outer-universal canonicalization preserves scope and strengthens the duplicate firewall. These extensions are tested, not covered by the earlier source-bound parser proof.
