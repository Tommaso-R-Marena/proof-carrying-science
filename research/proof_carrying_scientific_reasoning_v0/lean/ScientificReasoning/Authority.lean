import ScientificReasoning.Syntax

/-!
# Authority lattice and non-escalation
-/

namespace ScientificReasoning

/-- Rank: larger means stronger mathematical standing. -/
def Authority.rank : Authority → Nat
  | .disputed => 0
  | .hypothesis => 1
  | .empiricalAsserted => 2
  | .assumption => 2
  | .derived => 3
  | .mathVerified => 4

def Authority.le (a b : Authority) : Prop := a.rank ≤ b.rank

def Authority.meet (a b : Authority) : Authority :=
  if a.rank ≤ b.rank then a else b

theorem meet_le_left (a b : Authority) : (Authority.meet a b).rank ≤ a.rank := by
  unfold Authority.meet
  split
  · exact Nat.le_refl _
  · next h => exact Nat.le_of_lt (Nat.gt_of_not_le h)

theorem meet_le_right (a b : Authority) : (Authority.meet a b).rank ≤ b.rank := by
  unfold Authority.meet
  split
  · next h => exact h
  · exact Nat.le_refl _

/-- Empirical assertions cannot become mathVerified by meet. -/
theorem meet_empirical_not_math
    (a : Authority) (h : a = Authority.empiricalAsserted ∨ a = Authority.assumption) :
    Authority.meet a Authority.mathVerified ≠ Authority.mathVerified := by
  cases h with
  | inl he =>
      subst he
      intro hm
      have := congrArg Authority.rank hm
      simp [Authority.meet, Authority.rank] at this
  | inr he =>
      subst he
      intro hm
      have := congrArg Authority.rank hm
      simp [Authority.meet, Authority.rank] at this

/-- Meet never exceeds either argument's rank. -/
theorem meet_rank_le (a b : Authority) :
    (Authority.meet a b).rank ≤ min a.rank b.rank := by
  have hl := meet_le_left a b
  have hr := meet_le_right a b
  exact Nat.le_min.2 ⟨hl, hr⟩

end ScientificReasoning
