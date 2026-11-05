import Std

/-!
# The primitive proof-action calculus and its library extension

* `Fm` — propositional formulas over parameter atoms; `Fm.den` — independent denotation into
  Lean `Prop`; `Fm.subst` — parameter instantiation.
* `Pf` — proof terms (the receiver-approved primitive actions: hypothesis, `⊤`-intro,
  `⊥`-elim, conjunction intro/projections, disjunction intros, **two-branch** disjunction
  elimination, implication intro/apply) plus `lem j σ`, a reference to library entry `j`
  instantiated with parameters `σ`.
* `infer lib Γ p` — the small checker.  A disjunction elimination checks *both* named
  branches and requires them to prove the same conclusion; no branch can be discarded.
* `infer_sound` — a checked proof denotes a true Lean proposition in every valuation
  satisfying the context, provided every library statement is schematically valid.
-/

namespace PCSReasoningLibrary

inductive Fm where
  | atom (i : Nat)
  | top
  | bot
  | and (a b : Fm)
  | or (a b : Fm)
  | imp (a b : Fm)
  deriving DecidableEq, Repr

namespace Fm

def den (v : Nat → Prop) : Fm → Prop
  | atom i => v i
  | top => True
  | bot => False
  | and a b => den v a ∧ den v b
  | or a b => den v a ∨ den v b
  | imp a b => den v a → den v b

def subst (s : Nat → Fm) : Fm → Fm
  | atom i => s i
  | top => top
  | bot => bot
  | and a b => and (subst s a) (subst s b)
  | or a b => or (subst s a) (subst s b)
  | imp a b => imp (subst s a) (subst s b)

theorem den_subst (v : Nat → Prop) (s : Nat → Fm) (f : Fm) :
    den v (subst s f) ↔ den (fun i => den v (s i)) f := by
  induction f with
  | atom i => exact Iff.rfl
  | top => exact Iff.rfl
  | bot => exact Iff.rfl
  | and a b iha ihb => simp only [subst, den, iha, ihb]
  | or a b iha ihb => simp only [subst, den, iha, ihb]
  | imp a b iha ihb => simp only [subst, den, iha, ihb]

def size : Fm → Nat
  | atom _ | top | bot => 1
  | and a b | or a b | imp a b => a.size + b.size + 1

end Fm

/-- Parameter instantiation: parameter `i ↦ σ[i]`, other atoms unchanged. -/
def inst (σ : List Fm) : Nat → Fm := fun i => σ.getD i (.atom i)

inductive Pf where
  | hyp (φ : Fm)
  | topI
  | botE (φ : Fm) (p : Pf)
  | andI (p q : Pf)
  | andL (p : Pf)
  | andR (p : Pf)
  | orL (b : Fm) (p : Pf)
  | orR (a : Fm) (p : Pf)
  | orE (p : Pf) (a b : Fm) (q r : Pf)
  | lam (φ : Fm) (p : Pf)
  | app (p q : Pf)
  | lem (j : Nat) (σ : List Fm)
  deriving DecidableEq, Repr

namespace Pf

def size : Pf → Nat
  | hyp _ | topI | lem _ _ => 1
  | botE _ p | andL p | andR p | orL _ p | orR _ p | lam _ p => p.size + 1
  | andI p q | app p q => p.size + q.size + 1
  | orE p _ _ q r => p.size + q.size + r.size + 1

/-- Uses no library reference. -/
def Primitive : Pf → Prop
  | hyp _ | topI => True
  | lem _ _ => False
  | botE _ p | andL p | andR p | orL _ p | orR _ p | lam _ p => p.Primitive
  | andI p q | app p q => p.Primitive ∧ q.Primitive
  | orE p _ _ q r => p.Primitive ∧ q.Primitive ∧ r.Primitive

def subst (s : Nat → Fm) : Pf → Pf
  | hyp φ => hyp (φ.subst s)
  | topI => topI
  | botE φ p => botE (φ.subst s) (subst s p)
  | andI p q => andI (subst s p) (subst s q)
  | andL p => andL (subst s p)
  | andR p => andR (subst s p)
  | orL b p => orL (b.subst s) (subst s p)
  | orR a p => orR (a.subst s) (subst s p)
  | orE p a b q r => orE (subst s p) (a.subst s) (b.subst s) (subst s q) (subst s r)
  | lam φ p => lam (φ.subst s) (subst s p)
  | app p q => app (subst s p) (subst s q)
  | lem j σ => lem j (σ.map (·.subst s))

end Pf

/-- The checker.  `lib` lists the statements of the admitted library entries. -/
def infer (lib : List Fm) (Γ : List Fm) : Pf → Option Fm
  | .hyp φ => if φ ∈ Γ then some φ else none
  | .topI => some .top
  | .botE φ p => if infer lib Γ p = some .bot then some φ else none
  | .andI p q =>
    match infer lib Γ p, infer lib Γ q with
    | some a, some b => some (.and a b)
    | _, _ => none
  | .andL p =>
    match infer lib Γ p with
    | some (.and a _) => some a
    | _ => none
  | .andR p =>
    match infer lib Γ p with
    | some (.and _ b) => some b
    | _ => none
  | .orL b p => (infer lib Γ p).map (.or · b)
  | .orR a p => (infer lib Γ p).map (.or a ·)
  | .orE p a b q r =>
    if infer lib Γ p = some (.or a b) then
      match infer lib (a :: Γ) q, infer lib (b :: Γ) r with
      | some c1, some c2 => if c1 = c2 then some c1 else none
      | _, _ => none
    else none
  | .lam φ p => (infer lib (φ :: Γ) p).map (.imp φ ·)
  | .app p q =>
    match infer lib Γ p, infer lib Γ q with
    | some (.imp a b), some a' => if a = a' then some b else none
    | _, _ => none
  | .lem j σ => (lib[j]?).map (·.subst (inst σ))

/-- Schematic validity: true under every valuation. -/
def Valid (φ : Fm) : Prop := ∀ v, φ.den v

theorem Valid.subst {φ : Fm} (h : Valid φ) (s : Nat → Fm) : Valid (φ.subst s) :=
  fun v => (Fm.den_subst v s φ).2 (h _)

/-- **Checker soundness.** -/
theorem infer_sound {lib : List Fm} (hlib : ∀ φ ∈ lib, Valid φ) (v : Nat → Prop) :
    ∀ (p : Pf) (Γ : List Fm) (φ : Fm), (∀ ψ ∈ Γ, ψ.den v) → infer lib Γ p = some φ → φ.den v := by
  intro p
  induction p with
  | hyp ψ =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · cases h; exact hΓ _ (by assumption)
      · cases h
  | topI => intro Γ φ _ h; cases h; trivial
  | botE ψ p ih =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · rename_i hp; exact (ih Γ _ hΓ hp).elim
      · cases h
  | andI p q ihp ihq =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · rename_i a b hp hq; cases h; exact ⟨ihp Γ a hΓ hp, ihq Γ b hΓ hq⟩
      · cases h
  | andL p ih =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · rename_i a b hp; cases h; exact (ih Γ _ hΓ hp).1
      · cases h
  | andR p ih =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · rename_i a b hp; cases h; exact (ih Γ _ hΓ hp).2
      · cases h
  | orL b p ih =>
      intro Γ φ hΓ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨a, hp, rfl⟩ := h; exact Or.inl (ih Γ a hΓ hp)
  | orR a p ih =>
      intro Γ φ hΓ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨b, hp, rfl⟩ := h; exact Or.inr (ih Γ b hΓ hp)
  | orE p a b q r ihp ihq ihr =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · rename_i hp
        split at h
        · rename_i c1 c2 hq hr
          split at h
          · rename_i he; simp only [Option.some.injEq] at h; subst h
            rcases ihp Γ _ hΓ hp with ha | hb
            · exact ihq (a :: Γ) c1 (by
                intro ψ hψ; rcases List.mem_cons.1 hψ with rfl | hψ
                · exact ha
                · exact hΓ ψ hψ) hq
            · rw [he]
              exact ihr (b :: Γ) c2 (by
                intro ψ hψ; rcases List.mem_cons.1 hψ with rfl | hψ
                · exact hb
                · exact hΓ ψ hψ) hr
          · cases h
        · cases h
      · cases h
  | lam ψ p ih =>
      intro Γ φ hΓ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨b, hp, rfl⟩ := h
      intro hψ
      exact ih (ψ :: Γ) b (by
        intro χ hχ; rcases List.mem_cons.1 hχ with rfl | hχ
        · exact hψ
        · exact hΓ χ hχ) hp
  | app p q ihp ihq =>
      intro Γ φ hΓ h; simp only [infer] at h
      split at h
      · rename_i a b a' hp hq
        split at h
        · rename_i he; cases h; subst he; exact ihp Γ _ hΓ hp (ihq Γ _ hΓ hq)
        · cases h
      · cases h
  | lem j σ =>
      intro Γ φ hΓ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨ψ, hψ, rfl⟩ := h
      exact (hlib ψ (List.mem_of_getElem? hψ)).subst _ v

/-! ## Structural metatheory of the primitive calculus -/

/-- Weakening. -/
theorem infer_weaken {lib : List Fm} :
    ∀ (p : Pf) (Γ Δ : List Fm) (φ : Fm), (∀ ψ ∈ Γ, ψ ∈ Δ) → infer lib Γ p = some φ →
      infer lib Δ p = some φ := by
  intro p
  induction p with
  | hyp ψ =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      split at h
      · cases h; rename_i hm; simp [hs _ hm]
      · cases h
  | topI => intro Γ Δ φ _ h; exact h
  | botE ψ p ih =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      split at h
      · rename_i hp; rw [ih Γ Δ _ hs hp]; exact h
      · cases h
  | andI p q ihp ihq =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      split at h
      · rename_i a b hp hq; rw [ihp Γ Δ _ hs hp, ihq Γ Δ _ hs hq]; exact h
      · cases h
  | andL p ih =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      split at h
      · rename_i a b hp; rw [ih Γ Δ _ hs hp]; exact h
      · cases h
  | andR p ih =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      split at h
      · rename_i a b hp; rw [ih Γ Δ _ hs hp]; exact h
      · cases h
  | orL b p ih =>
      intro Γ Δ φ hs h; simp only [infer, Option.map_eq_some_iff] at h ⊢
      obtain ⟨a, hp, rfl⟩ := h; exact ⟨a, ih Γ Δ a hs hp, rfl⟩
  | orR a p ih =>
      intro Γ Δ φ hs h; simp only [infer, Option.map_eq_some_iff] at h ⊢
      obtain ⟨b, hp, rfl⟩ := h; exact ⟨b, ih Γ Δ b hs hp, rfl⟩
  | orE p a b q r ihp ihq ihr =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      have hs' : ∀ c, ∀ ψ ∈ c :: Γ, ψ ∈ c :: Δ := fun c ψ hψ => by
        rcases List.mem_cons.1 hψ with rfl | hψ
        · exact List.mem_cons_self
        · exact List.mem_cons_of_mem _ (hs ψ hψ)
      split at h
      · rename_i hp
        rw [if_pos (ihp Γ Δ _ hs hp)]
        split at h
        · rename_i c1 c2 hq hr
          rw [ihq _ _ _ (hs' a) hq, ihr _ _ _ (hs' b) hr]; exact h
        · cases h
      · cases h
  | lam ψ p ih =>
      intro Γ Δ φ hs h; simp only [infer, Option.map_eq_some_iff] at h ⊢
      obtain ⟨b, hp, rfl⟩ := h
      refine ⟨b, ih _ _ b (fun χ hχ => ?_) hp, rfl⟩
      rcases List.mem_cons.1 hχ with rfl | hχ
      · exact List.mem_cons_self
      · exact List.mem_cons_of_mem _ (hs χ hχ)
  | app p q ihp ihq =>
      intro Γ Δ φ hs h; simp only [infer] at h ⊢
      split at h
      · rename_i a b a' hp hq; rw [ihp Γ Δ _ hs hp, ihq Γ Δ _ hs hq]; exact h
      · cases h
  | lem j σ => intro Γ Δ φ _ h; exact h

/-- Substitution of parameters in primitive proofs. -/
theorem infer_subst (s : Nat → Fm) :
    ∀ (p : Pf) (Γ : List Fm) (φ : Fm), infer [] Γ p = some φ →
      infer [] (Γ.map (·.subst s)) (p.subst s) = some (φ.subst s) := by
  intro p
  induction p with
  | hyp ψ =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · cases h; rename_i hm
        simp only [Pf.subst, infer]
        rw [if_pos (List.mem_map_of_mem hm)]
      · cases h
  | topI => intro Γ φ h; cases h; rfl
  | botE ψ p ih =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i hp; cases h; simp only [Pf.subst, infer]; rw [ih Γ _ hp]; rfl
      · cases h
  | andI p q ihp ihq =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b hp hq; cases h; simp only [Pf.subst, infer]; rw [ihp Γ _ hp, ihq Γ _ hq]; rfl
      · cases h
  | andL p ih =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b hp; cases h; simp only [Pf.subst, infer]; rw [ih Γ _ hp]; rfl
      · cases h
  | andR p ih =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b hp; cases h; simp only [Pf.subst, infer]; rw [ih Γ _ hp]; rfl
      · cases h
  | orL b p ih =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨a, hp, rfl⟩ := h
      simp only [Pf.subst, infer]; rw [ih Γ a hp]; rfl
  | orR a p ih =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨b, hp, rfl⟩ := h
      simp only [Pf.subst, infer]; rw [ih Γ b hp]; rfl
  | orE p a b q r ihp ihq ihr =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i hp
        split at h
        · rename_i c1 c2 hq hr
          split at h
          · rename_i he; simp only [Option.some.injEq] at h; subst h
            have hp' := ihp Γ _ hp
            have hq' := ihq (a :: Γ) c1 hq
            have hr' := ihr (b :: Γ) c2 hr
            simp only [List.map_cons] at hq' hr'
            simp only [Fm.subst] at hp'
            simp only [Pf.subst, infer, hp', hq', hr', he, if_true]
          · cases h
        · cases h
      · cases h
  | lam ψ p ih =>
      intro Γ φ h; simp only [infer, Option.map_eq_some_iff] at h
      obtain ⟨b, hp, rfl⟩ := h
      have := ih (ψ :: Γ) b hp
      simp only [List.map_cons] at this
      simp only [Pf.subst, infer, this]; rfl
  | app p q ihp ihq =>
      intro Γ φ h; simp only [infer] at h
      split at h
      · rename_i a b a' hp hq
        split at h
        · rename_i he; cases h; subst he
          have hp' := ihp Γ _ hp
          have hq' := ihq Γ _ hq
          simp only [Fm.subst] at hp'
          simp only [Pf.subst, infer, hp', hq']; simp
        · cases h
      · cases h
  | lem j σ => intro Γ φ h; simp [infer] at h

end PCSReasoningLibrary
