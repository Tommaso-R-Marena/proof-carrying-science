import PCS.V2.FailClosedGate

/-!
# Properties of the fail-closed gates (arbitrary inputs)
-/

set_option autoImplicit false

namespace PCS.V2.FailClosed

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.Package
open PCS.V2.CertificateModel PCS.V2.Checkers PCS.V2.DomainAuthority PCS.V2.DomainAdapter
open PCS.V2.ClaimGraph PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Witnesses PCS.V2.PKPDCheck
open PCS.V2.Zip PCS.V2.CanonicalArchive

/-! ## Stages of `acceptPCS` -/

theorem acceptPCS_stages {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS O T inp = some r) :
    verifyPackage O.unicode O.ed25519 T.pk T.expected inp = some r.pkg ∧
    decodeCertModel r.pkg.cert = some r.model ∧
    envStage O.capture r.pkg.cert r.model inp.files = some r.env ∧
    O.workflow (.obj r.pkg.cert.members) inp.files = true ∧
    artifactTable r.model inp.files = some r.table ∧
    replayOK O.exec r.pkg.cert r.model r.table = true ∧
    verifyNormalizedSet inp.files = some (r.index, r.claims) ∧
    normalizedOK r.pkg.cert r.model r.index r.claims = true := by
  unfold acceptPCS at h
  split at h
  · cases h
  · rename_i pr hpr
    split at h
    · cases h
    · rename_i m hm
      split at h
      · cases h
      · rename_i env henv
        split at h
        · rename_i hw
          split at h
          · cases h
          · rename_i table htab
            split at h
            · rename_i hrep
              split at h
              · cases h
              · rename_i i ps hset
                split at h
                · rename_i hn
                  cases h
                  exact ⟨hpr, hm, henv, hw, htab, hrep, hset, hn⟩
                · cases h
            · cases h
        · cases h

theorem acceptPCS_of_stages {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {pr : PackageResult} {m : CertModel} {env : Option (EnvBinding × List InventoryItem)}
    {table : List (String × ByteArray)} {i : IndexV2} {ps : List (EntryV2 × WireV2)}
    (h1 : verifyPackage O.unicode O.ed25519 T.pk T.expected inp = some pr)
    (h2 : decodeCertModel pr.cert = some m)
    (h3 : envStage O.capture pr.cert m inp.files = some env)
    (h4 : O.workflow (.obj pr.cert.members) inp.files = true)
    (h5 : artifactTable m inp.files = some table)
    (h6 : replayOK O.exec pr.cert m table = true)
    (h7 : verifyNormalizedSet inp.files = some (i, ps))
    (h8 : normalizedOK pr.cert m i ps = true) :
    acceptPCS O T inp = some { pkg := pr, model := m, table, env, index := i, claims := ps } := by
  simp only [acceptPCS, h1, h2, h3, h4, h5, h6, h7, h8, if_true]

/-! ## The fallback executor is irrelevant under the check-type gate -/

theorem dispatch_congr_of_any {cs : List CertifiedChecker} {req : ReplayRequest}
    (h : cs.any (fun k => k.handles req) = true) (fb fb' : Executor) :
    dispatch cs fb req = dispatch cs fb' req := by
  unfold dispatch
  cases hf : cs.find? (·.handles req) with
  | some k => rfl
  | none =>
    obtain ⟨k, hk, hh⟩ := List.any_eq_true.mp h
    exact absurd (List.find?_eq_none.mp hf k hk) (by simp [hh])

theorem replayOK_congr {E E' : Executor} {c : CertV2} {m : CertModel}
    {table : List (String × ByteArray)}
    (h : ∀ e ∈ m.evidence, E (requestFor c m table e) = E' (requestFor c m table e)) :
    replayOK E c m table = replayOK E' c m table := by
  unfold replayOK
  rw [Bool.eq_iff_iff, List.all_eq_true, List.all_eq_true]
  exact ⟨fun h' e he => by rw [← h e he]; exact h' e he,
    fun h' e he => by rw [h e he]; exact h' e he⟩

theorem strict_exec_agree {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {c : CertV2} {m : CertModel} {table : List (String × ByteArray)}
    (hs : supportedEvidenceB cs c m table = true) (fb fb' : Executor) :
    ∀ e ∈ m.evidence, (strictOracles cs t fb).exec (requestFor c m table e) =
      (strictOracles cs t fb').exec (requestFor c m table e) := by
  intro e he
  exact dispatch_congr_of_any (List.all_eq_true.mp hs e he) fb fb'

/-- Acceptance with one fallback transfers to any other fallback once the check-type gate
    holds. -/
theorem acceptPCS_strict_transfer {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {fb : Executor} (fb' : Executor) {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS (strictOracles cs t fb) T inp = some r)
    (hs : supportedEvidenceB cs r.pkg.cert r.model r.table = true) :
    acceptPCS (strictOracles cs t fb') T inp = some r := by
  obtain ⟨h1, h2, h3, h4, h5, h6, h7, h8⟩ := acceptPCS_stages h
  rw [replayOK_congr (strict_exec_agree hs fb fb')] at h6
  exact acceptPCS_of_stages (O := strictOracles cs t fb') h1 h2 h3 h4 h5 h6 h7 h8

theorem acceptPCSStrictWith_spec {fb : Executor} {cs : List CertifiedChecker}
    {bs : List ClaimBinder} {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCSStrictWith fb cs bs t T inp = some r) :
    acceptPCS (strictOracles cs t fb) T inp = some r ∧ transcriptCovers t r = true ∧
      supportedEvidenceB cs r.pkg.cert r.model r.table = true ∧ claimsBoundB bs r = true := by
  unfold acceptPCSStrictWith at h
  split at h
  · cases h
  · rename_i r' hr
    split at h
    · rename_i hc
      cases h
      simp only [Bool.and_eq_true] at hc
      exact ⟨hr, hc.1.1, hc.1.2, hc.2⟩
    · cases h

theorem acceptPCSStrictWith_of {fb : Executor} {cs : List CertifiedChecker}
    {bs : List ClaimBinder} {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS (strictOracles cs t fb) T inp = some r)
    (hc : transcriptCovers t r = true) (hs : supportedEvidenceB cs r.pkg.cert r.model r.table = true)
    (hb : claimsBoundB bs r = true) : acceptPCSStrictWith fb cs bs t T inp = some r := by
  simp only [acceptPCSStrictWith, h, hc, hs, hb, Bool.and_self, if_true]

/-- **Transcript replay reports are never consulted.**  Strict acceptance is the same for
    every replay fallback executor — the transcript, the constant-`FAIL` executor, or any
    other function. -/
theorem acceptPCSStrictWith_fallback_irrelevant (fb fb' : Executor) (cs : List CertifiedChecker)
    (bs : List ClaimBinder) (t : AuthorityTranscript) (T : TrustAnchor) (inp : PackageInput) :
    acceptPCSStrictWith fb cs bs t T inp = acceptPCSStrictWith fb' cs bs t T inp := by
  cases h : acceptPCSStrictWith fb cs bs t T inp with
  | some r =>
    obtain ⟨ha, hc, hs, hb⟩ := acceptPCSStrictWith_spec h
    exact (acceptPCSStrictWith_of (acceptPCS_strict_transfer fb' ha hs) hc hs hb).symm
  | none =>
    cases h' : acceptPCSStrictWith fb' cs bs t T inp with
    | none => rfl
    | some r =>
      obtain ⟨ha, hc, hs, hb⟩ := acceptPCSStrictWith_spec h'
      rw [acceptPCSStrictWith_of (acceptPCS_strict_transfer fb ha hs) hc hs hb] at h
      cases h

theorem acceptArchiveStrictWith_fallback_irrelevant (fb fb' : Executor)
    (cs : List CertifiedChecker) (bs : List ClaimBinder) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) :
    acceptArchiveStrictWith fb cs bs t T raw = acceptArchiveStrictWith fb' cs bs t T raw := by
  simp only [acceptArchiveStrictWith, acceptPCSStrictWith_fallback_irrelevant fb fb']

/-- Strict acceptance (transcript fallback) implies acceptance by the earlier extended
    authority, so every theorem about the latter applies. -/
theorem acceptPCSStrictWith_transcript_spec {cs : List CertifiedChecker} {bs : List ClaimBinder}
    {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSStrictWith (transcriptExecutor t) cs bs t T inp = some r) :
    acceptPCSWithCheckers cs t T inp = some r ∧
      supportedEvidenceB cs r.pkg.cert r.model r.table = true ∧ claimsBoundB bs r = true := by
  obtain ⟨ha, hc, hs, hb⟩ := acceptPCSStrictWith_spec h
  refine ⟨?_, hs, hb⟩
  simp only [acceptPCSWithCheckers, ← strictOracles_transcript, ha, hc, if_true]

/-! ## Diagnostic mirror -/

theorem diagnosePCSStrictWith_accept_iff (fb : Executor) (cs : List CertifiedChecker)
    (bs : List ClaimBinder) (t : AuthorityTranscript) (T : TrustAnchor) (inp : PackageInput) :
    diagnosePCSStrictWith fb cs bs t T inp = "ACCEPT" ↔
      ∃ r, acceptPCSStrictWith fb cs bs t T inp = some r := by
  constructor
  · intro h
    unfold diagnosePCSStrictWith at h
    dsimp only at h
    split at h
    · simp at h
    · rename_i pr hpr
      split at h
      · simp at h
      · rename_i m hm
        split at h
        · simp at h
        · rename_i env henv
          split at h
          · rename_i hw
            split at h
            · simp at h
            · rename_i table htab
              split at h
              · rename_i hs
                split at h
                · rename_i hrep
                  split at h
                  · simp at h
                  · rename_i i ps hset
                    split at h
                    · rename_i hn
                      split at h
                      · rename_i hb
                        split at h
                        · rename_i hc
                          exact ⟨_, acceptPCSStrictWith_of
                            (acceptPCS_of_stages hpr hm henv hw htab hrep hset hn) hc hs hb⟩
                        · simp at h
                      · simp at h
                    · simp at h
                · simp at h
              · simp at h
          · simp at h
  · rintro ⟨⟨pkg, model, table, env, index, claims⟩, h⟩
    obtain ⟨ha, hc, hs, hb⟩ := acceptPCSStrictWith_spec h
    obtain ⟨h1, h2, h3, h4, h5, h6, h7, h8⟩ := acceptPCS_stages ha
    simp only [diagnosePCSStrictWith, h1, h2, h3, h4, h5, hs, h6, h7, h8, if_true, hb, hc]

theorem diagnoseArchiveStrictWith_accept_iff (fb : Executor) (cs : List CertifiedChecker)
    (bs : List ClaimBinder) (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    diagnoseArchiveStrictWith fb cs bs t T raw = "ACCEPT" ↔
      ∃ inp r, acceptArchiveStrictWith fb cs bs t T raw = some (inp, r) := by
  unfold diagnoseArchiveStrictWith acceptArchiveStrictWith
  cases decodeZip raw with
  | none => simp
  | some es =>
    simp only
    cases hinp : fromArchiveEntries es with
    | none => simp
    | some inp =>
      simp only
      rw [diagnosePCSStrictWith_accept_iff]
      constructor
      · rintro ⟨r, hr⟩; exact ⟨inp, r, by simp [hr]⟩
      · rintro ⟨inp', r, hr⟩
        cases h : acceptPCSStrictWith fb cs bs t T inp with
        | none => rw [h] at hr; cases hr
        | some r' => exact ⟨r', rfl⟩

/-! ## What strict acceptance establishes -/

/-- **Every evidence outcome of a strictly accepted package is computed by a certified
    checker.**  For each evidence item there is a verified built-in or registered checker `k`
    that handles its replay request, the executor's observation *is* `k.run` of the request
    (no fallback, no transcript), and a recorded `PASS` carries `k`'s machine-checked
    soundness proposition. -/
theorem strict_evidence_certified {fb : Executor} {cs : List CertifiedChecker}
    {bs : List ClaimBinder} {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCSStrictWith fb cs bs t T inp = some r) :
    ∀ e ∈ r.model.evidence, ∃ k ∈ builtinCheckers ++ cs,
      k.handles (requestFor r.pkg.cert r.model r.table e) = true ∧
      (strictOracles cs t fb).exec (requestFor r.pkg.cert r.model r.table e) =
        k.run (requestFor r.pkg.cert r.model r.table e) ∧
      (e.outcome = .pass → k.Holds (requestFor r.pkg.cert r.model r.table e)) := by
  intro e he
  obtain ⟨ha, _, hs, _⟩ := acceptPCSStrictWith_spec h
  have hrep := (acceptPCS_stages ha).2.2.2.2.2.1
  have hobs := replayOK_spec hrep e he
  have hany := List.all_eq_true.mp hs e he
  cases hf : (builtinCheckers ++ cs).find? (·.handles (requestFor r.pkg.cert r.model r.table e)) with
  | none =>
    obtain ⟨k, hk, hh⟩ := List.any_eq_true.mp hany
    exact absurd (List.find?_eq_none.mp hf k hk) (by simp [hh])
  | some k =>
    have hexec : (strictOracles cs t fb).exec (requestFor r.pkg.cert r.model r.table e) =
        k.run (requestFor r.pkg.cert r.model r.table e) := by
      simp [strictOracles, dispatch, hf]
    have hh : k.handles (requestFor r.pkg.cert r.model r.table e) = true := by
      simpa using List.find?_some hf
    refine ⟨k, List.mem_of_find?_eq_some hf, hh, hexec, fun hp => k.sound _ hh ?_⟩
    rw [← hexec, hobs, hp]

/-- **Generic soundness of the claim-binding gate.**  If the strict authority accepts, then
    for every registered binder `b` whose adapter satisfies the adapter contract, every
    certificate claim recorded at an assurance level whose predicate `b` decodes to `c`
    satisfies `b.D.Holds` in the world of the committed artifacts.  No obligation graph is
    supplied by the caller: the gate itself checked the canonical one. -/
theorem strict_supported_claim_sound {fb : Executor} {cs : List CertifiedChecker}
    {bs : List ClaimBinder} {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCSStrictWith fb cs bs t T inp = some r)
    {b : ClaimBinder} (hb : b ∈ bs)
    (hA : AdapterSound b.A (AuthorityValid cs (fun req => (fb req).outcome = .pass)))
    {cl : CertClaim} (hcl : cl ∈ r.model.claims) (hsup : supportive cl.status = true)
    {c : b.D.Claim} (hdec : b.A.decode cl.predicate = some c) :
    b.D.Holds (b.A.world r.table) c := by
  obtain ⟨ha, _, _, hbound⟩ := acceptPCSStrictWith_spec h
  have hcl' := List.all_eq_true.mp hbound cl hcl
  rw [hsup] at hcl'
  have hok : binderOK b r cl = true := List.all_eq_true.mp (by simpa using hcl') b hb
  unfold binderOK at hok
  rw [hdec] at hok
  have hda := of_decide_eq_true hok
  exact (domain_adapter_sound ha (dispatch_faithful _ (replayFaithful_reported fb)) b.A hA
    hda).holds

/-! ## Check types and rejection -/

/-- The `check_spec.type` of an evidence object (`none`: no `check_spec` object or no string
    `type` field). -/
def checkTypeOf (ev : JVal) : Option String := (PCS.V2.Chemistry.checkSpec ev).bind (fun sp => strField sp "type")

theorem isCheckType_eq_decide (ty : String) (ev : JVal) :
    isCheckType ty ev = decide (checkTypeOf ev = some ty) := by
  unfold isCheckType checkTypeOf
  cases PCS.V2.Chemistry.checkSpec ev <;> simp

theorem builtin_handles_false {req : ReplayRequest}
    (h : ∀ b ∈ builtinTypes, isCheckType b req.evidence = false) :
    ∀ k ∈ builtinCheckers, k.handles req = false := by
  intro k hk
  simp only [builtinCheckers, List.mem_cons, List.not_mem_nil, or_false] at hk
  rcases hk with rfl | rfl | rfl | rfl | rfl | rfl
  · exact h "reaction_balance" (by simp [builtinTypes])
  · exact h "unit_compatible" (by simp [builtinTypes])
  · exact h "csv_disjoint" (by simp [builtinTypes])
  · exact h "pkpd_contract" (by simp [builtinTypes])
  · exact h "pkpd_reference_match" (by simp [builtinTypes])
  · exact h "pkpd_peak_concentration_threshold" (by simp [builtinTypes])

/-- Every tag a certified checker of `builtinCheckers ++ registry ks` can handle. -/
def registeredTypes (ks : List DomainChecker) : List String := builtinTypes ++ ks.map (·.tag)

/-- An evidence object whose check type is none of the registered types is handled by no
    certified checker, for every certificate and artifact table. -/
theorem certifiedHandles_false {ks : List DomainChecker} {ev : JVal}
    (hty : ∀ ty ∈ registeredTypes ks, checkTypeOf ev ≠ some ty) (req : ReplayRequest)
    (hev : req.evidence = ev) : certifiedHandles (registry ks) req = false := by
  have hfalse : ∀ ty ∈ registeredTypes ks, isCheckType ty req.evidence = false := by
    intro ty hty'
    rw [isCheckType_eq_decide, hev]
    simpa using hty ty hty'
  unfold certifiedHandles
  rw [Bool.eq_false_iff]
  intro hany
  obtain ⟨k, hk, hh⟩ := List.any_eq_true.mp hany
  rcases List.mem_append.mp hk with hk | hk
  · rw [builtin_handles_false (fun b hb => hfalse b (List.mem_append_left _ hb)) k hk] at hh
    cases hh
  · obtain ⟨k', hk', rfl⟩ := List.mem_map.mp hk
    have := hfalse k'.tag (List.mem_append_right _ (List.mem_map_of_mem hk'))
    simp only [DomainChecker.toCertified] at hh
    rw [this] at hh
    cases hh

theorem verifyPackage_cert {U : UnicodeOps} {V : PCS.V2.Signature.Ed25519Verify}
    {pk : List UInt8} {expected : Option (List UInt8)} {inp : PackageInput} {pr : PackageResult}
    (h : verifyPackage U V pk expected inp = some pr) :
    verifyCertBytes inp.certificateBytes = some pr.cert := by
  unfold verifyPackage at h
  split at h
  · cases h
  · rename_i c hc
    split at h
    · cases h
    · split at h
      · cases h
      · split at h
        · cases h
        · split at h
          · split at h
            · cases h
            · cases h; exact hc
          · cases h

/-- **Fail-closed rejection of unregistered check types (package level).**  If the delivered
    certificate parses to a model containing an evidence item whose `check_spec.type` is
    missing or is none of the registered types — whatever its recorded outcome, whether or
    not a claim requires it — then strict acceptance fails for **every** replay fallback,
    every set of claim binders, every transcript and every trust anchor (hence for every
    signature and signer). -/
theorem strict_rejects_unregistered_type {inp : PackageInput} {c : CertV2} {m : CertModel}
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {ks : List DomainChecker} {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ registeredTypes ks, checkTypeOf e.json ≠ some ty)
    (fb : Executor) (bs : List ClaimBinder) (t : AuthorityTranscript) (T : TrustAnchor) :
    acceptPCSStrictWith fb (registry ks) bs t T inp = none := by
  cases h : acceptPCSStrictWith fb (registry ks) bs t T inp with
  | none => rfl
  | some r =>
    exfalso
    obtain ⟨ha, _, hs, _⟩ := acceptPCSStrictWith_spec h
    obtain ⟨h1, h2, _⟩ := acceptPCS_stages ha
    rw [verifyPackage_cert h1] at hc
    cases hc
    rw [h2] at hm
    cases hm
    have := List.all_eq_true.mp hs e he
    rw [certifiedHandles_false hty _ rfl] at this
    cases this

end PCS.V2.FailClosed
