import PCSReasoningLibrary.Library

/-!
# The prover episode of `environment.py` and verifier-derived feedback

`LeanEnvironment.step` is transcribed with its exact control flow:

* stepping a terminated episode is an error;
* the observation (Lean probe replay of the whole proposal) is an **untrusted oracle** — any
  function at all; a resource error terminates the episode with reward `-0.2`, truncated;
* an `invalid` observation, or a `closed` observation whose independent kernel verification
  fails, is invalid (reward `-0.2`, terminated, state not advanced);
* a `closed` observation that verifies gives reward `1.0` and a receipt;
* otherwise reward `-0.01 + 0.02·max(0, before − after)`; `max_steps` truncation.

Rewards are exact fixed-point integers in hundredths (`1.0 ↦ 100`, `-0.2 ↦ -20`,
`-0.01 ↦ -1`, `0.02 ↦ 2`), so no float adapter is needed.

The trusted verifier is a structure whose soundness is a *proof field*: any instance must prove
that acceptance entails the semantic statement.  `tokenVerifier` instantiates it with the
reasoning-library checker over prefix-encoded primitive proof actions, so success yields
schematic validity of the immutable original goal.
-/

namespace PCSVerifiedLearning

/-- A verifier with proved soundness. -/
structure Verifier (G A : Type) where
  check : G → List A → Bool
  Sem : G → Prop
  sound : ∀ g as, check g as = true → Sem g
  revision : String

inductive Obs where
  | resourceError
  | invalid
  | opened (goals : Nat)
  | closed
  deriving DecidableEq, Repr

def Obs.goals (fallback : Nat) : Obs → Nat
  | .opened n => n
  | .closed => 0
  | _ => fallback

inductive Status where
  | verified | invalid | exhausted | opened | resourceExhaustion
  deriving DecidableEq, Repr

structure Receipt (G A : Type) where
  goal : G
  actions : List A
  checker : String
  deriving DecidableEq, Repr

structure EState (G A : Type) where
  goal : G
  goalKey : G          -- the stored goal digest/index (`_goal_hash`)
  actions : List A
  done : Bool
  goals : Nat
  deriving DecidableEq, Repr

structure StepOut (G A : Type) where
  state : EState G A
  reward : Int
  terminated : Bool
  truncated : Bool
  status : Status
  receipt : Option (Receipt G A)
  deriving Repr

def reset {G A : Type} (obs : G → List A → Obs) (goal : G) : EState G A :=
  ⟨goal, goal, [], false, (obs goal []).goals 1⟩

/-- Exact transcription of `LeanEnvironment.step`. -/
def step {G A : Type} [DecidableEq G] (V : Verifier G A) (obs : G → List A → Obs) (maxSteps : Nat)
    (s : EState G A) (a : A) : Except String (StepOut G A) :=
  if s.done then .error "episode has terminated" else
  if s.goal ≠ s.goalKey then .error "immutable goal changed" else
  let proposal := s.actions ++ [a]
  let before := s.goals
  match obs s.goal proposal with
  | .resourceError => .ok ⟨{ s with done := true }, -20, false, true, .resourceExhaustion, none⟩
  | o =>
    let valid0 := o != .invalid
    let verified := valid0 && o == .closed && V.check s.goal proposal
    let valid := if o == .closed then verified else valid0
    let s1 := if valid then { s with actions := proposal, goals := o.goals s.goals } else s
    let exhausted := decide (maxSteps ≤ proposal.length)
    let after := s1.goals
    let reward : Int := if verified then 100 else if !valid then -20
      else -1 + 2 * ((before - after : Nat) : Int)
    .ok ⟨{ s1 with done := verified || !valid || exhausted }, reward, verified || !valid,
      exhausted && !verified,
      if verified then .verified else if !valid then .invalid else if exhausted then .exhausted
      else .opened,
      if verified then some ⟨s.goal, proposal, V.revision⟩ else none⟩

/-- The goal never changes across a step. -/
theorem step_goal {G A : Type} [DecidableEq G] (V : Verifier G A) (obs : G → List A → Obs) (m : Nat)
    (s : EState G A) (a : A) (o : StepOut G A) (h : step V obs m s a = .ok o) :
    o.state.goal = s.goal ∧ o.state.goalKey = s.goalKey := by
  rcases s with ⟨g, k, acts, d, n⟩
  unfold step at h
  by_cases hd : d = true
  · simp [hd] at h
  by_cases hk : g = k
  · subst hk
    cases hob : obs g (acts ++ [a]) <;> cases hc : V.check g (acts ++ [a]) <;>
      simp [hd, hob, hc] at h <;> subst h <;> simp
  · simp [hd, hk] at h

/-- **Success reward requires a fresh proof of the immutable original goal.**  For every
observation oracle: a step paying reward `1.0` (or reporting `verified`) had its exact proposal
accepted by the trusted verifier, and the goal is the stored original. -/
theorem episode_success_reward_requires_proof {G A : Type} [DecidableEq G] (V : Verifier G A)
    (obs : G → List A → Obs) (m : Nat) (s : EState G A) (a : A) (o : StepOut G A)
    (h : step V obs m s a = .ok o) (hr : o.reward = 100 ∨ o.status = .verified) :
    V.check s.goal (s.actions ++ [a]) = true ∧ V.Sem s.goal ∧ s.goal = s.goalKey ∧
      o.receipt = some ⟨s.goal, s.actions ++ [a], V.revision⟩ := by
  rcases s with ⟨g, k, acts, d, n⟩
  unfold step at h
  by_cases hd : d = true
  · simp [hd] at h
  by_cases hk : g = k
  · subst hk
    cases hob : obs g (acts ++ [a]) <;> cases hc : V.check g (acts ++ [a]) <;>
      simp [hd, hob, hc] at h <;> subst h <;> simp_all <;> first | exact V.sound _ _ hc | omega | (simp only [Obs.goals] at hr; split at hr <;> simp at hr <;> omega)
  · simp [hd, hk] at h

/-- Running an episode from `reset` over a list of proposed actions. -/
def run {G A : Type} [DecidableEq G] (V : Verifier G A) (obs : G → List A → Obs) (m : Nat) :
    EState G A → List A → List (StepOut G A)
  | _, [] => []
  | s, a :: as => match step V obs m s a with
    | .ok o => o :: run V obs m o.state as
    | .error _ => []

theorem run_goal {G A : Type} [DecidableEq G] (V : Verifier G A) (obs : G → List A → Obs) (m : Nat) :
    ∀ (as : List A) (s : EState G A), ∀ o ∈ run V obs m s as, o.state.goal = s.goal := by
  intro as
  induction as with
  | nil => intro s o ho; simp [run] at ho
  | cons a as ih =>
      intro s o ho
      simp only [run] at ho
      split at ho
      · rename_i o1 h1
        rcases List.mem_cons.1 ho with rfl | ho
        · exact (step_goal V obs m s a _ h1).1
        · rw [ih _ o ho, (step_goal V obs m s a _ h1).1]
      · simp at ho

/-- Along a whole episode, every success reward certifies the *original* reset goal. -/
theorem run_success_certifies_original {G A : Type} [DecidableEq G] (V : Verifier G A)
    (obs : G → List A → Obs) (m : Nat) (goal : G) (as : List A) :
    ∀ o ∈ run V obs m (reset obs goal) as, o.reward = 100 → V.Sem goal := by
  suffices H : ∀ (as : List A) (s : EState G A), s.goal = goal →
      ∀ o ∈ run V obs m s as, o.reward = 100 → V.Sem goal from
    H as _ rfl
  intro as
  induction as with
  | nil => intro s _ o ho; simp [run] at ho
  | cons a as ih =>
      intro s hs o ho hr
      simp only [run] at ho
      split at ho
      · rename_i o1 h1
        rcases List.mem_cons.1 ho with rfl | ho
        · have := episode_success_reward_requires_proof V obs m s a _ h1 (Or.inl hr)
          rw [← hs]; exact this.2.1
        · exact ih o1.state (by rw [(step_goal V obs m s a _ h1).1, hs]) o ho hr
      · simp at ho

/-! ## Producer feedback and verifier-derived training labels -/

/-- Untrusted producer feedback: everything except `goal`/`actions` is a claim. -/
structure Feedback (G A : Type) where
  goal : G
  actions : List A
  claimedReward : Int
  claimedVerified : Bool
  claimedReceipt : Option (Receipt G A)

structure TrainExample (G A : Type) where
  goal : G
  actions : List A
  label : Bool
  reward : Int
  checker : String
  deriving DecidableEq, Repr

/-- Intake: labels and rewards are recomputed by the trusted verifier. -/
def intake {G A : Type} (V : Verifier G A) (f : Feedback G A) : Option (TrainExample G A) :=
  if V.check f.goal f.actions then some ⟨f.goal, f.actions, true, 100, V.revision⟩ else none

/-- **Eligible feedback is re-verified**, and its label/reward are verifier-derived. -/
theorem eligible_feedback_reverified {G A : Type} (V : Verifier G A) (f : Feedback G A)
    (e : TrainExample G A) (h : intake V f = some e) :
    V.check e.goal e.actions = true ∧ V.Sem e.goal ∧ e.goal = f.goal ∧ e.actions = f.actions ∧
      e.label = true ∧ e.reward = 100 ∧ e.checker = V.revision := by
  unfold intake at h
  split at h
  · rename_i hc; cases h; exact ⟨hc, V.sound _ _ hc, rfl, rfl, rfl, rfl, rfl⟩
  · cases h

/-- Producer-supplied rewards, verified flags and receipts cannot influence intake. -/
theorem intake_noninterference {G A : Type} (V : Verifier G A) (f f' : Feedback G A)
    (hg : f.goal = f'.goal) (ha : f.actions = f'.actions) : intake V f = intake V f' := by
  unfold intake; rw [hg, ha]

/-- A forged success claim is rejected. -/
theorem forged_feedback_rejected {G A : Type} (V : Verifier G A) (f : Feedback G A)
    (h : V.check f.goal f.actions = false) : intake V f = none := by
  simp [intake, h]

/-- Replay of a receipt: exact checker revision and re-verification of the exact actions. -/
def replay {G A : Type} (V : Verifier G A) (r : Receipt G A) : Bool :=
  r.checker == V.revision && V.check r.goal r.actions

theorem replay_sound {G A : Type} (V : Verifier G A) (r : Receipt G A) (h : replay V r = true) :
    V.Sem r.goal ∧ r.checker = V.revision := by
  simp only [replay, Bool.and_eq_true, beq_iff_eq] at h
  exact ⟨V.sound _ _ h.2, h.1⟩

/-- Receipts issued by `step` replay. -/
theorem step_receipt_replays {G A : Type} [DecidableEq G] (V : Verifier G A) (obs : G → List A → Obs)
    (m : Nat) (s : EState G A) (a : A) (o : StepOut G A) (r : Receipt G A)
    (h : step V obs m s a = .ok o) (hr : o.receipt = some r) : replay V r = true := by
  have hv : o.status = .verified := by
    rcases s with ⟨g, k, acts, d, n⟩
    unfold step at h
    by_cases hd : d = true
    · simp [hd] at h
    by_cases hk : g = k
    · subst hk
      cases hob : obs g (acts ++ [a]) <;> cases hc : V.check g (acts ++ [a]) <;>
        simp [hd, hob, hc] at h <;> subst h <;> simp_all
    · simp [hd, hk] at h
  have := episode_success_reward_requires_proof V obs m s a o h (Or.inr hv)
  rw [this.2.2.2] at hr; cases hr
  simp [replay, this.1]

/-! ## Concrete verifier: prefix-encoded primitive proof actions -/

open PCSReasoningLibrary

/-- One primitive proof action (prefix encoding of a proof term; refines the first open goal). -/
inductive Tok where
  | hyp (φ : Fm) | topI | botE (φ : Fm) | andI | andL | andR | orL (b : Fm) | orR (a : Fm)
  | orE (a b : Fm) | lam (φ : Fm) | app
  deriving DecidableEq, Repr

def decode : Nat → List Tok → Option (Pf × List Tok)
  | 0, _ => none
  | _ + 1, [] => none
  | f + 1, t :: ts =>
    match t with
    | .hyp φ => some (.hyp φ, ts)
    | .topI => some (.topI, ts)
    | .botE φ => (decode f ts).map fun pr => (.botE φ pr.1, pr.2)
    | .andL => (decode f ts).map fun pr => (.andL pr.1, pr.2)
    | .andR => (decode f ts).map fun pr => (.andR pr.1, pr.2)
    | .orL b => (decode f ts).map fun pr => (.orL b pr.1, pr.2)
    | .orR a => (decode f ts).map fun pr => (.orR a pr.1, pr.2)
    | .lam φ => (decode f ts).map fun pr => (.lam φ pr.1, pr.2)
    | .andI => match decode f ts with
      | some (p, r) => (decode f r).map fun pr => (.andI p pr.1, pr.2)
      | none => none
    | .app => match decode f ts with
      | some (p, r) => (decode f r).map fun pr => (.app p pr.1, pr.2)
      | none => none
    | .orE a b => match decode f ts with
      | some (p, r) => match decode f r with
        | some (q, r') => (decode f r').map fun pr => (.orE p a b q pr.1, pr.2)
        | none => none
      | none => none

def encode : Pf → List Tok
  | .hyp φ => [.hyp φ]
  | .topI => [.topI]
  | .botE φ p => .botE φ :: encode p
  | .andI p q => .andI :: (encode p ++ encode q)
  | .andL p => .andL :: encode p
  | .andR p => .andR :: encode p
  | .orL b p => .orL b :: encode p
  | .orR a p => .orR a :: encode p
  | .orE p a b q r => .orE a b :: (encode p ++ encode q ++ encode r)
  | .lam φ p => .lam φ :: encode p
  | .app p q => .app :: (encode p ++ encode q)
  | .lem _ _ => []

/-- Fully decode an action sequence (all goals closed, no trailing actions). -/
def decodeAll (as : List Tok) : Option Pf :=
  match decode as.length as with
  | some (p, []) => some p
  | _ => none

def tokenCheck (goal : Fm) (as : List Tok) : Bool :=
  match decodeAll as with
  | some p => infer [] [] p == some goal
  | none => false

theorem tokenCheck_sound (goal : Fm) (as : List Tok) (h : tokenCheck goal as = true) : Valid goal := by
  unfold tokenCheck at h
  split at h
  · rename_i p _
    have hp : infer [] [] p = some goal := by simpa using h
    intro v
    exact infer_sound (lib := []) (by simp) v p [] goal (by simp) hp
  · cases h

def tokenVerifier : Verifier Fm Tok :=
  ⟨tokenCheck, Valid, tokenCheck_sound, "pcs-token-checker-v1"⟩

/-- Completeness of the action interface: every lemma-free proof is an action sequence. -/
theorem decode_encode : ∀ (p : Pf), p.Primitive → ∀ (f : Nat) (r : List Tok), p.size ≤ f →
    decode f (encode p ++ r) = some (p, r) := by
  intro p
  induction p with
  | hyp φ => intro _ f r hf; cases f with | zero => simp [Pf.size] at hf | succ f => rfl
  | topI => intro _ f r hf; cases f with | zero => simp [Pf.size] at hf | succ f => rfl
  | lem j σ => intro hp; exact absurd hp id
  | botE φ p ih =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f => simp only [encode, List.cons_append, decode]; rw [ih hp f r (by simp [Pf.size] at hf; omega)]; rfl
  | andL p ih =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f => simp only [encode, List.cons_append, decode]; rw [ih hp f r (by simp [Pf.size] at hf; omega)]; rfl
  | andR p ih =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f => simp only [encode, List.cons_append, decode]; rw [ih hp f r (by simp [Pf.size] at hf; omega)]; rfl
  | orL b p ih =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f => simp only [encode, List.cons_append, decode]; rw [ih hp f r (by simp [Pf.size] at hf; omega)]; rfl
  | orR a p ih =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f => simp only [encode, List.cons_append, decode]; rw [ih hp f r (by simp [Pf.size] at hf; omega)]; rfl
  | lam φ p ih =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f => simp only [encode, List.cons_append, decode]; rw [ih hp f r (by simp [Pf.size] at hf; omega)]; rfl
  | andI p q ihp ihq =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f =>
          simp only [Pf.size] at hf
          simp only [encode, List.cons_append, List.append_assoc, decode]
          rw [ihp hp.1 f (encode q ++ r) (by omega)]; simp only []; rw [ihq hp.2 f r (by omega)]; rfl
  | app p q ihp ihq =>
      intro hp f r hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f =>
          simp only [Pf.size] at hf
          simp only [encode, List.cons_append, List.append_assoc, decode]
          rw [ihp hp.1 f (encode q ++ r) (by omega)]; simp only []; rw [ihq hp.2 f r (by omega)]; rfl
  | orE p a b q r ihp ihq ihr =>
      intro hp f s hf; cases f with
      | zero => simp [Pf.size] at hf
      | succ f =>
          simp only [Pf.size] at hf
          simp only [encode, List.cons_append, List.append_assoc, decode]
          rw [ihp hp.1 f (encode q ++ (encode r ++ s)) (by omega)]; simp only []
          rw [ihq hp.2.1 f (encode r ++ s) (by omega)]; simp only []; rw [ihr hp.2.2 f s (by omega)]; rfl

theorem encode_length_ge : ∀ p : Pf, p.Primitive → p.size ≤ (encode p).length := by
  intro p
  induction p with
  | hyp _ | topI => intro _; simp [encode, Pf.size]
  | lem _ _ => intro hp; exact absurd hp id
  | botE _ p ih | andL p ih | andR p ih | orL _ p ih | orR _ p ih | lam _ p ih =>
      intro hp; have := ih hp; simp [encode, Pf.size]; omega
  | andI p q ihp ihq | app p q ihp ihq =>
      intro hp; have := ihp hp.1; have := ihq hp.2; simp [encode, Pf.size]; omega
  | orE p a b q r ihp ihq ihr =>
      intro hp; have := ihp hp.1; have := ihq hp.2.1; have := ihr hp.2.2
      simp [encode, Pf.size]; omega

theorem decodeAll_encode (p : Pf) (hp : p.Primitive) : decodeAll (encode p) = some p := by
  unfold decodeAll
  have := decode_encode p hp (encode p).length [] (encode_length_ge p hp)
  rw [List.append_nil] at this
  rw [this]

/-- Every checked primitive proof is accepted as an action sequence. -/
theorem tokenCheck_complete (goal : Fm) (p : Pf) (hp : p.Primitive) (h : infer [] [] p = some goal) :
    tokenCheck goal (encode p) = true := by
  simp [tokenCheck, decodeAll_encode p hp, h]

end PCSVerifiedLearning
