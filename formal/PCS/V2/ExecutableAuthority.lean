import PCS.V2.FailClosedProofs

/-!
# The executable authority runs the certified domain-checker registry

`pcs-lean-authority` (`PCSAuthority.lean`) now prints the verdict of
`executableAuthority` (raw `--zip` mode) / `executableAuthorityEntries` (directory mode).
Both run the **extended certified authority** `acceptArchiveWithCheckers cs` of
`PCS.V2.DomainAuthority`, where `cs` is built by the fail-closed registration function
`buildRegistry` from the production domain-checker list `productionCheckers`
(computational biology `residue_bounds`, `hydrophobic_score`; AI safety `trace_invariant`).

* `buildRegistry` accepts a list of `DomainChecker`s only if their tags are pairwise distinct
  and disjoint from the six built-in tags (`buildRegistry_eq_some_iff`); otherwise it returns
  `none` and the executable rejects **every** archive with stage `checker_registry`
  (`executableAuthorityWith_dup`).  A `DomainChecker` carries its soundness theorem as a
  field, so a checker without a formal soundness proof cannot even be written down.
* The six built-in checkers keep priority, so their meaning is unchanged
  (`executor_builtin_unchanged`); a request handled by no registered checker is executed
  exactly as by the production authority (`executor_unhandled_unchanged`).
* With an empty registry every executable `ACCEPT` is a production `ACCEPT`
  (`executableAuthorityWith_nil`); the converse fails exactly for transcript-trusted kinds.
* **Fail closed (current behaviour).**  The executed functions run the *strict* authority of
  `PCS.V2.FailClosed`: an evidence item whose `check_spec.type` is missing or unregistered is
  rejected before replay (stage `unsupported_check_type`), whatever the transcript reports;
  supported claims of registered domains must be bound by their own certified evidence
  (stage `claim_binding`); the replay fallback is the constant-`FAIL` executor, so transcript
  replay reports are never used as outcomes.  The earlier transcript-fallback extended
  authority (`acceptArchiveWithCheckers`) is kept as an analysis object: strict acceptance
  implies it (`certifiedAuthority_extended`), so its theorems still apply.
* `executableAuthority_refines_certifiedAuthority`: the executed function prints `ACCEPT`
  **iff** the certified strict authority `certifiedAuthority` accepts.
* `executableAuthority_sound`: `ACCEPT` ⇒ frontier-strength `ExtendedAssurance` plus the
  AI-safety and biology domain propositions for every domain-accepted claim, with
  `NoForgery` as the only hypothesis.
-/

set_option autoImplicit false

namespace PCS.V2.DomainAuthority

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Archive PCS.V2.Authority PCS.V2.HighAssurance
open PCS.V2.Zip PCS.V2.TCB PCS.V2.Package PCS.V2.CanonicalArchive PCS.V2.Replay PCS.V2.Signature
open PCS.V2.Checkers PCS.V2.CertificateModel PCS.V2.DomainAdapter PCS.V2.ClaimGraph
open PCS.V2.Index PCS.V2.Witnesses PCS.V2.PKPDCheck

/-! ## Oracle-generic transcript-gated acceptance and its diagnostic mirror -/

/-- Transcript-gated acceptance for arbitrary oracles. -/
def acceptPCSGated (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : Option AcceptedResult :=
  match acceptPCS O T inp with
  | none => none
  | some r => if transcriptCovers t r then some r else none

/-- Fail-closed diagnostic mirror of `acceptPCSGated` (same body as
    `diagnosePCSWithTranscript`, for arbitrary oracles). -/
def diagnosePCSGated (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : String :=
  match verifyPackage O.unicode O.ed25519 T.pk T.expected inp with
  | none => "package"
  | some pr =>
    match decodeCertModel pr.cert with
    | none => "certificate_model"
    | some m =>
      match envStage O.capture pr.cert m inp.files with
      | none => "environment"
      | some _ =>
        if O.workflow (.obj pr.cert.members) inp.files then
          match artifactTable m inp.files with
          | none => "artifact_table"
          | some table =>
            if replayOK O.exec pr.cert m table then
              match verifyNormalizedSet inp.files with
              | none => "normalized_set"
              | some (i, ps) =>
                if normalizedOK pr.cert m i ps then
                  let r : AcceptedResult :=
                    { pkg := pr, model := m, table := table,
                      env := (envStage O.capture pr.cert m inp.files).getD none,
                      index := i, claims := ps }
                  if transcriptCovers t r then "ACCEPT" else "transcript_binding"
                else "normalized"
            else "replay"
        else "workflow"

theorem diagnosePCSWithTranscript_eq_gated (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) :
    diagnosePCSWithTranscript t T inp = diagnosePCSGated (transcriptOracles t) t T inp := rfl

theorem acceptPCSWithTranscript_eq_gated (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) :
    acceptPCSWithTranscript t T inp = acceptPCSGated (transcriptOracles t) t T inp := rfl

theorem acceptPCSWithCheckers_eq_gated (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (inp : PackageInput) :
    acceptPCSWithCheckers cs t T inp = acceptPCSGated (authorityOraclesWith cs t) t T inp := rfl

/-- The diagnostic mirror prints `ACCEPT` exactly when gated acceptance succeeds. -/
theorem diagnosePCSGated_accept_iff (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) :
    diagnosePCSGated O t T inp = "ACCEPT" ↔ ∃ r, acceptPCSGated O t T inp = some r := by
  unfold diagnosePCSGated acceptPCSGated acceptPCS
  cases hpr : verifyPackage O.unicode O.ed25519 T.pk T.expected inp with
  | none => simp
  | some pr =>
    simp only
    cases hm : decodeCertModel pr.cert with
    | none => simp
    | some m =>
      simp only
      cases henv : envStage O.capture pr.cert m inp.files with
      | none => simp
      | some env =>
        simp only [Option.getD_some]
        by_cases hw : O.workflow (.obj pr.cert.members) inp.files = true
        · rw [if_pos hw, if_pos hw]
          cases htab : artifactTable m inp.files with
          | none => simp
          | some table =>
            simp only
            by_cases hrep : replayOK O.exec pr.cert m table = true
            · rw [if_pos hrep, if_pos hrep]
              cases hset : verifyNormalizedSet inp.files with
              | none => simp
              | some ip =>
                obtain ⟨i, ps⟩ := ip
                simp only
                by_cases hn : normalizedOK pr.cert m i ps = true
                · rw [if_pos hn, if_pos hn]
                  by_cases hcov : transcriptCovers t
                      { pkg := pr, model := m, table := table, env := env, index := i,
                        claims := ps } = true
                  · simp [hcov]
                  · simp [hcov]
                · simp [hn]
            · simp [hrep]
        · simp [hw]

/-- Raw-archive gated acceptance for arbitrary oracles. -/
def acceptArchiveGated (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) : Option (PackageInput × AcceptedResult) :=
  match decodeZip raw with
  | none => none
  | some es =>
    match fromArchiveEntries es with
    | none => none
    | some inp => (acceptPCSGated O t T inp).map (inp, ·)

/-- Raw-archive diagnostic mirror for arbitrary oracles. -/
def diagnoseArchiveGated (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) : String :=
  match decodeZip raw with
  | none => "canonical_archive"
  | some es =>
    match fromArchiveEntries es with
    | none => "archive_partition"
    | some inp => diagnosePCSGated O t T inp

theorem diagnoseArchiveGated_accept_iff (O : Oracles) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) :
    diagnoseArchiveGated O t T raw = "ACCEPT" ↔
      ∃ inp r, acceptArchiveGated O t T raw = some (inp, r) := by
  unfold diagnoseArchiveGated acceptArchiveGated
  cases decodeZip raw with
  | none => simp
  | some es =>
    simp only
    cases hinp : fromArchiveEntries es with
    | none => simp
    | some inp =>
      simp only
      rw [diagnosePCSGated_accept_iff]
      constructor
      · rintro ⟨r, hr⟩; exact ⟨inp, r, by simp [hr]⟩
      · rintro ⟨inp', r, hr⟩
        cases h : acceptPCSGated O t T inp with
        | none => rw [h] at hr; cases hr
        | some r' => exact ⟨r', rfl⟩

theorem diagnoseArchiveWithTranscript_eq_gated (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) :
    diagnoseArchiveWithTranscript t T raw = diagnoseArchiveGated (transcriptOracles t) t T raw :=
  rfl

theorem acceptArchiveWithCheckers_eq_gated (cs : List CertifiedChecker)
    (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    acceptArchiveWithCheckers cs t T raw = acceptArchiveGated (authorityOraclesWith cs t) t T raw :=
  rfl

/-! ## The extended diagnostic verdicts -/

/-- Verdict of the extended authority on a materialised package. -/
def diagnosePCSWithCheckers (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (inp : PackageInput) : String :=
  diagnosePCSGated (authorityOraclesWith cs t) t T inp

/-- Verdict of the extended authority on raw canonical archive bytes. -/
def diagnoseArchiveWithCheckers (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) : String :=
  diagnoseArchiveGated (authorityOraclesWith cs t) t T raw

theorem diagnoseArchiveWithCheckers_accept_iff (cs : List CertifiedChecker)
    (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    diagnoseArchiveWithCheckers cs t T raw = "ACCEPT" ↔
      ∃ inp r, acceptArchiveWithCheckers cs t T raw = some (inp, r) :=
  diagnoseArchiveGated_accept_iff _ t T raw

theorem diagnosePCSWithCheckers_accept_iff (cs : List CertifiedChecker)
    (t : AuthorityTranscript) (T : TrustAnchor) (inp : PackageInput) :
    diagnosePCSWithCheckers cs t T inp = "ACCEPT" ↔
      ∃ r, acceptPCSWithCheckers cs t T inp = some r :=
  diagnosePCSGated_accept_iff _ t T inp

/-- Empty registry: the extended verdict is literally the production verdict. -/
theorem diagnoseArchiveWithCheckers_nil (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) :
    diagnoseArchiveWithCheckers [] t T raw = diagnoseArchiveWithTranscript t T raw := by
  simp only [diagnoseArchiveWithCheckers, authorityOraclesWith_nil]; rfl

theorem diagnosePCSWithCheckers_nil (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) :
    diagnosePCSWithCheckers [] t T inp = diagnosePCSWithTranscript t T inp := by
  simp only [diagnosePCSWithCheckers, authorityOraclesWith_nil]; rfl

/-! ## Fail-closed registration -/

/-- Decidable registration conditions. -/
def registeredB (ks : List DomainChecker) : Bool :=
  decide ((ks.map (·.tag)).Nodup) && ks.all (fun k => !(builtinTypes.contains k.tag))

theorem registeredB_iff (ks : List DomainChecker) : registeredB ks = true ↔ Registered ks := by
  constructor
  · intro h
    simp only [registeredB, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true] at h
    refine ⟨h.1, fun k hk => ?_⟩
    have := h.2 k hk
    simpa using this
  · intro hr
    simp only [registeredB, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true]
    refine ⟨hr.nodup, fun k hk => ?_⟩
    simpa using hr.notBuiltin k hk

/-- **Fail-closed registration.**  Only checkers whose tags are pairwise distinct and not
    built-in are turned into an authority registry. -/
def buildRegistry (ks : List DomainChecker) : Option (List CertifiedChecker) :=
  if registeredB ks then some (registry ks) else none

theorem buildRegistry_eq_some_iff {ks : List DomainChecker} {cs : List CertifiedChecker} :
    buildRegistry ks = some cs ↔ Registered ks ∧ cs = registry ks := by
  unfold buildRegistry
  by_cases h : registeredB ks = true
  · simp only [h, if_true, Option.some.injEq]
    exact ⟨fun e => ⟨(registeredB_iff ks).mp h, e.symm⟩, fun ⟨_, e⟩ => e.symm⟩
  · rw [if_neg h]
    constructor
    · intro e; cases e
    · rintro ⟨hr, _⟩; exact absurd ((registeredB_iff ks).mpr hr) h

/-- Duplicate checker tags make registration fail. -/
theorem buildRegistry_dup_none {ks : List DomainChecker} (h : ¬ (ks.map (·.tag)).Nodup) :
    buildRegistry ks = none := by
  cases hb : buildRegistry ks with
  | none => rfl
  | some cs => exact absurd (buildRegistry_eq_some_iff.mp hb).1.nodup h

/-- A checker claiming a built-in tag makes registration fail (no shadowing of the six
    verified built-ins). -/
theorem buildRegistry_builtin_none {ks : List DomainChecker} {k : DomainChecker}
    (hk : k ∈ ks) (ht : k.tag ∈ builtinTypes) : buildRegistry ks = none := by
  cases hb : buildRegistry ks with
  | none => rfl
  | some cs => exact absurd ht ((buildRegistry_eq_some_iff.mp hb).1.notBuiltin k hk)

/-! ## The function executed by `pcs-lean-authority` -/

/-- The production domain checkers executed by `pcs-lean-authority`. -/
def productionCheckers : List DomainChecker := Instances.witnessRegistry

/-- Executable verdict for a given checker list (raw `--zip` mode).  Runs the **strict,
    fail-closed** authority of `PCS.V2.FailClosed`: unregistered check types are rejected
    before replay (stage `unsupported_check_type`), supported claims of registered domains
    must be bound by their own certified evidence (stage `claim_binding`), and the replay
    fallback is the constant-`FAIL` executor `failClosedExec` — the transcript's replay
    reports are never used as outcomes. -/
def executableAuthorityWith (ks : List DomainChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) : String :=
  match buildRegistry ks with
  | none => "checker_registry"
  | some cs => FailClosed.diagnoseArchiveStrictWith FailClosed.failClosedExec cs
      FailClosed.productionBinders t T raw

/-- Executable verdict for a given checker list (materialised-directory mode); the same
    strict authority as `executableAuthorityWith`. -/
def executableAuthorityEntriesWith (ks : List DomainChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (entries : List (String × ByteArray)) : String :=
  match buildRegistry ks with
  | none => "checker_registry"
  | some cs =>
    match fromArchiveEntries entries with
    | none => "archive_partition"
    | some inp => FailClosed.diagnosePCSStrictWith FailClosed.failClosedExec cs
        FailClosed.productionBinders t T inp

/-- **The function whose verdict `pcs-lean-authority --zip` prints.** -/
def executableAuthority (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) : String :=
  executableAuthorityWith productionCheckers t T raw

/-- **The function whose verdict `pcs-lean-authority <dir>` prints.** -/
def executableAuthorityEntries (t : AuthorityTranscript) (T : TrustAnchor)
    (entries : List (String × ByteArray)) : String :=
  executableAuthorityEntriesWith productionCheckers t T entries

/-- The certified registry of the executable. -/
def certifiedRegistry : List CertifiedChecker := registry productionCheckers

/-- **The certified strict authority on a materialised package** (stated with the
    transcript as replay fallback so that every theorem about the extended authority
    applies; the fallback is irrelevant, `FailClosed.acceptPCSStrictWith_fallback_irrelevant`). -/
def certifiedPCS (t : AuthorityTranscript) (T : TrustAnchor) (inp : PackageInput) :
    Option AcceptedResult :=
  FailClosed.acceptPCSStrictWith (transcriptExecutor t) certifiedRegistry
    FailClosed.productionBinders t T inp

/-- **The certified strict authority on raw archive bytes.** -/
def certifiedAuthority (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    Option (PackageInput × AcceptedResult) :=
  FailClosed.acceptArchiveStrictWith (transcriptExecutor t) certifiedRegistry
    FailClosed.productionBinders t T raw

theorem productionCheckers_registered : Registered productionCheckers :=
  Instances.witnessRegistry_registered

theorem buildRegistry_production : buildRegistry productionCheckers = some certifiedRegistry :=
  buildRegistry_eq_some_iff.mpr ⟨productionCheckers_registered, rfl⟩

/-- Strict acceptance implies acceptance by the earlier extended authority, plus both gates. -/
theorem certifiedPCS_spec {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : certifiedPCS t T inp = some r) :
    acceptPCSWithCheckers certifiedRegistry t T inp = some r ∧
      FailClosed.supportedEvidenceB certifiedRegistry r.pkg.cert r.model r.table = true ∧
      FailClosed.claimsBoundB FailClosed.productionBinders r = true :=
  FailClosed.acceptPCSStrictWith_transcript_spec h

theorem certifiedAuthority_spec {t : AuthorityTranscript} {T : TrustAnchor} {raw : ByteArray}
    {inp : PackageInput} {r : AcceptedResult} (h : certifiedAuthority t T raw = some (inp, r)) :
    ∃ es, decodeZip raw = some es ∧ fromArchiveEntries es = some inp ∧
      certifiedPCS t T inp = some r := by
  unfold certifiedAuthority FailClosed.acceptArchiveStrictWith at h
  split at h
  · cases h
  · rename_i es hes
    split at h
    · cases h
    · rename_i inp' hinp
      cases hr : certifiedPCS t T inp' with
      | none => simp only [certifiedPCS] at hr; rw [hr] at h; cases h
      | some r' =>
        simp only [certifiedPCS] at hr
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        exact ⟨es, hes, hinp, hr⟩

/-- The raw-archive certified strict authority implies the earlier extended authority. -/
theorem certifiedAuthority_extended {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : certifiedAuthority t T raw = some (inp, r)) :
    acceptArchiveWithCheckers certifiedRegistry t T raw = some (inp, r) := by
  obtain ⟨es, hz, hi, hp⟩ := certifiedAuthority_spec h
  simp only [acceptArchiveWithCheckers, hz, hi, (certifiedPCS_spec hp).1, Option.map_some]

/-- The executed function is the strict diagnostic verdict for the certified registry. -/
theorem executableAuthority_eq (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    executableAuthority t T raw = FailClosed.diagnoseArchiveStrictWith FailClosed.failClosedExec
      certifiedRegistry FailClosed.productionBinders t T raw := by
  simp only [executableAuthority, executableAuthorityWith, buildRegistry_production]

/-- **Executable authority = certified strict authority.**  `pcs-lean-authority --zip`
    prints `ACCEPT` exactly when the certified strict authority accepts the raw bytes. -/
theorem executableAuthority_refines_certifiedAuthority (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) :
    executableAuthority t T raw = "ACCEPT" ↔ ∃ inp r, certifiedAuthority t T raw = some (inp, r) := by
  rw [executableAuthority_eq, FailClosed.diagnoseArchiveStrictWith_accept_iff, certifiedAuthority,
    FailClosed.acceptArchiveStrictWith_fallback_irrelevant FailClosed.failClosedExec
      (transcriptExecutor t)]

/-- Directory mode: `ACCEPT` exactly when the certified strict authority accepts the
    archive partition of the entries. -/
theorem executableAuthorityEntries_refines_certifiedAuthority (t : AuthorityTranscript)
    (T : TrustAnchor) (entries : List (String × ByteArray)) :
    executableAuthorityEntries t T entries = "ACCEPT" ↔
      ∃ inp r, fromArchiveEntries entries = some inp ∧ certifiedPCS t T inp = some r := by
  simp only [executableAuthorityEntries, executableAuthorityEntriesWith, buildRegistry_production]
  cases fromArchiveEntries entries with
  | none => simp
  | some inp =>
    simp only [FailClosed.diagnosePCSStrictWith_accept_iff, Option.some.injEq, certifiedPCS,
      FailClosed.acceptPCSStrictWith_fallback_irrelevant FailClosed.failClosedExec
        (transcriptExecutor t)]
    exact ⟨fun ⟨r, hr⟩ => ⟨inp, r, rfl, hr⟩, fun ⟨_, r, e, hr⟩ => ⟨r, e ▸ hr⟩⟩

/-- Duplicate registration fails closed: every archive is rejected. -/
theorem executableAuthorityWith_dup {ks : List DomainChecker} (h : ¬ (ks.map (·.tag)).Nodup)
    (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    executableAuthorityWith ks t T raw = "checker_registry" := by
  simp [executableAuthorityWith, buildRegistry_dup_none h]

/-- Shadowing a built-in tag fails closed: every archive is rejected. -/
theorem executableAuthorityWith_builtin {ks : List DomainChecker} {k : DomainChecker}
    (hk : k ∈ ks) (ht : k.tag ∈ builtinTypes) (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) : executableAuthorityWith ks t T raw = "checker_registry" := by
  simp [executableAuthorityWith, buildRegistry_builtin_none hk ht]

/-- **Refinement of the original production authority.**  With no domain checker, every
    archive the strict executable accepts is accepted by the original production verdict
    `diagnoseArchiveWithTranscript`.  (The converse no longer holds: the production authority
    accepts unregistered check types on the transcript's word, the strict one rejects them —
    this is the intended loss of backward compatibility.) -/
theorem executableAuthorityWith_nil (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) (h : executableAuthorityWith [] t T raw = "ACCEPT") :
    diagnoseArchiveWithTranscript t T raw = "ACCEPT" := by
  have hreg : buildRegistry [] = some [] :=
    buildRegistry_eq_some_iff.mpr ⟨⟨List.nodup_nil, by simp⟩, rfl⟩
  simp only [executableAuthorityWith, hreg] at h
  rw [FailClosed.diagnoseArchiveStrictWith_accept_iff,
    FailClosed.acceptArchiveStrictWith_fallback_irrelevant _ (transcriptExecutor t)] at h
  obtain ⟨inp, r, h⟩ := h
  rw [← diagnoseArchiveWithCheckers_nil, diagnoseArchiveWithCheckers_accept_iff]
  refine ⟨inp, r, ?_⟩
  unfold FailClosed.acceptArchiveStrictWith at h
  unfold acceptArchiveWithCheckers
  split at h
  · cases h
  · rename_i es hes
    rw [hes]
    split at h
    · cases h
    · rename_i inp' hinp
      simp only [hinp]
      cases hr : FailClosed.acceptPCSStrictWith (transcriptExecutor t) [] FailClosed.productionBinders t T inp' with
      | none => rw [hr] at h; cases h
      | some r' =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        simp [(FailClosed.acceptPCSStrictWith_transcript_spec hr).1]

/-! ## Executor-level preservation of built-in and unhandled semantics -/

theorem dispatch_append_of_none (cs₁ cs₂ : List CertifiedChecker) (fb : Executor)
    (req : ReplayRequest) (h : cs₁.find? (·.handles req) = none) :
    dispatch (cs₁ ++ cs₂) fb req = dispatch cs₂ fb req := by
  simp [dispatch, List.find?_append, h]

/-- The extended executor coincides with the production executor on every request that
    no registered domain checker handles. -/
theorem executor_unhandled_unchanged (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (req : ReplayRequest) (h : ∀ k ∈ cs, k.handles req = false) :
    (authorityOraclesWith cs t).exec req = (transcriptOracles t).exec req := by
  simp only [authorityOraclesWith, transcriptOracles, builtinExecWith, dispatch,
    List.find?_append]
  cases hb : builtinCheckers.find? (·.handles req) with
  | some c => rfl
  | none =>
    have : cs.find? (·.handles req) = none := List.find?_eq_none.mpr (by simpa using h)
    simp [this]

/-- The six built-in checkers keep their exact behaviour: on any request a built-in
    handles, the extended executor runs that built-in, whatever is registered. -/
theorem executor_builtin_unchanged (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (req : ReplayRequest) {c : CertifiedChecker}
    (h : builtinCheckers.find? (·.handles req) = some c) :
    (authorityOraclesWith cs t).exec req = c.run req ∧
      (transcriptOracles t).exec req = c.run req := by
  simp [authorityOraclesWith, transcriptOracles, builtinExecWith, dispatch, List.find?_append, h]

/-- (Legacy executor.)  An unknown check type receives no certified meaning in the
    transcript-fallback executor: its PASS-meaning is only the external report.  The strict
    executable never reaches this case: it rejects such evidence before replay. -/
theorem authorityValid_unhandled (cs : List CertifiedChecker) (ExtHolds : ReplayRequest → Prop)
    (req : ReplayRequest) (hb : ∀ k ∈ builtinCheckers, k.handles req = false)
    (h : ∀ k ∈ cs, k.handles req = false) :
    AuthorityValid cs ExtHolds req ↔ ExtHolds req := by
  have : (builtinCheckers ++ cs).find? (·.handles req) = none :=
    List.find?_eq_none.mpr (by
      intro k hk
      rcases List.mem_append.mp hk with hk | hk
      · simpa using hb k hk
      · simpa using h k hk)
  simp [AuthorityValid, DispatchHolds, this]

/-- An unregistered check tag whose evidence the transcript did not report as PASS can
    never PASS in the executable authority (fail closed). -/
theorem executor_unknown_fail_closed (t : AuthorityTranscript) (req : ReplayRequest)
    {ty : String} (hty : ty ∉ builtinTypes) (hnotreg : ∀ k ∈ productionCheckers, k.tag ≠ ty)
    (htag : isCheckType ty req.evidence = true)
    (hrep : (transcriptExecutor t req).outcome ≠ .pass) :
    ((authorityOraclesWith certifiedRegistry t).exec req).outcome ≠ .pass := by
  have hreg : ∀ k ∈ certifiedRegistry, k.handles req = false := by
    intro k hk
    obtain ⟨k', hk', rfl⟩ := List.mem_map.mp hk
    cases hc : isCheckType k'.tag req.evidence with
    | false => exact hc
    | true => exact absurd (isCheckType_eq hc htag) (hnotreg k' hk')
  rw [executor_unhandled_unchanged _ t req hreg]
  have hb := builtin_not_handles hty htag
  have : builtinCheckers.find? (·.handles req) = none :=
    List.find?_eq_none.mpr (by intro k hk; simpa using hb k hk)
  simpa [transcriptOracles, builtinExecWith, dispatch, this] using hrep

/-! ## Soundness of the executed function -/

/-- **Soundness of `pcs-lean-authority --zip`.**  Sole hypothesis: Ed25519 unforgeability
    for the trust anchor.  If the executable prints `ACCEPT`, then the raw bytes are the
    canonical encoding of the accepted package, the certified extended authority accepted it
    with frontier-strength `ExtendedAssurance`, and **every** AI-safety or biology claim of
    the certificate that is domain-accepted with **any** obligation graph holds in the world
    of the committed artifacts. -/
theorem executableAuthority_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
        ExtendedAssurance certifiedRegistry t T
          (extendedContracts certifiedRegistry t T signed hB _ (replayFaithful_reported _)) inp r) ∧
      (∀ cid (g : Graph String AISafety.TraceIR) c,
        domainAccepts AISafety.aiAdapter r cid g = some c →
          ∀ a ∈ c.traces, ∃ tr, artBytes r.table a = some tr ∧
            AISafety.TraceSafe tr c.budget c.forbidden) ∧
      (∀ cid (g : Graph String Biology.BioIR) c,
        domainAccepts Biology.bioAdapter r cid g = some c →
          ∃ sq st, artBytes r.table c.seqA = some sq ∧ artBytes r.table c.sitesA = some st ∧
            Biology.SitesInRange sq st ∧ c.threshold ≤ Biology.hydroScore sq st) := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  refine ⟨inp, r, hr, ?_, ?_, ?_⟩
  · obtain ⟨es, hes, hp, ha⟩ := acceptArchiveWithCheckers_spec (certifiedAuthority_extended hr)
    exact ⟨es, decodeZip_sound hes, hp,
      pcs_extended_acceptance_sound _ hB (replayFaithful_reported _) ha⟩
  · intro cid g c hd
    exact Instances.ai_assurance hB (certifiedAuthority_extended hr) hd
  · intro cid g c hd
    exact Instances.bio_assurance hB (certifiedAuthority_extended hr) hd

end PCS.V2.DomainAuthority

namespace PCS.V2.DomainAuthority

open PCS PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Checkers PCS.V2.DomainAdapter
open PCS.V2.ClaimGraph PCS.V2.Witnesses

/-- **Domain soundness of `pcs-lean-authority --zip` with no cryptographic hypothesis.**
    The domain propositions concern the committed bytes, so they do not depend on who
    signed the archive: if the executable prints `ACCEPT`, every AI-safety claim that is
    domain-accepted with any obligation graph holds of the committed traces.  (Ed25519
    unforgeability is needed only for *authenticity* / attribution, see
    `executableAuthority_sound`.) -/
theorem executableAuthority_domain_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      ∀ cid (g : Graph String AISafety.TraceIR) c,
        domainAccepts AISafety.aiAdapter r cid g = some c →
          ∀ a ∈ c.traces, ∃ tr, artBytes r.table a = some tr ∧
            AISafety.TraceSafe tr c.budget c.forbidden := by
  obtain ⟨inp, r, hr⟩ := (executableAuthority_refines_certifiedAuthority t T raw).mp h
  refine ⟨inp, r, hr, fun cid g c hd => ?_⟩
  obtain ⟨_, _, _, ha⟩ := acceptArchiveWithCheckers_spec (certifiedAuthority_extended hr)
  exact (domain_adapter_sound (acceptPCSWithCheckers_spec ha).1
    (authorityWith_faithful certifiedRegistry (replayFaithful_reported (transcriptExecutor t)))
    AISafety.aiAdapter (AISafety.aiAdapter_sound productionCheckers_registered
      (by simp [productionCheckers, Instances.witnessRegistry]) _) hd).holds

end PCS.V2.DomainAuthority
