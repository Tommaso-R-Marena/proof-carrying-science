/-
Epistemic strata for proof-carrying science. Research-grade only.
-/

namespace PCSEpistemic

inductive Stratum where
  | integrity
  | computational
  | formal
  | continuum
  | empirical
  | causal
  deriving DecidableEq, Repr, Inhabited

def Stratum.rank : Stratum → Nat
  | .integrity => 0
  | .computational => 1
  | .formal => 2
  | .continuum => 3
  | .empirical => 4
  | .causal => 5

theorem Stratum.rank_inj {a b : Stratum} (h : a.rank = b.rank) : a = b := by
  cases a <;> cases b <;> simp [Stratum.rank] at h <;> try rfl
  all_goals cases h

def Stratum.le (a b : Stratum) : Prop := a.rank ≤ b.rank
def Stratum.lt (a b : Stratum) : Prop := a.rank < b.rank

instance : LE Stratum where
  le := Stratum.le

instance : LT Stratum where
  lt := Stratum.lt

instance (a b : Stratum) : Decidable (a ≤ b) :=
  inferInstanceAs (Decidable (a.rank ≤ b.rank))

instance (a b : Stratum) : Decidable (a < b) :=
  inferInstanceAs (Decidable (a.rank < b.rank))

theorem Stratum.le_def (a b : Stratum) : (a ≤ b) = (a.rank ≤ b.rank) := rfl
theorem Stratum.lt_def (a b : Stratum) : (a < b) = (a.rank < b.rank) := rfl

theorem Stratum.le_refl (a : Stratum) : a ≤ a := by
  rw [le_def]
  exact Nat.le_refl _

theorem Stratum.le_trans {a b c : Stratum} (hab : a ≤ b) (hbc : b ≤ c) : a ≤ c := by
  rw [le_def] at *
  exact Nat.le_trans hab hbc

theorem Stratum.le_antisymm {a b : Stratum} (hab : a ≤ b) (hba : b ≤ a) : a = b := by
  rw [le_def] at *
  exact rank_inj (Nat.le_antisymm hab hba)

def Stratum.meet (a b : Stratum) : Stratum :=
  if a.rank ≤ b.rank then a else b

def Stratum.join (a b : Stratum) : Stratum :=
  if a.rank ≤ b.rank then b else a

theorem Stratum.meet_le_left (a b : Stratum) : meet a b ≤ a := by
  rw [le_def, meet]
  by_cases h : a.rank ≤ b.rank
  · rw [if_pos h]; exact Nat.le_refl _
  · rw [if_neg h]; exact Nat.le_of_lt (Nat.lt_of_not_ge h)

theorem Stratum.meet_le_right (a b : Stratum) : meet a b ≤ b := by
  rw [le_def, meet]
  by_cases h : a.rank ≤ b.rank
  · rw [if_pos h]; exact h
  · rw [if_neg h]; exact Nat.le_refl _

theorem Stratum.le_join_left (a b : Stratum) : a ≤ join a b := by
  rw [le_def, join]
  by_cases h : a.rank ≤ b.rank
  · rw [if_pos h]; exact h
  · rw [if_neg h]; exact Nat.le_refl _

theorem Stratum.le_join_right (a b : Stratum) : b ≤ join a b := by
  rw [le_def, join]
  by_cases h : a.rank ≤ b.rank
  · rw [if_pos h]; exact Nat.le_refl _
  · rw [if_neg h]; exact Nat.le_of_lt (Nat.lt_of_not_ge h)

theorem Stratum.meet_comm (a b : Stratum) : meet a b = meet b a := by
  simp only [meet]
  by_cases h₁ : a.rank ≤ b.rank
  · by_cases h₂ : b.rank ≤ a.rank
    · have : a = b := le_antisymm (by rw [le_def]; exact h₁) (by rw [le_def]; exact h₂)
      subst this
      rfl
    · simp [h₁, h₂]
  · by_cases h₂ : b.rank ≤ a.rank
    · simp [h₁, h₂]
    · exact False.elim (h₂ (Nat.le_of_lt (Nat.lt_of_not_ge h₁)))

theorem Stratum.formal_lt_continuum : Stratum.formal < Stratum.continuum := by
  decide

theorem Stratum.computational_lt_empirical : Stratum.computational < Stratum.empirical := by
  decide

theorem Stratum.continuum_lt_causal : Stratum.continuum < Stratum.causal := by
  decide

def Stratum.canDischarge (evidence claim : Stratum) : Bool :=
  decide (claim ≤ evidence)

theorem Stratum.canDischarge_iff (evidence claim : Stratum) :
    canDischarge evidence claim = true ↔ claim ≤ evidence := by
  simp [canDischarge]

def Stratum.forbiddenPromotion (evidence claim : Stratum) : Bool :=
  decide (evidence < claim)

theorem Stratum.forbiddenPromotion_iff (evidence claim : Stratum) :
    forbiddenPromotion evidence claim = true ↔ evidence < claim := by
  simp [forbiddenPromotion]

theorem Stratum.forbidden_not_discharge {e c : Stratum}
    (h : forbiddenPromotion e c = true) : canDischarge e c = false := by
  have hlt : e < c := (forbiddenPromotion_iff e c).1 h
  have : ¬ c ≤ e := by
    rw [lt_def, le_def] at *
    exact fun hle => Nat.lt_irrefl _ (Nat.lt_of_lt_of_le hlt hle)
  simp [canDischarge, this]

end PCSEpistemic
