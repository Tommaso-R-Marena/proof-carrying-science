/-!
# Compositional refinement of scientific workflows

A scientific workflow is a sequence of stages `S₁ → S₂ → … → Sₙ` (e.g. sequence →
alignment → structure → score; simulation → analysis → statistic; model → inference →
safety evaluator → acceptance claim) whose intermediate data types differ from stage to
stage.  Each stage has

* an abstract **contract** (`Contract α β`: a precondition on inputs and an input/output
  relation — possibly non-deterministic, e.g. "any optimal alignment"), and
* an executable **implementation** (`Impl α β := α → Option β`; `none` is fail-closed
  rejection).

`Refines f K` (partial correctness): whenever the input satisfies the precondition and the
implementation returns an output, the output is related to the input by the contract.
`Total f K`: the implementation returns an output on every admissible input.

Sequential composition of contracts is the standard demonic composition: the composed
precondition requires the first precondition and that *every* admissible intermediate
result satisfies the next precondition; the composed relation is relational composition.

Main results (arbitrary length, heterogeneous types, arbitrary bracketing):

* `seq_refines`, `seq_total` — two-stage composition;
* `pipeline_refines` — if every stage of a pipeline refines its contract, the composed
  implementation refines the composed abstract workflow;
* `pipeline_total` — likewise for totality;
* `seq_pre_of_compatible` — with adjacent-stage compatibility (each stage's
  postcondition establishes the next precondition), the composed precondition is just the
  first stage's.

The file depends only on Lean core.
-/

set_option autoImplicit false

namespace PCS.V2.WorkflowRefinement

/-- Abstract stage contract. -/
structure Contract (α β : Type) where
  pre : α → Prop
  post : α → β → Prop

/-- ExecSECB1�M�r�