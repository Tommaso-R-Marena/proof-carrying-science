import Authority

/-!
A small kernel-checked, proof-carrying weighted trace fixture. The resource
identifiers are an illustrative budget, grant and shared delegation quota.
The witness/identity proof lives in Witness.lean. This fixture does NOT prove
that a real gateway logged these exact values; that is a separate bridge.
-/
namespace Writ11

def vector3 (budget grant ancestor : Nat) : Fin 3 → Nat :=
  fun i => if i.val == 0 then budget else if i.val == 1 then grant else ancestor

def initial : Fin 3 → Nat := vector3 5 3 2

def lawful : List (Fin 3 → Nat) :=
  [vector3 2 1 1, vector3 2 1 1]

def overBudget : List (Fin 3 → Nat) :=
  [vector3 4 1 1, vector3 2 1 1]

example : (Writ9.CheckWeighted initial lawful).map (fun f => f (0 : Fin 3)) = some 1 := by
  decide
example : (Writ9.CheckWeighted initial lawful).map (fun f => f (1 : Fin 3)) = some 1 := by
  decide
example : (Writ9.CheckWeighted initial lawful).map (fun f => f (2 : Fin 3)) = some 0 := by
  decide
example : (Writ9.CheckWeighted initial overBudget).isNone = true := by
  decide

end Writ11
