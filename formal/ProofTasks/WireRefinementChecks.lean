import PCS.WireCodecVectors

/-!
Additional machine-checked confirmations for the wire refinement verification pass
(`WIRE_REFINEMENT_VERIFY_PROMPT.md`, item 7).

* Unknown wire-format / spec-version / checker-version / enum strings are rejected
  by `decodeRawWire`.
* The raw recorded invariant booleans and the raw `wireSemanticHash` are ignored
  by the decoder, and a raw wire that *claims* all invariants hold can still decode
  to a typed wire that is **not** `WellFormed`. Hence neither is a proof of
  `WellFormed`.
-/

namespace PCS.ProofTasks.WireRefinementChecks

open PCS
open PCS.Decision
open PCS.Wire
open PCS.WireVectors
open PCS.WireCodec
open PCS.WireCodecVectors

/-! ### Unknown version / enum strings are rejected -/

example :
    decodeRawWire
      { rawPkpdWire with source := { rawPkpdWire.source with specVersion := "pcs-9.9" } }
      = none := by
  rfl

example :
    decodeRawWire
      { rawPkpdWire with
        source := { rawPkpdWire.source with checkerVersion := "rogue-checker/1.0" } }
      = none := by
  rfl

example :
    decodeRawWire
      { rawPkpdWire with claim := { rawPkpdWire.claim with kind := "astrological" } }
      = none := by
  rfl

example :
    decodeRawWire
      { rawPkpdWire with
        evidence := [{ id := "E_PK_REPLAY", kind := "computational_test",
                       outcome := "MAYBE",
                       predicateCommitment := some pkpdPredicateCommitment }] }
      = none := by
  rfl

example :
    decodeRawWire { rawPkpdWire with decision := "ACCEPTED" } = none := by
  rfl

/-! ### Raw invariant booleans and wire hash are not trusted -/

/-- The decoder output does not depend on the recorded invariant booleans or the
recorded wire hash: arbitrary values give the same typed wire. -/
theorem decode_ignores_invariants_and_hash
    (raw : RawDecisionWire) (inv : RawInvariantSummary) (hash : String) :
    decodeRawWire { raw with invariants := inv, wireSemanticHash := hash } =
      decodeRawWire raw := by
  rfl

/-- A forged raw wire: all recorded invariant flags are `true`, the recorded hash is
unchanged, but the recorded decision is upgraded to `FORMALLY_VERIFIED_UNDER_ASSUMPTIONS`. -/
def forgedDecisionRaw : RawDecisionWire :=
  { rawPkpdWire with decision := "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS" }

example : forgedDecisionRaw.invariants.uniqueEvidenceIds = true ∧
    forgedDecisionRaw.invariants.requiredIdsUnique = true ∧
    forgedDecisionRaw.invariants.allRequiredEvidencePresent = true ∧
    forgedDecisionRaw.invariants.contextCovers = true ∧
    forgedDecisionRaw.invariants.requiredEvidenceBound = true := by
  decide

/-- The forged raw wire decodes successfully, yet the decoded typed wire is not
`WellFormed`: the recorded-invariant flags do not provide a `WellFormed` proof. -/
theorem forged_decision_decodes_but_not_wellFormed :
    ∃ w, decodeRawWire forgedDecisionRaw = some w ∧ ¬ WellFormed w := by
  refine ⟨{ pkpdWire with recordedDecision := DecisionStatus.formal }, rfl, ?_⟩
  intro h
  have hd := h.decision
  revert hd
  decide

/-- A second forgery: the recorded flags claim scope/binding invariants hold, but the
claim's assumption scope names an assumption absent from the context. -/
def forgedScopeRaw : RawDecisionWire :=
  { rawPkpdWire with
    claim := { rawPkpdWire.claim with assumptions := ["A_PK_MODEL", "A_UNDECLARED"] } }

theorem forged_scope_decodes_but_not_wellFormed :
    ∃ w, decodeRawWire forgedScopeRaw = some w ∧ ¬ WellFormed w := by
  refine ⟨{ pkpdWire with
    claim := { pkpdWire.claim with assumptions := ["A_PK_MODEL", "A_UNDECLARED"] } },
    rfl, ?_⟩
  intro h
  have hc := h.exactContextScope
  revert hc
  decide

end PCS.ProofTasks.WireRefinementChecks
