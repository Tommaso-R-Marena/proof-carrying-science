import PCS.V2.Replay
import PCS.V2.Binding

/-!
# The composite v0.6 checker `acceptPCS` and its structural soundness

`acceptPCS` is the Lean transcription of `pcs/verifier_v06.py::verify_end_to_end_v06`
(stages 1–7), with every external component passed in explicitly as an oracle
(`Oracles`).  `acceptArchive` prefixes it with the ZIP layer
(`verifier_zip_v06.py::load_package_zip_v06`): the ZIP *decoder* is an oracle, the
member-name and control-file partition logic is Lean code.

`acceptPCS_sound` (no assumptions at all) unpacks acceptance into
`StructuralAssurance`.
-/

namespace PCS.V2.EndToEnd

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical
open PCS.V2.Common PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Package PCS.V2.CertificateModel
open PCS.V2.Signature PCS.V2.Replay

/-- Every component the Lean checker does not implement itself. -/
structure Oracles where
  /-- NFC + case folding tables (portability meaning only) -/
  unicode : UnicodeOps
  /-- Ed25519 verification primitive -/
  ed25519 : Ed25519Verify
  /-- static environment capture (`capture_environment_v06`) -/
  capture : CaptureFn
  /-- static workflow-dependency replay (`verify_static_workflow_replay_v06`) -/
  workflow : JVal → FileMap → Bool
  /-- evidence replay executor (`_replay_one`) -/
  exec : Executor

/-- The verifier's trust anchor: the public key and optional pinned fingerprint. -/
structure TrustAnchor where
  pk : List UInt8
  expected : Option (List UInt8)

structure AcceptedResult where
  pkg : PackageResult
  model : CertModel
  table : List (String × ByteArray)
  env : Option (EnvBinding × List InventoryItem)
  index : IndexV2
  claims : List (EntryV2 × WireV2)

/-- Stage 7 (`verify_normalized_set_after_replay_v06`) consistency with the certificate. -/
def normalizedOK (c : CertV2) (m : CertModel) (i : IndexV2) (ps : List (EntryV2 × WireV2)) : Bool :=
  i.certificateSemanticHash == c.semanticHash && i.certificateIntegrityHash == c.integrityHash &&
  decide (i.entries.map (·.claimId) = claimIds m) &&
  ps.all (fun p =>
    match m.claims.find? (·.id == p.1.claimId) with
    | some cl => decide (deriveWire c m cl = some p.2)
    | none => false)

/-- The complete Lean v0.6 checker over the exact delivered byte strings. -/
def acceptPCS (O : Oracles) (T : TrustAnchor) (inp : PackageInput) : Option AcceptedResult :=
  match verifyPackage O.unicode O.ed25519 T.pk T.expected inp with
  | none => none
  | some pr =>
    match decodeCertModel pr.cert with
    | none => none
    | some m =>
      match envStage O.capture pr.cert m inp.files with
      | none => none
      | some env =>
        if O.workflow (.obj pr.cert.members) inp.files then
          match artifactTable m inp.files with
          | none => none
          | some table =>
            if replayOK O.exec pr.cert m table then
              match verifyNormalizedSet inp.files with
              | none => none
              | some (i, ps) =>
                if normalizedOK pr.cert m i ps then
                  some { pkg := pr, model := m, table, env, index := i, claims := ps }
                else none
            else none
        else none

/-! ## ZIP layer -/

def requiredControl : List String :=
  ["certificate.json", "certificate_signature.json", "package_manifest.json",
   "package_signature.json"]

/-- `load_package_zip_v06` after decompression: partition decoded members into the
    three control records and the signed package file map. -/
def fromArchiveEntries (entries : List (String × ByteArray)) : Option PackageInput :=
  if (entries.map (·.1)).Nodup ∧ requiredControl.all (fun n => (entries.map (·.1)).contains n) then
    match lookup entries "certificate_signature.json", lookup entries "package_manifest.json",
          lookup entries "package_signature.json", lookup entries "certificate.json" with
    | some cs, some pm, some psig, some cert =>
      some { certificateBytes := cert, certificateSignatureBytes := cs, manifestBytes := pm,
             packageSignatureBytes := psig,
             files := entries.filter (fun e => !(controlNames.contains e.1)) }
    | _, _, _, _ => none
  else none

/-- ZIP decoder (`zipfile`): archive bytes ↦ (member name, decompressed bytes). -/
abbrev ZipDecoder := ByteArray → Option (List (String × ByteArray))

/-- The full checker from the raw archive bytes received by the verifier. -/
def acceptArchive (O : Oracles) (zip : ZipDecoder) (T : TrustAnchor) (raw : ByteArray) :
    Option (PackageInput × AcceptedResult) :=
  match zip raw with
  | none => none
  | some entries =>
    match fromArchiveEntries entries with
    | none => none
    | some inp => (acceptPCS O T inp).map (inp, ·)

/-! ## Structural soundness (unconditional) -/

/-- Everything acceptance establishes without any external assumption. -/
structure StructuralAssurance (O : Oracles) (T : TrustAnchor) (inp : PackageInput)
    (r : AcceptedResult) : Prop where
  package : PackageAccepted O.unicode O.ed25519 T.pk T.expected inp r.pkg
  model : decodeCertModel r.pkg.cert = some r.model
  env : envStage O.capture r.pkg.cert r.model inp.files = some r.env
  workflow : O.workflow (.obj r.pkg.cert.members) inp.files = true
  table : artifactTable r.model inp.files = some r.table
  replay : replayOK O.exec r.pkg.cert r.model r.table = true
  normalizedSet : verifyNormalizedSet inp.files = some (r.index, r.claims)
  normalized : normalizedOK r.pkg.cert r.model r.index r.claims = true

theorem acceptPCS_sound {O : Oracles} {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCS O T inp = some r) : StructuralAssurance O T inp r := by
  unfold acceptPCS at h
  split at h
  · cases h
  · rename_i pr hpr
    split at h
    · cases h
    · rename_i m hm
      split at h
      · cases h
      · rename_i env henv
        split at h
        · rename_i hw
          split at h
          · cases h
          · rename_i table ht
            split at h
            · rename_i hr
              split at h
              · cases h
              · rename_i i ps hn
                split at h
                · rename_i hok
                  cases h
                  exact ⟨verifyPackage_sound hpr, hm, henv, hw, ht, hr, hn, hok⟩
                · cases h
            · cases h
        · cases h

/-! ## Unpacking lemmas -/

theorem normalizedOK_spec {c : CertV2} {m : CertModel} {i : IndexV2} {ps : List (EntryV2 × WireV2)}
    (h : normalizedOK c m i ps = true) :
    i.certificateSemanticHash = c.semanticHash ∧ i.certificateIntegrityHash = c.integrityHash ∧
    i.entries.map (·.claimId) = claimIds m ∧
    ∀ p ∈ ps, ∃ cl ∈ m.claims, cl.id = p.1.claimId ∧ deriveWire c m cl = some p.2 := by
  simp only [normalizedOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq, List.all_eq_true] at h
  obtain ⟨⟨⟨h1, h2⟩, h3⟩, h4⟩ := h
  refine ⟨h1, h2, h3, fun p hp => ?_⟩
  have := h4 p hp
  split at this
  · rename_i cl hcl
    obtain ⟨hmem, hid⟩ := find?_mem_id hcl
    exact ⟨cl, hmem, hid, by simpa using this⟩
  · cases this

theorem replayOK_spec {exec : Executor} {c : CertV2} {m : CertModel}
    {table : List (String × ByteArray)} (h : replayOK exec c m table = true) :
    ∀ e ∈ m.evidence, exec (requestFor c m table e) = ⟨e.kind, e.outcome⟩ := by
  simp only [replayOK, List.all_eq_true, decide_eq_true_eq] at h
  exact h

theorem artifactTable_spec {m : CertModel} {files : FileMap} {table : List (String × ByteArray)}
    (h : artifactTable m files = some table) :
    ∀ x ∈ table, ∃ a ∈ m.artifacts, a.id = x.1 ∧ lookup files a.path = some x.2 ∧
      sha256 x.2.data.toList = a.sha256 := by
  intro x hx
  obtain ⟨a, ha, hax⟩ := mapOpt_mem h x hx
  unfold artifactEntry at hax
  split at hax
  · rename_i b hb
    split at hax
    · rename_i hc
      cases hax
      exact ⟨a, ha, rfl, hb, hc.1⟩
    · cases hax
  · cases hax

theorem artifactTable_ids {m : CertModel} {files : FileMap} {table : List (String × ByteArray)}
    (h : artifactTable m files = some table) : table.map (·.1) = m.artifacts.map (·.id) := by
  refine mapOpt_map_eq (fun a y hy => ?_) h
  unfold artifactEntry at hy
  split at hy
  · split at hy
    · cases hy; rfl
    · cases hy
  · cases hy

end PCS.V2.EndToEnd
