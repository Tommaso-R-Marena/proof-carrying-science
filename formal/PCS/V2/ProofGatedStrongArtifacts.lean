import PCS.V2.ProofGatedStrongGate
import PCS.V2.ProofGatedNetArtifacts

/-!
# Strong-gate artifacts: decoding, acceptance, compare-and-swap promotion, inference

This module connects the strong gate of `ProofGatedStrongGate` to the versioned canonical
`PGSI2-WIDE` artifacts of `ProofGatedNetArtifacts`. Everything is about exact strings
and is proved for every `StrongSpec` (architecture bound, target network, corpus,
interval):

1. `acceptStrongWire_iff`: the wire-level gate accepts `(oldRaw, newRaw)` **iff** both
   texts are canonical encodings of networks `o`, `n` and `o ↦ n` satisfies
   A ∧ B ∧ C (`StrongAdmissible`). This is sound and complete;
2. `acceptStrongWire_encode`: on canonical artifacts the wire gate *is* the model gate;
3. `commitS_refines`: a successful compare-and-swap commit binds the old and new active
   texts to decoded networks. The served predictions are exactly `predict cand` on
   **every** integer. Every integer served correctly before is served correctly after,
   and every error bound of the served model on `[lo,hi]` survives;
4. `commitS_complete`: every strongly admissible canonical proposal made against the
   current generation and active text commits;
5. `runCommitsS_invariant`: for an **arbitrary** list of proposals (stale, forged,
   adversarial or genuine), the final active text decodes to a network that keeps every
   originally correct integer and every original error bound on `[lo,hi]`. The number of
   successful commits plus the final loss is at most the initial loss;
6. `served_error_le`: every prediction served from the final artifact on `[lo,hi]` is
   within the initial model's exact worst-case error.

Trusted boundary (not modelled, so not proved): reading bytes from storage, file-system
atomicity of the compare-and-swap, hash collision resistance, signatures, process
isolation, and the faithfulness of an external runtime that executes the served network.
-/

namespace PCS.V2.ProofGatedStrongArtifacts

open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedNetArtifacts (encode decode decode_encode decode_canonical decode_valid
  decode_iff infer infer_encode encode_injective)

/-! ## Wire-level strong gate -/

/-- Decode both texts under the versioned architecture bound, then run the strong gate. -/
def acceptStrongWire (S : StrongSpec) (oldRaw newRaw : String) : Bool :=
  match decode S.arch oldRaw, decode S.arch newRaw with
  | some o, some n => acceptStrong S o n
  | _, _ => false

theorem strongAdmissible_valid {S : StrongSpec} {o n : WideNet}
    (h : StrongAdmissible S o n) : valid S.arch o = true ∧ valid S.arch n = true :=
  ⟨h.1.1, h.1.2.1⟩

/-- **Soundness and completeness of the wire-level strong gate.** -/
theorem acceptStrongWire_iff (S : StrongSpec) (oldRaw newRaw : String) :
    acceptStrongWire S oldRaw newRaw = true ↔
      ∃ o n, encode o = oldRaw ∧ encode n = newRaw ∧ StrongAdmissible S o n := by
  constructor
  · intro h
    unfold acceptStrongWire at h
    cases ho : decode S.arch oldRaw with
    | none => simp [ho] at h
    | some o =>
      cases hn : decode S.arch newRaw with
      | none => simp [ho, hn] at h
      | some n =>
        simp only [ho, hn] at h
        exact ⟨o, n, decode_canonical ho, decode_canonical hn, acceptStrong_sound h⟩
  · rintro ⟨o, n, rfl, rfl, hadm⟩
    obtain ⟨hvo, hvn⟩ := strongAdmissible_valid hadm
    simp [acceptStrongWire, decode_encode _ _ hvo, decode_encode _ _ hvn,
      acceptStrong_complete hadm]

/-- On canonical artifacts of valid networks the wire gate is the model gate. -/
theorem acceptStrongWire_encode (S : StrongSpec) (o n : WideNet) (ho : valid S.arch o = true)
    (hn : valid S.arch n = true) :
    acceptStrongWire S (encode o) (encode n) = acceptStrong S o n := by
  simp [acceptStrongWire, decode_encode _ _ ho, decode_encode _ _ hn]

/-- Non-canonical or invalid texts are never accepted, whatever the other side is. -/
theorem acceptStrongWire_noncanonical (S : StrongSpec) (oldRaw newRaw : String)
    (h : decode S.arch newRaw = none) : acceptStrongWire S oldRaw newRaw = false := by
  unfold acceptStrongWire
  cases decode S.arch oldRaw <;> simp [h]

/-! ## Compare-and-swap promotion -/

structure State where
  generation : Nat
  active : String
  deriving Repr, DecidableEq

structure Proposal where
  expectedGeneration : Nat
  expectedActive : String
  candidate : String
  deriving Repr, DecidableEq

/-- Commit iff the proposal names the current generation and the exact active text, and
the strong wire gate accepts. -/
def tryCommitS (S : StrongSpec) (s : State) (p : Proposal) : Option State :=
  if p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      acceptStrongWire S s.active p.candidate = true then
    some ⟨s.generation + 1, p.candidate⟩
  else none

/-- **End-to-end refinement of a successful strong commit.** -/
theorem commitS_refines {S : StrongSpec} {s s' : State} {p : Proposal}
    (h : tryCommitS S s p = some s') :
    ∃ old cand : WideNet,
      encode old = s.active ∧ encode cand = s'.active ∧
      decode S.arch s.active = some old ∧ decode S.arch s'.active = some cand ∧
      StrongAdmissible S old cand ∧
      s'.generation = s.generation + 1 ∧
      p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      (∀ x : Int, infer S.arch s'.active x = some (predict cand x)) ∧
      (∀ x : Int, infer S.arch s.active x = some (predict S.target x) →
        infer S.arch s'.active x = some (predict S.target x)) ∧
      (∀ B, ErrBound old S.target S.lo S.hi B → ErrBound cand S.target S.lo S.hi B) := by
  unfold tryCommitS at h
  by_cases hc : p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      acceptStrongWire S s.active p.candidate = true
  · rw [if_pos hc] at h
    cases h
    obtain ⟨hg, ha, hw⟩ := hc
    obtain ⟨old, cand, ho, hn, hadm⟩ := (acceptStrongWire_iff S _ _).mp hw
    obtain ⟨hvo, hvn⟩ := strongAdmissible_valid hadm
    refine ⟨old, cand, ho, hn, ho ▸ decode_encode _ _ hvo, hn ▸ decode_encode _ _ hvn,
      hadm, rfl, hg, ha, ?_, ?_, hadm.2.2⟩
    · intro x
      show infer S.arch p.candidate x = _
      rw [← hn]; exact infer_encode _ _ hvn x
    · intro x hold
      show infer S.arch p.candidate x = _
      rw [← ho, infer_encode _ _ hvo] at hold
      rw [← hn, infer_encode _ _ hvn, hadm.2.1 x (Option.some.inj hold)]
  · rw [if_neg hc] at h; cases h

/-- **Commit completeness.** -/
theorem commitS_complete (S : StrongSpec) (s : State) (old cand : WideNet)
    (hs : s.active = encode old) (hadm : StrongAdmissible S old cand) :
    tryCommitS S s ⟨s.generation, s.active, encode cand⟩ =
      some ⟨s.generation + 1, encode cand⟩ := by
  have hw : acceptStrongWire S s.active (encode cand) = true :=
    (acceptStrongWire_iff S _ _).mpr ⟨old, cand, hs.symm, rfl, hadm⟩
  simp [tryCommitS, hw]

theorem staleS_rejected (S : StrongSpec) (s : State) (p : Proposal)
    (h : p.expectedGeneration ≠ s.generation) : tryCommitS S s p = none := by
  simp [tryCommitS, h]

theorem substitutedS_rejected (S : StrongSpec) (s : State) (p : Proposal)
    (h : p.expectedActive ≠ s.active) : tryCommitS S s p = none := by
  simp [tryCommitS, h]

def gatedCommitS (S : StrongSpec) (s : State) (p : Proposal) : State :=
  (tryCommitS S s p).getD s

def runCommitsS (S : StrongSpec) : State → List Proposal → State
  | s, [] => s
  | s, p :: ps => runCommitsS S (gatedCommitS S s p) ps

/-- **Arbitrary commit sequences under the strong gate.** -/
theorem runCommitsS_invariant (S : StrongSpec) (ps : List Proposal) (s : State) (m₀ : WideNet)
    (h₀ : decode S.arch s.active = some m₀) :
    ∃ m, decode S.arch (runCommitsS S s ps).active = some m ∧
      s.generation ≤ (runCommitsS S s ps).generation ∧
      ((runCommitsS S s ps).generation - s.generation) + loss S.corpusSpec m ≤
        loss S.corpusSpec m₀ ∧
      (∀ x : Int, predict m₀ x = predict S.target x → predict m x = predict S.target x) ∧
      (∀ B, ErrBound m₀ S.target S.lo S.hi B → ErrBound m S.target S.lo S.hi B) := by
  induction ps generalizing s m₀ with
  | nil => exact ⟨m₀, h₀, Nat.le_refl _, by simp [runCommitsS], fun _ h => h, fun _ h => h⟩
  | cons p ps ih =>
    simp only [runCommitsS]
    cases hc : tryCommitS S s p with
    | none =>
      have : gatedCommitS S s p = s := by simp [gatedCommitS, hc]
      rw [this]
      exact ih s m₀ h₀
    | some s' =>
      have hg : gatedCommitS S s p = s' := by simp [gatedCommitS, hc]
      rw [hg]
      obtain ⟨old, cand, _, _, hdo, hdn, hadm, hgen, _⟩ := commitS_refines hc
      rw [h₀] at hdo
      cases hdo
      obtain ⟨m, hm, hle, hbound, hpres, hrob⟩ := ih s' cand hdn
      refine ⟨m, hm, by omega, ?_, fun x hx => hpres x (hadm.2.1 x hx),
        fun B hB => hrob B (hadm.2.2 B hB)⟩
      have := hadm.1.2.2.2.2
      omega

/-- **Served-error guarantee.** After any sequence of proposals, every prediction served
from the active artifact at an input of `[lo,hi]` is within the exact worst-case error of
the initial model. -/
theorem served_error_le (S : StrongSpec) (ps : List Proposal) (s : State) (m₀ : WideNet)
    (h₀ : decode S.arch s.active = some m₀) (x y : Int) (hx1 : S.lo ≤ x) (hx2 : x ≤ S.hi)
    (hy : infer S.arch (runCommitsS S s ps).active x = some y) :
    (y - predict S.target x).natAbs ≤ maxAbsErr m₀ S.target S.lo S.hi := by
  obtain ⟨m, hm, -, -, -, hrob⟩ := runCommitsS_invariant S ps s m₀ h₀
  have hB := hrob _ ((maxAbsErr_le_iff m₀ S.target S.lo S.hi _).mp (Nat.le_refl _))
  have : y = predict m x := by
    simp only [infer, hm, Option.map_some, Option.some.injEq] at hy
    exact hy.symm
  subst this
  exact hB x hx1 hx2

/-- After any sequence of proposals, every integer that the initial artifact served
correctly is still served correctly. -/
theorem served_noForget (S : StrongSpec) (ps : List Proposal) (s : State) (m₀ : WideNet)
    (h₀ : decode S.arch s.active = some m₀) (x : Int)
    (hx : infer S.arch s.active x = some (predict S.target x)) :
    infer S.arch (runCommitsS S s ps).active x = some (predict S.target x) := by
  obtain ⟨m, hm, -, -, hpres, -⟩ := runCommitsS_invariant S ps s m₀ h₀
  simp only [infer, h₀, Option.map_some, Option.some.injEq] at hx
  simp only [infer, hm, Option.map_some, hpres x hx]

/-! ## Executable fixtures (the robust chain of `ProofGatedStrongGate` on `[-10^9,10^9]`) -/

theorem chain_wires :
    encode gen0 = "PGSI2-WIDE|0" ∧ encode r1 = "PGSI2-WIDE|0|-2|0|1" ∧
      encode r2 = "PGSI2-WIDE|0|-1|1|1" ∧
      encode gen3 = "PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2" := by
  decide +kernel

/-- Three successive string-level strong commits, derived from the model-level
acceptance certificates via `commitS_complete`. -/
theorem three_strong_commits :
    runCommitsS specWide ⟨0, encode gen0⟩
      [⟨0, encode gen0, encode r1⟩, ⟨1, encode r1, encode r2⟩,
       ⟨2, encode r2, encode gen3⟩] = ⟨3, encode gen3⟩ := by
  have s1 : acceptStrong specWide gen0 r1 = true := by decide
  have s2 : acceptStrong specWide r1 r2 = true := by decide
  have s3 : acceptStrong specWide r2 gen3 = true := by decide
  have a1 := commitS_complete specWide ⟨0, encode gen0⟩ gen0 r1 rfl (acceptStrong_sound s1)
  have a2 := commitS_complete specWide ⟨1, encode r1⟩ r1 r2 rfl (acceptStrong_sound s2)
  have a3 := commitS_complete specWide ⟨2, encode r2⟩ r2 gen3 rfl (acceptStrong_sound s3)
  simp only [runCommitsS, gatedCommitS]
  rw [a1]; simp only [Option.getD_some]
  rw [a2]; simp only [Option.getD_some]
  rw [a3]; simp only [Option.getD_some]

/-- The out-of-distribution candidate is refused at the wire level by the strong gate on
`[-50,50]`, although the corpus-only gate of `ProofGatedNetArtifacts` accepts it. -/
theorem ood_wire_rejected :
    acceptStrongWire specMid (encode gen2) (encode PCS.V2.ProofGatedLimits.oodCandidate)
      = false ∧
    PCS.V2.ProofGatedNetArtifacts.acceptWire ⟨arch3, predict gen3, corpus9⟩ (encode gen2)
      (encode PCS.V2.ProofGatedLimits.oodCandidate) = true := by
  have hv2 : valid arch3 gen2 = true := by decide
  have hvo : valid arch3 PCS.V2.ProofGatedLimits.oodCandidate = true := by decide
  rw [acceptStrongWire_encode specMid _ _ hv2 hvo,
    PCS.V2.ProofGatedNetArtifacts.acceptWire_encode _ _ _ hv2 hvo]
  exact ⟨ood_only_C.2.2.2.2.2, by decide⟩

end PCS.V2.ProofGatedStrongArtifacts
