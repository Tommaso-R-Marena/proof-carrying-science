-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1146ea1f6158e8b8acb0a507edb9b30e57e6bac8844ea2639680bc1b192aead3
theorem omega_equivalence (p0 p1 p2 p3 : Bool) :
    ((p0 || p3) && (p2 && p2)) = ((p0 || p3) || (p2 && p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence
