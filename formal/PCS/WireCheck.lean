import PCS.Wire

/-!
Finite Boolean wire checker and its soundness bridge.

`wireCheck` is a total, executable Boolean test over a typed `DecisionWire`.
`wireCheck_sound` proves that a successful check constructs the typed formal
invariant `PCS.Wire.WellFormed`, so the existing `wire_*_sound` theorems apply:

  typed DecisionWire + wireCheck = true -> WellFormed -> Assures

Raw JSON parsing, JSON Schema validation, SHA-256/Ed25519, Python scientific
replay, and the JSON-text-to-typed-raw-wire construction remain outside this
theorem.
-/

namespace PCS.WireCheck

open PCS
open PCS.Decision
open PCS.Refinement
open PCS.Normalization
open PCS.Wire

def idsUnique (w : DecisionWire) : Bool :=
  decide (evidenceIds w).Nodup

def exactContextScope (w : DecisionWire) : Bool :=
  contextIds w == w.claim.assumptions

def evidenceCommitmentsBound (w : DecisionWire) : Bool :=
  w.evidence.all (fun e =>
    e.predicateCommitment == w.claim.predicateCommitment)

def wireCheck (w : DecisionWire) : Bool :=
  (w.source.claimId == w.claim.id) &&
  (evidenceIds w == w.claim.requiredEvidence) &&
  idsUnique w &&
  exactContextScope w &&
  evidenceCommitmentsBound w &&
  (decideClaim (decodeClaim w.claim) (decodedEvidence w) ==
    w.recordedDecision)

/-- A `Nodup` image under `f` makes `f` injective on the source list. -/
private theorem eq_of_mem_of_nodup_map {α β : Type} (f : α → β) :
    ∀ {l : List α}, (l.map f).Nodup →
      ∀ a ∈ l, ∀ b ∈ l, f a = f b → a = b
  | [], _, a, ha, _, _, _ => by simp at ha
  | x :: xs, h, a, ha, b, hb, hab => by
    simp only [List.map_cons, List.nodup_cons, List.mem_map] at h
    obtain ⟨hx, hxs⟩ := h
    simp only [List.mem_cons] at ha hb
    rcases ha with rfl | ha <;> rcases hb with rfl | hb
    · rfl
    · exact absurd ⟨b, hb, hab.symm⟩ hx
    · exact absurd ⟨a, ha, hab⟩ hx
    · exact eq_of_mem_of_nodup_map f hxs a ha b hb hab

/--
A no-duplicate-ID fact about the wire evidence list is enough to establish the
strong uniqueness field required by the normalized decision input.
-/
theorem decodedEvidence_unique_of_wire_ids_nodup
    {w : DecisionWire}
    (h : (evidenceIds w).Nodup) :
    UniqueEvidenceIds (decodedEvidence w) := by
  intro e₁ h₁ e₂ h₂ hid
  simp only [decodedEvidence, List.mem_map] at h₁ h₂
  obtain ⟨x₁, hx₁, rfl⟩ := h₁
  obtain ⟨x₂, hx₂, rfl⟩ := h₂
  have hx : x₁ = x₂ :=
    eq_of_mem_of_nodup_map (fun e : WireEvidence => e.id) h x₁ hx₁ x₂ hx₂ hid
  rw [hx]

/-- Exact claim-scoped context IDs imply the kernel's explicit context coverage. -/
theorem contextCovers_of_exact_context_scope
    {w : DecisionWire}
    (h : contextIds w = w.claim.assumptions) :
    ContextCovers (decodedContext w) (decodeClaim w.claim) := by
  intro aid haid
  have hmem : aid ∈ contextIds w := by
    rw [h]
    exact haid
  simp only [contextIds, List.mem_map] at hmem
  obtain ⟨a, ha, rfl⟩ := hmem
  exact ⟨decodeAssumption a, List.mem_map_of_mem ha, rfl⟩

/--
If every wire evidence object has the same full predicate commitment as the
claim, the decoded required evidence is predicate-bound in the Lean kernel.
-/
theorem requiredEvidenceBound_of_commitments
    {w : DecisionWire}
    (h : ∀ e ∈ w.evidence,
      e.predicateCommitment = w.claim.predicateCommitment) :
    RequiredEvidenceBound (decodeClaim w.claim) (decodedEvidence w) := by
  intro e he
  have hsrc : e ∈ decodedEvidence w := (mem_requiredEvidenceFor_iff.mp he).1
  simp only [decodedEvidence, List.mem_map] at hsrc
  obtain ⟨x, hx, rfl⟩ := hsrc
  simp only [decodeEvidence, decodeClaim]
  exact predicate_commitment_eq_preserved (h x hx)

/-- A successful finite Boolean wire check constructs the typed formal invariant. -/
theorem wireCheck_sound
    {w : DecisionWire}
    (h : wireCheck w = true) :
    WellFormed w := by
  simp only [wireCheck, Bool.and_eq_true, beq_iff_eq] at h
  obtain ⟨⟨⟨⟨⟨hsrc, hev⟩, huniq⟩, hctx⟩, hcomm⟩, hdec⟩ := h
  have hnodup : (evidenceIds w).Nodup := of_decide_eq_true huniq
  have hctxEq : contextIds w = w.claim.assumptions := by
    simpa [exactContextScope] using hctx
  have hcommAll : ∀ e ∈ w.evidence,
      e.predicateCommitment = w.claim.predicateCommitment := by
    simpa [evidenceCommitmentsBound] using hcomm
  exact {
    sourceClaim := hsrc
    exactEvidenceScope := hev
    exactContextScope := hctxEq
    uniqueEvidenceIds := decodedEvidence_unique_of_wire_ids_nodup hnodup
    context := contextCovers_of_exact_context_scope hctxEq
    binding := requiredEvidenceBound_of_commitments hcommAll
    decision := hdec
  }

theorem wireCheck_computational_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.computational) :
    Assures
      (decodedContext w)
      AssuranceLevel.computational
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_computational_sound w (wireCheck_sound checked) accepted

theorem wireCheck_formal_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.formal) :
    Assures
      (decodedContext w)
      AssuranceLevel.formal
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_formal_sound w (wireCheck_sound checked) accepted

theorem wireCheck_empirical_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.empirical) :
    Assures
      (decodedContext w)
      AssuranceLevel.empirical
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_empirical_sound w (wireCheck_sound checked) accepted

theorem wireCheck_mixed_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.mixed) :
    Assures
      (decodedContext w)
      AssuranceLevel.mixed
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_mixed_sound w (wireCheck_sound checked) accepted

end PCS.WireCheck
