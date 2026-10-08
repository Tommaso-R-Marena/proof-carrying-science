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

/-- Executable stage (fail-closed). -/
abbrev Impl (α β : Type) := α → Option β

variable {α β γ : Type}

/-- Partial-correctness refinement. -/
def Refines (f : Impl α β) (K : Contract α β) : Prop :=
  ∀ a b, K.pre a → f a = some b → K.post a b

/-- Totality on admissible inputs. -/
def Total (f : Impl α β) (K : Contract α β) : Prop :=
  ∀ a, K.pre a → ∃ b, f a = some b

/-- Demonic sequential composition of contracts. -/
def Contract.seq (K₁ : Contract α β) (K₂ : Contract β γ) : Contract α γ :=
  { pre := fun a => K₁.pre a ∧ ∀ b, K₁.post a b → K₂.pre b,
    post := fun a c => ∃ b, K₁.post a b ∧ K₂.post b c }

/-- Sequential composition of implementations. -/
def Impl.seq (f : Impl α β) (g : Impl β γ) : Impl α γ := fun a => (f a).bind g

theorem seq_refines {f : Impl α β} {g : Impl β γ} {K₁ : Contract α β} {K₂ : Contract β γ}
    (hf : Refines f K₁) (hg : Refines g K₂) : Refines (f.seq g) (K₁.seq K₂) := by
  intro a c ⟨hpre, hmid⟩ h
  simp only [Impl.seq, Option.bind_eq_some_iff] at h
  obtain ⟨b, hb, hc⟩ := h
  have hpost := hf a b hpre hb
  exact ⟨b, hpost, hg b c (hmid b hpost) hc⟩

theorem seq_total {f : Impl α β} {g : Impl β γ} {K₁ : Contract α β} {K₂ : Contract β γ}
    (hf : Refines f K₁) (hft : Total f K₁) (hgt : Total g K₂) : Total (f.seq g) (K₁.seq K₂) := by
  intro a ⟨hpre, hmid⟩
  obtain ⟨b, hb⟩ := hft a hpre
  obtain ⟨c, hc⟩ := hgt b (hmid b (hf a b hpre hb))
  exact ⟨c, by simp [Impl.seq, hb, hc]⟩

/-- Adjacent-stage compatibility makes the composed precondition the first one. -/
theorem seq_pre_of_compatible {K₁ : Contract α β} {K₂ : Contract β γ}
    (hcompat : ∀ a b, K₁.pre a → K₁.post a b → K₂.pre b) {a : α} (ha : K₁.pre a) :
    (K₁.seq K₂).pre a :=
  ⟨ha, fun b hb => hcompat a b ha hb⟩

/-! ## Pipelines of arbitrary length -/

/-- A workflow: single stages composed sequentially (arbitrary length and bracketing;
    intermediate types may all differ). -/
inductive Pipeline : Type → Type → Type 1
  | stage {α β : Type} (K : Contract α β) (f : Impl α β) : Pipeline α β
  | seq {α β γ : Type} (p : Pipeline α β) (q : Pipeline β γ) : Pipeline α γ

/-- The composed implementation. -/
def Pipeline.impl : {α β : Type} → Pipeline α β → Impl α β
  | _, _, .stage _ f => f
  | _, _, .seq p q => p.impl.seq q.impl

/-- The composed abstract workflow. -/
def Pipeline.spec : {α β : Type} → Pipeline α β → Contract α β
  | _, _, .stage K _ => K
  | _, _, .seq p q => p.spec.seq q.spec

/-- Every individual stage refines its declared contract. -/
def Pipeline.StagesRefine : {α β : Type} → Pipeline α β → Prop
  | _, _, .stage K f => Refines f K
  | _, _, .seq p q => p.StagesRefine ∧ q.StagesRefine

/-- Every individual stage refines and is total for its declared contract. -/
def Pipeline.StagesTotal : {α β : Type} → Pipeline α β → Prop
  | _, _, .stage K f => Refines f K ∧ Total f K
  | _, _, .seq p q => p.StagesTotal ∧ q.StagesTotal

/-- **Compositional workflow refinement.** -/
theorem pipeline_refines : ∀ {α β : Type} (p : Pipeline α β), p.StagesRefine →
    Refines p.impl p.spec
  | _, _, .stage _ _, h => h
  | _, _, .seq p q, h => seq_refines (pipeline_refines p h.1) (pipeline_refines q h.2)

theorem pipeline_total : ∀ {α β : Type} (p : Pipeline α β), p.StagesTotal →
    Refines p.impl p.spec ∧ Total p.impl p.spec
  | _, _, .stage _ _, h => h
  | _, _, .seq p q, h =>
    have ihp := pipeline_total p h.1
    have ihq := pipeline_total q h.2
    ⟨seq_refines ihp.1 ihq.1, seq_total ihp.1 ihp.2 ihq.2⟩

/-- End-to-end use: an accepted run of the composed workflow on an admissible input
    produces an output related to the input by the composed abstract workflow. -/
theorem pipeline_run_sound {α β : Type} (p : Pipeline α β) (hp : p.StagesRefine) {a : α}
    {b : β} (hpre : p.spec.pre a) (hrun : p.impl a = some b) : p.spec.post a b :=
  pipeline_refines p hp a b hpre hrun

end PCS.V2.WorkflowRefinement
