import PCS.V2.ProofGatedProtocol
import PCS.V2.ProofGatedInterpreter

/-!
# V6 end-to-end theorem: from certificate bytes to executed predictions

`v6_end_to_end` composes the V6 chain in one statement. Start from any state whose active
bytes decode (under the deployment architecture) to a network `m₀`, and feed the
promotion state machine **any** list of certificate byte strings. Then the final active
bytes are the canonical encoding of a valid network `m` such that:

* the **independent reference interpreter** run on the final active bytes returns exactly
  `predict m x`, for every integer `x`;
* every integer on which `m₀` agreed with the target is still served correctly;
* every input of `[lo, hi]` is served within the exact worst-case error of `m₀`;
* the number of accepted certificates plus the final corpus loss is at most the initial
  corpus loss, and the generation advanced by exactly the number of acceptances;
* every logged acceptance is justified by a certificate that the checker accepts;
* if the deployment architecture satisfies `NoOverflow` for an input bound `X`, a runtime
  with registers of `2·h` values (e.g. `int64`) computes `predict m x` exactly for
  `|x| ≤ X`.

`v6_end_to_end_complete`: conversely, every admissible chain is realised.
-/

namespace PCS.V2.ProofGatedV6EndToEnd

open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedProtocol
open PCS.V2.ProofGatedInterpreter

theorem v6_end_to_end (S : StrongSpec) (s : PState) (m₀ : WideNet)
    (h₀ : decodeBytes S.arch s.active = some m₀) (cbs : List Bytes) :
    ∃ m, encodeBytes m = (run S s cbs).1.active ∧ valid S.arch m = true ∧
      (∀ x, interpBytes S.arch (run S s cbs).1.active x = some (predict m x)) ∧
      (∀ x, predict m₀ x = predict S.target x → predict m x = predict S.target x) ∧
      (∀ x, S.lo ≤ x → x ≤ S.hi → errAt m S.target x ≤ maxAbsErr m₀ S.target S.lo S.hi) ∧
      acceptedCount (run S s cbs).2 + loss S.corpusSpec m ≤ loss S.corpusSpec m₀ ∧
      (run S s cbs).1.generation = s.generation + acceptedCount (run S s cbs).2 ∧
      (∀ e ∈ (run S s cbs).2, EntryOK S e) ∧
      (∀ X h, NoOverflow S.arch X h → ∀ x : Int, x.natAbs ≤ X → predictK h m x = predict m x) := by
  obtain ⟨m, ⟨hd, hnf, hrob⟩, hg, hl⟩ := run_invariant S cbs s m₀ h₀
  have hv := decodeBytes_valid hd
  refine ⟨m, decodeBytes_canonical hd, hv, fun x => ?_, hnf, ?_, hl, hg,
    run_log_sound S cbs s, fun X h hno x hx => predictK_eq_predict S.arch X h hno m hv x hx⟩
  · rw [interpBytes_eq_inferBytes]; simp [inferBytes, hd]
  · exact hrob _ ((maxAbsErr_le_iff m₀ S.target S.lo S.hi _).mp (Nat.le_refl _))

theorem v6_end_to_end_complete (S : StrongSpec) (g : Nat) (a : WideNet) (ms : List WideNet)
    (hc : AdmChain S a ms) (hv : valid S.arch (lastModel a ms) = true) :
    (run S ⟨g, encodeBytes a⟩ (genCerts S g a ms)).1.active = encodeBytes (lastModel a ms) ∧
    ∀ x, interpBytes S.arch (run S ⟨g, encodeBytes a⟩ (genCerts S g a ms)).1.active x =
      some (predict (lastModel a ms) x) := by
  have h := (run_complete S ms g a hc).1
  rw [h]
  exact ⟨rfl, fun x => interp_encode S.arch _ hv x⟩

end PCS.V2.ProofGatedV6EndToEnd
