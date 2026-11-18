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

/-- Exhaustive 6×6 meet table (locks Finding G / Python meet_tables). -/
theorem meet_truth_table (a b : Authority) :
    Authority.meet a b =
      (if a.rank < b.rank then a
       else if b.rank < a.rank then b
       else if a.tie ≤ b.tie then a else b) := by
  rfl

theorem meet_exhaustive (a b : Authority) :
    Authority.meet a b =
      match a, b with
      | .disputed, _ => .disputed
      | _, .disputed => .disputed
      | .hypothesis, .hypothesis => .hypothesis
      | .hypothesis, .empiricalAsserted => .hypothesis
      | .hypothesis, .assumption => .hypothesis
      | .hypothesis, .derived => .hypothesis
      | .hypothesis, .mathVerified => .hypothesis
      | .empiricalAsserted, .hypothesis => .hypothesis
      | .assumption, .hypothesis => .hypothesis
      | .derived, .hypothesis => .hypothesis
      | .mathVerified, .hypothesis => .hypothesis
      | .empiricalAsserted, .empiricalAsserted => .empiricalAsserted
      | .assumption, .assumption => .assumption
      | .assumption, .empiricalAsserted => .assumption
      | .empiricalAsserted, .assumption => .assumption
      | .empiricalAsserted, .derived => .empiricalAsserted
      | .derived, .empiricalAsserted => .empiricalAsserted
      | .empiricalAsserted, .mathVerified => .empiricalAsserted
      | .mathVerified, .empiricalAsserted => .empiricalAsserted
      | .assumption, .derived => .assumption
      | .derived, .assumption => .assumption
      | .assumption, .mathVerified => .assumption
      | .mathVerified, .assumption => .assumption
      | .derived, .derived => .derived
      | .derived, .mathVerified => .derived
      | .mathVerified, .derived => .derived
      | .mathVerified, .mathVerified => .mathVerified := by
  cases a <;> cases b <;> decide

theorem meet_idem (a : Authority) : Authority.meet a a = a := by
  cases a <;> decide

theorem meet_assoc (a b c : Authority) :
    Authority.meet (Authority.meet a b) c = Authority.meet a (Authority.meet b c) := by
  cases a <;> cases b <;> cases c <;> decide

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

#print axioms ScientificReasoning.meet_comm
#print axioms ScientificReasoning.meet_exhaustive
#print axioms ScientificReasoning.meet_assoc
#print axioms ScientificReasoning.meet_idem

