-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=acb62cf527d4dceeb9abfc910476dcbf1e7b7efc6e8c8a0525d3d675ab32ae13
theorem omega_equivalence (p0 p1 p2 p3 : Bool) :
    (p0 && (p2 || p1)) = (p0 || (p2 || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence
