import PCS.V2.ProofGatedPromotion

/-!
# Pure exact-wire inference and preservation across certified promotions

This module bridges the accepted canonical text directly to predictions,
without silently replacing it with a separately asserted Python model.
It does not prove the external Python loader, storage, or operating system.
-/

namespace PCS.V2.ProofGatedInference

open PCS.V2.ProofGatedSelfImprovement
open PCS.V2.ProofGatedArtifacts
open PCS.V2.ProofGatedPromotion

def infer (raw : String) (x : Int) : Option Int :=
  (decode raw).map (fun m => predict m x)

theorem infer_sound {raw : String} {x y : Int}
    (h : infer raw x = some y) :
    ∃ m, decode raw = some m ∧ predict m x = y := by
  unfold infer at h
  cases hd : decode raw with
  | none => simp [hd] at h
  | some m =>
      have hp : predict m x = y := by
        simpa [hd] using h
      exact ⟨m, by simp, hp⟩

theorem infer_canonical {raw : String} {x y : Int}
    (h : infer raw x = some y) :
    ∃ m, encode m = raw ∧ predict m x = y := by
  obtain ⟨m, hd, hp⟩ := infer_sound h
  exact ⟨m, decode_canonical hd, hp⟩

theorem committed_inference_preserves_correct_cases
    {before after : State} {proposal : Proposal}
    (h : tryCommit before proposal = some after)
    (x : Int) (hx : x ∈ corpus) (y : Int)
    (hold : infer before.active x = some y)
    (hcorrect : y = target x) :
    infer after.active x = some y := by
  obtain ⟨old, candidate, hdOld, hdNew, hadm, _⟩ :=
    commit_requires_genuine_improvement h
  have hpred : predict old x = y := by
    simpa [infer, hdOld] using hold
  have hcorrectOld : correct old x := by
    simp [correct, hpred, hcorrect]
  have hnew : correct candidate x := hadm.1 x hx hcorrectOld
  have hnewPred : predict candidate x = y := by
    simpa [correct, hcorrect] using hnew
  simp [infer, hdNew, hnewPred]

theorem committed_inference_exact_artifact
    {before after : State} {proposal : Proposal}
    (h : tryCommit before proposal = some after)
    (x : Int) :
    ∃ m, encode m = after.active ∧
      infer after.active x = some (predict m x) := by
  obtain ⟨_, candidate, _, hdNew, _, _⟩ :=
    commit_requires_genuine_improvement h
  refine ⟨candidate, decode_canonical hdNew, ?_⟩
  simp [infer, hdNew]

end PCS.V2.ProofGatedInference
