import PCS.V2.ProofGatedBoundary

/-!
# V7 Priority 3: independently checkable transition receipts and receipt chains

A receipt (`ProofGatedBoundary.Receipt`, wire format `PGSR7|…`, a new tag) binds:
the canonical policy bytes, the old state (generation, active bytes), the expected
generation, the committed candidate, the certificate bytes, the decision and the new state.

**Independent checker** `checkReceipt pinnedBytes rc`: decode the pinned policy bytes,
re-run the trusted checker table on the receipt's certificate against the receipt's old
state, and compare every field.

* `checkReceipt_sound`: an accepted receipt is *exactly* the receipt that the authority
  emits for some request in the receipt's old state, under the pinned policy;
* `checkReceipt_complete`: every receipt the authority emits is accepted;
* `decodeReceipt_iff`: the receipt byte format is canonical; `checkReceiptBytes_*`.

**Chains** `checkChain pinnedBytes genesis rcs final`:
* `checkChain_sound`: an accepted chain is the log of an actual authority run from the
  genesis state to `final` (`chain_realised`), so every invariant holds from the genesis
  model to the final model (`checkChain_invariant`);
* `checkChain_complete`: every authority run yields an accepted chain.

**What a chain does *not* prove** (counterexamples, all kernel-checked):
* `prefix_attack`: every prefix of a valid chain is a valid chain (to an earlier state):
  continuity of a supplied chain does not establish that it is current. Concretely, the
  one-step prefix of the three-step chain is valid and ends at `r1`, which is wrong at
  inputs where the current `gen3` is right;
* `fork_attack`: two different valid chains from the same genesis reach the same generation
  with different active models: a generation counter alone does not identify the state.

**External anchoring (explicit assumption)**: if the verifier obtains the authoritative
`(generation, active bytes)` from protected monotonic storage (`anchor`), then
`anchored_sound` gives the full invariant for the anchored state, `anchored_rejects_prefix`
rejects every strictly shorter (in accepted steps) prefix, and `anchored_unique_state`
fixes the state. Signatures, protected storage and monotonic counters are **not
implemented**: they appear only as the hypothesis that the anchor is authoritative.
-/

namespace PCS.V2.ProofGatedReceipt

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedPolicy
open PCS.V2.ProofGatedBoundary

/-! ## Independent receipt checker -/

/-- Executable form of `ReceiptOK`. -/
def receiptOKB (p : Policy) (rc : Receipt) : Bool :=
  rc.version == receiptVersion && rc.policyBytes == encodePolicy p && rc.expectedGen == rc.oldGen &&
  (if rc.accepted then
    runChecker p rc.oldGen rc.oldActive rc.certificate == some rc.candidate &&
      rc.newGen == rc.oldGen + 1 && rc.newActive == rc.candidate
  else
    runChecker p rc.oldGen rc.oldActive rc.certificate == none && rc.candidate == [] &&
      rc.newGen == rc.oldGen && rc.newActive == rc.oldActive)

theorem receiptOKB_iff (p : Policy) (rc : Receipt) : receiptOKB p rc = true ↔ ReceiptOK p rc := by
  unfold receiptOKB ReceiptOK
  cases rc.accepted <;> simp [Bool.and_eq_true, beq_iff_eq, and_assoc]

/-- **The independent receipt checker.** -/
def checkReceipt (pinnedBytes : Bytes) (rc : Receipt) : Bool :=
  match decodePolicy pinnedBytes with
  | some p => receiptOKB p rc
  | none => false

/-- **Soundness**: an accepted receipt is exactly the receipt emitted by the authority for
some request in the receipt's old state, and it records the authority's new state. -/
theorem checkReceipt_sound {pinnedBytes : Bytes} {rc : Receipt}
    (h : checkReceipt pinnedBytes rc = true) :
    ∃ p, decodePolicy pinnedBytes = some p ∧ ∃ r : Request,
      propose ⟨p, rc.oldGen, rc.oldActive⟩ r = (⟨p, rc.newGen, rc.newActive⟩, rc) := by
  unfold checkReceipt at h
  cases hp : decodePolicy pinnedBytes with
  | none => rw [hp] at h; cases h
  | some p =>
    rw [hp] at h
    refine ⟨p, rfl, ⟨[], 0, [], rc.certificate⟩, ?_⟩
    obtain ⟨hv, hpb, he, hrest⟩ := (receiptOKB_iff p rc).mp h
    obtain ⟨version, policyBytes, oldGen, oldActive, expectedGen, candidate, certificate, accepted,
      newGen, newActive⟩ := rc
    simp only at hv hpb he hrest ⊢
    subst hv hpb he
    cases accepted with
    | true =>
      simp only [if_true] at hrest
      obtain ⟨hr, hg, ha⟩ := hrest
      subst hg ha
      simp only [propose, safeDecide, hr, mkReceipt]
    | false =>
      simp only [Bool.false_eq_true, if_false] at hrest
      obtain ⟨hr, hc, hg, ha⟩ := hrest
      subst hc hg ha
      simp only [propose, safeDecide, hr, mkReceipt]

/-- **Completeness**: every receipt the authority emits passes the checker (given the
canonical bytes of the authority's policy). -/
theorem checkReceipt_complete (s : AState) (r : Request) :
    checkReceipt (encodePolicy s.policy) (propose s r).2 = true := by
  simp only [checkReceipt, decodePolicy_encodePolicy]
  exact (receiptOKB_iff _ _).mpr (propose_receipt_ok s r)

/-- Semantic content of an accepted receipt. -/
theorem checkReceipt_accepted {pinnedBytes : Bytes} {rc : Receipt}
    (h : checkReceipt pinnedBytes rc = true) (ha : rc.accepted = true) :
    ∃ p o n, decodePolicy pinnedBytes = some p ∧ decodeBytes p.arch rc.oldActive = some o ∧
      decodeBytes p.arch rc.newActive = some n ∧ StrongAdmissible p.spec o n ∧
      rc.newGen = rc.oldGen + 1 := by
  unfold checkReceipt at h
  cases hp : decodePolicy pinnedBytes with
  | none => rw [hp] at h; cases h
  | some p =>
    rw [hp] at h
    obtain ⟨-, -, -, hrest⟩ := (receiptOKB_iff p rc).mp h
    rw [ha] at hrest
    simp only [if_true] at hrest
    obtain ⟨hr, hg, hn⟩ := hrest
    obtain ⟨o, n, ho, hn', -, -, hadm⟩ := runChecker_sound hr
    exact ⟨p, o, n, rfl, ho, hn ▸ hn', hadm, hg⟩

/-- A receipt naming a different policy is rejected. -/
theorem checkReceipt_wrong_policy (p : Policy) (rc : Receipt) (h : rc.policyBytes ≠ encodePolicy p) :
    checkReceipt (encodePolicy p) rc = false := by
  cases hc : checkReceipt (encodePolicy p) rc with
  | false => rfl
  | true =>
    simp only [checkReceipt, decodePolicy_encodePolicy] at hc
    exact absurd ((receiptOKB_iff p rc).mp hc).2.1 h

/-! ## Canonical receipt bytes `PGSR7|…` -/

def receiptTag : List Char := "PGSR7".toList

theorem receiptTag_pipe_free : '|' ∉ receiptTag := by decide

theorem receiptTag_ascii : AsciiChars receiptTag := by
  intro c hc; revert c; decide

def boolI (b : Bool) : Int := if b then 1 else 0

def receiptToInts (rc : Receipt) : List Int :=
  [(rc.version : Int), (rc.oldGen : Int), (rc.expectedGen : Int), boolI rc.accepted,
    (rc.newGen : Int)] ++
  block (rc.policyBytes.map byteI) ++ block (rc.oldActive.map byteI) ++
  block (rc.candidate.map byteI) ++ block (rc.certificate.map byteI) ++
  block (rc.newActive.map byteI)

def takeBool : List Int → Option (Bool × List Int)
  | z :: r => if z = 1 then some (true, r) else if z = 0 then some (false, r) else none
  | [] => none

def takeBytes (zs : List Int) : Option (Bytes × List Int) := do
  let (bi, rest) ← takeBlock zs
  let bs ← bytesOfInts bi
  some (bs, rest)

theorem takeBytes_block (bs : Bytes) (r : List Int) :
    takeBytes (block (bs.map byteI) ++ r) = some (bs, r) := by
  simp [takeBytes, takeBlock_block, bytesOfInts_map]

theorem takeBytes_block_nil (bs : Bytes) : takeBytes (block (bs.map byteI)) = some (bs, []) := by
  have := takeBytes_block bs []
  simpa using this

def parseReceipt (zs : List Int) : Option Receipt := do
  let (version, zs) ← takeNat zs
  let (oldGen, zs) ← takeNat zs
  let (expectedGen, zs) ← takeNat zs
  let (accepted, zs) ← takeBool zs
  let (newGen, zs) ← takeNat zs
  let (policyBytes, zs) ← takeBytes zs
  let (oldActive, zs) ← takeBytes zs
  let (candidate, zs) ← takeBytes zs
  let (certificate, zs) ← takeBytes zs
  let (newActive, zs) ← takeBytes zs
  if zs = [] then
    some ⟨version, policyBytes, oldGen, oldActive, expectedGen, candidate, certificate, accepted,
      newGen, newActive⟩
  else none

theorem takeBool_boolI (b : Bool) (r : List Int) : takeBool (boolI b :: r) = some (b, r) := by
  cases b <;> simp [takeBool, boolI]

theorem parseReceipt_receiptToInts (rc : Receipt) : parseReceipt (receiptToInts rc) = some rc := by
  simp only [receiptToInts, parseReceipt, List.cons_append, List.nil_append, List.append_assoc,
    takeNat_nat, takeBool_boolI, takeBytes_block, takeBytes_block_nil,
    Option.bind_eq_bind, Option.bind_some]
  simp

def encodeReceipt (rc : Receipt) : Bytes := (encodeInts receiptTag (receiptToInts rc)).map charToByte

def parseReceiptBytes (bs : Bytes) : Option Receipt :=
  if bs.all isAsciiByte then (decodeInts receiptTag (bs.map byteToChar)).bind parseReceipt else none

def decodeReceipt (bs : Bytes) : Option Receipt :=
  match parseReceiptBytes bs with
  | some rc => if encodeReceipt rc = bs then some rc else none
  | none => none

theorem decodeReceipt_encodeReceipt (rc : Receipt) : decodeReceipt (encodeReceipt rc) = some rc := by
  have ha := asciiChars_encodeInts receiptTag receiptTag_ascii (receiptToInts rc)
  have hp : parseReceiptBytes (encodeReceipt rc) = some rc := by
    unfold parseReceiptBytes encodeReceipt
    rw [if_pos (all_ascii_map_charToByte _ ha), map_byteToChar_charToByte _ ha,
      decodeInts_encodeInts receiptTag receiptTag_pipe_free, Option.bind_some,
      parseReceipt_receiptToInts]
  simp [decodeReceipt, hp]

theorem decodeReceipt_iff (bs : Bytes) (rc : Receipt) :
    decodeReceipt bs = some rc ↔ encodeReceipt rc = bs := by
  constructor
  · intro h
    unfold decodeReceipt at h
    cases hp : parseReceiptBytes bs with
    | none => simp [hp] at h
    | some rc' =>
      by_cases he : encodeReceipt rc' = bs
      · simp [hp, he] at h; subst h; exact he
      · simp [hp, he] at h
  · rintro rfl; exact decodeReceipt_encodeReceipt rc

theorem encodeReceipt_injective {a b : Receipt} (h : encodeReceipt a = encodeReceipt b) : a = b := by
  have := decodeReceipt_encodeReceipt a
  rw [h, decodeReceipt_encodeReceipt] at this
  exact (Option.some.inj this).symm

/-- Byte-level receipt checker. -/
def checkReceiptBytes (pinnedBytes rb : Bytes) : Bool :=
  match decodeReceipt rb with
  | some rc => checkReceipt pinnedBytes rc
  | none => false

theorem checkReceiptBytes_complete (s : AState) (r : Request) :
    checkReceiptBytes (encodePolicy s.policy) (encodeReceipt (propose s r).2) = true := by
  simp only [checkReceiptBytes, decodeReceipt_encodeReceipt]
  exact checkReceipt_complete s r

theorem checkReceiptBytes_sound {pinnedBytes rb : Bytes} (h : checkReceiptBytes pinnedBytes rb = true) :
    ∃ rc, encodeReceipt rc = rb ∧ ∃ p, decodePolicy pinnedBytes = some p ∧ ∃ r : Request,
      propose ⟨p, rc.oldGen, rc.oldActive⟩ r = (⟨p, rc.newGen, rc.newActive⟩, rc) := by
  unfold checkReceiptBytes at h
  cases hd : decodeReceipt rb with
  | none => rw [hd] at h; cases h
  | some rc =>
    rw [hd] at h
    exact ⟨rc, (decodeReceipt_iff rb rc).mp hd, checkReceipt_sound h⟩

/-! ## Receipt chains -/

def chainB : Nat × Bytes → List Receipt → Nat × Bytes → Bool
  | a, [], b => a == b
  | a, rc :: rcs, b => (rc.oldGen, rc.oldActive) == a && chainB (rc.newGen, rc.newActive) rcs b

theorem chainB_iff (a : Nat × Bytes) (rcs : List Receipt) (b : Nat × Bytes) :
    chainB a rcs b = true ↔ Chain a rcs b := by
  induction rcs generalizing a with
  | nil => simp [chainB, Chain]
  | cons rc rcs ih => simp [chainB, Chain, ih]

/-- **The chain checker**: the pinned policy bytes decode, every receipt passes the
independent checker, and the receipts chain from `genesis` to `final`. -/
def checkChain (pinnedBytes : Bytes) (genesis : Nat × Bytes) (rcs : List Receipt)
    (final : Nat × Bytes) : Bool :=
  (decodePolicy pinnedBytes).isSome && rcs.all (checkReceipt pinnedBytes) && chainB genesis rcs final

/-- **An accepted chain is realised by an actual authority run.** -/
theorem chain_realised {pinnedBytes : Bytes} {genesis final : Nat × Bytes} {rcs : List Receipt}
    {p : Policy} (hp : decodePolicy pinnedBytes = some p)
    (h : checkChain pinnedBytes genesis rcs final = true) :
    ∃ rs : List Request, runAdv ⟨p, genesis.1, genesis.2⟩ rs = (⟨p, final.1, final.2⟩, rcs) := by
  simp only [checkChain, Bool.and_eq_true, List.all_eq_true] at h
  obtain ⟨⟨-, hall⟩, hch⟩ := h
  have hch' := (chainB_iff _ _ _).mp hch
  clear hch
  revert hall hch'
  induction rcs generalizing genesis with
  | nil =>
    intro _ hch'
    refine ⟨[], ?_⟩
    have : genesis = final := hch'
    subst this; rfl
  | cons rc rcs ih =>
    intro hall hch'
    obtain ⟨p', hp', r, hr⟩ := checkReceipt_sound (hall rc (by simp))
    rw [hp] at hp'; cases hp'
    have hg : (rc.oldGen, rc.oldActive) = genesis := hch'.1
    obtain ⟨rs, hrs⟩ := ih (genesis := (rc.newGen, rc.newActive)) (fun x hx => hall x (by simp [hx])) hch'.2
    refine ⟨r :: rs, ?_⟩
    rw [← hg]
    simp only [runAdv, hr, hrs]

theorem checkChain_sound {pinnedBytes : Bytes} {genesis final : Nat × Bytes} {rcs : List Receipt}
    (h : checkChain pinnedBytes genesis rcs final = true) :
    ∃ p, decodePolicy pinnedBytes = some p ∧ ∃ rs : List Request,
      runAdv ⟨p, genesis.1, genesis.2⟩ rs = (⟨p, final.1, final.2⟩, rcs) := by
  have hs : (decodePolicy pinnedBytes).isSome = true := by
    simp only [checkChain, Bool.and_eq_true] at h; exact h.1.1
  cases hp : decodePolicy pinnedBytes with
  | none => rw [hp] at hs; cases hs
  | some p => exact ⟨p, rfl, chain_realised hp h⟩

/-- **Completeness of the chain checker**: the log of every authority run is accepted. -/
theorem checkChain_complete (s : AState) (rs : List Request) :
    checkChain (encodePolicy s.policy) (s.generation, s.active) (runAdv s rs).2
      ((runAdv s rs).1.generation, (runAdv s rs).1.active) = true := by
  simp only [checkChain, Bool.and_eq_true, List.all_eq_true, decodePolicy_encodePolicy,
    Option.isSome_some, true_and]
  refine ⟨fun rc hrc => ?_, (chainB_iff _ _ _).mpr (runAdv_log_chain s rs)⟩
  simp only [checkReceipt, decodePolicy_encodePolicy]
  exact (receiptOKB_iff _ _).mpr (runAdv_log_sound s rs rc hrc)

/-- Accepted receipts account for the whole generation change along a chain. -/
theorem chain_generation {p : Policy} : ∀ (rcs : List Receipt) (a b : Nat × Bytes),
    Chain a rcs b → (∀ rc ∈ rcs, ReceiptOK p rc) → b.1 = a.1 + acceptedCount rcs
  | [], a, b, h, _ => by have : a = b := h; subst this; simp [acceptedCount]
  | rc :: rcs, a, b, h, hok => by
    have ih := chain_generation rcs _ b h.2 (fun x hx => hok x (by simp [hx]))
    have ha : rc.oldGen = a.1 := congrArg Prod.fst h.1
    rcases log_generation_explained p rc (hok rc (by simp)) with ⟨hacc, hg⟩ | ⟨hacc, hg, -⟩
    · simp only [acceptedCount, List.filter_cons, hacc, if_true, List.length_cons] at ih ⊢
      omega
    · simp only [acceptedCount, List.filter_cons, hacc, Bool.false_eq_true, if_false] at ih ⊢
      omega

theorem checkChain_receipts {pinnedBytes : Bytes} {genesis final : Nat × Bytes}
    {rcs : List Receipt} {p : Policy} (hp : decodePolicy pinnedBytes = some p)
    (h : checkChain pinnedBytes genesis rcs final = true) :
    (∀ rc ∈ rcs, ReceiptOK p rc) ∧ Chain genesis rcs final := by
  simp only [checkChain, Bool.and_eq_true, List.all_eq_true] at h
  refine ⟨fun rc hrc => ?_, (chainB_iff _ _ _).mp h.2⟩
  have := h.1.2 rc hrc
  simp only [checkReceipt, hp] at this
  exact (receiptOKB_iff p rc).mp this

/-- **Invariants along an accepted chain**: from a genesis model `m₀`, the final active
bytes decode to a network that keeps every integer `m₀` got right, stays within every error
bound of `m₀` on the pinned interval, and pays one unit of pinned-corpus loss per accepted
step. -/
theorem checkChain_invariant {pinnedBytes : Bytes} {genesis final : Nat × Bytes}
    {rcs : List Receipt} {p : Policy} {m₀ : WideNet} (hp : decodePolicy pinnedBytes = some p)
    (h : checkChain pinnedBytes genesis rcs final = true)
    (h₀ : decodeBytes p.arch genesis.2 = some m₀) :
    ∃ m, decodeBytes p.arch final.2 = some m ∧
      (∀ x, predict m₀ x = predict p.target x → predict m x = predict p.target x) ∧
      (∀ B, ErrBound m₀ p.target p.lo p.hi B → ErrBound m p.target p.lo p.hi B) ∧
      acceptedCount rcs + loss p.spec.corpusSpec m ≤ loss p.spec.corpusSpec m₀ ∧
      final.1 = genesis.1 + acceptedCount rcs := by
  obtain ⟨rs, hrs⟩ := chain_realised hp h
  obtain ⟨m, ⟨-, hd, hnf, hrob⟩, hg, hl⟩ := runAdv_invariant ⟨p, genesis.1, genesis.2⟩ rs m₀ h₀
  rw [hrs] at hd hg hl
  exact ⟨m, hd, hnf, hrob, hl, hg⟩

/-! ## What a chain does not prove -/

/-- The chain of a prefix. -/
theorem chain_take : ∀ (rcs : List Receipt) (a b : Nat × Bytes) (k : Nat), Chain a rcs b →
    Chain a (rcs.take k) (replayLog a (rcs.take k))
  | [], a, _, k, _ => by simp [Chain, replayLog]
  | rc :: rcs, a, b, 0, _ => by simp [Chain, replayLog]
  | rc :: rcs, a, b, k + 1, h => by
    simp only [List.take_succ_cons, Chain, replayLog]
    exact ⟨h.1, chain_take rcs _ b k h.2⟩

/-- **Every prefix of a valid chain is a valid chain** (to an earlier state). -/
theorem prefix_valid {pinnedBytes : Bytes} {genesis final : Nat × Bytes} {rcs : List Receipt}
    (h : checkChain pinnedBytes genesis rcs final = true) (k : Nat) :
    checkChain pinnedBytes genesis (rcs.take k) (replayLog genesis (rcs.take k)) = true := by
  simp only [checkChain, Bool.and_eq_true, List.all_eq_true] at h ⊢
  refine ⟨⟨h.1.1, fun rc hrc => h.1.2 rc (List.mem_of_mem_take hrc)⟩, ?_⟩
  exact (chainB_iff _ _ _).mpr (chain_take rcs genesis final k ((chainB_iff _ _ _).mp h.2))

/-- The receipts of the three-step robust chain, as emitted by the authority. -/
def wideReceipts : List Receipt := (runAdv ⟨pinned0, 0, encodeBytes gen0⟩ genuineReqs).2

theorem wideReceipts_valid :
    checkChain (encodePolicy pinned0) (0, encodeBytes gen0) wideReceipts (3, encodeBytes gen3) = true := by
  decide +kernel

/-- **Prefix (rollback) attack**: the one-receipt prefix is also a valid chain; it ends at
generation 1 with `r1`, which is wrong at `x = 0`, where the current `gen3` is right. -/
theorem prefix_attack :
    checkChain (encodePolicy pinned0) (0, encodeBytes gen0) (wideReceipts.take 1) (1, encodeBytes r1) = true ∧
    predict gen3 0 = predict pinned0.target 0 ∧ predict r1 0 ≠ predict pinned0.target 0 := by
  refine ⟨?_, by decide, by decide⟩
  decide +kernel

/-- A direct certificate for `gen0 ↦ gen3`. -/
def directReq : Request := ⟨[], 0, [], encodeCert (genCert specWide 0 gen0 gen3)⟩

/-- **Fork attack**: two different valid chains from the same genesis reach generation 1
with different active models (`r1` and `gen3`): the generation alone does not identify
the authoritative state. -/
theorem fork_attack :
    checkChain (encodePolicy pinned0) (0, encodeBytes gen0) (wideReceipts.take 1) (1, encodeBytes r1) = true ∧
    checkChain (encodePolicy pinned0) (0, encodeBytes gen0)
      (runAdv ⟨pinned0, 0, encodeBytes gen0⟩ [directReq]).2 (1, encodeBytes gen3) = true ∧
    encodeBytes r1 ≠ encodeBytes gen3 := by
  refine ⟨prefix_attack.1, ?_, by decide⟩
  decide +kernel

/-! ## External anchoring (explicit assumption) -/

/-- An anchor: the authoritative `(generation, active bytes)` read from protected,
monotonic storage. **That storage is an assumption, not implemented here.** -/
abbrev Anchor := Nat × Bytes

/-- Anchored verification: the chain must end exactly at the anchor. -/
def checkAnchored (pinnedBytes : Bytes) (genesis : Nat × Bytes) (rcs : List Receipt)
    (anchor : Anchor) : Bool :=
  checkChain pinnedBytes genesis rcs anchor

/-- **Anchored soundness**: the anchored active model satisfies every invariant relative
to the genesis model. -/
theorem anchored_sound {pinnedBytes : Bytes} {genesis : Nat × Bytes} {rcs : List Receipt}
    {anchor : Anchor} {p : Policy} {m₀ : WideNet} (hp : decodePolicy pinnedBytes = some p)
    (h : checkAnchored pinnedBytes genesis rcs anchor = true)
    (h₀ : decodeBytes p.arch genesis.2 = some m₀) :
    ∃ m, decodeBytes p.arch anchor.2 = some m ∧
      (∀ x, predict m₀ x = predict p.target x → predict m x = predict p.target x) ∧
      (∀ B, ErrBound m₀ p.target p.lo p.hi B → ErrBound m p.target p.lo p.hi B) ∧
      anchor.1 = genesis.1 + acceptedCount rcs :=
  let ⟨m, h1, h2, h3, _, h5⟩ := checkChain_invariant hp h h₀
  ⟨m, h1, h2, h3, h5⟩

/-- **Anchoring rejects stale prefixes**: a prefix with fewer accepted receipts than the
anchored chain is rejected against the same anchor. -/
theorem anchored_rejects_prefix {pinnedBytes : Bytes} {genesis : Nat × Bytes}
    {rcs : List Receipt} {anchor : Anchor} (h : checkAnchored pinnedBytes genesis rcs anchor = true)
    (k : Nat) (hk : acceptedCount (rcs.take k) < acceptedCount rcs) :
    checkAnchored pinnedBytes genesis (rcs.take k) anchor = false := by
  cases hc : checkAnchored pinnedBytes genesis (rcs.take k) anchor with
  | false => rfl
  | true =>
    obtain ⟨p, hp, -⟩ := checkChain_sound h
    obtain ⟨hok, hch⟩ := checkChain_receipts hp h
    obtain ⟨hok', hch'⟩ := checkChain_receipts hp hc
    have e1 := chain_generation rcs genesis anchor hch hok
    have e2 := chain_generation (rcs.take k) genesis anchor hch' hok'
    omega

/-- Two anchored chains end at the same state: the anchor. -/
theorem anchored_unique_state {pinnedBytes : Bytes} {genesis : Nat × Bytes}
    {rcs₁ rcs₂ : List Receipt} {anchor : Anchor}
    (h₁ : checkAnchored pinnedBytes genesis rcs₁ anchor = true)
    (h₂ : checkAnchored pinnedBytes genesis rcs₂ anchor = true) :
    replayLog genesis rcs₁ = replayLog genesis rcs₂ := by
  obtain ⟨p, hp, -⟩ := checkChain_sound h₁
  rw [chain_replay (checkChain_receipts hp h₁).2, chain_replay (checkChain_receipts hp h₂).2]

/-- **With the authoritative anchor, the prefix attack fails** (the anchor is `(3, gen3)`). -/
theorem anchored_prefix_rejected :
    checkAnchored (encodePolicy pinned0) (0, encodeBytes gen0) (wideReceipts.take 1)
      (3, encodeBytes gen3) = false := by
  decide +kernel

/-- **Without monotonic anchoring the rollback succeeds**: if an attacker can reset the
anchor to an older value, the old prefix is accepted. -/
theorem rollback_without_monotonic_anchor :
    checkAnchored (encodePolicy pinned0) (0, encodeBytes gen0) (wideReceipts.take 1)
      (1, encodeBytes r1) = true := prefix_attack.1

/-- Every receipt of the robust chain, serialised as `PGSR7` bytes, passes the byte-level
checker. -/
theorem wideReceipts_bytes_ok :
    ∀ rc ∈ wideReceipts, checkReceiptBytes (encodePolicy pinned0) (encodeReceipt rc) = true := by
  intro rc h
  simp only [checkReceiptBytes, decodeReceipt_encodeReceipt, checkReceipt, decodePolicy_encodePolicy]
  exact (receiptOKB_iff _ _).mpr (runAdv_log_sound _ _ rc h)

end PCS.V2.ProofGatedReceipt
