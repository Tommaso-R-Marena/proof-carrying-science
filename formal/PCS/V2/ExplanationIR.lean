import PCS.V2.SemanticIR

/-!
# Explanation IR: the certified structural half of Lean → human explanation

Given a (checked) structured claim, `toExplanation R c` derives an **Explanation IR**
deterministically and structurally.  It records

* the claim's explicitly bound variables (subject) and their sorts,
* the assumptions and the main conclusion as explanation trees (`ExplNode`) whose
  constructors name the logical role (`forEvery`, `thereExists`, `negation`, `allOf`,
  `anyOf`, `ifThen`, `atom`, `equal`, `notEqual`, …),
* every quantifier in syntactic order, the number of negations,
* the referenced definitions and sorts with their grounding (Lean name, signature,
  provenance) taken from the approved registry,
* the trust/authority boundary and an explicit list of what is **not** established.

Results:

* `explanation_roundtrip` — the claim is recovered *exactly* from its Explanation IR
  (`(toExplanation R c).toClaim = c`); hence the IR loses no supported meaning.
* `explanationIR_preserves_semantics` — the Explanation IR has its *own* compositional
  semantics (`ExplanationIR.denote`, over `ExplNode.denote`), and it coincides with the
  claim's denotation in every model and valuation.
* `explanation_quantifiers_faithful`, `explanation_negations_faithful`,
  `explanation_references_grounded`, `explanation_references_complete` — the summary
  fields are exactly the corresponding structural features of the claim.

**Not certified.**  `renderLiteral` turns the IR into deterministic literal English, and a
future (LLM) stylistic renderer may produce beginner/technical prose from the IR.  No
theorem here states that any English string means the claim; prose is presentation only.
`renderLean` is the deterministic Lean-source rendering of a claim used to bind
elaboration and proof receipts to the candidate; its meaning inside Lean is an explicit
external bridge (see `PCS.V2.TranslationAuthority`).
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-- Explanation trees: one constructor per logical role. -/
inductive ExplNode where
  | always
  | never
  | atom (symbol : String) (leanName : String) (args : List Term)
  | equal (a b : Term)
  | notEqual (a b : Term)
  | negation (n : ExplNode)
  | allOf (a b : ExplNode)
  | anyOf (a b : ExplNode)
  | ifThen (premise conclusion : ExplNode)
  | forEvery (var : String) (sort : SortId) (body : ExplNode)
  | thereExists (var : String) (sort : SortId) (body : ExplNode)
  | unsupported (tag : String)
  deriving Repr, DecidableEq, Inhabited

/-- Grounded Lean name of a symbol (marked if unresolved; never accepted anyway). -/
def leanNameOf (R : Registry) (f : String) : String :=
  match R.resolve f with
  | some e => e.leanName
  | none => "?unresolved:" ++ f

/-- Structural derivation of an explanation tree. -/
def toNode (R : Registry) : Formula → ExplNode
  | .tt => .always
  | .ff => .never
  | .pred p args => .atom p (leanNameOf R p) args
  | .eq a b => .equal a b
  | .ne a b => .notEqual a b
  | .not φ => .negation (toNode R φ)
  | .and φ ψ => .allOf (toNode R φ) (toNode R ψ)
  | .or φ ψ => .anyOf (toNode R φ) (toNode R ψ)
  | .imp φ ψ => .ifThen (toNode R φ) (toNode R ψ)
  | .quant .all x s φ => .forEvery x s (toNode R φ)
  | .quant .ex x s φ => .thereExists x s (toNode R φ)
  | .unsupported t => .unsupported t

/-- Reading an explanation tree back as a formula. -/
def ExplNode.toFormula : ExplNode → Formula
  | .always => .tt
  | .never => .ff
  | .atom p _ args => .pred p args
  | .equal a b => .eq a b
  | .notEqual a b => .ne a b
  | .negation n => .not n.toFormula
  | .allOf a b => .and a.toFormula b.toFormula
  | .anyOf a b => .or a.toFormula b.toFormula
  | .ifThen a b => .imp a.toFormula b.toFormula
  | .forEvery x s n => .quant .all x s n.toFormula
  | .thereExists x s n => .quant .ex x s n.toFormula
  | .unsupported t => .unsupported t

theorem toNode_roundtrip (R : Registry) : ∀ φ : Formula, (toNode R φ).toFormula = φ
  | .tt | .ff | .pred _ _ | .eq _ _ | .ne _ _ | .unsupported _ => rfl
  | .not φ => by simp [toNode, ExplNode.toFormula, toNode_roundtrip R φ]
  | .and φ ψ | .or φ ψ | .imp φ ψ => by
    simp [toNode, ExplNode.toFormula, toNode_roundtrip R φ, toNode_roundtrip R ψ]
  | .quant .all _ _ φ | .quant .ex _ _ φ => by
    simp [toNode, ExplNode.toFormula, toNode_roundtrip R φ]

/-- Independent compositional semantics of explanation trees. -/
def ExplNode.denote (M : Model) : (String → M.Dom) → ExplNode → Prop
  | _, .always => True
  | _, .never => False
  | ρ, .atom p _ args => M.pred p (args.map (Term.denote M ρ))
  | ρ, .equal a b => Term.denote M ρ a = Term.denote M ρ b
  | ρ, .notEqual a b => ¬ Term.denote M ρ a = Term.denote M ρ b
  | ρ, .negation n => ¬ ExplNode.denote M ρ n
  | ρ, .allOf a b => ExplNode.denote M ρ a ∧ ExplNode.denote M ρ b
  | ρ, .anyOf a b => ExplNode.denote M ρ a ∨ ExplNode.denote M ρ b
  | ρ, .ifThen a b => ExplNode.denote M ρ a → ExplNode.denote M ρ b
  | ρ, .forEvery x s n => ∀ d, M.HasSort s d → ExplNode.denote M (update ρ x d) n
  | ρ, .thereExists x s n => ∃ d, M.HasSort s d ∧ ExplNode.denote M (update ρ x d) n
  | _, .unsupported _ => False

theorem toNode_denote (R : Registry) (M : Model) :
    ∀ (φ : Formula) (ρ : String → M.Dom), (toNode R φ).denote M ρ ↔ φ.denote M ρ
  | .tt, _ | .ff, _ | .eq _ _, _ | .ne _ _, _ | .unsupported _, _ => Iff.rfl
  | .pred p args, ρ => by simp [toNode, ExplNode.denote, Formula.denote, Term.denoteList_eq_map]
  | .not φ, ρ => not_congr (toNode_denote R M φ ρ)
  | .and φ ψ, ρ => and_congr (toNode_denote R M φ ρ) (toNode_denote R M ψ ρ)
  | .or φ ψ, ρ => or_congr (toNode_denote R M φ ρ) (toNode_denote R M ψ ρ)
  | .imp φ ψ, ρ => imp_congr (toNode_denote R M φ ρ) (toNode_denote R M ψ ρ)
  | .quant .all x s φ, ρ =>
    forall_congr' fun d => imp_congr Iff.rfl (toNode_denote R M φ (update ρ x d))
  | .quant .ex x s φ, ρ =>
    exists_congr fun d => and_congr Iff.rfl (toNode_denote R M φ (update ρ x d))

/-! ## Structural summaries -/

/-- Quantifiers of a formula in syntactic (pre-)order. -/
def Formula.quantifiers : Formula → List (Quant × String × SortId)
  | .tt | .ff | .unsupported _ | .pred _ _ | .eq _ _ | .ne _ _ => []
  | .not φ => Formula.quantifiers φ
  | .quant q x s φ => (q, x, s) :: Formula.quantifiers φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.quantifiers φ ++ Formula.quantifiers ψ

/-- Number of explicit negations (`¬` and `≠`). -/
def Formula.negations : Formula → Nat
  | .tt | .ff | .unsupported _ | .pred _ _ | .eq _ _ => 0
  | .ne _ _ => 1
  | .not φ => Formula.negations φ + 1
  | .quant _ _ _ φ => Formula.negations φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.negations φ + Formula.negations ψ

/-- Order-preserving duplicate removal. -/
def uniq {α : Type} [DecidableEq α] : List α → List α
  | [] => []
  | a :: as => if as.contains a then uniq as else a :: uniq as

theorem mem_uniq {α : Type} [DecidableEq α] {a : α} : ∀ {l : List α}, a ∈ uniq l ↔ a ∈ l
  | [] => Iff.rfl
  | b :: bs => by
    unfold uniq
    by_cases h : bs.contains b
    · simp only [h, if_true, mem_uniq, List.mem_cons]
      constructor
      · exact Or.inr
      · rintro (rfl | h')
        · simpa using h
        · exact h'
    · have h' : b ∉ bs := by simpa using h
      simp [h', mem_uniq]

/-- Fixed statement of the trust/authority boundary (part of every explanation). -/
def trustBoundaryStatement : List String :=
  [ "Kernel-checked in Lean: the PCS semantic translation checker is sound with respect to " ++
      "the compositional semantics of the supported fragment (PCS.V2.TranslationChecker).",
    "Kernel-checked in Lean: this explanation is derived structurally from the checked claim " ++
      "and has the same meaning (explanationIR_preserves_semantics).",
    "External (receipt-verified, trusted verifier keys): human or authorized confirmation of " ++
      "the selected interpretation; Lean elaboration of the rendered source; Lean kernel " ++
      "proof of the rendered statement.",
    "External (trusted runtime): parsing/serialization of JSON inputs, the compiled checker " ++
      "binary, file IO, and the Python pipeline that invokes it." ]

/-- What an explanation never claims. -/
def notEstablishedStatement : List String :=
  [ "That the selected structured interpretation is what the speaker actually intended " ++
      "(only that an authorized process confirmed it).",
    "That the natural-language text has a unique meaning.",
    "That any English rendering of this explanation is semantically certified.",
    "That the assumptions hold in the real world, or that empirical premises are true.",
    "That the proposing model is correct or calibrated." ]

/-- **The Explanation IR.** -/
structure ExplanationIR where
  variables : List Binder
  assumptions : List ExplNode
  conclusion : ExplNode
  quantifiers : List (Quant × String × SortId)
  negations : Nat
  references : List SymbolEntry
  sortReferences : List SortEntry
  trustBoundary : List String
  notEstablished : List String
  deriving Repr, DecidableEq, Inhabited

/-- All quantifiers of a claim: parameters (read universally) then those inside the
    assumptions and the conclusion. -/
def SemanticClaim.quantifiers (c : SemanticClaim) : List (Quant × String × SortId) :=
  c.params.map (fun b => (Quant.all, b.name, b.sort)) ++
    c.assumptions.flatMap Formula.quantifiers ++ Formula.quantifiers c.conclusion

/-- All negations of a claim. -/
def SemanticClaim.negations (c : SemanticClaim) : Nat :=
  (c.assumptions.map Formula.negations).foldl (· + ·) 0 + Formula.negations c.conclusion

/-- Sorts mentioned by a claim's binders. -/
def Formula.binderSorts : Formula → List SortId
  | .tt | .ff | .unsupported _ | .pred _ _ | .eq _ _ | .ne _ _ => []
  | .not φ => Formula.binderSorts φ
  | .quant _ _ s φ => s :: Formula.binderSorts φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.binderSorts φ ++ Formula.binderSorts ψ

def SemanticClaim.sorts (c : SemanticClaim) : List SortId :=
  c.params.map (·.sort) ++ c.assumptions.flatMap Formula.binderSorts ++
    Formula.binderSorts c.conclusion

/-- **Deterministic structural derivation of the Explanation IR.** -/
def toExplanation (R : Registry) (c : SemanticClaim) : ExplanationIR :=
  { variables := c.params,
    assumptions := c.assumptions.map (toNode R),
    conclusion := toNode R c.conclusion,
    quantifiers := c.quantifiers,
    negations := c.negations,
    references := (uniq c.symbols).filterMap R.resolve,
    sortReferences := (uniq c.sorts).filterMap R.resolveSort,
    trustBoundary := trustBoundaryStatement,
    notEstablished := notEstablishedStatement }

/-- Reading an Explanation IR back as a structured claim. -/
def ExplanationIR.toClaim (e : ExplanationIR) : SemanticClaim :=
  { params := e.variables,
    assumptions := e.assumptions.map ExplNode.toFormula,
    conclusion := e.conclusion.toFormula }

/-- Semantics of an Explanation IR (its own trees, closed over its variables). -/
def ExplanationIR.denote (M : Model) (ρ : String → M.Dom) (e : ExplanationIR) : Prop :=
  denoteParams M e.variables ρ (fun ρ' =>
    (∀ a ∈ e.assumptions, ExplNode.denote M ρ' a) → ExplNode.denote M ρ' e.conclusion)

/-- **Exact structural round trip** claim → Explanation IR → claim. -/
theorem explanation_roundtrip (R : Registry) (c : SemanticClaim) :
    (toExplanation R c).toClaim = c := by
  cases c with
  | mk ps as cl =>
    simp only [toExplanation, ExplanationIR.toClaim, List.map_map, toNode_roundtrip]
    congr
    conv => rhs; rw [← List.map_id as]
    apply List.map_congr_left
    intro a _
    simp [toNode_roundtrip]

theorem denoteParams_congr (M : Model) :
    ∀ (bs : List Binder) (ρ : String → M.Dom) (k k' : (String → M.Dom) → Prop),
      (∀ ρ', k ρ' ↔ k' ρ') → (denoteParams M bs ρ k ↔ denoteParams M bs ρ k')
  | [], ρ, _, _, h => h ρ
  | _ :: bs, _, k, k', h =>
    forall_congr' fun _ => imp_congr Iff.rfl (denoteParams_congr M bs _ k k' h)

/-- **The Explanation IR preserves the supported meaning**: its own semantics coincides
    with the claim's denotation in every model and valuation. -/
theorem explanationIR_preserves_semantics (R : Registry) (M : Model) (ρ : String → M.Dom)
    (c : SemanticClaim) : (toExplanation R c).denote M ρ ↔ c.denote M ρ := by
  unfold ExplanationIR.denote SemanticClaim.denote toExplanation
  simp only
  apply denoteParams_congr
  intro ρ'
  apply imp_congr
  · constructor
    · intro h a ha; exact (toNode_denote R M a ρ').mp (h _ (List.mem_map.mpr ⟨a, ha, rfl⟩))
    · intro h n hn
      obtain ⟨a, ha, rfl⟩ := List.mem_map.mp hn
      exact (toNode_denote R M a ρ').mpr (h a ha)
  · exact toNode_denote R M c.conclusion ρ'

theorem explanation_quantifiers_faithful (R : Registry) (c : SemanticClaim) :
    (toExplanation R c).quantifiers = c.quantifiers := rfl

theorem explanation_negations_faithful (R : Registry) (c : SemanticClaim) :
    (toExplanation R c).negations = c.negations := rfl

/-- Every referenced definition is an approved registry entry for a symbol of the claim,
    and it is the *unique* resolution of that symbol. -/
theorem explanation_references_grounded (R : Registry) (c : SemanticClaim) :
    ∀ e ∈ (toExplanation R c).references, e.id ∈ c.symbols ∧ R.resolve e.id = some e ∧
      e ∈ R.symbols := by
  intro e he
  simp only [toExplanation, List.mem_filterMap, mem_uniq] at he
  obtain ⟨f, hf, hr⟩ := he
  unfold Registry.resolve at hr
  split at hr
  · rename_i e' hent
    cases hr
    have hmem : e ∈ R.entries f := by rw [hent]; exact List.mem_singleton_self e
    simp only [Registry.entries, List.mem_filter, beq_iff_eq] at hmem
    refine ⟨hmem.2 ▸ hf, ?_, hmem.1⟩
    rw [hmem.2]; unfold Registry.resolve; rw [hent]
  · cases hr

/-- Every uniquely resolved symbol of the claim is listed among the references. -/
theorem explanation_references_complete (R : Registry) (c : SemanticClaim) :
    ∀ f ∈ c.symbols, ∀ e, R.resolve f = some e → e ∈ (toExplanation R c).references := by
  intro f hf e he
  simp only [toExplanation, List.mem_filterMap, mem_uniq]
  exact ⟨f, hf, he⟩

/-! ## Deterministic renderers (presentation only; not semantically certified) -/

mutual
/-- Lean-source rendering of a term. -/
def renderTermLean (R : Registry) : Term → String
  | .var x => x
  | .app f [] => leanNameOf R f
  | .app f (a :: as) => "(" ++ leanNameOf R f ++ renderTermsLean R (a :: as) ++ ")"
def renderTermsLean (R : Registry) : List Term → String
  | [] => ""
  | t :: ts => " " ++ renderTermLean R t ++ renderTermsLean R ts
end

/-- Lean type name of a sort. -/
def leanTypeOf (R : Registry) (s : SortId) : String :=
  match R.resolveSort s with
  | some e => e.leanType
  | none => "?unresolved_sort:" ++ s

/-- Lean-source rendering of a formula (fully parenthesised). -/
def renderLean (R : Registry) : Formula → String
  | .tt => "True"
  | .ff => "False"
  | .pred p [] => leanNameOf R p
  | .pred p (a :: as) => "(" ++ leanNameOf R p ++ renderTermsLean R (a :: as) ++ ")"
  | .eq a b => "(" ++ renderTermLean R a ++ " = " ++ renderTermLean R b ++ ")"
  | .ne a b => "(" ++ renderTermLean R a ++ " ≠ " ++ renderTermLean R b ++ ")"
  | .not φ => "(¬ " ++ renderLean R φ ++ ")"
  | .and φ ψ => "(" ++ renderLean R φ ++ " ∧ " ++ renderLean R ψ ++ ")"
  | .or φ ψ => "(" ++ renderLean R φ ++ " ∨ " ++ renderLean R ψ ++ ")"
  | .imp φ ψ => "(" ++ renderLean R φ ++ " → " ++ renderLean R ψ ++ ")"
  | .quant .all x s φ => "(∀ (" ++ x ++ " : " ++ leanTypeOf R s ++ "), " ++ renderLean R φ ++ ")"
  | .quant .ex x s φ => "(∃ (" ++ x ++ " : " ++ leanTypeOf R s ++ "), " ++ renderLean R φ ++ ")"
  | .unsupported t => "(PCS_UNSUPPORTED_CONSTRUCT \"" ++ t ++ "\")"

/-- Lean-source rendering of a claim: `∀ (x : T) …, A₁ → … → C`. -/
def renderClaimLean (R : Registry) (c : SemanticClaim) : String :=
  let body := c.assumptions.foldr (fun a acc => renderLean R a ++ " → " ++ acc)
    (renderLean R c.conclusion)
  match c.params with
  | [] => body
  | ps => "∀" ++ String.join (ps.map (fun b => " (" ++ b.name ++ " : " ++ leanTypeOf R b.sort ++ ")")) ++
      ", " ++ body

mutual
/-- Literal English rendering of a term. -/
def renderTermEn : Term → String
  | .var x => x
  | .app f [] => f
  | .app f (a :: as) => f ++ "(" ++ renderTermsEn (a :: as) ++ ")"
def renderTermsEn : List Term → String
  | [] => ""
  | [t] => renderTermEn t
  | t :: ts => renderTermEn t ++ ", " ++ renderTermsEn ts
end

/-- Literal English rendering of an explanation tree. -/
def ExplNode.renderEn : ExplNode → String
  | .always => "true"
  | .never => "false"
  | .atom p ln [] => p ++ " [" ++ ln ++ "] holds"
  | .atom p ln (a :: as) => p ++ " [" ++ ln ++ "] holds of (" ++ renderTermsEn (a :: as) ++ ")"
  | .equal a b => renderTermEn a ++ " equals " ++ renderTermEn b
  | .notEqual a b => renderTermEn a ++ " does not equal " ++ renderTermEn b
  | .negation n => "it is not the case that (" ++ n.renderEn ++ ")"
  | .allOf a b => "both (" ++ a.renderEn ++ ") and (" ++ b.renderEn ++ ")"
  | .anyOf a b => "at least one of (" ++ a.renderEn ++ ") or (" ++ b.renderEn ++ ")"
  | .ifThen a b => "if (" ++ a.renderEn ++ ") then (" ++ b.renderEn ++ ")"
  | .forEvery x s n => "for every " ++ x ++ " of sort " ++ s ++ ", " ++ n.renderEn
  | .thereExists x s n => "there exists " ++ x ++ " of sort " ++ s ++ " such that " ++ n.renderEn
  | .unsupported t => "[unsupported construct: " ++ t ++ "]"

/-- Deterministic literal English rendering of an Explanation IR (presentation only). -/
def ExplanationIR.renderLiteral (e : ExplanationIR) : String :=
  let vars := String.intercalate ", " (e.variables.map (fun b => b.name ++ " of sort " ++ b.sort))
  let asms := e.assumptions.map ExplNode.renderEn
  let head := if e.variables.isEmpty then "" else "For every " ++ vars ++ ": "
  let mid := if asms.isEmpty then "" else
    "assuming " ++ String.intercalate "; and " asms ++ ", it follows that "
  head ++ mid ++ e.conclusion.renderEn ++ "."

end PCS.V2.Semantic
