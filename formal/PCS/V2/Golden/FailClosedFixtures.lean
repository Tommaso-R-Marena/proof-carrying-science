import PCS.V2.ExecutableFailClosed
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.Golden.Insider

/-!
# Kernel-checked adversarial fixtures for the fail-closed gates

Each fixture is a consistently built certificate (correct artifact digest, semantic and
integrity hashes, normalized wire and index, manifest over the members) that an insider
holding the signing key would sign.  For each, the theorems below hold **for every pair of
signature byte strings** (in particular the genuine signatures; the campaign file checks by
evaluation that those verify), every transcript (in particular one reporting `PASS` for every
evidence item) and every trust anchor:

* `m7`  — unregistered tag `trace_invariant_v2` over the **safe** golden trace;
* `m7b` — `check_spec` with **no `type` field**;
* `m7c` — the golden evidence plus an **unrequired** evidence item `E2` of unregistered type `external_python`, recorded `PASS`;
  these three are rejected by the check-type gate
  (`PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type`);
* `m15` — claim/evidence predicates with budget 2 but a certified `check_spec` with budget 4 (registered tag; the claim is false of the
  committed trace, whose cumulative risk is 4).  Rejected because a supported AI-safety claim
  that is false of the delivered bytes can never be accepted
  (`PCS.V2.ExecutableFailClosed.executableAuthority_rejects_false_supported_ai_claim`).

Only certificate parsing is evaluated in the kernel (two SHA-256 domain digests per fixture,
through the proved fast SHA-256); no signature is evaluated, because the statements quantify
over all signatures.  The hash literals were printed by `tools/PrintFailClosedLiterals.lean`
and are re-checked here by the kernel.
-/

set_option autoImplicit false

namespace PCS.V2.Golden.FailClosedFixtures

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Index
open PCS.V2.CertificateModel PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses PCS.V2.Domains
open PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden PCS.V2.PKPDCheck
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.SHA256 PCS.V2.Canonical PCS.V2.FailClosed
open PCS.V2.ExecutableFailClosed

/-- An evidence check type outside the registered list yields an offending evidence item. -/
theorem bad_of_types {m : CertModel} {o : Option String}
    (h : o ∈ m.evidence.map (fun e => checkTypeOf e.json))
    (ho : ∀ ty ∈ executableTypes, o ≠ some ty) :
    ∃ e ∈ m.evidence, ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty := by
  obtain ⟨e, he, rfl⟩ := List.mem_map.mp h
  exact ⟨e, he, ho⟩

/-! ## Fixture `m7`: unregistered tag `trace_invariant_v2` over the **safe** golden trace -/

def m7Sem : List UInt8 := [227, 112, 112, 62, 182, 238, 80, 86, 9, 240, 194, 236, 22, 111, 37, 48, 186, 80, 176, 84, 21, 4, 42, 88, 74, 82, 16, 192, 168, 41, 113, 165]
def m7Int : List UInt8 := [103, 42, 197, 107, 247, 193, 23, 70, 191, 252, 52, 12, 40, 76, 46, 107, 2, 70, 100, 158, 2, 171, 141, 33, 61, 198, 164, 163, 63, 194, 128, 32]

theorem m7_semHash : m7.semHash = m7Sem := by
  rw [FixtureSpec.semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem m7_intHash : m7.intHash = m7Int := by
  rw [FixtureSpec.intHash, m7_semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

def m7CertJ : JVal := .obj (m7.certMembers (hexEncode m7Sem) (hexEncode m7Int))

def m7CertV : CertV2 :=
  { members := m7.certMembers (hexEncode m7Sem) (hexEncode m7Int),
    semanticHash := m7Sem, integrityHash := m7Int }

theorem m7_certBytes_jcs : m7.certBytes = jcsBytes m7CertJ := by
  rw [FixtureSpec.certBytes, FixtureSpec.certJ, m7_semHash, m7_intHash]; rfl

theorem m7CertJ_canonical : canonical m7CertJ = true := by kernel_rfl

theorem m7CertJ_size : (jcsBytes m7CertJ).size = 1686 := by
  rw [jcsBytes_size]; kernel_rfl

theorem verifyCertBytes_m7 : verifyCertBytes m7.certBytes = some m7CertV := by
  have hs : (jcsBytes m7CertJ).size ≤ maxCertificateBytes := by
    rw [m7CertJ_size]; decide
  rw [m7_certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete m7CertJ_canonical hs]
  simp only [m7CertJ, certHashesOK, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

def m7Model : CertModel := (decodeCertModel m7CertV).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_m7 : decodeCertModel m7CertV = some m7Model := by kernel_rfl

/-- The package input materialised from the members, for arbitrary signatures. -/
def m7Input (csig psig : List UInt8) : PackageInput :=
  { certificateBytes := m7.certBytes, certificateSignatureBytes := m7.certSigBytesWith csig,
    manifestBytes := m7.manifestBytes, packageSignatureBytes := m7.pkgSigBytesWith psig,
    files := m7.files }

theorem fromArchiveEntries_m7 :
    ∀ csig psig : List UInt8,
      fromArchiveEntries (m7.entriesWith csig psig) = some (m7Input csig psig) := by
  kernel_rfl

theorem m7_types : m7Model.evidence.map (fun e => checkTypeOf e.json) = [some "trace_invariant_v2"] := by
  kernel_rfl

theorem m7_bad : ∃ e ∈ m7Model.evidence, ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty :=
  bad_of_types (o := some "trace_invariant_v2") (by rw [m7_types]; simp) (by rw [executableTypes_eq]; decide)

/-- **Directory mode, kernel-checked**: for all signatures, transcripts and trust anchors,
    `pcs-lean-authority <dir>` does not print `ACCEPT` on fixture `m7`. -/
theorem m7_rejected_entries (csig psig : List UInt8) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthorityEntries t T (m7.entriesWith csig psig) ≠ "ACCEPT" := by
  obtain ⟨e, he, hty⟩ := m7_bad
  exact executableAuthorityEntries_rejects_unregistered_type (fromArchiveEntries_m7 csig psig)
    verifyCertBytes_m7 decodeCertModel_m7 he hty t T

/-- **Zip mode, kernel-checked**: every raw byte string decoding to the members of fixture
    `m7` (with any signatures) is rejected, for every transcript and trust anchor. -/
theorem m7_rejected_zip (csig psig : List UInt8) {raw : ByteArray}
    (hz : decodeZip raw = some (m7.entriesWith csig psig)) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" := by
  obtain ⟨e, he, hty⟩ := m7_bad
  exact executableAuthority_rejects_unregistered_type hz (fromArchiveEntries_m7 csig psig)
    verifyCertBytes_m7 decodeCertModel_m7 he hty t T

/-! ## Fixture `m7b`: `check_spec` with **no `type` field** -/

def m7bSem : List UInt8 := [106, 218, 98, 143, 209, 240, 47, 225, 78, 255, 137, 100, 142, 245, 11, 249, 19, 246, 77, 70, 60, 0, 34, 172, 36, 220, 170, 51, 5, 82, 27, 229]
def m7bInt : List UInt8 := [245, 192, 155, 169, 65, 50, 85, 120, 150, 254, 110, 165, 232, 181, 227, 129, 206, 59, 255, 233, 87, 206, 47, 53, 209, 172, 219, 4, 83, 47, 206, 99]

theorem m7b_semHash : m7b.semHash = m7bSem := by
  rw [FixtureSpec.semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem m7b_intHash : m7b.intHash = m7bInt := by
  rw [FixtureSpec.intHash, m7b_semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

def m7bCertJ : JVal := .obj (m7b.certMembers (hexEncode m7bSem) (hexEncode m7bInt))

def m7bCertV : CertV2 :=
  { members := m7b.certMembers (hexEncode m7bSem) (hexEncode m7bInt),
    semanticHash := m7bSem, integrityHash := m7bInt }

theorem m7b_certBytes_jcs : m7b.certBytes = jcsBytes m7bCertJ := by
  rw [FixtureSpec.certBytes, FixtureSpec.certJ, m7b_semHash, m7b_intHash]; rfl

theorem m7bCertJ_canonical : canonical m7bCertJ = true := by kernel_rfl

theorem m7bCertJ_size : (jcsBytes m7bCertJ).size = 1658 := by
  rw [jcsBytes_size]; kernel_rfl

theorem verifyCertBytes_m7b : verifyCertBytes m7b.certBytes = some m7bCertV := by
  have hs : (jcsBytes m7bCertJ).size ≤ maxCertificateBytes := by
    rw [m7bCertJ_size]; decide
  rw [m7b_certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete m7bCertJ_canonical hs]
  simp only [m7bCertJ, certHashesOK, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

def m7bModel : CertModel := (decodeCertModel m7bCertV).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_m7b : decodeCertModel m7bCertV = some m7bModel := by kernel_rfl

/-- The package input materialised from the members, for arbitrary signatures. -/
def m7bInput (csig psig : List UInt8) : PackageInput :=
  { certificateBytes := m7b.certBytes, certificateSignatureBytes := m7b.certSigBytesWith csig,
    manifestBytes := m7b.manifestBytes, packageSignatureBytes := m7b.pkgSigBytesWith psig,
    files := m7b.files }

theorem fromArchiveEntries_m7b :
    ∀ csig psig : List UInt8,
      fromArchiveEntries (m7b.entriesWith csig psig) = some (m7bInput csig psig) := by
  kernel_rfl

theorem m7b_types : m7bModel.evidence.map (fun e => checkTypeOf e.json) = [none] := by
  kernel_rfl

theorem m7b_bad : ∃ e ∈ m7bModel.evidence, ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty :=
  bad_of_types (o := none) (by rw [m7b_types]; simp) (by rw [executableTypes_eq]; decide)

/-- **Directory mode, kernel-checked**: for all signatures, transcripts and trust anchors,
    `pcs-lean-authority <dir>` does not print `ACCEPT` on fixture `m7b`. -/
theorem m7b_rejected_entries (csig psig : List UInt8) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthorityEntries t T (m7b.entriesWith csig psig) ≠ "ACCEPT" := by
  obtain ⟨e, he, hty⟩ := m7b_bad
  exact executableAuthorityEntries_rejects_unregistered_type (fromArchiveEntries_m7b csig psig)
    verifyCertBytes_m7b decodeCertModel_m7b he hty t T

/-- **Zip mode, kernel-checked**: every raw byte string decoding to the members of fixture
    `m7b` (with any signatures) is rejected, for every transcript and trust anchor. -/
theorem m7b_rejected_zip (csig psig : List UInt8) {raw : ByteArray}
    (hz : decodeZip raw = some (m7b.entriesWith csig psig)) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" := by
  obtain ⟨e, he, hty⟩ := m7b_bad
  exact executableAuthority_rejects_unregistered_type hz (fromArchiveEntries_m7b csig psig)
    verifyCertBytes_m7b decodeCertModel_m7b he hty t T

/-! ## Fixture `m7c`: the golden evidence plus an **unrequired** evidence item `E2` of unregistered type `external_python`, recorded `PASS` -/

def m7cSem : List UInt8 := [75, 184, 114, 149, 58, 107, 228, 136, 4, 121, 171, 22, 246, 76, 229, 248, 140, 179, 249, 156, 224, 74, 70, 227, 209, 163, 50, 211, 12, 101, 163, 90]
def m7cInt : List UInt8 := [43, 115, 0, 102, 211, 202, 222, 199, 121, 92, 133, 87, 30, 142, 71, 255, 98, 12, 134, 180, 241, 177, 29, 79, 254, 81, 15, 215, 150, 110, 220, 86]

theorem m7c_semHash : m7c.semHash = m7cSem := by
  rw [FixtureSpec.semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem m7c_intHash : m7c.intHash = m7cInt := by
  rw [FixtureSpec.intHash, m7c_semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

def m7cCertJ : JVal := .obj (m7c.certMembers (hexEncode m7cSem) (hexEncode m7cInt))

def m7cCertV : CertV2 :=
  { members := m7c.certMembers (hexEncode m7cSem) (hexEncode m7cInt),
    semanticHash := m7cSem, integrityHash := m7cInt }

theorem m7c_certBytes_jcs : m7c.certBytes = jcsBytes m7cCertJ := by
  rw [FixtureSpec.certBytes, FixtureSpec.certJ, m7c_semHash, m7c_intHash]; rfl

theorem m7cCertJ_canonical : canonical m7cCertJ = true := by kernel_rfl

theorem m7cCertJ_size : (jcsBytes m7cCertJ).size = 1985 := by
  rw [jcsBytes_size]; kernel_rfl

theorem verifyCertBytes_m7c : verifyCertBytes m7c.certBytes = some m7cCertV := by
  have hs : (jcsBytes m7cCertJ).size ≤ maxCertificateBytes := by
    rw [m7cCertJ_size]; decide
  rw [m7c_certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete m7cCertJ_canonical hs]
  simp only [m7cCertJ, certHashesOK, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

def m7cModel : CertModel := (decodeCertModel m7cCertV).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_m7c : decodeCertModel m7cCertV = some m7cModel := by kernel_rfl

/-- The package input materialised from the members, for arbitrary signatures. -/
def m7cInput (csig psig : List UInt8) : PackageInput :=
  { certificateBytes := m7c.certBytes, certificateSignatureBytes := m7c.certSigBytesWith csig,
    manifestBytes := m7c.manifestBytes, packageSignatureBytes := m7c.pkgSigBytesWith psig,
    files := m7c.files }

theorem fromArchiveEntries_m7c :
    ∀ csig psig : List UInt8,
      fromArchiveEntries (m7c.entriesWith csig psig) = some (m7cInput csig psig) := by
  kernel_rfl

theorem m7c_types : m7cModel.evidence.map (fun e => checkTypeOf e.json) = [some "trace_invariant", some "external_python"] := by
  kernel_rfl

theorem m7c_bad : ∃ e ∈ m7cModel.evidence, ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty :=
  bad_of_types (o := some "external_python") (by rw [m7c_types]; simp) (by rw [executableTypes_eq]; decide)

/-- **Directory mode, kernel-checked**: for all signatures, transcripts and trust anchors,
    `pcs-lean-authority <dir>` does not print `ACCEPT` on fixture `m7c`. -/
theorem m7c_rejected_entries (csig psig : List UInt8) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthorityEntries t T (m7c.entriesWith csig psig) ≠ "ACCEPT" := by
  obtain ⟨e, he, hty⟩ := m7c_bad
  exact executableAuthorityEntries_rejects_unregistered_type (fromArchiveEntries_m7c csig psig)
    verifyCertBytes_m7c decodeCertModel_m7c he hty t T

/-- **Zip mode, kernel-checked**: every raw byte string decoding to the members of fixture
    `m7c` (with any signatures) is rejected, for every transcript and trust anchor. -/
theorem m7c_rejected_zip (csig psig : List UInt8) {raw : ByteArray}
    (hz : decodeZip raw = some (m7c.entriesWith csig psig)) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" := by
  obtain ⟨e, he, hty⟩ := m7c_bad
  exact executableAuthority_rejects_unregistered_type hz (fromArchiveEntries_m7c csig psig)
    verifyCertBytes_m7c decodeCertModel_m7c he hty t T

/-! ## Fixture `m15`: claim/evidence predicates with budget 2 but a certified `check_spec` with budget 4 -/

def m15Sem : List UInt8 := [20, 27, 223, 202, 252, 150, 132, 135, 236, 201, 116, 87, 139, 137, 121, 27, 192, 154, 194, 136, 2, 54, 163, 125, 132, 29, 85, 247, 86, 189, 55, 46]
def m15Int : List UInt8 := [253, 41, 175, 18, 157, 0, 32, 21, 247, 65, 214, 240, 229, 115, 41, 155, 233, 174, 172, 57, 16, 67, 222, 126, 148, 255, 119, 47, 160, 128, 13, 78]

theorem m15_semHash : m15.semHash = m15Sem := by
  rw [FixtureSpec.semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem m15_intHash : m15.intHash = m15Int := by
  rw [FixtureSpec.intHash, m15_semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

def m15CertJ : JVal := .obj (m15.certMembers (hexEncode m15Sem) (hexEncode m15Int))

def m15CertV : CertV2 :=
  { members := m15.certMembers (hexEncode m15Sem) (hexEncode m15Int),
    semanticHash := m15Sem, integrityHash := m15Int }

theorem m15_certBytes_jcs : m15.certBytes = jcsBytes m15CertJ := by
  rw [FixtureSpec.certBytes, FixtureSpec.certJ, m15_semHash, m15_intHash]; rfl

theorem m15CertJ_canonical : canonical m15CertJ = true := by kernel_rfl

theorem m15CertJ_size : (jcsBytes m15CertJ).size = 1683 := by
  rw [jcsBytes_size]; kernel_rfl

theorem verifyCertBytes_m15 : verifyCertBytes m15.certBytes = some m15CertV := by
  have hs : (jcsBytes m15CertJ).size ≤ maxCertificateBytes := by
    rw [m15CertJ_size]; decide
  rw [m15_certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete m15CertJ_canonical hs]
  simp only [m15CertJ, certHashesOK, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

def m15Model : CertModel := (decodeCertModel m15CertV).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_m15 : decodeCertModel m15CertV = some m15Model := by kernel_rfl

/-- The package input materialised from the members, for arbitrary signatures. -/
def m15Input (csig psig : List UInt8) : PackageInput :=
  { certificateBytes := m15.certBytes, certificateSignatureBytes := m15.certSigBytesWith csig,
    manifestBytes := m15.manifestBytes, packageSignatureBytes := m15.pkgSigBytesWith psig,
    files := m15.files }

theorem fromArchiveEntries_m15 :
    ∀ csig psig : List UInt8,
      fromArchiveEntries (m15.entriesWith csig psig) = some (m15Input csig psig) := by
  kernel_rfl

/-! ### `m15`: the false supported claim -/

/-- The decoded claim `C1` of `m15`: budget 2, recorded `COMPUTATIONALLY_SUPPORTED`. -/
def m15Claim : CertClaim := ⟨"C1", .computational, predJ 2 7, ["E1"], ["A1"], .computational⟩

theorem m15_claims : m15Model.claims = [m15Claim] := by kernel_rfl

theorem m15_artifacts_paths :
    m15Model.artifacts.map (fun a => (a.id, a.path)) = [(traceId, tracePath)] := by kernel_rfl

theorem m15_claim_decodes : aiAdapter.decode m15Claim.predicate = some ⟨["trace"], 2, 7⟩ := by
  decide

theorem lookup_m15_trace : lookup m15.files tracePath = some m15.trace := by kernel_rfl

/-- The committed trace `[0, 1, 2, 4, 1, 8]` has cumulative risk 4 > 2. -/
theorem m15_trace_unsafe : ¬ TraceSafe m15.trace.data.toList 2 7 := by
  intro h
  have := h.2 6 (by decide)
  revert this
  decide

theorem m15_hunsafe (csig psig : List UInt8) :
    ∀ art ∈ m15Model.artifacts, art.id = "trace" → ∀ bytes,
      lookup (m15Input csig psig).files art.path = some bytes →
        ¬ TraceSafe bytes.data.toList 2 7 := by
  intro art hart _ bytes hl
  have hp : (art.id, art.path) ∈ m15Model.artifacts.map (fun a => (a.id, a.path)) :=
    List.mem_map_of_mem hart
  rw [m15_artifacts_paths] at hp
  simp only [List.mem_singleton, Prod.mk.injEq] at hp
  rw [hp.2] at hl
  change lookup m15.files tracePath = some bytes at hl
  rw [lookup_m15_trace] at hl
  cases hl
  exact m15_trace_unsafe

/-- **Zip mode, kernel-checked**: the binding-mismatch archive is rejected for all
    signatures, transcripts and trust anchors. -/
theorem m15_rejected_zip (csig psig : List UInt8) {raw : ByteArray}
    (hz : decodeZip raw = some (m15.entriesWith csig psig)) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" :=
  executableAuthority_rejects_false_supported_ai_claim hz (fromArchiveEntries_m15 csig psig)
    verifyCertBytes_m15 decodeCertModel_m15 (cl := m15Claim) (by rw [m15_claims]; simp) rfl
    m15_claim_decodes (a := "trace") (by simp) (m15_hunsafe csig psig) t T


/-- **Directory mode, kernel-checked.** -/
theorem m15_rejected_entries (csig psig : List UInt8) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthorityEntries t T (m15.entriesWith csig psig) ≠ "ACCEPT" :=
  executableAuthorityEntries_rejects_false_supported_ai_claim (fromArchiveEntries_m15 csig psig)
    verifyCertBytes_m15 decodeCertModel_m15 (cl := m15Claim) (by rw [m15_claims]; simp) rfl
    m15_claim_decodes (a := "trace") (by simp) (m15_hunsafe csig psig) t T

end PCS.V2.Golden.FailClosedFixtures
