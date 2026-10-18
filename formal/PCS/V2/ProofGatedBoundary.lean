import PCS.V2.ProofGatedPolicy
import PCS.V2.ProofGatedInterpreter
import PCS.V2.ProofGatedProtocol

/-!
# V7 Priority 2: the trusted/untrusted boundary as a pure state machine

**Trusted state** (`AState`): the pinned policy, the generation and the exact active
artifact bytes. The checker implementation is *code*: the fixed table `runChecker`
(selected by the pinned policy's `checker` field), not data in any request.

**Two input channels** (`Event`):
* `propose r` — the untrusted proposer's channel. `r : Request` is arbitrary data
  (requested policy, requested generation, requested incumbent, certificate bytes that
  embed the candidate artifact);
* `govern p` — the separately governed channel that may replace the policy.

The adversary controls only the first channel: an adversarial trace is a `List Request`,
and `runEvents_proposals` shows that it is interpreted exactly as the event trace
`rs.map Event.propose`, which contains no governance event. **The type of the proposer's
input does not contain a policy-replacement operation**; `propose_policy_frame` shows that no
proposal changes the policy, and `policy_change_needs_governance` that any policy change in
a mixed trace is caused by a governance event.

Every proposal produces a receipt (`Receipt`; codec and independent checker in
`ProofGatedReceipt`) recording the policy bytes, the old state, the expected generation,
the certificate, the decision, the committed candidate and the new state.

## Safety results (all adversarial request sequences)

1. `propose_reject_frame` — a rejected request changes neither the active model nor the
   policy nor the generation;
2. `propose_accept_unique` — an accepted request corresponds to exactly one canonical
   certificate accepted under the pinned policy;
3. `propose_accept_generation` — a commit advances the generation by one, and the accepted
   certificate names the current generation and the exact current incumbent (no stale
   incumbent); `accepted_cert_at_most_once` — a certificate is accepted at most once in any
   trace (replay protection);
4. `runAdv_invariant` — no-forgetting on every integer, the interval-error bound and the
   improvement accounting relative to the initial model, the policy unchanged;
5. `authorized_predict` — what the authority serves (`servePred`, via the reference byte
   interpreter) is exactly `predict m` of the network `m` whose canonical bytes are
   committed;
6. `runAdv_log_sound`, `runAdv_log_chain`, `log_generation_explained`, `replay_log` — every
   receipt is a real transition, receipts chain, every generation change is an accepted
   receipt, and replaying the log reconstructs the final state.

## Safety versus liveness

* `adversary_can_stall`: an adversary that controls all proposals can prevent all
  progress — liveness is impossible without assumptions on the proposer;
* `honest_progress`: if an admissible successor exists, an honest request built from the
  current state is accepted;
* `race_one_winner`: two requests built from the same state cannot both commit
  (linearisation at the atomic commit);
* `progress_bounded`: every trace has at most `loss m₀` acceptances, so uninterrupted
  forward progress is impossible in principle;
* `dead_end_stuck`: there are policies and reachable states with nonzero loss from which
  **no** request is ever accepted, even from an honest proposer.

## Crash consistency (abstract model)

`Disk` models durable storage with a staging slot; handling a request is split into
micro-steps (verify → stage → commit (atomic pointer swap) → log → clear). For a crash
after **any** micro-step of **any** request, `recover` yields exactly the abstract state
after either the completed requests or one more (`crash_recover_consistent`). This proves
the abstract protocol is crash-consistent *given* that the atomic commit, durable writes
and read-after-write behave as modelled; it does not prove that a filesystem provides
these primitives.
-/

namespace PCS.V2.ProofGatedBoundary

open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedCert7
open PCS.V2.ProofGatedPolicy
open PCS.V2.ProofGatedInterpreter

/-- Trusted authority state. -/
structure AState where
  policy : Policy
  generation : Nat
  active : Bytes
  deriving Repr, DecidableEq

def receiptVersion : Nat := 7

/-- A transition receipt. -/
structure Receipt where
  version : Nat
  policyBytes : Bytes
  oldGen : Nat
  oldActive : Bytes
  expectedGen : Nat
  candidate : Bytes
  certificate : Bytes
  accepted : Bool
  newGen : Nat
  newActive : Bytes
  deriving Repr, DecidableEq

def mkReceipt (s : AState) (cb : Bytes) : Option Bytes → Receipt
  | some cand => ⟨receiptVersion, encodePolicy s.policy, s.generation, s.active, s.generation,
      cand, cb, true, s.generation + 1, cand⟩
  | none => ⟨receiptVersion, encodePolicy s.policy, s.generation, s.active, s.generation,
      [], cb, false, s.generation, s.active⟩

/-- **One proposal**: the verdict is the pinned-policy verdict (`safeDecide`). -/
def propose (s : AState) (r : Request) : AState × Receipt :=
  match safeDecide s.policy s.generation s.active r with
  | some cand => (⟨s.policy, s.generation + 1, cand⟩, mkReceipt s r.certificate (some cand))
  | none => (s, mkReceipt s r.certificate none)

/-- An adversarial run: only the proposal channel. -/
def runAdv : AState → List Request → AState × List Receipt
  | s, [] => (s, [])
  | s, r :: rs =>
    let p := propose s r
    let rest := runAdv p.1 rs
    (rest.1, p.2 :: rest.2)

/-! ## The two channels -/

inductive Event
  | propose (r : Request)
  | govern (p : Policy)
  deriving Repr, DecidableEq

/-- Governance may install a new supported policy under which the active artifact still
decodes. -/
def govern (s : AState) (p : Policy) : AState :=
  if p.supported ∧ (decodeBytes p.arch s.active).isSome then { s with policy := p } else s

def runEvents : AState → List Event → AState × List Receipt
  | s, [] => (s, [])
  | s, .propose r :: es =>
    let p := propose s r
    let rest := runEvents p.1 es
    (rest.1, p.2 :: rest.2)
  | s, .govern q :: es => runEvents (govern s q) es

def isGovern : Event → Bool
  | .govern _ => true
  | .propose _ => false

/-- The proposer's channel is interpreted as governance-free events. -/
theorem runEvents_proposals (s : AState) (rs : List Request) :
    runEvents s (rs.map Event.propose) = runAdv s rs := by
  induction rs generalizing s with
  | nil => rfl
  | cons r rs ih => simp only [List.map_cons, runEvents, runAdv, ih]

theorem proposals_no_governance (rs : List Request) : ∀ e ∈ rs.map Event.propose, isGovern e = false := by
  intro e he
  simp only [List.mem_map] at he
  obtain ⟨_, _, rfl⟩ := he
  rfl

/-! ## Single proposals -/

theorem propose_policy_frame (s : AState) (r : Request) : (propose s r).1.policy = s.policy := by
  unfold propose
  cases safeDecide s.policy s.generation s.active r <;> rfl

theorem propose_cases (s : AState) (r : Request) :
    (safeDecide s.policy s.generation s.active r = none ∧ (propose s r).1 = s ∧
      (propose s r).2 = mkReceipt s r.certificate none) ∨
    (∃ cand, safeDecide s.policy s.generation s.active r = some cand ∧
      (propose s r).1 = ⟨s.policy, s.generation + 1, cand⟩ ∧
      (propose s r).2 = mkReceipt s r.certificate (some cand)) := by
  unfold propose
  cases h : safeDecide s.policy s.generation s.active r with
  | none => exact Or.inl ⟨rfl, rfl, rfl⟩
  | some cand => exact Or.inr ⟨cand, rfl, rfl, rfl⟩

/-- **(1) Rejected requests change nothing.** -/
theorem propose_reject_frame {s : AState} {r : Request} (h : (propose s r).2.accepted = false) :
    (propose s r).1 = s := by
  rcases propose_cases s r with ⟨_, h1, _⟩ | ⟨cand, _, _, h3⟩
  · exact h1
  · rw [h3] at h; cases h

/-- **(2) An accepted request corresponds to exactly one canonical certificate accepted
under the pinned policy.** -/
theorem propose_accept_unique {s : AState} {r : Request} (h : (propose s r).2.accepted = true) :
    (s.policy.checker = checkerPGSC6 ∧ ∃ c, (encodeCert c = r.certificate ∧
        checkCert s.policy.spec s.generation s.active c = true) ∧
      ∀ c', encodeCert c' = r.certificate → c' = c) ∨
    (s.policy.checker = checkerPGSC7 ∧ ∃ c, (encodeCert7 c = r.certificate ∧
        checkCert7 s.policy.spec s.generation s.active c = true) ∧
      ∀ c', encodeCert7 c' = r.certificate → c' = c) := by
  rcases propose_cases s r with ⟨_, _, h3⟩ | ⟨cand, h1, _, _⟩
  · rw [h3] at h; cases h
  · exact runChecker_unique_cert h1

/-- **(3) Commits advance the generation, and the accepted certificate names the current
generation and the exact current incumbent.** -/
theorem propose_accept_generation {s : AState} {r : Request}
    (h : (propose s r).2.accepted = true) :
    (propose s r).1.generation = s.generation + 1 ∧ (propose s r).1.policy = s.policy ∧
    Accepts s.policy s.generation s.active r.certificate (propose s r).1.active := by
  rcases propose_cases s r with ⟨_, _, h3⟩ | ⟨cand, h1, h2, _⟩
  · rw [h3] at h; cases h
  · rw [h2]; exact ⟨rfl, rfl, (runChecker_accepts h1).2⟩

/-- The semantic content of an accepted proposal. -/
theorem propose_accept_sound {s : AState} {r : Request} (h : (propose s r).2.accepted = true) :
    ∃ o n, decodeBytes s.policy.arch s.active = some o ∧
      decodeBytes s.policy.arch (propose s r).1.active = some n ∧
      encodeBytes n = (propose s r).1.active ∧ StrongAdmissible s.policy.spec o n := by
  rcases propose_cases s r with ⟨_, _, h3⟩ | ⟨cand, h1, h2, _⟩
  · rw [h3] at h; cases h
  · rw [h2]; exact safeDecide_sound h1

/-! ## Adversarial traces -/

def acceptedCount (log : List Receipt) : Nat := (log.filter (·.accepted)).length

theorem runAdv_policy (s : AState) (rs : List Request) : (runAdv s rs).1.policy = s.policy := by
  induction rs generalizing s with
  | nil => rfl
  | cons r rs ih => simp only [runAdv]; rw [ih, propose_policy_frame]

/-- The invariant relative to the initial model `m₀`, under the pinned policy `p`. -/
def Inv (p : Policy) (m₀ : WideNet) (s : AState) (m : WideNet) : Prop :=
  s.policy = p ∧ decodeBytes p.arch s.active = some m ∧
  (∀ x, predict m₀ x = predict p.target x → predict m x = predict p.target x) ∧
  (∀ B, ErrBound m₀ p.target p.lo p.hi B → ErrBound m p.target p.lo p.hi B)

/-- **(4) Preservation over arbitrary adversarial request sequences.** -/
theorem runAdv_invariant (s : AState) (rs : List Request) (m₀ : WideNet)
    (h₀ : decodeBytes s.policy.arch s.active = some m₀) :
    ∃ m, Inv s.policy m₀ (runAdv s rs).1 m ∧
      (runAdv s rs).1.generation = s.generation + acceptedCount (runAdv s rs).2 ∧
      acceptedCount (runAdv s rs).2 + loss s.policy.spec.corpusSpec m ≤
        loss s.policy.spec.corpusSpec m₀ := by
  suffices H : ∀ (rs : List Request) (s : AState) (m₁ : WideNet), Inv s.policy m₀ s m₁ →
      ∃ m, Inv s.policy m₀ (runAdv s rs).1 m ∧
        (runAdv s rs).1.generation = s.generation + acceptedCount (runAdv s rs).2 ∧
        acceptedCount (runAdv s rs).2 + loss s.policy.spec.corpusSpec m ≤
          loss s.policy.spec.corpusSpec m₁ by
    exact H rs s m₀ ⟨rfl, h₀, fun _ h => h, fun _ h => h⟩
  intro rs
  induction rs with
  | nil =>
    intro s m₁ hI
    exact ⟨m₁, hI, by simp [runAdv, acceptedCount], by simp [runAdv, acceptedCount]⟩
  | cons r rs ih =>
    intro s m₁ hI
    have hpol := propose_policy_frame s r
    rcases propose_cases s r with ⟨hd, hs, hrc⟩ | ⟨cand, hd, hs, hrc⟩
    · obtain ⟨m, hm, hg, hl⟩ := ih (propose s r).1 m₁ (by rw [hs]; exact hI)
      rw [hs] at hm hg hl
      refine ⟨m, ?_, ?_, ?_⟩
      · simp only [runAdv, hs]; exact hm
      · simp only [runAdv, acceptedCount, List.filter_cons, hrc, mkReceipt] at hg ⊢
        simpa [hs] using hg
      · simp only [runAdv, acceptedCount, List.filter_cons, hrc, mkReceipt] at hl ⊢
        simpa [hs] using hl
    · obtain ⟨o, n, ho, hn, -, hadm⟩ := safeDecide_sound hd
      have hIo := hI.2.1
      rw [hI.1] at ho
      rw [hIo] at ho; cases ho
      have hpe : s.policy = (propose s r).1.policy := hpol.symm
      have hI' : Inv s.policy m₀ (propose s r).1 n := by
        refine ⟨hpol, ?_, fun x hx => ?_, fun B hB => ?_⟩
        · rw [hs]; exact hI.1 ▸ hn
        · have := hadm.2.1 x (hI.1 ▸ hI.2.2.1 x hx); rw [← hI.1] at this ⊢; exact this
        · have := hadm.2.2 B (hI.1 ▸ hI.2.2.2 B hB); rw [← hI.1] at this ⊢; exact this
      obtain ⟨m, hm, hg, hl⟩ := ih (propose s r).1 n (by rw [← hpe]; exact hI')
      rw [← hpe] at hm hl
      have hlt := hadm.1.2.2.2.2
      refine ⟨m, ?_, ?_, ?_⟩
      · simp only [runAdv]; exact hm
      · simp only [runAdv, acceptedCount, List.filter_cons, hrc, mkReceipt, if_true,
          List.length_cons] at hg ⊢
        rw [hg, hs]; simp only; omega
      · simp only [runAdv, acceptedCount, List.filter_cons, hrc, mkReceipt, if_true,
          List.length_cons] at hl ⊢
        omega

/-! ## (5) Authorised predictions -/

/-- What the authority serves: the reference byte interpreter on the active bytes, under the
pinned architecture. -/
def servePred (s : AState) (x : Int) : Option Int := interpBytes s.policy.arch s.active x

/-- **Authorised predictions are exactly the committed network's.** -/
theorem authorized_predict (s : AState) (rs : List Request) (m₀ : WideNet)
    (h₀ : decodeBytes s.policy.arch s.active = some m₀) :
    ∃ m, encodeBytes m = (runAdv s rs).1.active ∧ valid s.policy.arch m = true ∧
      ∀ x, servePred (runAdv s rs).1 x = some (predict m x) := by
  obtain ⟨m, ⟨hp, hd, -, -⟩, -, -⟩ := runAdv_invariant s rs m₀ h₀
  refine ⟨m, decodeBytes_canonical hd, decodeBytes_valid hd, fun x => ?_⟩
  simp only [servePred, hp, interpBytes_eq_inferBytes, inferBytes, hd, Option.map_some]

/-! ## (6) The audit log -/

/-- A receipt that records a genuine transition under the pinned policy. -/
def ReceiptOK (pol : Policy) (rc : Receipt) : Prop :=
  rc.version = receiptVersion ∧ rc.policyBytes = encodePolicy pol ∧ rc.expectedGen = rc.oldGen ∧
  (if rc.accepted then
    runChecker pol rc.oldGen rc.oldActive rc.certificate = some rc.candidate ∧
      rc.newGen = rc.oldGen + 1 ∧ rc.newActive = rc.candidate
  else
    runChecker pol rc.oldGen rc.oldActive rc.certificate = none ∧ rc.candidate = [] ∧
      rc.newGen = rc.oldGen ∧ rc.newActive = rc.oldActive)

theorem propose_receipt_ok (s : AState) (r : Request) : ReceiptOK s.policy (propose s r).2 := by
  rcases propose_cases s r with ⟨hd, _, hrc⟩ | ⟨cand, hd, _, hrc⟩
  · rw [hrc]; simp [ReceiptOK, mkReceipt]; exact hd
  · rw [hrc]; simp [ReceiptOK, mkReceipt]; exact hd

theorem propose_receipt_states (s : AState) (r : Request) :
    (propose s r).2.oldGen = s.generation ∧ (propose s r).2.oldActive = s.active ∧
    (propose s r).2.newGen = (propose s r).1.generation ∧
    (propose s r).2.newActive = (propose s r).1.active ∧
    (propose s r).2.certificate = r.certificate := by
  rcases propose_cases s r with ⟨_, hs, hrc⟩ | ⟨cand, _, hs, hrc⟩
  · rw [hrc, hs]; exact ⟨rfl, rfl, rfl, rfl, rfl⟩
  · rw [hrc, hs]; exact ⟨rfl, rfl, rfl, rfl, rfl⟩

/-- **Every receipt in the log records a genuine transition under the pinned policy.** -/
theorem runAdv_log_sound (s : AState) (rs : List Request) :
    ∀ rc ∈ (runAdv s rs).2, ReceiptOK s.policy rc := by
  induction rs generalizing s with
  | nil => simp [runAdv]
  | cons r rs ih =>
    intro rc hrc
    simp only [runAdv, List.mem_cons] at hrc
    rcases hrc with rfl | hrc
    · exact propose_receipt_ok s r
    · have := ih (propose s r).1 rc hrc
      rwa [propose_policy_frame] at this

/-- Receipts chain from a state to a state. -/
def Chain : Nat × Bytes → List Receipt → Nat × Bytes → Prop
  | a, [], b => a = b
  | a, rc :: rcs, b => (rc.oldGen, rc.oldActive) = a ∧ Chain (rc.newGen, rc.newActive) rcs b

theorem runAdv_log_chain (s : AState) (rs : List Request) :
    Chain (s.generation, s.active) (runAdv s rs).2 ((runAdv s rs).1.generation, (runAdv s rs).1.active) := by
  induction rs generalizing s with
  | nil => rfl
  | cons r rs ih =>
    obtain ⟨h1, h2, h3, h4, -⟩ := propose_receipt_states s r
    simp only [runAdv, Chain]
    refine ⟨by rw [h1, h2], ?_⟩
    rw [h3, h4]; exact ih _

/-- **No unexplained generation changes**: a receipt changes the generation iff it is an
acceptance, and then by exactly one. -/
theorem log_generation_explained (pol : Policy) (rc : Receipt) (h : ReceiptOK pol rc) :
    (rc.accepted = true ∧ rc.newGen = rc.oldGen + 1) ∨
      (rc.accepted = false ∧ rc.newGen = rc.oldGen ∧ rc.newActive = rc.oldActive) := by
  obtain ⟨-, -, -, h⟩ := h
  cases ha : rc.accepted
  · rw [ha] at h; simp only [Bool.false_eq_true, if_false] at h
    exact Or.inr ⟨rfl, h.2.2.1, h.2.2.2⟩
  · rw [ha] at h; simp only [if_true] at h
    exact Or.inl ⟨rfl, h.2.1⟩

/-- Replaying a receipt log from a state. -/
def replayLog : Nat × Bytes → List Receipt → Nat × Bytes
  | a, [] => a
  | _, rc :: rcs => replayLog (rc.newGen, rc.newActive) rcs

theorem chain_replay {a b : Nat × Bytes} {rcs : List Receipt} (h : Chain a rcs b) : replayLog a rcs = b := by
  induction rcs generalizing a with
  | nil => exact h
  | cons rc rcs ih => exact ih h.2

/-- **Replaying the audit log reconstructs the final state.** -/
theorem replay_log (s : AState) (rs : List Request) :
    replayLog (s.generation, s.active) (runAdv s rs).2 =
      ((runAdv s rs).1.generation, (runAdv s rs).1.active) :=
  chain_replay (runAdv_log_chain s rs)

/-- Accepted receipts carry strictly increasing old generations along a chain. -/
theorem chain_gen_mono {pol : Policy} :
    ∀ (rcs : List Receipt) (a b : Nat × Bytes), Chain a rcs b → (∀ rc ∈ rcs, ReceiptOK pol rc) →
      ∀ rc ∈ rcs, a.1 ≤ rc.oldGen ∧ rc.newGen ≤ b.1 := by
  intro rcs
  induction rcs with
  | nil => intro a b _ _ rc h; simp at h
  | cons rc rcs ih =>
    intro a b hc hok rc' hrc'
    have hgen : rc.oldGen ≤ rc.newGen := by
      rcases log_generation_explained pol rc (hok rc (by simp)) with ⟨_, h⟩ | ⟨_, h, _⟩ <;> omega
    have hrest := ih (rc.newGen, rc.newActive) b hc.2 (fun x hx => hok x (by simp [hx]))
    have ha : a.1 = rc.oldGen := by rw [← hc.1]
    simp only [List.mem_cons] at hrc'
    rcases hrc' with rfl | hrc'
    · refine ⟨by omega, ?_⟩
      cases rcs with
      | nil => have := hc.2; simp only [Chain] at this; rw [← this]; exact Nat.le_refl _
      | cons rc2 rcs2 =>
        have := hrest rc2 (by simp)
        have h2 : (rc2.oldGen, rc2.oldActive) = (rc'.newGen, rc'.newActive) := hc.2.1
        have : rc2.oldGen = rc'.newGen := congrArg Prod.fst h2
        have hg2 : rc2.oldGen ≤ rc2.newGen := by
          rcases log_generation_explained pol rc2 (hok rc2 (by simp)) with ⟨_, h⟩ | ⟨_, h, _⟩ <;> omega
        omega
    · have := hrest rc' hrc'
      exact ⟨by simp only at this; omega, this.2⟩

/-- **Replay protection**: two accepted receipts of a log with the same certificate bytes
are the same position — formally, along any chain of genuine receipts, accepted receipts
with equal certificate bytes have equal old generations, and old generations of accepted
receipts strictly increase. -/
theorem accepted_same_cert_same_gen {pol : Policy} {rc₁ rc₂ : Receipt}
    (h₁ : ReceiptOK pol rc₁) (h₂ : ReceiptOK pol rc₂) (ha₁ : rc₁.accepted = true)
    (ha₂ : rc₂.accepted = true) (hc : rc₁.certificate = rc₂.certificate) :
    rc₁.oldGen = rc₂.oldGen := by
  obtain ⟨-, -, -, h₁⟩ := h₁
  obtain ⟨-, -, -, h₂⟩ := h₂
  rw [ha₁] at h₁; rw [ha₂] at h₂
  simp only [if_true] at h₁ h₂
  obtain ⟨-, acc₁⟩ := runChecker_accepts h₁.1
  obtain ⟨-, acc₂⟩ := runChecker_accepts h₂.1
  rw [hc] at acc₁
  rcases acc₁ with ⟨_, c₁, e₁, -, g₁, -⟩ | ⟨h7, c₁, e₁, -, g₁, -⟩ <;>
    rcases acc₂ with ⟨h6', c₂, e₂, -, g₂, -⟩ | ⟨h7', c₂, e₂, -, g₂, -⟩
  · rw [← g₁, ← g₂, encodeCert_injective (e₁.trans e₂.symm)]
  · exact absurd (e₁.trans e₂.symm) (pgsc6_not_pgsc7 c₁ c₂)
  · exact absurd (e₂.trans e₁.symm) (pgsc6_not_pgsc7 c₂ c₁)
  · rw [← g₁, ← g₂, encodeCert7_injective (e₁.trans e₂.symm)]

/-- Positions of accepted receipts in a log. -/
def acceptedGens (log : List Receipt) : List Nat := (log.filter (·.accepted)).map (·.oldGen)

theorem runAdv_acceptedGens (s : AState) (rs : List Request) :
    (acceptedGens (runAdv s rs).2).Pairwise (· < ·) ∧
      ∀ g ∈ acceptedGens (runAdv s rs).2, s.generation ≤ g := by
  induction rs generalizing s with
  | nil => simp [runAdv, acceptedGens]
  | cons r rs ih =>
    obtain ⟨ih1, ih2⟩ := ih (propose s r).1
    obtain ⟨h1, h2, h3, h4, -⟩ := propose_receipt_states s r
    have hmono : s.generation ≤ (propose s r).1.generation := by
      rcases propose_cases s r with ⟨_, hs, _⟩ | ⟨_, _, hs, _⟩ <;> (rw [hs]; simp)
    by_cases ha : (propose s r).2.accepted = true
    · have hg := (propose_accept_generation ha).1
      simp only [runAdv, acceptedGens, List.filter_cons, ha, if_true, List.map_cons,
        List.pairwise_cons, List.mem_cons] at ih1 ih2 ⊢
      refine ⟨⟨fun g hg' => ?_, ih1⟩, ?_⟩
      · have := ih2 g hg'; rw [h1]; omega
      · rintro g (rfl | hg')
        · rw [h1]; omega
        · have := ih2 g hg'; omega
    · simp only [Bool.not_eq_true] at ha
      simp only [runAdv, acceptedGens, List.filter_cons, ha, Bool.false_eq_true, if_false] at ih1 ih2 ⊢
      exact ⟨ih1, fun g hg => by have := ih2 g hg; omega⟩

/-- **A certificate is accepted at most once in any adversarial trace.** -/
theorem accepted_cert_at_most_once (s : AState) (rs : List Request) (i j : Nat)
    (hi : i < ((runAdv s rs).2.filter (·.accepted)).length)
    (hj : j < ((runAdv s rs).2.filter (·.accepted)).length) (hij : i < j) :
    ((runAdv s rs).2.filter (·.accepted))[i].certificate ≠
      ((runAdv s rs).2.filter (·.accepted))[j].certificate := by
  intro heq
  have hok : ∀ rc ∈ (runAdv s rs).2.filter (·.accepted), ReceiptOK s.policy rc ∧ rc.accepted = true :=
    fun rc h => ⟨runAdv_log_sound s rs rc (List.mem_filter.mp h).1,
      by simpa using (List.mem_filter.mp h).2⟩
  have hi' := hok _ (List.getElem_mem hi)
  have hj' := hok _ (List.getElem_mem hj)
  have hg := accepted_same_cert_same_gen hi'.1 hj'.1 hi'.2 hj'.2 heq
  have hpw := (runAdv_acceptedGens s rs).1
  unfold acceptedGens at hpw
  have := List.pairwise_iff_getElem.mp hpw i j (by simpa using hi) (by simpa using hj) hij
  simp only [List.getElem_map] at this
  omega

/-! ## Governance -/

/-- **A policy change requires a governance event.** -/
theorem policy_change_needs_governance (s : AState) (es : List Event)
    (h : (runEvents s es).1.policy ≠ s.policy) : ∃ e ∈ es, isGovern e = true := by
  induction es generalizing s with
  | nil => exact absurd rfl h
  | cons e es ih =>
    cases e with
    | govern q => exact ⟨.govern q, by simp, rfl⟩
    | propose r =>
      simp only [runEvents] at h
      obtain ⟨e', he', hg⟩ := ih (propose s r).1 (by rwa [propose_policy_frame])
      exact ⟨e', by simp [he'], hg⟩

/-- Governance never installs an unsupported policy or one under which the active
artifact does not decode. -/
theorem govern_safe (s : AState) (p : Policy) :
    govern s p = s ∨ (govern s p = { s with policy := p } ∧ p.supported ∧
      (decodeBytes p.arch s.active).isSome) := by
  unfold govern
  by_cases h : p.supported ∧ (decodeBytes p.arch s.active).isSome = true
  · rw [if_pos h]; exact Or.inr ⟨rfl, h.1, h.2⟩
  · rw [if_neg h]; exact Or.inl rfl

/-! ## Safety versus liveness -/

theorem joinFields_ne_nil (f : List Char) (hf : f ≠ []) (fs : List (List Char)) :
    PCS.V2.ProofGatedCodec.joinFields (f :: fs) ≠ [] := by
  cases fs <;> simp [PCS.V2.ProofGatedCodec.joinFields, hf]

theorem encodeCert_ne_nil (c : Cert) : encodeCert c ≠ [] := by
  simp only [encodeCert, encodeCertChars, PCS.V2.ProofGatedCodec.encodeInts, ne_eq,
    List.map_eq_nil_iff]
  exact joinFields_ne_nil _ (by decide) _

theorem encodeCert7_ne_nil (c : Cert7) : encodeCert7 c ≠ [] := by
  simp only [encodeCert7, PCS.V2.ProofGatedCodec.encodeInts, ne_eq, List.map_eq_nil_iff]
  exact joinFields_ne_nil _ (by decide) _

/-- **An adversary controlling every proposal can stall the system forever.** -/
theorem adversary_can_stall (s : AState) (n : Nat) :
    (runAdv s (List.replicate n ⟨[], 0, [], []⟩)).1 = s := by
  induction n with
  | zero => rfl
  | succ n ih =>
    have hr : safeDecide s.policy s.generation s.active ⟨[], 0, [], []⟩ = none := by
      cases h : safeDecide s.policy s.generation s.active ⟨[], 0, [], []⟩ with
      | none => rfl
      | some cand =>
        obtain ⟨-, acc⟩ := runChecker_accepts h
        rcases acc with ⟨-, c, e, -⟩ | ⟨-, c, e, -⟩
        · exact absurd e (encodeCert_ne_nil c)
        · exact absurd e (encodeCert7_ne_nil c)
    have hp : propose s ⟨[], 0, [], []⟩ = (s, mkReceipt s [] none) := by
      simp only [propose, hr]
    simp only [List.replicate_succ, runAdv, hp, ih]

/-- **Honest progress**: if an admissible successor exists under a supported pinned
policy, the honest request built from the current state is accepted. -/
theorem honest_progress (s : AState) (hp : s.policy.supported) (o n : WideNet)
    (ho : s.active = encodeBytes o) (h : StrongAdmissible s.policy.spec o n) :
    ∃ r : Request, (propose s r).2.accepted = true ∧ (propose s r).1.active = encodeBytes n ∧
      (propose s r).1.generation = s.generation + 1 := by
  obtain ⟨cb, hcb⟩ := runChecker_complete s.policy hp s.generation o n h
  refine ⟨⟨encodePolicy s.policy, s.generation, s.active, cb⟩, ?_⟩
  have hd : safeDecide s.policy s.generation s.active ⟨encodePolicy s.policy, s.generation, s.active, cb⟩ =
      some (encodeBytes n) := by
    show runChecker s.policy s.generation s.active cb = _
    rw [ho]; exact hcb
  simp [propose, hd, mkReceipt]

/-- **Linearisation / race**: if two requests would both be accepted at `s`, then after
the first commits, the second is rejected. -/
theorem race_one_winner (s : AState) (r₁ r₂ : Request)
    (h₁ : (propose s r₁).2.accepted = true) (h₂ : (propose s r₂).2.accepted = true) :
    (propose (propose s r₁).1 r₂).2.accepted = false := by
  obtain ⟨hg₁, hp₁, -⟩ := propose_accept_generation h₁
  obtain ⟨-, -, acc₂⟩ := propose_accept_generation h₂
  cases h : (propose (propose s r₁).1 r₂).2.accepted with
  | false => rfl
  | true =>
    obtain ⟨-, -, acc⟩ := propose_accept_generation h
    rw [hp₁, hg₁] at acc
    -- the same certificate bytes would name generation `g` and `g + 1`
    rcases acc₂ with ⟨_, c, e, -, g, -⟩ | ⟨_, c, e, -, g, -⟩ <;>
      rcases acc with ⟨_, c', e', -, g', -⟩ | ⟨_, c', e', -, g', -⟩
    · rw [encodeCert_injective (e.trans e'.symm)] at g; omega
    · exact absurd (e.trans e'.symm) (pgsc6_not_pgsc7 c c')
    · exact absurd (e'.trans e.symm) (pgsc6_not_pgsc7 c' c)
    · rw [encodeCert7_injective (e.trans e'.symm)] at g; omega

/-- **Bounded progress**: every adversarial trace has at most `loss m₀` acceptances. -/
theorem progress_bounded (s : AState) (rs : List Request) (m₀ : WideNet)
    (h₀ : decodeBytes s.policy.arch s.active = some m₀) :
    acceptedCount (runAdv s rs).2 ≤ loss s.policy.spec.corpusSpec m₀ := by
  obtain ⟨m, -, -, hl⟩ := runAdv_invariant s rs m₀ h₀
  omega

/-- The dead-end policy of `ProofGatedV6Limits` (target `|x|`, width ≤ 1, parameters in
`[-1,1]`, corpus `[-1, 1]`, interval `[-1, 1]`). -/
def deadPolicy : Policy := ⟨7, 6, 1, PCS.V2.ProofGatedV6Limits.arch11,
  PCS.V2.ProofGatedV6Limits.absNet, [-1, 1], -1, 1⟩

theorem deadPolicy_spec : deadPolicy.spec = PCS.V2.ProofGatedV6Limits.specDead := rfl

/-- **Dead end**: from the reachable state with active `relu` (loss `1`), **no request
whatsoever** is ever accepted, so no amount of honest effort makes progress. -/
theorem dead_end_stuck (g : Nat) (rs : List Request) :
    (runAdv ⟨deadPolicy, g, encodeBytes PCS.V2.ProofGatedV6Limits.reluNet⟩ rs).1 =
      ⟨deadPolicy, g, encodeBytes PCS.V2.ProofGatedV6Limits.reluNet⟩ ∧
    0 < loss deadPolicy.spec.corpusSpec PCS.V2.ProofGatedV6Limits.reluNet := by
  refine ⟨?_, by decide⟩
  induction rs with
  | nil => rfl
  | cons r rs ih =>
    have hr : (propose ⟨deadPolicy, g, encodeBytes PCS.V2.ProofGatedV6Limits.reluNet⟩ r).2.accepted = false := by
      cases h : (propose ⟨deadPolicy, g, encodeBytes PCS.V2.ProofGatedV6Limits.reluNet⟩ r).2.accepted with
      | false => rfl
      | true =>
        obtain ⟨o, n, ho, -, -, hadm⟩ := propose_accept_sound h
        have hv : decodeBytes deadPolicy.arch (encodeBytes PCS.V2.ProofGatedV6Limits.reluNet) =
            some PCS.V2.ProofGatedV6Limits.reluNet :=
          decodeBytes_encodeBytes deadPolicy.arch PCS.V2.ProofGatedV6Limits.reluNet (by decide)
        have ho' : decodeBytes deadPolicy.arch (encodeBytes PCS.V2.ProofGatedV6Limits.reluNet) = some o := ho
        rw [hv] at ho'
        cases ho'
        have hadm' : StrongAdmissible PCS.V2.ProofGatedV6Limits.specDead
            PCS.V2.ProofGatedV6Limits.reluNet n := hadm
        have := (acceptStrong_iff _ _ _).mpr hadm'
        rw [PCS.V2.ProofGatedV6Limits.dead_end.2.2 n] at this
        cases this
    simp only [runAdv]
    rw [propose_reject_frame hr]; exact ih

/-! ## Crash consistency of an abstract staged-commit protocol -/

/-- Durable storage: the trusted state, the receipt log and a staging slot. -/
structure Disk where
  st : AState
  log : List Receipt
  staged : Option Receipt
  deriving Repr, DecidableEq

/-- The abstract run, with the log accumulated. -/
def absDisk (d₀ : Disk) (rs : List Request) : Disk :=
  ⟨(runAdv d₀.st rs).1, d₀.log ++ (runAdv d₀.st rs).2, none⟩

/-- Micro-steps for one request (`k` = number of completed micro-steps, `0 … 4`):
`1` verify and stage the receipt, `2` atomic commit of `(generation, active)` (the
linearisation point; a rejection commits nothing), `3` append the receipt to the log,
`4` clear the staging slot. -/
def microStep (d : Disk) (r : Request) : Nat → Disk
  | 0 => d
  | 1 => { d with staged := some (propose d.st r).2 }
  | 2 => { d with st := (propose d.st r).1, staged := some (propose d.st r).2 }
  | 3 => ⟨(propose d.st r).1, d.log ++ [(propose d.st r).2], some (propose d.st r).2⟩
  | _ => ⟨(propose d.st r).1, d.log ++ [(propose d.st r).2], none⟩

/-- Recovery after a crash: a staged receipt whose new state is already durable but which
is not yet the last log entry is logged; in every other case the staging slot is
discarded. -/
def recover (d : Disk) : Disk :=
  match d.staged with
  | none => d
  | some rc =>
    if d.st.generation = rc.newGen ∧ d.st.active = rc.newActive ∧ rc.oldGen ≠ rc.newGen ∧
        d.log.getLast? ≠ some rc then ⟨d.st, d.log ++ [rc], none⟩
    else { d with staged := none }

/-- Complete `j` requests, then crash after `k` micro-steps of the next one. -/
def crashState (d₀ : Disk) (rs : List Request) (j k : Nat) : Disk :=
  match rs.drop j with
  | [] => absDisk d₀ rs
  | r :: _ => microStep (absDisk d₀ (rs.take j)) r k

theorem runAdv_snoc (s : AState) (rs : List Request) (r : Request) :
    runAdv s (rs ++ [r]) =
      ((propose (runAdv s rs).1 r).1, (runAdv s rs).2 ++ [(propose (runAdv s rs).1 r).2]) := by
  induction rs generalizing s with
  | nil => rfl
  | cons r' rs ih => simp only [List.cons_append, runAdv, ih]

theorem absDisk_append_one (d₀ : Disk) (rs : List Request) (r : Request) :
    absDisk d₀ (rs ++ [r]) =
      ⟨(propose (absDisk d₀ rs).st r).1, (absDisk d₀ rs).log ++ [(propose (absDisk d₀ rs).st r).2], none⟩ := by
  simp only [absDisk, runAdv_snoc, List.append_assoc]

theorem chain_last : ∀ (rcs : List Receipt) (a b : Nat × Bytes), Chain a rcs b →
    ∀ x, rcs.getLast? = some x → x.newGen = b.1
  | [], _, _, _, x, h => by simp at h
  | [rc], _, b, hc, x, h => by
    simp only [List.getLast?_singleton, Option.some.injEq] at h
    subst h
    have := hc.2
    simp only [Chain] at this
    rw [← this]
  | rc :: rc2 :: rcs, _, b, hc, x, h =>
    chain_last (rc2 :: rcs) _ b hc.2 x (by rw [List.getLast?_cons_cons] at h; exact h)

theorem runAdv_last (s : AState) (rs : List Request) :
    ∀ x, (runAdv s rs).2.getLast? = some x → x.newGen = (runAdv s rs).1.generation :=
  chain_last _ _ _ (runAdv_log_chain s rs)

/-- The durable log is consistent with the durable generation: its last receipt (if any)
ends at the current generation. -/
def LogConsistent (d : Disk) : Prop := ∀ x, d.log.getLast? = some x → x.newGen = d.st.generation

theorem absDisk_logConsistent (d₀ : Disk) (h : LogConsistent d₀) (rs : List Request) :
    LogConsistent (absDisk d₀ rs) := by
  intro x hx
  simp only [absDisk] at hx ⊢
  rw [List.getLast?_append] at hx
  cases hl : (runAdv d₀.st rs).2.getLast? with
  | some y =>
    rw [hl] at hx; simp only [Option.some_or, Option.some.injEq] at hx; subst hx
    exact runAdv_last _ _ y hl
  | none =>
    rw [hl] at hx; simp only [Option.none_or] at hx
    have hnil : (runAdv d₀.st rs).2 = [] := List.getLast?_eq_none_iff.mp hl
    have hrs : rs = [] := by cases rs with
      | nil => rfl
      | cons _ _ => simp [runAdv] at hnil
    subst hrs
    exact h x hx

/-- **Crash consistency**: after a crash at any micro-step of any request, recovery yields
exactly the abstract state after the completed requests or after one more. -/
theorem crash_recover_consistent (d₀ : Disk) (hd₀ : LogConsistent d₀) (rs : List Request)
    (j k : Nat) :
    recover (crashState d₀ rs j k) = absDisk d₀ (rs.take j) ∨
      recover (crashState d₀ rs j k) = absDisk d₀ (rs.take (j + 1)) := by
  cases hdr : rs.drop j with
  | nil =>
    have h1 : rs.take j = rs := List.take_of_length_le (List.drop_eq_nil_iff.mp hdr)
    left
    simp only [crashState, hdr, recover, absDisk, h1]
  | cons r rest =>
    have htake : rs.take (j + 1) = rs.take j ++ [r] := by
      rw [List.take_add_one, ← List.head?_drop, hdr]; rfl
    simp only [crashState, hdr]
    rw [htake, absDisk_append_one]
    have hcons := absDisk_logConsistent d₀ hd₀ (rs.take j)
    have hs0 : (absDisk d₀ (rs.take j)).staged = none := rfl
    generalize absDisk d₀ (rs.take j) = D at hcons hs0 ⊢
    obtain ⟨st, log, staged⟩ := D
    simp only at hs0
    subst hs0
    obtain ⟨e1, e2, e3, e4, -⟩ := propose_receipt_states st r
    match k with
    | 0 => left; rfl
    | 1 =>
      left
      simp only [microStep, recover]
      rw [if_neg (fun hc => hc.2.2.1 (e1.trans hc.1))]
    | 2 =>
      simp only [microStep, recover]
      by_cases hacc : (propose st r).2.accepted = true
      · have hg := (propose_accept_generation hacc).1
        right
        rw [if_pos ⟨e3.symm, e4.symm, by rw [e1, e3, hg]; omega, fun hl => by
          have := hcons _ hl; simp only at this; rw [e3, hg] at this; omega⟩]
      · simp only [Bool.not_eq_true] at hacc
        have hs := propose_reject_frame hacc
        left
        rw [if_neg (fun hc => by rw [hs] at hc; exact hc.2.2.1 (e1.trans hc.1)), hs]
    | 3 =>
      right
      simp only [microStep, recover]
      rw [if_neg (fun hc => hc.2.2.2 (by simp))]
    | n + 4 => right; rfl

/-- After recovery, the durable state satisfies every invariant of the abstract machine
(`runAdv_invariant`), because it *is* an abstract state. -/
theorem crash_recover_invariant (d₀ : Disk) (hd₀ : LogConsistent d₀) (rs : List Request)
    (j k : Nat) (m₀ : WideNet) (h₀ : decodeBytes d₀.st.policy.arch d₀.st.active = some m₀) :
    ∃ i, (i = j ∨ i = j + 1) ∧ recover (crashState d₀ rs j k) = absDisk d₀ (rs.take i) ∧
      ∃ m, Inv d₀.st.policy m₀ (recover (crashState d₀ rs j k)).st m := by
  rcases crash_recover_consistent d₀ hd₀ rs j k with h | h
  · obtain ⟨m, hm, -⟩ := runAdv_invariant d₀.st (rs.take j) m₀ h₀
    exact ⟨j, Or.inl rfl, h, m, by rw [h]; exact hm⟩
  · obtain ⟨m, hm, -⟩ := runAdv_invariant d₀.st (rs.take (j + 1)) m₀ h₀
    exact ⟨j + 1, Or.inr rfl, h, m, by rw [h]; exact hm⟩

/-- **Replay after recovery is harmless**: if the crashed request had committed, re-sending
it is rejected; the effect of a request is applied at most once. -/
theorem replay_after_commit (s : AState) (r : Request) (h : (propose s r).2.accepted = true) :
    (propose (propose s r).1 r).2.accepted = false :=
  race_one_winner s r r h h

/-! ## Executable adversarial fixture -/

/-- The three genuine certificates of the robust chain `gen0 ↦ r1 ↦ r2 ↦ gen3`, wrapped
in requests that request nothing (empty requested policy). -/
def genuineReqs : List Request :=
  (PCS.V2.ProofGatedProtocol.genCerts specWide 0 gen0 [r1, r2, gen3]).map
    (fun cb => ⟨[], 0, [], cb⟩)

/-- An adversarial interleaving: an interval-narrowing policy substitution, garbage with
a forged requested generation, the first genuine certificate, its replay, a stale request,
and the remaining genuine certificates. -/
def advTrace : List Request :=
  [attackInterval, ⟨PCS.V2.ProofGatedBytes.ascii "garbage", 7, PCS.V2.ProofGatedBytes.ascii "x",
    PCS.V2.ProofGatedBytes.ascii "PGSC6|junk"⟩] ++ genuineReqs.take 1 ++
    genuineReqs.take 1 ++ [attackStale] ++ genuineReqs.drop 1

/-- **Exactly the three genuine certificates are accepted**; the policy substitution,
garbage, replay and stale request are rejected; the final state is generation 3 with the
canonical bytes of the perfect `gen3`, under the unchanged pinned policy. -/
theorem adversarial_trace :
    (runAdv ⟨pinned0, 0, encodeBytes gen0⟩ advTrace).1 = ⟨pinned0, 3, encodeBytes gen3⟩ ∧
    acceptedCount (runAdv ⟨pinned0, 0, encodeBytes gen0⟩ advTrace).2 = 3 ∧
    ((runAdv ⟨pinned0, 0, encodeBytes gen0⟩ advTrace).2.map (·.accepted)) =
      [false, false, true, false, false, true, true] := by
  decide +kernel

end PCS.V2.ProofGatedBoundary
