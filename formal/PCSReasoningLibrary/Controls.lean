import PCSReasoningLibrary.Separation

/-!
# Executed controls for the reasoning library

Positive and adversarial controls, closed by ordinary kernel evaluation.
-/

namespace PCSReasoningLibrary.Controls

open PCSReasoningLibrary Separation

def A : Fm := .atom 0
def B : Fm := .atom 1

/-! ### `A ∨ B → A`: one closed branch never authorises the theorem -/

/-- A disjunction elimination whose second branch tries to reuse the first branch's
hypothesis: rejected (the `B` branch has no proof of `A`). -/
def oneBranch : Pf := .lam (.or A B) (.orE (.hyp (.or A B)) A B (.hyp A) (.hyp A))

example : infer [] [] oneBranch = none := by decide

/-- The correct two-branch proof of `A ∨ B → B ∨ A` is accepted. -/
def swapPf : Pf :=
  .lam (.or A B) (.orE (.hyp (.or A B)) A B (.orR B (.hyp A)) (.orL A (.hyp B)))

example : infer [] [] swapPf = some (.imp (.or A B) (.or B A)) := by decide

/-! ### Unverified macro admission and cyclic dependencies -/

/-- A model proposes `A → B` as a "lemma" with a bogus proof. -/
def bogus : Entry :=
  { name := "bogus", stmt := .imp A B, proof := .lam A (.hyp A), deps := [], cost := 2,
    foundation := "PCS" }

example : admittedB "PCS" [bogus] = false := by decide

/-- An entry citing itself (a dependency cycle) is rejected. -/
def selfCite : Entry :=
  { name := "cyc", stmt := .imp A A, proof := .lem 0 [], deps := [0], cost := 1,
    foundation := "PCS" }

example : admittedB "PCS" [selfCite] = false := by decide

/-- Two mutually citing entries: rejected. -/
def cycA : Entry := { selfCite with name := "cycA", proof := .lem 1 [], deps := [1] }
def cycB : Entry := { selfCite with name := "cycB", proof := .lem 0 [], deps := [0] }

example : admittedB "PCS" [cycA, cycB] = false := by decide

/-- An entry citing an undeclared dependency is rejected even if the proof checks. -/
def idEntry : Entry :=
  { name := "id", stmt := .imp A A, proof := .lam A (.hyp A), deps := [], cost := 2,
    foundation := "PCS" }
def undeclared : Entry :=
  { name := "uses_id", stmt := .imp A A, proof := .lem 0 [], deps := [], cost := 1,
    foundation := "PCS" }

example : admittedB "PCS" [idEntry] = true := by decide
example : admittedB "PCS" [idEntry, undeclared] = false := by decide
example : admittedB "PCS" [idEntry, { undeclared with deps := [0] }] = true := by decide

/-! ### Changed foundation / altered checker revision invalidates provenance -/

example : admittedB "PCS" (sharedLib "PCS") = true := sharedLib_admitted "PCS"
example : admittedB "PCS-altered" (sharedLib "PCS") = false := by decide

/-! ### Search: an adversarial policy cannot manufacture acceptance -/

/-- Policy proposing only wrong proofs. -/
def badPolicy : Nat → List Pf := fun _ => [.hyp B, oneBranch, .topI]

example : search [] [] (.imp (.or A B) (.or B A)) [] [] badPolicy 3 = none := by decide

/-- With a helpful policy the shared proof is accepted in round 1. -/
example : search (stmts (sharedLib "PCS")) (famCtx 6) (.atom 6) [] [] (fun _ => [sharedProof 6]) 1 =
    some (sharedProof 6) := by decide

/-- The fair fallback finds `A → A` regardless of the adversarial policy. -/
example : search [] [] (.imp A A) [A] [.hyp A] badPolicy 2 = some (.lam A (.hyp A)) := by decide

/-! ### Reuse family: small and larger instances -/

example : baselineWork 10 = 2047 := by decide
example : sharedTotal 10 = 33 + 50 + 740 := by rw [sharedTotal_eq]
example : (bc (famCtx 4) 5 (.atom 4)).1 = some (tree 4) := by decide
example : infer [dmp] (famCtx 40) (sharedProof 40) = some (.atom 40) := by decide +kernel
example : sharedTotal 40 < baselineWork 40 :=
  certified_reuse_complexity_separation.2.2.2.2.2.2 40 (by decide)

/-! ### Research plan: failed dependencies stay unavailable -/

def planOK : List Node :=
  [⟨.imp A A, [], .lam A (.hyp A)⟩,
   ⟨.and (.imp A A) (.imp A A), [0], .andI (.lem 0 []) (.lem 0 [])⟩]

def planBad : List Node :=
  [⟨.imp A B, [], .lam A (.hyp A)⟩,
   ⟨.and (.imp A B) (.imp A B), [0], .andI (.lem 0 []) (.lem 0 [])⟩]

example : (execPlan planOK).map (fun s => match s with | .verified _ => true | _ => false) =
    [true, true] := by decide
example : execPlan planBad = [.failed, .blocked] := by decide

end PCSReasoningLibrary.Controls
