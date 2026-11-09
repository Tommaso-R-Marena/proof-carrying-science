import Authority
import Provenance

/-!
A proof of the product of two explicit safety monitors: (a) delegated
capability attenuation and (b) lineage sensitivity preservation.

This is a conditional composition result: it requires both independent
predicates, correctly grounded source provenance, and a separately enforced
sink-classification check. It is not a proof of Python gateway refinement,
real-world consequences, implicit information-flow safety, or legitimate
human approval.
-/
namespace Writ12

theorem dual_axis_nonamplification
    {n : Nat} (parents : Fin n → List (Fin n)) (labels : Fin n → Nat)
    (rootScope : Writ9.Scope) (delegations : List Writ9.Scope)
    {action bytes : Nat} {ancestor child : Fin n}
    (safeChain : Writ9.SafeChain rootScope delegations)
    (childAuthority : Writ9.Allows (Writ9.LastScope rootScope delegations)
      action (labels child) bytes)
    (checkedLineage : CheckFlow parents labels = true)
    (sourcePath : Reaches parents ancestor child)
    {sink : Nat} (sinkAccepts : labels child ≤ sink) :
    Writ9.Allows rootScope action (labels child) bytes ∧ labels ancestor ≤ sink := by
  exact ⟨Writ9.arbitrary_chain_nonamplification rootScope delegations
            safeChain childAuthority,
         checked_release_sound checkedLineage sourcePath sinkAccepts⟩

end Writ12
