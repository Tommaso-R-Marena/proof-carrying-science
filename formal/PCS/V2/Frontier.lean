import PCS.V2.CanonicalArchive

/-!
# Frontier flagship: authoritative raw-archive acceptance under unforgeability alone

`PCS.V2.HighAssurance.pcs_high_assurance_acceptance_sound` is parameterised by
`AuthorityContracts`, i.e. by Ed25519 unforgeability **and** a user-chosen meaning
`describes` of the environment capture together with `CaptureSound` for it.

Instantiating `describes` with the meaning that the Lean authority *verifies itself*
(`PCS.V2.EnvFacts.EnvFacts`, via `authority_capture_sound`) removes the capture hypothesis.
The resulting theorems have exactly one hypothesis — `NoForgery` for the Lean RFC 8032
verifier and the trust-anchor key, a cryptographic hardness assumption that Lean cannot
prove — and conclude:

* structural package/certificate/index/normalized-decision assurance and per-claim
  `Assures` (from the generic flagship, `ScientificAssurance`);
* authenticity against the key holder's actual signing record;
* every member and artifact digest is FIPS 180-4 SHA-256 of the exact bytes;
* every passing `reaction_balance`, `unit_compatible`, `csv_disjoint`, `pkpd_contract`,
  `pkpd_reference_match` or `pkpd_peak_concentration_threshold` item denotes its declarative scientific proposition;
* every signed static-workflow claim satisfies `WorkflowDescribes` w.r.t. the transcript's
  normalized static analysis;
* the signed environment declaration equals the transcript capture, which satisfies the
  verified `EnvFacts` (bound sources, exact/hash pins, interpreter versions, digest-pinned
  bases);
* for `pcs_frontier_archive_acceptance_sound`: the raw archive bytes are exactly the
  canonical STORED ZIP encoding of a uniquely named member list (no `ZipDecoderFaithful`).

Nothing about the parts of the environment capture *outside* `EnvFacts` is concluded, so
no assumption about them is needed.
-/

set_option autoImplicit false

namespace PCS.V2.Frontier

open PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Archive PCS.V2.Authority PCS.V2.HighAssurance
open PCS.V2.Zip PCS.V2.TCB PCS.V2.Package PCS.V2.CanonicalArchive PCS.V2.Replay PCS.V2.Signature
open PCS.V2.Domains

/-- The meaning of the authority's environment capture that Lean verifies itself. -/
def VerifiedCapture (t : AuthorityTranscript) (inv : List InventoryItem) (v : JVal) : Prop :=
  v = .null ∨ (v = t.environmentCapture ∧ PCS.V2.EnvFacts.EnvFacts inv v)

/-- `AuthorityContracts` whose capture component is a theorem: only unforgeability is
    supplied. -/
def verifiedContracts (t : AuthorityTranscript) (T : TrustAnchor) (signed : List UInt8 → Prop)
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed) : AuthorityContracts t T :=
  { signed := signed, noForgery := hB, describes := VerifiedCapture t,
    captureSound := authority_capture_sound t }

/-- **Frontier flagship (package form).**  Sole hypothesis: Ed25519 unforgeability for the
    trust anchor. -/
theorem pcs_frontier_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r) :
    HighAssurance t T (verifiedContracts t T signed hB) inp r :=
  pcs_high_assurance_acceptance_sound _ h

/-- **Frontier flagship (raw canonical archive form).**  Sole hypothesis: Ed25519
    unforgeability for the trust anchor.  No `ZipDecoderFaithful`, `ReplayFaithful` (for the
    six verified built-ins), `Ed25519ImplCorrect`, SHA-256-specification or `CaptureSound`
    hypothesis. -/
theorem pcs_frontier_archive_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) :
    ∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      HighAssurance t T (verifiedContracts t T signed hB) inp r :=
  pcs_canonical_archive_acceptance_sound _ h

/-- The same from the compiled authority's `ACCEPT` verdict in `--zip` mode. -/
theorem pcs_frontier_authority_binary_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} (h : diagnoseArchiveWithTranscript t T raw = "ACCEPT") :
    ∃ inp r es, acceptArchiveWithTranscript t T raw = some (inp, r) ∧ CanonicalZip raw es ∧
      ArchivePartition es inp ∧ HighAssurance t T (verifiedContracts t T signed hB) inp r :=
  pcs_authority_archive_binary_sound _ h

/-- The environment conclusion of the frontier flagship, unfolded: the signed declaration
    is the transcript capture and satisfies the verified `EnvFacts`. -/
theorem pcs_frontier_environment {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r)
    {eb : EnvBinding} {inv : List InventoryItem} (he : r.env = some (eb, inv)) :
    envProjection eb.signed = t.environmentCapture ∧
      PCS.V2.EnvFacts.EnvFacts inv (envProjection eb.signed) := by
  rcases ((pcs_frontier_acceptance_sound hB h).environment eb inv he).2 with h0 | h1
  · exact absurd h0 (envProjection_ne_null _)
  · exact h1

/-! ## Exact forgery extraction (no unforgeability hypothesis) -/

/-- **Reduction to a forgery.**  If the Lean authority accepts a package and the trust-anchor
    key holder did *not* sign the package envelope or the certificate envelope, then the
    accepted package itself contains a concrete forgery for the Lean RFC 8032 verifier under
    the trust-anchor key: the delivered signature bytes on an unsigned message.  This is the
    exact contrapositive content of `NoForgery`; it needs no cryptographic assumption. -/
theorem pcs_unsigned_acceptance_yields_forgery {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} (signed : List UInt8 → Prop)
    (h : acceptPCSWithTranscript t T inp = some r)
    (hun : ¬ signed (signedMessage packageSignatureDomain (encodeManifest r.pkg.manifest)) ∨
      ∃ csp, certSigPayload r.pkg.cert = some csp ∧
        ¬ signed (signedMessage certificateSignatureDomain csp)) :
    ∃ m s, PCS.V2.Ed25519.verify T.pk m s = true ∧ ¬ signed m := by
  have hs := (acceptPCS_sound (acceptPCSWithTranscript_implies_acceptPCS h)).package
  have hV : (transcriptOracles t).ed25519 = PCS.V2.Ed25519.verify := transcriptOracles_ed25519 t
  rcases hun with hp | ⟨csp, hcsp, hc⟩
  · have hv := hs.packageSig.verified
    rw [hV] at hv
    exact ⟨_, _, hv, hp⟩
  · obtain ⟨csp', hcsp', hcs⟩ := hs.certSig
    rw [hcsp] at hcsp'
    cases hcsp'
    have hv := hcs.verified
    rw [hV] at hv
    exact ⟨_, _, hv, hc⟩

end PCS.V2.Frontier
