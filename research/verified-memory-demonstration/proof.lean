import Lean
theorem PCSKnownL0 : ∀ (a : Nat) (b : Nat) (c : Nat), (((a + b) = (a + c)) → (b = c)) := by
  intro a b c h; exact Nat.add_left_cancel h
theorem PCSKnownL1 : ∀ (a : Nat) (b : Nat) (c : Nat), (((a + c) = (b + c)) → (a = b)) := by
  intro a b c h; exact Nat.add_right_cancel h
theorem PCSKnownL2 : ∀ (a : Nat) (b : Nat), (((Nat.succ a) = (Nat.succ b)) → (a = b)) := by
  intro a b h; exact Nat.succ.inj h
theorem PCSKnownL3 : ∀ (n : Nat), (¬ ((Nat.succ n) = (0 : Nat))) := by
  intro n; exact Nat.succ_ne_zero n
theorem PCSKnownL4 : ∀ (a : Nat) (b : Nat) (c : Nat), (((a + c) ≤ (b + c)) → (a ≤ b)) := by
  intro a b c h; exact Nat.le_of_add_le_add_right h
theorem PCSKnownL5 : ∀ (a : Nat) (b : Nat), (((Nat.succ a) ≤ (Nat.succ b)) → (a ≤ b)) := by
  intro a b h; exact Nat.succ_le_succ_iff.mp h
theorem PCSKnownL6 : ∀ (a : Nat) (b : Nat) (c : Nat), ((a * (b + c)) = ((a * b) + (a * c))) := by
  intro a b c; exact Nat.left_distrib a b c
theorem PCSKnownL7 : ∀ (xs : List Nat), ((List.length (List.reverse xs)) = (List.length xs)) := by
  intro xs; exact List.length_reverse
theorem PCSKnownL8 : ∀ (xs : List Nat) (ys : List Nat), ((List.reverse (xs ++ ys)) = ((List.reverse ys) ++ (List.reverse xs))) := by
  intro xs ys; exact List.reverse_append
theorem PCSKnownL9 : ∀ (xs : List Nat), ((List.reverse (List.reverse xs)) = xs) := by
  intro xs; exact List.reverse_reverse xs
theorem PCSKnownL10 : ∀ (xs : List Nat) (ys : List Nat) (zs : List Nat), (((xs ++ ys) = (xs ++ zs)) → (ys = zs)) := by
  intro xs ys zs h; exact (List.append_right_inj xs).mp h
theorem PCSKnownL11 : ∀ (xs : List Nat) (ys : List Nat) (zs : List Nat), (((xs ++ zs) = (ys ++ zs)) → (xs = ys)) := by
  intro xs ys zs h; exact (List.append_left_inj zs).mp h
theorem PCSKnownL12 : ∀ (xs : List Nat) (ys : List Nat), (((List.reverse xs) = (List.reverse ys)) → (xs = ys)) := by
  intro xs ys h; exact List.reverse_inj.mp h
theorem PCSReuseL0 : ∀ (q0 : Nat → Nat), ((∀ (q2 : Nat), ((q0 (Nat.succ q2)) = ((q0 q2) + (1 : Nat)))) → (∀ (q2 : Nat), ((q0 q2) = ((q0 (0 : Nat)) + q2)))) := by
  intro h0
  intro h1
  intro h2
  (induction h2 using Nat.rec; case' succ h3 h4 => skip)
  rw [h1]
  simp only [Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add, Nat.mul_zero, Nat.zero_mul, Nat.mul_succ, Nat.succ_mul]
  rw [h4]
  simp only [Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add, Nat.mul_zero, Nat.zero_mul, Nat.mul_succ, Nat.succ_mul]
theorem PCSReuseL1 : ∀ (q0 : Nat → Prop), (((q0 (0 : Nat)) ∧ (∀ (q3 : Nat), ((q0 q3) → (q0 (Nat.succ q3))))) → (∀ (q2 : Nat), (q0 q2))) := by
  intro h0
  intro h1
  intro h2
  (induction h2 using Nat.rec; case' succ h3 h4 => skip)
  apply h1.2
  exact h4
  exact h1.1
theorem PCSReuseL2 : ∀ (q0 : List Nat) (q1 : List Nat), ((List.length (q0 ++ q1)) = ((List.length q0) + (List.length q1))) := by
  intro h0
  intro h1
  (induction h0 using List.rec; case' cons h2 h3 h4 => skip)
  simp only [List.nil_append, List.cons_append, List.append_nil, List.length_nil, List.length_cons, Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add]
  rw [h4]
  simp only [List.nil_append, List.cons_append, List.append_nil, List.length_nil, List.length_cons, Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add]
theorem PCSReuseL3 : ∀ (v0 : List Nat) (v1 : Nat) (v2 : List Nat), ((List.length ((List.cons v1 v2) ++ v0)) = ((List.length (List.cons v1 v2)) + (List.length v0))) := by
  intro h0
  intro h1
  intro h2
  simp only [List.nil_append, List.cons_append, List.append_nil, List.length_nil, List.length_cons, Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add]
  (induction h2 using List.rec; case' cons h3 h4 h5 => skip)
  (induction h1 using Nat.rec; case' succ h2 h6 => skip)
  rw [h6]
  simp only [List.nil_append, List.cons_append, List.append_nil, List.length_nil, List.length_cons, Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add]
  rw [h5]
  simp only [List.nil_append, List.cons_append, List.append_nil, List.length_nil, List.length_cons, Nat.add_zero, Nat.zero_add, Nat.add_succ, Nat.succ_add]

theorem pcs_memory_demo : ∀ (f : Nat → Nat), ((∀ (k : Nat), ((f (Nat.succ k)) = ((f k) + (1 : Nat)))) → (∀ (n : Nat), ((f (((n * n) * n) + (2 : Nat))) = ((f (0 : Nat)) + (((n * n) * n) + (2 : Nat)))))) := by
  intro h0
  intro h1
  intro h2
  rw [← PCSReuseL0]
  intro h3
  rw [h1]
#print axioms pcs_memory_demo
