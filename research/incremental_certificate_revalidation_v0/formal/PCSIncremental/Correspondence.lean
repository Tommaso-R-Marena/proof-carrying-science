import PCSIncremental.Soundness

/-!
# Formal–executable correspondence boundary

This module states the intended refinement relation between the Lean model and
the research Python verifier. A full refinement proof of the Python runtime is
**not** claimed. Shared abstract obligations are recorded here.
-/
namespace PCSIncremental

/-- Shared trace event kinds used by differential tests. -/
inductive TraceEvent where
  | lookup (key : ObligationKey) (hit : Bool)
  | reuse (id : NodeId) (key : ObligationKey)
  | recheck (id : NodeId) (ok : Bool)
  | reject (id : NodeId)
  deriving Repr, DecidableEq

/-- An abstract verification report. -/
structure Report where
  accepted : Bool
  reused : List NodeId
  rechecked : List NodeId
  rejected : List NodeId
  outputs : List (NodeId × Value)
  deriving Repr, DecidableEq

/-- Correspondence obligation: if the executable incremental verifier accepts,
and its serialized `(graph', changes, σ', certs')` decode to Lean values satisfying
`IncrementalAccept`, then `FreshValid` holds in Lean. -/
def executableAcceptImpliesLeanFresh
    (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) (cache' : Cache)
    (execAccepted : Bool)
    (decodedAccept : IncrementalAccept check vs g' changes σ' certs' cache') :
    execAccepted = true → FreshValid check g' σ' certs' := by
  intro _
  exact decodedAccept.fresh'

/-- The remaining unverified boundary: decoding Python JSON into Lean structures
and proving the executable algorithm establishes `IncrementalAccept`. -/
structure RefinementGap where
  serialization : String :=
    "JSON canonicalization and NodeId map injectivity assumed by tests"
  algorithmProof : String :=
    "Python affected-closure ≡ Affected is differentially tested, not kernel-proved"
  runtime : String :=
    "Python interpreter, OS, and filesystem are outside the Lean model"

/-- Documented gap instance. -/
def documentedGap : RefinementGap := {}

/-- Exact equality of reports is the differential-test oracle relation. -/
def reportsAgree (a b : Report) : Prop := a = b

theorem reportsAgree_refl (r : Report) : reportsAgree r r := rfl

end PCSIncremental

#print axioms PCSIncremental.executableAcceptImpliesLeanFresh
