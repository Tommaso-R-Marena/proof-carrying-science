import PCS.V2.ProofGatedCert7
import PCS.V2.ProofGatedV6Limits

/-!
# V7 Priority 1: an independently fixed verification policy

A **policy** (`Policy`) is the complete, semantically significant verification
configuration fixed by the trusted authority:

* `version` (policy format, `7`), `checker` (which trusted checker implementation:
  `6` = PGSC6 with the exact no-forgetting search, `7` = PGSC7 with the sweep witness),
  `predicate` (the decision predicate; `1` = strong gate A ∧ B ∧ C);
* the architecture limit `arch`, the `target` network, the `corpus`, and the robustness
  interval `[lo, hi]`.

Its canonical bytes `encodePolicy p` (`PGPOL7|…`) bind **every** field:
`decodePolicy_iff` (the decoder accepts exactly canonical encodings) and
`encodePolicy_injective`.

The trusted checker table `runChecker p g active cb` is fixed code: it dispatches on the
pinned policy's `checker` field and evaluates the certificate bytes `cb` against the pinned
policy, the authority's generation `g` and the authority's active bytes `active`.

## Untrusted requests

A `Request` is entirely proposer-controlled: it may name a *requested* policy (bytes), a
*requested* generation, a *requested* incumbent, and carries certificate bytes (which embed
the candidate artifact).

* **Safe design** (`safeDecide`): the verdict is `runChecker pinned g active r.certificate`.
  `safe_policy_independent`: two requests with the same certificate bytes get the same
  verdict, whatever they request; `safeDecide_eq` says the verdict *is* the pinned-policy
  verdict. `safeDecide_sound`: acceptance implies the strong gate under the pinned policy.
* **Strict design** (`strictDecide`): additionally rejects any request whose requested
  policy bytes, generation or incumbent differ from the authority's (`strict_exact`).
* **Unsafe designs**, each refuted by a concrete, kernel-checked attack in which the
  committed candidate violates the pinned policy while the safe design rejects:
  - `naive_target_attack` (proposer substitutes the target network),
  - `naive_interval_attack` (narrower robustness interval),
  - `naive_corpus_attack` (different corpus: a step with no pinned-corpus progress),
  - `naive_arch_attack` (wider architecture: the committed bytes do not even decode under
    the pinned architecture),
  - `naive_checker_attack` (proposer selects a weaker legacy checker id),
  - `stale_generation_attack` (verifier trusts the requested generation/incumbent: an old
    certificate rolls the active model back).
* **Digest commitments** (`digestDecide`): if the authority pins only a digest `H` of the
  policy bytes, the safe guarantees hold **under the explicit hypothesis** that no other
  byte string has the pinned digest (`digest_sound`); with a colliding digest the target
  attack succeeds (`digest_collision_attack`).
-/

namespace PCS.V2.ProofGatedPolicy

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedCert7
open PCS.V2.ProofGatedNetArtifacts (toInts ofInts ofInts_toInts)

def policyVersion : Nat := 7
def checkerPGSC6 : Nat := 6
def checkerPGSC7 : Nat := 7

structure Policy where
  version : Nat
  checker : Nat
  predicate : Nat
  arch : Arch
  target : WideNet
  corpus : List Int
  lo : Int
  hi : Int
  deriving Repr, DecidableEq

def Policy.spec (p : Policy) : StrongSpec := ⟨p.arch, p.target, p.corpus, p.lo, p.hi⟩

/-- The policy is one the trusted checker table implements. -/
def Policy.supported (p : Policy) : Prop :=
  p.version = policyVersion ∧ p.predicate = predStrongABC ∧
    (p.checker = checkerPGSC6 ∨ p.checker = checkerPGSC7)

instance (p : Policy) : Decidable p.supported := by unfold Policy.supported; infer_instance

/-! ## Canonical policy bytes `PGPOL7|…` -/

def policyTag : List Char := "PGPOL7".toList

theorem policyTag_pipe_free : '|' ∉ policyTag := by decide

theorem policyTag_ascii : AsciiChars policyTag := by
  intro c hc; revert c; decide

def policyToInts (p : Policy) : List Int :=
  [(p.version : Int), (p.checker : Int), (p.predicate : Int), (p.arch.maxWidth : Int),
    (p.arch.bound : Int), p.lo, p.hi] ++ block p.corpus ++ block (toInts p.target)

def parsePolicy (zs : List Int) : Option Policy := do
  let (version, zs) ← takeNat zs
  let (checker, zs) ← takeNat zs
  let (predicate, zs) ← takeNat zs
  let (maxWidth, zs) ← takeNat zs
  let (bound, zs) ← takeNat zs
  let (lo, zs) ← takeInt zs
  let (hi, zs) ← takeInt zs
  let (corpus, zs) ← takeBlock zs
  let (tInts, zs) ← takeBlock zs
  let target ← ofInts tInts
  if zs = [] then some ⟨version, checker, predicate, ⟨maxWidth, bound⟩, target, corpus, lo, hi⟩
  else none

theorem parsePolicy_policyToInts (p : Policy) : parsePolicy (policyToInts p) = some p := by
  simp only [policyToInts, parsePolicy, List.cons_append, List.nil_append,
    takeNat_nat, takeInt, takeBlock_block, takeBlock_block_nil, ofInts_toInts,
    Option.bind_eq_bind, Option.bind_some]
  simp

/-- The canonical policy bytes (the authority's commitment). -/
def encodePolicy (p : Policy) : Bytes := (encodeInts policyTag (policyToInts p)).map charToByte

def parsePolicyBytes (bs : Bytes) : Option Policy :=
  if bs.all isAsciiByte then (decodeInts policyTag (bs.map byteToChar)).bind parsePolicy else none

def decodePolicy (bs : Bytes) : Option Policy :=
  match parsePolicyBytes bs with
  | some p => if encodePolicy p = bs then some p else none
  | none => none

theorem decodePolicy_encodePolicy (p : Policy) : decodePolicy (encodePolicy p) = some p := by
  have ha := asciiChars_encodeInts policyTag policyTag_ascii (policyToInts p)
  have hp : parsePolicyBytes (encodePolicy p) = some p := by
    unfold parsePolicyBytes encodePolicy
    rw [if_pos (all_ascii_map_charToByte _ ha), map_byteToChar_charToByte _ ha,
      decodeInts_encodeInts policyTag policyTag_pipe_free, Option.bind_some,
      parsePolicy_policyToInts]
  simp [decodePolicy, hp]

/-- **Exact acceptance characterisation** of the policy decoder. -/
theorem decodePolicy_iff (bs : Bytes) (p : Policy) :
    decodePolicy bs = some p ↔ encodePolicy p = bs := by
  constructor
  · intro h
    unfold decodePolicy at h
    cases hp : parsePolicyBytes bs with
    | none => simp [hp] at h
    | some p' =>
      by_cases he : encodePolicy p' = bs
      · simp [hp, he] at h; subst h; exact he
      · simp [hp, he] at h
  · rintro rfl; exact decodePolicy_encodePolicy p

theorem encodePolicy_injective {p q : Policy} (h : encodePolicy p = encodePolicy q) : p = q := by
  have := decodePolicy_encodePolicy p
  rw [h, decodePolicy_encodePolicy] at this
  exact (Option.some.inj this).symm

/-- **The policy bytes bind every field.** -/
theorem encodePolicy_binds {p q : Policy} (h : encodePolicy p = encodePolicy q) :
    p.version = q.version ∧ p.checker = q.checker ∧ p.predicate = q.predicate ∧
    p.arch = q.arch ∧ p.target = q.target ∧ p.corpus = q.corpus ∧ p.lo = q.lo ∧ p.hi = q.hi := by
  have := encodePolicy_injective h
  subst this
  exact ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

/-! ## The trusted checker table -/

/-- **The trusted checker table** (fixed code). On acceptance it returns the candidate
bytes to commit. -/
def runChecker (p : Policy) (g : Nat) (active cb : Bytes) : Option Bytes :=
  if p.version = policyVersion ∧ p.predicate = predStrongABC then
    if p.checker = checkerPGSC6 then
      match decodeCert cb with
      | some c => if checkCert p.spec g active c then some c.candidate else none
      | none => none
    else if p.checker = checkerPGSC7 then
      match decodeCert7 cb with
      | some c => if checkCert7 p.spec g active c then some c.base.candidate else none
      | none => none
    else none
  else none

/-- What an accepted certificate establishes. -/
def Accepts (p : Policy) (g : Nat) (active cb cand : Bytes) : Prop :=
  (p.checker = checkerPGSC6 ∧ ∃ c, encodeCert c = cb ∧ checkCert p.spec g active c = true ∧
      c.generation = g ∧ c.incumbent = active ∧ c.candidate = cand) ∨
  (p.checker = checkerPGSC7 ∧ ∃ c, encodeCert7 c = cb ∧ checkCert7 p.spec g active c = true ∧
      c.base.generation = g ∧ c.base.incumbent = active ∧ c.base.candidate = cand)

theorem runChecker_accepts {p : Policy} {g : Nat} {active cb cand : Bytes}
    (h : runChecker p g active cb = some cand) : p.supported ∧ Accepts p g active cb cand := by
  unfold runChecker at h
  by_cases hv : p.version = policyVersion ∧ p.predicate = predStrongABC
  · rw [if_pos hv] at h
    by_cases h6 : p.checker = checkerPGSC6
    · rw [if_pos h6] at h
      cases hd : decodeCert cb with
      | none => simp [hd] at h
      | some c =>
        rw [hd] at h
        by_cases hc : checkCert p.spec g active c = true
        · simp only [hc, if_true, Option.some.injEq] at h
          obtain ⟨hH, -⟩ := checkCert_sound hc
          exact ⟨⟨hv.1, hv.2, Or.inl h6⟩, Or.inl ⟨h6, c, (decodeCert_iff cb c).mp hd, hc,
            hH.2.2.2.1, hH.2.2.2.2, h⟩⟩
        · simp [hc] at h
    · rw [if_neg h6] at h
      by_cases h7 : p.checker = checkerPGSC7
      · rw [if_pos h7] at h
        cases hd : decodeCert7 cb with
        | none => simp [hd] at h
        | some c =>
          rw [hd] at h
          by_cases hc : checkCert7 p.spec g active c = true
          · simp only [hc, if_true, Option.some.injEq] at h
            obtain ⟨hH, -⟩ := checkCert7_sound hc
            exact ⟨⟨hv.1, hv.2, Or.inr h7⟩, Or.inr ⟨h7, c, (decodeCert7_iff cb c).mp hd, hc,
              hH.2.2.2.1, hH.2.2.2.2, h⟩⟩
          · simp [hc] at h
      · simp [h7] at h
  · simp [hv] at h

/-- **Soundness of the checker table**: an accepted certificate relates the canonical
networks of the active bytes and of the committed bytes by the strong gate **of the
pinned policy**. -/
theorem runChecker_sound {p : Policy} {g : Nat} {active cb cand : Bytes}
    (h : runChecker p g active cb = some cand) :
    ∃ o n, decodeBytes p.arch active = some o ∧ decodeBytes p.arch cand = some n ∧
      encodeBytes o = active ∧ encodeBytes n = cand ∧ StrongAdmissible p.spec o n := by
  obtain ⟨-, hacc⟩ := runChecker_accepts h
  rcases hacc with ⟨-, c, -, hc, -, -, rfl⟩ | ⟨-, c, -, hc, -, -, rfl⟩
  · obtain ⟨hH, o, n, ho, hn, heo, hen, hadm⟩ := checkCert_sound hc
    exact ⟨o, n, hH.2.2.2.2 ▸ ho, hn, heo, hen, hadm⟩
  · obtain ⟨-, o, n, ho, hn, heo, hen, hadm⟩ := checkCert7_sound hc
    exact ⟨o, n, ho, hn, heo, hen, hadm⟩

/-- **Exactly one canonical certificate**: the accepted certificate record is uniquely
determined by the accepted bytes. -/
theorem runChecker_unique_cert {p : Policy} {g : Nat} {active cb cand : Bytes}
    (h : runChecker p g active cb = some cand) :
    (p.checker = checkerPGSC6 ∧ ∃ c, (encodeCert c = cb ∧ checkCert p.spec g active c = true) ∧
      ∀ c', encodeCert c' = cb → c' = c) ∨
    (p.checker = checkerPGSC7 ∧ ∃ c, (encodeCert7 c = cb ∧ checkCert7 p.spec g active c = true) ∧
      ∀ c', encodeCert7 c' = cb → c' = c) := by
  obtain ⟨-, hacc⟩ := runChecker_accepts h
  rcases hacc with ⟨h6, c, hc, hk, -⟩ | ⟨h7, c, hc, hk, -⟩
  · exact Or.inl ⟨h6, c, ⟨hc, hk⟩, fun c' hc' => encodeCert_injective (hc'.trans hc.symm)⟩
  · exact Or.inr ⟨h7, c, ⟨hc, hk⟩, fun c' hc' => encodeCert7_injective (hc'.trans hc.symm)⟩

/-- **Completeness of the checker table** for every supported policy. -/
theorem runChecker_complete (p : Policy) (hp : p.supported) (g : Nat) (o n : WideNet)
    (h : StrongAdmissible p.spec o n) :
    ∃ cb, runChecker p g (encodeBytes o) cb = some (encodeBytes n) := by
  obtain ⟨hv, hpr, hc⟩ := hp
  rcases hc with h6 | h7
  · refine ⟨encodeCert (genCert p.spec g o n), ?_⟩
    simp only [runChecker, hv, hpr, h6, and_self, if_true, decodeCert_encodeCert,
      checkCert_complete p.spec g o n h]
    rfl
  · refine ⟨encodeCert7 (genCert7 p.spec g o n), ?_⟩
    have h6 : p.checker ≠ checkerPGSC6 := by rw [h7]; decide
    simp only [runChecker, hv, hpr, h7, and_self, if_true,
      decodeCert7_encodeCert7, checkCert7_complete p.spec g o n h]
    rfl

/-- An unsupported policy (unknown version, predicate or checker id) accepts nothing. -/
theorem runChecker_unsupported (p : Policy) (hp : ¬ p.supported) (g : Nat) (active cb : Bytes) :
    runChecker p g active cb = none := by
  cases h : runChecker p g active cb with
  | none => rfl
  | some cand => exact absurd (runChecker_accepts h).1 hp

/-- The certificate's own configuration fields must equal the pinned policy's. -/
theorem runChecker_binds_config {p : Policy} {g : Nat} {active cb cand : Bytes}
    (h : runChecker p g active cb = some cand) :
    (∃ c, encodeCert c = cb ∧ configMatches p.spec c ∧ c.generation = g) ∨
    (∃ c, encodeCert7 c = cb ∧ configMatches p.spec c.base ∧ c.base.generation = g) := by
  obtain ⟨-, hacc⟩ := runChecker_accepts h
  rcases hacc with ⟨-, c, hc, hk, hg, -⟩ | ⟨-, c, hc, hk, hg, -⟩
  · exact Or.inl ⟨c, hc, (checkCert_sound hk).1.2.2.1, hg⟩
  · exact Or.inr ⟨c, hc, (checkCert7_sound hk).1.2.2.1, hg⟩

/-! ## Untrusted requests and the safe design -/

/-- A request from the untrusted proposer. Every field is proposer-controlled. -/
structure Request where
  requestedPolicy : Bytes
  requestedGeneration : Nat
  requestedActive : Bytes
  certificate : Bytes
  deriving Repr, DecidableEq

/-- **Safe design**: the verifier uses only the pinned policy and its own state. -/
def safeDecide (pinned : Policy) (g : Nat) (active : Bytes) (r : Request) : Option Bytes :=
  runChecker pinned g active r.certificate

/-- The policy that the safe verifier actually uses: always the pinned one. -/
def safePolicyUsed (pinned : Policy) (_r : Request) : Policy := pinned

theorem safePolicyUsed_eq (pinned : Policy) (r : Request) : safePolicyUsed pinned r = pinned := rfl

theorem safeDecide_eq (pinned : Policy) (g : Nat) (active : Bytes) (r : Request) :
    safeDecide pinned g active r = runChecker (safePolicyUsed pinned r) g active r.certificate :=
  rfl

/-- **Policy independence**: requested policy bytes, requested generation and requested
incumbent cannot change the verdict. -/
theorem safe_policy_independent (pinned : Policy) (g : Nat) (active : Bytes) (r r' : Request)
    (h : r.certificate = r'.certificate) :
    safeDecide pinned g active r = safeDecide pinned g active r' := by
  simp [safeDecide, h]

/-- Any modification of the requested fields alone leaves the verdict unchanged. -/
theorem safe_ignores_requested (pinned : Policy) (g : Nat) (active : Bytes) (r : Request)
    (pb : Bytes) (rg : Nat) (ra : Bytes) :
    safeDecide pinned g active ⟨pb, rg, ra, r.certificate⟩ = safeDecide pinned g active r := rfl

theorem safeDecide_sound {pinned : Policy} {g : Nat} {active : Bytes} {r : Request}
    {cand : Bytes} (h : safeDecide pinned g active r = some cand) :
    ∃ o n, decodeBytes pinned.arch active = some o ∧ decodeBytes pinned.arch cand = some n ∧
      encodeBytes n = cand ∧ StrongAdmissible pinned.spec o n := by
  obtain ⟨o, n, ho, hn, -, hen, hadm⟩ := runChecker_sound h
  exact ⟨o, n, ho, hn, hen, hadm⟩

/-- **Strict design**: also rejects any request that names a different policy, generation
or incumbent. -/
def strictDecide (pinned : Policy) (g : Nat) (active : Bytes) (r : Request) : Option Bytes :=
  if r.requestedPolicy = encodePolicy pinned ∧ r.requestedGeneration = g ∧
      r.requestedActive = active then safeDecide pinned g active r
  else none

theorem strict_exact {pinned : Policy} {g : Nat} {active : Bytes} {r : Request} {cand : Bytes}
    (h : strictDecide pinned g active r = some cand) :
    r.requestedPolicy = encodePolicy pinned ∧ r.requestedGeneration = g ∧
      r.requestedActive = active ∧ safeDecide pinned g active r = some cand := by
  unfold strictDecide at h
  by_cases hc : r.requestedPolicy = encodePolicy pinned ∧ r.requestedGeneration = g ∧
      r.requestedActive = active
  · rw [if_pos hc] at h; exact ⟨hc.1, hc.2.1, hc.2.2, h⟩
  · rw [if_neg hc] at h; cases h

/-- A requested policy that differs from the pinned one in **any** field is rejected by
the strict design. -/
theorem strict_rejects_other_policy (pinned q : Policy) (hq : q ≠ pinned) (g : Nat)
    (active : Bytes) (r : Request) (hr : r.requestedPolicy = encodePolicy q) :
    strictDecide pinned g active r = none := by
  unfold strictDecide
  rw [if_neg]
  rintro ⟨h, -⟩
  exact hq (encodePolicy_injective (hr.symm.trans h))

/-! ## Unsafe designs -/

/-- **Unsafe design 1**: the verifier uses the proposer's requested policy. -/
def naiveDecide (g : Nat) (active : Bytes) (r : Request) : Option Bytes :=
  match decodePolicy r.requestedPolicy with
  | some p => runChecker p g active r.certificate
  | none => none

/-- **Unsafe design 2**: the verifier trusts the requested generation and incumbent. -/
def staleDecide (pinned : Policy) (r : Request) : Option Bytes :=
  runChecker pinned r.requestedGeneration r.requestedActive r.certificate

/-- A legacy deployment whose checker table also contains a corpus-only checker
(id `0`, from the V5 era), selectable through the requested policy. -/
def legacyTable (p : Policy) (g : Nat) (active cb : Bytes) : Option Bytes :=
  if p.checker = 0 then
    match decodeCert cb with
    | some c =>
      match decodeBytes p.arch active, decodeBytes p.arch c.candidate with
      | some o, some n =>
        if c.generation = g ∧ c.incumbent = active ∧ accept p.spec.corpusSpec o n = true then
          some c.candidate else none
      | _, _ => none
    | none => none
  else runChecker p g active cb

/-- **Unsafe design 3**: a requested policy can select any checker of the legacy table. -/
def naiveLegacyDecide (g : Nat) (active : Bytes) (r : Request) : Option Bytes :=
  match decodePolicy r.requestedPolicy with
  | some p => legacyTable p g active r.certificate
  | none => none

/-! ## Evaluation lemmas for the fixtures -/

theorem naiveDecide_encode (p : Policy) (g : Nat) (active : Bytes) (rg : Nat) (ra cb : Bytes) :
    naiveDecide g active ⟨encodePolicy p, rg, ra, cb⟩ = runChecker p g active cb := by
  simp [naiveDecide, decodePolicy_encodePolicy]

theorem runChecker_pgsc6 (p : Policy) (hv : p.version = policyVersion)
    (hp : p.predicate = predStrongABC) (h6 : p.checker = checkerPGSC6) (g : Nat) (active : Bytes)
    (c : Cert) :
    runChecker p g active (encodeCert c) = if checkCert p.spec g active c then some c.candidate else none := by
  simp only [runChecker, hv, hp, h6, and_self, if_true, decodeCert_encodeCert]

theorem runChecker_pgsc6_accept (p : Policy) (hv : p.version = policyVersion)
    (hp : p.predicate = predStrongABC) (h6 : p.checker = checkerPGSC6) (g : Nat) (o n : WideNet)
    (h : StrongAdmissible p.spec o n) :
    runChecker p g (encodeBytes o) (encodeCert (genCert p.spec g o n)) = some (encodeBytes n) := by
  rw [runChecker_pgsc6 p hv hp h6, checkCert_complete p.spec g o n h]
  rfl

theorem runChecker_pgsc6_config (p : Policy) (hv : p.version = policyVersion)
    (hp : p.predicate = predStrongABC) (h6 : p.checker = checkerPGSC6) (g : Nat) (active : Bytes)
    (c : Cert) (h : ¬ configMatches p.spec c) : runChecker p g active (encodeCert c) = none := by
  rw [runChecker_pgsc6 p hv hp h6, checkCert_config_rejected _ _ _ _ h]
  rfl

/-! ## The pinned policy of the fixtures and the attacks -/

/-- The pinned policy: PGSC6 checker, strong predicate, `arch3`, target `gen3`,
corpus `[-4..4]`, interval `[-10^9, 10^9]` (exactly `specWide`). -/
def pinned0 : Policy := ⟨7, 6, 1, arch3, gen3, corpus9, -1000000000, 1000000000⟩

theorem pinned0_spec : pinned0.spec = specWide := rfl

theorem pinned0_supported : pinned0.supported := by decide

/-- Attack 1: replace the target by the zero network. -/
def malTarget : Policy := { pinned0 with target := gen0 }

def attackTarget : Request :=
  ⟨encodePolicy malTarget, 0, encodeBytes gen3, encodeCert (genCert malTarget.spec 0 gen3 gen0)⟩

theorem malTarget_admissible : StrongAdmissible malTarget.spec gen3 gen0 := by
  rw [← acceptStrong_iff]; decide

theorem pinned_rejects_regression : ¬ StrongAdmissible pinned0.spec gen3 gen0 :=
  gen3_gen0_not_admissible

/-- **Target substitution succeeds against the naive design**: the perfect `gen3` is
replaced by the zero network, which the pinned policy forbids; the safe design rejects the
same request. -/
theorem naive_target_attack :
    naiveDecide 0 (encodeBytes gen3) attackTarget = some (encodeBytes gen0) ∧
    ¬ StrongAdmissible pinned0.spec gen3 gen0 ∧
    safeDecide pinned0 0 (encodeBytes gen3) attackTarget = none := by
  refine ⟨?_, pinned_rejects_regression, ?_⟩
  · rw [attackTarget, naiveDecide_encode]
    exact runChecker_pgsc6_accept malTarget rfl rfl rfl 0 gen3 gen0 malTarget_admissible
  · exact runChecker_pgsc6_config pinned0 rfl rfl rfl _ _ _ (by decide)

/-- Attack 2: narrow the robustness interval to `[-4, 4]`. -/
def malInterval : Policy := { pinned0 with lo := -4, hi := 4 }

def attackInterval : Request :=
  ⟨encodePolicy malInterval, 0, encodeBytes gen0, encodeCert (genCert malInterval.spec 0 gen0 gen1)⟩

/-- **Interval narrowing**: the naive design commits `gen1`, which nearly doubles the
worst-case error on the pinned interval (`interval_mismatch`); the safe design rejects. -/
theorem naive_interval_attack :
    naiveDecide 0 (encodeBytes gen0) attackInterval = some (encodeBytes gen1) ∧
    ¬ StrongAdmissible pinned0.spec gen0 gen1 ∧
    safeDecide pinned0 0 (encodeBytes gen0) attackInterval = none := by
  have hadm : StrongAdmissible malInterval.spec gen0 gen1 := by
    rw [← acceptStrong_iff]; decide
  refine ⟨?_, ?_, ?_⟩
  · rw [attackInterval, naiveDecide_encode]
    exact runChecker_pgsc6_accept malInterval rfl rfl rfl 0 gen0 gen1 hadm
  · rw [← acceptStrong_iff]; decide
  · exact runChecker_pgsc6_config pinned0 rfl rfl rfl _ _ _ (by decide)

/-- `gen2` plus a unit that fixes the input `x = 8` only (outside the corpus `[-4..4]`). -/
def outOfCorpusFix : WideNet := ⟨[uA, uB, ⟨1, -4, -3⟩], 0⟩

/-- Attack 3: replace the corpus by `[8]`. -/
def malCorpus : Policy := { pinned0 with corpus := [8] }

def attackCorpus : Request :=
  ⟨encodePolicy malCorpus, 0, encodeBytes gen2,
    encodeCert (genCert malCorpus.spec 0 gen2 outOfCorpusFix)⟩

/-- **Corpus substitution**: the naive design commits a step that makes **no progress on
the pinned corpus** (equal pinned loss), so the pinned improvement accounting
(accepted steps + loss ≤ initial loss) no longer holds; the safe design rejects. -/
theorem naive_corpus_attack :
    naiveDecide 0 (encodeBytes gen2) attackCorpus = some (encodeBytes outOfCorpusFix) ∧
    loss pinned0.spec.corpusSpec outOfCorpusFix = loss pinned0.spec.corpusSpec gen2 ∧
    ¬ StrongAdmissible pinned0.spec gen2 outOfCorpusFix ∧
    safeDecide pinned0 0 (encodeBytes gen2) attackCorpus = none := by
  have hadm : StrongAdmissible malCorpus.spec gen2 outOfCorpusFix := by
    rw [← acceptStrong_iff]; decide
  refine ⟨?_, by decide, ?_, ?_⟩
  · rw [attackCorpus, naiveDecide_encode]
    exact runChecker_pgsc6_accept malCorpus rfl rfl rfl 0 gen2 outOfCorpusFix hadm
  · rw [← acceptStrong_iff]; decide
  · exact runChecker_pgsc6_config pinned0 rfl rfl rfl _ _ _ (by decide)

/-- `gen3` padded with six dead units: nine hidden units, beyond `arch3`'s width 8. -/
def gen3pad : WideNet := ⟨[uA, uB, uC] ++ List.replicate 6 ⟨0, 0, 0⟩, 0⟩

/-- Attack 4: widen the architecture limit to nine units. -/
def malArch : Policy := { pinned0 with arch := ⟨9, 32⟩ }

def attackArch : Request :=
  ⟨encodePolicy malArch, 0, encodeBytes gen0, encodeCert (genCert malArch.spec 0 gen0 gen3pad)⟩

/-- **Architecture widening**: the naive design commits bytes that the pinned
architecture cannot even decode, so the deployment serves nothing; the safe design
rejects. -/
theorem naive_arch_attack :
    naiveDecide 0 (encodeBytes gen0) attackArch = some (encodeBytes gen3pad) ∧
    decodeBytes pinned0.arch (encodeBytes gen3pad) = none ∧
    (∀ x, inferBytes pinned0.arch (encodeBytes gen3pad) x = none) ∧
    safeDecide pinned0 0 (encodeBytes gen0) attackArch = none := by
  have hadm : StrongAdmissible malArch.spec gen0 gen3pad := by
    rw [← acceptStrong_iff]; decide
  have hnd : decodeBytes pinned0.arch (encodeBytes gen3pad) = none := by
    cases h : decodeBytes pinned0.arch (encodeBytes gen3pad) with
    | none => rfl
    | some m =>
      have hv := decodeBytes_valid h
      rw [encodeBytes_injective (decodeBytes_canonical h)] at hv
      exact absurd hv (by decide)
  refine ⟨?_, hnd, fun x => inferBytes_none hnd x, ?_⟩
  · rw [attackArch, naiveDecide_encode]
    exact runChecker_pgsc6_accept malArch rfl rfl rfl 0 gen0 gen3pad hadm
  · exact runChecker_pgsc6_config pinned0 rfl rfl rfl _ _ _ (by decide)

/-- Attack 5: select the legacy corpus-only checker id `0`. -/
def malChecker : Policy := { pinned0 with checker := 0 }

def attackChecker : Request :=
  ⟨encodePolicy malChecker, 0, encodeBytes gen2, encodeCert (genCert pinned0.spec 0 gen2 blindForget)⟩

theorem blindForget_not_admissible : ¬ StrongAdmissible pinned0.spec gen2 blindForget := by
  rw [← acceptStrong_iff]; decide

/-- **Checker substitution**: the naive legacy design commits `blindForget`, which forgets
the input `-12`; the safe design rejects. -/
theorem naive_checker_attack :
    naiveLegacyDecide 0 (encodeBytes gen2) attackChecker = some (encodeBytes blindForget) ∧
    predict gen2 (-12) = predict gen3 (-12) ∧ predict blindForget (-12) ≠ predict gen3 (-12) ∧
    safeDecide pinned0 0 (encodeBytes gen2) attackChecker = none := by
  refine ⟨?_, by decide, by decide, ?_⟩
  · have h2 : decodeBytes malChecker.arch (encodeBytes gen2) = some gen2 :=
      decodeBytes_encodeBytes _ _ (by decide)
    have hb : decodeBytes malChecker.arch (encodeBytes blindForget) = some blindForget :=
      decodeBytes_encodeBytes _ _ (by decide)
    have hacc : accept malChecker.spec.corpusSpec gen2 blindForget = true := by decide
    have hl : naiveLegacyDecide 0 (encodeBytes gen2) attackChecker =
        legacyTable malChecker 0 (encodeBytes gen2) (encodeCert (genCert pinned0.spec 0 gen2 blindForget)) := by
      simp [naiveLegacyDecide, attackChecker, decodePolicy_encodePolicy]
    rw [hl]
    unfold legacyTable
    have hm : malChecker.checker = 0 := rfl
    rw [if_pos hm, decodeCert_encodeCert]
    have e1 : (genCert pinned0.spec 0 gen2 blindForget).candidate = encodeBytes blindForget := rfl
    have e2 : (genCert pinned0.spec 0 gen2 blindForget).generation = 0 := rfl
    have e3 : (genCert pinned0.spec 0 gen2 blindForget).incumbent = encodeBytes gen2 := rfl
    simp only [e1, e2, e3, h2, hb, hacc, and_self, if_true]
  · cases h : safeDecide pinned0 0 (encodeBytes gen2) attackChecker with
    | none => rfl
    | some cand =>
      obtain ⟨o, n, ho, hn, -, hadm⟩ := safeDecide_sound h
      obtain ⟨-, hacc⟩ := runChecker_accepts h
      rcases hacc with ⟨-, c, hc, -, -, -, hcc⟩ | ⟨h7, -⟩
      · have hce : c = genCert pinned0.spec 0 gen2 blindForget := encodeCert_injective hc
        rw [decodeBytes_encodeBytes _ _ (by decide)] at ho
        rw [← hcc, hce, show (genCert pinned0.spec 0 gen2 blindForget).candidate =
          encodeBytes blindForget from rfl, decodeBytes_encodeBytes _ _ (by decide)] at hn
        cases ho; cases hn
        exact absurd hadm blindForget_not_admissible
      · exact absurd h7 (by decide)

/-- Attack 6: an old certificate, presented with its old generation and incumbent. -/
def attackStale : Request :=
  ⟨encodePolicy pinned0, 0, encodeBytes gen0, encodeCert cert1⟩

theorem pinned0_accepts_cert1 :
    runChecker pinned0 0 (encodeBytes gen0) (encodeCert cert1) = some (encodeBytes r1) := by
  rw [runChecker_pgsc6 pinned0 rfl rfl rfl, pinned0_spec, cert1_accepted]
  rfl

/-- **Trusting the requested generation**: at generation 3 with the perfect `gen3` active,
the stale design accepts the generation-0 certificate `cert1` and rolls the active model
back to `r1`, which is not an admissible successor of `gen3`; the safe design rejects. -/
theorem stale_generation_attack :
    staleDecide pinned0 attackStale = some (encodeBytes r1) ∧
    ¬ StrongAdmissible pinned0.spec gen3 r1 ∧
    safeDecide pinned0 3 (encodeBytes gen3) attackStale = none := by
  refine ⟨pinned0_accepts_cert1, by rw [← acceptStrong_iff]; decide, ?_⟩
  show runChecker pinned0 3 (encodeBytes gen3) (encodeCert cert1) = none
  rw [runChecker_pgsc6 pinned0 rfl rfl rfl, checkCert_stale_rejected _ _ _ _ (by decide)]
  rfl

/-! ## Digest commitments: an explicit hypothesis -/

section digest
variable {D : Type} [DecidableEq D]

/-- The authority pins only a digest of the policy bytes and decodes the requested bytes. -/
def digestDecide (H : Bytes → D) (pinnedDigest : D) (g : Nat) (active : Bytes) (r : Request) :
    Option Bytes :=
  if H r.requestedPolicy = pinnedDigest then
    match decodePolicy r.requestedPolicy with
    | some p => runChecker p g active r.certificate
    | none => none
  else none

/-- **Under the explicit no-collision hypothesis for the pinned bytes**, the digest
design is the strict-policy design. -/
theorem digest_sound (H : Bytes → D) (pinned : Policy)
    (hnc : ∀ b, H b = H (encodePolicy pinned) → b = encodePolicy pinned)
    (g : Nat) (active : Bytes) (r : Request) :
    digestDecide H (H (encodePolicy pinned)) g active r =
      if r.requestedPolicy = encodePolicy pinned then safeDecide pinned g active r else none := by
  unfold digestDecide
  by_cases he : H r.requestedPolicy = H (encodePolicy pinned)
  · have := hnc _ he
    rw [if_pos he, if_pos this, this, decodePolicy_encodePolicy]
    rfl
  · rw [if_neg he, if_neg]
    intro h; exact he (h ▸ rfl)

theorem digest_sound_accept (H : Bytes → D) (pinned : Policy)
    (hnc : ∀ b, H b = H (encodePolicy pinned) → b = encodePolicy pinned)
    {g : Nat} {active : Bytes} {r : Request} {cand : Bytes}
    (h : digestDecide H (H (encodePolicy pinned)) g active r = some cand) :
    ∃ o n, decodeBytes pinned.arch active = some o ∧ decodeBytes pinned.arch cand = some n ∧
      StrongAdmissible pinned.spec o n := by
  rw [digest_sound H pinned hnc] at h
  split at h
  · obtain ⟨o, n, ho, hn, -, hadm⟩ := safeDecide_sound h
    exact ⟨o, n, ho, hn, hadm⟩
  · cases h

end digest

/-- **The no-collision hypothesis is necessary**: with a colliding (constant) digest the
target-substitution attack succeeds against the digest design. -/
theorem digest_collision_attack :
    let H : Bytes → Nat := fun _ => 0
    digestDecide H (H (encodePolicy pinned0)) 0 (encodeBytes gen3) attackTarget =
      some (encodeBytes gen0) ∧ ¬ StrongAdmissible pinned0.spec gen3 gen0 := by
  refine ⟨?_, pinned_rejects_regression⟩
  show (if (0 : Nat) = 0 then _ else none) = _
  rw [if_pos rfl]
  exact naive_target_attack.1

/-- Every policy field is semantically significant: changing the target, the interval,
the corpus, the architecture or the checker id each changes a verdict (attacks 1–5), and
changing the version or predicate to an unsupported value rejects everything. -/
theorem unsupported_version_rejects (g : Nat) (active cb : Bytes) :
    runChecker { pinned0 with version := 6 } g active cb = none :=
  runChecker_unsupported _ (by decide) g active cb

theorem unsupported_predicate_rejects (g : Nat) (active cb : Bytes) :
    runChecker { pinned0 with predicate := 0 } g active cb = none :=
  runChecker_unsupported _ (by decide) g active cb

end PCS.V2.ProofGatedPolicy
