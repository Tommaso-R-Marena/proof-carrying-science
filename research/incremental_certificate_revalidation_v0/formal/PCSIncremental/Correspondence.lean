import PCSIncremental.Soundness

/-!
# Formal–executable correspondence boundary

Differential testing is **not** a refinement proof. This module records the
intended obligation: if an executable acceptance decodes to Lean premises
satisfying `IncrementalAccept`, then `FreshValid` follows by the kernel theorem.
The remaining gap is showing the Python algorithm establishes those premises.
-/

namespace PCSIncremental

inductive TraceEvent where
  | lookup (key : ObligationKey) (hit : Bool)
  | reuse (id : NodeId) (key : ObligationKey)
  | recheck (id : NodeId) (ok : Bool)
  | reject (id : NodeId)
  deriving Repr, DecidableEq

structure Report where
  accepted : Bool
  reused : List NodeId
  rechecked : List NodeId
  rejected : List NodeId
  outputs : List (NodeId × Value)
  deriving Repr, DecidableEq

/-- If executable acceptance is decoded into `IncrementalAccept` premises, then
Lean `FreshValid` holds — by the substantive soundness theorem, not by assuming
fresh validity in the predicate. -/
theorem executableAcceptImpliesLeanFresh
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate)
    (execAccepted : Bool)
    (decodedAccept : IncrementalAccept check vs g' changes σ' certs') :
    execAccepted = true → FreshValid check g' σ' certs' := by
  intro _
  exact incremental_implies_fresh check vs g' changes σ' certs' decodedAccept

structure RefinementGap where
  serialization : String :=
    "JSON canonicalization and NodeId map injectivity assumed by tests"
  algorithmProof : String :=
    "Python establishes IncrementalAccept premises only differentially, not kernel-proved"
  invalidationAlign : String :=
    "Both sides use updated-graph Affected under ChangesComplete; prior-only invalidation is unsound for new edges"
  runtime : String :=
    "Python interpreter, OS, and filesystem are outside the Lean model"

def documentedGap : RefinementGap := {}

def reportsAgree (a b : Report) : Prop := a = b

theorem reportsAgree_refl (r : Report) : reportsAgree r r := rfl

end PCSIncremental

#print axioms PCSIncremental.executableAcceptImpliesLeanFresh
