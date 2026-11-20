import Std

namespace SetBatchPromotion

/-- A case earns one point for correspondence and a second for a proof of the
corresponding statement. A proof of an unrelated translation earns neither. -/
inductive Status where
  | unresolved | corresponds | proved
  deriving DecidableEq, Repr

def credit : Status → Nat
  | .unresolved => 0
  | .corresponds => 1
  | .proved => 2

def score (cases : List C) (report : C → Status) : Nat :=
  (cases.map (fun c => credit (report c))).sum

/-- The checker and reviewer cases are parameters fixed for the entire history. -/
def accepts (cases : List C) (replay : R → C → Status) (a b : R) : Bool :=
  cases.all (fun c => decide (credit (replay a c) ≤ credit (replay b c))) &&
  decide (score cases (replay a) < score cases (replay b))

inductive History (cases : List C) (replay : R → C → Status) : Nat → R → R → Prop where
  | zero (a) : History cases replay 0 a a
  | step {k a b c} : History cases replay k a b →
      accepts cases replay b c = true → History cases replay (k+1) a c

private theorem credit_le (s : Status) : credit s ≤ 2 := by cases s <;> decide

private theorem score_le (cs : List C) (r : C → Status) : score cs r ≤ 2 * cs.length := by
  induction cs with
  | nil => simp [score]
  | cons c cs ih =>
    have h := credit_le (r c)
    simp only [score, List.map_cons, List.sum_cons, List.length_cons] at *
    omega

/-- From any initial revision, finitely many further promotions are possible.
Every unit of initial evidence reduces the maximum remaining history length.
Each individual case also retains its previous level of earned evidence. -/
theorem history_bound_and_preservation {cs : List C} {replay : R → C → Status}
    {k a b} (h : History cs replay k a b) :
    k + score cs (replay a) ≤ score cs (replay b) ∧
    (∀ c ∈ cs, credit (replay a c) ≤ credit (replay b c)) := by
  induction h with
  | zero a => exact ⟨by simp, fun _ _ => Nat.le_refl _⟩
  | step hist accepted ih =>
    simp only [accepts, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq] at accepted
    constructor
    · have h := accepted.2
      omega
    · intro c hc
      exact Nat.le_trans (ih.2 c hc) (accepted.1 c hc)

theorem remaining_promotions_bound {cs : List C} {replay : R → C → Status}
    {k a b} (h : History cs replay k a b) : k + score cs (replay a) ≤ 2 * cs.length :=
  Nat.le_trans (history_bound_and_preservation h).1 (score_le _ _)

#print axioms history_bound_and_preservation
#print axioms remaining_promotions_bound
end SetBatchPromotion
