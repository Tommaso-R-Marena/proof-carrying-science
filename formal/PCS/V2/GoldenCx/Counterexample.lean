import PCS.V2.GoldenCx.AuthorityStage
import PCS.V2.ZipComplete
import PCS.V2.ExecutableFailClosed
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.Golden.Acceptance

/-!
# The former counterexample: a correctly signed archive with an unregistered check type

The archive `cxRaw` (`PCS.V2.GoldenCx.Spec`) is consistently built and Ed25519-signed.  Its
claim `C1` asserts "trace `trace` never takes action `7` and its cumulative risk stays ≤ 4",
but the committed trace `[0, 1, 2, 4, 1, 7]` takes action `7`, and the evidence item `E1` uses
the **unregistered** tag `trace_invariant_v2`.

Before the fail-closed change the executable took `E1`'s replay outcome from the transcript
and printed `ACCEPT` (this is still true of the legacy extended authority:
`legacyAuthority_cx`, and it is why `legacy_no_unconditional_claim_bridge` holds).

Now (kernel-checked):

* `cx_package_valid` — both signatures verify and the evidence package is well formed;
* `cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected` — the exact decision functions of
  `pcs-lean-authority` (zip mode on the concrete bytes, directory mode, both command-line
  wrappers) never print `ACCEPT`, for **every** transcript and every trust anchor / key
  string / pin.  Derived from the general theorem
  `PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type`.
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.DomainAuthority PCS.V2.Zip
open PCS.V2.ClaimGraph PCS.V2.DomainAdapter PCS.V2.Witnesses PCS.V2.Witnesses.AISafety
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.Checkers PCS.V2.FailClosed PCS.V2.ExecutableFailClosed

/-- The seven archive members with literal byte contents. -/
def entriesV : List (String × ByteArray) :=
  [(tracePath, cx.trace), ("certificate.json", certBA), ("certificate_signature.json", certSigBA),
   (wirePath, wireBA), (indexPath, indexBA), ("package_manifest.json", manifestBA),
   ("package_signature.json", pkgSigBA)]

theorem cxEntries_eq : cxEntries = entriesV := by
  rw [cxEntries, FixtureSpec.entriesWith, certBA_eq, certSigBA_eq, wireBA_eq, indexBA_eq,
    manifestBA_eq, pkgSigBA_eq]
  rfl

theorem fromArchiveEntries_cx : fromArchiveEntries cxEntries = some inputV := by
  rw [cxEntries_eq]; kernel_rfl

theorem cxEntries_sorted : strictSorted (cxEntries.map (·.1)) = true := by
  rw [cxEntries_eq]; kernel_rfl

theorem cxEntries_wellSized : wellSizedB cxEntries = true := by
  rw [cxEntries_eq]; kernel_rfl

theorem decodeZip_cx : decodeZip cxRaw = some cxEntries :=
  decodeZip_encodeZip cxEntries cxEntries_sorted cxEntries_wellSized

/-! ## The legacy (transcript-fallback) authority accepted this archive -/

/-- The earlier extended authority — built-ins, registered checkers, then **transcript
    fallback** — accepts the raw counterexample bytes.  This was the trust-boundary violation. -/
theorem legacyAuthority_cx :
    acceptArchiveWithCheckers certifiedRegistry cxTranscript goldenAnchor cxRaw =
      some (inputV, resultV) :=
  PCS.V2.Golden.acceptArchiveWithCheckers_of decodeZip_cx fromArchiveEntries_cx
    acceptPCSWithCheckers_cx

/-- **The signatures and the evidence package are valid.**  Both Ed25519 signatures verify
    under the trust anchor, the manifest and file map check, and every member digest
    matches (package stage, kernel-checked including both signature verifications). -/
theorem cx_package_valid :
    verifyPackage authorityUnicode PCS.V2.Ed25519.verify goldenAnchor.pk goldenAnchor.expected
      inputV = some pkgResultV := by
  rw [PCS.V2.Golden.goldenAnchor_eq]; exact verifyPackage_cx

/-- The decoded certificate claim `C1`. -/
def cxClaim : CertClaim := ⟨"C1", .computational, predJ 4 7, ["E1"], ["A1"], .computational⟩

theorem modelV_claims : modelV.claims = [cxClaim] := by kernel_rfl

/-- The certificate's only evidence item: `E1`, recorded `PASS`, unregistered tag. -/
def cxE1 : CertEvidence := ⟨"E1", .computationalTest, .pass, predJ 4 7, cx.evidenceJ⟩

theorem modelV_evidence : modelV.evidence = [cxE1] := by kernel_rfl

theorem cxE1_type : checkTypeOf cxE1.json = some "trace_invariant_v2" := by kernel_rfl

theorem cxE1_unregistered : ∀ ty ∈ executableTypes, checkTypeOf cxE1.json ≠ some ty := by
  rw [cxE1_type, executableTypes_eq]; decide

theorem cxE1_mem : cxE1 ∈ modelV.evidence := by rw [modelV_evidence]; simp

theorem tableV_eq : resultV.table = [(traceId, cx.trace)] := rfl

theorem cxClaim_mem : cxClaim ∈ resultV.model.claims := by
  rw [show resultV.model = modelV from rfl, modelV_claims]; simp

theorem cxClaim_decodes : aiAdapter.decode cxClaim.predicate = some goldenTraceClaim := by
  decide

theorem cx_trace_unsafe : ¬ TraceSafe cx.trace.data.toList 4 7 := by
  intro h
  exact h.1 7 (by decide) rfl

theorem cx_not_holds : ¬ aiDomain.Holds resultV.table goldenTraceClaim := by
  intro h
  obtain ⟨tr, htr, hs⟩ := h "trace" (by simp [goldenTraceClaim])
  have : tr = cx.trace.data.toList := by
    rw [tableV_eq] at htr
    simp only [artBytes, lookup, traceId] at htr
    simpa using htr.symm
  subst this
  exact cx_trace_unsafe hs

/-- **Impossibility, for the legacy authority.**  It is false that whenever the
    transcript-fallback extended authority accepts, every certificate claim whose predicate
    the AI-safety adapter decodes holds of the committed artifacts. -/
theorem legacy_no_unconditional_claim_bridge :
    ¬ ∀ (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) inp r,
        acceptArchiveWithCheckers certifiedRegistry t T raw = some (inp, r) →
          ∀ cl ∈ r.model.claims, ∀ tc, aiAdapter.decode cl.predicate = some tc →
            aiDomain.Holds r.table tc := by
  intro h
  exact cx_not_holds (h cxTranscript goldenAnchor cxRaw _ _ legacyAuthority_cx cxClaim
    cxClaim_mem goldenTraceClaim cxClaim_decodes)

/-! ## The strict executable rejects it — for every transcript and every trust anchor -/

theorem inputV_cert : inputV.certificateBytes = certBA := rfl

theorem verifyCertBytes_inputV : verifyCertBytes inputV.certificateBytes = some certV := by
  rw [inputV_cert]; exact verifyCertBytes_certBA

/-- The certified strict authority rejects the counterexample package input. -/
theorem cx_certifiedPCS_none (t : AuthorityTranscript) (T : TrustAnchor) :
    certifiedPCS t T inputV = none :=
  PCS.V2.ExecutableFailClosed.certifiedPCS_rejects_unregistered_type verifyCertBytes_inputV
    decodeCertModel_cx cxE1_mem cxE1_unregistered t T

/-- **Zip mode, concrete bytes.**  The function whose verdict `pcs-lean-authority --zip`
    prints does not return `ACCEPT` on the correctly signed counterexample archive, for every
    transcript (in particular one reporting `PASS` for `E1`) and every trust anchor. -/
theorem cx_rejected (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthority t T cxRaw ≠ "ACCEPT" :=
  PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type decodeZip_cx
    fromArchiveEntries_cx verifyCertBytes_inputV decodeCertModel_cx cxE1_mem cxE1_unregistered t T

/-- **Directory mode.** -/
theorem cx_entries_rejected (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthorityEntries t T cxEntries ≠ "ACCEPT" :=
  PCS.V2.ExecutableFailClosed.executableAuthorityEntries_rejects_unregistered_type
    fromArchiveEntries_cx verifyCertBytes_inputV decodeCertModel_cx cxE1_mem cxE1_unregistered t T

/-- **Command line, both modes**: for every transcript file, key string and pin. -/
theorem cx_cli_rejected (transcript : ByteArray) (keyB64 : String) (fp : Option String) :
    PCS.V2.AuthorityCLI.zipModeOutput cxRaw transcript keyB64 fp ≠ some "ACCEPT" ∧
    PCS.V2.AuthorityCLI.dirModeOutput cxEntries transcript keyB64 fp ≠ some "ACCEPT" :=
  ⟨PCS.V2.ExecutableFailClosed.zipModeOutput_rejects_unregistered_type decodeZip_cx
      fromArchiveEntries_cx verifyCertBytes_inputV decodeCertModel_cx cxE1_mem cxE1_unregistered
      transcript keyB64 fp,
   PCS.V2.ExecutableFailClosed.dirModeOutput_rejects_unregistered_type fromArchiveEntries_cx
      verifyCertBytes_inputV decodeCertModel_cx cxE1_mem cxE1_unregistered transcript keyB64 fp⟩

/-- **Valid signature ≠ acceptance.**  The archive's package stage (signatures, manifest,
    digests) succeeds under the golden trust anchor, the legacy authority accepted it, and
    the strict executable rejects it for every transcript. -/
theorem cx_signed_but_rejected :
    verifyPackage authorityUnicode PCS.V2.Ed25519.verify goldenAnchor.pk goldenAnchor.expected
      inputV = some pkgResultV ∧
    acceptArchiveWithCheckers certifiedRegistry cxTranscript goldenAnchor cxRaw =
      some (inputV, resultV) ∧
    ∀ t, executableAuthority t goldenAnchor cxRaw ≠ "ACCEPT" :=
  ⟨cx_package_valid, legacyAuthority_cx, fun t => cx_rejected t goldenAnchor⟩

end PCS.V2.GoldenCx
