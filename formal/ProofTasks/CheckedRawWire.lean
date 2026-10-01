import PCS.WireCodec
import PCS.WireCheck

/-!
Next refinement step after the verified finite wire checker.

This task composes the structural/version/enum decoder with the verified Boolean
wire checker. It deliberately starts from the already typed `RawDecisionWire`;
raw JSON text/bytes, JSON Schema, SHA-256/Ed25519, and Python scientific replay
remain outside this theorem.
-/

namespace PCS.ProofTasks.CheckedRawWire

open PCS
open PCS.Decision
open PCS.Wire
open PCS.WireCodec
open PCS.WireCheck

/--
Decode structural/version/enum syntax, then keep the typed wire only if the
machine-checked finite checker accepts it.
-/
def checkedDecodeRawWire (raw : RawDecisionWire) : Option DecisionWire :=
  match decodeRawWire raw with
  | none => none
  | some w => if wireCheck w then some w else none

/-- Successful checked decoding came from the structural raw-wire decoder. -/
theorem checkedDecodeRawWire_decodes
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w) :
    decodeRawWire raw = some w := by
  sorry

/-- Successful checked decoding means the finite checker accepted the result. -/
theorem checkedDecodeRawWire_checked
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w) :
    wireCheck w = true := by
  sorry

/-- Successful checked decoding constructs the verified formal invariant. -/
theorem checkedDecodeRawWire_sound
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w) :
    WellFormed w := by
  sorry

theorem checkedDecodeRawWire_computational_sound
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w)
    (accepted : w.recordedDecision = DecisionStatus.computational) :
    Assures
      (decodedContext w)
      AssuranceLevel.computational
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  sorry

theorem checkedDecodeRawWire_formal_sound
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w)
    (accepted : w.recordedDecision = DecisionStatus.formal) :
    Assures
      (decodedContext w)
      AssuranceLevel.formal
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  sorry

theorem checkedDecodeRawWire_empirical_sound
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w)
    (accepted : w.recordedDecision = DecisionStatus.empirical) :
    Assures
      (decodedContext w)
      AssuranceLevel.empirical
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  sorry

theorem checkedDecodeRawWire_mixed_sound
    {raw : RawDecisionWire} {w : DecisionWire}
    (h : checkedDecodeRawWire raw = some w)
    (accepted : w.recordedDecision = DecisionStatus.mixed) :
    Assures
      (decodedContext w)
      AssuranceLevel.mixed
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  sorry

end PCS.ProofTasks.CheckedRawWire
