import ScientificReasoning.Syntax

/-!
# Authority lattice — commutative meet (Finding G fix)
-/

namespace ScientificReasoning

def Authority.rank : Authority → Nat
  | .disputed => 0
  | .hypothesis => 1
  | .empiricalAsserted => 2
  | .assumption => 2
  | .derived => 3
  | .mathVerified => 4

/-- Secondary total order for equal-rank ties (unique per constructor). -/
def Authority.tie : Authority → Nat
  | .disputed => 0
  | .hypothesis => 1
  | .assumption => 2
  | .empiricalAsserted => 3
  | .derived => 4
  | .mathVerified => 5

def Authority.meet (a b : Authority) : Authority :=
  if a.rank < b.rank then a
  else if b.rank < a.rank then b
  else if a.tie ≤ b.tie then a else b

theorem meet_le_left (a b : Authority) : (Authority.meet a b).rank ≤ a.rank := by
  unfold Authority.meet Authority.rank
  cases a <;> cases b <;> decide

theorem meet_le_right (a b : Authority) : (Authority.meet a b).rank ≤ b.rank := by
  unfold Authority.meet Authority.rank
  cases a <;> cases b <;> decide

theorem meet_comm (a b : Authority) : Authority.meet a b = Authority.meet b a := by
  unfold Authority.meet Authority.rank Authority.tie
  cases a <;> cases b <;> decide

theorem meet_empirical_not_math
    (a : Authority) (h : a = Authority.empiricalAsserted ∨ a = Authority.assumption) :
    Authority.meet a Authority.mathVerified ≠ Authority.mathVerified := by
  cases h with
  | inl he => subst he; decide
  | inr he => subst he; decide

theorem meet_rank_le (a b : Authority) :
    (Authority.meet a b).rank ≤ min a.rank b.rank :=
  Nat.le_min.2 ⟨meet_le_left a b, meet_le_right a b⟩

/-- Declared authority is untrusted; mathEstablished is never set by Hyp from labels. -/
structure Assurance where
  declared : Authority
  mathEstablished : Bool
  deriving Repr, DecidableEq, Inhabited

def Assurance.meetA (x y : Assurance) : Assurance :=
  { declared := Authority.meet x.declared y.declared
    mathEstablished := x.mathEstablished && y.mathEstablished }

def Assurance.hypDeclared (a : Authority) : Assurance :=
  { declared := a, mathEstablished := false }

end ScientificReasoning
