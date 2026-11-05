/-!
# PCS Semantic Translation Contract v1 — the typed semantic fragment and its meaning

This file defines the **structured semantic representation** shared by

* the *human-selected interpretation* of a natural-language claim, and
* the *formal translation candidate* that PCS is asked to accept,

together with an **independent, compositional denotational semantics** for it.  Nothing
here mentions the translation checker: the meaning of a claim is defined once, by
structural recursion, against an arbitrary many-sorted first-order structure (`Model`).
The checker (`PCS.V2.TranslationChecker`) is later proved sound *against this meaning*.

## The fragment

* **Terms** `Term`: variables and applications of grounded function symbols (constants are
  nullary applications).
* **Formulas** `Formula`: `⊤`, `⊥`, grounded atomic predicates, equality, inequality,
  `¬`, `∧`, `∨`, `→`, and typed quantifiers `∀ x : s, φ` / `∃ x : s, φ`.
  The explicit constructor `unsupported tag` records any construct outside the fragment
  (modalities, probabilities, generalised quantifiers such as "most", temporal operators,
  …); it is *never* accepted by the checker.
* **Claims** `SemanticClaim`: explicitly bound, typed parameters (universally read), an
  explicit list of assumptions/hypotheses, and a conclusion.  Assumptions and conclusions
  are kept apart *structurally*; the claim means
  `∀ params, (⋀ assumptions) → conclusion`.

## Symbol environment

A `Registry` lists the approved sorts and symbols.  Every symbol entry carries its
canonical semantic id, the canonical Lean constant that grounds it, its typed signature
(argument sorts, result sort for functions) and a provenance string (module + digest).

## Semantics

A `Model` is a many-sorted structure presented in relativised form: a domain `Dom`,
a sort-membership predicate `HasSort`, and interpretations of function and predicate
symbols *by canonical id*.  Quantifiers range over the elements of the stated sort.
`Formula.denote M ρ φ` and `SemanticClaim.denote M ρ c` are the meanings.

`Model.Conforms R M` states that `M` respects the registry's function signatures; with it,
`Term.denote_hasSort` proves type soundness of term denotation for well-typed terms under
well-typed valuations.

The file depends only on Lean core.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-- Semantic sort identifiers (grounded in the registry). -/
abbrev SortId := String

/-! ## Syntax -/

/-- Terms of the fragment. -/
inductive Term where
  | var (x : String)
  | app (f : String) (args : List Term)
  deriving Repr, Inhabited

mutual
/-- Decidable equality of terms (nested inductive: written by hand). -/
def Term.decEq : (a b : Term) → Decidable (a = b)
  | .var x, .var y =>
    if h : x = y then isTrue (h ▸ rfl) else isFalse (fun e => by cases e; exact h rfl)
  | .app f as, .app g bs =>
    if h : f = g then
      match Term.decEqList as bs with
      | isTrue e => isTrue (by subst h; subst e; rfl)
      | isFalse n => isFalse (fun e => by cases e; exact n rfl)
    else isFalse (fun e => by cases e; exact h rfl)
  | .var _, .app _ _ => isFalse (fun e => by cases e)
  | .app _ _, .var _ => isFalse (fun e => by cases e)
/-- Decidable equality of term lists. -/
def Term.decEqList : (a b : List Term) → Decidable (a = b)
  | [], [] => isTrue rfl
  | a :: as, b :: bs =>
    match Term.decEq a b, Term.decEqList as bs with
    | isTrue h1, isTrue h2 => isTrue (by subst h1; subst h2; rfl)
    | isFalse n, _ => isFalse (fun e => by cases e; exact n rfl)
    | _, isFalse n => isFalse (fun e => by cases e; exact n rfl)
  | [], _ :: _ => isFalse (fun e => by cases e)
  | _ :: _, [] => isFalse (fun e => by cases e)
end

instance : DecidableEq Term := Term.decEq

/-- The two quantifiers. -/
inductive Quant where
  | all
  | ex
  deriving Repr, DecidableEq, Inhabited

/-- Formulas of the supported fragment (plus an explicit `unsupported` marker). -/
inductive Formula where
  | tt
  | ff
  | pred (p : String) (args : List Term)
  | eq (a b : Term)
  | ne (a b : Term)
  | not (φ : Formula)
  | and (φ ψ : Formula)
  | or (φ ψ : Formula)
  | imp (φ ψ : Formula)
  | quant (q : Quant) (x : String) (s : SortId) (φ : Formula)
  | unsupported (tag : String)
  deriving Repr, DecidableEq, Inhabited

/-- An explicitly bound, typed variable. -/
structure Binder where
  name : String
  sort : SortId
  deriving Repr, DecidableEq, Inhabited

/-- A structured claim: typed parameters, explicit assumptions, conclusion. -/
structure SemanticClaim where
  params : List Binder
  assumptions : List Formula
  conclusion : Formula
  deriving Repr, DecidableEq, Inhabited

/-! ## Approved symbol environment -/

/-- Typed signature of a symbol. -/
inductive SymKind where
  | pred (args : List SortId)
  | fn (args : List SortId) (result : SortId)
  deriving Repr, DecidableEq, Inhabited

/-- An approved, grounded symbol. -/
structure SymbolEntry where
  /-- canonical semantic id (the name used inside `Term`/`Formula`) -/
  id : String
  /-- canonical Lean constant grounding the symbol -/
  leanName : String
  /-- typed signature -/
  kind : SymKind
  /-- provenance (defining module and content digest) -/
  provenance : String
  deriving Repr, DecidableEq, Inhabited

/-- An approved, grounded sort. -/
structure SortEntry where
  id : SortId
  leanType : String
  provenance : String
  deriving Repr, DecidableEq, Inhabited

/-- The approved symbol environment. -/
structure Registry where
  sorts : List SortEntry
  symbols : List SymbolEntry
  deriving Repr, DecidableEq, Inhabited

/-- All entries with a given id. -/
def Registry.entries (R : Registry) (f : String) : List SymbolEntry :=
  R.symbols.filter (fun e => e.id == f)

/-- Unique resolution of a symbol id (`none` if absent **or** ambiguous). -/
def Registry.resolve (R : Registry) (f : String) : Option SymbolEntry :=
  match R.entries f with
  | [e] => some e
  | _ => none

/-- Unique resolution of a sort id. -/
def Registry.resolveSort (R : Registry) (s : SortId) : Option SortEntry :=
  match R.sorts.filter (fun e => e.id == s) with
  | [e] => some e
  | _ => none

/-- Registry well-formedness: symbol ids distinct, sort ids distinct, every sort mentioned
    in a signature is registered. -/
def Registry.wellFormedB (R : Registry) : Bool :=
  decide ((R.symbols.map (·.id)).Nodup) && decide ((R.sorts.map (·.id)).Nodup) &&
    R.symbols.all (fun e =>
      match e.kind with
      | .pred ss => ss.all (fun s => (R.resolveSort s).isSome)
      | .fn ss r => ss.all (fun s => (R.resolveSort s).isSome) && (R.resolveSort r).isSome)

/-! ## Models and denotation -/

/-- A many-sorted structure in relativised form; symbols are interpreted by canonical id. -/
structure Model where
  Dom : Type
  HasSort : SortId → Dom → Prop
  fn : String → List Dom → Dom
  pred : String → List Dom → Prop

/-- Valuation update. -/
def update {α : Type} (ρ : String → α) (x : String) (d : α) : String → α :=
  fun y => if y = x then d else ρ y

mutual
/-- Denotation of a term. -/
def Term.denote (M : Model) (ρ : String → M.Dom) : Term → M.Dom
  | .var x => ρ x
  | .app f args => M.fn f (Term.denoteList M ρ args)
/-- Denotation of a term list. -/
def Term.denoteList (M : Model) (ρ : String → M.Dom) : List Term → List M.Dom
  | [] => []
  | t :: ts => Term.denote M ρ t :: Term.denoteList M ρ ts
end

theorem Term.denoteList_eq_map (M : Model) (ρ : String → M.Dom) :
    ∀ ts, Term.denoteList M ρ ts = ts.map (Term.denote M ρ)
  | [] => rfl
  | t :: ts => by simp [Term.denoteList, Term.denoteList_eq_map M ρ ts]

/-- **Compositional denotation of formulas.** -/
def Formula.denote (M : Model) : (String → M.Dom) → Formula → Prop
  | _, .tt => True
  | _, .ff => False
  | ρ, .pred p args => M.pred p (Term.denoteList M ρ args)
  | ρ, .eq a b => Term.denote M ρ a = Term.denote M ρ b
  | ρ, .ne a b => Term.denote M ρ a ≠ Term.denote M ρ b
  | ρ, .not φ => ¬ Formula.denote M ρ φ
  | ρ, .and φ ψ => Formula.denote M ρ φ ∧ Formula.denote M ρ ψ
  | ρ, .or φ ψ => Formula.denote M ρ φ ∨ Formula.denote M ρ ψ
  | ρ, .imp φ ψ => Formula.denote M ρ φ → Formula.denote M ρ ψ
  | ρ, .quant .all x s φ => ∀ d, M.HasSort s d → Formula.denote M (update ρ x d) φ
  | ρ, .quant .ex x s φ => ∃ d, M.HasSort s d ∧ Formula.denote M (update ρ x d) φ
  | _, .unsupported _ => False

/-- Universal closure over a parameter list, continuation style. -/
def denoteParams (M : Model) : List Binder → (String → M.Dom) → ((String → M.Dom) → Prop) → Prop
  | [], ρ, k => k ρ
  | b :: bs, ρ, k => ∀ d, M.HasSort b.sort d → denoteParams M bs (update ρ b.name d) k

/-- **Denotation of a structured claim**: for all well-sorted values of the parameters, the
    conjunction of the assumptions implies the conclusion. -/
def SemanticClaim.denote (M : Model) (ρ : String → M.Dom) (c : SemanticClaim) : Prop :=
  denoteParams M c.params ρ (fun ρ' =>
    (∀ a ∈ c.assumptions, Formula.denote M ρ' a) → Formula.denote M ρ' c.conclusion)

/-! ## Free variables, symbols, fragment membership -/

mutual
def Term.freeVars (bound : List String) : Term → List String
  | .var x => if bound.contains x then [] else [x]
  | .app _ args => Term.freeVarsList bound args
def Term.freeVarsList (bound : List String) : List Term → List String
  | [] => []
  | t :: ts => Term.freeVars bound t ++ Term.freeVarsList bound ts
end

/-- Free variables of a formula relative to a list of bound names. -/
def Formula.freeVars : List String → Formula → List String
  | _, .tt | _, .ff | _, .unsupported _ => []
  | b, .pred _ args => Term.freeVarsList b args
  | b, .eq x y | b, .ne x y => Term.freeVars b x ++ Term.freeVars b y
  | b, .not φ => Formula.freeVars b φ
  | b, .and φ ψ | b, .or φ ψ | b, .imp φ ψ => Formula.freeVars b φ ++ Formula.freeVars b ψ
  | b, .quant _ x _ φ => Formula.freeVars (x :: b) φ

/-- Free variables of a claim (variables bound neither by a parameter nor a quantifier). -/
def SemanticClaim.freeVars (c : SemanticClaim) : List String :=
  let b := c.params.map (·.name)
  (c.assumptions.flatMap (Formula.freeVars b)) ++ Formula.freeVars b c.conclusion

mutual
def Term.symbols : Term → List String
  | .var _ => []
  | .app f args => f :: Term.symbolsList args
def Term.symbolsList : List Term → List String
  | [] => []
  | t :: ts => Term.symbols t ++ Term.symbolsList ts
end

/-- Function and predicate symbols referenced by a formula. -/
def Formula.symbols : Formula → List String
  | .tt | .ff | .unsupported _ => []
  | .pred p args => p :: Term.symbolsList args
  | .eq x y | .ne x y => Term.symbols x ++ Term.symbols y
  | .not φ | .quant _ _ _ φ => Formula.symbols φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.symbols φ ++ Formula.symbols ψ

def SemanticClaim.symbols (c : SemanticClaim) : List String :=
  c.assumptions.flatMap Formula.symbols ++ Formula.symbols c.conclusion

/-- Unsupported-construct tags occurring in a formula. -/
def Formula.unsupportedTags : Formula → List String
  | .unsupported t => [t]
  | .tt | .ff | .pred _ _ | .eq _ _ | .ne _ _ => []
  | .not φ | .quant _ _ _ φ => Formula.unsupportedTags φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.unsupportedTags φ ++ Formula.unsupportedTags ψ

def SemanticClaim.unsupportedTags (c : SemanticClaim) : List String :=
  c.assumptions.flatMap Formula.unsupportedTags ++ Formula.unsupportedTags c.conclusion

/-- All binder names (parameters and quantified variables), in order. -/
def Formula.binders : Formula → List String
  | .tt | .ff | .unsupported _ | .pred _ _ | .eq _ _ | .ne _ _ => []
  | .not φ => Formula.binders φ
  | .quant _ x _ φ => x :: Formula.binders φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.binders φ ++ Formula.binders ψ

/-- Binder hygiene: along every scope path no binder name is re-bound, and no binder
    name is in `avoid` (the parameters in scope and every registered symbol / Lean name,
    so a rendered Lean binder can never capture a grounded constant). -/
def Formula.hygienicB : List String → Formula → Bool
  | _, .tt | _, .ff | _, .unsupported _ | _, .pred _ _ | _, .eq _ _ | _, .ne _ _ => true
  | a, .not φ => Formula.hygienicB a φ
  | a, .and φ ψ | a, .or φ ψ | a, .imp φ ψ => Formula.hygienicB a φ && Formula.hygienicB a ψ
  | a, .quant _ x _ φ => !(a.contains x) && Formula.hygienicB (x :: a) φ

/-! ## Typing -/

/-- Typing context: variable ↦ sort, innermost binding first. -/
abbrev Ctx := List (String × SortId)

/-- Context lookup (innermost first). -/
def Ctx.lookup : Ctx → String → Option SortId
  | [], _ => none
  | (y, s) :: Γ, x => if x = y then some s else Ctx.lookup Γ x

mutual
/-- Sort of a term, if well typed. -/
def Term.sortOf (R : Registry) (Γ : Ctx) : Term → Option SortId
  | .var x => Γ.lookup x
  | .app f args =>
    match R.resolve f with
    | some ⟨_, _, .fn ss r, _⟩ =>
      match Term.sortsOf R Γ args with
      | some ts => if ts = ss then some r else none
      | none => none
    | _ => none
/-- Sorts of a term list. -/
def Term.sortsOf (R : Registry) (Γ : Ctx) : List Term → Option (List SortId)
  | [] => some []
  | t :: ts =>
    match Term.sortOf R Γ t, Term.sortsOf R Γ ts with
    | some s, some ss => some (s :: ss)
    | _, _ => none
end

/-- Well-typedness of formulas. -/
def Formula.wellTypedB (R : Registry) : Ctx → Formula → Bool
  | _, .tt | _, .ff => true
  | _, .unsupported _ => false
  | Γ, .pred p args =>
    match R.resolve p with
    | some ⟨_, _, .pred ss, _⟩ => decide (Term.sortsOf R Γ args = some ss)
    | _ => false
  | Γ, .eq a b | Γ, .ne a b =>
    match Term.sortOf R Γ a, Term.sortOf R Γ b with
    | some s, some t => decide (s = t)
    | _, _ => false
  | Γ, .not φ => Formula.wellTypedB R Γ φ
  | Γ, .and φ ψ | Γ, .or φ ψ | Γ, .imp φ ψ => Formula.wellTypedB R Γ φ && Formula.wellTypedB R Γ ψ
  | Γ, .quant _ x s φ => (R.resolveSort s).isSome && Formula.wellTypedB R ((x, s) :: Γ) φ

/-- The typing context introduced by a parameter list. -/
def paramCtx (ps : List Binder) : Ctx := (ps.map (fun b => (b.name, b.sort))).reverse

/-- Well-typedness of a claim under the registry. -/
def SemanticClaim.wellTypedB (R : Registry) (c : SemanticClaim) : Bool :=
  c.params.all (fun b => (R.resolveSort b.sort).isSome) &&
    c.assumptions.all (Formula.wellTypedB R (paramCtx c.params)) &&
    Formula.wellTypedB R (paramCtx c.params) c.conclusion

/-- Pointwise sort membership of a value list. -/
inductive SortsHold (M : Model) : List SortId → List M.Dom → Prop
  | nil : SortsHold M [] []
  | cons {s : SortId} {d : M.Dom} {ss : List SortId} {ds : List M.Dom} :
      M.HasSort s d → SortsHold M ss ds → SortsHold M (s :: ss) (d :: ds)

/-- A model conforms to the registry's function signatures. -/
def Model.Conforms (R : Registry) (M : Model) : Prop :=
  ∀ f e ss r, R.resolve f = some e → e.kind = .fn ss r →
    ∀ ds : List M.Dom, SortsHold M ss ds → M.HasSort r (M.fn f ds)

/-- A valuation is well typed for a context. -/
def WellTypedVal (M : Model) (Γ : Ctx) (ρ : String → M.Dom) : Prop :=
  ∀ x s, Γ.lookup x = some s → M.HasSort s (ρ x)

mutual
/-- **Type soundness of term denotation.** -/
theorem Term.denote_hasSort {R : Registry} {M : Model} (hM : M.Conforms R) {Γ : Ctx}
    {ρ : String → M.Dom} (hρ : WellTypedVal M Γ ρ) :
    ∀ (t : Term) (s : SortId), Term.sortOf R Γ t = some s → M.HasSort s (Term.denote M ρ t)
  | .var x, s, h => by simp only [Term.sortOf] at h; exact hρ x s h
  | .app f args, s, h => by
    simp only [Term.sortOf] at h
    split at h
    · rename_i id ln ss r pv hres
      split at h
      · rename_i ts hts
        split at h
        · rename_i heq
          cases h
          subst heq
          simp only [Term.denote]
          exact hM f _ ts s hres rfl _ (Term.denoteList_hasSort hM hρ args ts hts)
        · cases h
      · cases h
    · cases h
/-- List version. -/
theorem Term.denoteList_hasSort {R : Registry} {M : Model} (hM : M.Conforms R) {Γ : Ctx}
    {ρ : String → M.Dom} (hρ : WellTypedVal M Γ ρ) :
    ∀ (ts : List Term) (ss : List SortId), Term.sortsOf R Γ ts = some ss →
      SortsHold M ss (Term.denoteList M ρ ts)
  | [], ss, h => by simp only [Term.sortsOf, Option.some.injEq] at h; subst h; exact .nil
  | t :: ts, ss, h => by
    simp only [Term.sortsOf] at h
    split at h
    · rename_i s ss' h1 h2
      cases h
      exact .cons (Term.denote_hasSort hM hρ t s h1) (Term.denoteList_hasSort hM hρ ts ss' h2)
    · cases h
end

end PCS.V2.Semantic
