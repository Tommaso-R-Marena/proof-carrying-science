import PCS.V2.NormalizedWireProofs

/-!
# Claim / predicate / evidence binding and hash non-substitution (P1, P2)

* `verifyWireBytes_scope` : exact claim/evidence/context scope, evidence-ID
  uniqueness, source-claim identity and the recomputed decision, at the v2 level;
* `verifyWireBytes_evidence_commitments` : every evidence item carries exactly
  the claim's 32-byte predicate commitment;
* `projection_injective` : the hashed projection determines every field;
* `wire_hash_binding` : two accepted wires with the same `wire_semantic_hash`
  are identical, or a SHA-256 collision exists;
* anti-substitution corollaries for claim, predicate commitment, evidence,
  context, decision and source-certificate hashes;
* `PredicateCommits` / `predicate_commitment_binding` : a commitment determines
  the committed predicate JSON up to a SHA-256 collision, and binds every
  evidence item of an accepted wire to the same predicate;
* `wire_digest_not_predicate_digest` : the decision-domain digest of an accepted
  wire cannot double as a predicate-domain commitment without a collision.
-/

namespace PCS.V2.Binding

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Common
open PCS.V2.NormalizedWire

/-! ## v2-level consequences of `WellFormed` -/

structure Scope (w : WireV2) : Prop where
  sourceClaim : w.source.claimId = w.claim.id
  evidenceScope : w.evidence.map (·.id) = w.claim.requiredEvidence
  contextScope : w.context.map (·.id) = w.claim.assumptions
  evidenceIdsUnique : (w.evidence.map (·.id)).Nodup
  contextIdsUnique : (w.context.map (·.id)).Nodup
  decision : decideClaim (kernelClaim w) (kernelEvidence w) = w.decision

theorem verifyWireBytes_scope {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) : Scope w := by
  have hwf := verifyWireBytes_wellFormed h
  have hsem := (verifyWireBytes_accepted h).semantic
  simp only [semanticOK, PCS.WireCheck.wireCheck, Bool.and_eq_true, beq_iff_eq] at hsem
  obtain ⟨⟨_, ⟨⟨⟨⟨_, _⟩, huniq⟩, _⟩, _⟩, _⟩, _⟩ := hsem
  refine ⟨hwf.sourceClaim, ?_, ?_, ?_, verifyWireBytes_context_unique h, hwf.decision⟩
  · have := hwf.exactEvidenceScope
    simpa [PCS.Wire.evidenceIds, toV1, toV1Evidence, toV1Claim, Function.comp_def] using this
  · have := hwf.exactContextScope
    simpa [PCS.Wire.contextIds, toV1, toV1Assumption, toV1Claim, Function.comp_def] using this
  · have := of_decide_eq_true huniq
    simpa [PCS.Wire.evidenceIds, toV1, toV1Evidence, Function.comp_def] using this

theorem verifyWireBytes_evidence_commitments {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) :
    ∀ e ∈ w.evidence, e.predicateCommitment = w.claim.predicateCommitment := by
  have hsem := (verifyWireBytes_accepted h).semantic
  simp only [semanticOK, PCS.WireCheck.wireCheck, Bool.and_eq_true, beq_iff_eq] at hsem
  obtain ⟨⟨_, ⟨⟨_, hcomm⟩, _⟩⟩, _⟩ := hsem
  intro e he
  simp only [PCS.WireCheck.evidenceCommitmentsBound, List.all_eq_true, beq_iff_eq, toV1,
    List.mem_map, toV1Evidence, toV1Claim] at hcomm
  have := hcomm _ ⟨e, he, rfl⟩
  simp only [Option.some.injEq] at this
  exact commitmentStr_injective this

/-! ## Injectivity of the hashed projection -/

theorem encodeSource_injective {a b : SourceV2} (h : encodeSource a = encodeSource b) : a = b := by
  simp only [encodeSource, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    true_and, and_true] at h
  obtain ⟨h1, h2, h3, h4⟩ := h
  cases a; cases b
  simp only at h1 h2 h3 h4
  rw [hexEncode_injective h1, hexEncode_injective h2, h3, h4]

theorem encodeAssumption_injective : ∀ a b, encodeAssumption a = encodeAssumption b → a = b := by
  intro a b h
  simp only [encodeAssumption, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    true_and, and_true] at h
  cases a; cases b; simp_all

theorem str_injective : ∀ a b : String, JVal.str a = JVal.str b → a = b := by
  intro a b h; cases h; rfl

theorem encodeClaim_injective {a b : ClaimV2} (h : encodeClaim a = encodeClaim b) : a = b := by
  simp only [encodeClaim, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    JVal.arr.injEq, true_and, and_true] at h
  obtain ⟨h1, h2, h3, h4, h5⟩ := h
  cases a; cases b
  simp only at h1 h2 h3 h4 h5
  rw [map_injective_of str_injective h1, h2, claimKindName_injective _ _ h3,
    commitmentStr_injective h4, map_injective_of str_injective h5]

theorem encodeEvidence_injective : ∀ a b, encodeEvidence a = encodeEvidence b → a = b := by
  intro a b h
  simp only [encodeEvidence, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    true_and, and_true] at h
  obtain ⟨h1, h2, h3, h4⟩ := h
  cases a; cases b
  simp only at h1 h2 h3 h4
  rw [h1, evidenceKindName_injective _ _ h2, outcomeName_injective _ _ h3,
    commitmentStr_injective h4]

/-- The hashed projection determines every field except the hash itself. -/
theorem projection_injective {w₁ w₂ : WireV2} (h : projection w₁ = projection w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) : w₁ = w₂ := by
  simp only [projection, coreMembers, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq,
    JVal.str.injEq, JVal.arr.injEq, true_and, and_true] at h
  obtain ⟨hc, hctx, hd, hev, hs⟩ := h
  cases w₁; cases w₂
  simp only at hc hctx hd hev hs hh
  rw [encodeClaim_injective hc, map_injective_of encodeAssumption_injective hctx,
    decisionName_injective _ _ hd, map_injective_of encodeEvidence_injective hev,
    encodeSource_injective hs, hh]

/-- `encodeWire` is injective (all fields, including the hash). -/
theorem encodeWire_injective {w₁ w₂ : WireV2} (h : encodeWire w₁ = encodeWire w₂) : w₁ = w₂ := by
  simp only [encodeWire, coreMembers, List.cons_append, List.nil_append, JVal.obj.injEq,
    List.cons.injEq, Prod.mk.injEq, JVal.str.injEq, JVal.arr.injEq, true_and, and_true] at h
  obtain ⟨hc, hctx, hd, hev, hs, hh⟩ := h
  apply projection_injective _ (hexEncode_injective hh)
  simp only [projection, coreMembers, hc, hctx, hd, hev, hs]

/-- Canonical bytes determine the typed wire. -/
theorem encodedBytes_injective {w₁ w₂ : WireV2} (h : encodedBytes w₁ = encodedBytes w₂) :
    w₁ = w₂ :=
  encodeWire_injective (jcsBytes_injective h)

/-! ## Hash binding -/

/-- (P2) Two accepted wires with equal `wire_semantic_hash` are identical, or a
    concrete SHA-256 collision exists. -/
theorem wire_hash_binding {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) : w₁ = w₂ ∨ Sha256Collision := by
  have e₁ := verifyWireBytes_hash h₁
  have e₂ := verifyWireBytes_hash h₂
  rw [e₁, e₂] at hh
  rcases digest_binding hh with ⟨_, hp⟩ | hcol
  · exact Or.inl (projection_injective hp (by rw [e₁, e₂, hp]))
  · exact Or.inr hcol

/-- Equal hashes and equal bytes coincide for accepted wires (up to collision). -/
theorem wire_hash_binds_bytes {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) : r₁ = r₂ ∨ Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact Or.inl (verifyWireBytes_nonmalleable h₁ h₂)
  · exact Or.inr c

/-! ## Anti-substitution corollaries (P1 / Objective 2 / Objective 9) -/

theorem claim_substitution_needs_collision {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) (hc : w₁.claim ≠ w₂.claim) :
    Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact absurd rfl hc
  · exact c

theorem predicate_substitution_needs_collision {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash)
    (hp : w₁.claim.predicateCommitment ≠ w₂.claim.predicateCommitment) : Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact absurd rfl hp
  · exact c

theorem evidence_substitution_needs_collision {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) (he : w₁.evidence ≠ w₂.evidence) :
    Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact absurd rfl he
  · exact c

theorem context_substitution_needs_collision {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) (he : w₁.context ≠ w₂.context) :
    Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact absurd rfl he
  · exact c

theorem decision_substitution_needs_collision {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) (hd : w₁.decision ≠ w₂.decision) :
    Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact absurd rfl hd
  · exact c

theorem source_substitution_needs_collision {r₁ r₂ : ByteArray} {w₁ w₂ : WireV2}
    (h₁ : verifyWireBytes r₁ = some w₁) (h₂ : verifyWireBytes r₂ = some w₂)
    (hh : w₁.wireSemanticHash = w₂.wireSemanticHash) (hs : w₁.source ≠ w₂.source) :
    Sha256Collision := by
  rcases wire_hash_binding h₁ h₂ hh with rfl | c
  · exact absurd rfl hs
  · exact c

/-! ## Predicate commitments -/

/-- `d` is the v2 predicate commitment of the predicate JSON `p`
    (`predicate_commitment_v06(p)` without the textual prefix). -/
def PredicateCommits (d : List UInt8) (p : JVal) : Prop :=
  d = domainDigest predicateCommitmentDomain p

/-- A commitment determines the predicate, or a SHA-256 collision exists. -/
theorem predicate_commitment_binding {d : List UInt8} {p₁ p₂ : JVal}
    (h₁ : PredicateCommits d p₁) (h₂ : PredicateCommits d p₂) : p₁ = p₂ ∨ Sha256Collision := by
  rcases digest_binding (h₁.symm.trans h₂) with ⟨_, hp⟩ | c
  · exact Or.inl hp
  · exact Or.inr c

/-- Evidence-to-claim predicate binding: if the claim's commitment opens to `p`,
    every evidence item of an accepted wire commits to the same `p`. -/
theorem evidence_bound_to_claim_predicate {raw : ByteArray} {w : WireV2} {p : JVal}
    (h : verifyWireBytes raw = some w) (hp : PredicateCommits w.claim.predicateCommitment p) :
    ∀ e ∈ w.evidence, PredicateCommits e.predicateCommitment p := by
  intro e he
  unfold PredicateCommits
  rw [verifyWireBytes_evidence_commitments h e he]
  exact hp

/-- Evidence cannot be about a different predicate than the claim (up to collision). -/
theorem evidence_predicate_unique {raw : ByteArray} {w : WireV2} {p q : JVal}
    (h : verifyWireBytes raw = some w) (hp : PredicateCommits w.claim.predicateCommitment p)
    {e : EvidenceV2} (he : e ∈ w.evidence) (hq : PredicateCommits e.predicateCommitment q) :
    q = p ∨ Sha256Collision :=
  predicate_commitment_binding hq (evidence_bound_to_claim_predicate h hp e he)

/-- Domain non-confusion: an accepted wire's decision-domain digest can equal
    some predicate-domain commitment only via a SHA-256 collision. -/
theorem wire_digest_not_predicate_digest {raw : ByteArray} {w : WireV2} {p : JVal}
    (h : verifyWireBytes raw = some w) (hc : PredicateCommits w.wireSemanticHash p) :
    Sha256Collision := by
  have e := verifyWireBytes_hash h
  rw [e] at hc
  exact cross_domain_digest_collision (by decide) hc

end PCS.V2.Binding
