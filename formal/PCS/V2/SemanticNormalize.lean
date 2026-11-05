import PCS.V2.SemanticIR

/-!
# Canonical normalization of semantic claims, and why it preserves denotation

The translation checker compares the human-selected interpretation and the formal
candidate **after** a canonical normalization.  This file defines that normalization and
proves that it is *denotation-preserving*, so comparing normal forms is sound.

The normalization performs exactly three representational identifications:

1. **α-renaming** — bound variable names (parameters and quantified variables) are
   replaced by de Bruijn indices (`Term.toDB`, `Formula.toDB`).  Free variables keep their
   names; a variable bound at a different binder, or captured by an inner binder, gets a
   different index, so variable capture and rebinding are *not* identified.
2. **Inequality desugaring** — `a ≠ b` becomes `¬ (a = b)`.
3. **Assumption set semantics** — two claims are identified when their normalized
   assumption lists contain the same formulas (order and duplicates are irrelevant);
   this is the only non-syntactic step and it is justified by
   `ndenoteClaim_congr_assumptions`.

Everything else is kept: `∀` vs `∃`, the sort of every binder, the direction of every
implication, every negation, `∧` vs `∨`, assumptions vs conclusion, symbol identity, and
the scope (de Bruijn index) of every variable occurrence.

Main results:

* `Term.toDB_denote`, `Formula.toDB_denote` — de Bruijn conversion is exact for every
  model, valuation and environment (`extend` relates named and nameless environments).
* `SemanticClaim.normalize_denote` — a claim and its normal form have the same denotation.
* `NClaim.Equiv` — the accepted equivalence of normal forms (decidable: `NClaim.equivB`).
* `alphaEquiv_denote_iff` — **if two claims have `Equiv` normal forms then, for every
  model and every valuation, their denotations are logically equivalent.**
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Nameless syntax -/

/-- Nameless terms. -/
inductive NTerm where
  | bvar (i : Nat)
  | fvar (x : String)
  | app (f : String) (args : List NTerm)
  deriving Repr, Inhabited

mutual
def NTerm.decEq : (a b : NTerm) → Decidable (a = b)
  | .bvar i, .bvar j => if h : i = j then isTrue (h ▸ rfl) else isFalse (fun e => by cases e; exact h rfl)
  | .fvar x, .fvar y => if h : x = y then isTrue (h ▸ rfl) else isFalse (fun e => by cases e; exact h rfl)
  | .app f as, .app g bs =>
    if h : f = g then
      match NTerm.decEqList as bs with
      | isTrue e => isTrue (by subst h; subst e; rfl)
      | isFalse n => isFalse (fun e => by cases e; exact n rfl)
    else isFalse (fun e => by cases e; exact h rfl)
  | .bvar _, .fvar _ => isFalse (fun e => by cases e)
  | .bvar _, .app _ _ => isFalse (fun e => by cases e)
  | .fvar _, .bvar _ => isFalse (fun e => by cases e)
  | .fvar _, .app _ _ => isFalse (fun e => by cases e)
  | .app _ _, .bvar _ => isFalse (fun e => by cases e)
  | .app _ _, .fvar _ => isFalse (fun e => by cases e)
def NTerm.decEqList : (a b : List NTerm) → Decidable (a = b)
  | [], [] => isTrue rfl
  | a :: as, b :: bs =>
    match NTerm.decEq a b, NTerm.decEqList as bs with
    | isTrue h1, isTrue h2 => isTrue (by subst h1; subst h2; rfl)
    | isFalse n, _ => isFalse (fun e => by cases e; exact n rfl)
    | _, isFalse n => isFalse (fun e => by cases e; exact n rfl)
  | [], _ :: _ => isFalse (fun e => by cases e)
  | _ :: _, [] => isFalse (fun e => by cases e)
end

instance : DecidableEq NTerm := NTerm.decEq

/-- Nameless formulas (no `ne`: it is desugared). -/
inductive NFormula where
  | tt
  | ff
  | pred (p : String) (args : List NTerm)
  | eq (a b : NTerm)
  | not (φ : NFormula)
  | and (φ ψ : NFormula)
  | or (φ ψ : NFormula)
  | imp (φ ψ : NFormula)
  | quant (q : Quant) (s : SortId) (φ : NFormula)
  | unsupported (tag : String)
  deriving Repr, DecidableEq, Inhabited

/-! ## de Bruijn conversion -/

/-- Position of the innermost binding of `x` in a context (innermost first). -/
def idx : List String → String → Option Nat
  | [], _ => none
  | y :: ys, x => if x = y then some 0 else (idx ys x).map (· + 1)

mutual
def Term.toDB (ctx : List String) : Term → NTerm
  | .var x => match idx ctx x with
    | some i => .bvar i
    | none => .fvar x
  | .app f args => .app f (Term.toDBList ctx args)
def Term.toDBList (ctx : List String) : List Term → List NTerm
  | [] => []
  | t :: ts => Term.toDB ctx t :: Term.toDBList ctx ts
end

/-- Canonical nameless form of a formula. -/
def Formula.toDB : List String → Formula → NFormula
  | _, .tt => .tt
  | _, .ff => .ff
  | c, .pred p args => .pred p (Term.toDBList c args)
  | c, .eq a b => .eq (Term.toDB c a) (Term.toDB c b)
  | c, .ne a b => .not (.eq (Term.toDB c a) (Term.toDB c b))
  | c, .not φ => .not (Formula.toDB c φ)
  | c, .and φ ψ => .and (Formula.toDB c φ) (Formula.toDB c ψ)
  | c, .or φ ψ => .or (Formula.toDB c φ) (Formula.toDB c ψ)
  | c, .imp φ ψ => .imp (Formula.toDB c φ) (Formula.toDB c ψ)
  | c, .quant q x s φ => .quant q s (Formula.toDB (x :: c) φ)
  | _, .unsupported t => .unsupported t

/-! ## Nameless denotation -/

/-- Push a value on a nameless environment. -/
def consEnv {α : Type} (d : α) (env : Nat → α) : Nat → α
  | 0 => d
  | i + 1 => env i

mutual
def NTerm.denote (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom) : NTerm → M.Dom
  | .bvar i => env i
  | .fvar x => ρ x
  | .app f args => M.fn f (NTerm.denoteList M ρ env args)
def NTerm.denoteList (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom) :
    List NTerm → List M.Dom
  | [] => []
  | t :: ts => NTerm.denote M ρ env t :: NTerm.denoteList M ρ env ts
end

/-- Denotation of nameless formulas (free variables read from `ρ`, bound ones from `env`). -/
def NFormula.denote (M : Model) (ρ : String → M.Dom) : (Nat → M.Dom) → NFormula → Prop
  | _, .tt => True
  | _, .ff => False
  | env, .pred p args => M.pred p (NTerm.denoteList M ρ env args)
  | env, .eq a b => NTerm.denote M ρ env a = NTerm.denote M ρ env b
  | env, .not φ => ¬ NFormula.denote M ρ env φ
  | env, .and φ ψ => NFormula.denote M ρ env φ ∧ NFormula.denote M ρ env ψ
  | env, .or φ ψ => NFormula.denote M ρ env φ ∨ NFormula.denote M ρ env ψ
  | env, .imp φ ψ => NFormula.denote M ρ env φ → NFormula.denote M ρ env ψ
  | env, .quant .all s φ => ∀ d, M.HasSort s d → NFormula.denote M ρ (consEnv d env) φ
  | env, .quant .ex s φ => ∃ d, M.HasSort s d ∧ NFormula.denote M ρ (consEnv d env) φ
  | _, .unsupported _ => False

/-- The named valuation determined by a context, a nameless environment and the
    valuation of free names. -/
def extend {α : Type} (ρ : String → α) (ctx : List String) (env : Nat → α) : String → α :=
  fun x => match idx ctx x with
    | some i => env i
    | none => ρ x

theorem extend_nil {α : Type} (ρ : String → α) (env : Nat → α) : extend ρ [] env = ρ := rfl

theorem update_extend {α : Type} (ρ : String → α) (ctx : List String) (env : Nat → α)
    (x : String) (d : α) : update (extend ρ ctx env) x d = extend ρ (x :: ctx) (consEnv d env) := by
  funext y
  unfold update extend
  simp only [idx]
  by_cases h : y = x
  · simp [h, consEnv]
  · simp only [h, if_false]
    cases idx ctx y <;> rfl

mutual
/-- **de Bruijn conversion of terms is exact.** -/
theorem Term.toDB_denote (M : Model) (ρ : String → M.Dom) (ctx : List String)
    (env : Nat → M.Dom) : ∀ t : Term,
    Term.denote M (extend ρ ctx env) t = NTerm.denote M ρ env (Term.toDB ctx t)
  | .var x => by
    simp only [Term.denote, Term.toDB, extend]
    cases idx ctx x <;> rfl
  | .app f args => by
    simp only [Term.denote, Term.toDB, NTerm.denote]
    rw [Term.toDBList_denote M ρ ctx env args]
theorem Term.toDBList_denote (M : Model) (ρ : String → M.Dom) (ctx : List String)
    (env : Nat → M.Dom) : ∀ ts : List Term,
    Term.denoteList M (extend ρ ctx env) ts = NTerm.denoteList M ρ env (Term.toDBList ctx ts)
  | [] => rfl
  | t :: ts => by
    simp only [Term.denoteList, Term.toDBList, NTerm.denoteList]
    rw [Term.toDB_denote M ρ ctx env t, Term.toDBList_denote M ρ ctx env ts]
end

/-- **de Bruijn conversion (with `≠` desugaring) of formulas is exact.** -/
theorem Formula.toDB_denote (M : Model) (ρ : String → M.Dom) :
    ∀ (φ : Formula) (ctx : List String) (env : Nat → M.Dom),
    Formula.denote M (extend ρ ctx env) φ ↔ NFormula.denote M ρ env (Formula.toDB ctx φ)
  | .tt, _, _ => Iff.rfl
  | .ff, _, _ => Iff.rfl
  | .pred p args, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    rw [Term.toDBList_denote]
  | .eq a b, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    rw [Term.toDB_denote, Term.toDB_denote]
  | .ne a b, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    rw [Term.toDB_denote, Term.toDB_denote]
  | .not φ, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    exact not_congr (Formula.toDB_denote M ρ φ ctx env)
  | .and φ ψ, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    exact and_congr (Formula.toDB_denote M ρ φ ctx env) (Formula.toDB_denote M ρ ψ ctx env)
  | .or φ ψ, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    exact or_congr (Formula.toDB_denote M ρ φ ctx env) (Formula.toDB_denote M ρ ψ ctx env)
  | .imp φ ψ, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    exact imp_congr (Formula.toDB_denote M ρ φ ctx env) (Formula.toDB_denote M ρ ψ ctx env)
  | .quant .all x s φ, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    apply forall_congr'; intro d; apply imp_congr Iff.rfl
    rw [update_extend]
    exact Formula.toDB_denote M ρ φ (x :: ctx) (consEnv d env)
  | .quant .ex x s φ, ctx, env => by
    simp only [Formula.denote, Formula.toDB, NFormula.denote]
    apply exists_congr; intro d; apply and_congr Iff.rfl
    rw [update_extend]
    exact Formula.toDB_denote M ρ φ (x :: ctx) (consEnv d env)
  | .unsupported _, _, _ => Iff.rfl

/-- Closed-context form. -/
theorem Formula.toDB_denote_nil (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom)
    (φ : Formula) : Formula.denote M ρ φ ↔ NFormula.denote M ρ env (Formula.toDB [] φ) :=
  Formula.toDB_denote M ρ φ [] env

/-- α-equivalent formulas (equal nameless forms) have the same denotation everywhere. -/
theorem Formula.alpha_denote_iff {φ ψ : Formula} (h : Formula.toDB [] φ = Formula.toDB [] ψ)
    (M : Model) (ρ : String → M.Dom) : Formula.denote M ρ φ ↔ Formula.denote M ρ ψ := by
  rw [Formula.toDB_denote_nil M ρ (fun _ => ρ ""), Formula.toDB_denote_nil M ρ (fun _ => ρ ""), h]

/-! ## Claims -/

/-- Nameless claims. -/
structure NClaim where
  paramSorts : List SortId
  assumptions : List NFormula
  conclusion : NFormula
  deriving Repr, DecidableEq, Inhabited

/-- Context after binding the parameters (innermost first). -/
def ctxOf (bs : List Binder) (ctx : List String) : List String :=
  bs.foldl (fun c b => b.name :: c) ctx

/-- **The canonical normal form of a claim.** -/
def SemanticClaim.normalize (c : SemanticClaim) : NClaim :=
  { paramSorts := c.params.map (·.sort),
    assumptions := c.assumptions.map (Formula.toDB (ctxOf c.params [])),
    conclusion := Formula.toDB (ctxOf c.params []) c.conclusion }

/-- Nameless universal closure. -/
def ndenoteParams (M : Model) (ρ : String → M.Dom) :
    List SortId → (Nat → M.Dom) → ((Nat → M.Dom) → Prop) → Prop
  | [], env, k => k env
  | s :: ss, env, k => ∀ d, M.HasSort s d → ndenoteParams M ρ ss (consEnv d env) k

/-- Denotation of a nameless claim. -/
def NClaim.denote (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom) (n : NClaim) : Prop :=
  ndenoteParams M ρ n.paramSorts env (fun e =>
    (∀ a ∈ n.assumptions, NFormula.denote M ρ e a) → NFormula.denote M ρ e n.conclusion)

theorem denoteParams_toDB (M : Model) (ρ : String → M.Dom) :
    ∀ (bs : List Binder) (ctx : List String) (env : Nat → M.Dom)
      (k : (String → M.Dom) → Prop) (K : (Nat → M.Dom) → Prop),
      (∀ e, k (extend ρ (ctxOf bs ctx) e) ↔ K e) →
      (denoteParams M bs (extend ρ ctx env) k ↔ ndenoteParams M ρ (bs.map (·.sort)) env K)
  | [], ctx, env, k, K, h => h env
  | b :: bs, ctx, env, k, K, h => by
    simp only [denoteParams, ndenoteParams, List.map]
    apply forall_congr'; intro d; apply imp_congr Iff.rfl
    rw [update_extend]
    exact denoteParams_toDB M ρ bs (b.name :: ctx) (consEnv d env) k K h

/-- **Normalization preserves the denotation of claims.** -/
theorem SemanticClaim.normalize_denote (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom)
    (c : SemanticClaim) : c.denote M ρ ↔ c.normalize.denote M ρ env := by
  unfold SemanticClaim.denote NClaim.denote SemanticClaim.normalize
  simp only
  rw [← extend_nil ρ env]
  apply denoteParams_toDB M ρ c.params [] env
  intro e
  apply imp_congr
  · constructor
    · intro h a ha
      obtain ⟨a', ha', rfl⟩ := List.mem_map.mp ha
      exact (Formula.toDB_denote M ρ a' _ e).mp (h a' ha')
    · intro h a ha
      exact (Formula.toDB_denote M ρ a _ e).mpr (h _ (List.mem_map.mpr ⟨a, ha, rfl⟩))
  · exact Formula.toDB_denote M ρ c.conclusion _ e

/-- **The accepted equivalence of normal forms**: same parameter sorts (in order), same
    nameless conclusion, and the same *set* of nameless assumptions. -/
def NClaim.Equiv (n m : NClaim) : Prop :=
  n.paramSorts = m.paramSorts ∧ n.conclusion = m.conclusion ∧
    (∀ a ∈ n.assumptions, a ∈ m.assumptions) ∧ (∀ a ∈ m.assumptions, a ∈ n.assumptions)

/-- Decision procedure for `NClaim.Equiv`. -/
def NClaim.equivB (n m : NClaim) : Bool :=
  decide (n.paramSorts = m.paramSorts) && decide (n.conclusion = m.conclusion) &&
    n.assumptions.all (fun a => m.assumptions.contains a) &&
    m.assumptions.all (fun a => n.assumptions.contains a)

theorem NClaim.equivB_iff (n m : NClaim) : n.equivB m = true ↔ n.Equiv m := by
  unfold NClaim.equivB NClaim.Equiv
  simp [List.all_eq_true, and_assoc]

theorem ndenoteParams_congr (M : Model) (ρ : String → M.Dom) :
    ∀ (ss : List SortId) (env : Nat → M.Dom) (K K' : (Nat → M.Dom) → Prop),
      (∀ e, K e ↔ K' e) → (ndenoteParams M ρ ss env K ↔ ndenoteParams M ρ ss env K')
  | [], env, _, _, h => h env
  | s :: ss, env, K, K', h => by
    simp only [ndenoteParams]
    apply forall_congr'; intro d; apply imp_congr Iff.rfl
    exact ndenoteParams_congr M ρ ss _ K K' h

/-- Assumption-set semantics: equivalent normal forms have equal denotations. -/
theorem ndenoteClaim_congr_assumptions {n m : NClaim} (h : n.Equiv m) (M : Model)
    (ρ : String → M.Dom) (env : Nat → M.Dom) : n.denote M ρ env ↔ m.denote M ρ env := by
  obtain ⟨hs, hc, h1, h2⟩ := h
  unfold NClaim.denote
  rw [hs, hc]
  apply ndenoteParams_congr
  intro e
  apply imp_congr _ Iff.rfl
  exact ⟨fun H a ha => H a (h2 a ha), fun H a ha => H a (h1 a ha)⟩

/-- **α-equivalence soundness for claims.**  If the normal forms of `c` and `d` are
    equivalent, then for every model `M` and every valuation `ρ` the denotations of `c`
    and `d` are logically equivalent. -/
theorem alphaEquiv_denote_iff {c d : SemanticClaim} (h : c.normalize.Equiv d.normalize)
    (M : Model) (ρ : String → M.Dom) : c.denote M ρ ↔ d.denote M ρ := by
  let env : Nat → M.Dom := fun _ => ρ ""
  rw [SemanticClaim.normalize_denote M ρ env c, SemanticClaim.normalize_denote M ρ env d]
  exact ndenoteClaim_congr_assumptions h M ρ env

end PCS.V2.Semantic
