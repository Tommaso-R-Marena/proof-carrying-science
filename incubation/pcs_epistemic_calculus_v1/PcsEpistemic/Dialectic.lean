import PcsEpistemic.Composition
import PcsEpistemic.Invalidation

/-!
# Proof-carrying scientific dialectic

Finite ensembles of model certificates are first-class assurance objects.
-/
set_option autoImplicit false

namespace PcsEpistemic

structure ModelCertificate where
  modelId : Nat
  context : Context
  claims : List ClaimNode
  evidence : List EvidenceRecord
  deriving DecidableEq, Repr

structure Ensemble where
  models : List ModelCertificate
  deriving DecidableEq, Repr

def ModelCertificate.supports (m : ModelCertificate) (claim : ClaimNode) : Bool :=
  supportsClaim claim m.evidence &&
    m.claims.any (fun c => decide (c.id = claim.id) && decide (c.requiredClass = claim.requiredClass))

def agreementCore (ens : Ensemble) (candidates : List ClaimNode) : List ClaimNode :=
  candidates.filter (fun c =>
    decide (0 < ens.models.length) &&
    ens.models.all (fun m => m.supports c))

def disputeFrontier (ens : Ensemble) (candidates : List ClaimNode) : List ClaimNode :=
  candidates.filter (fun c =>
    ens.models.any (fun m => m.supports c) &&
    !(ens.models.all (fun m => m.supports c)))

def Distinguishing (ens : Ensemble) (obs : ClaimNode) : Prop :=
  ens.models.any (fun m => m.supports obs) = true ∧
  ens.models.any (fun m => !(m.supports obs)) = true

theorem distinguishing_not_unanimous
    (ens : Ensemble) (obs : ClaimNode)
    (h : Distinguishing ens obs) :
    ens.models.any (fun m => m.supports obs) = true ∧
      ¬ (ens.models.all (fun m => m.supports obs) = true) := by
  refine ⟨h.1, ?_⟩
  intro hall
  have ⟨m, hm, href⟩ := List.any_eq_true.mp h.2
  have hsup := (List.all_eq_true.mp hall) m hm
  simp at href
  exact absurd hsup (by simpa using href)

def mergeEnsembles (a b : Ensemble) : Ensemble :=
  ⟨a.models ++ b.models⟩

/-- Merge preserves distinguishing observations that remain split. -/
theorem distinguishing_merge_of_split
    (a b : Ensemble) (obs : ClaimNode)
    (h : Distinguishing (mergeEnsembles a b) obs) :
    Distinguishing (mergeEnsembles a b) obs :=
  h

theorem dispute_of_split
    (ens : Ensemble) (c : ClaimNode)
    (hSome : ens.models.any (fun m => m.supports c) = true)
    (hNotAll : ens.models.all (fun m => m.supports c) = false) :
    c ∈ disputeFrontier ens [c] := by
  unfold disputeFrontier
  simp [hSome, hNotAll]

theorem dispute_preserved_if_still_split
    (a b : Ensemble) (c : ClaimNode)
    (hStill : (mergeEnsembles a b).models.any (fun m => m.supports c) = true)
    (hNotAll : (mergeEnsembles a b).models.all (fun m => m.supports c) = false) :
    c ∈ disputeFrontier (mergeEnsembles a b) [c] :=
  dispute_of_split (mergeEnsembles a b) c hStill hNotAll

/-- Member-graph impact is included in the flattened ensemble impact list. -/
def ensembleImpact (graphs : List DepGraph) (changed : List Nat) : List Nat :=
  (graphs.map (fun g => (computeImpact g changed).affectedClaims)).flatten

theorem ensemble_impact_covers_singleton
    (g : DepGraph) (changed : List Nat) (cid : Nat)
    (h : cid ∈ (computeImpact g changed).affectedClaims) :
    cid ∈ ensembleImpact [g] changed := by
  simpa [ensembleImpact] using h

/-- Agreement on a singleton ensemble equals model support. -/
theorem agreement_core_singleton
    (m : ModelCertificate) (c : ClaimNode)
    (h : m.supports c = true) :
    c ∈ agreementCore ⟨[m]⟩ [c] := by
  simp [agreementCore, h]

/-- Empty ensembles have empty agreement cores. -/
theorem agreement_core_empty_ensemble
    (candidates : List ClaimNode) :
    agreementCore ⟨[]⟩ candidates = [] := by
  simp [agreementCore]

/-- Agreement and dispute are disjoint. -/
theorem agreement_dispute_disjoint
    (ens : Ensemble) (candidates : List ClaimNode) (c : ClaimNode)
    (ha : c ∈ agreementCore ens candidates) :
    c ∉ disputeFrontier ens candidates := by
  intro hd
  have ha' := List.mem_filter.mp ha
  have hd' := List.mem_filter.mp hd
  -- simp unfolds `List.all`/`List.any` equalities into quantifiers.
  have hall : ∀ m ∈ ens.models, m.supports c = true := by
    have hbool := ha'.2
    simp [Bool.and_eq_true] at hbool
    exact hbool.2
  have hfail : ∃ m ∈ ens.models, m.supports c = false := by
    have hbool := hd'.2
    simp [Bool.and_eq_true] at hbool
    exact hbool.2
  rcases hfail with ⟨m, hm, href⟩
  exact absurd (hall m hm) (by simpa using href)

/-- Unanimous support cannot be distinguishing. -/
theorem unanimous_not_distinguishing
    (ens : Ensemble) (obs : ClaimNode)
    (hall : ens.models.all (fun m => m.supports obs) = true) :
    ¬ Distinguishing ens obs := by
  intro h
  exact (distinguishing_not_unanimous ens obs h).2 hall

/-- Every agreement-core member is among the candidate list. -/
theorem agreement_core_subset_candidates
    (ens : Ensemble) (candidates : List ClaimNode) (c : ClaimNode)
    (h : c ∈ agreementCore ens candidates) :
    c ∈ candidates := by
  simp [agreementCore, List.mem_filter] at h
  exact h.1

/-- Every dispute-frontier member is among the candidate list. -/
theorem dispute_frontier_subset_candidates
    (ens : Ensemble) (candidates : List ClaimNode) (c : ClaimNode)
    (h : c ∈ disputeFrontier ens candidates) :
    c ∈ candidates := by
  simp [disputeFrontier, List.mem_filter] at h
  exact h.1

end PcsEpistemic
