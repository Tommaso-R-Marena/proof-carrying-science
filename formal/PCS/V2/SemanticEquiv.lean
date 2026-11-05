import PCS.V2.SemanticNormalize

/-!
# Proof-carrying semantic equivalence certificates (Semantic Intelligence v2)

v1 accepted a candidate only when its canonical normal form was *equal* (up to α-renaming,
`≠`-desugaring and assumption-set order) to the normal form of the selected interpretation.
That is sound but very incomplete: a candidate that writes `Q ∧ P` for `P ∧ Q`, or
`¬ ∃ x, ¬ P x` for `∀ x, P x`, was rejected.

This file adds a **small, independently checkable certificate language** for semantic
equivalence of nameless formulas and claims:

* `Rule` — a finite catalogue of rewrite rules.  Each rule is a *classical first-order
  equivalence* (double negation, commutativity/associativity of `∧`/`∨`, symmetry of `=`,
  `→`-elimination, De Morgan, quantifier negation, contraposition, (un)currying,
  distribution of `∀` over `∧` and of `∃` over `∨`, swapping adjacent like quantifiers via
  a de Bruijn index swap, unit and idempotence laws).
* `rewriteAt` — apply a rule at a *path* inside a formula (congruence closure).
* `EquivCert` — two step lists, one rewriting the interpretation's normal form and one
  rewriting the candidate's, which must meet in `NClaim.Equiv`-equivalent forms.
* `checkCert` — the certificate checker.  It is a few dozen lines of total, structural code:
  it never searches, it only replays steps.

Main results (all for **every** model, valuation and nameless environment):

* `Rule.apply_sound` — every rule application preserves denotation.
* `rewriteAt_sound` — rewriting at any path preserves denotation (congruence, including
  under binders).
* `NClaim.applySteps_sound` — replaying a step list preserves claim denotation.
* `translation_certificate_sound` / `certificate_acceptance_implies_semantic_preservation` —
  if `checkCert cert I.normalize C.normalize = true` then for every model `M` and valuation
  `ρ`, `I.denote M ρ ↔ C.denote M ρ`.
* `certificate_checker_rejects_invalid_derivations` — a certificate whose steps do not
  replay, or whose endpoints are not equivalent, is rejected; and no certificate at all is
  accepted for semantically inequivalent claims (`inequivalent_claims_admit_no_certificate`).
* `untrusted_translation_search_cannot_forge_certified_equivalence` — for an *arbitrary*
  (untrusted, possibly adversarial) certificate generator, every certificate it produces that
  the checker accepts is semantically sound.

Incompleteness: the rule catalogue does not decide first-order equivalence (nothing can);
failure to find or check a certificate is never evidence of inequivalence.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Semantic equivalence of nameless formulas -/

/-- Two nameless formulas are semantically equivalent: same truth value in every model, for
    every valuation of free names and every nameless environment. -/
def NFormula.SemEquiv (φ ψ : NFormula) : Prop :=
  ∀ (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom),
    NFormula.denote M ρ env φ ↔ NFormula.denote M ρ env ψ

theorem NFormula.SemEquiv.refl (φ : NFormula) : NFormula.SemEquiv φ φ := fun _ _ _ => Iff.rfl

theorem NFormula.SemEquiv.symm {φ ψ : NFormula} (h : NFormula.SemEquiv φ ψ) :
    NFormula.SemEquiv ψ φ := fun M ρ env => (h M ρ env).symm

theorem NFormula.SemEquiv.trans {φ ψ χ : NFormula} (h₁ : NFormula.SemEquiv φ ψ)
    (h₂ : NFormula.SemEquiv ψ χ) : NFormula.SemEquiv φ χ :=
  fun M ρ env => (h₁ M ρ env).trans (h₂ M ρ env)

/-! ## de Bruijn index swap (for exchanging adjacent quantifiers) -/

/-- Swap indices `c` and `c+1`. -/
def swapIdx (c i : Nat) : Nat := if i = c then c + 1 else if i = c + 1 then c else i

mutual
/-- Swap bound variables `c` and `c+1` in a term. -/
def NTerm.swapBV (c : Nat) : NTerm → NTerm
  | .bvar i => .bvar (swapIdx c i)
  | .fvar x => .fvar x
  | .app f args => .app f (NTerm.swapBVList c args)
def NTerm.swapBVList (c : Nat) : List NTerm → List NTerm
  | [] => []
  | t :: ts => NTerm.swapBV c t :: NTerm.swapBVList c ts
end

/-- Swap bound variables `c` and `c+1` in a formula (the cutoff moves under binders). -/
def NFormula.swapBV : Nat → NFormula → NFormula
  | _, .tt => .tt
  | _, .ff => .ff
  | c, .pred p args => .pred p (NTerm.swapBVList c args)
  | c, .eq a b => .eq (NTerm.swapBV c a) (NTerm.swapBV c b)
  | c, .not φ => .not (NFormula.swapBV c φ)
  | c, .and φ ψ => .and (NFormula.swapBV c φ) (NFormula.swapBV c ψ)
  | c, .or φ ψ => .or (NFormula.swapBV c φ) (NFormula.swapBV c ψ)
  | c, .imp φ ψ => .imp (NFormula.swapBV c φ) (NFormula.swapBV c ψ)
  | c, .quant q s φ => .quant q s (NFormula.swapBV (c + 1) φ)
  | _, .unsupported t => .unsupported t

mutual
theorem NTerm.swapBV_denote (M : Model) (ρ : String → M.Dom) (c : Nat) (env : Nat → M.Dom) :
    ∀ t : NTerm, NTerm.denote M ρ env (NTerm.swapBV c t) =
      NTerm.denote M ρ (fun i => env (swapIdx c i)) t
  | .bvar i => rfl
  | .fvar x => rfl
  | .app f args => by
    simp only [NTerm.swapBV, NTerm.denote]
    rw [NTerm.swapBVList_denote M ρ c env args]
theorem NTerm.swapBVList_denote (M : Model) (ρ : String → M.Dom) (c : Nat) (env : Nat → M.Dom) :
    ∀ ts : List NTerm, NTerm.denoteList M ρ env (NTerm.swapBVList c ts) =
      NTerm.denoteList M ρ (fun i => env (swapIdx c i)) ts
  | [] => rfl
  | t :: ts => by
    simp only [NTerm.swapBVList, NTerm.denoteList]
    rw [NTerm.swapBV_denote M ρ c env t, NTerm.swapBVList_denote M ρ c env ts]
end

theorem consEnv_swapIdx {α : Type} (d : α) (env : Nat → α) (c : Nat) :
    (fun i => consEnv d env (swapIdx (c + 1) i)) = consEnv d (fun i => env (swapIdx c i)) := by
  funext i
  cases i with
  | zero => simp [swapIdx, consEnv]
  | succ j =>
    simp only [swapIdx, consEnv]
    by_cases h1 : j = c
    · subst h1; simp
    · by_cases h2 : j = c + 1
      · subst h2; simp
      · simp [h1, h2]

/-- **Renaming lemma**: swapping bound variables `c, c+1` in the syntax is the same as
    swapping the corresponding environment entries. -/
theorem NFormula.swapBV_denote (M : Model) (ρ : String → M.Dom) :
    ∀ (φ : NFormula) (c : Nat) (env : Nat → M.Dom),
    NFormula.denote M ρ env (NFormula.swapBV c φ) ↔
      NFormula.denote M ρ (fun i => env (swapIdx c i)) φ
  | .tt, _, _ => Iff.rfl
  | .ff, _, _ => Iff.rfl
  | .pred p args, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]; rw [NTerm.swapBVList_denote]
  | .eq a b, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]; rw [NTerm.swapBV_denote, NTerm.swapBV_denote]
  | .not φ, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]; exact not_congr (NFormula.swapBV_denote M ρ φ c env)
  | .and φ ψ, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]
    exact and_congr (NFormula.swapBV_denote M ρ φ c env) (NFormula.swapBV_denote M ρ ψ c env)
  | .or φ ψ, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]
    exact or_congr (NFormula.swapBV_denote M ρ φ c env) (NFormula.swapBV_denote M ρ ψ c env)
  | .imp φ ψ, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]
    exact imp_congr (NFormula.swapBV_denote M ρ φ c env) (NFormula.swapBV_denote M ρ ψ c env)
  | .quant .all s φ, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]
    apply forall_congr'; intro d; apply imp_congr Iff.rfl
    rw [NFormula.swapBV_denote M ρ φ (c + 1) (consEnv d env), consEnv_swapIdx]
  | .quant .ex s φ, c, env => by
    simp only [NFormula.swapBV, NFormula.denote]
    apply exists_congr; intro d; apply and_congr Iff.rfl
    rw [NFormula.swapBV_denote M ρ φ (c + 1) (consEnv d env), consEnv_swapIdx]
  | .unsupported _, _, _ => Iff.rfl

theorem consEnv_swap0 {α : Type} (d₁ d₂ : α) (env : Nat → α) :
    (fun i => consEnv d₁ (consEnv d₂ env) (swapIdx 0 i)) = consEnv d₂ (consEnv d₁ env) := by
  funext i
  match i with
  | 0 => rfl
  | 1 => rfl
  | j + 2 => simp [swapIdx, consEnv]

/-! ## The rule catalogue -/

/-- Certified rewrite rules (each applied left-to-right at a position). -/
inductive Rule where
  | dnegElim | dnegIntro
  | andComm | orComm
  | andAssocL | andAssocR | orAssocL | orAssocR
  | eqSymm
  | impToOr | orToImp
  | deMorganAnd | deMorganAndInv | deMorganOr | deMorganOrInv
  | notAll | notAllInv | notEx | notExInv
  | contrapose
  | curry | uncurry
  | allAnd | allAndInv | exOr | exOrInv
  | quantSwap
  | andTrue | orFalse | impTrueL | notTrue | notFalse
  | andIdem | orIdem
  deriving Repr, DecidableEq, Inhabited

/-- All rules (used by the untrusted search and by the wire codec). -/
def Rule.all : List Rule :=
  [.dnegElim, .dnegIntro, .andComm, .orComm, .andAssocL, .andAssocR, .orAssocL, .orAssocR,
   .eqSymm, .impToOr, .orToImp, .deMorganAnd, .deMorganAndInv, .deMorganOr, .deMorganOrInv,
   .notAll, .notAllInv, .notEx, .notExInv, .contrapose, .curry, .uncurry,
   .allAnd, .allAndInv, .exOr, .exOrInv, .quantSwap,
   .andTrue, .orFalse, .impTrueL, .notTrue, .notFalse, .andIdem, .orIdem]

/-- Stable wire names. -/
def Rule.name : Rule → String
  | .dnegElim => "dneg_elim" | .dnegIntro => "dneg_intro"
  | .andComm => "and_comm" | .orComm => "or_comm"
  | .andAssocL => "and_assoc_l" | .andAssocR => "and_assoc_r"
  | .orAssocL => "or_assoc_l" | .orAssocR => "or_assoc_r"
  | .eqSymm => "eq_symm"
  | .impToOr => "imp_to_or" | .orToImp => "or_to_imp"
  | .deMorganAnd => "de_morgan_and" | .deMorganAndInv => "de_morgan_and_inv"
  | .deMorganOr => "de_morgan_or" | .deMorganOrInv => "de_morgan_or_inv"
  | .notAll => "not_all" | .notAllInv => "not_all_inv"
  | .notEx => "not_ex" | .notExInv => "not_ex_inv"
  | .contrapose => "contrapose"
  | .curry => "curry" | .uncurry => "uncurry"
  | .allAnd => "all_and" | .allAndInv => "all_and_inv"
  | .exOr => "ex_or" | .exOrInv => "ex_or_inv"
  | .quantSwap => "quant_swap"
  | .andTrue => "and_true" | .orFalse => "or_false" | .impTrueL => "imp_true_l"
  | .notTrue => "not_true" | .notFalse => "not_false"
  | .andIdem => "and_idem" | .orIdem => "or_idem"

/-- Decode a rule name. -/
def Rule.ofName (s : String) : Option Rule := Rule.all.find? (fun r => r.name == s)

/-- Apply a rule at the root (`none` if the pattern does not match). -/
def Rule.apply : Rule → NFormula → Option NFormula
  | .dnegElim, .not (.not φ) => some φ
  | .dnegIntro, φ => some (.not (.not φ))
  | .andComm, .and φ ψ => some (.and ψ φ)
  | .orComm, .or φ ψ => some (.or ψ φ)
  | .andAssocL, .and φ (.and ψ χ) => some (.and (.and φ ψ) χ)
  | .andAssocR, .and (.and φ ψ) χ => some (.and φ (.and ψ χ))
  | .orAssocL, .or φ (.or ψ χ) => some (.or (.or φ ψ) χ)
  | .orAssocR, .or (.or φ ψ) χ => some (.or φ (.or ψ χ))
  | .eqSymm, .eq a b => some (.eq b a)
  | .impToOr, .imp φ ψ => some (.or (.not φ) ψ)
  | .orToImp, .or (.not φ) ψ => some (.imp φ ψ)
  | .deMorganAnd, .not (.and φ ψ) => some (.or (.not φ) (.not ψ))
  | .deMorganAndInv, .or (.not φ) (.not ψ) => some (.not (.and φ ψ))
  | .deMorganOr, .not (.or φ ψ) => some (.and (.not φ) (.not ψ))
  | .deMorganOrInv, .and (.not φ) (.not ψ) => some (.not (.or φ ψ))
  | .notAll, .not (.quant .all s φ) => some (.quant .ex s (.not φ))
  | .notAllInv, .quant .ex s (.not φ) => some (.not (.quant .all s φ))
  | .notEx, .not (.quant .ex s φ) => some (.quant .all s (.not φ))
  | .notExInv, .quant .all s (.not φ) => some (.not (.quant .ex s φ))
  | .contrapose, .imp φ ψ => some (.imp (.not ψ) (.not φ))
  | .curry, .imp (.and φ ψ) χ => some (.imp φ (.imp ψ χ))
  | .uncurry, .imp φ (.imp ψ χ) => some (.imp (.and φ ψ) χ)
  | .allAnd, .quant .all s (.and φ ψ) => some (.and (.quant .all s φ) (.quant .all s ψ))
  | .allAndInv, .and (.quant .all s φ) (.quant .all t ψ) =>
    if s = t then some (.quant .all s (.and φ ψ)) else none
  | .exOr, .quant .ex s (.or φ ψ) => some (.or (.quant .ex s φ) (.quant .ex s ψ))
  | .exOrInv, .or (.quant .ex s φ) (.quant .ex t ψ) =>
    if s = t then some (.quant .ex s (.or φ ψ)) else none
  | .quantSwap, .quant q s (.quant q' t φ) =>
    if q = q' then some (.quant q t (.quant q s (NFormula.swapBV 0 φ))) else none
  | .andTrue, .and φ .tt => some φ
  | .orFalse, .or φ .ff => some φ
  | .impTrueL, .imp .tt φ => some φ
  | .notTrue, .not .tt => some .ff
  | .notFalse, .not .ff => some .tt
  | .andIdem, .and φ ψ => if φ = ψ then some φ else none
  | .orIdem, .or φ ψ => if φ = ψ then some φ else none
  | _, _ => none

section Classical
open Classical

theorem quantSwap_sound (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom) (q : Quant)
    (s t : SortId) (φ : NFormula) :
    NFormula.denote M ρ env (.quant q s (.quant q t φ)) ↔
      NFormula.denote M ρ env (.quant q t (.quant q s (NFormula.swapBV 0 φ))) := by
  cases q with
  | all =>
    simp only [NFormula.denote, NFormula.swapBV_denote, consEnv_swap0]
    exact ⟨fun h d₂ h₂ d₁ h₁ => h d₁ h₁ d₂ h₂, fun h d₁ h₁ d₂ h₂ => h d₂ h₂ d₁ h₁⟩
  | ex =>
    simp only [NFormula.denote, NFormula.swapBV_denote, consEnv_swap0]
    exact ⟨fun ⟨d₁, h₁, d₂, h₂, h⟩ => ⟨d₂, h₂, d₁, h₁, h⟩,
      fun ⟨d₂, h₂, d₁, h₁, h⟩ => ⟨d₁, h₁, d₂, h₂, h⟩⟩

/-- **Every rule application is a semantic equivalence** (classical first-order logic,
    sorts possibly empty). -/
theorem Rule.apply_sound : ∀ (r : Rule) (φ ψ : NFormula), r.apply φ = some ψ →
    NFormula.SemEquiv φ ψ := by
  intro r φ ψ h M ρ env
  unfold Rule.apply at h
  split at h <;> (try (split at h)) <;> (try (cases h))
  all_goals (try subst_vars)
  all_goals (try (simp only [NFormula.denote]; done))
  all_goals (try (exact quantSwap_sound M ρ env _ _ _ _))
  all_goals (try (simp [NFormula.denote]; done))
  all_goals simp only [NFormula.denote]
  all_goals first
    | exact And.comm
    | exact Or.comm
    | exact and_assoc.symm
    | exact and_assoc
    | exact or_assoc.symm
    | exact or_assoc
    | exact eq_comm
    | exact ⟨fun h => (Classical.em _).elim (fun a => Or.inr (h a)) Or.inl,
        fun h a => h.elim (fun n => absurd a n) id⟩
    | exact ⟨fun h a => h.elim (fun n => absurd a n) id,
        fun h => (Classical.em _).elim (fun a => Or.inr (h a)) Or.inl⟩
    | exact ⟨fun h => (Classical.em _).elim (fun a => Or.inr (fun b => h ⟨a, b⟩)) Or.inl,
        fun h ⟨a, b⟩ => h.elim (fun n => n a) (fun n => n b)⟩
    | exact ⟨fun h ⟨a, b⟩ => h.elim (fun n => n a) (fun n => n b),
        fun h => (Classical.em _).elim (fun a => Or.inr (fun b => h ⟨a, b⟩)) Or.inl⟩
    | exact ⟨fun h nb a => nb (h a), fun h a => Classical.byContradiction (fun nb => h nb a)⟩
    | exact ⟨fun h => ⟨fun d hd => (h d hd).1, fun d hd => (h d hd).2⟩,
        fun h d hd => ⟨h.1 d hd, h.2 d hd⟩⟩
    | exact ⟨fun h d hd => ⟨h.1 d hd, h.2 d hd⟩,
        fun h => ⟨fun d hd => (h d hd).1, fun d hd => (h d hd).2⟩⟩
    | exact ⟨fun ⟨d, hd, h⟩ => h.elim (fun a => Or.inl ⟨d, hd, a⟩) (fun b => Or.inr ⟨d, hd, b⟩),
        fun h => h.elim (fun ⟨d, hd, a⟩ => ⟨d, hd, Or.inl a⟩) (fun ⟨d, hd, b⟩ => ⟨d, hd, Or.inr b⟩)⟩
    | exact ⟨fun h => h.elim (fun ⟨d, hd, a⟩ => ⟨d, hd, Or.inl a⟩) (fun ⟨d, hd, b⟩ => ⟨d, hd, Or.inr b⟩),
        fun ⟨d, hd, h⟩ => h.elim (fun a => Or.inl ⟨d, hd, a⟩) (fun b => Or.inr ⟨d, hd, b⟩)⟩

end Classical

/-! ## Rewriting at a position (congruence) -/

/-- Apply a rule at a path.  Path components select children: `0` for the body of `¬` and of
    a quantifier, `0`/`1` for the left/right operand of `∧`, `∨`, `→`. -/
def rewriteAt (r : Rule) : List Nat → NFormula → Option NFormula
  | [], φ => r.apply φ
  | 0 :: p, .not φ => (rewriteAt r p φ).map NFormula.not
  | 0 :: p, .and φ ψ => (rewriteAt r p φ).map (fun φ' => .and φ' ψ)
  | 1 :: p, .and φ ψ => (rewriteAt r p ψ).map (NFormula.and φ)
  | 0 :: p, .or φ ψ => (rewriteAt r p φ).map (fun φ' => .or φ' ψ)
  | 1 :: p, .or φ ψ => (rewriteAt r p ψ).map (NFormula.or φ)
  | 0 :: p, .imp φ ψ => (rewriteAt r p φ).map (fun φ' => .imp φ' ψ)
  | 1 :: p, .imp φ ψ => (rewriteAt r p ψ).map (NFormula.imp φ)
  | 0 :: p, .quant q s φ => (rewriteAt r p φ).map (NFormula.quant q s)
  | _, _ => none

theorem option_map_eq_some {α β : Type} {f : α → β} {o : Option α} {b : β}
    (h : o.map f = some b) : ∃ a, o = some a ∧ f a = b := by
  cases o with
  | none => cases h
  | some a => exact ⟨a, rfl, Option.some.inj h⟩

/-- **Congruence**: rewriting with a certified rule at any position (including under any
    number of binders) is a semantic equivalence. -/
theorem rewriteAt_sound (r : Rule) : ∀ (p : List Nat) (φ ψ : NFormula),
    rewriteAt r p φ = some ψ → NFormula.SemEquiv φ ψ
  | [], φ, ψ, h => Rule.apply_sound r φ ψ h
  | 0 :: p, .not φ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact not_congr (rewriteAt_sound r p φ φ' h1 M ρ env)
  | 0 :: p, .and φ χ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact and_congr (rewriteAt_sound r p φ φ' h1 M ρ env) Iff.rfl
  | 1 :: p, .and χ φ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact and_congr Iff.rfl (rewriteAt_sound r p φ φ' h1 M ρ env)
  | 0 :: p, .or φ χ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact or_congr (rewriteAt_sound r p φ φ' h1 M ρ env) Iff.rfl
  | 1 :: p, .or χ φ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact or_congr Iff.rfl (rewriteAt_sound r p φ φ' h1 M ρ env)
  | 0 :: p, .imp φ χ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact imp_congr (rewriteAt_sound r p φ φ' h1 M ρ env) Iff.rfl
  | 1 :: p, .imp χ φ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env; exact imp_congr Iff.rfl (rewriteAt_sound r p φ φ' h1 M ρ env)
  | 0 :: p, .quant q s φ, ψ, h => by
    obtain ⟨φ', h1, rfl⟩ := option_map_eq_some h
    intro M ρ env
    cases q with
    | all =>
      simp only [NFormula.denote]
      exact forall_congr' (fun d => imp_congr Iff.rfl (rewriteAt_sound r p φ φ' h1 M ρ _))
    | ex =>
      simp only [NFormula.denote]
      exact exists_congr (fun d => and_congr Iff.rfl (rewriteAt_sound r p φ φ' h1 M ρ _))
  | 0 :: _, .tt, _, h | 0 :: _, .ff, _, h | 0 :: _, .pred _ _, _, h | 0 :: _, .eq _ _, _, h
  | 0 :: _, .unsupported _, _, h => by cases h
  | 1 :: _, .tt, _, h | 1 :: _, .ff, _, h | 1 :: _, .pred _ _, _, h | 1 :: _, .eq _ _, _, h
  | 1 :: _, .unsupported _, _, h | 1 :: _, .not _, _, h | 1 :: _, .quant _ _ _, _, h => by cases h
  | (_ + 2) :: _, φ, _, h => by cases φ <;> cases h

/-! ## Claim-level steps and certificates -/

/-- Which formula of a nameless claim a step rewrites. -/
inductive Target where
  | concl
  | assm (j : Nat)
  deriving Repr, DecidableEq, Inhabited

/-- One certificate step: apply `rule` at `path` inside `target`. -/
structure Step where
  target : Target
  path : List Nat
  rule : Rule
  deriving Repr, DecidableEq, Inhabited

/-- Replay one step on a nameless claim. -/
def NClaim.applyStep (n : NClaim) (st : Step) : Option NClaim :=
  match st.target with
  | .concl => (rewriteAt st.rule st.path n.conclusion).map
      (fun c => { n with conclusion := c })
  | .assm j =>
    match n.assumptions[j]? with
    | some a => (rewriteAt st.rule st.path a).map
        (fun a' => { n with assumptions := n.assumptions.set j a' })
    | none => none

/-- Replay a step list (fails closed on the first step that does not apply). -/
def NClaim.applySteps (n : NClaim) : List Step → Option NClaim
  | [] => some n
  | st :: sts =>
    match n.applyStep st with
    | some n' => n'.applySteps sts
    | none => none

/-- **A semantic-equivalence certificate**: a rewrite derivation for each side.  The two
    derivations must end in `NClaim.Equiv`-equivalent nameless claims. -/
structure EquivCert where
  left : List Step
  right : List Step
  deriving Repr, DecidableEq, Inhabited

/-- **The certificate checker** (replay only; no search). -/
def checkCert (c : EquivCert) (n m : NClaim) : Bool :=
  match n.applySteps c.left, m.applySteps c.right with
  | some a, some b => a.equivB b
  | _, _ => false

/-- Semantic equivalence of nameless claims (every model, valuation and environment). -/
def NClaim.SemEquiv (n m : NClaim) : Prop :=
  ∀ (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom), n.denote M ρ env ↔ m.denote M ρ env

theorem NClaim.SemEquiv.refl (n : NClaim) : NClaim.SemEquiv n n := fun _ _ _ => Iff.rfl

theorem NClaim.SemEquiv.symm {n m : NClaim} (h : NClaim.SemEquiv n m) : NClaim.SemEquiv m n :=
  fun M ρ env => (h M ρ env).symm

theorem NClaim.SemEquiv.trans {n m k : NClaim} (h₁ : NClaim.SemEquiv n m)
    (h₂ : NClaim.SemEquiv m k) : NClaim.SemEquiv n k :=
  fun M ρ env => (h₁ M ρ env).trans (h₂ M ρ env)

theorem forall_mem_set_iff {α : Type} (P : α → Prop) :
    ∀ (l : List α) (j : Nat) (a b : α), l[j]? = some a → (P a ↔ P b) →
      ((∀ x ∈ l.set j b, P x) ↔ (∀ x ∈ l, P x))
  | [], j, a, b, h, _ => by simp at h
  | y :: ys, 0, a, b, h, hab => by
    simp only [List.getElem?_cons_zero, Option.some.injEq] at h
    subst h
    simp only [List.set_cons_zero, List.forall_mem_cons]
    exact and_congr hab.symm Iff.rfl
  | y :: ys, j + 1, a, b, h, hab => by
    simp only [List.getElem?_cons_succ] at h
    simp only [List.set_cons_succ, List.forall_mem_cons]
    exact and_congr Iff.rfl (forall_mem_set_iff P ys j a b h hab)

/-- Replaying one step preserves claim denotation. -/
theorem NClaim.applyStep_sound (n n' : NClaim) (st : Step) (h : n.applyStep st = some n') :
    NClaim.SemEquiv n n' := by
  intro M ρ env
  obtain ⟨target, path, rule⟩ := st
  cases target with
  | concl =>
    simp only [NClaim.applyStep] at h
    obtain ⟨c, hc, rfl⟩ := option_map_eq_some h
    unfold NClaim.denote
    apply ndenoteParams_congr
    intro e
    exact imp_congr Iff.rfl (rewriteAt_sound _ _ _ _ hc M ρ e)
  | assm j =>
    simp only [NClaim.applyStep] at h
    cases ha : n.assumptions[j]? with
    | none => rw [ha] at h; cases h
    | some a =>
      rw [ha] at h
      obtain ⟨a', ha', rfl⟩ := option_map_eq_some h
      unfold NClaim.denote
      apply ndenoteParams_congr
      intro e
      exact imp_congr (forall_mem_set_iff (NFormula.denote M ρ e) n.assumptions j a a' ha
        (rewriteAt_sound _ _ _ _ ha' M ρ e)).symm Iff.rfl

/-- Replaying a step list preserves claim denotation. -/
theorem NClaim.applySteps_sound : ∀ (sts : List Step) (n n' : NClaim),
    n.applySteps sts = some n' → NClaim.SemEquiv n n'
  | [], n, n', h => by cases h; exact NClaim.SemEquiv.refl n
  | st :: sts, n, n', h => by
    unfold NClaim.applySteps at h
    split at h
    · rename_i m hm
      exact (NClaim.applyStep_sound n m st hm).trans (NClaim.applySteps_sound sts m n' h)
    · cases h

/-- **Soundness of the certificate checker on nameless claims.** -/
theorem checkCert_sound {c : EquivCert} {n m : NClaim} (h : checkCert c n m = true) :
    NClaim.SemEquiv n m := by
  unfold checkCert at h
  split at h
  · rename_i a b ha hb
    have hab : a.Equiv b := (NClaim.equivB_iff a b).mp h
    have hmid : NClaim.SemEquiv a b := fun M ρ env => ndenoteClaim_congr_assumptions hab M ρ env
    exact (NClaim.applySteps_sound _ _ _ ha).trans
      (hmid.trans (NClaim.applySteps_sound _ _ _ hb).symm)
  · cases h

/-- **Translation certificate soundness.**  If the checker accepts a certificate relating the
    normal form of the selected interpretation `I` and the normal form of the candidate `C`,
    then for **every** model `M` and **every** valuation `ρ` the two claims have logically
    equivalent denotations. -/
theorem translation_certificate_sound {cert : EquivCert} {I C : SemanticClaim}
    (h : checkCert cert I.normalize C.normalize = true) (M : Model) (ρ : String → M.Dom) :
    I.denote M ρ ↔ C.denote M ρ := by
  let env : Nat → M.Dom := fun _ => ρ ""
  rw [SemanticClaim.normalize_denote M ρ env I, SemanticClaim.normalize_denote M ρ env C]
  exact checkCert_sound h M ρ env

/-- Same statement under the name used by the v2 contract. -/
theorem certificate_acceptance_implies_semantic_preservation {cert : EquivCert}
    {I C : SemanticClaim} (h : checkCert cert I.normalize C.normalize = true) :
    ∀ (M : Model) (ρ : String → M.Dom), I.denote M ρ ↔ C.denote M ρ :=
  translation_certificate_sound h

/-- **Invalid derivations are rejected**: if a step of either derivation fails to replay, or
    the replayed endpoints are not `Equiv`, the checker rejects. -/
theorem certificate_checker_rejects_invalid_derivations (c : EquivCert) (n m : NClaim) :
    (n.applySteps c.left = none → checkCert c n m = false) ∧
    (m.applySteps c.right = none → checkCert c n m = false) ∧
    (∀ a b, n.applySteps c.left = some a → m.applySteps c.right = some b → ¬ a.Equiv b →
      checkCert c n m = false) := by
  refine ⟨fun h => ?_, fun h => ?_, fun a b ha hb hn => ?_⟩
  · unfold checkCert; rw [h]
  · unfold checkCert; rw [h]; cases n.applySteps c.left <;> rfl
  · unfold checkCert; rw [ha, hb]
    show a.equivB b = false
    cases hab : a.equivB b
    · rfl
    · exact absurd ((NClaim.equivB_iff a b).mp hab) hn

/-- **No certificate exists for semantically inequivalent claims**: if some model and
    valuation distinguish `I` and `C`, every certificate is rejected. -/
theorem inequivalent_claims_admit_no_certificate {I C : SemanticClaim} {M : Model}
    {ρ : String → M.Dom} (h : ¬ (I.denote M ρ ↔ C.denote M ρ)) (cert : EquivCert) :
    checkCert cert I.normalize C.normalize = false := by
  cases hc : checkCert cert I.normalize C.normalize
  · rfl
  · exact absurd (translation_certificate_sound hc M ρ) h

/-- **An untrusted certificate generator cannot forge certified equivalence**: for an
    arbitrary search procedure (no assumption whatsoever about it), every certificate it
    outputs that the checker accepts is semantically sound. -/
theorem untrusted_translation_search_cannot_forge_certified_equivalence
    (search : SemanticClaim → SemanticClaim → List EquivCert) (I C : SemanticClaim)
    (h : (search I C).any (fun cert => checkCert cert I.normalize C.normalize) = true) :
    ∀ (M : Model) (ρ : String → M.Dom), I.denote M ρ ↔ C.denote M ρ := by
  obtain ⟨cert, _, hc⟩ := List.any_eq_true.mp h
  exact translation_certificate_sound hc

/-- The empty certificate checks exactly the v1 normal-form equivalence, so every v1
    acceptance has a (trivial) v2 certificate. -/
theorem checkCert_empty (n m : NClaim) : checkCert ⟨[], []⟩ n m = n.equivB m := rfl

end PCS.V2.Semantic
