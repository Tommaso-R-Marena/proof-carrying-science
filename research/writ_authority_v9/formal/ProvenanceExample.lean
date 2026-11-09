import Provenance

namespace Writ12Example

def parentGraph : Fin 3 → List (Fin 3) :=
  fun i => if i.val == 2 then [(0 : Fin 3), (1 : Fin 3)] else []

def safeLabels : Fin 3 → Nat :=
  fun i => if i.val == 1 || i.val == 2 then 2 else 0

def launderedLabels : Fin 3 → Nat :=
  fun i => if i.val == 1 then 2 else 0

example : Writ12.CheckFlow parentGraph safeLabels = true := by decide
example : Writ12.CheckFlow parentGraph launderedLabels = false := by decide

end Writ12Example
