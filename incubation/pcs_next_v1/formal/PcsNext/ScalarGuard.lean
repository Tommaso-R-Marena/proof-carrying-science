/-
  Finite-domain non-worsening guard for scalar integer models.
  Scope: explicit finite list domains only — not ℝ, not general intelligence.
-/
namespace PcsNext.ScalarGuard

structure ScalarModel where
  a : Int
  b : Int
deriving Repr

def eval (m : ScalarModel) (x : Int) : Int := m.a * x + m.b

def pointwiseError (m : ScalarModel) (x y : Int) : Nat :=
  Int.natAbs (eval m x - y)

def totalLoss (m : ScalarModel) : List (Int × Int) → Nat
  | [] => 0
  | (x, y) :: rest => pointwiseError m x y + totalLoss m rest

/-- Accepted improvement on a frozen dataset: loss strictly decreases. -/
def improvesOn (old new : ScalarModel) (data : List (Int × Int)) : Prop :=
  totalLoss new data < totalLoss old data

theorem improvesOn_implies_lt (old new : ScalarModel) (data : List (Int × Int))
    (h : improvesOn old new data) :
    totalLoss new data < totalLoss old data := h

theorem improvesOn_not_ge (old new : ScalarModel) (data : List (Int × Int))
    (h : improvesOn old new data) :
    ¬ (totalLoss old data ≤ totalLoss new data) := by
  intro hge
  exact Nat.lt_irrefl _ (Nat.lt_of_lt_of_le h hge)

/-- Designated behavior preservation on an explicit finite domain. -/
def preservesWithin (old new : ScalarModel) (domain : List Int) (bound : Nat) : Prop :=
  ∀ x ∈ domain, Int.natAbs (eval new x - eval old x) ≤ bound

theorem preservesWithin_nil (old new : ScalarModel) (bound : Nat) :
    preservesWithin old new [] bound := by
  intro x hx
  cases hx

theorem preservesWithin_cons
    (old new : ScalarModel) (x : Int) (xs : List Int) (bound : Nat)
    (hx : Int.natAbs (eval new x - eval old x) ≤ bound)
    (hxs : preservesWithin old new xs bound) :
    preservesWithin old new (x :: xs) bound := by
  intro y hy
  cases hy with
  | head => exact hx
  | tail _ hmem => exact hxs y hmem

/-- Concrete finite-domain example: identical models preserve with bound 0. -/
theorem preserves_same_model_zero_bound (m : ScalarModel) (domain : List Int) :
    preservesWithin m m domain 0 := by
  intro x _hx
  simp [eval]

end PcsNext.ScalarGuard
