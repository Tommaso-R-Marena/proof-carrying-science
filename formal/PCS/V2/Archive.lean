import PCS.V2.TCB

/-!
# Archive layer: from decoded ZIP members to the signed package

`acceptArchive` (in `PCS.V2.EndToEnd`) consists of an external ZIP *decoder*
(`ZipDecoder`, an oracle) followed by the Lean partition `fromArchiveEntries`.  This
file proves what the Lean part establishes about the decoded member list, so that the
external archive boundary shrinks to exactly "the decoder returns the archive's
(name, bytes) members" (`PCS.V2.TCB.ZipDecoderFaithful`).

Main results (all unconditional):

* `fromArchiveEntries_sound` — the partition is exact: unique member names, the four
  control records are the archive's members of those names, and the signed file map
  is the archive minus the three self-referential control records;
* `archive_no_duplicate_members` — an accepted archive never contains two members with
  the same name (no ZIP "shadow entry" ambiguity);
* `archive_members_signed` — every non-control archive member is a manifest-signed
  member with the signed size and SHA-256 digest;
* `archive_manifest_members_present` — every signed member occurs in the archive;
* `archive_certificate_member` — the certificate used for verification is the
  archive's `certificate.json` member, which is itself a signed member;
* `pcs_archive_scientific_assurance_exact` — the flagship plus all of the above;
* `pcs_raw_archive_assurance` — the same, stated about the archive's semantic member
  list under the narrow ZIP contract `ZipDecoderFaithful`;
* `production_raw_archive_assurance` — the same for the production verifier, under the
  explicit correspondence hypothesis `ProductionRefinesLean`.
-/

namespace PCS.V2.Archive

open PCS.V2.Json PCS.V2.SHA256 PCS.V2.Index PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Flagship
open PCS.V2.TCB

theorem lookup_filter_of_keep {files : FileMap} {p : (String × ByteArray) → Bool} {n : String}
    (hkeep : ∀ b, p (n, b) = true) : lookup (files.filter p) n = lookup files n := by
  induction files with
  | nil => rfl
  | cons x xs ih =>
    obtain ⟨m, b⟩ := x
    by_cases hm : m = n
    · subst hm
      simp [lookup, hkeep b]
    · have hmn : (m == n) = false := by simpa using hm
      by_cases hp : p (m, b) = true
      · simp only [lookup, List.filter_cons, hp, if_true, List.find?_cons, hmn] at ih ⊢
        exact ih
      · simp only [lookup, List.filter_cons, hp, List.find?_cons, hmn] at ih ⊢
        simpa using ih

/-- Exact content of the Lean archive partition. -/
structure ArchivePartition (entries : List (String × ByteArray)) (inp : PackageInput) : Prop where
  nodup : (entries.map (·.1)).Nodup
  certificate : lookup entries "certificate.json" = some inp.certificateBytes
  certificateSignature : lookup entries "certificate_signature.json" =
    some inp.certificateSignatureBytes
  manifest : lookup entries "package_manifest.json" = some inp.manifestBytes
  packageSignature : lookup entries "package_signature.json" = some inp.packageSignatureBytes
  files : inp.files = entries.filter (fun e => !(controlNames.contains e.1))

theorem fromArchiveEntries_sound {entries : List (String × ByteArray)} {inp : PackageInput}
    (h : fromArchiveEntries entries = some inp) : ArchivePartition entries inp := by
  unfold fromArchiveEntries at h
  split at h
  · rename_i hc
    split at h
    · rename_i cs pm psig cert h1 h2 h3 h4
      cases h
      exact ⟨hc.1, h4, h1, h2, h3, rfl⟩
    · cases h
  · cases h

/-- The certificate bytes the checker verifies are the archive's `certificate.json`
    member, and that member is also part of the signed file map. -/
theorem certificate_in_files {entries : List (String × ByteArray)} {inp : PackageInput}
    (h : ArchivePartition entries inp) : lookup inp.files "certificate.json" = some inp.certificateBytes := by
  rw [h.files, lookup_filter_of_keep (fun _ => by simp [controlNames])]
  exact h.certificate

theorem mem_files_iff {entries : List (String × ByteArray)} {inp : PackageInput}
    (h : ArchivePartition entries inp) (n : String) (b : ByteArray) :
    (n, b) ∈ inp.files ↔ (n, b) ∈ entries ∧ n ∉ controlNames := by
  rw [h.files, List.mem_filter]
  simp

/-- Accepted archive ⇒ the decoder's output and the Lean partition. -/
theorem acceptArchive_entries {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor} {raw : ByteArray}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, zip raw = some entries ∧ ArchivePartition entries inp ∧ acceptPCS O T inp = some r := by
  unfold acceptArchive at h
  split at h
  · cases h
  · rename_i entries he
    split at h
    · cases h
    · rename_i inp' hinp
      cases hr : acceptPCS O T inp' with
      | none => rw [hr] at h; cases h
      | some r' =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        exact ⟨entries, he, fromArchiveEntries_sound hinp, hr⟩

theorem archive_no_duplicate_members {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, zip raw = some entries ∧ (entries.map (·.1)).Nodup := by
  obtain ⟨entries, he, hp, _⟩ := acceptArchive_entries h
  exact ⟨entries, he, hp.nodup⟩

/-- Every non-control archive member is signed by the manifest, with exact size and
    SHA-256 digest: an accepted archive carries no unsigned or substituted payload. -/
theorem archive_members_signed {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, zip raw = some entries ∧
      ∀ n b, (n, b) ∈ entries → n ∉ controlNames →
        ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧ b.size = fm.size ∧ sha256 b.data.toList = fm.sha256 := by
  obtain ⟨entries, he, hp, hr⟩ := acceptArchive_entries h
  refine ⟨entries, he, fun n b hb hn => ?_⟩
  have hs := acceptPCS_sound hr
  exact fileMap_member_digest hs.package.fileMapOK ((mem_files_iff hp n b).2 ⟨hb, hn⟩)

/-- Every manifest-signed member is present in the archive (no missing member). -/
theorem archive_manifest_members_present {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, zip raw = some entries ∧
      ∀ n ∈ manifestNames r.pkg.manifest, ∃ b, (n, b) ∈ entries ∧ n ∉ controlNames := by
  obtain ⟨entries, he, hp, hr⟩ := acceptArchive_entries h
  refine ⟨entries, he, fun n hn => ?_⟩
  have hs := acceptPCS_sound hr
  have hf := (fileMap_exact_names hs.package.fileMapOK n).2 hn
  simp only [fileNames, List.mem_map] at hf
  obtain ⟨⟨n', b⟩, hmem, rfl⟩ := hf
  exact ⟨b, ((mem_files_iff hp n' b).1 hmem)⟩

/-- The verified certificate is the archive's `certificate.json` member; that member is
    signed by the manifest with exactly the certificate's size and digest. -/
theorem archive_certificate_member {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, zip raw = some entries ∧ lookup entries "certificate.json" = some inp.certificateBytes ∧
      ∃ fm, ("certificate.json", fm) ∈ r.pkg.manifest.files ∧ inp.certificateBytes.size = fm.size ∧
        sha256 inp.certificateBytes.data.toList = fm.sha256 := by
  obtain ⟨entries, he, hp, hr⟩ := acceptArchive_entries h
  have hs := acceptPCS_sound hr
  exact ⟨entries, he, hp.certificate,
    fileMap_member_digest hs.package.fileMapOK (lookup_mem (certificate_in_files hp))⟩

/-- Archive-level flagship: the decoded member list is partitioned exactly, every
    non-control member is signed with its exact digest, every signed member is present,
    and the full `ScientificAssurance` holds. -/
theorem pcs_archive_scientific_assurance_exact {O : Oracles} {zip : ZipDecoder}
    {T : TrustAnchor} (K : ExternalContracts O T) {raw : ByteArray} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, zip raw = some entries ∧ ArchivePartition entries inp ∧
      (∀ n b, (n, b) ∈ entries → n ∉ controlNames →
        ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧ b.size = fm.size ∧
          sha256 b.data.toList = fm.sha256) ∧
      (∀ n ∈ manifestNames r.pkg.manifest, ∃ b, (n, b) ∈ entries ∧ n ∉ controlNames) ∧
      ScientificAssurance O T K inp r := by
  obtain ⟨entries, he, hp, hr⟩ := acceptArchive_entries h
  have hs := acceptPCS_sound hr
  refine ⟨entries, he, hp, fun n b hb hn => ?_, fun n hn => ?_,
    pcs_accept_implies_scientific_assurance K hr⟩
  · exact fileMap_member_digest hs.package.fileMapOK ((mem_files_iff hp n b).2 ⟨hb, hn⟩)
  · have hf := (fileMap_exact_names hs.package.fileMapOK n).2 hn
    simp only [fileNames, List.mem_map] at hf
    obtain ⟨⟨n', b⟩, hmem, rfl⟩ := hf
    exact ⟨b, ((mem_files_iff hp n' b).1 hmem)⟩

/-! ## Composing with the narrow ZIP contract and the production correspondence -/

/-- With the ZIP decoder contract `ZipDecoderFaithful` (the decoder returns the members
    the archive format assigns to `raw`), acceptance of the raw archive bytes yields the
    exact archive-level assurance about the archive's *semantic* member list. -/
theorem pcs_raw_archive_assurance {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor}
    {ZipSemantics : ByteArray → List (String × ByteArray) → Prop}
    (hZ : ZipDecoderFaithful zip ZipSemantics) (K : ExternalContracts O T) {raw : ByteArray}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptArchive O zip T raw = some (inp, r)) :
    ∃ entries, ZipSemantics raw entries ∧ ArchivePartition entries inp ∧
      (∀ n b, (n, b) ∈ entries → n ∉ controlNames →
        ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧ b.size = fm.size ∧
          sha256 b.data.toList = fm.sha256) ∧
      (∀ n ∈ manifestNames r.pkg.manifest, ∃ b, (n, b) ∈ entries ∧ n ∉ controlNames) ∧
      ScientificAssurance O T K inp r := by
  obtain ⟨entries, he, hp, hs, hm, hsa⟩ := pcs_archive_scientific_assurance_exact K h
  exact ⟨entries, hZ raw entries he, hp, hs, hm, hsa⟩

/-- Production acceptance of raw archive bytes, under the explicit production ↔ Lean
    correspondence hypothesis and the ZIP contract, yields the same exact assurance. -/
theorem production_raw_archive_assurance {production : ByteArray → Bool} {O : Oracles}
    {zip : ZipDecoder} {T : TrustAnchor}
    {ZipSemantics : ByteArray → List (String × ByteArray) → Prop}
    (hP : ProductionRefinesLean production O zip T) (hZ : ZipDecoderFaithful zip ZipSemantics)
    (K : ExternalContracts O T) {raw : ByteArray} (h : production raw = true) :
    ∃ inp r entries, acceptArchive O zip T raw = some (inp, r) ∧ ZipSemantics raw entries ∧
      ArchivePartition entries inp ∧
      (∀ n b, (n, b) ∈ entries → n ∉ controlNames →
        ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧ b.size = fm.size ∧
          sha256 b.data.toList = fm.sha256) ∧
      ScientificAssurance O T K inp r := by
  have hs := hP raw h
  cases hr : acceptArchive O zip T raw with
  | none => rw [hr] at hs; cases hs
  | some ir =>
    obtain ⟨inp, r⟩ := ir
    obtain ⟨entries, he, hp, hsg, _, hsa⟩ := pcs_raw_archive_assurance hZ K hr
    exact ⟨inp, r, entries, rfl, he, hp, hsg, hsa⟩

end PCS.V2.Archive
