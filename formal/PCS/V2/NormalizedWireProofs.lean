import PCS.V2.NormalizedWire

/-!
# Soundness of the Lean v0.6/v2 normalized-decision byte checker

Main theorems (all about `verifyWireBytes : ByteArray → Option WireV2`):

* `verifyWireBytes_canonical`  : the accepted bytes are exactly `encodedBytes w`;
* `verifyWireBytes_nonmalleable` : no two different byte strings are accepted as
  the same typed wire;
* `verifyWireBytes_parser_independent` : every JSON value whose canonical bytes
  are the accepted bytes is the encoding of the returned wire;
* `verifyWireBytes_schema` / `verifyWireBytes_wellFormed` : schema + `WellFormed`;
* `verifyWireBytes_hash` : the stored `wire_semantic_hash` is the domain-separated
  SHA-256 of the exact projection;
* `verifyWireBytes_assures` : accepted decision level `L` ⇒ `Assures Γ L C E`.
-/

namespace PCS.V2.NormalizedWire

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common

/-! ## Decoder soundness -/

theorem decodeSource_sound {v : JVal} {s : SourceV2} (h : decodeSource v = some s) :
    encodeSource s = v := by
  unfold decodeSource at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i ih' sh' hih hsh
        cases h
        simp [encodeSource, hexEncode_of_hexDecode hih, hexEncode_of_hexDecode hsh]
      · cases h
    · cases h
  · cases h

theorem decodeAssumption_sound {v : JVal} {a : AssumptionV2} (h : decodeAssumption v = some a) :
    encodeAssumption a = v := by
  unfold decodeAssumption at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl⟩ := hk
      cases h; rfl
    · cases h
  · cases h

theorem hexDecode'_sound {s : String} {d : List UInt8} (h : decodeClaim.hexDecode' s = some d) :
    commitmentStr d = s := by
  unfold decodeClaim.hexDecode' at h
  split at h
  · rename_i hp
    unfold commitmentStr
    rw [hexChars_of_decodeChars h, ← hp, List.take_append_drop]
    simp
  · cases h

theorem decodeClaim_sound {v : JVal} {c : ClaimV2} (h : decodeClaim v = some c) :
    encodeClaim c = v := by
  unfold decodeClaim at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i as' kd' pc' re' has hkd hpc hre
        cases h
        simp only [encodeClaim, strArray_sound has, strArray_sound hre, decodeEnum_sound hkd,
          hexDecode'_sound hpc]
      · cases h
    · cases h
  · cases h

theorem decodeEvidence_sound {v : JVal} {e : EvidenceV2} (h : decodeEvidence v = some e) :
    encodeEvidence e = v := by
  unfold decodeEvidence at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i kd' oc' pc' hkd hoc hpc
        cases h
        simp only [encodeEvidence, decodeEnum_sound hkd, decodeEnum_sound hoc,
          hexDecode'_sound hpc]
      · cases h
    · cases h
  · cases h

theorem decodeStructure_sound {v : JVal} {w : WireV2} (h : decodeStructure v = some w) :
    encodeWire w = v := by
  unfold decodeStructure at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i cl' ctx' dec' ev' src' wsh' hcl hctx hdec hev hsrc hwsh
        cases h
        simp only [encodeWire, coreMembers, decodeClaim_sound hcl,
          mapOpt_inv (fun x y hxy => decodeAssumption_sound hxy) hctx,
          decodeEnum_sound hdec, mapOpt_inv (fun x y hxy => decodeEvidence_sound hxy) hev,
          decodeSource_sound hsrc, hexEncode_of_hexDecode hwsh, List.cons_append,
          List.nil_append]
      · cases h
    · cases h
  · cases h

theorem decodeWire_sound {v : JVal} {w : WireV2} (h : decodeWire v = some w) :
    encodeWire w = v ∧ schemaOK w = true := by
  unfold decodeWire at h
  split at h
  · rename_i w' hw
    split at h
    · cases h; exact ⟨decodeStructure_sound hw, by assumption⟩
    · cases h
  · cases h

/-! ## Byte-level checker soundness -/

/-- Everything the checker establishes, as one structure. -/
structure Accepted (raw : ByteArray) (w : WireV2) : Prop where
  bytes : raw = encodedBytes w
  canonical : canonical (encodeWire w) = true
  size : raw.size ≤ maxWireBytes
  schema : schemaOK w = true
  semantic : semanticOK w = true

theorem verifyWireBytes_accepted {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) : Accepted raw w := by
  unfold verifyWireBytes at h
  split at h
  · cases h
  · rename_i v hv
    split at h
    · cases h
    · rename_i w' hw
      split at h
      · cases h
        obtain ⟨hraw, hcanon, hsize⟩ := parseCanonicalBytes_sound hv
        obtain ⟨henc, hschema⟩ := decodeWire_sound hw
        subst henc
        exact ⟨hraw, hcanon, hsize, hschema, by assumption⟩
      · cases h

/-- (A, C) The accepted bytes are exactly the canonical encoding of the typed wire. -/
theorem verifyWireBytes_canonical {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) : raw = encodedBytes w :=
  (verifyWireBytes_accepted h).bytes

/-- (C) Non-malleability: one typed wire has exactly one accepted byte string. -/
theorem verifyWireBytes_nonmalleable {raw₁ raw₂ : ByteArray} {w : WireV2}
    (h₁ : verifyWireBytes raw₁ = some w) (h₂ : verifyWireBytes raw₂ = some w) : raw₁ = raw₂ :=
  (verifyWireBytes_canonical h₁).trans (verifyWireBytes_canonical h₂).symm

/-- (A) No parser ambiguity: any JSON value (from any parser) whose canonical bytes
    are the accepted bytes is the encoding of the returned typed wire. -/
theorem verifyWireBytes_parser_independent {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) {v : JVal} (hv : jcsBytes v = raw) : v = encodeWire w :=
  jcsBytes_injective (hv.trans (verifyWireBytes_canonical h))

/-- (B) Complete structural schema. -/
theorem verifyWireBytes_schema {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) : schemaOK w = true :=
  (verifyWireBytes_accepted h).schema

private theorem semanticOK_parts {w : WireV2} (h : semanticOK w = true) :
    hashOK w = true ∧ PCS.WireCheck.wireCheck (toV1 w) = true ∧ contextIdsUnique w = true := by
  simp only [semanticOK, Bool.and_eq_true] at h
  exact ⟨h.1.1, h.1.2, h.2⟩

/-- (P2) Hash binding wiring: the stored digest is SHA-256 of the exact
    domain-separated canonical projection. -/
theorem verifyWireBytes_hash {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) :
    w.wireSemanticHash = domainDigest normalizedDecisionDomain (projection w) := by
  have := (semanticOK_parts (verifyWireBytes_accepted h).semantic).1
  simpa [hashOK, expectedHash] using this

/-- (D) The refined v1 wire satisfies the existing formal invariant. -/
theorem verifyWireBytes_wellFormed {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) : PCS.Wire.WellFormed (toV1 w) :=
  PCS.WireCheck.wireCheck_sound (semanticOK_parts (verifyWireBytes_accepted h).semantic).2.1

theorem verifyWireBytes_context_unique {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) : (w.context.map (·.id)).Nodup := by
  have := (semanticOK_parts (verifyWireBytes_accepted h).semantic).2.2
  simpa [contextIdsUnique] using this

/-- (E) Decision soundness for every supported claim mode. -/
theorem verifyWireBytes_assures {raw : ByteArray} {w : WireV2} {L : AssuranceLevel}
    (h : verifyWireBytes raw = some w) (hL : levelOf w.decision = some L) :
    Assures (gamma w) L (kernelClaim w) (kernelEvidence w) := by
  have hwf := verifyWireBytes_wellFormed h
  cases hd : w.decision <;> rw [hd] at hL <;> simp [levelOf] at hL <;> subst hL
  · exact PCS.Wire.wire_formal_sound (toV1 w) hwf hd
  · exact PCS.Wire.wire_computational_sound (toV1 w) hwf hd
  · exact PCS.Wire.wire_empirical_sound (toV1 w) hwf hd
  · exact PCS.Wire.wire_mixed_sound (toV1 w) hwf hd

theorem verifyWireBytes_computational_sound {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) (hd : w.decision = .computational) :
    Assures (gamma w) .computational (kernelClaim w) (kernelEvidence w) :=
  verifyWireBytes_assures h (by rw [hd]; rfl)

theorem verifyWireBytes_formal_sound {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) (hd : w.decision = .formal) :
    Assures (gamma w) .formal (kernelClaim w) (kernelEvidence w) :=
  verifyWireBytes_assures h (by rw [hd]; rfl)

theorem verifyWireBytes_empirical_sound {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) (hd : w.decision = .empirical) :
    Assures (gamma w) .empirical (kernelClaim w) (kernelEvidence w) :=
  verifyWireBytes_assures h (by rw [hd]; rfl)

theorem verifyWireBytes_mixed_sound {raw : ByteArray} {w : WireV2}
    (h : verifyWireBytes raw = some w) (hd : w.decision = .mixed) :
    Assures (gamma w) .mixed (kernelClaim w) (kernelEvidence w) :=
  verifyWireBytes_assures h (by rw [hd]; rfl)

end PCS.V2.NormalizedWire
