import PCS.Refinement

namespace PCS.Normalized

open PCS.Decision
open PCS.Refinement

/-- Version tag for the normalized decision state consumed by the formal bridge.
    Raw JSON parsing/schema validation is deliberately outside this structure. -/
inductive NormalizedVersion
  | v1
  deriving DecidableEq, Repr

/-- A certificate state after parsing, schema checking, evidence replay,
    ID normalization, semantic claim/evidence binding, and assumption-context
    construction have succeeded.

    Constructing this structure from serialized PCS bytes is the refinement
    obligation tracked separately from the pure decision theorem. -/
structure DecisionInput where
  version : NormalizedVersion := NormalizedVersion.v1
  Γ : List Assumption
  claim : Claim
  evidence : List Evidence
  uniqueEvidenceIds : ∀ e₁ ∈ evidence, ∀ e₂ ∈ evidence,
    e₁.id = e₂.id → e₁ = e₂
  context : ContextCovers Γ claim
  binding : RequiredEvidenceBound claim evidence

/-- The pure executable decision attached to a normalized state. -/
def decide (input : DecisionInput) : DecisionStatus :=
  decideClaim input.claim input.evidence

theorem context_available (input : DecisionInput) :
    ContextCovers input.Γ input.claim :=
  input.context

theorem binding_available (input : DecisionInput) :
    RequiredEvidenceBound input.claim input.evidence :=
  input.binding

theorem evidence_ids_unique (input : DecisionInput) :
    ∀ e₁ ∈ input.evidence, ∀ e₂ ∈ input.evidence,
      e₁.id = e₂.id → e₁ = e₂ :=
  input.uniqueEvidenceIds

end PCS.Normalized
