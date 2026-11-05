import PCS.V2.Golden.Acceptance
import PCS.V2.ExecutableGeneral

/-!
# Kernel-checked rejection of a tampered golden archive

`tamperedRaw` is the canonical ZIP of the golden archive members with **only** the trace
member replaced by `[0, 1, 2, 4, 1, 7]`, which takes the forbidden action `7`.  The signed
certificate, both genuine Ed25519 signature records, the manifest, wire and index are the
original golden bytes (the "swapped artifact" attack).

`tamperedRaw_rejected` proves, in the kernel, that the function whose verdict
`pcs-lean-authority --zip` prints does **not** return `ACCEPT` on these bytes — for every
transcript and every trust anchor.  The proof evaluates no hash and no signature: it decodes
the ZIP (through the decoder-completeness theorem), partitions the members, reuses the golden
certificate parse, and applies the general rejection theorem
`executableAuthority_rejects_unsafe_trace_evidence`: the certificate records `E1` as a
`PASS` `trace_invariant` replay over artifact `trace`, whose archived bytes violate the
invariant, so no acceptance is possible.  (Operationally the compiled binary reports
`REJECT:package` — the manifest digest of the trace member no longer matches; the theorem does
not need to know which stage rejects.)
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Index
open PCS.V2.CertificateModel PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses
open PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden PCS.V2.PKPDCheck
open PCS.V2.ExecutableGeneral

/-- The tampered trace: the golden trace with its last action replaced by the forbidden `7`. -/
def tamperedTrace : ByteArray := ⟨#[0, 1, 2, 4, 1, 7]⟩

/-- The golden members with the trace member swapped. -/
def tamperedEntries : List (String × ByteArray) :=
  [(tracePath, tamperedTrace), ("certificate.json", certBA), ("certificate_signature.json", certSigBA),
   (wirePath, wireBA), (indexPath, indexBA), ("package_manifest.json", manifestBA),
   ("package_signature.json", pkgSigBA)]

/-- The raw canonical ZIP bytes of the tampered archive. -/
def tamperedRaw : ByteArray := ⟨(encodeZip tamperedEntries).toArray⟩

def tamperedInput : PackageInput :=
  { certificateBytes := certBA, certificateSignatureBytes := certSigBA, manifestBytes := manifestBA,
    packageSignatureBytes := pkgSigBA,
    files := [(tracePath, tamperedTrace), ("certificate.json", certBA), (wirePath, wireBA),
              (indexPath, indexBA)] }

theorem tamperedEntries_sorted : strictSorted (tamperedEntries.map (·.1)) = true := by kernel_rfl

theorem tamperedEntries_wellSized : wellSizedB tamperedEntries = true := by kernel_rfl

theorem decodeZip_tampered : decodeZip tamperedRaw = some tamperedEntries :=
  decodeZip_encodeZip tamperedEntries tamperedEntries_sorted tamperedEntries_wellSized

theorem fromArchiveEntries_tampered : fromArchiveEntries tamperedEntries = some tamperedInput := by
  kernel_rfl

/-- The golden certificate's evidence item `E1`, as decoded. -/
def goldenE1 : CertEvidence := ⟨"E1", .computationalTest, .pass, predJ 4 7, golden.evidenceJ⟩

theorem modelV_evidence : modelV.evidence = [goldenE1] := by kernel_rfl

theorem modelV_artifacts_paths : modelV.artifacts.map (fun a => (a.id, a.path)) = [(traceId, tracePath)] := by
  kernel_rfl

theorem goldenE1_tag : isCheckType "trace_invariant" goldenE1.json = true := by kernel_rfl

theorem goldenE1_parse : parseTrace goldenE1.json = some ("trace", 4, 7) := by kernel_rfl

theorem tamperedTrace_unsafe : ¬ TraceSafe tamperedTrace.data.toList 4 7 := by
  intro h
  exact h.1 7 (by decide) rfl

theorem lookup_tampered_trace : lookup tamperedInput.files tracePath = some tamperedTrace := by
  kernel_rfl

/-- Every certificate artifact with id `trace` points to the tampered member, whose bytes are
    unsafe. -/
theorem tampered_hunsafe : ∀ art ∈ modelV.artifacts, art.id = "trace" → ∀ bytes,
    lookup tamperedInput.files art.path = some bytes → ¬ TraceSafe bytes.data.toList 4 7 := by
  intro art hart hid bytes hl
  have hp : (art.id, art.path) ∈ modelV.artifacts.map (fun a => (a.id, a.path)) :=
    List.mem_map_of_mem hart
  rw [modelV_artifacts_paths] at hp
  simp only [List.mem_singleton, Prod.mk.injEq] at hp
  rw [hp.2, lookup_tampered_trace] at hl
  cases hl
  exact tamperedTrace_unsafe

/-- **Kernel-checked rejection (zip mode).**  For every transcript and every trust anchor,
    `pcs-lean-authority --zip` does not print `ACCEPT` on the tampered golden archive. -/
theorem tamperedRaw_rejected (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthority t T tamperedRaw ≠ "ACCEPT" :=
  executableAuthority_rejects_unsafe_trace_evidence decodeZip_tampered fromArchiveEntries_tampered
    verifyCertBytes_certBA decodeCertModel_golden (e := goldenE1) (by rw [modelV_evidence]; simp)
    rfl goldenE1_tag goldenE1_parse tampered_hunsafe t T

/-- **Kernel-checked rejection (directory mode).** -/
theorem tamperedEntries_rejected (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthorityEntries t T tamperedEntries ≠ "ACCEPT" :=
  executableAuthorityEntries_rejects_unsafe_trace_evidence fromArchiveEntries_tampered
    verifyCertBytes_certBA decodeCertModel_golden (e := goldenE1) (by rw [modelV_evidence]; simp)
    rfl goldenE1_tag goldenE1_parse tampered_hunsafe t T

/-- In particular the golden transcript, the golden trust anchor and the genuine golden
    signatures do not make the tampered archive acceptable, while the untampered archive is
    accepted (`aiSafetyGoldenArchive_accepts`): the verdict separates the two byte strings. -/
theorem golden_vs_tampered :
    executableAuthority goldenTranscript goldenAnchor goldenRaw = "ACCEPT" ∧
    executableAuthority goldenTranscript goldenAnchor tamperedRaw ≠ "ACCEPT" :=
  ⟨aiSafetyGoldenArchive_accepts, tamperedRaw_rejected _ _⟩

end PCS.V2.Golden
