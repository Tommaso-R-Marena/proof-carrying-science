import PCS.V2.HighAssurance
import PCS.V2.Zip

/-!
# Raw canonical-archive authority: no `ZipDecoderFaithful` hypothesis

`PCS.V2.Archive.pcs_raw_archive_assurance` needs the abstract ZIP contract
`ZipDecoderFaithful zip ZipSemantics`.  For the canonical PCS `STORED` archive the
compiled authority now decodes the **raw archive bytes itself** with the Lean decoder
`PCS.V2.Zip.decodeZip` (`pcs-lean-authority --zip …`), so Python materialisation is no
longer an authoritative byte-boundary component, and the ZIP contract is the theorem
`PCS.V2.Zip.leanZip_faithful`.

* `pcs_canonical_archive_builtin_sound` — **no hypothesis**: authoritative acceptance of
  raw bytes implies that they are exactly the canonical encoding of a uniquely named member
  list, the Lean archive partition of that list, and `VerifiedBuiltinAssurance`.
* `pcs_canonical_archive_acceptance_sound` — the same plus `HighAssurance`, under only
  `AuthorityContracts` (Ed25519 unforgeability for the trust anchor and the residual
  environment-capture meaning).
* `pcs_authority_archive_binary_sound` — from the compiled authority's `ACCEPT` in
  `--zip` mode.
-/

namespace PCS.V2.CanonicalArchive

open PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Archive PCS.V2.Authority PCS.V2.HighAssurance
open PCS.V2.Zip PCS.V2.TCB PCS.V2.Package PCS.V2.Domains PCS

/-- The authoritative raw-archive checker (canonical PCS ZIP subset). -/
def acceptArchiveWithTranscript (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    Option (PackageInput × AcceptedResult) :=
  match decodeZip raw with
  | none => none
  | some es =>
    match fromArchiveEntries es with
    | none => none
    | some inp => (acceptPCSWithTranscript t T inp).map (inp, ·)

/-- The verdict printed by `pcs-lean-authority --zip`. -/
def diagnoseArchiveWithTranscript (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    String :=
  match decodeZip raw with
  | none => "canonical_archive"
  | some es =>
    match fromArchiveEntries es with
    | none => "archive_partition"
    | some inp => diagnosePCSWithTranscript t T inp

theorem acceptArchiveWithTranscript_spec {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) :
    ∃ es, decodeZip raw = some es ∧ ArchivePartition es inp ∧
      acceptPCSWithTranscript t T inp = some r := by
  unfold acceptArchiveWithTranscript at h
  split at h
  · cases h
  · rename_i es hes
    split at h
    · cases h
    · rename_i inp' hinp
      cases hr : acceptPCSWithTranscript t T inp' with
      | none => rw [hr] at h; cases h
      | some r' =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        exact ⟨es, hes, fromArchiveEntries_sound hinp, hr⟩

theorem diagnoseArchive_accept {t : AuthorityTranscript} {T : TrustAnchor} {raw : ByteArray}
    (h : diagnoseArchiveWithTranscript t T raw = "ACCEPT") :
    ∃ inp r, acceptArchiveWithTranscript t T raw = some (inp, r) := by
  unfold diagnoseArchiveWithTranscript at h
  split at h
  · exact absurd h (by decide)
  · rename_i es hes
    split at h
    · exact absurd h (by decide)
    · rename_i inp hinp
      obtain ⟨r, hr⟩ := diagnose_accept_implies_accept h
      exact ⟨inp, r, by simp [acceptArchiveWithTranscript, hes, hinp, hr]⟩

/-- **Canonical raw-archive soundness with no hypothesis at all.** -/
theorem pcs_canonical_archive_builtin_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) :
    ∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧ VerifiedBuiltinAssurance t T inp r := by
  obtain ⟨es, hes, hp, ha⟩ := acceptArchiveWithTranscript_spec h
  exact ⟨es, decodeZip_sound hes, hp, pcs_verified_builtin_acceptance_sound ha⟩

/-- **High-assurance canonical raw-archive soundness.**  Hypotheses: only
    `AuthorityContracts` — no `ZipDecoderFaithful`, no `ReplayFaithful` for the built-in
    kinds, no `Ed25519ImplCorrect`, no SHA-256 specification assumption. -/
theorem pcs_canonical_archive_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    (K : AuthorityContracts t T) {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) :
    ∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧ HighAssurance t T K inp r := by
  obtain ⟨es, hes, hp, ha⟩ := acceptArchiveWithTranscript_spec h
  exact ⟨es, decodeZip_sound hes, hp, pcs_high_assurance_acceptance_sound K ha⟩

/-- The authoritative raw-archive checker refines the generic `acceptArchive` with the
    Lean decoder, so every generic raw-archive theorem applies with `zip := decodeZip`. -/
theorem acceptArchiveWithTranscript_refines {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) :
    acceptArchive (transcriptOracles t) decodeZip T raw = some (inp, r) := by
  obtain ⟨es, hes, hp, ha⟩ := acceptArchiveWithTranscript_spec h
  have hinp : fromArchiveEntries es = some inp := by
    unfold acceptArchiveWithTranscript at h
    rw [hes] at h
    simp only at h
    split at h
    · cases h
    · rename_i inp' hinp'
      cases hr : acceptPCSWithTranscript t T inp' with
      | none => rw [hr] at h; cases h
      | some r' =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        rw [← h.1]; exact hinp'
  simp [acceptArchive, hes, hinp, acceptPCSWithTranscript_implies_acceptPCS ha]

/-- **The compiled authority's `ACCEPT` on raw archive bytes is sound** (`--zip` mode). -/
theorem pcs_authority_archive_binary_sound {t : AuthorityTranscript} {T : TrustAnchor}
    (K : AuthorityContracts t T) {raw : ByteArray}
    (h : diagnoseArchiveWithTranscript t T raw = "ACCEPT") :
    ∃ inp r es, acceptArchiveWithTranscript t T raw = some (inp, r) ∧ CanonicalZip raw es ∧
      ArchivePartition es inp ∧ HighAssurance t T K inp r := by
  obtain ⟨inp, r, hr⟩ := diagnoseArchive_accept h
  obtain ⟨es, hz, hp, hh⟩ := pcs_canonical_archive_acceptance_sound K hr
  exact ⟨inp, r, es, hr, hz, hp, hh⟩

/-- Zero-assumption version from the compiled authority's `ACCEPT` in `--zip` mode. -/
theorem pcs_authority_archive_binary_builtin_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : diagnoseArchiveWithTranscript t T raw = "ACCEPT") :
    ∃ inp r es, acceptArchiveWithTranscript t T raw = some (inp, r) ∧ CanonicalZip raw es ∧
      ArchivePartition es inp ∧ VerifiedBuiltinAssurance t T inp r := by
  obtain ⟨inp, r, hr⟩ := diagnoseArchive_accept h
  obtain ⟨es, hz, hp, hv⟩ := pcs_canonical_archive_builtin_sound hr
  exact ⟨inp, r, es, hr, hz, hp, hv⟩

end PCS.V2.CanonicalArchive
