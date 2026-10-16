import Std

/-!
Finite-state action-shield certificates. First-party continuation, not a newly
supplied Aristotle result. An untrusted policy may choose any admitted action;
every declared nondeterministic successor is checked, and induction covers every
finite history. This is a theorem about the exact finite transition model.
Deployment needs an explicit transition/model correspondence premise. There is
no liveness, model completeness, sensor integrity or general AI-safety theorem.
-/
set_option autoImplicit false

namespace PCSActionShield

structure Edge where
  source : Nat
  action : Nat
  target : Nat
  deriving DecidableEq, Repr

structure Model where
  initial : List Nat
  safe : List Nat
  edges : List Edge
  allowed : List (Nat × Nat)
  forbidden : List Nat
  deriving DecidableEq, Repr

/-- The finite certificate checks every possible successor, including branches
    not encountered in any submitted log. -/
def check (m : Model) : Bool :=
  m.initial.all (fun s => decide (s ∈ m.safe)) &&
  m.edges.all (fun e => decide (e.source ∈ m.safe →
    (e.source, e.action) ∈ m.allowed → e.target ∈ m.safe ∧ e.action ∉ m.forbidden))

def Certified (m : Model) : Prop :=
  (∀ s ∈ m.initial, s ∈ m.safe) ∧
  ∀ e ∈ m.edges, e.source ∈ m.safe →
    (e.source, e.action) ∈ m.allowed → e.target ∈ m.safe ∧ e.action ∉ m.forbidden

theorem check_iff_certified (m : Model) : check m = true ↔ Certified m := by
  simp only [check, Certified, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq]

/-- A policy supplies only proposals; the exact model and allowed table decide
    admission. The target is never selected by the policy checker. -/
def Admitted (m : Model) (e : Edge) : Prop :=
  e ∈ m.edges ∧ (e.source, e.action) ∈ m.allowed

inductive History (m : Model) : List Edge → Nat → Prop where
  | initial (s : Nat) (hs : s ∈ m.initial) : History m [] s
  | step {history : List Edge} {s : Nat} (h : History m history s)
      (e : Edge) (hsrc : e.source = s) (hadmit : Admitted m e) :
      History m (history ++ [e]) e.target

/-- Universal finite-history safety, regardless of the proposing policy and of
    which modeled nondeterministic successor occurs. -/
theorem admitted_histories_safe {m : Model} (hc : check m = true)
    {history : List Edge} {s : Nat} (h : History m history s) :
    s ∈ m.safe ∧ ∀ e ∈ history, e.action ∉ m.forbidden := by
  have cert := (check_iff_certified m).mp hc
  induction h with
  | initial s hs => exact ⟨cert.1 s hs, by simp⟩
  | @step history s h e hsrc hadmit ih =>
    have next := cert.2 e hadmit.1 (hsrc ▸ ih.1) hadmit.2
    refine ⟨next.1, ?_⟩
    intro x hx
    simp only [List.mem_append, List.mem_singleton] at hx
    rcases hx with hx | rfl
    · exact ih.2 x hx
    · exact next.2

/-- An extensional optimized guard has exactly the same admitted histories.
    The equality premise may be supplied by a separately source-bound compiler
    or CertiForge certificate; it is not assumed from optimizer output alone. -/
def GuardMatches (m : Model) (guard : Nat → Nat → Bool) : Prop :=
  ∀ s a, guard s a = true ↔ (s, a) ∈ m.allowed

inductive GuardHistory (m : Model) (guard : Nat → Nat → Bool) : List Edge → Nat → Prop where
  | initial (s : Nat) (hs : s ∈ m.initial) : GuardHistory m guard [] s
  | step {history : List Edge} {s : Nat} (h : GuardHistory m guard history s)
      (e : Edge) (hsrc : e.source = s) (hedge : e ∈ m.edges)
      (hguard : guard e.source e.action = true) :
      GuardHistory m guard (history ++ [e]) e.target

theorem optimized_guard_histories_safe {m : Model} {guard : Nat → Nat → Bool}
    (hc : check m = true) (hg : GuardMatches m guard)
    {history : List Edge} {s : Nat} (h : GuardHistory m guard history s) :
    s ∈ m.safe ∧ ∀ e ∈ history, e.action ∉ m.forbidden := by
  apply admitted_histories_safe hc
  induction h with
  | initial s hs => exact History.initial s hs
  | step h e hsrc hedge hguard ih =>
    exact History.step ih e hsrc ⟨hedge, (hg _ _).mp hguard⟩

/-- Deployment abstraction relates concrete state/action observations to the
    exact finite model. Its assumptions are explicit and independently open. -/
structure Correspondence (m : Model) (State Action : Type)
    (initial : State → Prop) (step : State → Action → State → Prop)
    (admission : State → Action → Prop) where
  state : State → Nat
  action : Action → Nat
  initial_models : ∀ x, initial x → state x ∈ m.initial
  step_models : ∀ x a y, step x a y → ⟨state x, action a, state y⟩ ∈ m.edges
  admission_models : ∀ x a, admission x a → (state x, action a) ∈ m.allowed

inductive DeployedHistory {State Action : Type} (initial : State → Prop)
    (step : State → Action → State → Prop) (admission : State → Action → Prop) : State → Prop where
  | initial (x : State) (hi : initial x) : DeployedHistory initial step admission x
  | step {x y : State} (h : DeployedHistory initial step admission x) (a : Action)
      (hs : step x a y) (ha : admission x a) : DeployedHistory initial step admission y

/-- Concrete deployment safety only under the stated abstraction/transition and
    admission correspondence. No log, producer signature or neural policy can
    discharge these premises on its own. -/
theorem deployed_histories_safe {m : Model} (hc : check m = true)
    {State Action : Type} {initial : State → Prop} {step : State → Action → State → Prop}
    {admission : State → Action → Prop} (corr : Correspondence m State Action initial step admission)
    {x : State} (h : DeployedHistory initial step admission x) : corr.state x ∈ m.safe := by
  have cert := (check_iff_certified m).mp hc
  induction h with
  | initial x hi => exact cert.1 _ (corr.initial_models x hi)
  | step h a hs ha ih =>
    exact (cert.2 _ (corr.step_models _ _ _ hs) ih (corr.admission_models _ _ ha)).1

end PCSActionShield
