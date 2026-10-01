import PCS.V2.Signature
import PCS.V2.Index

/-!
# v0.6 package: namespace, certificate hashes, manifest and exact file-map binding

Lean checkers for

* `validate_package_namespace_v06`           → `namespaceOK`
* `verify_certificate_hashes_v06` (hash part) → `verifyCertBytes`
* `parse_package_manifest_bytes_v06`          → `verifyManifestBytes`
* `verify_package_file_map_v06`               → `fileMapOK`, `verifyPackage`

Unicode NFC normalisation and case folding are table-driven functions supplied by
the Python runtime (`unicodedata`, `str.casefold`).  They are a *parameter*
(`UnicodeOps`), so every namespace theorem holds for whatever folding function the
platform actually uses: no theorem depends on those tables being correct.
-/

namespace PCS.V2.Package

open PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common
open PCS.V2.Signature PCS.V2.Index

/-! ## Generic list lemma -/

theorem inj_of_nodup_map {α β : Type} {f : α → β} :
    ∀ {l : List α}, (l.map f).Nodup → ∀ {x y}, x ∈ l → y ∈ l → f x = f y → x = y
  | [], _, _, _, hx, _, _ => by cases hx
  | a :: l, h, x, y, hx, hy, hf => by
    simp only [List.map_cons, List.nodup_cons, List.mem_map] at h
    simp only [List.mem_cons] at hx hy
    rcases hx with rfl | hx <;> rcases hy with rfl | hy
    · rfl
    · exact absurd ⟨y, hy, hf.symm⟩ h.1
    · exact absurd ⟨x, hx, hf⟩ h.1
    · exact inj_of_nodup_map h.2 hx hy hf

theorem not_mem_of_contains_false {l : List String} {x : String} (h : l.contains x = false) :
    x ∉ l := by
  intro hm; simp [hm] at h

/-! ## Portable namespace -/

/-- Unicode table functions supplied by the runtime (trusted only for portability
    *meaning*, never for any PCS soundness theorem). -/
structure UnicodeOps where
  nfc : String → String
  casefold : String → String

def excludedNames : List String := ["package_manifest.json", "package_signature.json"]
def controlNames : List String :=
  ["certificate_signature.json", "package_manifest.json", "package_signature.json"]

def maxMemberNameBytes : Nat := 1024
def maxSegmentBytes : Nat := 255
def maxPackageFiles : Nat := 1000
def maxSingleFile : Nat := 50 * 1024 * 1024
def maxTotalBytes : Nat := 100 * 1024 * 1024

def segments (name : String) : List String := name.splitOn "/"

def forbiddenChar (c : Char) : Bool :=
  c.toNat < 32 || c.toNat == 127 || "<>:\"|?*".toList.contains c

def reservedStems : List String :=
  ["con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8",
   "com9", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"]

def rstripSpaceDot (cs : List Char) : List Char :=
  (cs.reverse.dropWhile (fun c => c == ' ' || c == '.')).reverse

/-- `segment.split(".", 1)[0].rstrip(" .").casefold()` -/
def stem (U : UnicodeOps) (seg : String) : String :=
  U.casefold (String.ofList (rstripSpaceDot (seg.toList.takeWhile (· ≠ '.'))))

def segmentOK (U : UnicodeOps) (seg : String) : Bool :=
  seg != "" && seg != "." && seg != ".." && decide (seg.utf8ByteSize ≤ maxSegmentBytes) &&
  U.nfc seg == seg && seg.toList.all (fun c => !forbiddenChar c) &&
  (match seg.toList.getLast? with
   | some c => c != ' ' && c != '.'
   | none => false) &&
  !(reservedStems.contains (stem U seg))

def nameOK (U : UnicodeOps) (name : String) : Bool :=
  name != "" && !(excludedNames.contains name) && decide (name.utf8ByteSize ≤ maxMemberNameBytes) &&
  !(name.toList.contains '\\') && (segments name).all (segmentOK U)

/-- Cross-platform comparison key: NFC + case fold per segment. -/
def portableKey (U : UnicodeOps) (name : String) : String :=
  "/".intercalate ((segments name).map (fun s => U.casefold (U.nfc s)))

/-- Proper parent directories of a member name. -/
def parentPrefixes (name : String) : List String :=
  let segs := segments name
  (List.range (segs.length - 1)).map (fun i => "/".intercalate (segs.take (i + 1)))

def namespaceOK (U : UnicodeOps) (names : List String) : Bool :=
  decide names.Nodup && names.all (nameOK U) && decide (names.map (portableKey U)).Nodup &&
  names.all (fun n => (parentPrefixes n).all (fun q => !(names.contains q)))

/-! ## Namespace theorems -/

theorem namespaceOK_nodup {U : UnicodeOps} {names : List String} (h : namespaceOK U names = true) :
    names.Nodup := by
  simp only [namespaceOK, Bool.and_eq_true, decide_eq_true_eq] at h
  exact h.1.1.1

theorem namespaceOK_name {U : UnicodeOps} {names : List String} (h : namespaceOK U names = true)
    {n : String} (hn : n ∈ names) : nameOK U n = true := by
  simp only [namespaceOK, Bool.and_eq_true, List.all_eq_true] at h
  exact h.1.1.2 n hn

/-- No path traversal / absolute paths / empty or dot segments. -/
theorem namespace_no_traversal {U : UnicodeOps} {names : List String}
    (h : namespaceOK U names = true) {n : String} (hn : n ∈ names) :
    ∀ seg ∈ segments n, seg ≠ "" ∧ seg ≠ "." ∧ seg ≠ ".." := by
  have := namespaceOK_name h hn
  simp only [nameOK, Bool.and_eq_true, List.all_eq_true] at this
  intro seg hs
  have hseg := this.2 seg hs
  simp only [segmentOK, Bool.and_eq_true] at hseg
  obtain ⟨⟨⟨⟨⟨⟨⟨h1, h2⟩, h3⟩, _⟩, _⟩, _⟩, _⟩, _⟩ := hseg
  exact ⟨by simpa using h1, by simpa using h2, by simpa using h3⟩

/-- No member is a control/self-referential record. -/
theorem namespace_not_excluded {U : UnicodeOps} {names : List String}
    (h : namespaceOK U names = true) {n : String} (hn : n ∈ names) : n ∉ excludedNames := by
  have := namespaceOK_name h hn
  simp only [nameOK, Bool.and_eq_true, Bool.not_eq_true'] at this
  exact not_mem_of_contains_false this.1.1.1.2

/-- No backslash anywhere in an accepted name. -/
theorem namespace_no_backslash {U : UnicodeOps} {names : List String}
    (h : namespaceOK U names = true) {n : String} (hn : n ∈ names) : '\\' ∉ n.toList := by
  have := namespaceOK_name h hn
  simp only [nameOK, Bool.and_eq_true] at this
  have h2 := this.1.2
  simp only [Bool.not_eq_true'] at h2
  intro hm
  have := List.contains_iff_mem.mpr hm
  rw [h2] at this; cases this

/-- No cross-platform alias: two accepted names with the same NFC+casefold key are
    the same name (for the folding functions actually used). -/
theorem namespace_no_alias {U : UnicodeOps} {names : List String}
    (h : namespaceOK U names = true) {n₁ n₂ : String} (h₁ : n₁ ∈ names) (h₂ : n₂ ∈ names)
    (hk : portableKey U n₁ = portableKey U n₂) : n₁ = n₂ := by
  simp only [namespaceOK, Bool.and_eq_true, decide_eq_true_eq] at h
  exact inj_of_nodup_map h.1.2 h₁ h₂ hk

/-- No accepted file is simultaneously a parent directory of another accepted file. -/
theorem namespace_no_parent {U : UnicodeOps} {names : List String}
    (h : namespaceOK U names = true) {n : String} (hn : n ∈ names) {q : String}
    (hq : q ∈ parentPrefixes n) : q ∉ names := by
  simp only [namespaceOK, Bool.and_eq_true, List.all_eq_true] at h
  have := h.2 n hn q hq
  simp only [Bool.not_eq_true'] at this
  exact not_mem_of_contains_false this

/-! ## Certificate hash layer (`verify_certificate_hashes_v06`) -/

def maxCertificateBytes : Nat := 10 * 1024 * 1024
def certSpecVersion : String := "pcs-0.6"
def certProfile : String := "pcs-jcs-rfc8785-v1"

def field (ms : List (String × JVal)) (k : String) : Option JVal :=
  (ms.find? (fun kv => kv.1 == k)).map (·.2)

def digestField (ms : List (String × JVal)) (k : String) : Option (List UInt8) :=
  match field ms k with
  | some (.str s) => decDigest s
  | _ => none

def strField (ms : List (String × JVal)) (k : String) : Option String :=
  match field ms k with
  | some (.str s) => some s
  | _ => none

/-- `semantic_projection_v06`: drop `generated_at`, `semantic_hash`, `integrity_hash`. -/
def semanticProjection (ms : List (String × JVal)) : JVal :=
  .obj (ms.filter (fun kv => !(["generated_at", "semantic_hash", "integrity_hash"].contains kv.1)))

/-- `integrity_projection_v06`: drop `integrity_hash`. -/
def integrityProjection (ms : List (String × JVal)) : JVal :=
  .obj (ms.filter (fun kv => kv.1 != "integrity_hash"))

structure CertV2 where
  members : List (String × JVal)
  semanticHash : List UInt8
  integrityHash : List UInt8

def certHashesOK (c : CertV2) : Bool :=
  strField c.members "spec_version" == some certSpecVersion &&
  strField c.members "canonical_json_profile" == some certProfile &&
  strField c.members "semantic_hash_format" == some certificateSemanticDomain &&
  strField c.members "integrity_hash_format" == some certificateIntegrityDomain &&
  c.semanticHash == domainDigest certificateSemanticDomain (semanticProjection c.members) &&
  c.integrityHash == domainDigest certificateIntegrityDomain (integrityProjection c.members)

/-- Lean checker for certificate bytes (canonical gate + hash recomputation). -/
def verifyCertBytes (raw : ByteArray) : Option CertV2 :=
  match parseCanonicalBytes maxCertificateBytes raw with
  | some (.obj ms) =>
    match digestField ms "semantic_hash", digestField ms "integrity_hash" with
    | some sh, some ih =>
      let c : CertV2 := { members := ms, semanticHash := sh, integrityHash := ih }
      if certHashesOK c then some c else none
    | _, _ => none
  | _ => none

/-- `certificate_signature_payload_v06`. -/
def certSigKeys : List String :=
  ["canonical_json_profile", "checker_version", "integrity_hash", "integrity_hash_format",
   "semantic_hash", "semantic_hash_format", "spec_version", "subject"]

def certSigPayload (c : CertV2) : Option JVal :=
  (mapOpt (fun k => (field c.members k).map (fun v => (k, v))) certSigKeys).map JVal.obj

/-! ## Package manifest -/

def packageFormat : String := "pcs-package-v2"
def maxManifestBytes : Nat := 10 * 1024 * 1024
def certificateMember : String := "certificate.json"

structure FileMeta where
  sha256 : List UInt8
  size : Nat

structure ManifestV2 where
  certSemanticHash : List UInt8
  certIntegrityHash : List UInt8
  files : List (String × FileMeta)

def encodeMeta (m : FileMeta) : JVal :=
  .obj [("sha256", .str (hexEncode m.sha256)), ("size", .num m.size)]

def encodeManifest (m : ManifestV2) : JVal :=
  .obj [("canonical_json_profile", .str certProfile),
        ("certificate_integrity_hash", .str (hexEncode m.certIntegrityHash)),
        ("certificate_integrity_hash_format", .str certificateIntegrityDomain),
        ("certificate_semantic_hash", .str (hexEncode m.certSemanticHash)),
        ("certificate_semantic_hash_format", .str certificateSemanticDomain),
        ("certificate_spec_version", .str certSpecVersion),
        ("files", .obj (m.files.map (fun nf => (nf.1, encodeMeta nf.2)))),
        ("package_format", .str packageFormat)]

def decodeMeta : JVal → Option FileMeta
  | .obj [(k₁, .str h), (k₂, .num n)] =>
    if k₁ = "sha256" ∧ k₂ = "size" ∧ 0 ≤ n then
      (decDigest h).map (fun d => { sha256 := d, size := n.toNat })
    else none
  | _ => none

def decodeFile (kv : String × JVal) : Option (String × FileMeta) :=
  (decodeMeta kv.2).map (fun m => (kv.1, m))

def decodeManifest : JVal → Option ManifestV2
  | .obj [(k₁, .str prof), (k₂, .str ih), (k₃, .str ihf), (k₄, .str sh), (k₅, .str shf),
          (k₆, .str sv), (k₇, .obj fs), (k₈, .str pf)] =>
    if k₁ = "canonical_json_profile" ∧ k₂ = "certificate_integrity_hash" ∧
       k₃ = "certificate_integrity_hash_format" ∧ k₄ = "certificate_semantic_hash" ∧
       k₅ = "certificate_semantic_hash_format" ∧ k₆ = "certificate_spec_version" ∧
       k₇ = "files" ∧ k₈ = "package_format" ∧ prof = certProfile ∧
       ihf = certificateIntegrityDomain ∧ shf = certificateSemanticDomain ∧
       sv = certSpecVersion ∧ pf = packageFormat then
      match decDigest ih, decDigest sh, mapOpt decodeFile fs with
      | some ih', some sh', some fs' =>
        some { certSemanticHash := sh', certIntegrityHash := ih', files := fs' }
      | _, _, _ => none
    else none
  | _ => none

def manifestNames (m : ManifestV2) : List String := m.files.map (·.1)

def manifestOK (U : UnicodeOps) (m : ManifestV2) : Bool :=
  namespaceOK U (manifestNames m) && (manifestNames m).contains certificateMember

def verifyManifestBytes (U : UnicodeOps) (raw : ByteArray) : Option ManifestV2 :=
  match parseCanonicalBytes maxManifestBytes raw with
  | none => none
  | some v =>
    match decodeManifest v with
    | some m => if manifestOK U m then some m else none
    | none => none

/-! ## Exact file-map binding (`verify_package_file_map_v06`) -/

def fileNames (files : FileMap) : List String := files.map (·.1)

def totalBytes (files : FileMap) : Nat := (files.map (fun f => f.2.size)).sum

/-- One manifest entry is matched by exactly-sized, exactly-hashed delivered bytes. -/
def memberOK (files : FileMap) (nf : String × FileMeta) : Bool :=
  match lookup files nf.1 with
  | some b => b.size == nf.2.size && sha256 b.data.toList == nf.2.sha256 &&
              decide (b.size ≤ maxSingleFile)
  | none => false

def fileMapOK (U : UnicodeOps) (m : ManifestV2) (c : CertV2) (certBytes : ByteArray)
    (files : FileMap) : Bool :=
  namespaceOK U (fileNames files) &&
  (fileNames files).all (fun n => (manifestNames m).contains n) &&
  m.files.all (memberOK files) &&
  decide (files.length ≤ maxPackageFiles) && decide (totalBytes files ≤ maxTotalBytes) &&
  decide (lookup files certificateMember = some certBytes) &&
  m.certSemanticHash == c.semanticHash && m.certIntegrityHash == c.integrityHash

/-! ## The signed package checker -/

/-- Inputs of `verify_end_to_end_v06`'s cryptographic and package stages. -/
structure PackageInput where
  certificateBytes : ByteArray
  certificateSignatureBytes : ByteArray
  manifestBytes : ByteArray
  packageSignatureBytes : ByteArray
  files : FileMap

structure PackageResult where
  cert : CertV2
  certSignature : SigRecordV2
  manifest : ManifestV2
  packageSignature : SigRecordV2

/-- Stages 1–3 of `verify_end_to_end_v06` as one Lean checker. -/
def verifyPackage (U : UnicodeOps) (V : Ed25519Verify) (pk : List UInt8)
    (expected : Option (List UInt8)) (inp : PackageInput) : Option PackageResult :=
  match verifyCertBytes inp.certificateBytes with
  | none => none
  | some c =>
    match certSigPayload c with
    | none => none
    | some csp =>
      match verifySigRecordBytes V pk expected certificateSignatureDomain csp
              inp.certificateSignatureBytes with
      | none => none
      | some cs =>
        match verifyManifestBytes U inp.manifestBytes with
        | none => none
        | some m =>
          if fileMapOK U m c inp.certificateBytes inp.files then
            match verifySigRecordBytes V pk expected packageSignatureDomain (encodeManifest m)
                    inp.packageSignatureBytes with
            | none => none
            | some ps => some { cert := c, certSignature := cs, manifest := m, packageSignature := ps }
          else none

end PCS.V2.Package
