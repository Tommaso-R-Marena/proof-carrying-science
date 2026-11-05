import PCS.V2.ExecutableGeneral

/-!
# Fail-closed behaviour of `pcs-lean-authority`, for every input

Kernel-checked theorems about the exact pure decision functions run by
`pcs-lean-authority` (`executableAuthority` for `--zip`, `executableAuthorityEntries` for
directory mode, and the command-line wrappers `zipModeOutput` / `dirModeOutput`), for **all**
archive bytes, transcripts, keys and fingerprint pins.

## Rejection

* `executableAuthority_rejects_unregistered_type` (and the directory-mode and command-line
  forms): if the delivered certificate contains an evidence item whose `check_spec.type` is
  missing or is not one of the registered types (the six verified built-ins and the three
  registered domain checkers), the verdict is not `ACCEPT` — whatever the item's recorded
  outcome, whether or not any claim requires it, whatever the transcript reports, and
  whoever signed the archive.  The hypotheses only concern pre-acceptance parsing of the
  input bytes.
* `executableAuthority_rejects_false_supported_ai_claim`: a certificate claim recorded at an
  assurance level whose AI-safety predicate is false of the delivered trace bytes is rejected
  — for every transcript and trust anchor.

## Acceptance

* `executableAuthority_evidence_certified`: on `ACCEPT`, every evidence item has a registered
  check type, and its replay outcome is computed by a certified Lean checker *inside the
  executable's own executor* (whose fallback is the constant `FAIL`); a recorded `PASS` carries
  that checker's soundness proposition.
* `executableAuthority_supported_claims_sound`: on `ACCEPT`, every AI-safety or biology claim
  recorded at an assurance level holds of the committed artifacts — **with no obligation
  graph supplied by anyone, no `NoForgery`, and no assumption on the transcript**.  This is
  the claim-level bridge that was previously refuted for the transcript-fallback executable
  (`PCS.V2.GoldenCx.legacy_no_unconditional_claim_bridge`).
-/

set_option autoImplicit false

namespace PCS.V2.ExecutableFailClosed

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.Package
open PCS.V2.CertificateModel PCS.V2.Index PCS.V2.Zip PCS.V2.Checkers PCS.V2.DomainAuthority
open PCS.V2.Witnesses PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.Biology PCS.V2.DomainAdapter
open PCS.V2.AuthorityCLI PCS.V2.FailClosed PCS.V2.ExecutableGeneral

/-- The check types the executable supports: the six verified built-ins and the tags of the
    registered domain checkers (`residue_bounds`, `hydrophobic_score`, `trace_invariant`). -/
def executableTypes : List String := registeredTypes productionCheckers

theorem executableTypes_eq : executableTypes =
    ["reaction_balance", "unit_compatible", "csv_disjoint", "pkpd_contract",
     "pkpd_reference_match", "pkpd_peak_concentration_threshold", "residue_bounds",
     "hydrophobic_score", "trace_invariant"] := rfl

/-! ## Rejection of unregistered check types -/

/-- Package level. -/
theorem certifiedPCS_rejects_unregistered_type {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty)
    (t : AuthorityTranscript) (T : TrustAnchor) : certifiedPCS t T inp = none :=
  strict_rejects_unregistered_type hc hm he hty _ _ t T

/-- **Zip mode.**  For every raw byte string decoding to members whose certificate contains
    an evidence item with a missing or unregistered `check_spec.type`, the function whose
    verdict `pcs-lean-authority --zip` prints does not return `ACCEPT` — for every transcript
    and every trust anchor (any key, any pin), hence regardless of signatures and signer. -/
theorem executableAuthority_rejects_unregistered_type {raw : ByteArray}
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hz : decodeZip raw = some es) (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty)
    (t : AuthorityTranscript) (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" := by
  intro h
  obtain ⟨inp', r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  obtain ⟨es', hz', hi', hp⟩ := certifiedAuthority_spec hr
  rw [hz] at hz'; cases hz'
  rw [hi] at hi'; cases hi'
  rw [certifiedPCS_rejects_unregistered_type hc hm he hty t T] at hp
  cases hp

/-- **Directory mode.** -/
theorem executableAuthorityEntries_rejects_unregistered_type {es : List (String × ByteArray)}
    {inp : PackageInput} {c : CertV2} {m : CertModel} (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty)
    (t : AuthorityTranscript) (T : TrustAnchor) : executableAuthorityEntries t T es ≠ "ACCEPT" := by
  intro h
  obtain ⟨inp', r, hi', hp⟩ := (executableAuthorityEntries_refines_certifiedAuthority t T es).mp h
  rw [hi] at hi'; cases hi'
  rw [certifiedPCS_rejects_unregistered_type hc hm he hty t T] at hp
  cases hp

/-- **Command line, `--zip`.**  For every transcript file content, key string and optional
    fingerprint, the printed line is not `ACCEPT`. -/
theorem zipModeOutput_rejects_unregistered_type {raw : ByteArray}
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hz : decodeZip raw = some es) (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty)
    (transcript : ByteArray) (keyB64 : String) (fp : Option String) :
    zipModeOutput raw transcript keyB64 fp ≠ some "ACCEPT" := by
  intro h
  obtain ⟨t, _, hacc⟩ := (zipModeOutput_accept_iff raw transcript keyB64 fp).mp h
  exact executableAuthority_rejects_unregistered_type hz hi hc hm he hty t _ hacc

/-- `dirModeOutput` prints `ACCEPT` only if the transcript decodes and the directory-mode
    authority accepts. -/
theorem dirModeOutput_accept {entries : List (String × ByteArray)} {transcript : ByteArray}
    {keyB64 : String} {fp : Option String}
    (h : dirModeOutput entries transcript keyB64 fp = some "ACCEPT") :
    ∃ t, decodeAuthorityTranscriptBytes transcript = some t ∧
      executableAuthorityEntries t (cliAnchor keyB64 fp) entries = "ACCEPT" := by
  unfold dirModeOutput at h
  cases ht : decodeAuthorityTranscriptBytes transcript with
  | none => rw [ht] at h; cases h
  | some t =>
    rw [ht] at h
    refine ⟨t, rfl, ?_⟩
    simp only at h
    generalize executableAuthorityEntries t (cliAnchor keyB64 fp) entries = stage at h ⊢
    by_cases hs : stage = "ACCEPT"
    · exact hs
    · exfalso
      split at h
      · simp at h
      · rw [if_neg hs] at h
        have := congrArg (fun o => o.map String.toList) h
        simp only [Option.map_some, String.toList_append, Option.some.injEq] at this
        rw [show "REJECT:".toList = ['R', 'E', 'J', 'E', 'C', 'T', ':'] by decide,
          show "ACCEPT".toList = ['A', 'C', 'C', 'E', 'P', 'T'] by decide] at this
        simp at this

/-- **Command line, directory mode.** -/
theorem dirModeOutput_rejects_unregistered_type {es : List (String × ByteArray)}
    {inp : PackageInput} {c : CertV2} {m : CertModel} (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty)
    (transcript : ByteArray) (keyB64 : String) (fp : Option String) :
    dirModeOutput es transcript keyB64 fp ≠ some "ACCEPT" := by
  intro h
  obtain ⟨t, _, hacc⟩ := dirModeOutput_accept h
  exact executableAuthorityEntries_rejects_unregistered_type hi hc hm he hty t _ hacc

/-! ## What `ACCEPT` establishes -/

theorem certifiedAuthority_strict {t : AuthorityTranscript} {T : TrustAnchor} {raw : ByteArray}
    {inp : PackageInput} {r : AcceptedResult} (h : certifiedAuthority t T raw = some (inp, r)) :
    acceptPCSStrictWith (transcriptExecutor t) certifiedRegistry productionBinders t T inp =
      some r := by
  obtain ⟨_, _, _, hp⟩ := certifiedAuthority_spec h
  exact hp

/-- **Every evidence outcome of an accepted archive is certified.**  If the executable prints
    `ACCEPT`, every evidence item of the accepted certificate has a registered check type, and
    there is a certified checker `k` (verified built-in or registered domain checker) that
    handles its replay request such that the executable's own replay executor — whose
    fallback is the constant `FAIL`, never the transcript — returns exactly `k.run`, and a
    recorded `PASS` carries `k`'s soundness proposition. -/
theorem executableAuthority_evidence_certified {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      ∀ e ∈ r.model.evidence, (∃ ty ∈ executableTypes, checkTypeOf e.json = some ty) ∧
        ∃ k ∈ builtinCheckers ++ certifiedRegistry,
          k.handles (requestFor r.pkg.cert r.model r.table e) = true ∧
          (strictOracles certifiedRegistry t failClosedExec).exec
              (requestFor r.pkg.cert r.model r.table e) =
            k.run (requestFor r.pkg.cert r.model r.table e) ∧
          (e.outcome = .pass → k.Holds (requestFor r.pkg.cert r.model r.table e)) := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  have hs := certifiedAuthority_strict hr
  rw [acceptPCSStrictWith_fallback_irrelevant _ failClosedExec] at hs
  refine ⟨inp, r, hr, fun e he => ⟨?_, strict_evidence_certified hs e he⟩⟩
  obtain ⟨_, _, hsup, _⟩ := acceptPCSStrictWith_spec hs
  have hh := List.all_eq_true.mp hsup e he
  refine Classical.byContradiction fun hne => ?_
  have hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty :=
    fun ty hty' heq => hne ⟨ty, hty', heq⟩
  have h2 : certifiedHandles certifiedRegistry (requestFor r.pkg.cert r.model r.table e) = false :=
    certifiedHandles_false hty _ rfl
  rw [h2] at hh
  cases hh

theorem aiBinder_mem : aiBinder ∈ productionBinders := by simp [productionBinders]
theorem bioBinder_mem : bioBinder ∈ productionBinders := by simp [productionBinders]

theorem boundsChecker_mem : boundsChecker ∈ productionCheckers := by
  simp [productionCheckers, Instances.witnessRegistry]
theorem scoreChecker_mem : scoreChecker ∈ productionCheckers := by
  simp [productionCheckers, Instances.witnessRegistry]

/-- **Supported claims hold (graph-free, no cryptographic or transcript assumption).**  If
    the executable prints `ACCEPT`, then every certificate claim recorded at an assurance
    level (`FORMALLY_PROVEN`, `COMPUTATIONALLY_SUPPORTED`, `EMPIRICALLY_SUPPORTED`,
    `MIXED_SUPPORTED`) whose predicate decodes as an AI-safety trace claim holds of the
    committed trace bytes, and every such claim decoding as a biology residue-site claim
    holds of the committed sequence and site bytes. -/
theorem executableAuthority_supported_claims_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      (∀ cl ∈ r.model.claims, supportive cl.status = true → ∀ tc,
        aiAdapter.decode cl.predicate = some tc → aiDomain.Holds r.table tc) ∧
      (∀ cl ∈ r.model.claims, supportive cl.status = true → ∀ bc,
        bioAdapter.decode cl.predicate = some bc → bioDomain.Holds r.table bc) := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  have hs := certifiedAuthority_strict hr
  refine ⟨inp, r, hr, fun cl hcl hsup tc hdec => ?_, fun cl hcl hsup bc hdec => ?_⟩
  · exact strict_supported_claim_sound hs aiBinder_mem
      (aiAdapter_sound productionCheckers_registered traceChecker_mem _) hcl hsup
      (b := aiBinder) hdec
  · exact strict_supported_claim_sound hs bioBinder_mem
      (bioAdapter_sound productionCheckers_registered boundsChecker_mem scoreChecker_mem _)
      hcl hsup (b := bioBinder) hdec

/-- **Rejection of false supported AI-safety claims (zip mode).**  If the delivered
    certificate has a claim recorded at an assurance level whose predicate decodes to a trace
    claim `tc`, and for some trace `a` of `tc` every delivered file that a certificate artifact
    with id `a` points to violates `TraceSafe · tc.budget tc.forbidden`, the executable does
    not print `ACCEPT` — for every transcript and every trust anchor. -/
theorem executableAuthority_rejects_false_supported_ai_claim {raw : ByteArray}
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hz : decodeZip raw = some es) (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {cl : CertClaim} (hcl : cl ∈ m.claims) (hsup : supportive cl.status = true)
    {tc : TraceClaim} (hdec : aiAdapter.decode cl.predicate = some tc)
    {a : String} (ha : a ∈ tc.traces)
    (hunsafe : ∀ art ∈ m.artifacts, art.id = a → ∀ bytes,
      lookup inp.files art.path = some bytes → ¬ TraceSafe bytes.data.toList tc.budget tc.forbidden)
    (t : AuthorityTranscript) (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT" := by
  intro h
  obtain ⟨inp', r, hr, hai, _⟩ := executableAuthority_supported_claims_sound h
  obtain ⟨es', hz', hi', ha'⟩ := certifiedAuthority_stages hr
  rw [hz] at hz'; cases hz'
  rw [hi] at hi'; cases hi'
  obtain ⟨hc', hm', htab, _⟩ := acceptPCSWithCheckers_stages ha'
  rw [hc] at hc'; cases hc'
  rw [hm] at hm'; cases hm'
  obtain ⟨tr, htr, hsafe⟩ := hai cl hcl hsup tc hdec a ha
  simp only [artBytes] at htr
  obtain ⟨y, hy, rfl⟩ := Option.map_eq_some_iff.mp htr
  obtain ⟨art, hart, hid, hl, _⟩ := artifactTable_spec htab (a, y) (lookup_mem hy)
  exact hunsafe art hart hid y hl hsafe

/-- Package-level form of the supported AI-claim bridge. -/
theorem certifiedPCS_supported_ai_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} (hp : certifiedPCS t T inp = some r) :
    ∀ cl ∈ r.model.claims, supportive cl.status = true → ∀ tc,
      aiAdapter.decode cl.predicate = some tc → aiDomain.Holds r.table tc :=
  fun _ hcl hsup _ hdec => strict_supported_claim_sound hp aiBinder_mem
    (aiAdapter_sound productionCheckers_registered traceChecker_mem _) hcl hsup
    (b := aiBinder) hdec

/-- **Rejection of false supported AI-safety claims (directory mode).** -/
theorem executableAuthorityEntries_rejects_false_supported_ai_claim
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {cl : CertClaim} (hcl : cl ∈ m.claims) (hsup : supportive cl.status = true)
    {tc : TraceClaim} (hdec : aiAdapter.decode cl.predicate = some tc)
    {a : String} (ha : a ∈ tc.traces)
    (hunsafe : ∀ art ∈ m.artifacts, art.id = a → ∀ bytes,
      lookup inp.files art.path = some bytes → ¬ TraceSafe bytes.data.toList tc.budget tc.forbidden)
    (t : AuthorityTranscript) (T : TrustAnchor) : executableAuthorityEntries t T es ≠ "ACCEPT" := by
  intro h
  obtain ⟨inp', r, hi', hp⟩ := (executableAuthorityEntries_refines_certifiedAuthority t T es).mp h
  rw [hi] at hi'; cases hi'
  obtain ⟨hc', hm', htab, _⟩ := acceptPCSWithCheckers_stages (certifiedPCS_spec hp).1
  rw [hc] at hc'; cases hc'
  rw [hm] at hm'; cases hm'
  obtain ⟨tr, htr, hsafe⟩ := certifiedPCS_supported_ai_sound hp cl hcl hsup tc hdec a ha
  simp only [artBytes] at htr
  obtain ⟨y, hy, rfl⟩ := Option.map_eq_some_iff.mp htr
  obtain ⟨art, hart, hid, hl, _⟩ := artifactTable_spec htab (a, y) (lookup_mem hy)
  exact hunsafe art hart hid y hl hsafe

end PCS.V2.ExecutableFailClosed
