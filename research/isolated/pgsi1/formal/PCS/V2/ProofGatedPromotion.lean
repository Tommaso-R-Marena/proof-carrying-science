import PCS.V2.ProofGatedArtifacts

/-!
# PCS checked compare-and-swap transition (pure specification)

The authoritative *mathematical* state stores exact canonical text, rather
than a hash. A production content-addressed store corresponds to this model
only assuming collision-resistance, faithful loading, isolation and atomicity.
These assumptions must NOT be silently smuggled into the Lean theorem.
-/

namespace PCS.V2.ProofGatedPromotion

open PCS.V2.ProofGatedArtifacts
open PCS.V2.ProofGatedSelfImprovement

structure State where
  generation : Nat
  active : String
  deriving Repr, DecidableEq

structure Proposal where
  expectedGeneration : Nat
  expectedActive : String
  candidate : String
  deriving Repr, DecidableEq

def tryCommit (state : State) (proposal : Proposal) : Option State :=
  if hg : proposal.expectedGeneration = state.generation then
    if hp : proposal.expectedActive = state.active then
      if ha : acceptWire state.active proposal.candidate = true then
        some ⟨state.generation + 1, proposal.candidate⟩
      else none
    else none
  else none

theorem commit_sound {state newState : State} {p : Proposal}
    (h : tryCommit state p = some newState) :
    p.expectedGeneration = state.generation ∧
    p.expectedActive = state.active ∧
    newState.generation = state.generation + 1 ∧
    newState.active = p.candidate ∧
    acceptWire state.active p.candidate = true := by
  by_cases hg : p.expectedGeneration = state.generation
  · by_cases hp : p.expectedActive = state.active
    · by_cases ha : acceptWire state.active p.candidate = true
      · simp only [tryCommit, dif_pos hg, dif_pos hp, dif_pos ha,
          Option.some.injEq] at h
        cases h
        exact ⟨hg, hp, rfl, rfl, ha⟩
      · simp [tryCommit, hg, hp, ha] at h
    · simp [tryCommit, hg, hp] at h
  · simp [tryCommit, hg] at h

theorem commit_requires_genuine_improvement {state newState : State}
    {p : Proposal} (h : tryCommit state p = some newState) :
    ∃ old candidate,
      decode state.active = some old ∧
      decode newState.active = some candidate ∧
      admissible old candidate ∧
      loss candidate < loss old := by
  obtain ⟨_, _, _, heq, ha⟩ := commit_sound h
  obtain ⟨old, candidate, hdOld, hdNew, _, _, hadm⟩ :=
    acceptWire_sound ha
  exact ⟨old, candidate, hdOld, by simpa [heq] using hdNew,
    hadm, hadm.2.2⟩

theorem stale_generation_cannot_commit {state : State} {p : Proposal}
    (h : p.expectedGeneration ≠ state.generation) :
    tryCommit state p = none := by
  simp [tryCommit, h]

theorem substituted_active_cannot_commit {state : State} {p : Proposal}
    (h : p.expectedActive ≠ state.active) :
    tryCommit state p = none := by
  by_cases hg : p.expectedGeneration = state.generation
  · simp [tryCommit, hg, h]
  · simp [tryCommit, hg]

def gatedCommit (s : State) (p : Proposal) : State :=
  (tryCommit s p).getD s

theorem gatedCommit_monotone_generation (s : State) (p : Proposal) :
    s.generation ≤ (gatedCommit s p).generation := by
  cases hc : tryCommit s p with
  | none => simp [gatedCommit, hc]
  | some newState =>
    have h := (commit_sound hc).2.2.1
    simp only [gatedCommit, hc, Option.getD_some]
    omega

end PCS.V2.ProofGatedPromotion
