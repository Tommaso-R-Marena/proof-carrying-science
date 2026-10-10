import PCSDecisionDiagram.Apply
namespace PCSDD
/-- Once an apply computation succeeds, additional structural fuel preserves its complete output. -/
theorem apply_ok_add_fuel {n : Nat} {lim : Limits} :
    ∀ fuel op a b m r m', apply n lim fuel op a b m = .ok (r,m') →
      ∀ extra, apply n lim (fuel + extra) op a b m = .ok (r,m') := by
  intro fuel
  induction fuel with
  | zero =>
    intro op a b m r m' h extra
    simp [apply] at h
  | succ fuel ih =>
    intro op a b m r m' h extra
    rw [Nat.succ_add]
    unfold apply at h ⊢
    split at h
    · cases h
    rename_i hops
    simp only [if_neg hops]
    simp only at h
    split at h
    · rename_i rr hlook
      try simp only [hlook]
      exact h
    · rename_i hlook
      try simp only [hlook]
      split at h
      · rename_i ht
        try simp only [if_pos ht]
        exact h
      · rename_i ht
        try simp only [if_neg ht]
        try simp only at h
        split at h
        · cases h
        rename_i lo m1 h1
        rw [ih _ _ _ _ _ _ h1 extra]
        dsimp only
        split at h
        · cases h
        rename_i hi m2 h2
        rw [ih _ _ _ _ _ _ h2 extra]
        dsimp only
        split at h
        · cases h
        rename_i rr m3 h3
        exact h
theorem apply_ok_target {n : Nat} {lim : Limits} {fuel target : Nat}
    {op : BOp} {a b r : Nat} {m m' : Mgr}
    (h : apply n lim fuel op a b m = .ok (r,m')) (bound : fuel ≤ target) :
    apply n lim target op a b m = .ok (r,m') := by
  obtain ⟨extra, ht⟩ := Nat.exists_eq_add_of_le bound
  rw [ht]
  exact apply_ok_add_fuel fuel op a b m r m' h extra
#print axioms apply_ok_add_fuel
#print axioms apply_ok_target
end PCSDD
