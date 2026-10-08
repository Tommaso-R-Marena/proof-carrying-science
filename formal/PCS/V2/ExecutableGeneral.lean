import PCS.V2.AuthorityCLI
import PCS.V2.Witnesses.AISafetyDeployment

/-!
# What the executable's `ACCEPT` means for *arbitrary* archives and transcripts

This file connects the exact pure decision functions run by `pcs-lean-authority`
(`executableAuthority` for `--zip`, `executableAuthorityEntries` for directory mode, and the
command-line wrappers `AuthorityCLI.zipModeOutput` / `dirModeOutput`) to the bounded
AI-safety invariant `TraceSafe`, for **every** input: every raw byte string, every
transcript, every public key and fingerprint pin.

## What already existed, and what was missing

* `executableAuthority_refines_certifiedAuthority`: `ACCEPT` ⇔ the certified extended
  authority accepts.
* `executableAuthority_domain_sound`: `ACCEPT` ⇒ every AI-safety claim that is
  *domain-accepted with some obligation graph* holds of the committed traces.

The second theorem is general, but its conclusion is gated by `domainAccepts`, a check the
executable never runs (the obligation graph is not an input of `pcs-lean-authority`).  The
missing bridge was therefore a statement about the executable's verdict **alone**, phrased in
terms of the bytes the executable actually reads.  This file proves it:

* `executableAuthority_registered_evidence_sound` (domain-independent): `ACCEPT` ⇒ for every
  evidence item that the signed certificate records as `PASS` and whose `check_spec.type` is
  the tag of a registered certified checker, that checker's soundness proposition holds of
  the committed artifacts.  No `NoForgery`, no assumption on the transcript.
* `executableAuthority_trace_evidence_sound` (AI safety): `ACCEPT` ⇒ for every `PASS`
  evidence item tagged `trace_invariant` with parameters `(a, b, f)`, the archive member
  holding artifact `a` — its exact bytes in the decoded raw ZIP — satisfies
  `TraceSafe · b f`.
* `executableAuthority_trace_claim_sound`: the claim-level form (a certificate claim whose
  predicate decodes to "trace `a` is safe for budget `b`, forbidden action `f`" and which
  requires such a `PASS` evidence item) — derived through the *existing*
  `executableAuthority_domain_sound` via a canonical one-leaf obligation graph that is
  shown to be domain-accepted.
* `executableAuthority_rejects_unsafe_trace_evidence` (and the directory-mode and CLI
  forms): the contrapositive, stated purely in terms of **pre-acceptance parsing** of the
  input bytes.  Any archive whose certificate records a `PASS` `trace_invariant` evidence
  item over a member whose bytes violate the invariant is rejected — for every transcript and
  every trust anchor, i.e. no matter who signed it.

## Why the general result must be conditional (proved obstructions)

* **(Historical; now repaired.)**  For the earlier transcript-fallback authority,
  `PCS.V2.GoldenCx.legacy_no_unconditional_claim_bridge` (kernel-checked) exhibits a
  consistently signed archive it accepts whose AI-safety claim predicate is false of the
  committed trace (evidence tag `trace_invariant_v2`, `PASS` taken from the transcript).  The
  strict executable rejects that archive (`PCS.V2.GoldenCx.cx_rejected`), and for it the
  graph-free claim-level bridge for *supported* claims is proved:
  `PCS.V2.ExecutableFailClosed.executableAuthority_supported_claims_sound`.
* `ACCEPT` alone does not imply that any trace is safe: acceptance means the certificate is
  *honest about its replays*, not that its outcomes are positive.  A `FAIL`-recorded
  certified item over an unsafe trace is reproduced as `FAIL` for every transcript
  (`PCS.V2.ExecutableLimits.certifiedTag_fails_unsafe`), so it passes the replay stage.
* Deployed-world safety needs `FaithfulLog` (`committed_safe_deployed_unsafe`, existing);
  with it, `executableAuthority_deployed_trace_safe` transfers the bridge to a deployed run.
-/

set_option autoImplicit false

namespace PCS.V2.ExecutableGeneral

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.Package
open PCS.V2.CertificateModel PCS.V2.Index PCS.V2.Zip PCS.V2.Archive PCS.V2.Checkers
open PCS.V2.DomainAuthority PCS.V2.Witnesses PCS.V2.Witnesses.AISafety PCS.V2.PKPDCheck
open PCS.V2.DomainAdapter PCS.V2.ClaimGraph PCS.V2.AuthorityCLI PCS.V2.Signature
open PCS.V2.FailClosed (verifyPackage_cert)

/-! ## Pure stages recovered from acceptance -/

/-- The pure parsing facts behind an acceptance: the certificate parses, its model decodes,
    and the artifact table is built from the delivered files. -/
theorem acceptPCSWithCheckers_stages {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSWithCheckers cs t T inp = some r) :
    verifyCertBytes inp.certificateBytes = some r.pkg.cert ∧
    decodeCertModel r.pkg.cert = some r.model ∧
    artifactTable r.model inp.files = some r.table ∧
    replayOK (authorityOraclesWith cs t).exec r.pkg.cert r.model r.table = true := by
  have hs := acceptPCS_sound (acceptPCSWithCheckers_spec h).1
  obtain ⟨pr, hpr⟩ : ∃ pr, verifyPackage (authorityOraclesWith cs t).unicode
      (authorityOraclesWith cs t).ed25519 T.pk T.expected inp = some pr ∧ pr = r.pkg := by
    have h1 := (acceptPCSWithCheckers_spec h).1
    unfold acceptPCS at h1
    split at h1
    · cases h1
    · rename_i pr hpr
      refine ⟨pr, hpr, ?_⟩
      repeat' (first | (split at h1) | (cases h1; rfl) | cases h1)
  obtain ⟨hv, rfl⟩ := hpr
  exact ⟨verifyPackage_cert hv, hs.model, hs.table, hs.replay⟩

/-! ## Domain-independent bridge: registered certified checkers -/

/-- **Package level.**  If the certified extended authority accepts a package, every
    `PASS`-recorded evidence item whose tag is that of a registered checker `k` satisfies
    `k`'s soundness proposition on the committed artifact table. -/
theorem certified_registered_evidence_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSWithCheckers certifiedRegistry t T inp = some r)
    {k : DomainChecker} (hk : k ∈ productionCheckers)
    {e : CertEvidence} (he : e ∈ r.model.evidence) (hpass : e.outcome = .pass)
    (ht : isCheckType k.tag e.json = true) :
    k.Holds (requestFor r.pkg.cert r.model r.table e) := by
  obtain ⟨_, _, _, hrep⟩ := acceptPCSWithCheckers_stages h
  have hobs := replayOK_spec hrep e he
  have hv := authorityWith_faithful certifiedRegistry
    (replayFaithful_reported (transcriptExecutor t)) (requestFor r.pkg.cert r.model r.table e)
    (by rw [hobs, hpass])
  exact registry_valid productionCheckers_registered hk ht hv

/-- Acceptance of the raw `--zip` path, unfolded to its pure stages. -/
theorem certifiedAuthority_stages {t : AuthorityTranscript} {T : TrustAnchor} {raw : ByteArray}
    {inp : PackageInput} {r : AcceptedResult}
    (h : certifiedAuthority t T raw = some (inp, r)) :
    ∃ es, decodeZip raw = some es ∧ fromArchiveEntries es = some inp ∧
      acceptPCSWithCheckers certifiedRegistry t T inp = some r := by
  obtain ⟨es, hz, hi, hp⟩ := certifiedAuthority_spec h
  exact ⟨es, hz, hi, (certifiedPCS_spec hp).1⟩

/-- **Domain-independent executable bridge.**  For *every* raw archive, transcript and
    trust anchor: if `pcs-lean-authority --zip` prints `ACCEPT`, then for every registered
    certified checker `k` and every evidence item the signed certificate records as `PASS`
    with tag `k.tag`, `k`'s soundness proposition holds of the committed artifact table.
    No cryptographic hypothesis, no hypothesis about the transcript. -/
theorem executableAuthority_registered_evidence_sound {t : AuthorityTranscript}
    {T : TrustAnchor} {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ es inp r, decodeZip raw = some es ∧ CanonicalZip raw es ∧
      fromArchiveEntries es = some inp ∧ certifiedAuthority t T raw = some (inp, r) ∧
      verifyCertBytes inp.certificateBytes = some r.pkg.cert ∧
      decodeCertModel r.pkg.cert = some r.model ∧
      artifactTable r.model inp.files = some r.table ∧
      ∀ k ∈ productionCheckers, ∀ e ∈ r.model.evidence, e.outcome = .pass →
        isCheckType k.tag e.json = true → k.Holds (requestFor r.pkg.cert r.model r.table e) := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  obtain ⟨es, hz, hi, ha⟩ := certifiedAuthority_stages hr
  obtain ⟨hc, hm, htab, _⟩ := acceptPCSWithCheckers_stages ha
  exact ⟨es, inp, r, hz, decodeZip_sound hz, hi, hr, hc, hm, htab,
    fun k hk e he hp ht => certified_registered_evidence_sound ha hk he hp ht⟩

/-! ## AI-safety specialisation: the trace invariant on the archived member bytes -/

theorem traceChecker_mem : traceChecker ∈ productionCheckers := by
  simp [productionCheckers, Instances.witnessRegistry]

/-- A member of the filtered package files is a member of the archive entries. -/
theorem lookup_files_mem {es : List (String × ByteArray)} {inp : PackageInput}
    (hi : fromArchiveEntries es = some inp) {p : String} {b : ByteArray}
    (hl : lookup inp.files p = some b) : (p, b) ∈ es := by
  have hm := lookup_mem hl
  rw [(fromArchiveEntries_sound hi).files] at hm
  exact (List.mem_filter.mp hm).1

/-- **Package level, AI safety.**  Every `PASS` `trace_invariant` evidence item of an
    accepted package names (via its `check_spec`) an artifact `a`, budget `b` and forbidden
    action `f`, and the certificate artifact `a`'s delivered member bytes — bound by the
    certificate's SHA-256 digest — satisfy `TraceSafe · b f`. -/
theorem certified_trace_evidence_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSWithCheckers certifiedRegistry t T inp = some r)
    {e : CertEvidence} (he : e ∈ r.model.evidence) (hpass : e.outcome = .pass)
    (ht : isCheckType "trace_invariant" e.json = true) :
    ∃ a b f, parseTrace e.json = some (a, b, f) ∧
      ∃ art ∈ r.model.artifacts, ∃ bytes, art.id = a ∧ lookup inp.files art.path = some bytes ∧
        PCS.V2.SHA256.sha256 bytes.data.toList = art.sha256 ∧ TraceSafe bytes.data.toList b f := by
  obtain ⟨_, _, htab, _⟩ := acceptPCSWithCheckers_stages h
  obtain ⟨⟨a, b, f⟩, hx, tr, htr, hsafe⟩ :=
    certified_registered_evidence_sound h traceChecker_mem he hpass ht
  refine ⟨a, b, f, hx, ?_⟩
  simp only [requestFor, artBytes] at htr
  obtain ⟨y, hy, rfl⟩ := Option.map_eq_some_iff.mp htr
  obtain ⟨art, hart, hid, hl, hd⟩ := artifactTable_spec htab (a, y) (lookup_mem hy)
  exact ⟨art, hart, y, hid, hl, hd, hsafe⟩

/-- **The executable bridge for AI safety (zip mode).**  For every raw byte string `raw`,
    every transcript `t` and every trust anchor `T` (any key, any pin): if the function whose
    verdict `pcs-lean-authority --zip` prints returns `ACCEPT`, then `raw` is a canonical ZIP
    with members `es`, and for every evidence item that the parsed signed certificate records
    as `PASS` with `check_spec.type = "trace_invariant"` and parameters `(a, b, f)`, the
    member of `es` that holds certificate artifact `a` has bytes satisfying the bounded
    invariant `TraceSafe · b f` (no action `f`, cumulative risk ≤ `b` after every step).

    Hypotheses: none.  In particular no `NoForgery` (the conclusion is about the committed
    bytes, not about who signed them) and no `FaithfulLog` (it is about the committed trace,
    not a deployed run). -/
theorem executableAuthority_trace_evidence_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ es inp c m, decodeZip raw = some es ∧ CanonicalZip raw es ∧
      fromArchiveEntries es = some inp ∧ verifyCertBytes inp.certificateBytes = some c ∧
      decodeCertModel c = some m ∧
      ∀ e ∈ m.evidence, e.outcome = .pass → isCheckType "trace_invariant" e.json = true →
        ∃ a b f, parseTrace e.json = some (a, b, f) ∧
          ∃ art ∈ m.artifacts, ∃ bytes, art.id = a ∧ (art.path, bytes) ∈ es ∧
            PCS.V2.SHA256.sha256 bytes.data.toList = art.sha256 ∧
            TraceSafe bytes.data.toList b f := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  obtain ⟨es, hz, hi, ha⟩ := certifiedAuthority_stages hr
  obtain ⟨hc, hm, _, _⟩ := acceptPCSWithCheckers_stages ha
  refine ⟨es, inp, r.pkg.cert, r.model, hz, decodeZip_sound hz, hi, hc, hm, ?_⟩
  intro e he hp ht
  obtain ⟨a, b, f, hx, art, hart, bytes, hid, hl, hd, hs⟩ := certified_trace_evidence_sound ha he hp ht
  exact ⟨a, b, f, hx, art, hart, bytes, hid, lookup_files_mem hi hl, hd, hs⟩

/-- **Directory mode.**  The same bridge for `pcs-lean-authority <dir>` on any list of
    collected entries. -/
theorem executableAuthorityEntries_trace_evidence_sound {t : AuthorityTranscript}
    {T : TrustAnchor} {es : List (String × ByteArray)}
    (h : executableAuthorityEntries t T es = "ACCEPT") :
    ∃ inp c m, fromArchiveEntries es = some inp ∧ verifyCertBytes inp.certificateBytes = some c ∧
      decodeCertModel c = some m ∧
      ∀ e ∈ m.evidence, e.outcome = .pass → isCheckType "trace_invariant" e.json = true →
        ∃ a b f, parseTrace e.json = some (a, b, f) ∧
          ∃ art ∈ m.artifacts, ∃ bytes, art.id = a ∧ (art.path, bytes) ∈ es ∧
            PCS.V2.SHA256.sha256 bytes.data.toList = art.sha256 ∧
            TraceSafe bytes.data.toList b f := by
  obtain ⟨inp, r, hi, ha⟩ := (executableAuthorityEntries_refines_certifiedAuthority t T es).mp h
  replace ha := (certifiedPCS_spec ha).1
  obtain ⟨hc, hm, _, _⟩ := acceptPCSWithCheckers_stages ha
  refine ⟨inp, r.pkg.cert, r.model, hi, hc, hm, ?_⟩
  intro e he hp ht
  obtain ⟨a, b, f, hx, art, hart, bytes, hid, hl, hd, hs⟩ := certified_trace_evidence_sound ha he hp ht
  exact ⟨a, b, f, hx, art, hart, bytes, hid, lookup_files_mem hi hl, hd, hs⟩

/-- **Command-line form.**  For every archive file content, transcript file content, base64
    key string and optional fingerprint: if the line printed by `pcs-lean-authority --zip` is
    `ACCEPT`, the transcript bytes decode, and the trace bridge holds for the raw bytes. -/
theorem zipModeOutput_trace_evidence_sound {archive transcript : ByteArray} {keyB64 : String}
    {fp : Option String} (h : zipModeOutput archive transcript keyB64 fp = some "ACCEPT") :
    ∃ t es inp c m, decodeAuthorityTranscriptBytes transcript = some t ∧
      executableAuthority t (cliAnchor keyB64 fp) archive = "ACCEPT" ∧
      decodeZip archive = some es ∧ CanonicalZip archive es ∧
      fromArchiveEntries es = some inp ∧ verifyCertBytes inp.certificateBytes = some c ∧
      decodeCertModel c = some m ∧
      ∀ e ∈ m.evidence, e.outcome = .pass → isCheckType "trace_invariant" e.json = true →
        ∃ a b f, parseTrace e.json = some (a, b, f) ∧
          ∃ art ∈ m.artifacts, ∃ bytes, art.id = a ∧ (art.path, bytes) ∈ es ∧
            PCS.V2.SHA256.sha256 bytes.data.toList = art.sha256 ∧
            TraceSafe bytes.data.toList b f := by
  obtain ⟨t, ht, hacc⟩ := (zipModeOutput_accept_iff archive transcript keyB64 fp).mp h
  obtain ⟨es, inp, c, m, h1, h2, h3, h4, h5, h6⟩ := executableAuthority_trace_evidence_sound hacc
  exact ⟨t, es, inp, c, m, ht, hacc, h1, h2, h3, h4, h5, h6⟩

/-! ## Rejection: the contrapositive in pre-acceptance terms -/

/-- **Package level rejection.**  If the delivered certificate parses to a model recording a
    `PASS` `trace_invariant` evidence item with parameters `(a, b, f)`, and every delivered
    file that a certificate artifact with id `a` points to violates `TraceSafe · b f`, then
    the certified authority rejects — for every transcript and every trust anchor. -/
theorem certified_rejects_unsafe_trace_evidence {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence) (hpass : e.outcome = .pass)
    (ht : isCheckType "trace_invariant" e.json = true)
    {a : String} {b f : Nat} (hp : parseTrace e.json = some (a, b, f))
    (hunsafe : ∀ art ∈ m.artifacts, art.id = a → ∀ bytes,
      lookup inp.files art.path = some bytes → ¬ TraceSafe bytes.data.toList b f)
    (t : AuthorityTranscript) (T : TrustAnchor) :
    acceptPCSWithCheckers certifiedRegistry t T inp = none := by
  cases hr : acceptPCSWithCheckers certifiedRegistry t T inp with
  | none => rfl
  | some r =>
    exfalso
    obtain ⟨hc', hm', _, _⟩ := acceptPCSWithCheckers_stages hr
    rw [hc] at hc'; cases hc'
    rw [hm] at hm'; cases hm'
    obtain ⟨a', b', f', hx, art, hart, bytes, hid, hl, _, hs⟩ :=
      certified_trace_evidence_sound hr he hpass ht
    rw [hp] at hx
    cases hx
    exact hunsafe art hart hid bytes hl hs

/-- **Zip-mode rejection (executable).**  For every raw byte string that decodes to members
    whose certificate records a `PASS` `trace_invariant` evidence item over a member whose
    bytes violate the declared invariant, `pcs-lean-authority --zip` does **not** print
    `ACCEPT` — for every transcript and every trust anchor, hence regardless of signatures,
    signer, or key. -/
theorem executableAuthority_rejects_unsafe_trace_evidence {raw : ByteArray}
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hz : decodeZip raw = some es) (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence) (hpass : e.outcome = .pass)
    (ht : isCheckType "trace_invariant" e.json = true)
    {a : String} {b f : Nat} (hp : parseTrace e.json = some (a, b, f))
    (hunsafe : ∀ art ∈ m.artifacts, art.id = a → ∀ bytes,
      lookup inp.files art.path = some bytes → ¬ TraceSafe bytes.data.toList b f)
    (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthority t T raw ≠ "ACCEPT" := by
  intro h
  obtain ⟨inp', r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  obtain ⟨es', hz', hi', ha⟩ := certifiedAuthority_stages hr
  rw [hz] at hz'; cases hz'
  rw [hi] at hi'; cases hi'
  rw [certified_rejects_unsafe_trace_evidence hc hm he hpass ht hp hunsafe t T] at ha
  cases ha

/-- **Directory-mode rejection (executable).** -/
theorem executableAuthorityEntries_rejects_unsafe_trace_evidence
    {es : List (String × ByteArray)} {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence) (hpass : e.outcome = .pass)
    (ht : isCheckType "trace_invariant" e.json = true)
    {a : String} {b f : Nat} (hp : parseTrace e.json = some (a, b, f))
    (hunsafe : ∀ art ∈ m.artifacts, art.id = a → ∀ bytes,
      lookup inp.files art.path = some bytes → ¬ TraceSafe bytes.data.toList b f)
    (t : AuthorityTranscript) (T : TrustAnchor) :
    executableAuthorityEntries t T es ≠ "ACCEPT" := by
  intro h
  obtain ⟨inp', r, hi', ha⟩ := (executableAuthorityEntries_refines_certifiedAuthority t T es).mp h
  replace ha := (certifiedPCS_spec ha).1
  rw [hi] at hi'; cases hi'
  rw [certified_rejects_unsafe_trace_evidence hc hm he hpass ht hp hunsafe t T] at ha
  cases ha

end PCS.V2.ExecutableGeneral

namespace PCS.V2.ExecutableGeneral

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.Package
open PCS.V2.CertificateModel PCS.V2.Index PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses
open PCS.V2.Witnesses.AISafety PCS.V2.PKPDCheck PCS.V2.DomainAdapter

/-- The adapter's leaf check for a `safe` node is exactly "certified tag and matching
    parameters". -/
theorem aiLeafCheck_spec {ev : JVal} {a : String} {b f : Nat}
    (h : aiAdapter.leafCheck ev (.safe a b f) = true) :
    isCheckType "trace_invariant" ev = true ∧ parseTrace ev = some (a, b, f) := by
  simp only [aiAdapter, decide_eq_true_eq, traceNodeOf] at h
  split at h
  · rename_i ht
    obtain ⟨x, hx, hxe⟩ := Option.map_eq_some_iff.mp h
    obtain ⟨a', b', f'⟩ := x
    simp only [TraceIR.safe.injEq] at hxe
    obtain ⟨rfl, rfl, rfl⟩ := hxe
    exact ⟨ht, hx⟩
  · cases h

/-- **Claim-level executable bridge (graph-free).**  For every raw archive, transcript and
    trust anchor: if `pcs-lean-authority --zip` prints `ACCEPT`, then for every certificate
    claim whose signed predicate decodes (by the AI-safety adapter) to a trace claim `tc`, and
    every trace `a` of `tc` that is covered by a `PASS`-recorded evidence item accepted by the
    adapter's leaf check for "trace `a` is safe for `tc.budget`, `tc.forbidden`", the archived
    member bytes of `a` satisfy that invariant.  If every trace of `tc` is so covered, the
    domain proposition `aiDomain.Holds` holds of the committed artifact table.

    Relation to `executableAuthority_domain_sound`: that theorem concludes the same for
    claims accepted with an arbitrary (untrusted) obligation graph; this one needs no graph,
    because the coverage condition is stated directly on the signed certificate. -/
theorem executableAuthority_trace_claim_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ es inp r, decodeZip raw = some es ∧ fromArchiveEntries es = some inp ∧
      certifiedAuthority t T raw = some (inp, r) ∧
      ∀ cl ∈ r.model.claims, ∀ tc, aiAdapter.decode cl.predicate = some tc →
        (∀ a ∈ tc.traces, (∃ e ∈ r.model.evidence, e.outcome = .pass ∧
            aiAdapter.leafCheck e.json (.safe a tc.budget tc.forbidden) = true) →
          ∃ art ∈ r.model.artifacts, ∃ bytes, art.id = a ∧ (art.path, bytes) ∈ es ∧
            TraceSafe bytes.data.toList tc.budget tc.forbidden) ∧
        ((∀ a ∈ tc.traces, ∃ e ∈ r.model.evidence, e.outcome = .pass ∧
            aiAdapter.leafCheck e.json (.safe a tc.budget tc.forbidden) = true) →
          aiDomain.Holds r.table tc) := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  obtain ⟨es, hz, hi, ha⟩ := certifiedAuthority_stages hr
  refine ⟨es, inp, r, hz, hi, hr, fun cl _ tc _ => ⟨?_, ?_⟩⟩
  · intro a _ ⟨e, he, hp, hl⟩
    obtain ⟨ht, hx⟩ := aiLeafCheck_spec hl
    obtain ⟨a', b', f', hx', art, hart, bytes, hid, hlk, _, hs⟩ :=
      certified_trace_evidence_sound ha he hp ht
    rw [hx] at hx'
    cases hx'
    exact ⟨art, hart, bytes, hid, lookup_files_mem hi hlk, hs⟩
  · intro hcov a ha'
    obtain ⟨e, he, hp, hl⟩ := hcov a ha'
    obtain ⟨ht, hx⟩ := aiLeafCheck_spec hl
    obtain ⟨⟨a', b', f'⟩, hx', tr, htr, hs⟩ :=
      certified_registered_evidence_sound ha traceChecker_mem he hp ht
    change parseTrace e.json = some (a', b', f') at hx'
    rw [hx] at hx'
    cases hx'
    exact ⟨tr, htr, hs⟩

/-- **Deployed-run form (needs `FaithfulLog`).**  For every raw archive, transcript and trust
    anchor: if `pcs-lean-authority --zip` prints `ACCEPT`, then for every deployed run `ew`
    that the committed artifact table faithfully logs, every `PASS` `trace_invariant` evidence
    item's parameters `(a, b, f)` describe a deployed episode `a` satisfying `TraceSafe · b f`.
    `FaithfulLog` is an explicit premise about the world; it is not checked by PCS and cannot
    be dropped (`committed_safe_deployed_unsafe`). -/
theorem executableAuthority_deployed_trace_safe {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      ∀ ew : DeployedRun, FaithfulLog r.table ew →
        ∀ e ∈ r.model.evidence, e.outcome = .pass → isCheckType "trace_invariant" e.json = true →
          ∃ a b f, parseTrace e.json = some (a, b, f) ∧
            ∃ tr, ew.episode a = some tr ∧ TraceSafe tr b f := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  obtain ⟨es, _, _, ha⟩ := certifiedAuthority_stages hr
  refine ⟨inp, r, hr, fun ew hlog e he hp ht => ?_⟩
  obtain ⟨⟨a, b, f⟩, hx, tr, htr, hs⟩ :=
    certified_registered_evidence_sound ha traceChecker_mem he hp ht
  exact ⟨a, b, f, hx, tr, hlog a tr htr, hs⟩

end PCS.V2.ExecutableGeneral
