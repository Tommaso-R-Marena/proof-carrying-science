import PCS.V2.ProofGatedCertCodec

/-!
# A proof-carrying promotion state machine over bytes

State: the current generation and the **exact active artifact bytes**. Input: arbitrary
certificate byte strings (from an untrusted, possibly adversarial, source). Transition:
decode the certificate (`decodeCert`), run the independent checker `checkCert` against
the deployment configuration, the current generation and the current active bytes; on
acceptance the active bytes become *exactly* the candidate bytes carried by the
certificate and the generation advances by one; otherwise nothing changes. Every step
appends a log entry recording the verifier decision, the active identity before and after,
and the certificate bytes.

Serving: `serve S s x = inferBytes S.arch s.active x`, i.e. decode the active bytes with the
deployment architecture and evaluate `predict`.

Results (every configuration, every initial valid model, every input sequence):
* `step_accept_refines` — an accepted step relates byte artifacts `o ↦ n` satisfying
  A ∧ B ∧ C, sets the active bytes to `encodeBytes n` and serves exactly `predict n`;
* `step_reject` — a rejected step changes nothing; malformed certificates, mismatched
  configurations, stale generations and substituted incumbents are rejected;
* `run_invariant` — over arbitrary adversarial sequences: the active bytes always decode
  to a valid network `m`; every integer the initial model got right is still right; every
  error bound of the initial model on `[lo,hi]` still holds; generations gained plus
  final loss is at most the initial loss;
* `run_log_sound` / `run_log_chain` — **observational consistency**: every logged
  acceptance carries certificate bytes that the checker accepts at the logged generation
  and logged active identity, the logged identity after an acceptance is exactly the
  certificate's candidate, rejected entries leave identity unchanged, consecutive entries
  chain, and the final state is the last logged identity; `serve_run` — what is served
  after any run is exactly `predict` of the decoded final active artifact;
* `run_complete` — every chain of strongly admissible modifications is realised by the
  generated certificates, ending with the exact canonical bytes of the last model;
* `hash_identity_*` — if the active identity is compared through a digest `H`, the
  byte-level guarantees transfer **under the explicit host hypothesis** that `H` has no
  collision with the active artifact; with a colliding digest, a substituted incumbent
  leads to a commit that violates the strong gate (`colliding_hash_breaks_gate`).
-/

namespace PCS.V2.ProofGatedProtocol

open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec

structure PState where
  generation : Nat
  active : Bytes
  deriving Repr, DecidableEq

inductive Decision
  | accepted
  | rejected
  deriving Repr, DecidableEq

structure LogEntry where
  generation : Nat
  activeBefore : Bytes
  certificate : Bytes
  decision : Decision
  activeAfter : Bytes
  deriving Repr, DecidableEq

/-- One transition of the promotion state machine. -/
def step (S : StrongSpec) (s : PState) (cb : Bytes) : PState × Decision :=
  match decodeCert cb with
  | some c =>
    if checkCert S s.generation s.active c then (⟨s.generation + 1, c.candidate⟩, .accepted)
    else (s, .rejected)
  | none => (s, .rejected)

/-- Run over an arbitrary list of certificate byte strings, producing the final state and
the decision log. -/
def run (S : StrongSpec) : PState → List Bytes → PState × List LogEntry
  | s, [] => (s, [])
  | s, cb :: cbs =>
    let r := step S s cb
    let rest := run S r.1 cbs
    (rest.1, ⟨s.generation, s.active, cb, r.2, r.1.active⟩ :: rest.2)

/-- What the runtime serves from a state. -/
def serve (S : StrongSpec) (s : PState) (x : Int) : Option Int := inferBytes S.arch s.active x

/-! ## Single steps -/

theorem step_decision (S : StrongSpec) (s : PState) (cb : Bytes) :
    (step S s cb).2 = .accepted ↔ checkCertBytes S s.generation s.active cb = true := by
  unfold step checkCertBytes
  cases decodeCert cb with
  | none => simp
  | some c => by_cases h : checkCert S s.generation s.active c = true <;> simp [h]

theorem step_reject {S : StrongSpec} {s : PState} {cb : Bytes}
    (h : (step S s cb).2 = .rejected) : (step S s cb).1 = s := by
  unfold step at h ⊢
  cases hd : decodeCert cb with
  | none => rfl
  | some c =>
    rw [hd] at h
    by_cases hc : checkCert S s.generation s.active c = true
    · simp [hc] at h
    · simp [hc]

theorem step_rejected_of_check {S : StrongSpec} {s : PState} {cb : Bytes}
    (h : checkCertBytes S s.generation s.active cb = false) : step S s cb = (s, .rejected) := by
  have hd : (step S s cb).2 = .rejected := by
    cases h2 : (step S s cb).2 with
    | rejected => rfl
    | accepted => rw [(step_decision S s cb).mp h2] at h; cases h
  exact Prod.ext (step_reject hd) hd

/-- **Refinement of an accepted step**: bytes → decoded networks → strong gate →
committed bytes → served function. -/
theorem step_accept_refines {S : StrongSpec} {s : PState} {cb : Bytes}
    (h : (step S s cb).2 = .accepted) :
    ∃ c o n, encodeCert c = cb ∧ checkCert S s.generation s.active c = true ∧
      decodeBytes S.arch s.active = some o ∧ decodeBytes S.arch (step S s cb).1.active = some n ∧
      StrongAdmissible S o n ∧
      (step S s cb).1 = ⟨s.generation + 1, encodeBytes n⟩ ∧ c.candidate = encodeBytes n ∧
      ∀ x, serve S (step S s cb).1 x = some (predict n x) := by
  unfold step at h ⊢
  cases hd : decodeCert cb with
  | none => rw [hd] at h; cases h
  | some c =>
    rw [hd] at h
    by_cases hc : checkCert S s.generation s.active c = true
    · simp only [hc, if_true]
      obtain ⟨hH, o, n, ho, hn, _, hen, hadm⟩ := checkCert_sound hc
      have hvn := decodeBytes_valid hn
      refine ⟨c, o, n, (decodeCert_iff cb c).mp hd, hc, hH.2.2.2.2 ▸ ho, hn, hadm,
        by rw [hen], hen.symm, fun x => ?_⟩
      simp only [serve]
      rw [← hen]
      exact inferBytes_encodeBytes _ _ hvn x
    · simp [hc] at h

/-- Malformed certificate bytes are rejected without changing the state. -/
theorem step_malformed (S : StrongSpec) (s : PState) (cb : Bytes) (h : decodeCert cb = none) :
    step S s cb = (s, .rejected) := by
  simp [step, h]

/-- A certificate made for another configuration is rejected. -/
theorem step_config_mismatch (S : StrongSpec) (s : PState) (c : Cert)
    (h : ¬ configMatches S c) : step S s (encodeCert c) = (s, .rejected) := by
  simp [step, decodeCert_encodeCert, checkCert_config_rejected S _ _ c h]

/-- A certificate for another generation (stale or future) is rejected. -/
theorem step_stale (S : StrongSpec) (s : PState) (c : Cert) (h : c.generation ≠ s.generation) :
    step S s (encodeCert c) = (s, .rejected) := by
  simp [step, decodeCert_encodeCert, checkCert_stale_rejected S _ _ c h]

/-- A certificate for a substituted incumbent artifact is rejected. -/
theorem step_substituted (S : StrongSpec) (s : PState) (c : Cert) (h : c.incumbent ≠ s.active) :
    step S s (encodeCert c) = (s, .rejected) := by
  simp [step, decodeCert_encodeCert, checkCert_substituted_rejected S _ _ c h]

/-! ## Arbitrary adversarial sequences -/

/-- The invariant relative to an initial model `m₀`. -/
def Inv (S : StrongSpec) (m₀ : WideNet) (s : PState) (m : WideNet) : Prop :=
  decodeBytes S.arch s.active = some m ∧
  (∀ x, predict m₀ x = predict S.target x → predict m x = predict S.target x) ∧
  (∀ B, ErrBound m₀ S.target S.lo S.hi B → ErrBound m S.target S.lo S.hi B)

def acceptedCount (log : List LogEntry) : Nat := (log.filter (·.decision = .accepted)).length

theorem run_fst_nil (S : StrongSpec) (s : PState) : run S s [] = (s, []) := rfl

/-- **Preservation over arbitrary certificate sequences.** -/
theorem run_invariant (S : StrongSpec) (cbs : List Bytes) (s : PState) (m₀ : WideNet)
    (h₀ : decodeBytes S.arch s.active = some m₀) :
    ∃ m, Inv S m₀ (run S s cbs).1 m ∧
      (run S s cbs).1.generation = s.generation + acceptedCount (run S s cbs).2 ∧
      acceptedCount (run S s cbs).2 + loss S.corpusSpec m ≤ loss S.corpusSpec m₀ := by
  suffices H : ∀ (cbs : List Bytes) (s : PState) (m₁ : WideNet), Inv S m₀ s m₁ →
      ∃ m, Inv S m₀ (run S s cbs).1 m ∧
        (run S s cbs).1.generation = s.generation + acceptedCount (run S s cbs).2 ∧
        acceptedCount (run S s cbs).2 + loss S.corpusSpec m ≤ loss S.corpusSpec m₁ by
    exact H cbs s m₀ ⟨h₀, fun _ h => h, fun _ h => h⟩
  intro cbs
  induction cbs with
  | nil => intro s m₁ hI; exact ⟨m₁, hI, by simp [run, acceptedCount], by simp [run, acceptedCount]⟩
  | cons cb cbs ih =>
    intro s m₁ hI
    cases hdec : (step S s cb).2 with
    | rejected =>
      have hs := step_reject hdec
      obtain ⟨m, hm, hg, hl⟩ := ih (step S s cb).1 m₁ (by rw [hs]; exact hI)
      refine ⟨m, hm, ?_, ?_⟩
      · simp only [run, acceptedCount, List.filter_cons, hdec] at hg ⊢
        simp only [reduceCtorEq, decide_false, Bool.false_eq_true, if_false]
        rw [hg, hs]
      · simp only [run, acceptedCount, List.filter_cons, hdec] at hl ⊢
        simpa using hl
    | accepted =>
      obtain ⟨c, o, n, -, -, ho, hn, hadm, hs', -, -⟩ := step_accept_refines hdec
      rw [hI.1] at ho; cases ho
      have hI' : Inv S m₀ (step S s cb).1 n :=
        ⟨hn, fun x hx => hadm.2.1 x (hI.2.1 x hx), fun B hB => hadm.2.2 B (hI.2.2 B hB)⟩
      obtain ⟨m, hm, hg, hl⟩ := ih (step S s cb).1 n hI'
      have hlt := hadm.1.2.2.2.2
      refine ⟨m, hm, ?_, ?_⟩
      · simp only [run, acceptedCount, List.filter_cons, hdec, decide_true, if_true,
          List.length_cons] at hg ⊢
        rw [hg, hs']; simp only; omega
      · simp only [run, acceptedCount, List.filter_cons, hdec, decide_true, if_true,
          List.length_cons] at hl ⊢
        omega

/-- **Observational consistency of serving**: after any run, the runtime serves exactly
`predict m` on every integer, for the unique valid network `m` whose canonical bytes are
the active artifact. -/
theorem serve_run (S : StrongSpec) (cbs : List Bytes) (s : PState) (m₀ : WideNet)
    (h₀ : decodeBytes S.arch s.active = some m₀) :
    ∃ m, encodeBytes m = (run S s cbs).1.active ∧ valid S.arch m = true ∧
      ∀ x, serve S (run S s cbs).1 x = some (predict m x) := by
  obtain ⟨m, ⟨hd, -, -⟩, -, -⟩ := run_invariant S cbs s m₀ h₀
  exact ⟨m, decodeBytes_canonical hd, decodeBytes_valid hd,
    fun x => by simp [serve, inferBytes, hd]⟩

/-- **Served no-forgetting over arbitrary runs.** -/
theorem serve_noForget (S : StrongSpec) (cbs : List Bytes) (s : PState) (m₀ : WideNet)
    (h₀ : decodeBytes S.arch s.active = some m₀) (x : Int)
    (hx : predict m₀ x = predict S.target x) :
    serve S (run S s cbs).1 x = some (predict S.target x) := by
  obtain ⟨m, ⟨hd, hnf, -⟩, -, -⟩ := run_invariant S cbs s m₀ h₀
  simp [serve, inferBytes, hd, hnf x hx]

/-- **Served worst-case error over arbitrary runs.** -/
theorem serve_error_le (S : StrongSpec) (cbs : List Bytes) (s : PState) (m₀ : WideNet)
    (h₀ : decodeBytes S.arch s.active = some m₀) (x : Int) (hx1 : S.lo ≤ x) (hx2 : x ≤ S.hi) :
    ∃ y, serve S (run S s cbs).1 x = some y ∧
      (y - predict S.target x).natAbs ≤ maxAbsErr m₀ S.target S.lo S.hi := by
  obtain ⟨m, ⟨hd, -, hrob⟩, -, -⟩ := run_invariant S cbs s m₀ h₀
  refine ⟨predict m x, by simp [serve, inferBytes, hd], ?_⟩
  exact hrob _ ((maxAbsErr_le_iff m₀ S.target S.lo S.hi _).mp (Nat.le_refl _)) x hx1 hx2

/-! ## The decision log -/

/-- Each log entry is justified by the checker. -/
def EntryOK (S : StrongSpec) (e : LogEntry) : Prop :=
  match e.decision with
  | .accepted => ∃ c, encodeCert c = e.certificate ∧
      checkCert S e.generation e.activeBefore c = true ∧ e.activeAfter = c.candidate
  | .rejected => checkCertBytes S e.generation e.activeBefore e.certificate = false ∧
      e.activeAfter = e.activeBefore

/-- **Log soundness**: every logged decision is exactly the checker's decision on the
logged certificate, generation and incumbent identity, and the logged identity after the
step is the certificate's candidate (on acceptance) or unchanged (on rejection). -/
theorem run_log_sound (S : StrongSpec) (cbs : List Bytes) (s : PState) :
    ∀ e ∈ (run S s cbs).2, EntryOK S e := by
  induction cbs generalizing s with
  | nil => simp [run]
  | cons cb cbs ih =>
    intro e he
    simp only [run, List.mem_cons] at he
    rcases he with rfl | he
    · cases hdec : (step S s cb).2 with
      | rejected =>
        simp only [EntryOK]
        refine ⟨?_, by rw [step_reject hdec]⟩
        cases h : checkCertBytes S s.generation s.active cb with
        | false => rfl
        | true => rw [(step_decision S s cb).mpr h] at hdec; cases hdec
      | accepted =>
        simp only [EntryOK]
        obtain ⟨c, o, n, hc, hchk, -, -, -, hs', hcand, -⟩ := step_accept_refines hdec
        exact ⟨c, hc, hchk, by rw [hs', hcand]⟩
    · exact ih _ e he

/-- Consecutive log entries chain, and the final state is the last logged identity. -/
def Chained : Bytes → List LogEntry → Bytes → Prop
  | a, [], b => a = b
  | a, e :: es, b => e.activeBefore = a ∧ Chained e.activeAfter es b

theorem run_log_chain (S : StrongSpec) (cbs : List Bytes) (s : PState) :
    Chained s.active (run S s cbs).2 (run S s cbs).1.active := by
  induction cbs generalizing s with
  | nil => simp [run, Chained]
  | cons cb cbs ih => exact ⟨rfl, ih _⟩

/-- Logged generations are consecutive at acceptances and constant at rejections. -/
theorem run_log_generations (S : StrongSpec) (cbs : List Bytes) (s : PState) :
    ∀ e ∈ (run S s cbs).2, s.generation ≤ e.generation := by
  induction cbs generalizing s with
  | nil => simp [run]
  | cons cb cbs ih =>
    intro e he
    simp only [run, List.mem_cons] at he
    rcases he with rfl | he
    · exact Nat.le_refl _
    · have := ih _ e he
      have hg : s.generation ≤ (step S s cb).1.generation := by
        cases hdec : (step S s cb).2 with
        | rejected => rw [step_reject hdec]; exact Nat.le_refl _
        | accepted =>
          obtain ⟨_, _, _, _, _, _, _, _, hs', _, _⟩ := step_accept_refines hdec
          rw [hs']; exact Nat.le_succ _
      omega

/-! ## Completeness: every admissible chain is realised -/

/-- A chain of strongly admissible modifications, as an explicit list of models. -/
def AdmChain (S : StrongSpec) : WideNet → List WideNet → Prop
  | _, [] => True
  | a, b :: bs => StrongAdmissible S a b ∧ AdmChain S b bs

def lastModel : WideNet → List WideNet → WideNet
  | a, [] => a
  | _, b :: bs => lastModel b bs

/-- The (untrusted) generator: one certificate per step. -/
def genCerts (S : StrongSpec) : Nat → WideNet → List WideNet → List Bytes
  | _, _, [] => []
  | g, a, b :: bs => encodeCert (genCert S g a b) :: genCerts S (g + 1) b bs

/-- **Completeness of the protocol**: running the generated certificates of an admissible
chain accepts every step and ends with the canonical bytes of the last model. -/
theorem run_complete (S : StrongSpec) (ms : List WideNet) :
    ∀ (g : Nat) (a : WideNet), AdmChain S a ms →
      (run S ⟨g, encodeBytes a⟩ (genCerts S g a ms)).1 =
          ⟨g + ms.length, encodeBytes (lastModel a ms)⟩ ∧
        acceptedCount (run S ⟨g, encodeBytes a⟩ (genCerts S g a ms)).2 = ms.length := by
  induction ms with
  | nil => intro g a _; simp [genCerts, run, lastModel, acceptedCount]
  | cons b bs ih =>
    intro g a hc
    have hstep : step S ⟨g, encodeBytes a⟩ (encodeCert (genCert S g a b)) =
        (⟨g + 1, encodeBytes b⟩, .accepted) := by
      have := checkCert_complete S g a b hc.1
      simp only [step, decodeCert_encodeCert, this, if_true]
      rfl
    obtain ⟨h1, h2⟩ := ih (g + 1) b hc.2
    simp only [genCerts, run, hstep, lastModel, List.length_cons]
    refine ⟨?_, ?_⟩
    · rw [h1]; simp only [PState.mk.injEq, and_true]; omega
    · simp only [acceptedCount, List.filter_cons, decide_true, if_true, List.length_cons]
      simp only [acceptedCount] at h2
      rw [h2]

/-! ## Digest-based identity: an explicit host hypothesis -/

section hash
variable {D : Type} [DecidableEq D]

/-- A checker variant that identifies the incumbent by a digest `H` instead of by bytes
and then evaluates the certificate *on the incumbent bytes it carries*. -/
def checkCertH (H : Bytes → D) (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert) : Bool :=
  decide (H c.incumbent = H active) && checkCert S g c.incumbent c

/-- Under the host hypothesis that no other byte string has the active artifact's digest,
the digest checker accepts exactly what the byte checker accepts. -/
theorem hash_identity_sound (H : Bytes → D) (S : StrongSpec) (g : Nat) (active : Bytes)
    (hnc : ∀ b, H b = H active → b = active) (c : Cert) :
    checkCertH H S g active c = checkCert S g active c := by
  unfold checkCertH
  by_cases he : H c.incumbent = H active
  · have := hnc _ he
    simp [this]
  · have hne : c.incumbent ≠ active := fun h => he (h ▸ rfl)
    simp [he, checkCert_substituted_rejected S g active c hne]

/-- A step that uses digest identity. -/
def stepH (H : Bytes → D) (S : StrongSpec) (s : PState) (cb : Bytes) : PState × Decision :=
  match decodeCert cb with
  | some c =>
    if checkCertH H S s.generation s.active c then (⟨s.generation + 1, c.candidate⟩, .accepted)
    else (s, .rejected)
  | none => (s, .rejected)

theorem hash_identity_step (H : Bytes → D) (S : StrongSpec) (s : PState)
    (hnc : ∀ b, H b = H s.active → b = s.active) (cb : Bytes) :
    stepH H S s cb = step S s cb := by
  unfold stepH step
  cases decodeCert cb with
  | none => rfl
  | some c => simp only [hash_identity_sound H S s.generation s.active hnc c]

end hash

/-- **The no-collision hypothesis is necessary.** With a digest that collides (here the
constant digest), a certificate for the substituted incumbent `gen0` is accepted while the
active artifact is the perfect `gen3`, and the committed candidate `r1` is *not* a strongly
admissible successor of `gen3`. -/
theorem colliding_hash_breaks_gate :
    let H : Bytes → Nat := fun _ => 0
    let s : PState := ⟨0, encodeBytes gen3⟩
    (stepH H specWide s (encodeCert cert1)).2 = .accepted ∧
    (stepH H specWide s (encodeCert cert1)).1.active = encodeBytes r1 ∧
    ¬ StrongAdmissible specWide gen3 r1 := by
  have hc : checkCert specWide 0 (encodeBytes gen0) cert1 = true := cert1_accepted
  refine ⟨?_, ?_, ?_⟩
  · simp only [stepH, decodeCert_encodeCert, checkCertH]
    have hinc : cert1.incumbent = encodeBytes gen0 := rfl
    rw [hinc, hc]; rfl
  · simp only [stepH, decodeCert_encodeCert, checkCertH]
    have hinc : cert1.incumbent = encodeBytes gen0 := rfl
    rw [hinc, hc]; rfl
  · rw [← acceptStrong_iff]; decide

/-! ## Executable fixtures -/

/-- The three-step robust chain of `ProofGatedStrongGate`, as an admissible chain. -/
theorem wide_chain_adm : AdmChain specWide gen0 [r1, r2, gen3] := by
  refine ⟨?_, ?_, ?_, trivial⟩ <;> rw [← acceptStrong_iff] <;> decide

/-- The protocol, fed the generated certificates, commits all three steps and ends at the
canonical bytes of the perfect network. -/
theorem wide_chain_run :
    (run specWide ⟨0, encodeBytes gen0⟩ (genCerts specWide 0 gen0 [r1, r2, gen3])).1 =
      ⟨3, encodeBytes gen3⟩ :=
  (run_complete specWide [r1, r2, gen3] 0 gen0 wide_chain_adm).1

/-- An adversarial interleaving: garbage, a replayed certificate, a tampered certificate,
then the genuine certificates. Exactly the genuine ones are accepted. -/
theorem adversarial_run :
    let genuine := genCerts specWide 0 gen0 [r1, r2, gen3]
    let replay := encodeCert cert1
    let tampered := encodeCert { cert1 with errLevel := 2000000000 }
    acceptedCount (run specWide ⟨0, encodeBytes gen0⟩
      ([ascii "garbage", tampered] ++ genuine.take 1 ++ [replay] ++ genuine.drop 1)).2 = 3 ∧
    (run specWide ⟨0, encodeBytes gen0⟩
      ([ascii "garbage", tampered] ++ genuine.take 1 ++ [replay] ++ genuine.drop 1)).1 =
      ⟨3, encodeBytes gen3⟩ := by
  decide +kernel

end PCS.V2.ProofGatedProtocol
