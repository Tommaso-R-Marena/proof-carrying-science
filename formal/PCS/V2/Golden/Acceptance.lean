import PCS.V2.Golden.AuthorityStage
import PCS.V2.ZipComplete
import PCS.V2.Witnesses.AISafetyCampaign

/-!
# Kernel-checked acceptance of the committed golden AI-safety archive

This file closes the executable-to-kernel gap for the golden fixture
(`fixtures/ai_safety_golden/`): the exact function executed by `pcs-lean-authority --zip`
is proved, in Lean's trusted kernel, to print `ACCEPT` on the raw golden ZIP bytes
`goldenRaw`, and the bounded AI-safety property of the committed trace is derived from that
acceptance through the existing soundness theorems.

Chain (every arrow is a theorem):

```
goldenRaw (= canonical ZIP encoding of goldenEntries)
  ─ decodeZip_encodeZip + goldenEntries_sorted/_wellSized ─▶ decodeZip goldenRaw = some goldenEntries
  ─ fromArchiveEntries_golden ─▶ package input inputV (literal member bytes)
  ─ verifyPackage_golden (certificate, two Ed25519 signatures, manifest, file map)
  ─ acceptPCS_golden (certificate model, env, workflow, artifact table, certified
    trace_invariant replay, normalized index/wire) ─ transcriptCovers_golden
  ─▶ certifiedAuthority_golden : certifiedAuthority … goldenRaw = some (inputV, resultV)
  ─ executableAuthority_refines_certifiedAuthority ─▶ aiSafetyGoldenArchive_accepts
  ─ executableAuthority_domain_sound ─▶ aiSafetyGoldenArchive_committed_safe   (no FaithfulLog)
  ─ aiBridge.transport ─▶ aiSafetyGoldenArchive_deployed_safe                (needs FaithfulLog)
```

No `NoForgery` hypothesis is used or claimed: the signing key is the public RFC 8032 TEST 1
key, so signature verification here establishes *integrity relative to that published key*,
not provenance.
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.DomainAuthority PCS.V2.Zip
open PCS.V2.ClaimGraph PCS.V2.DomainAdapter PCS.V2.Witnesses PCS.V2.Witnesses.AISafety
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.Checkers

/-! ## Archive entries -/

/-- The seven archive members with literal byte contents. -/
def entriesV : List (String × ByteArray) :=
  [(tracePath, golden.trace), ("certificate.json", certBA), ("certificate_signature.json", certSigBA),
   (wirePath, wireBA), (indexPath, indexBA), ("package_manifest.json", manifestBA),
   ("package_signature.json", pkgSigBA)]

theorem goldenEntries_eq : goldenEntries = entriesV := by
  rw [goldenEntries, FixtureSpec.entriesWith, certBA_eq, certSigBA_eq, wireBA_eq, indexBA_eq,
    manifestBA_eq, pkgSigBA_eq]
  rfl

theorem fromArchiveEntries_golden : fromArchiveEntries goldenEntries = some inputV := by
  rw [goldenEntries_eq]; kernel_rfl

/-- The member names are strictly increasing (canonical ZIP order). -/
theorem goldenEntries_sorted : strictSorted (goldenEntries.map (·.1)) = true := by
  rw [goldenEntries_eq]; kernel_rfl

/-- Every ZIP field is in range.  (Only lengths are computed; no CRC-32 is evaluated.) -/
theorem goldenEntries_wellSized : wellSizedB goldenEntries = true := by
  rw [goldenEntries_eq]; kernel_rfl

/-- **Raw ZIP decoding (kernel-checked, via decoder completeness).** -/
theorem decodeZip_golden : decodeZip goldenRaw = some goldenEntries :=
  decodeZip_encodeZip goldenEntries goldenEntries_sorted goldenEntries_wellSized

/-! ## Acceptance -/

/-- Composition of the archive stages (arbitrary inputs). -/
theorem acceptArchiveWithCheckers_of {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {T : TrustAnchor} {raw : ByteArray} {es : List (String × ByteArray)} {inp : PackageInput}
    {r : AcceptedResult} (h1 : decodeZip raw = some es) (h2 : fromArchiveEntries es = some inp)
    (h3 : acceptPCSWithCheckers cs t T inp = some r) :
    acceptArchiveWithCheckers cs t T raw = some (inp, r) := by
  simp only [acceptArchiveWithCheckers, h1, h2, h3, Option.map_some]

/-- Composition of the archive stages for the strict authority (arbitrary inputs). -/
theorem certifiedAuthority_of {t : AuthorityTranscript} {T : TrustAnchor} {raw : ByteArray}
    {es : List (String × ByteArray)} {inp : PackageInput} {r : AcceptedResult}
    (h1 : decodeZip raw = some es) (h2 : fromArchiveEntries es = some inp)
    (h3 : certifiedPCS t T inp = some r) : certifiedAuthority t T raw = some (inp, r) := by
  simp only [certifiedPCS] at h3
  simp only [certifiedAuthority, FailClosed.acceptArchiveStrictWith, h1, h2, h3, Option.map_some]

/-- **Check-type gate on the golden certificate**: its only evidence item `E1` has the
    registered tag `trace_invariant`. -/
theorem supportedEvidence_golden :
    FailClosed.supportedEvidenceB certifiedRegistry certV modelV tableV = true := by kernel_rfl

/-- **Claim-binding gate on the golden result**: claim `C1` (recorded
    `COMPUTATIONALLY_SUPPORTED`) is domain-accepted by the AI-safety adapter through its
    canonical graph from its own required evidence `E1`. -/
theorem claimsBound_golden :
    FailClosed.claimsBoundB FailClosed.productionBinders resultV = true := by kernel_rfl

/-- **The certified strict authority accepts the golden package input.** -/
theorem certifiedPCS_golden : certifiedPCS goldenTranscript goldenAnchor inputV = some resultV :=
  FailClosed.acceptPCSStrictWith_of acceptPCS_golden transcriptCovers_golden
    supportedEvidence_golden claimsBound_golden

/-- **The certified strict authority accepts the raw golden bytes.** -/
theorem certifiedAuthority_golden :
    certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inputV, resultV) :=
  certifiedAuthority_of decodeZip_golden fromArchiveEntries_golden certifiedPCS_golden

/-- **Concrete executable acceptance, kernel-checked.**  The exact function whose verdict
    `pcs-lean-authority --zip` prints returns `ACCEPT` on the committed golden ZIP bytes. -/
theorem aiSafetyGoldenArchive_accepts :
    executableAuthority goldenTranscript goldenAnchor goldenRaw = "ACCEPT" :=
  (executableAuthority_refines_certifiedAuthority _ _ _).mpr ⟨_, _, certifiedAuthority_golden⟩

/-- The same verdict as stated in the campaign file. -/
theorem aiSafetyGoldenArchive_verdict_eq : aiSafetyGoldenArchive_verdict = "ACCEPT" :=
  aiSafetyGoldenArchive_accepts

/-- **Directory mode**: `pcs-lean-authority <dir>` on the seven golden members (in the
    canonical order) prints `ACCEPT`. -/
theorem aiSafetyGoldenArchive_entries_accepts :
    executableAuthorityEntries goldenTranscript goldenAnchor goldenEntries = "ACCEPT" :=
  (executableAuthorityEntries_refines_certifiedAuthority _ _ _).mpr
    ⟨_, _, fromArchiveEntries_golden, certifiedPCS_golden⟩

/-! ## Domain consequences -/

theorem resultV_trace : artBytes resultV.table "trace" = some traceBytes.data.toList := by
  kernel_rfl

/-- The (untrusted) golden obligation graph is domain-accepted on the accepted result. -/
theorem golden_domainAccepts :
    domainAccepts aiAdapter resultV "C1" goldenGraph = some goldenTraceClaim := by
  kernel_rfl

/-- **Committed-world bounded AI-safety property (no `FaithfulLog`, no `NoForgery`).**
    The certified authority accepts the raw golden bytes; the golden graph is
    domain-accepted with the claim "no action 7, cumulative risk ≤ 4 after every step" over
    the committed `trace` artifact; and — *derived from the acceptance through
    `executableAuthority_domain_sound`*, not re-evaluated — the committed trace bytes satisfy
    that invariant.  Every domain-accepted graph for `C1` yields the same conclusion. -/
theorem aiSafetyGoldenArchive_committed_safe :
    certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inputV, resultV) ∧
    domainAccepts aiAdapter resultV "C1" goldenGraph = some goldenTraceClaim ∧
    (∀ g, domainAccepts aiAdapter resultV "C1" g = some goldenTraceClaim →
      artBytes resultV.table "trace" = some traceBytes.data.toList ∧
      TraceSafe traceBytes.data.toList 4 7) := by
  refine ⟨certifiedAuthority_golden, golden_domainAccepts, fun g hg => ⟨resultV_trace, ?_⟩⟩
  obtain ⟨inp, r, hr, hsafe⟩ := aiSafetyGoldenArchive_domain_sound aiSafetyGoldenArchive_accepts
  rw [certifiedAuthority_golden] at hr
  cases hr
  obtain ⟨tr, htr, hs⟩ := hsafe g hg
  rw [resultV_trace] at htr
  cases htr
  exact hs

/-- **Deployed-world property, only under `FaithfulLog`.**  If the committed artifact table
    faithfully logs a deployed run, every deployed episode named by the claim is safe.
    Without `FaithfulLog` no deployed-world statement is made
    (`committed_safe_deployed_unsafe` shows the premise is necessary). -/
theorem aiSafetyGoldenArchive_deployed_safe (ew : DeployedRun)
    (hlog : FaithfulLog resultV.table ew) : DeployedSafe ew goldenTraceClaim := by
  obtain ⟨inp, r, hr, h⟩ := PCS.V2.Witnesses.AISafetyCampaign.aiSafetyGoldenArchive_deployed_safe
    aiSafetyGoldenArchive_accepts
  rw [certifiedAuthority_golden] at hr
  cases hr
  exact h goldenGraph ew golden_domainAccepts hlog

end PCS.V2.Golden
