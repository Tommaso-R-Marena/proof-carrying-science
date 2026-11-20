import Lean

/-!
# Proof-Gated Recursive Autoformalization (PGRA) — exact finite acceptance gate

A *capability certificate* over a frozen formalization corpus is a finite list of
per-case statuses. The gate is Bool-computable and mirrors
`PCS.V2.ProofGatedSelfImprovement`, but the state is formalization capability —
not ReLU neurons.

Acceptance requires:
1. **preserves** — every previously non-`fail` case keeps the same status;
2. **expands** — at least one previous `fail` becomes non-`fail`;
3. **strict loss** — the count of `fail` entries strictly decreases.

This module is research-only reference policy. It is not a deployment authority.
-/

namespace PCS.V2.ProofGatedFormalization

/-- Per-case formalization outcome on the frozen corpus. Nat codes: 0/1/2. -/
inductive CaseStatus where
  | fail
  | abstain
  | supported
  deriving Repr, DecidableEq, Inhabited

/-- Non-fail statuses are treated as certified outcomes (status-locked). -/
def CaseStatus.isCertified : CaseStatus → Bool
  | .fail => false
  | .abstain => true
  | .supported => true

def CaseStatus.toNat : CaseStatus → Nat
  | .fail => 0
  | .abstain => 1
  | .supported => 2

def CaseStatus.ofNat? : Nat → Option CaseStatus
  | 0 => some .fail
  | 1 => some .abstain
  | 2 => some .supported
  | _ => none

theorem CaseStatus.ofNat_toNat (s : CaseStatus) : CaseStatus.ofNat? s.toNat = some s := by
  cases s <;> rfl

theorem CaseStatus.toNat_ofNat? {n : Nat} {s : CaseStatus}
    (h : CaseStatus.ofNat? n = some s) : s.toNat = n := by
  revert s
  match n with
  | 0 => intro s h; cases h; rfl
  | 1 => intro s h; cases h; rfl
  | 2 => intro s h; cases h; rfl
  | n+3 => intro s h; cases h

/-- Finite capability vector: one `CaseStatus` per corpus case (length = corpus size). -/
abbrev Capability := List CaseStatus

/-- Exact loss: number of unresolved (`fail`) corpus cases. -/
def loss : Capability → Nat
  | [] => 0
  | .fail :: rest => loss rest + 1
  | _ :: rest => loss rest

/-- Bool checker: non-fail statuses are bit-identical under zip; lengths must match. -/
def preservesB : Capability → Capability → Bool
  | [], [] => true
  | s :: ss, t :: ts =>
      decide (s ≠ CaseStatus.fail → t = s) && preservesB ss ts
  | _, _ => false

/-- Bool checker: some fail becomes non-fail; lengths must match. -/
def expandsB : Capability → Capability → Bool
  | [], [] => false
  | s :: ss, t :: ts =>
      decide (s = CaseStatus.fail ∧ t ≠ CaseStatus.fail) || expandsB ss ts
  | _, _ => false

/-- Propositional preservation (same length + status lock on non-fail). -/
def preservesP : Capability → Capability → Prop
  | [], [] => True
  | s :: ss, t :: ts => (s ≠ CaseStatus.fail → t = s) ∧ preservesP ss ts
  | _, _ => False

/-- Propositional expansion (same length + at least one fail→non-fail). -/
def expandsP : Capability → Capability → Prop
  | [], [] => False
  | s :: ss, t :: ts => (s = CaseStatus.fail ∧ t ≠ CaseStatus.fail) ∨ expandsP ss ts
  | _, _ => False

def admissible (a b : Capability) : Prop :=
  preservesP a b ∧ expandsP a b ∧ loss b < loss a

def accept (a b : Capability) : Bool :=
  (preservesB a b && expandsB a b) && decide (loss b < loss a)

private theorem preservesB_sound (a b : Capability)
    (h : preservesB a b = true) : preservesP a b := by
  induction a generalizing b with
  | nil =>
      match b with
      | [] => exact True.intro
      | _ :: _ => simp [preservesB] at h
  | cons s ss ih =>
      match b with
      | [] => simp [preservesB] at h
      | t :: ts =>
          have hparts :
              (s ≠ CaseStatus.fail → t = s) ∧ preservesB ss ts = true := by
            simpa only [preservesB, Bool.and_eq_true, decide_eq_true_eq] using h
          exact ⟨hparts.1, ih ts hparts.2⟩

private theorem expandsB_sound (a b : Capability)
    (h : expandsB a b = true) : expandsP a b := by
  induction a generalizing b with
  | nil =>
      match b with
      | [] => simp [expandsB] at h
      | _ :: _ => simp [expandsB] at h
  | cons s ss ih =>
      match b with
      | [] => simp [expandsB] at h
      | t :: ts =>
          have hparts :
              (s = CaseStatus.fail ∧ t ≠ CaseStatus.fail) ∨
                expandsB ss ts = true := by
            simpa only [expandsB, Bool.or_eq_true, decide_eq_true_eq] using h
          cases hparts with
          | inl hy => exact Or.inl hy
          | inr htail => exact Or.inr (ih ts htail)

theorem accept_sound {a b : Capability} (h : accept a b = true) :
    admissible a b := by
  simp only [accept, Bool.and_eq_true] at h
  exact ⟨preservesB_sound a b h.1.1,
    expandsB_sound a b h.1.2, (decide_eq_true_eq).mp h.2⟩

theorem accepted_preserves {a b : Capability} (h : accept a b = true) :
    preservesP a b :=
  (accept_sound h).1

theorem accepted_expands {a b : Capability} (h : accept a b = true) :
    expandsP a b :=
  (accept_sound h).2.1

theorem accepted_strict_loss {a b : Capability} (h : accept a b = true) :
    loss b < loss a :=
  (accept_sound h).2.2

/-- Index-level reading of preservation: non-fail entries are unchanged. -/
theorem preservesP_getElem? {a b : Capability} (h : preservesP a b)
    (i : Nat) {s : CaseStatus} (hs : a[i]? = some s) (hne : s ≠ .fail) :
    b[i]? = some s := by
  induction a generalizing b i with
  | nil =>
      cases hs
  | cons x xs ih =>
      match b with
      | [] =>
          cases h
      | y :: ys =>
          have hp : (x ≠ CaseStatus.fail → y = x) ∧ preservesP xs ys := h
          match i with
          | 0 =>
              have hx : x = s := by
                simpa [List.getElem?_cons_zero] using hs
              subst hx
              have hy : y = x := hp.1 hne
              simp [hy]
          | i'+1 =>
              have hs' : xs[i']? = some s := by
                simpa [List.getElem?_cons_succ] using hs
              have hb := ih hp.2 i' hs'
              simpa [List.getElem?_cons_succ] using hb

theorem accepted_preserves_at {a b : Capability} (h : accept a b = true)
    (i : Nat) {s : CaseStatus} (hs : a[i]? = some s) (hne : s ≠ .fail) :
    b[i]? = some s :=
  preservesP_getElem? (accepted_preserves h) i hs hne

theorem two_accepted_steps {a b c : Capability}
    (hab : accept a b = true) (hbc : accept b c = true) :
    loss c < loss a :=
  Nat.lt_trans (accepted_strict_loss hbc) (accepted_strict_loss hab)

/-! Certified accepted chains are finite: exact nonnegative fail-count is a
    strictly decreasing Nat potential. -/
inductive CertifiedTrace : Nat → Capability → Capability → Prop where
  | zero (m : Capability) : CertifiedTrace 0 m m
  | extend {n : Nat} {a b c : Capability} :
      CertifiedTrace n a b → accept b c = true → CertifiedTrace (n + 1) a c

theorem trace_preserves {n : Nat} {a b : Capability}
    (h : CertifiedTrace n a b) (i : Nat) {s : CaseStatus}
    (hs : a[i]? = some s) (hne : s ≠ .fail) :
    b[i]? = some s := by
  induction h with
  | zero m => exact hs
  | extend hp hc ih =>
      exact accepted_preserves_at hc i (ih hs) hne

theorem trace_length_bound {n : Nat} {a b : Capability}
    (h : CertifiedTrace n a b) : n + loss b ≤ loss a := by
  induction h with
  | zero m => simp
  | extend hp hc ih =>
      have hd := accepted_strict_loss hc
      omega

theorem trace_steps_bounded {n : Nat} {a b : Capability}
    (h : CertifiedTrace n a b) : n ≤ loss a := by
  have hb := trace_length_bound h
  omega

/-! Arbitrarily varying untrusted proposers do not break integrity: rejected
    candidates leave the capability unchanged (monotonic non-regression). -/
def gatedStep (m proposed : Capability) : Capability :=
  if accept m proposed then proposed else m

theorem gatedStep_preserves (m proposed : Capability) (i : Nat)
    {s : CaseStatus} (hs : m[i]? = some s) (hne : s ≠ .fail) :
    (gatedStep m proposed)[i]? = some s := by
  cases h : accept m proposed with
  | false => simpa [gatedStep, h] using hs
  | true =>
      simpa [gatedStep, h] using (accepted_preserves_at h i hs hne)

theorem gatedStep_loss (m proposed : Capability) :
    loss (gatedStep m proposed) ≤ loss m := by
  cases h : accept m proposed with
  | false => simp [gatedStep, h]
  | true =>
      simpa [gatedStep, h] using (Nat.le_of_lt (accepted_strict_loss h))

def runStrategies : Capability → List (Capability → Capability) → Capability
  | m, [] => m
  | m, strategy :: rest =>
      runStrategies (gatedStep m (strategy m)) rest

theorem arbitrary_strategies_preserve (strategies : List (Capability → Capability))
    (m : Capability) (i : Nat) {s : CaseStatus}
    (hs : m[i]? = some s) (hne : s ≠ .fail) :
    (runStrategies m strategies)[i]? = some s := by
  induction strategies generalizing m with
  | nil => simpa [runStrategies] using hs
  | cons strategy rest ih =>
      change (runStrategies (gatedStep m (strategy m)) rest)[i]? = some s
      exact ih (gatedStep m (strategy m))
        (gatedStep_preserves m (strategy m) i hs hne)

theorem arbitrary_strategies_nonincrease (strategies : List (Capability → Capability))
    (m : Capability) : loss (runStrategies m strategies) ≤ loss m := by
  induction strategies generalizing m with
  | nil => simp [runStrategies]
  | cons strategy rest ih =>
      change loss (runStrategies (gatedStep m (strategy m)) rest) ≤ loss m
      exact Nat.le_trans (ih (gatedStep m (strategy m)))
        (gatedStep_loss m (strategy m))

theorem preservesP_length {a b : Capability} (h : preservesP a b) :
    a.length = b.length := by
  induction a generalizing b with
  | nil =>
      match b with
      | [] => rfl
      | _ :: _ => cases h
  | cons _ xs ih =>
      match b with
      | [] => cases h
      | _ :: ys =>
          have hp : _ ∧ preservesP xs ys := h
          simpa using (congrArg Nat.succ (ih hp.2))

theorem loss_zero_of_no_fail (m : Capability)
    (h : ∀ s ∈ m, s ≠ .fail) : loss m = 0 := by
  induction m with
  | nil => rfl
  | cons s ss ih =>
      have hs : s ≠ .fail := h s (by simp)
      have hss : ∀ t ∈ ss, t ≠ .fail := fun t ht => h t (by simp [ht])
      match s with
      | .fail => exact (hs rfl).elim
      | .abstain => exact ih hss
      | .supported => exact ih hss

theorem expandsP_has_fail {a b : Capability} (h : expandsP a b) :
    ∃ s ∈ a, s = CaseStatus.fail := by
  induction a generalizing b with
  | nil =>
      match b with
      | [] => cases h
      | _ :: _ => cases h
  | cons s ss ih =>
      match b with
      | [] => cases h
      | t :: ts =>
          cases h with
          | inl hy => exact ⟨s, by simp, hy.1⟩
          | inr htail =>
              obtain ⟨u, hu, heq⟩ := ih htail
              exact ⟨u, by simp [hu], heq⟩

theorem perfect_cannot_advance (m : Capability)
    (hperfect : ∀ s ∈ m, s ≠ .fail) (candidate : Capability) :
    accept m candidate = false := by
  cases hc : accept m candidate with
  | false => rfl
  | true =>
      obtain ⟨s, hs, heq⟩ := expandsP_has_fail (accepted_expands hc)
      exact False.elim (hperfect s hs heq)

/-! Concrete finite corpus examples (length 4).
    Status lock: non-fail entries must stay bit-identical, so improvements may
    only rewrite `fail` cells (e.g. abstain stays abstain). -/
def startCap : Capability := [.fail, .fail, .fail, .abstain]
def midCap : Capability := [.supported, .fail, .fail, .abstain]
def lateCap : Capability := [.supported, .abstain, .fail, .abstain]
def perfectCap : Capability := [.supported, .abstain, .supported, .abstain]
def regressiveCap : Capability := [.fail, .fail, .fail, .fail]

example : accept startCap midCap = true := by decide
example : accept midCap lateCap = true := by decide
example : accept lateCap perfectCap = true := by decide
example : accept startCap regressiveCap = false := by decide
example : accept perfectCap startCap = false := by decide
example : loss perfectCap = 0 := by decide
example : loss startCap = 3 := by decide

theorem perfectCap_no_fail (s : CaseStatus) (hs : s ∈ perfectCap) : s ≠ .fail := by
  simp [perfectCap] at hs
  rcases hs with rfl | rfl | rfl | rfl <;> decide

theorem perfectCap_terminal (candidate : Capability) :
    accept perfectCap candidate = false :=
  perfect_cannot_advance perfectCap perfectCap_no_fail candidate

theorem two_step_demo :
    accept startCap midCap = true ∧
    accept midCap lateCap = true ∧
    loss lateCap < loss startCap := by
  decide

end PCS.V2.ProofGatedFormalization
