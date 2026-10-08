# PCS — Executable AI-Safety Assurance Report

> **Superseded in part (fail-closed update).** `pcs-lean-authority` now rejects any evidence
> whose `check_spec.type` is missing or unregistered (`REJECT:unsupported_check_type`) and any
> supported AI-safety/biology claim not bound by its own certified evidence
> (`REJECT:claim_binding`). The counterexample archive below is now **rejected** in both modes
> (`GoldenCx.cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected`); `cx_accepts` was replaced by
> `legacyAuthority_cx` (acceptance by the old transcript-fallback authority only), and
> `executableAuthorityWith_nil` is now one-directional. See `PCS_FAIL_CLOSED_REPORT.md`.

This report covers the run that follows the generic-domain soundness work
(`PCS_GENERIC_DOMAIN_SOUNDNESS_REPORT.md`). All earlier results (`domain_adapter_sound`,
`root_assurance_sound`, `untrusted_proposer_cannot_forge_assurance`, `pipeline_refines`,
`pcs_generic_domain_archive_acceptance_sound` and its certified/extended variants, the
biology / AI-safety / ML-evaluation witnesses, and the counterexample suite) are unchanged
and still build. Their trust boundaries are also unchanged.

New production modules (all imported by `PCS.lean`, so they build as part of the default target):

| File | Content |
|---|---|
| `PCS/V2/ExecutableAuthority.lean` | the executable authority now runs the certified checker registry; refinement and soundness theorems |
| `PCS/V2/Ed25519Sign.lean` | a test-only RFC 8032 Ed25519 *signer*, used only to produce fixtures |
| `PCS/V2/Witnesses/AISafetyGolden.lean` | the golden AI-safety archive builder and its literal signatures |
| `PCS/V2/Witnesses/AISafetyCampaign.lean` | golden-archive theorems and the adversarial campaign |
| `PCS/V2/ExternalWorld.lean` | `ExternalWorldBridge` and the external-world transfer theorems |
| `PCS/V2/Witnesses/AISafetyDeployment.lean` | the AI-safety bridge (committed trace ⟶ deployed run) and a proof that its premise is needed |
| `PCS/V2/DistributedContributors.lean` | distributed-contributor admission protocol and its non-authority theorems |
| `PCS/V2/ClaimGraphMemo.lean` | completeness of `checkGraph`, the memoized checker, and its equality with the spec |
| `PCS/V2/ExecutableAudit.lean` | `#print axioms` for every major new result |
| `tools/WriteAISafetyGolden.lean` | writes `fixtures/ai_safety_golden/` from the Lean builder |
| `PCS/V2/Golden/*.lean` (later run) | kernel proof that the executable authority accepts the golden archive; byte-level link to the committed files; `Golden/Audit.lean` prints axioms |
| `PCS/V2/{KernelRfl,KernelEq,SHA256Fast,SHA256Memo,Crc32Memo,SplitOnFuel,ZipComplete,AuthorityCLI}.lean` (later run) | kernel-evaluation support (each a proved rewrite), ZIP decoder completeness, the CLI's pure verdict function |
| `tools/CheckGoldenFileLiterals.lean` (later run) | checks that the byte literals equal the committed fixture files |

---

## 1. The certified checker registry is now on the executable path

### What changed in the executable

`PCSAuthority.lean` (the root of the `pcs-lean-authority` executable) used to print the verdict
of the production authority (`diagnoseArchiveWithTranscript` / `diagnosePCSWithTranscript`). It
now prints:

* `--zip` mode: `PCS.V2.DomainAuthority.executableAuthority transcript {pk, expected} raw`
* directory mode: `PCS.V2.DomainAuthority.executableAuthorityEntries transcript {pk, expected} entries`

The command-line interface and output format are the same as before: `ACCEPT` or
`REJECT:<stage>`, and a plain `REJECT` for a directory-mode partition failure.

```lean
def productionCheckers : List DomainChecker := Instances.witnessRegistry
  -- residue_bounds, hydrophobic_score (biology), trace_invariant (AI safety)

def buildRegistry (ks : List DomainChecker) : Option (List CertifiedChecker)
  -- some (registry ks) iff tags pairwise distinct and disjoint from the 6 built-in tags

def executableAuthorityWith (ks : List DomainChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) : String :=
  match buildRegistry ks with
  | none => "checker_registry"
  | some cs => diagnoseArchiveWithCheckers cs t T raw

def executableAuthority (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) : String :=
  executableAuthorityWith productionCheckers t T raw

def certifiedRegistry : List CertifiedChecker := registry productionCheckers
def certifiedAuthority (t) (T) (raw) : Option (PackageInput × AcceptedResult) :=
  acceptArchiveWithCheckers certifiedRegistry t T raw
```

`acceptArchiveWithCheckers` is the extended certified authority from the generic-domain run. It
was reused, not reimplemented. A `DomainChecker` stores its semantic soundness theorem as a
structure field, so a checker cannot be registered unless its soundness proof exists
(requirement 7).

### Theorems (namespace `PCS.V2.DomainAuthority`)

```lean
theorem executableAuthority_refines_certifiedAuthority (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) :
    executableAuthority t T raw = "ACCEPT" ↔ ∃ inp r, certifiedAuthority t T raw = some (inp, r)

theorem executableAuthorityEntries_refines_certifiedAuthority   -- same, directory mode

theorem buildRegistry_eq_some_iff {ks cs} :
    buildRegistry ks = some cs ↔ Registered ks ∧ cs = registry ks
theorem executableAuthorityWith_dup {ks} (h : ¬ (ks.map (·.tag)).Nodup) (t T raw) :
    executableAuthorityWith ks t T raw = "checker_registry"          -- duplicate tags fail closed
theorem executableAuthorityWith_builtin                              -- shadowing a built-in fails closed
theorem executableAuthorityWith_nil (t T raw) :
    executableAuthorityWith [] t T raw = diagnoseArchiveWithTranscript t T raw
                                                                     -- empty registry = original authority
theorem executor_builtin_unchanged (cs t req) {c}
    (h : builtinCheckers.find? (·.handles req) = some c) :
    (authorityOraclesWith cs t).exec req = c.run req ∧ (transcriptOracles t).exec req = c.run req
                                                                     -- six built-ins keep their meaning
theorem executor_unhandled_unchanged                                 -- unhandled requests: as before
theorem executor_unknown_fail_closed (t req) {ty} (hty : ty ∉ builtinTypes)
    (hnotreg : ∀ k ∈ productionCheckers, k.tag ≠ ty) (htag : isCheckType ty req.evidence = true)
    (hrep : (transcriptExecutor t req).outcome ≠ .pass) :
    ((authorityOraclesWith certifiedRegistry t).exec req).outcome ≠ .pass

theorem executableAuthority_sound {t T} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw} (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
        ExtendedAssurance certifiedRegistry t T (extendedContracts …) inp r) ∧
      (∀ cid g c, domainAccepts AISafety.aiAdapter r cid g = some c →
          ∀ a ∈ c.traces, ∃ tr, artBytes r.table a = some tr ∧
            AISafety.TraceSafe tr c.budget c.forbidden) ∧
      (∀ cid g c, domainAccepts Biology.bioAdapter r cid g = some c →
          ∃ sq st, artBytes r.table c.seqA = some sq ∧ artBytes r.table c.sitesA = some st ∧
            Biology.SitesInRange sq st ∧ c.threshold ≤ Biology.hydroScore sq st)

theorem executableAuthority_domain_sound {t T raw}
    (h : executableAuthority t T raw = "ACCEPT") :
    ∃ inp r, certifiedAuthority t T raw = some (inp, r) ∧
      ∀ cid g c, domainAccepts AISafety.aiAdapter r cid g = some c →
        ∀ a ∈ c.traces, ∃ tr, artBytes r.table a = some tr ∧
          AISafety.TraceSafe tr c.budget c.forbidden                -- no cryptographic hypothesis
```

The refinement theorem is stated as an iff on acceptance, not as an equality between functions.
The two functions have different types: the executable returns a diagnostic `String` stage,
while the certified authority returns `Option (input × result)`. The iff is the exact
correspondence available: the binary prints `ACCEPT` exactly when the certified authority
accepts. **Answer: yes, the real `pcs-lean-authority` binary now runs the certified AI-safety
checker (`trace_invariant`) and the two biology checkers.**

Notes:

* **Backward compatibility for unknown tags.** An unknown `check_spec.type` falls back to the
  host transcript, exactly as in the original production authority. This keeps old packages
  verifying. Such a PASS has no certified meaning: `authorityValid_unhandled` shows that its
  only meaning is "the transcript reported PASS", and it can never discharge a domain leaf,
  because a leaf requires the registered tag (`unknown_tag_no_leaf`). An unknown tag whose
  transcript does not report PASS is rejected (`executor_unknown_fail_closed`).
* **Host-reported outcomes are ignored for certified tags.** For built-in and registered tags,
  Lean recomputes the outcome itself. Running the binary on the golden archive with an
  observation file that reports `"outcome":"FAIL"` still gives `ACCEPT`. This is intended: the
  host transcript has no authority over checks that Lean executes.

---

## 2. The golden AI-safety archive

### Fixture

The committed world contains one artifact, `trace`, with bytes `[0,1,2,4,1,8]`. The claim
predicate states: forbidden action `7`, cumulative-risk budget `4`, checked by `trace_invariant`.
With the witness's per-action risk `risk a = a % 4`, the per-step risks are 0, 1, 2, 0, 1, 0.
The cumulative risk (`stateAfter`) is therefore 0, 1, 3, 3, 4, 4, which never exceeds 4, and
action 7 never occurs (`golden_trace_safe`). The checker version is
`pcs-python-kernel/0.6.0-ai-safety-golden`.

**Signing.** A real Ed25519 signature was produced inside the project. `PCS/V2/Ed25519Sign.lean`
is a test-only RFC 8032 signer that reproduces RFC 8032 §7.1 TEST 1. It signed the certificate
and package messages with the **publicly known RFC 8032 TEST 1 secret seed**. The two signatures
are stored as literals (`goldenCertSig`, `goldenPkgSig`). They are verified by the production
verifier `PCS.V2.Ed25519.verify`, which is the same code used in the earlier runs. No axiom and
no fake signature is involved. Build-time `#guard`s confirm that the in-project signer
reproduces both literals, and that `PCS.V2.Ed25519.verify testPk msg sig` holds for both
messages.

Because the secret key is public, `NoForgery` is **false** for this trust anchor. For that
reason the golden-archive theorems are stated without `NoForgery`. They rely on the
crypto-free `executableAuthority_domain_sound` path: the domain property is checked directly
on the committed bytes.

Files (written by `lake env lean --run tools/WriteAISafetyGolden.lean`):

```
fixtures/ai_safety_golden/archive.zip        7745 bytes
  sha256 741da6497f4a3ed9bdc86d99aeb1f3c4f7320ec220934046e6e300745d98daee
fixtures/ai_safety_golden/package/           materialised entries
fixtures/ai_safety_golden/observations.json  authority observation transcript
fixtures/ai_safety_golden/pk.b64             RFC 8032 TEST 1 public key
fixtures/ai_safety_golden/fingerprint.hex
```

The real binary:

```
$ cd fixtures/ai_safety_golden
$ ../../.lake/build/bin/pcs-lean-authority --zip archive.zip "$(cat pk.b64)" observations.json "$(cat fingerprint.hex)"
ACCEPT
$ ../../.lake/build/bin/pcs-lean-authority package "$(cat pk.b64)" observations.json "$(cat fingerprint.hex)"
ACCEPT
$ # one byte of archive.zip overwritten at offset 3000:
REJECT:canonical_archive
```

### Results (namespace `PCS.V2.Witnesses.AISafetyCampaign`)

Evaluated, as compiled `#guard`s that run during `lake build`:

* `#guard aiSafetyGoldenArchive_verdict == "ACCEPT"`, where
  `aiSafetyGoldenArchive_verdict := executableAuthority goldenTranscript goldenAnchor goldenRaw`.
  This is the exact function the binary runs, applied to the exact raw bytes.
* The accepted result's artifact table is `[("trace", bytes)]`, and the golden graph is
  domain-accepted with the golden claim. The original production authority also accepts.

Kernel-checked theorems:

```lean
theorem golden_claim_decodes : aiAdapter.decode (predJ 4 7) = some goldenTraceClaim
theorem golden_trace_safe : TraceSafe traceBytes.data.toList 4 7
theorem golden_checker_passes   -- the certified trace checker returns PASS on the committed trace
theorem golden_graph_accepted :
    checkGraph (pcsCheckerIn aiAdapter goldenEvidence goldenCertClaim) goldenGraph
      (.all goldenTraceClaim) = true

theorem aiSafetyGoldenArchive_domain_sound (hacc : aiSafetyGoldenArchive_verdict = "ACCEPT") :
    ∃ inp r, certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inp, r) ∧
      ∀ g, domainAccepts aiAdapter r "C1" g = some goldenTraceClaim →
        ∃ tr, artBytes r.table "trace" = some tr ∧ TraceSafe tr 4 7

theorem aiSafetyGoldenArchive_deployed_safe (hacc : aiSafetyGoldenArchive_verdict = "ACCEPT") :
    ∃ inp r, certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inp, r) ∧
      ∀ g (ew : DeployedRun), domainAccepts aiAdapter r "C1" g = some goldenTraceClaim →
        FaithfulLog r.table ew → DeployedSafe ew goldenTraceClaim
```

`TraceSafe tr budget forbidden` means: no action equals `forbidden`, and
`stateAfter (tr.take k) ≤ budget` for every prefix `k`.

### Kernel proof of the golden verdict (`PCS/V2/Golden/`)

*Update (later run).* The verdict is now a kernel theorem. Earlier, `aiSafetyGoldenArchive_accepts`
was only checked by compiled evaluation (`#guard`) and by the binary, because a single
`decide +kernel` over the decoder stages ran for more than 15–19 minutes per stage
(`decodeZip`, `verifyCertBytes`, `verifyIndexBytes`, Ed25519 over a computed message). It is now
proved **without `native_decide` or `Lean.ofReduceBool`**, stage by stage:

```lean
-- PCS/V2/Golden/Acceptance.lean (namespace PCS.V2.Golden)
theorem decodeZip_golden : decodeZip goldenRaw = some goldenEntries
theorem certifiedAuthority_golden :
    certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inputV, resultV)
theorem aiSafetyGoldenArchive_accepts :
    executableAuthority goldenTranscript goldenAnchor goldenRaw = "ACCEPT"
theorem aiSafetyGoldenArchive_entries_accepts :
    executableAuthorityEntries goldenTranscript goldenAnchor goldenEntries = "ACCEPT"
theorem aiSafetyGoldenArchive_committed_safe :
    certifiedAuthority goldenTranscript goldenAnchor goldenRaw = some (inputV, resultV) ∧
    domainAccepts aiAdapter resultV "C1" goldenGraph = some goldenTraceClaim ∧
    (∀ g, domainAccepts aiAdapter resultV "C1" g = some goldenTraceClaim →
      artBytes resultV.table "trace" = some traceBytes.data.toList ∧
      TraceSafe traceBytes.data.toList 4 7)
theorem aiSafetyGoldenArchive_deployed_safe (ew : DeployedRun)
    (hlog : FaithfulLog resultV.table ew) : DeployedSafe ew goldenTraceClaim

-- PCS/V2/Golden/ArchiveBytes.lean
theorem archiveBytes_eq_goldenRaw : archiveBA = goldenRaw          -- the committed archive.zip literal
theorem observationsBA_eq : observationsBA = goldenTranscriptBytes -- the committed observations.json literal
theorem decodeAuthorityTranscriptBytes_golden :
    decodeAuthorityTranscriptBytes observationsBA = some goldenTranscript
theorem cliAnchor_golden : cliAnchor FileLit.pkB64 (some FileLit.fingerprintHex) = goldenAnchor
theorem pcsLeanAuthority_golden_zip_output :
    zipModeOutput archiveBA observationsBA FileLit.pkB64 (some FileLit.fingerprintHex) = some "ACCEPT"
theorem pcsLeanAuthority_golden_dir_output :
    dirModeOutput goldenEntries observationsBA FileLit.pkB64 (some FileLit.fingerprintHex) = some "ACCEPT"
```

`aiSafetyGoldenArchive_committed_safe` and `aiSafetyGoldenArchive_deployed_safe` are the old
end-to-end theorems with the `hacc` premise discharged. The `TraceSafe` conclusion is **derived
from the acceptance** through `executableAuthority_domain_sound`; it is not evaluated separately.
`zipModeOutput` and `dirModeOutput` (`PCS/V2/AuthorityCLI.lean`) are the pure functions whose
result `PCSAuthority.main` prints after reading its input files.

How it was made feasible. Each step is a proved rewrite or a separate kernel check:

* `kernel_rfl` (`PCS/V2/KernelRfl.lean`) closes a closed goal `lhs = rhs` by adding the
  auxiliary lemma `Eq.refl lhs` directly, so the **kernel** checks the definitional equality.
  It adds no axiom. If the kernel cannot check the equality, the tactic fails.
* Canonical-JSON byte gates use the proved completeness theorem `parseCanonicalBytes_complete`,
  since the bytes are `jcsBytes v` of a canonical value `v`. They are never re-parsed in the kernel.
* `decodeZip` uses the new decoder-completeness theorem
  `decodeZip_encodeZip` (`PCS/V2/ZipComplete.lean`): for sorted, well-sized entries,
  `decodeZip (encodeZip es) = some es`.
* SHA-256 uses `sha256_eq_sha256Fast` (`PCS/V2/SHA256Fast.lean`, a list-based implementation
  proved equal to the production one) and `sha256_eq_sha256Memo` (`PCS/V2/SHA256Memo.lean`,
  a table of separately proved digests).
* CRC-32 uses `crc32_eq_crc32Memo` together with kernel-checked fold checkpoints
  (`PCS/V2/Crc32Memo.lean`), which avoids kernel deep recursion.
* Path segmentation uses `segments_eq_segmentsFuel` (`PCS/V2/SplitOnFuel.lean`).
* `ByteArray` equality uses `byteArray_instDecidableEq_eq` (`PCS/V2/KernelEq.lean`).
* The fixture literals in `PCS/V2/Golden/Literals.lean` are untrusted. Each one is proved equal
  to the builder's value (`PCS/V2/Golden/Provenance*.lean`).
* The two Ed25519 signatures are verified by kernel evaluation of the production verifier
  (`certSig_verifies`, `pkgSig_verifies`; about 70 s together).

The kernel work for the whole golden chain takes about 11 minutes of build time.

**What remains outside the kernel statement.**

1. "The literal `FileLit.archiveBytes` (and `observationsBytes`, `pkB64`, `fingerprintHex`)
   equals the file on disk." This is re-checked by `lake env lean --run
   tools/CheckGoldenFileLiterals.lean`, which reads the committed files and compares them byte
   for byte (current output: all four `match`, `OK`).
2. `PCSAuthority.main` itself: reading files, collecting a directory, and `println`. Directory
   mode is proved only for the members in canonical order (`goldenEntries`). The order that
   `readDir` returns is not modelled.
3. The Lean compiler, which produces the binary from the same definitions.

The signing key is still the public RFC 8032 TEST 1 key, so no `NoForgery` claim is made.

---

## 3. Adversarial archive campaign

All of the following are `#guard`s in `AISafetyCampaign.lean`, run on every build. "Re-signed"
means the mutated package was consistently re-signed with the test key, simulating an insider
who holds the signing key.

| # | mutation | executable verdict | original production authority |
|---|---|---|---|
| M1 | forbidden action 7 inserted (re-signed) | `replay` | **`ACCEPT`** |
| M2 | cumulative risk over budget (re-signed) | `replay` | **`ACCEPT`** |
| M3 | trace artifact swapped, not re-signed | `package` | |
| M4 | artifact digest changed (re-signed) | `artifact_table` | |
| M4b | certificate bytes changed, not re-signed | `package` | |
| M5 | claim changed (budget 100, evidence 4; re-signed) | `normalized_set` | |
| M6 | budget changed consistently to 2 (re-signed) | `replay` | |
| M7 | checker tag → unregistered tag (re-signed) | `ACCEPT`, but `domainVerdict = none`; with a transcript that does not report PASS: `replay` | |
| M8 | missing evidence | `normalized_set` | |
| M8b | claim requires nothing, no evidence | `normalized_set`, `domainVerdict = none` | |
| M9 | stale transcript (other certificate) / wrong evidence id | `transcript_binding` | |
| M10 | duplicate `trace_invariant` registration; always-PASS checker shadowing built-in `csv_disjoint` | `checker_registry` | |
| M11 | graph root replaced by leaf | `domainVerdict = none` | |
| M12 | graph child omitted | `domainVerdict = none` | |
| M13 | extra unsupported obligation | `domainVerdict = none` | |
| M14 | certificate signature / package signature / manifest bytes changed | `package` | |
| M14b | archive byte flips (offset 100, end − 5) | `canonical_archive` | |
| M14c | wrong expected fingerprint | `package` | |

In M1 and M2 the original transcript-trusting authority **accepts** a re-signed unsafe
trace, while the new executable rejects it. This is the concrete gain from running the certified
checker inside Lean. M7 is backward compatible: the package verifies, but the domain-level
AI-safety assurance is withheld.

Kernel theorems explaining the rejections:

```lean
theorem replay_mismatch_rejects {exec c m table e} (he : e ∈ m.evidence)
    (hne : exec (requestFor c m table e) ≠ ⟨e.kind, e.outcome⟩) : replayOK exec c m table = false
theorem forbidden_trace_checker_fails   -- certified checker FAILs on a trace containing 7
theorem over_budget_checker_fails       -- certified checker FAILs on an over-budget trace
theorem unknown_tag_no_leaf {ev} (h : isCheckType "trace_invariant" ev = false) (n) :
    aiAdapter.leafCheck ev n = false
theorem duplicate_registry_fails_closed (t T raw) :
    executableAuthorityWith [traceChecker, traceChecker] t T raw = "checker_registry"
theorem graph_attacks_rejected   -- root→leaf, child omitted, extra unsupported node, valid evidence
                                 -- on the wrong leaf, stale evidence id, weaker leaf than parent
                                 -- expects, cycle, duplicate ids: all `checkGraph … = false`
theorem wrong_decoder_rejected   -- a decoder that reads budget 100 from the claim cannot get the
                                 -- golden evidence (budget 4) accepted for the budget-100 claim
```

---

## 4. Distributed contributors (`PCS.V2.DistributedContributors`)

### Protocol

```lean
structure Submission (Cid L C) where author : Cid; node : Node L C
abbrev Store := List (Submission Cid L C)
def admit V st s :=                         -- the only way material becomes authoritative
  if st.any (·.node.id == s.node.id) then st          -- no overwrite
  else if admissible V st s.node then st ++ [s] else st
-- admissible: leaf ⇒ V.leaf ob claim (the leaf's own claim); derive ⇒ all children already
-- committed ∧ V.rule r claim childClaims; unsupported ⇒ false
def run V subs := subs.foldl (admit V) []
def protocolAccepts V goal root subs : Bool  -- committed node with id `root` has claim `goal`
abbrev History := List (Submission × Bool)              -- public, includes verdicts
abbrev Strategy := History → Nat → Option (Node L C)    -- adaptive, stochastic (seed), may abstain
def execute V (strat : Cid → Strategy) (sched : List (Cid × Nat)) …   -- arbitrary interleaving
```

`root` and `goal` are protocol parameters fixed by the signed claim binding. Contributors
cannot choose them.

### Main theorem

```lean
theorem accepted_contributions_cannot_forge_assurance [DecidableEq C] {V : Checker L C}
    {Sem : C → Prop} (hV : CheckerSound V Sem) (goal : C) (root : String)
    (strat : Cid → Strategy Cid L C) (sched : List (Cid × Nat))
    (h : executionAccepts V goal root strat sched = true) : Sem goal
```

The theorem quantifies over every contributor-identity type `Cid` (any finite population),
every strategy profile (honest, adversarial, adaptive to the full public history, randomised
through per-turn seeds, colluding) and every schedule or interleaving. Its only premise is
`CheckerSound V Sem`, which is soundness of the trusted validator. **No assumption is made about
any contributor.**

It is proved from a store invariant (`run_invariant`: every committed node's claim holds), not
by calling `root_assurance_sound`. A refinement theorem then connects the protocol to the
existing graph checker:

```lean
theorem protocol_graph_accepted [DecidableEq C] {V goal root subs}
    (h : protocolAccepts V goal root subs = true) :
    checkGraph V (storeGraph (run V subs) root) goal = true
```

So an accepted committed store is a graph that `checkGraph` accepts, and therefore
`checkGraphMemo` accepts it too. All existing graph theorems apply to it.

### Protocol facts

```lean
theorem unverified_leaf_rejected (V st a i c ob) (h : V.leaf ob c = false) :
    admit V st ⟨a, ⟨i, c, .leaf ob⟩⟩ = st
theorem no_overwrite (V) {st e} (he : e ∈ st) (s) (hid : s.node.id = e.node.id) : admit V st s = st
theorem committed_persistent (V subs more) {e} (he : e ∈ run V subs) : e ∈ run V (subs ++ more)
theorem committed_provenance    -- every committed entry is a submitted one (authorship preserved)
theorem committed_ids_nodup     -- committed ids are pairwise distinct
theorem committed_children_earlier  -- children committed strictly earlier (acyclic by construction)
theorem accepted_root_claim_fixed   -- the accepted root node carries exactly `goal`, was submitted
theorem accepted_conclusion_order_independent {strat₁ strat₂ sched₁ sched₂}
    (h₁ : executionAccepts V goal root strat₁ sched₁ = true)
    (h₂ : executionAccepts V goal root strat₂ sched₂ = true) :
    (∃ e₁ ∈ finalStore V strat₁ sched₁, ∃ e₂ ∈ finalStore V strat₂ sched₂,
      e₁.node.id = root ∧ e₂.node.id = root ∧ e₁.node.claim = e₂.node.claim) ∧ Sem goal
theorem coalition_is_submission_list (V strat sched) :
    ∃ subs, finalStore V strat sched = run V subs   -- collusion adds nothing beyond a joint list
theorem execution_provenance
theorem squatting_blocks_liveness :   -- proved limitation
    protocolAccepts V 1 "root" [honest] = true ∧ protocolAccepts V 1 "root" [adv, honest] = false ∧
    protocolAccepts V 1 "root" [honest, adv] = true
theorem pcs_distributed_domain_sound   -- PCS instance: contributions checked with the adapter's
    … (hacc : acceptPCS O T inp = some r) (hV : ReplayFaithful O.exec Valid)
    (A : DomainAdapter D) (hA : AdapterSound A Valid) (cl) (hcomp : A.compile c = some ir)
    (root strat sched) (h : executionAccepts (pcsChecker A r cl) ir root strat sched = true) :
    D.Holds (A.world r.table) c
theorem golden_distributed_protocol   -- (AISafetyCampaign) two volunteers build the golden graph
```

**Ordering.** The order of contributions can change *whether* a root is accepted: an adversary
can squat an id and block liveness. It cannot change *what* an accepted root means. Liveness
against squatting would need an extra protocol rule, such as per-contributor namespaces or
revalidated replacement. That rule is not needed for soundness and was not added.

---

## 5. External-world bridge (`PCS/V2/ExternalWorld.lean`)

```lean
structure ExternalWorldBridge (D : Domain) where
  ExternalWorld : Type
  ExternalHolds : ExternalWorld → D.Claim → Prop
  Corresponds : D.World → ExternalWorld → Prop          -- data adequacy
  transport : ∀ w ew c, Corresponds w ew → D.Holds w c → ExternalHolds ew c

theorem DomainAdapter.external_world_transfer_sound {O T inp r Valid}
    (hacc : acceptPCS O T inp = some r) (hV : ReplayFaithful O.exec Valid)
    (A : DomainAdapter D) (hA : AdapterSound A Valid) (B : ExternalWorldBridge D)
    {cid g c} (hd : domainAccepts A r cid g = some c)
    {ew : B.ExternalWorld} (hcorr : B.Corresponds (A.world r.table) ew) :
    B.ExternalHolds ew c ∧ D.Holds (A.world r.table) c

theorem DomainAdapter.false_external_world_not_corresponding … (hbad : ¬ B.ExternalHolds ew c) :
    ¬ B.Corresponds (A.world r.table) ew

theorem DomainAuthority.archive_external_world_transfer_sound (cs) {t T signed}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed) {raw inp r}
    (h : acceptArchiveWithCheckers cs t T raw = some (inp, r)) (A) (hA : AdapterSound A …)
    (Bw : ExternalWorldBridge D) {cid g c} (hd : domainAccepts A r cid g = some c)
    {ew} (hcorr : Bw.Corresponds (A.world r.table) ew) : Bw.ExternalHolds ew c
```

The correspondence premise `hcorr` is an explicit hypothesis. No theorem produces it from PCS
acceptance.

AI-safety instance (`Witnesses/AISafetyDeployment.lean`): `DeployedRun` holds the actions the
deployed agent actually executed. `FaithfulLog w ew` says each committed episode log equals the
deployed episode. `DeployedSafe` is the external reading of the claim, and `aiBridge` is the
bridge. `aiSafetyGoldenArchive_deployed_safe` applies it to the golden archive.

```lean
theorem committed_safe_deployed_unsafe :
    aiDomain.Holds goldenWorld goldenClaim ∧ ¬ DeployedSafe unsafeRun goldenClaim ∧
      ¬ FaithfulLog goldenWorld unsafeRun
```

This shows the premise cannot be dropped. The committed trace is safe and the deployed run is
unsafe, yet PCS acceptance depends only on committed bytes and cannot tell the two apart.

---

## 6. Memoized obligation-graph checker (`PCS/V2/ClaimGraphMemo.lean`)

```lean
theorem checkGraph_iff (V g goal) : checkGraph V g goal = true ↔ AcceptedGraph V g goal
  -- completeness of the specification checker (closes the open item of the earlier report)

def visit V g : Nat → (stack done : List String) → String → Option (List String)
  -- DFS with a `done` set: a verified node is never re-expanded (`visit_done`);
  -- `stack` detects cycles
def checkGraphMemo V g goal : Bool :=
  decide ((g.nodes.map (·.id)).Nodup) && rootBoundB g goal &&
    (visit V g g.nodes.length [] [] g.root).isSome

theorem checkGraphMemo_eq (V g goal) : checkGraphMemo V g goal = checkGraph V g goal
theorem root_assurance_sound_memo (hV : CheckerSound V Sem) (h : checkGraphMemo V g goal = true) :
    Sem goal
theorem memo_rejects_id_collision   -- an id reused by a malicious node: rejected
theorem memo_rejects_cycle
theorem memo_rejects_missing
```

Because the result is an equality of functions, cycles, duplicate ids, missing nodes and
unsupported nodes are rejected exactly as before. There is no cache-key collision attack: the
cache stores node ids, and ids are checked unique before `visit` runs (`memo_rejects_id_collision`).
`#guard checkGraphMemo trivialChecker (diamondChain 40) 0` evaluates a chain of 40 shared
diamonds. That graph has 2^40 root-to-leaf paths, so the plain tree-unfolding checker cannot
evaluate it. The memoized checker visits each node once, using O(n) `visit` calls with
list-based `find`/`contains`. The complexity is shown only by this evaluation; no complexity
theorem was proved.

---

## 7. Falsification attempts

| attack | outcome |
|---|---|
| malicious certified-checker registration | impossible without a soundness proof (a field of `DomainChecker`); a trivially "sound" always-PASS checker shadowing a built-in → `checker_registry` (M10) |
| duplicate checker tags | `executableAuthorityWith_dup`, M10 |
| checker-tag substitution | M7: package accepted (backward compatibility), domain assurance withheld (`unknown_tag_no_leaf`) |
| good graph + wrong domain decoder | `wrong_decoder_rejected` |
| good committed trace, false claim about an external run | `committed_safe_deployed_unsafe`, `false_external_world_not_corresponding` |
| colluding contributors | `coalition_is_submission_list` + `accepted_contributions_cannot_forge_assurance` |
| valid evidence for the wrong leaf | `graph_attacks_rejected` (4th conjunct), `unverified_leaf_rejected` |
| stale evidence | M9, `graph_attacks_rejected` (5th conjunct) |
| replace graph root | M11; contributors: `no_overwrite`, `accepted_root_claim_fixed` |
| ordering attacks | `accepted_conclusion_order_independent`; liveness attack is real: `squatting_blocks_liveness` |
| memo cache collision / wrong-node reuse | `checkGraphMemo_eq`, `memo_rejects_id_collision` |
| insider re-signs an unsafe trace | M1/M2: rejected by the new executable, **accepted** by the original production authority |

---

## 8. Trusted components and open items

Trusted / assumed:

* The Lean kernel and compiler. The binary runs compiled code, and `#guard` results come from
  compiled evaluation.
* `NoForgery` for the trust anchor, but only in the theorems that state it
  (`executableAuthority_sound`, `archive_external_world_transfer_sound`, and the earlier
  frontier theorems). The domain-level theorems (`executableAuthority_domain_sound`,
  `aiSafetyGoldenArchive_*`) do not use it.
* The host observation transcript, only for check types that Lean does not execute. Such checks
  never receive certified domain meaning.
* `CheckerSound` / `AdapterSound` / `ReplayFaithful` for the specific validators, as premises.
  For the production witnesses these are discharged by the registered checkers' soundness
  fields.
* Explicit correspondence premises (`FaithfulLog`, `Corresponds`) for any external-world
  conclusion.

Open:

1. ~~A kernel proof of `aiSafetyGoldenArchive_verdict = "ACCEPT"`~~: **done** (see §2,
   `PCS/V2/Golden/`). What remains is the file-equals-literal link (checked by
   `tools/CheckGoldenFileLiterals.lean`) and the I/O shell of `PCSAuthority.main`.
2. The test key is public, so `NoForgery` does not hold for the golden anchor. A deployment
   needs a secret key, and the fixture would be regenerated by changing `testSeed` in
   `AISafetyGolden.lean` and rerunning the tool.
3. Liveness against id-squatting in the contributor protocol is not provided (proved
   limitation).
4. No asymptotic complexity theorem for `checkGraphMemo`; only an evaluation witness.

### Why none of this is a proof of global AI safety

The AI-safety result is limited to the declared bounded property `TraceSafe` (no forbidden
action, cumulative risk within budget) of **committed trace bytes**. It extends to a deployed
execution only under the explicit `FaithfulLog` premise. It says nothing about traces that were
not committed, about other episodes, about whether the invariant is the right one, or about the
behaviour of any AI system outside the recorded trace.

---

## 9. Build, audit and axioms

```
$ lake build                       # default targets: PCS, pcs-lean-authority
Build completed successfully (215 jobs).    # (later run, including PCS/V2/Golden/*; ~11 min from clean)
```

`PCS/V2/Golden/Audit.lean` prints the axioms of the golden-chain theorems on every build. All of
them depend on exactly `[propext, Classical.choice, Quot.sound]`.

The only warning is a pre-existing unused variable in `PCS/V2/SHA256.lean`.

Forbidden-escape audit:

```
$ rg -n -w "sorry|admit|axiom|unsafe|extern|implemented_by|native_decide" PCS PCS.lean PCSAuthority.lean tools -g '*.lean' | grep -v "#print axioms"
```

The only hits are doc-comment prose ("axiom dependencies", "never an `axiom`", "`native_decide`
is excluded") and the identifier `admit`, which is the contributor-admission function in
`DistributedContributors.lean`, not the tactic. There are no `sorry`, no `admit` tactic, no
`axiom` declarations, and no `unsafe`, `extern`, `implemented_by` or `native_decide`.

Axioms (`PCS/V2/ExecutableAudit.lean`, printed by every build). Every major new theorem depends
only on a subset of `[propext, Classical.choice, Quot.sound]`. For example:

```
executableAuthority_refines_certifiedAuthority  [propext, Classical.choice, Quot.sound]
executableAuthority_sound                        [propext, Classical.choice, Quot.sound]
executableAuthority_domain_sound                 [propext, Classical.choice, Quot.sound]
aiSafetyGoldenArchive_domain_sound               [propext, Classical.choice, Quot.sound]
aiSafetyGoldenArchive_deployed_safe              [propext, Classical.choice, Quot.sound]
golden_trace_safe / golden_checker_passes        [propext, Quot.sound]
golden_claim_decodes                             [propext]
accepted_contributions_cannot_forge_assurance    [propext, Classical.choice, Quot.sound]
protocol_graph_accepted                          [propext, Classical.choice, Quot.sound]
external_world_transfer_sound                    [propext, Classical.choice, Quot.sound]
archive_external_world_transfer_sound            [propext, Classical.choice, Quot.sound]
committed_safe_deployed_unsafe                   [propext]
checkGraphMemo_eq / root_assurance_sound_memo    [propext, Classical.choice, Quot.sound]
memo_rejects_*                                   [propext]
```

No `Lean.ofReduceBool`, no `Lean.trustCompiler`, and no project axiom.

Commands to reproduce the fixture and the binary verdict:

```
lake build
lake env lean --run tools/WriteAISafetyGolden.lean
lake env lean --run tools/CheckGoldenFileLiterals.lean   # literal = committed files
cd fixtures/ai_safety_golden
../../.lake/build/bin/pcs-lean-authority --zip archive.zip "$(cat pk.b64)" observations.json "$(cat fingerprint.hex)"
```

## 10. Generalisation beyond the golden archive (follow-up)

See `PCS_EXECUTABLE_GENERAL_ASSURANCE_REPORT.md`. In summary:
- `ExecutableGeneral.executableAuthority_trace_evidence_sound` covers **every** archive,
  transcript and trust anchor. If the executable prints `ACCEPT`, every `PASS` evidence item
  with the certified `trace_invariant` tag has safe archived member bytes.
- Kernel-checked rejections: `Golden.tamperedRaw_rejected` and
  `Golden.Insider.insider_rejected_entries`.
- A kernel-checked counterexample, `GoldenCx.no_unconditional_claim_bridge`, shows the
  certified-tag condition cannot be dropped.
