import PCS.V2.Golden.Rejection

/-!
# Kernel-checked rejection of the insider-re-signed unsafe archive

The adversarial campaign's mutation `m1` (`PCS.V2.Witnesses.AISafetyCampaign.m1`) is the
golden fixture with the trace `[0, 1, 2, 4, 1, 7]` (forbidden action `7`) and a certificate
that is **consistently rebuilt** for that trace: correct artifact digest, correct semantic and
integrity hashes, correct normalized wire and index, a manifest over the new members, and the
evidence item `E1` recorded as a `PASS` `trace_invariant` replay.  Re-signed with the test
key it is exactly what an insider holding the signing key would produce.  The *original*
production authority (transcript-only replay) accepts it (`#guard` in the campaign file).

`insider_rejected_entries` / `insider_rejected_zip` prove in the kernel that the executable's
decision function rejects it **for every pair of signature byte strings**, every transcript
and every trust anchor: the rejection cannot be bypassed by any choice of key or signature,
because it follows from the general theorem
`executableAuthority_rejects_unsafe_trace_evidence` and the certificate's own content.

Only the certificate parse is evaluated (two SHA-256 domain digests, kernel-checked through
the proved fast SHA-256); no signature is evaluated, since the statement quantifies over all
signatures.
-/

set_option autoImplicit false

namespace PCS.V2.Golden.Insider

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Index
open PCS.V2.CertificateModel PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses PCS.V2.Domains
open PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden PCS.V2.PKPDCheck
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.ExecutableGeneral PCS.V2.SHA256 PCS.V2.Canonical
open PCS.V2.Golden

/-- Semantic hash of the insider certificate (checked below by kernel evaluation). -/
def semLit : List UInt8 :=
  [158, 210, 218, 170, 208, 248, 151, 190, 79, 76, 92, 25, 73, 187, 208, 103, 235, 166, 88, 31,
   144, 245, 169, 71, 13, 63, 231, 170, 125, 9, 194, 148]

/-- Integrity hash of the insider certificate (checked below by kernel evaluation). -/
def intLit : List UInt8 :=
  [247, 95, 143, 167, 219, 29, 241, 207, 160, 132, 211, 191, 17, 79, 104, 245, 107, 122, 229, 89,
   189, 124, 16, 34, 210, 6, 101, 179, 217, 59, 45, 89]

theorem m1_semHash : m1.semHash = semLit := by
  rw [FixtureSpec.semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem m1_intHash : m1.intHash = intLit := by
  rw [FixtureSpec.intHash, m1_semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

def certJV1 : JVal := .obj (m1.certMembers (hexEncode semLit) (hexEncode intLit))

def certV1 : CertV2 :=
  { members := m1.certMembers (hexEncode semLit) (hexEncode intLit),
    semanticHash := semLit, integrityHash := intLit }

theorem m1_certBytes_jcs : m1.certBytes = jcsBytes certJV1 := by
  rw [FixtureSpec.certBytes, FixtureSpec.certJ, m1_semHash, m1_intHash]; rfl

theorem certJV1_canonical : canonical certJV1 = true := by kernel_rfl

theorem certJV1_size : (jcsBytes certJV1).size = 1683 := by
  rw [jcsBytes_size]; kernel_rfl

/-- The insider certificate parses (canonical bytes, both hashes recomputed and matching). -/
theorem verifyCertBytes_m1 : verifyCertBytes m1.certBytes = some certV1 := by
  have hs : (jcsBytes certJV1).size ≤ maxCertificateBytes := by
    rw [certJV1_size]; decide
  rw [m1_certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete certJV1_canonical hs]
  simp only [certJV1, certHashesOK, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

def modelV1 : CertModel := (decodeCertModel certV1).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_m1 : decodeCertModel certV1 = some modelV1 := by kernel_rfl

/-- The insider certificate's evidence item: `E1`, recorded `PASS`, `trace_invariant`. -/
def insiderE1 : CertEvidence := ⟨"E1", .computationalTest, .pass, predJ 4 7, m1.evidenceJ⟩

theorem modelV1_evidence : modelV1.evidence = [insiderE1] := by kernel_rfl

theorem modelV1_artifacts_paths :
    modelV1.artifacts.map (fun a => (a.id, a.path)) = [(traceId, tracePath)] := by kernel_rfl

theorem insiderE1_tag : isCheckType "trace_invariant" insiderE1.json = true := by kernel_rfl

theorem insiderE1_parse : parseTrace insiderE1.json = some ("trace", 4, 7) := by kernel_rfl

/-- The package input materialised from the insider members, for arbitrary signatures. -/
def insiderInput (csig psig : List UInt8) : PackageInput :=
  { certificateBytes := m1.certBytes, certificateSignatureBytes := m1.certSigBytesWith csig,
    manifestBytes := m1.manifestBytes, packageSignatureBytes := m1.pkgSigBytesWith psig,
    files := m1.files }

theorem fromArchiveEntries_insider_all :
    ∀ csig psig : List UInt8,
      fromArchiveEntries (m1.entriesWith csig psig) = some (insiderInput csig psig) := by
  kernel_rfl

theorem lookup_insider_trace : lookup m1.files tracePath = some m1.trace := by kernel_rfl

theorem m1_trace_unsafe : ¬ TraceSafe m1.trace.data.toList 4 7 := by
  intro h
  exact h.1 7 (by decide) rfl

theorem insider_hunsafe (csig psig : List UInt8) :
    ∀ art ∈ modelV1.artifacts, art.id = "trace" → ∀ bytes,
      lookup (insiderInput csig psig).files art.path = some bytes →
        ¬ TraceSafe bytes.data.toList 4 7 := by
  intro art hart hid bytes hl
  have hp : (art.id, art.path) ∈ modelV1.artifacts.map (fun a => (a.id, a.path)) :=
    List.mem_map_of_mem hart
  rw [modelV1_artifacts_paths] at hp
  simp only [List.mem_singleton, Prod.mk.injEq] at hp
  rw [hp.2] at hl
  change lookup m1.files tracePath = some bytes at hl
  rw [lookup_insider_trace] at hl
  cases hl
  exact m1_trace_unsafe

/-- **Kernel-checked rejection of the insider archive (directory mode).**  For all
    signature byte strings `csig`, `psig` (in particular the genuine test-key signatures an
    insider would produce), every transcript and every trust anchor,
    `pcs-lean-authority <dir>` does not print `ACCEPT` on the insider's members. -/
theorem insider_rejected_entries (csig psig : List UInt8) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthorityEntries t T (m1.entriesWith csig psig) ≠ "ACCEPT" :=
  executableAuthorityEntries_rejects_unsafe_trace_evidence (fromArchiveEntries_insider_all csig psig)
    verifyCertBytes_m1 decodeCertModel_m1 (e := insiderE1) (by rw [modelV1_evidence]; simp)
    rfl insiderE1_tag insiderE1_parse (insider_hunsafe csig psig) t T

/-- **Kernel-checked rejection of the insider archive (zip mode).**  Every raw byte string
    whose canonical-ZIP decoding is the insider's member list — with any signature bytes — is
    rejected by `pcs-lean-authority --zip`, for every transcript and trust anchor.  (The
    campaign's concrete `m1.build` decodes to `m1.entriesWith m1.genCertSig m1.genPkgSig`;
    that decoding fact is evaluated by `#guard`, not kernel-checked, because it would require
    evaluating Ed25519 *signing* in the kernel.) -/
theorem insider_rejected_zip (csig psig : List UInt8) {raw : ByteArray}
    (hz : decodeZip raw = some (m1.entriesWith csig psig)) (t : AuthorityTranscript)
    (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" :=
  executableAuthority_rejects_unsafe_trace_evidence hz (fromArchiveEntries_insider_all csig psig)
    verifyCertBytes_m1 decodeCertModel_m1 (e := insiderE1) (by rw [modelV1_evidence]; simp)
    rfl insiderE1_tag insiderE1_parse (insider_hunsafe csig psig) t T

end PCS.V2.Golden.Insider
