import PCS.V2.Binding

/-!
# PCS v0.6 normalized decision index `pcs-normalized-decision-index-v2` and the
# normalized set (P3)

Typed model of `schemas/normalized_decision_index_v06.schema.json`, the Lean
checker `verifyIndexBytes` (mirroring `parse_normalized_index_bytes_v06`) and the
Lean set checker `verifyNormalizedSet` (the replay-independent part of
`verify_normalized_set_after_replay_v06`): index ↔ wire ↔ file binding,
duplicate/extra/missing member rejection and path/claim non-confusion.
-/

namespace PCS.V2.Index

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common
open PCS.V2.NormalizedWire

def indexFormat : String := "pcs-normalized-decision-index-v2"
def indexPath : String := "normalized/index.json"
def maxIndexBytes : Nat := 10 * 1024 * 1024

structure EntryV2 where
  claimId : String
  decision : DecisionStatus
  /-- the 32-byte storage key in `normalized/<hex>.json` -/
  storageKey : List UInt8
  wireSemanticHash : List UInt8
  deriving DecidableEq, Repr

structure IndexV2 where
  certificateIntegrityHash : List UInt8
  certificateSemanticHash : List UInt8
  entries : List EntryV2
  indexSemanticHash : List UInt8
  deriving DecidableEq, Repr

def pathPrefix : String := "normalized/"
def pathSuffix : String := ".json"

/-- `normalized/<64 hex>.json` -/
def keyPath (k : List UInt8) : String :=
  String.ofList (pathPrefix.toList ++ hexChars k ++ pathSuffix.toList)

/-- `normalized_storage_key_v06(claim_id) = sha256(claim_id.encode("utf-8"))` -/
def storageKey (claimId : String) : List UInt8 := PCS.V2.SHA256.sha256 claimId.toUTF8.data.toList

def encodeEntry (e : EntryV2) : JVal :=
  .obj [("claim_id", .str e.claimId), ("decision", .str (decisionName e.decision)),
        ("path", .str (keyPath e.storageKey)),
        ("wire_semantic_hash", .str (hexEncode e.wireSemanticHash))]

def coreMembers (i : IndexV2) : List (String × JVal) :=
  [("canonical_json_profile", .str jcsProfile),
   ("certificate_integrity_hash", .str (hexEncode i.certificateIntegrityHash)),
   ("certificate_semantic_hash", .str (hexEncode i.certificateSemanticHash)),
   ("entries", .arr (i.entries.map encodeEntry)),
   ("index_format", .str indexFormat),
   ("index_hash_format", .str normalizedIndexDomain)]

def projection (i : IndexV2) : JVal := .obj (coreMembers i)

def encodeIndex (i : IndexV2) : JVal :=
  .obj (coreMembers i ++ [("index_semantic_hash", .str (hexEncode i.indexSemanticHash))])

def expectedHash (i : IndexV2) : List UInt8 := domainDigest normalizedIndexDomain (projection i)

/-! ## Decoding -/

def decodePath (s : String) : Option (List UInt8) :=
  let cs := s.toList
  let n := pathPrefix.length
  let m := pathSuffix.length
  if cs.take n = pathPrefix.toList ∧ cs.drop (cs.length - m) = pathSuffix.toList ∧
     n + m ≤ cs.length then
    decodeChars ((cs.drop n).take (cs.length - n - m))
  else none

def decodeEntry : JVal → Option EntryV2
  | .obj [(k₁, .str cid), (k₂, .str dec), (k₃, .str p), (k₄, .str wsh)] =>
    if k₁ = "claim_id" ∧ k₂ = "decision" ∧ k₃ = "path" ∧ k₄ = "wire_semantic_hash" then
      match decodeEnum allDecisions decisionName dec, decodePath p, hexDecode wsh with
      | some d, some key, some h => some { claimId := cid, decision := d, storageKey := key,
                                           wireSemanticHash := h }
      | _, _, _ => none
    else none
  | _ => none

def decodeStructure : JVal → Option IndexV2
  | .obj [(k₁, .str prof), (k₂, .str ih), (k₃, .str sh), (k₄, .arr es), (k₅, .str ifmt),
          (k₆, .str ihf), (k₇, .str ish)] =>
    if k₁ = "canonical_json_profile" ∧ k₂ = "certificate_integrity_hash" ∧
       k₃ = "certificate_semantic_hash" ∧ k₄ = "entries" ∧ k₅ = "index_format" ∧
       k₆ = "index_hash_format" ∧ k₇ = "index_semantic_hash" ∧ prof = jcsProfile ∧
       ifmt = indexFormat ∧ ihf = normalizedIndexDomain then
      match hexDecode ih, hexDecode sh, mapOpt decodeEntry es, hexDecode ish with
      | some ih', some sh', some es', some ish' =>
        some { certificateIntegrityHash := ih', certificateSemanticHash := sh',
               entries := es', indexSemanticHash := ish' }
      | _, _, _, _ => none
    else none
  | _ => none

def entryOK (e : EntryV2) : Bool :=
  isSafeId e.claimId && e.storageKey.length == 32 && e.wireSemanticHash.length == 32

def schemaOK (i : IndexV2) : Bool :=
  i.certificateIntegrityHash.length == 32 && i.certificateSemanticHash.length == 32 &&
  decide (i.entries.length ≤ maxItems) && i.entries.all entryOK && i.indexSemanticHash.length == 32

def decodeIndex (v : JVal) : Option IndexV2 :=
  match decodeStructure v with
  | some i => if schemaOK i then some i else none
  | none => none

/-! ## Semantic checks (`validate_normalized_index_v06`) -/

def semanticOK (i : IndexV2) : Bool :=
  i.indexSemanticHash == expectedHash i &&
  decide (i.entries.map (·.claimId)).Nodup &&
  decide (i.entries.map (·.storageKey)).Nodup &&
  i.entries.all (fun e => e.storageKey == storageKey e.claimId)

def verifyIndexBytes (raw : ByteArray) : Option IndexV2 :=
  match parseCanonicalBytes maxIndexBytes raw with
  | none => none
  | some v =>
    match decodeIndex v with
    | none => none
    | some i => if semanticOK i then some i else none

/-! ## The normalized set over a package file map -/

/-- A package file map (production: `Mapping[str, bytes]`). -/
abbrev FileMap := List (String × ByteArray)

def lookup (files : FileMap) (p : String) : Option ByteArray := (files.find? (·.1 == p)).map (·.2)

def isNormalizedMember (p : String) : Bool := p.toList.take pathPrefix.length == pathPrefix.toList

def normalizedNames (files : FileMap) : List String :=
  (files.map (·.1)).filter isNormalizedMember

/-- Per-entry binding check between index entry, delivered bytes and the wire. -/
def entryBinds (i : IndexV2) (e : EntryV2) (w : WireV2) : Bool :=
  w.source.claimId == e.claimId && w.decision == e.decision &&
  w.wireSemanticHash == e.wireSemanticHash &&
  w.source.certificateSemanticHash == i.certificateSemanticHash &&
  w.source.certificateIntegrityHash == i.certificateIntegrityHash

def checkEntries (files : FileMap) (i : IndexV2) : List EntryV2 → Option (List (EntryV2 × WireV2))
  | [] => some []
  | e :: es =>
    match lookup files (keyPath e.storageKey) with
    | none => none
    | some raw =>
      match verifyWireBytes raw with
      | none => none
      | some w =>
        if entryBinds i e w then (checkEntries files i es).map ((e, w) :: ·) else none

/-- Exact normalized member set: the index plus one file per entry, nothing else,
    and no duplicate names in the file map. -/
def membersOK (files : FileMap) (i : IndexV2) : Bool :=
  decide (files.map (·.1)).Nodup &&
  (normalizedNames files).all (fun p => p == indexPath || (i.entries.map (keyPath ·.storageKey)).contains p) &&
  decide ((normalizedNames files).length = i.entries.length + 1)

/-- The Lean normalized-set checker. -/
def verifyNormalizedSet (files : FileMap) : Option (IndexV2 × List (EntryV2 × WireV2)) :=
  match lookup files indexPath with
  | none => none
  | some rawIndex =>
    match verifyIndexBytes rawIndex with
    | none => none
    | some i =>
      if membersOK files i then (checkEntries files i i.entries).map (i, ·) else none

end PCS.V2.Index
