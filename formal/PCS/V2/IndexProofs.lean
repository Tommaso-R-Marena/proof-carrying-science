import PCS.V2.Index

/-!
# Soundness of the normalized index and normalized-set checkers (P3)
-/

namespace PCS.V2.Index

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common
open PCS.V2.NormalizedWire PCS.V2.Binding

/-! ## Decoding soundness -/

theorem split3 {α : Type} (L : List α) (n m : Nat) (h : n + m ≤ L.length) :
    L.take n ++ (L.drop n).take (L.length - n - m) ++ L.drop (L.length - m) = L := by
  rw [← List.take_add, show n + (L.length - n - m) = L.length - m by omega]
  exact List.take_append_drop _ _

theorem decodePath_sound {s : String} {k : List UInt8} (h : decodePath s = some k) :
    keyPath k = s := by
  unfold decodePath at h
  simp only at h
  split at h
  · rename_i hc
    obtain ⟨hp, hs, hl⟩ := hc
    have hk := hexChars_of_decodeChars h
    unfold keyPath
    rw [hk, ← hp, ← hs, split3 _ _ _ hl, String.ofList_toList]
  · cases h

theorem decodeEntry_sound {v : JVal} {e : EntryV2} (h : decodeEntry v = some e) :
    encodeEntry e = v := by
  unfold decodeEntry at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i d key hh hd hkey hhh
        cases h
        simp only [encodeEntry, decodeEnum_sound hd, decodePath_sound hkey,
          hexEncode_of_hexDecode hhh]
      · cases h
    · cases h
  · cases h

theorem decodeStructure_sound {v : JVal} {i : IndexV2} (h : decodeStructure v = some i) :
    encodeIndex i = v := by
  unfold decodeStructure at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i ih' sh' es' ish' hih hsh hes hish
        cases h
        simp only [encodeIndex, coreMembers, hexEncode_of_hexDecode hih,
          hexEncode_of_hexDecode hsh, mapOpt_inv (fun x y hxy => decodeEntry_sound hxy) hes,
          hexEncode_of_hexDecode hish, List.cons_append, List.nil_append]
      · cases h
    · cases h
  · cases h

theorem decodeIndex_sound {v : JVal} {i : IndexV2} (h : decodeIndex v = some i) :
    encodeIndex i = v ∧ schemaOK i = true := by
  unfold decodeIndex at h
  split at h
  · rename_i i' hi
    split at h
    · cases h; exact ⟨decodeStructure_sound hi, by assumption⟩
    · cases h
  · cases h

/-! ## Index checker soundness -/

structure IndexAccepted (raw : ByteArray) (i : IndexV2) : Prop where
  bytes : raw = jcsBytes (encodeIndex i)
  canonical : canonical (encodeIndex i) = true
  schema : schemaOK i = true
  hash : i.indexSemanticHash = domainDigest normalizedIndexDomain (projection i)
  claimIdsUnique : (i.entries.map (·.claimId)).Nodup
  pathsUnique : (i.entries.map (·.storageKey)).Nodup
  pathsDerived : ∀ e ∈ i.entries, e.storageKey = storageKey e.claimId

theorem verifyIndexBytes_accepted {raw : ByteArray} {i : IndexV2}
    (h : verifyIndexBytes raw = some i) : IndexAccepted raw i := by
  unfold verifyIndexBytes at h
  split at h
  · cases h
  · rename_i v hv
    split at h
    · cases h
    · rename_i i' hi
      split at h
      · rename_i hsem
        cases h
        obtain ⟨hraw, hcanon, _⟩ := parseCanonicalBytes_sound hv
        obtain ⟨henc, hschema⟩ := decodeIndex_sound hi
        subst henc
        simp only [semanticOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq,
          List.all_eq_true] at hsem
        obtain ⟨⟨⟨hh, hc⟩, hp⟩, hd⟩ := hsem
        exact ⟨hraw, hcanon, hschema, hh, hc, hp, hd⟩
      · cases h

theorem verifyIndexBytes_nonmalleable {r₁ r₂ : ByteArray} {i : IndexV2}
    (h₁ : verifyIndexBytes r₁ = some i) (h₂ : verifyIndexBytes r₂ = some i) : r₁ = r₂ :=
  (verifyIndexBytes_accepted h₁).bytes.trans (verifyIndexBytes_accepted h₂).bytes.symm

/-! ## Index hash binding -/

theorem keyPath_injective {a b : List UInt8} (h : keyPath a = keyPath b) : a = b := by
  unfold keyPath at h
  have := congrArg String.toList h
  simp only [String.toList_ofList, List.append_assoc, List.append_cancel_left_eq,
    List.append_cancel_right_eq] at this
  exact hexChars_injective this

theorem encodeEntry_injective : ∀ a b, encodeEntry a = encodeEntry b → a = b := by
  intro a b h
  simp only [encodeEntry, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    true_and, and_true] at h
  obtain ⟨h1, h2, h3, h4⟩ := h
  cases a; cases b
  simp only at h1 h2 h3 h4
  rw [h1, decisionName_injective _ _ h2, keyPath_injective h3, hexEncode_injective h4]

theorem projection_injective {i₁ i₂ : IndexV2} (h : projection i₁ = projection i₂)
    (hh : i₁.indexSemanticHash = i₂.indexSemanticHash) : i₁ = i₂ := by
  simp only [projection, coreMembers, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq,
    JVal.str.injEq, JVal.arr.injEq, true_and, and_true] at h
  obtain ⟨h1, h2, h3⟩ := h
  cases i₁; cases i₂
  simp only at h1 h2 h3 hh
  rw [hexEncode_injective h1, hexEncode_injective h2, map_injective_of encodeEntry_injective h3, hh]

/-- Two accepted indexes with the same `index_semantic_hash` are identical, or a
    SHA-256 collision exists. -/
theorem index_hash_binding {r₁ r₂ : ByteArray} {i₁ i₂ : IndexV2}
    (h₁ : verifyIndexBytes r₁ = some i₁) (h₂ : verifyIndexBytes r₂ = some i₂)
    (hh : i₁.indexSemanticHash = i₂.indexSemanticHash) : i₁ = i₂ ∨ Sha256Collision := by
  have e₁ := (verifyIndexBytes_accepted h₁).hash
  have e₂ := (verifyIndexBytes_accepted h₂).hash
  rw [e₁, e₂] at hh
  rcases digest_binding hh with ⟨_, hp⟩ | c
  · exact Or.inl (projection_injective hp (by rw [e₁, e₂, hp]))
  · exact Or.inr c

/-- Index digests and wire digests live in different domains. -/
theorem index_digest_not_wire_digest {r₁ r₂ : ByteArray} {i : IndexV2} {w : WireV2}
    (h₁ : verifyIndexBytes r₁ = some i) (h₂ : verifyWireBytes r₂ = some w)
    (heq : i.indexSemanticHash = w.wireSemanticHash) : Sha256Collision := by
  rw [(verifyIndexBytes_accepted h₁).hash, verifyWireBytes_hash h₂] at heq
  exact cross_domain_digest_collision (by decide) heq

/-! ## File-map lemmas -/

theorem lookup_mem {files : FileMap} {p : String} {raw : ByteArray}
    (h : lookup files p = some raw) : (p, raw) ∈ files := by
  unfold lookup at h
  cases hf : files.find? (·.1 == p) with
  | none => rw [hf] at h; cases h
  | some q =>
    rw [hf] at h
    simp only [Option.map_some, Option.some.injEq] at h
    have hm := List.mem_of_find?_eq_some hf
    have hq := List.find?_some hf
    simp only [beq_iff_eq] at hq
    obtain ⟨a, b⟩ := q
    simp only at hq h
    subst hq h
    exact hm

/-- With unique names, the looked-up bytes are the only bytes stored under that name. -/
theorem lookup_unique {files : FileMap} (hnd : (files.map (·.1)).Nodup) {p : String}
    {raw raw' : ByteArray} (h : lookup files p = some raw) (h' : (p, raw') ∈ files) : raw' = raw := by
  have hm := lookup_mem h
  induction files with
  | nil => cases hm
  | cons x xs ih =>
    simp only [List.map_cons, List.nodup_cons, List.mem_map] at hnd
    simp only [List.mem_cons] at hm h'
    rcases hm with hm | hm <;> rcases h' with h' | h'
    · rw [← hm] at h'; cases h'; rfl
    · exact absurd ⟨_, h', by rw [← hm]⟩ hnd.1
    · exact absurd ⟨_, hm, by rw [← h']⟩ hnd.1
    · have hl : lookup xs p = some raw := by
        unfold lookup at h ⊢
        have hne : (x.1 == p) = false := by
          simp only [beq_eq_false_iff_ne]
          intro hx; exact hnd.1 ⟨_, hm, by rw [hx]⟩
        simp [hne] at h ⊢
        exact h
      exact ih hnd.2 hl h' hm

/-! ## Normalized-set soundness -/

theorem checkEntries_sound {files : FileMap} {i : IndexV2} :
    ∀ {es : List EntryV2} {ps : List (EntryV2 × WireV2)},
    checkEntries files i es = some ps →
      ps.map Prod.fst = es ∧
      ∀ p ∈ ps, ∃ raw, lookup files (keyPath p.1.storageKey) = some raw ∧
        verifyWireBytes raw = some p.2 ∧ entryBinds i p.1 p.2 = true
  | [], ps, h => by simp [checkEntries] at h; subst h; simp
  | e :: es, ps, h => by
    simp only [checkEntries] at h
    split at h
    · cases h
    · rename_i raw hraw
      split at h
      · cases h
      · rename_i w hw
        split at h
        · rename_i hb
          cases hrest : checkEntries files i es with
          | none => rw [hrest] at h; cases h
          | some ps' =>
            rw [hrest] at h
            simp only [Option.map_some, Option.some.injEq] at h
            subst h
            obtain ⟨h1, h2⟩ := checkEntries_sound hrest
            refine ⟨by simp [h1], ?_⟩
            intro p hp
            simp only [List.mem_cons] at hp
            rcases hp with rfl | hp
            · exact ⟨raw, hraw, hw, hb⟩
            · exact h2 p hp
        · cases h

/-- Everything the Lean normalized-set checker establishes. -/
structure SetAccepted (files : FileMap) (i : IndexV2) (ps : List (EntryV2 × WireV2)) : Prop where
  indexBytes : ∃ raw, lookup files indexPath = some raw ∧ verifyIndexBytes raw = some i
  entries : ps.map Prod.fst = i.entries
  wires : ∀ p ∈ ps, ∃ raw, lookup files (keyPath p.1.storageKey) = some raw ∧
    verifyWireBytes raw = some p.2
  claimBound : ∀ p ∈ ps, p.2.source.claimId = p.1.claimId ∧ p.2.claim.id = p.1.claimId
  decisionBound : ∀ p ∈ ps, p.2.decision = p.1.decision
  hashBound : ∀ p ∈ ps, p.2.wireSemanticHash = p.1.wireSemanticHash
  certificateBound : ∀ p ∈ ps,
    p.2.source.certificateSemanticHash = i.certificateSemanticHash ∧
    p.2.source.certificateIntegrityHash = i.certificateIntegrityHash
  pathDerived : ∀ e ∈ i.entries, e.storageKey = storageKey e.claimId
  claimIdsUnique : (i.entries.map (·.claimId)).Nodup
  pathsUnique : (i.entries.map (·.storageKey)).Nodup
  namesUnique : (files.map (·.1)).Nodup
  noExtraMembers : ∀ p ∈ normalizedNames files,
    p = indexPath ∨ ∃ e ∈ i.entries, p = keyPath e.storageKey

theorem verifyNormalizedSet_sound {files : FileMap} {i : IndexV2} {ps : List (EntryV2 × WireV2)}
    (h : verifyNormalizedSet files = some (i, ps)) : SetAccepted files i ps := by
  unfold verifyNormalizedSet at h
  split at h
  · cases h
  · rename_i rawIndex hri
    split at h
    · cases h
    · rename_i i' hi
      split at h
      · rename_i hm
        cases hce : checkEntries files i' i'.entries with
        | none => rw [hce] at h; cases h
        | some ps' =>
          rw [hce] at h
          simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
          obtain ⟨rfl, rfl⟩ := h
          obtain ⟨hmap, hall⟩ := checkEntries_sound hce
          have ia := verifyIndexBytes_accepted hi
          simp only [membersOK, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true,
            Bool.or_eq_true, beq_iff_eq, List.contains_iff_mem, List.mem_map] at hm
          obtain ⟨⟨hnd, hext⟩, _⟩ := hm
          have hbind : ∀ p ∈ ps', entryBinds i' p.1 p.2 = true := fun p hp => by
            obtain ⟨_, _, _, hb⟩ := hall p hp; exact hb
          have hb' : ∀ p ∈ ps', p.2.source.claimId = p.1.claimId ∧ p.2.decision = p.1.decision ∧
              p.2.wireSemanticHash = p.1.wireSemanticHash ∧
              p.2.source.certificateSemanticHash = i'.certificateSemanticHash ∧
              p.2.source.certificateIntegrityHash = i'.certificateIntegrityHash := by
            intro p hp
            have := hbind p hp
            simp only [entryBinds, Bool.and_eq_true, beq_iff_eq] at this
            exact ⟨this.1.1.1.1, this.1.1.1.2, this.1.1.2, this.1.2, this.2⟩
          refine ⟨⟨rawIndex, hri, hi⟩, hmap, ?_, ?_, ?_, ?_, ?_, ia.pathsDerived,
            ia.claimIdsUnique, ia.pathsUnique, hnd, ?_⟩
          · intro p hp
            obtain ⟨raw, h1, h2, _⟩ := hall p hp
            exact ⟨raw, h1, h2⟩
          · intro p hp
            obtain ⟨raw, _, hw, _⟩ := hall p hp
            have hsc := (verifyWireBytes_scope hw).sourceClaim
            exact ⟨(hb' p hp).1, hsc ▸ (hb' p hp).1⟩
          · exact fun p hp => (hb' p hp).2.1
          · exact fun p hp => (hb' p hp).2.2.1
          · exact fun p hp => (hb' p hp).2.2.2
          · intro p hp
            rcases hext p hp with h1 | ⟨e, he, h2⟩
            · exact Or.inl h1
            · exact Or.inr ⟨e, he, h2.symm⟩
      · cases h

/-- No missing members: every indexed claim's wire file is present in the package. -/
theorem verifyNormalizedSet_no_missing {files : FileMap} {i : IndexV2}
    {ps : List (EntryV2 × WireV2)} (h : verifyNormalizedSet files = some (i, ps)) :
    ∀ e ∈ i.entries, ∃ raw, (keyPath e.storageKey, raw) ∈ files := by
  have hs := verifyNormalizedSet_sound h
  intro e he
  rw [← hs.entries] at he
  obtain ⟨p, hp, rfl⟩ := List.mem_map.mp he
  obtain ⟨raw, hl, _⟩ := hs.wires p hp
  exact ⟨raw, lookup_mem hl⟩

/-- The index path is never confused with a claim wire path. -/
theorem indexPath_ne_keyPath (k : List UInt8) (hk : k.length = 32) : indexPath ≠ keyPath k := by
  intro h
  have := congrArg (fun s => s.toList.length) h
  simp [keyPath, length_hexChars, hk, indexPath, pathPrefix, pathSuffix] at this
  revert this; decide

/-- Distinct index entries name distinct claims and distinct files. -/
theorem verifyNormalizedSet_entries_distinct {files : FileMap} {i : IndexV2}
    {ps : List (EntryV2 × WireV2)} (h : verifyNormalizedSet files = some (i, ps)) :
    (i.entries.map (·.claimId)).Nodup ∧ (i.entries.map (keyPath ·.storageKey)).Nodup := by
  have hs := verifyNormalizedSet_sound h
  refine ⟨hs.claimIdsUnique, ?_⟩
  have := hs.pathsUnique
  rw [show (i.entries.map (keyPath ·.storageKey)) = (i.entries.map (·.storageKey)).map keyPath by
    simp [Function.comp_def]]
  exact nodup_map_of_injective (fun a b hab => keyPath_injective hab) this

/-- Every accepted claim of an accepted normalized set carries its logical assurance. -/
theorem verifyNormalizedSet_assures {files : FileMap} {i : IndexV2}
    {ps : List (EntryV2 × WireV2)} (h : verifyNormalizedSet files = some (i, ps))
    {p : EntryV2 × WireV2} (hp : p ∈ ps) {L : AssuranceLevel} (hL : levelOf p.1.decision = some L) :
    Assures (gamma p.2) L (kernelClaim p.2) (kernelEvidence p.2) := by
  have hs := verifyNormalizedSet_sound h
  obtain ⟨raw, _, hw⟩ := hs.wires p hp
  rw [← hs.decisionBound p hp] at hL
  exact verifyWireBytes_assures hw hL

end PCS.V2.Index
