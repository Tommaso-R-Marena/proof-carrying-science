/-!
# Example symbols: bounded agent traces (Semantic Intelligence v2 registry)

Uninterpreted placeholder declarations that the v2 fixture registry grounds its AI-safety
symbols in.  They are `opaque`: Lean knows their types and nothing else, so no fact about any
real agent, permission system or deployment is asserted.  `tools/CheckRegistryGrounding.lean`
checks the registry against these declarations in the actual Lean environment (name, kind,
argument and result types).  Time points are `Nat`.
-/

namespace PCS.Examples.Agent

/-- An action identifier in a committed trace. -/
structure Action where
  id : Nat
  deriving Repr, DecidableEq, Inhabited

/-- Permission is revoked at time `t` (uninterpreted). -/
opaque revoked : Nat → Prop
/-- Time `i` is strictly before time `j` in the committed trace (uninterpreted). -/
opaque before : Nat → Nat → Prop
/-- The agent performs action `a` at time `t` (uninterpreted). -/
opaque performs : Nat → Action → Prop
/-- Action `a` is forbidden by the policy (uninterpreted). -/
opaque forbidden : Action → Prop
/-- Resource use at time `t` is within budget (uninterpreted). -/
opaque withinBudget : Nat → Prop

end PCS.Examples.Agent
