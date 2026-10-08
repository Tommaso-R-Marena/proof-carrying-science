import PCS.V2.Witnesses.AISafety
import PCS.V2.WorkflowRefinement

/-!
# Workflow-refinement witness: trace → risks → cumulative risk → verdict

A three-stage evaluator pipeline with heterogeneous intermediate types
(`List UInt8 → List Nat → Nat → Bool`).  Each stage refines its own small contract;
`pipeline_refines` composes them, and the composed contract yields the per-transition
safety invariant of `PCS.V2.Witnesses.AISafety` for every accepted run.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.WorkflowWitness

open PCS.V2.WorkflowRefinement PCS.V2.Witnesses.AISafety

def riskStage : Pipeline (List UInt8) (List Nat) :=
  .stage ⟨fun _ => True, fun tr rs => rs = tr.map risk⟩ (fun tr => some (tr.map risk))

def sumStage : Pipeline (List Nat) Nat :=
  .stage ⟨fun _ => True, fun rs s => s = rs.sum⟩ (fun rs => some rs.sum)

/-- Fail-closed verdict: only `true` is ever produced, and only within budget. -/
def verdictStage (budget : Nat) : Pipeline Nat Bool :=
  .stage ⟨fun _ => True, fun s v => v = true → s ≤ budget⟩
    (fun s => if s ≤ budget then some true else none)

def evaluator (budget : Nat) : Pipeline (List UInt8) Bool :=
  .seq (.seq riskStage sumStage) (verdictStage budget)

theorem evaluator_stages (budget : Nat) : (evaluator budget).StagesRefine := by
  refine ⟨⟨?_, ?_⟩, ?_⟩
  · intro tr rs _ h; cases h; rfl
  · intro rs s _ h; cases h; rfl
  · intro s v _ h _
    simp only at h
    split at h
    · assumption
    · cases h

/-- An accepted run of the composed evaluator certifies the per-transition invariant. -/
theorem evaluator_sound (budget : Nat) (tr : List UInt8)
    (h : (evaluator budget).impl tr = some true) :
    ∀ k ≤ tr.length, stateAfter (tr.take k) ≤ budget := by
  have hpre : (evaluator budget).spec.pre tr :=
    ⟨⟨trivial, fun _ _ => trivial⟩, fun _ _ => trivial⟩
  obtaid�PЀL@��^����