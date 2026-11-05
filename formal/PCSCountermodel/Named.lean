import PCSCountermodel.Core

/-!
# Named-variable syntax and its lowering to de Bruijn `Formula`

`NFormula` mirrors the game's recursive JSON AST (fields `op, p, x, y, f, a, b`) *after*
parsing: predicates and variables are strings. Byte parsing, JSON schema validation and the
correspondence between JSON objects and `NFormula` values are **outside** the scope of the
theorems below.

* `lookupIdx ctx x` resolves a name to the index of its **first** (innermost) occurrence in
  the binder context, so a newly bound name shadows outer ones.
* `lower ctx f` translates to `Formula ctx.length`, rejecting (`none`) unbound variables and
  unknown predicate names.
* `NHolds` is an independent Tarskian semantics for named formulas, with total valuations
  `String → Fin n` updated at binders.
* `lower_sound` / `lower_closed_sound`: lowering preserves semantics.
* `lower_isSome_iff`: lowering succeeds exactly for well-scoped formulas.
* `namedChecker_sound`: the checker run through the lowering is sound and complete with
  respect to the named semantics.
-/

namespace PCSCountermodel

/-- Named formulas (post-parse image of the game AST). -/
inductive NFormula where
  | pred (p : String) (x : String)
  | rel (x y : String)
  | not (a : NFormula)
  | and (a b : NFormula)
  | or (a b : NFormula)
  | imp (a b : NFormula)
  | all (x : String) (f : NFormula)
  | ex (x : String) (f : NFormula)
  deriving Repr, DecidableEq

/-- Predicate names accepted by the lowering. -/
def parsePred : String → Option UPred
  | "P" => some .P
  | "Q" => some .Q
  | _ => none

/-- Resolve a name to its innermost binder (index of the first occurrence). -/
def lookupIdx : (ctx : List String) → String → Option (Fin ctx.length)
  | [], _ => none
  | y :: ctx, x => if x = y then some ⟨0, by simp⟩ else (lookupIdx ctx x).map Fin.succ

/-- Lower a named formula under binder context `ctx` (innermost binder first). -/
def lower : (ctx : List String) → NFormula → Option (Formula ctx.length)
  | ctx, .pred p x =>
      match parsePred p, lookupIdx ctx x with
      | some q, some i => some (.pred q i)
      | _, _ => none
  | ctx, .rel x y =>
      match lookupIdx ctx x, lookupIdx ctx y with
      | some i, some j => some (.rel i j)
      | _, _ => none
  | ctx, .not a => (lower ctx a).map .not
  | ctx, .and a b =>
      match lower ctx a, lower ctx b with
      | some ga, some gb => some (.and ga gb)
      | _, _ => none
  | ctx, .or a b =>
      match lower ctx a, lower ctx b with
      | some ga, some gb => some (.or ga gb)
      | _, _ => none
  | ctx, .imp a b =>
      match lower ctx a, lower ctx b with
      | some ga, some gb => some (.imp ga gb)
      | _, _ => none
  | ctx, .all x f => (lower (x :: ctx) f).map .all
  | ctx, .ex x f => (lower (x :: ctx) f).map .ex

/-! ### Independent named semantics -/

/-- Valuation update at a binder. -/
def update {n : Nat} (ρ : String → Fin n) (x : String) (d : Fin n) : String → Fin n :=
  fun y => if y = x then d else ρ y

/-- Named predicate interpretation (unknown names are false; the lowering rejects them). -/
def NPred {n : Nat} (w : World n) (p : String) (d : Fin n) : Prop :=
  (p = "P" ∧ w.P d = true) ∨ (p = "Q" ∧ w.Q d = true)

/-- Tarskian satisfaction for named formulas. -/
def NHolds {n : Nat} (w : World n) : (String → Fin n) → NFormula → Prop
  | ρ, .pred p x => NPred w p (ρ x)
  | ρ, .rel x y => w.R (ρ x) (ρ y) = true
  | ρ, .not a => ¬ NHolds w ρ a
  | ρ, .and a b => NHolds w ρ a ∧ NHolds w ρ b
  | ρ, .or a b => NHolds w ρ a ∨ NHolds w ρ b
  | ρ, .imp a b => NHolds w ρ a → NHolds w ρ b
  | ρ, .all x f => ∀ d : Fin n, NHolds w (update ρ x d) f
  | ρ, .ex x f => ∃ d : Fin n, NHolds w (update ρ x d) f

/-- A valuation `ρ` and a de Bruijn environment `e` agree on context `ctx`. -/
def Agree {n : Nat} (ctx : List String) (ρ : String → Fin n) (e : Env ctx.length n) : Prop :=
  ∀ x i, lookupIdx ctx x = some i → ρ x = e i

theorem agree_cons {n : Nat} {ctx : List String} {ρ : String → Fin n} {e : Env ctx.length n}
    (h : Agree ctx ρ e) (x : String) (d : Fin n) :
    Agree (x :: ctx) (update ρ x d) (extend e d) := by
  intro y i hy
  simp only [lookupIdx] at hy
  unfold update
  by_cases hxy : y = x
  · simp only [hxy, if_pos] at hy ⊢
    cases hy; rfl
  · simp only [hxy, if_false] at hy ⊢
    cases hl : lookupIdx ctx y with
    | none => rw [hl] at hy; cases hy
    | some j =>
        rw [hl] at hy; cases hy
        exact h y j hl

theorem parsePred_sound {n : Nat} (w : World n) {p : String} {q : UPred}
    (h : parsePred p = some q) (d : Fin n) : NPred w p d ↔ w.unary q d = true := by
  unfold parsePred at h
  split at h
  · cases h; simp [NPred, World.unary]
  · cases h; simp [NPred, World.unary]
  · cases h

/-- **Lowering preserves semantics** under any agreeing valuation/environment pair. -/
theorem lower_sound {n : Nat} (w : World n) :
    ∀ (f : NFormula) (ctx : List String) (g : Formula ctx.length),
      lower ctx f = some g →
      ∀ (ρ : String → Fin n) (e : Env ctx.length n), Agree ctx ρ e →
        (NHolds w ρ f ↔ Holds w e g) := by
  intro f
  induction f with
  | pred p x =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      split at hg
      · rename_i q i hq hi
        cases hg
        simp only [NHolds, Holds]
        rw [hag x i hi]
        exact parsePred_sound w hq _
      · cases hg
  | rel x y =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      split at hg
      · rename_i i j hi hj
        cases hg
        simp only [NHolds, Holds]
        rw [hag x i hi, hag y j hj]
      · cases hg
  | not a ih =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      cases ha : lower ctx a with
      | none => rw [ha] at hg; cases hg
      | some ga =>
          rw [ha] at hg; cases hg
          simp only [NHolds, Holds]
          rw [ih ctx ga ha ρ e hag]
  | and a b iha ihb =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      split at hg
      · rename_i ga gb ha hb
        cases hg
        simp only [NHolds, Holds]
        rw [iha ctx ga ha ρ e hag, ihb ctx gb hb ρ e hag]
      · cases hg
  | or a b iha ihb =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      split at hg
      · rename_i ga gb ha hb
        cases hg
        simp only [NHolds, Holds]
        rw [iha ctx ga ha ρ e hag, ihb ctx gb hb ρ e hag]
      · cases hg
  | imp a b iha ihb =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      split at hg
      · rename_i ga gb ha hb
        cases hg
        simp only [NHolds, Holds]
        rw [iha ctx ga ha ρ e hag, ihb ctx gb hb ρ e hag]
      · cases hg
  | all x f ih =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      cases hf : lower (x :: ctx) f with
      | none => rw [hf] at hg; cases hg
      | some gf =>
          rw [hf] at hg; cases hg
          simp only [NHolds, Holds]
          exact forall_congr' fun d => ih (x :: ctx) gf hf _ _ (agree_cons hag x d)
  | ex x f ih =>
      intro ctx g hg ρ e hag
      simp only [lower] at hg
      cases hf : lower (x :: ctx) f with
      | none => rw [hf] at hg; cases hg
      | some gf =>
          rw [hf] at hg; cases hg
          simp only [NHolds, Holds]
          exact exists_congr fun d => ih (x :: ctx) gf hf _ _ (agree_cons hag x d)

/-- **Closed lowering preserves semantics** for every valuation. -/
theorem lower_closed_sound {n : Nat} (w : World n) {f : NFormula} {g : Formula 0}
    (hg : lower [] f = some g) (ρ : String → Fin n) :
    NHolds w ρ f ↔ Holds w emptyEnv g :=
  lower_sound w f [] g hg ρ emptyEnv (fun _ _ h => by simp [lookupIdx] at h)

/-! ### Scope checking: lowering succeeds exactly on well-scoped formulas -/

/-- Every variable occurrence is bound by an enclosing binder or listed in `ctx`, and every
predicate name is `P` or `Q`. -/
def WellScoped : List String → NFormula → Prop
  | ctx, .pred p x => (p = "P" ∨ p = "Q") ∧ x ∈ ctx
  | ctx, .rel x y => x ∈ ctx ∧ y ∈ ctx
  | ctx, .not a => WellScoped ctx a
  | ctx, .and a b => WellScoped ctx a ∧ WellScoped ctx b
  | ctx, .or a b => WellScoped ctx a ∧ WellScoped ctx b
  | ctx, .imp a b => WellScoped ctx a ∧ WellScoped ctx b
  | ctx, .all x f => WellScoped (x :: ctx) f
  | ctx, .ex x f => WellScoped (x :: ctx) f

theorem lookupIdx_isSome_iff : ∀ (ctx : List String) (x : String),
    (lookupIdx ctx x).isSome = true ↔ x ∈ ctx := by
  intro ctx x
  induction ctx with
  | nil => simp [lookupIdx]
  | cons y ctx ih =>
      simp only [lookupIdx, List.mem_cons]
      by_cases h : x = y
      · simp [h]
      · simp [h, ih]

theorem parsePred_isSome_iff (p : String) : (parsePred p).isSome = true ↔ (p = "P" ∨ p = "Q") := by
  unfold parsePred
  split
  · simp
  · simp
  · rename_i h1 h2
    simp only [Option.isSome_none, Bool.false_eq_true, false_iff]
    intro h; rcases h with h | h
    · exact h1 h
    · exact h2 h

/-- **Lowering rejects exactly the ill-scoped formulas** (unbound variables or unknown
predicate names). -/
theorem lower_isSome_iff : ∀ (f : NFormula) (ctx : List String),
    (lower ctx f).isSome = true ↔ WellScoped ctx f := by
  intro f
  induction f with
  | pred p x =>
      intro ctx
      simp only [lower, WellScoped]
      rw [← parsePred_isSome_iff, ← lookupIdx_isSome_iff]
      cases parsePred p <;> cases lookupIdx ctx x <;> simp
  | rel x y =>
      intro ctx
      simp only [lower, WellScoped]
      rw [← lookupIdx_isSome_iff, ← lookupIdx_isSome_iff]
      cases lookupIdx ctx x <;> cases lookupIdx ctx y <;> simp
  | not a ih => intro ctx; simp [lower, WellScoped, ih]
  | and a b iha ihb =>
      intro ctx; simp only [lower, WellScoped]
      rw [← iha, ← ihb]
      cases lower ctx a <;> cases lower ctx b <;> simp
  | or a b iha ihb =>
      intro ctx; simp only [lower, WellScoped]
      rw [← iha, ← ihb]
      cases lower ctx a <;> cases lower ctx b <;> simp
  | imp a b iha ihb =>
      intro ctx; simp only [lower, WellScoped]
      rw [← iha, ← ihb]
      cases lower ctx a <;> cases lower ctx b <;> simp
  | all x f ih => intro ctx; simp [lower, WellScoped, ih]
  | ex x f ih => intro ctx; simp [lower, WellScoped, ih]

/-! ### The checker on named input -/

/-- Lower both closed named formulas and run the checker; `none` if either is rejected. -/
def namedChecker {n : Nat} (w : World n) (original proposal : NFormula) : Option Bool :=
  match lower [] original, lower [] proposal with
  | some a, some b => some (checker w a b)
  | _, _ => none

/-- **Named checker soundness/completeness.** If both formulas lower, the checker's verdict
is `true` exactly when the named statements disagree (for any valuation). -/
theorem namedChecker_sound {n : Nat} (w : World n) {original proposal : NFormula} {c : Bool}
    (h : namedChecker w original proposal = some c) (ρ : String → Fin n) :
    c = true ↔ ¬ (NHolds w ρ original ↔ NHolds w ρ proposal) := by
  unfold namedChecker at h
  split at h
  · rename_i a b ha hb
    cases h
    rw [lower_closed_sound w ha ρ, lower_closed_sound w hb ρ]
    exact checker_iff w a b
  · cases h

/-- The named checker returns a verdict exactly when both formulas are closed and well-scoped. -/
theorem namedChecker_isSome_iff {n : Nat} (w : World n) (original proposal : NFormula) :
    (namedChecker w original proposal).isSome = true ↔
      WellScoped [] original ∧ WellScoped [] proposal := by
  unfold namedChecker
  rw [← lower_isSome_iff, ← lower_isSome_iff]
  cases lower [] original <;> cases lower [] proposal <;> simp

end PCSCountermodel
