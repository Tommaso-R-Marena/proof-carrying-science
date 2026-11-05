import PCS.V2.Witnesses.AISafetyGolden
import PCS.V2.Witnesses.AISafetyDeployment
import PCS.V2.DistributedContributors

/-!
# Golden AI-safety archive: end-to-end results and adversarial campaign

## What is proved (kernel-checked theorems)

* `aiSafetyGoldenArchive_domain_sound` — if the executable authority prints `ACCEPT` on the
  golden raw bytes, then the certified extended authority accepted them, and for every
  obligation graph with which the signed claim `C1` is domain-accepted as the golden trace
  claim, the committed `trace` bytes satisfy the bounded invariant (no action `7`, cumulative
  risk `≤ 4` after every step).  No cryptographic hypothesis.
* `aiSafetyGoldenArchive_deployed_safe` — the same, transported to a deployed execution
  under the explicit `FaithfulLog` premise.
* Kernel-checked facts about the committed data: the decoded claim, the certified checker's
  PASS on the committed trace, the obligation graph's acceptance against the committed
  evidence, the invariant of the committed trace.
* Rejection explanations: `replay_mismatch_rejects`, `unknown_tag_no_leaf`,
  `duplicate_registry_fails_closed`, and small `decide` theorems for graph attacks.

## What is evaluated (`#guard`, compiled evaluation — tests, not proofs)

* `aiSafetyGoldenArchive_verdict = "ACCEPT"` — the exact function run by
  `pcs-lean-authority --zip`, on the raw golden bytes;
* the accepted result's artifact table is exactly `[("trace", trace bytes)]` and the golden
  graph is domain-accepted with the golden claim;
* every adversarial mutation is rejected **at the intended stage**.

A direct `decide` proof of `aiSafetyGoldenArchive_verdict = "ACCEPT"` is out of reach (kernel
reduction of the JCS / UTF-8 / SHA-256 stages over the ~7.7 KB archive exceeds 15–20 minutes
per stage).  The verdict **is** kernel-proved, stage by stage and without `native_decide`, in
`PCS.V2.Golden.Acceptance` (`PCS.V2.Golden.aiSafetyGoldenArchive_accepts`), which also
discharges the `hacc` premise of the theorems below
(`PCS.V2.Golden.aiSafetyGoldenArchive_committed_safe`, `…_deployed_safe`).
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.AISafetyCampaign

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.Signature PCS.V2.Index PCS.V2.EndToEnd
open PCS.V2.Replay PCS.V2.Authority PCS.V2.CertificateModel PCS.V2.ClaimGraph
open PCS.V2.DomainAdapter PCS.V2.DomainAuthority PCS.V2.Witnesses PCS.V2.Witnesses.AISafety
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.CanonicalArchive

/-! ## The golden domain objects -/

/-- The golden domain claim (decoded from the signed claim predicate). -/
def goldenTraceClaim : TraceClaim := ⟨["trace"], 4, 7⟩

/-- The (untrusted) obligation graph for `C1`. -/
def goldenGraph : Graph String TraceIR :=
  ⟨[⟨"root", .all goldenTraceClaim, .derive "ai.episodes" ["s1"]⟩,
    ⟨"s1", .safe "trace" 4 7, .leaf "E1"⟩], "root"⟩

def goldenEvidence : List CertEvidence :=
  [⟨"E1", .computationalTest, .pass, predJ 4 7, golden.evidenceJ⟩]

def goldenCertClaim : CertClaim :=
  ⟨"C1", .computational, predJ 4 7, ["E1"], ["A1"], .computational⟩

/-- The verdict printed by `pcs-lean-authority --zip` on the golden archive. -/
def aiSafetyGoldenArchive_verdict : String :=
  executableAuthority goldenTranscript goldenAnchor goldenRaw

/-- Domain verdict of claim `C1` with graph `g` on the result of the certified authority. -/
def domainVerdict (t : AuthorityTranscript) (raw : ByteArray) (g : Graph String TraceIR) :
    Option TraceClaim :=
  match certifiedAuthority t goldenAnchor raw with
  | some (_, r) => domainAccepts aiAdapter r "C1" g
  | none => none

/-! ### Kernel-checked facts about the committed data -/

theorem golden_claim_decodes : aiAdapter.decode (predJ 4 7) = some goldenTraceClaim := by decide

theorem golden_trace_safe : TraceSafe traceBytes.data.toList 4 7 := by
  refine traceTestB_sound ?_; decide

theorem golden_checker_passes :
    (traceChecker.run ⟨[], checkerVersion, golden.evidenceJ, [("trace", traceBytes)]⟩).outcome =
      .pass := by decide

theorem golden_graph_accepted :
    checkGraph (pcsCheckerIn aiAdapter goldenEvidence goldenCertClaim) goldenGraph
      (.all goldenTraceClaim) = true := by decide

/-! ### Evaluation of the complete raw-byte path (compiled; not a proof) -/

#guard golden.genCertSig == goldenCertSig
#guard golden.genPkgSig == goldenPkgSig
#guard PCS.V2.Ed25519.verify testPk golden.certMsg goldenCertSig
#guard PCS.V2.Ed25519.verify testPk golden.pkgMsg goldenPkgSig
#guard (decodeAuthorityTranscriptBytes goldenTranscriptBytes).isSome
#guard aiSafetyGoldenArchive_verdict == "ACCEPT"
#guard (certifiedAuthority goldenTranscript goldenAnchor goldenRaw).any
  (fun p => p.2.table.map (·.1) == ["trace"] && p.2.table.map (·.2) == [traceBytes])
#guard domainVerdict goldenTranscript goldenRaw goldenGraph == some goldenTraceClaim
-- the unchanged production authority also accepts it (it trusts the transcript for E1)
#guard diagnoseArchiveWithTranscript goldenTranscript goldenAnchor goldenRaw == "ACCEPT"

/-! ### End-to-end theorems for the golden archive -/

/-- **Golden archive ⟹ bounded AI-safety property of the committed trace.**
    No cryptographic hypothesis (the property concerns the committed bytes). -/
theorem aiSafetyGoldenArchive_domain_sound (hacc : aiSafetyGoldenArchive_verdict = "ACCEPT") :
    ∃ inp r, certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inp, r) ∧
      ∀ g, domainAccepts aiAdapter r "C1" g = some goldenTraceClaim →
        ∃ tr, artBytes r.table "trace" = some tr ∧ TraceSafe tr 4 7 := by
  obtain ⟨inp, r, hr, h⟩ := executableAuthority_domain_sound hacc
  exact ⟨inp, r, hr, fun g hd => h "C1" g goldenTraceClaim hd "trace" (by simp [goldenTraceClaim])⟩

/-- **Golden archive ⟹ the deployed execution is safe, under the explicit premise that the
    committed trace faithfully logs it.** -/
theorem aiSafetyGoldenArchive_deployed_safe (hacc : aiSafetyGoldenArchive_verdict = "ACCEPT") :
    ∃ inp r, certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inp, r) ∧
      ∀ g (ew : DeployedRun), domainAccepts aiAdapter r "C1" g = some goldenTraceClaim →
        FaithfulLog r.table ew → DeployedSafe ew goldenTraceClaim := by
  obtain ⟨inp, r, hr, h⟩ := executableAuthority_domain_sound hacc
  refine ⟨inp, r, hr, fun g ew hd hcorr => ?_⟩
  exact aiBridge.transport r.table ew goldenTraceClaim hcorr (h "C1" g goldenTraceClaim hd)

/-! ## Rejection explanations (theorems) -/

/-- A recorded outcome that disagrees with the fresh Lean replay makes the package fail
    the replay stage. -/
theorem replay_mismatch_rejects {exec : Executor} {c : CertV2} {m : CertModel}
    {table : List (String × ByteArray)} {e : CertEvidence} (he : e ∈ m.evidence)
    (hne : exec (requestFor c m table e) ≠ ⟨e.kind, e.outcome⟩) : replayOK exec c m table = false := by
  cases h : replayOK exec c m table with
  | false => rfl
  | true =>
    simp only [replayOK, List.all_eq_true, decide_eq_true_eq] at h
    exact absurd (h e he) hne

/-- Evidence whose `check_spec.type` is not `trace_invariant` can never discharge an
    AI-safety leaf (checker-tag substitution / unknown tag). -/
theorem unknown_tag_no_leaf {ev : JVal} (h : PCS.V2.PKPDCheck.isCheckType "trace_invariant" ev = false)
    (n : TraceIR) : aiAdapter.leafCheck ev n = false := by
  simp [aiAdapter, traceNodeOf, h]

/-- Registering the AI-safety checker twice fails closed for every archive. -/
theorem duplicate_registry_fails_closed (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    executableAuthorityWith [traceChecker, traceChecker] t T raw = "checker_registry" :=
  executableAuthorityWith_dup (by decide) t T raw

/-- A forbidden action in the committed trace makes the certified checker FAIL. -/
theorem forbidden_trace_checker_fails :
    (traceChecker.run ⟨[], checkerVersion, golden.evidenceJ, [("trace", ⟨#[0, 1, 2, 4, 1, 7]⟩)]⟩).outcome =
      .fail := by decide

/-- Cumulative risk over budget makes the certified checker FAIL. -/
theorem over_budget_checker_fails :
    (traceChecker.run ⟨[], checkerVersion, golden.evidenceJ, [("trace", ⟨#[3, 3, 0, 1]⟩)]⟩).outcome =
      .fail := by decide

/-- Graph attacks against the committed evidence (each rejected by the graph checker). -/
theorem graph_attacks_rejected :
    let V := pcsCheckerIn aiAdapter goldenEvidence goldenCertClaim
    let goal : TraceIR := .all goldenTraceClaim
    -- root replaced by the leaf
    checkGraph V { goldenGraph with root := "s1" } goal = false ∧
    -- child omitted
    checkGraph V ⟨[⟨"root", goal, .derive "ai.episodes" []⟩], "root"⟩ goal = false ∧
    -- extra unsupported obligation
    checkGraph V ⟨[⟨"root", goal, .derive "ai.episodes" ["s1", "u"]⟩,
      ⟨"s1", .safe "trace" 4 7, .leaf "E1"⟩, ⟨"u", .safe "trace" 4 7, .unsupported "manual"⟩], "root"⟩ goal = false ∧
    -- valid evidence attached to the wrong leaf (a different trace)
    checkGraph V ⟨[⟨"root", .all ⟨["other"], 4, 7⟩, .derive "ai.episodes" ["s1"]⟩,
      ⟨"s1", .safe "other" 4 7, .leaf "E1"⟩], "root"⟩ (.all ⟨["other"], 4, 7⟩) = false ∧
    -- stale evidence id (not in this certificate)
    checkGraph V ⟨[⟨"root", goal, .derive "ai.episodes" ["s1"]⟩,
      ⟨"s1", .safe "trace" 4 7, .leaf "E0"⟩], "root"⟩ goal = false ∧
    -- weaker leaf than the parent expects (larger budget)
    checkGraph V ⟨[⟨"root", goal, .derive "ai.episodes" ["s1"]⟩,
      ⟨"s1", .safe "trace" 9 7, .leaf "E1"⟩], "root"⟩ goal = false ∧
    -- cycle
    checkGraph V ⟨[⟨"root", goal, .derive "ai.episodes" ["root"]⟩], "root"⟩ goal = false ∧
    -- duplicate ids
    checkGraph V ⟨goldenGraph.nodes ++ [⟨"s1", .safe "trace" 4 7, .leaf "E1"⟩], "root"⟩ goal = false := by
  decide

/-- A wrong domain decoder (one that ignores the declared budget and reads 100) gets no
    domain acceptance with the honest graph, nor with a graph built for its own reading. -/
def wrongDecoderAdapter : DomainAdapter aiDomain :=
  { aiAdapter with decode := fun v => (aiAdapter.decode v).map (fun c => { c with budget := 100 }) }

theorem wrong_decoder_rejected :
    let V := pcsCheckerIn wrongDecoderAdapter goldenEvidence goldenCertClaim
    checkGraph V goldenGraph (.all ⟨["trace"], 100, 7⟩) = false ∧
    checkGraph V ⟨[⟨"root", .all ⟨["trace"], 100, 7⟩, .derive "ai.episodes" ["s1"]⟩,
      ⟨"s1", .safe "trace" 100 7, .leaf "E1"⟩], "root"⟩ (.all ⟨["trace"], 100, 7⟩) = false := by
  decide

/-! ## Adversarial archive campaign (compiled evaluation) -/

/-- The verdict of the executable authority on a raw archive with a transcript. -/
def verdict (t : AuthorityTranscript) (raw : ByteArray) : String :=
  executableAuthority t goldenAnchor raw

/-- The verdict of the **original** production authority (transcript-trusting for all
    non-built-in evidence). -/
def productionVerdict (t : AuthorityTranscript) (raw : ByteArray) : String :=
  diagnoseArchiveWithTranscript t goldenAnchor raw

def replaceEntry (es : List (String × ByteArray)) (n : String) (b : ByteArray) :
    List (String × ByteArray) := es.map (fun e => if e.1 = n then (n, b) else e)

def zipOf (es : List (String × ByteArray)) : ByteArray := ⟨(PCS.V2.Zip.encodeZip es).toArray⟩

def flipByte (b : ByteArray) (i : Nat) : ByteArray := b.set! i (b.get! i ^^^ 1)

/-- M1: a forbidden action inserted (consistently re-signed by an insider holding the key). -/
def m1 : FixtureSpec := { trace := ⟨#[0, 1, 2, 4, 1, 7]⟩ }
#guard verdict m1.transcript m1.build == "replay"
-- the original, transcript-trusting authority would have accepted it:
#guard productionVerdict m1.transcript m1.build == "ACCEPT"

/-- M2: cumulative risk exceeds the budget (re-signed). -/
def m2 : FixtureSpec := { trace := ⟨#[3, 3, 0, 1]⟩ }
#guard verdict m2.transcript m2.build == "replay"
#guard productionVerdict m2.transcript m2.build == "ACCEPT"

-- M3: trace artifact swapped without re-signing.
#guard verdict goldenTranscript (zipOf (replaceEntry goldenEntries tracePath ⟨#[0, 1, 2, 4, 1, 7]⟩)) ==
  "package"

/-- M4: artifact digest changed in the (re-signed) certificate. -/
def m4 : FixtureSpec := { artifactDigest := some (PCS.V2.SHA256.sha256 [9]) }
#guard verdict m4.transcript m4.build == "artifact_table"

-- M4b: certificate bytes changed without re-signing.
#guard verdict goldenTranscript
  (zipOf (replaceEntry goldenEntries "certificate.json" m4.certBytes)) == "package"

/-- M5: claim changed (claim budget 100, evidence still budget 4; re-signed). -/
def m5 : FixtureSpec := { claimBudget := 100 }
#guard verdict m5.transcript m5.build == "normalized_set"

/-- M6: budget changed consistently to 2 (re-signed): the trace's risk 4 exceeds it. -/
def m6 : FixtureSpec := { claimBudget := 2, evBudget := 2 }
#guard verdict m6.transcript m6.build == "replay"

/-- M7: checker tag changed to an unregistered tag (re-signed).  The strict executable
    rejects it before replay, whatever the transcript reports (the legacy
    transcript-fallback authority accepted it on the transcript's word). -/
def m7 : FixtureSpec := { checkTag := "trace_invariant_v2" }
#guard verdict m7.transcript m7.build == "unsupported_check_type"
#guard productionVerdict m7.transcript m7.build == "ACCEPT"
#guard domainVerdict m7.transcript m7.build goldenGraph == none
#guard verdict { m7.transcript with replay := [⟨"E1", .computationalTest, .unverified⟩] } m7.build ==
  "unsupported_check_type"

/-- The verdict of the **legacy** extended authority (certified registry, transcript
    fallback, no claim-binding gate). -/
def legacyVerdict (t : AuthorityTranscript) (raw : ByteArray) : String :=
  diagnoseArchiveWithCheckers certifiedRegistry t goldenAnchor raw

/-- M7b: `check_spec` without a `type` field (re-signed): rejected before replay. -/
def m7b : FixtureSpec :=
  { checkSpecOverride := some (.obj [("budget", .num 4), ("forbidden", .num 7),
      ("trace_artifact", .str traceId)]) }
#guard verdict m7b.transcript m7b.build == "unsupported_check_type"
#guard legacyVerdict m7b.transcript m7b.build == "ACCEPT"

/-- An additional evidence object with an unregistered type (`external_python`), recorded
    `PASS`, required by no claim. -/
def externalE2 : JVal :=
  .obj [("artifact_ids", .arr [.str traceId]),
        ("check_spec", .obj [("script", .str "check.py"), ("type", .str "external_python")]),
        ("checker", .str checkerVersion), ("claim_ids", .arr []), ("id", .str "E2"),
        ("kind", .str "computational_test"), ("outcome", .str "PASS"),
        ("predicate", predJ 4 7)]

/-- M7c: the golden archive plus an unrequired unregistered-type evidence item (re-signed):
    rejected — unregistered evidence is refused even when no claim depends on it. -/
def m7c : FixtureSpec := { extraEvidence := [("E2", externalE2)] }
#guard verdict m7c.transcript m7c.build == "unsupported_check_type"
#guard legacyVerdict m7c.transcript m7c.build == "ACCEPT"

/-- M15: claim/evidence binding mismatch with a *registered* tag (re-signed).  The claim and
    the evidence predicate say budget 2 (false: the trace's cumulative risk is 4), but the
    evidence `check_spec` runs the certified checker with budget 4, which passes.  The legacy
    authority accepted the archive with `C1` recorded `COMPUTATIONALLY_SUPPORTED`; the strict
    executable rejects it at the claim-binding gate. -/
def m15 : FixtureSpec :=
  { claimBudget := 2, evBudget := 2, checkSpecOverride := some (checkSpecJ "trace_invariant" 4 7) }
#guard verdict m15.transcript m15.build == "claim_binding"
#guard legacyVerdict m15.transcript m15.build == "ACCEPT"

/-- M8: missing evidence (the claim requires `E1`, the certificate omits it; re-signed). -/
def m8 : FixtureSpec := { withEvidence := false }
#guard verdict m8.transcript m8.build == "normalized_set"

/-- M8b: claim requires nothing and the certificate carries no evidence (re-signed):
    rejected at the `normalized_set` stage, and in any case it has no domain leaf. -/
def m8b : FixtureSpec := { withEvidence := false, required := [] }
#guard verdict m8b.transcript m8b.build == "normalized_set"
#guard domainVerdict m8b.transcript m8b.build goldenGraph == none

-- M9: stale / wrong evidence: a transcript produced for another certificate.
#guard verdict m6.transcript goldenRaw == "transcript_binding"
#guard verdict { goldenTranscript with replay := [⟨"E0", .computationalTest, .pass⟩] } goldenRaw ==
  "transcript_binding"

-- M10: duplicate checker registration / built-in shadowing / tag substitution.
#guard executableAuthorityWith [traceChecker, traceChecker] goldenTranscript goldenAnchor goldenRaw ==
  "checker_registry"
-- a (trivially "sound") always-PASS checker trying to shadow the built-in `csv_disjoint`
#guard executableAuthorityWith [⟨"csv_disjoint", fun _ => ⟨.computationalTest, .pass⟩, fun _ => True,
  fun _ _ _ => trivial⟩] goldenTranscript goldenAnchor goldenRaw == "checker_registry"

-- M11–M13: graph root changed, child omitted, extra unsupported obligation.
#guard domainVerdict goldenTranscript goldenRaw { goldenGraph with root := "s1" } == none
#guard domainVerdict goldenTranscript goldenRaw
  ⟨[⟨"root", .all goldenTraceClaim, .derive "ai.episodes" []⟩], "root"⟩ == none
#guard domainVerdict goldenTranscript goldenRaw
  ⟨[⟨"root", .all goldenTraceClaim, .derive "ai.episodes" ["s1", "u"]⟩,
    ⟨"s1", .safe "trace" 4 7, .leaf "E1"⟩, ⟨"u", .safe "trace" 4 7, .unsupported "manual"⟩], "root"⟩ == none

-- M14: signature / package / archive bytes changed; wrong trust anchor.
#guard verdict goldenTranscript (zipOf (replaceEntry goldenEntries "certificate_signature.json"
  (golden.certSigBytesWith (goldenCertSig.set 10 0)))) == "package"
#guard verdict goldenTranscript (zipOf (replaceEntry goldenEntries "package_signature.json"
  (golden.pkgSigBytesWith (goldenPkgSig.set 40 0)))) == "package"
#guard verdict goldenTranscript (zipOf (replaceEntry goldenEntries "package_manifest.json"
  (flipByte golden.manifestBytes 30))) == "package"
#guard verdict goldenTranscript (flipByte goldenRaw 100) == "canonical_archive"
#guard verdict goldenTranscript (flipByte goldenRaw (goldenRaw.size - 5)) == "canonical_archive"
#guard executableAuthority goldenTranscript { goldenAnchor with expected := some (List.replicate 32 0) }
  goldenRaw == "package"

/-! ## Distributed contributors on the golden evidence -/

open PCS.V2.DistributedContributors in
/-- Two honest contributors (leaf first, then the decomposition) get the golden claim
    accepted through the admission protocol; a colluding adversary that first squats the
    leaf id with evidence for a different trace is rejected at admission and cannot change
    the outcome; reusing a stale evidence id is rejected. -/
theorem golden_distributed_protocol :
    let V := pcsCheckerIn aiAdapter goldenEvidence goldenCertClaim
    let leaf : Submission String String TraceIR := ⟨"volunteer-1", ⟨"s1", .safe "trace" 4 7, .leaf "E1"⟩⟩
    let rootN : Submission String String TraceIR :=
      ⟨"volunteer-2", ⟨"root", .all goldenTraceClaim, .derive "ai.episodes" ["s1"]⟩⟩
    let wrongLeaf : Submission String String TraceIR := ⟨"adversary", ⟨"s1", .safe "other" 4 7, .leaf "E1"⟩⟩
    let staleLeaf : Submission String String TraceIR := ⟨"adversary", ⟨"s1", .safe "trace" 4 7, .leaf "E0"⟩⟩
    protocolAccepts V (.all goldenTraceClaim) "root" [leaf, rootN] = true ∧
    protocolAccepts V (.all goldenTraceClaim) "root" [wrongLeaf, staleLeaf, leaf, rootN] = true ∧
    run V [wrongLeaf] = [] ∧ run V [staleLeaf] = [] ∧
    protocolAccepts V (.all goldenTraceClaim) "root" [rootN, leaf] = false := by
  decide

end PCS.V2.Witnesses.AISafetyCampaign
