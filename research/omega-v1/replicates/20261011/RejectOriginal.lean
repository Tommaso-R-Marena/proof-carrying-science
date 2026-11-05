-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=0957c06a5f8e34b1b32734aabbe8d91252d1f3a06c703807ab9047873fd4ef26
theorem omega_equivalence (p0 p1 p2 p3 : Bool) :
    ((p2 || (!p2 || p1)) && ((!p1) && (p1 && p2))) = ((p2 || (!p2 || p1)) || ((!p1) && (p1 && p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence
