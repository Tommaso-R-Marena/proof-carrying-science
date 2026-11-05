/-
  Discrete mass-conservation facts for a two-cell transfer.
  Amounts are Nats; a successful transfer preserves total mass.
-/
namespace PcsNext.Conservation

/-- Transfer `k` units from A to B when A has enough. -/
def transfer (a b k : Nat) : Nat × Nat :=
  if k ≤ a then (a - k, b + k) else (a, b)

def total (p : Nat × Nat) : Nat := p.1 + p.2

theorem transfer_preserves_total (a b k : Nat) :
    total (transfer a b k) = a + b := by
  unfold transfer total
  by_cases h : k ≤ a
  · simp [h]
    omega
  · simp [h]

theorem transfer_nonincreasing_donor (a b k : Nat) :
    (transfer a b k).1 ≤ a := by
  unfold transfer
  by_cases h : k ≤ a
  · simp [h]
  · simp [h]

theorem transfer_zero (a b : Nat) : transfer a b 0 = (a, b) := by
  simp [transfer]

theorem transfer_too_large (a b : Nat) :
    transfer a b (a + 1) = (a, b) := by
  unfold transfer
  have : ¬ (a + 1 ≤ a) := by omega
  simp [this]

end PcsNext.Conservation
