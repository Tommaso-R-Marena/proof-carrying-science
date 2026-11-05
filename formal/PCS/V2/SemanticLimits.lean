import PCS.V2.TranslationV2

/-!
# Formal limits of semantic translation checking (Semantic Intelligence v2)

Kernel-checked negative and impossibility results.  Each states something PCS can **not**
conclude, so that no diagnostic or report overclaims.

* `no_countermodel_found_within_bound_is_not_equivalence_proof` — the bounded countermodel
  search can be exhausted (bound 2) on two claims that are *not* equivalent; a size-3
  countermodel exists and is checked.
* `structural_rejection_is_not_semantic_inequivalence` — two claims with different canonical
  normal forms (so v1's semantic gate rejects) are equivalent in every model; v2 certifies
  them with a two-step certificate.
* `intent_gap` — for every candidate claim there is a possible intended meaning it does not
  express; nothing computed from the request alone can exclude that this was the speaker's
  intent.  Human/authorized confirmation is therefore an *external* premise.
* `registry_name_does_not_fix_meaning` — two registry-conforming models that differ only in
  the interpretation of one approved predicate give a well-typed claim different truth
  values: a symbol name, Lean name or digest does not by itself determine meaning; the
  elaboration bridge to the intended model remains an explicit hypothesis.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.Limits

open PCS.V2.Semantic

def limitsRegistry : Registry :=
  ⟨[⟨"Obj", "PCS.Examples.Obj", "PCS/Examples/Limits.lean"⟩],
   [⟨"P", "PCS.Examples.P", .pred ["Obj"], "PCS/Examples/Limits.lean"⟩,
    ⟨"Q", "PCS.Examples.Q", .pred ["Obj"], "PCS/Examples/Limits.lean"⟩]⟩

def vx : Term := .var "x"
def vy : Term := .var "y"
def vz : Term := .var "z"

/-- "There are at least three distinct objects." -/
def atLeastThree : SemanticClaim :=
  ⟨[], [], .quant .ex "x" "Obj" (.quant .ex "y" "Obj" (.quant .ex "z" "Obj"
    (.and (.ne vx vy) (.and (.ne vx vz) (.ne vy vz)))))⟩

/-- "False." -/
def falsum : SemanticClaim := ⟨[], [], .ff⟩

def threeModel : FinModel := ⟨[("Obj", [0, 1, 2])], [], []⟩

theorem search_exhausted_at_two :
    searchCountermodel limitsRegistry atLeastThree falsum 2 100000 = .exhausted := by decide

theorem three_element_countermodel :
    checkCountermodel limitsRegistry atLeastThree falsum (mkWitness atLeastThree falsum threeModel)
      = true := by decide

/-- **Bounded search is not an equivalence proof.** -/
theorem no_countermodel_found_within_bound_is_not_equivalence_proof :
    searchCountermodel limitsRegistry atLeastThree falsum 2 100000 = .exhausted ∧
    (∀ G ∈ searchClass limitsRegistry atLeastThree falsum 2, G.conformsB limitsRegistry = true →
      (atLeastThree.denote G.toModel ρ0 ↔ falsum.denote G.toModel ρ0)) ∧
    ¬ (∀ (M : Model) (ρ : String → M.Dom), M.Conforms limitsRegistry →
      (atLeastThree.denote M ρ ↔ falsum.denote M ρ)) :=
  ⟨search_exhausted_at_two, search_exhausted_complete search_exhausted_at_two,
    countermodel_demonstrates_semantic_difference three_element_countermodel⟩

/-- `∀ x, P x ∧ Q x` -/
def conjPQ : SemanticClaim :=
  ⟨[], [], .quant .all "x" "Obj" (.and (.pred "P" [vx]) (.pred "Q" [vx]))⟩
/-- `¬ ∃ x, ¬ (Q x ∧ P x)` -/
def conjQPneg : SemanticClaim :=
  ⟨[], [], .not (.quant .ex "x" "Obj" (.not (.and (.pred "Q" [vx]) (.pred "P" [vx]))))⟩

def conjCert : EquivCert :=
  ⟨[], [⟨.concl, [], .notEx⟩, ⟨.concl, [0], .dnegElim⟩, ⟨.concl, [0], .andComm⟩]⟩

theorem conjCert_checks : checkCert conjCert conjPQ.normalize conjQPneg.normalize = true := by
  decide

/-- **A structural rejection is not a semantic inequivalence.** -/
theorem structural_rejection_is_not_semantic_inequivalence :
    conjPQ.normalize.equivB conjQPneg.normalize = false ∧
    ∀ (M : Model) (ρ : String → M.Dom), conjPQ.denote M ρ ↔ conjQPneg.denote M ρ :=
  ⟨by decide, translation_certificate_sound conjCert_checks⟩

/-- A one-point model (for refuting `True ↔ False`). -/
def unitModel : Model := ⟨Unit, fun _ _ => True, fun _ _ => (), fun _ _ => True⟩

/-- **The intent gap.**  For every candidate there is a possible intended meaning it does not
    express.  Since a request carries no mathematical object that determines the speaker's
    intent, PCS can only *assume* (via an authorized confirmation receipt) that the selected
    interpretation is the intended one. -/
theorem intent_gap (C : SemanticClaim) :
    ∃ J : SemanticClaim, ¬ ∀ (M : Model) (ρ : String → M.Dom), J.denote M ρ ↔ C.denote M ρ := by
  by_cases h : ∀ (M : Model) (ρ : String → M.Dom),
      (⟨[], [], .tt⟩ : SemanticClaim).denote M ρ ↔ C.denote M ρ
  · refine ⟨⟨[], [], .ff⟩, fun h' => ?_⟩
    have h1 := (h unitModel (fun _ => ())).mp
      (by simp [SemanticClaim.denote, denoteParams, Formula.denote])
    have h2 := (h' unitModel (fun _ => ())).mpr h1
    simp [SemanticClaim.denote, denoteParams, Formula.denote] at h2
  · exact ⟨_, h⟩

def holdsModel (b : Bool) : Model :=
  ⟨Unit, fun _ _ => True, fun _ _ => (), fun p _ => p = "P" → b = true⟩

/-- `∀ x, P x` -/
def allP : SemanticClaim := ⟨[], [], .quant .all "x" "Obj" (.pred "P" [vx])⟩

/-- **A registered name does not fix meaning.**  Two registry-conforming models with the same
    carriers, differing only in the interpretation of the approved predicate `P`, disagree on
    the well-typed closed claim `∀ x, P x`. -/
theorem registry_name_does_not_fix_meaning :
    allP.wellTypedB limitsRegistry = true ∧ allP.freeVars = [] ∧
    (holdsModel true).Conforms limitsRegistry ∧ (holdsModel false).Conforms limitsRegistry ∧
    allP.denote (holdsModel true) (fun _ => ()) ∧ ¬ allP.denote (holdsModel false) (fun _ => ()) := by
  refine ⟨by decide, by decide, ?_, ?_, ?_, ?_⟩
  · intro f e ss r _ _ ds _; exact trivial
  · intro f e ss r _ _ ds _; exact trivial
  · simp [allP, SemanticClaim.denote, denoteParams, Formula.denote, holdsModel]
  · simp [allP, SemanticClaim.denote, denoteParams, Formula.denote, holdsModel]

end PCS.V2.Semantic.Limits
