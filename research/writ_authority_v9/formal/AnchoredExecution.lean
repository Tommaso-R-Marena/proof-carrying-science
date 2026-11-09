import Authority
import Provenance

/-!
Writ/13 source-anchored execution calculus, research-only.

The checkpoint and manifest identifiers are opaque Nat values. Equality of
identifiers is an explicit cryptographic-root-of-trust assumption, NOT a
theorem that SHA-256 resists collisions or that Ed25519 verifies signatures.
The provenance graph covers only explicitly represented dependencies.

CheckAnchored is an executable *abstract* product checker for a pinned source
identity, finite explicit-flow graph and weighted authority trace. The theorems
show exact correspondence to the conjunction of its independent declarative
predicates. They do NOT establish Python/SQLite-to-Lean refinement.
-/
namespace Writ13

def CheckAnchored {n m : Nat}
    (committed current : Nat)
    (parents : Fin n → List (Fin n)) (label : Fin n → Nat)
    (balance : Fin m → Nat) (trace : List (Fin m → Nat)) :
    Option (Fin m → Nat) :=
  if committed = current ∧ Writ12.CheckFlow parents label = true then
    Writ9.CheckWeighted balance trace
  else
    none

/-- All accepted executions have the witnessed identity, an explicitly
flow-sound graph and a trace valid under the independent weighted calculus. -/
theorem anchored_sound {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {balance final : Fin m → Nat} {trace : List (Fin m → Nat)}
    (accepted : CheckAnchored committed current parents label balance trace = some final) :
    committed = current ∧ Writ12.FlowSound parents label ∧
    Writ9.WeightedRuns balance trace final := by
  have h : (committed = current ∧ Writ12.CheckFlow parents label = true) ∧
      Writ9.CheckWeighted balance trace = some final := by
    simpa [CheckAnchored] using accepted
  exact ⟨h.1.1, (Writ12.checkFlow_iff parents label).mp h.1.2,
         Writ9.checkWeighted_sound h.2⟩

/-- Completeness relative to the explicitly stated checkpoint, flow and
weighted-trace predicates. -/
theorem anchored_complete {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {balance final : Fin m → Nat} {trace : List (Fin m → Nat)}
    (same : committed = current) (safe : Writ12.FlowSound parents label)
    (run : Writ9.WeightedRuns balance trace final) :
    CheckAnchored committed current parents label balance trace = some final := by
  have checked : committed = current ∧ Writ12.CheckFlow parents label = true :=
    ⟨same, (Writ12.checkFlow_iff parents label).mpr safe⟩
  simpa [CheckAnchored, checked] using Writ9.checkWeighted_complete run

/-- A successful run cannot spend more of *any* finite authority resource than
its initial balance, including shared ancestors and weighted budgets. -/
theorem anchored_no_overspend {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {balance final : Fin m → Nat} {trace : List (Fin m → Nat)}
    (accepted : CheckAnchored committed current parents label balance trace = some final)
    (i : Fin m) : Writ9.WeightedUsed i trace ≤ balance i := by
  have valid := (anchored_sound accepted).2.2
  have exact := Writ9.weighted_quota_conservation valid i
  omega

/-- Every accepted low-sink release is protected against *explicit*
dataflow laundering; it cannot use an ancestor with a higher label. -/
theorem anchored_release_nonlaundering {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {balance final : Fin m → Nat} {trace : List (Fin m → Nat)}
    (accepted : CheckAnchored committed current parents label balance trace = some final)
    {ancestor child : Fin n} (path : Writ12.Reaches parents ancestor child)
    {sink : Nat} (allowed : label child ≤ sink) :
    label ancestor ≤ sink := by
  have safe := (anchored_sound accepted).2.1
  exact Nat.le_trans (Writ12.nonlaundering safe path) allowed

/-- Combining accepted resource-accounting and source evidence with
attenuated delegation yields both budget and permission non-amplification. -/
theorem anchored_dual_authority {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {balance final : Fin m → Nat} {trace : List (Fin m → Nat)}
    (accepted : CheckAnchored committed current parents label balance trace = some final)
    (root : Writ9.Scope) (delegations : List Writ9.Scope)
    {action bytes : Nat} {source : Fin n}
    (safeChain : Writ9.SafeChain root delegations)
    (scope : Writ9.Allows (Writ9.LastScope root delegations)
      action (label source) bytes) :
    committed = current ∧
      Writ9.Allows root action (label source) bytes := by
  exact ⟨(anchored_sound accepted).1,
         Writ9.arbitrary_chain_nonamplification root delegations safeChain scope⟩

end Writ13
