import PCSIncremental.Graph

/-!
# Certificates and exact obligation keys

An obligation key captures everything that must match for reuse eligibility.
Exact product equality is used; cryptographic digests are not assumed.
-/

namespace PCSIncremental

/-- Mathematical certificate payload paired with a claimed output. -/
structure Certificate where
  payload : CertPayload
  output : Value
  deriving Repr, DecidableEq, Inhabited

/-- Exact obligation identifying a node's verification duty. -/
structure ObligationKey where
  id : NodeId
  op : OpId
  policy : PolicyId
  version : VersionId
  evidence : EvidenceId
  depOutputs : List Value
  deriving Repr, DecidableEq, Inhabited

/-- Build an obligation key from a node and resolved dependency outputs. -/
def obligationOf (n : Node) (depOutputs : List Value) : ObligationKey where
  id := n.id
  op := n.op
  policy := n.policy
  version := n.version
  evidence := n.evidence
  depOutputs := depOutputs

/-- Eligibility: cached obligation equals current obligation exactly. -/
def eligible (cached current : ObligationKey) : Prop :=
  cached = current

theorem eligible_refl (k : ObligationKey) : eligible k k := rfl

theorem eligible_symm {a b : ObligationKey} (h : eligible a b) : eligible b a :=
  h.symm

theorem eligible_trans {a b c : ObligationKey}
    (h₁ : eligible a b) (h₂ : eligible b c) : eligible a c :=
  h₁.trans h₂

theorem policy_change_breaks_eligibility
    (k : ObligationKey) (p' : PolicyId) (hne : p' ≠ k.policy) :
    ¬ eligible k { k with policy := p' } := by
  intro h
  have hp : k.policy = p' := congrArg ObligationKey.policy h
  exact hne hp.symm

theorem version_change_breaks_eligibility
    (k : ObligationKey) (v' : VersionId) (hne : v' ≠ k.version) :
    ¬ eligible k { k with version := v' } := by
  intro h
  have hv : k.version = v' := congrArg ObligationKey.version h
  exact hne hv.symm

theorem dep_output_change_breaks_eligibility
    (k : ObligationKey) (deps' : List Value) (hne : deps' ≠ k.depOutputs) :
    ¬ eligible k { k with depOutputs := deps' } := by
  intro h
  have hd : k.depOutputs = deps' := congrArg ObligationKey.depOutputs h
  exact hne hd.symm

theorem evidence_change_breaks_eligibility
    (k : ObligationKey) (e' : EvidenceId) (hne : e' ≠ k.evidence) :
    ¬ eligible k { k with evidence := e' } := by
  intro h
  have he : k.evidence = e' := congrArg ObligationKey.evidence h
  exact hne he.symm

theorem op_change_breaks_eligibility
    (k : ObligationKey) (o' : OpId) (hne : o' ≠ k.op) :
    ¬ eligible k { k with op := o' } := by
  intro h
  have ho : k.op = o' := congrArg ObligationKey.op h
  exact hne ho.symm

end PCSIncremental
