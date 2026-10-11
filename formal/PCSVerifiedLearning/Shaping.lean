import PCSVerifiedLearning.Episode

/-!
# Verifier-controlled potential-based reward shaping (exact rationals)

An episode is a start state and a list of macro-steps `(r, d, s')`: reward `r` (already the
macro's internally discounted reward), actual duration `d` and successor state `s'`.  The
discounted return discounts each macro-step by `γ^d`.

Shaped reward `r' = r + γ^d Φ(s') − Φ(s)` with a **frozen**, verifier-computed potential `Φ`
whose value at the final (terminal or truncated) state is forced to `0`.

* `potential_return_telescopes` — shaped return = return − `Φ(s₀)`;
* `general_telescope` — without the zero-end convention: `+ γ^T Φ(s_T)`;
* `potential_shaping_preserves_policy_order` — for every pair of policies, represented by their
  finite distributions over episodes from `s₀`, expected shaped returns compare exactly as
  expected returns;
* `macro_discount_correct` — macro-level discounting with `γ^duration` equals the primitive
  per-step discounted return;
* `shaped_reward_bounds` — bounded potentials give bounded shaped rewards;
* `dense_reward_cycle_positive` — the current dense reward is *not* potential-based: a valid
  split-then-close cycle returning to the same goal count earns `+0.02`, so it strictly prefers
  longer proofs; `potential_cycle_zero` — any potential term sums to zero on such a cycle.
-/

namespace PCSVerifiedLearning.Shaping

variable {S : Type}

def ret (γ : Rat) : List (Rat × Nat × S) → Rat
  | [] => 0
  | (r, d, _) :: t => r + γ ^ d * ret γ t

/-- Potential with the terminal/truncation convention: zero at the final state. -/
def phiEnd (Φ : S → Rat) (t : List (Rat × Nat × S)) (s : S) : Rat :=
  if t = [] then 0 else Φ s

def shapedRet (γ : Rat) (Φ : S → Rat) : S → List (Rat × Nat × S) → Rat
  | _, [] => 0
  | s, (r, d, s') :: t => (r + γ ^ d * phiEnd Φ t s' - Φ s) + γ ^ d * shapedRet γ Φ s' t

/-- **Telescoping identity** (non-empty episodes). -/
theorem potential_return_telescopes (γ : Rat) (Φ : S → Rat) :
    ∀ (s : S) (steps : List (Rat × Nat × S)), steps ≠ [] →
      shapedRet γ Φ s steps = ret γ steps - Φ s := by
  intro s steps
  induction steps generalizing s with
  | nil => intro h; exact absurd rfl h
  | cons x t ih =>
      intro _
      obtain ⟨r, d, s'⟩ := x
      by_cases ht : t = []
      · subst ht; simp only [shapedRet, phiEnd, ret, if_pos rfl]
        generalize γ ^ d = g; grind
      · simp only [shapedRet, phiEnd, ret, if_neg ht, ih s' ht]
        generalize γ ^ d = g; generalize ret γ t = R; grind

theorem rpow_add (g : Rat) (a : Nat) : ∀ b : Nat, g ^ (a + b) = g ^ a * g ^ b
  | 0 => by rw [Nat.add_zero, Rat.pow_zero]; grind
  | b + 1 => by
      rw [← Nat.add_assoc, Rat.pow_succ, Rat.pow_succ, rpow_add g a b]
      generalize g ^ a = x; generalize g ^ b = y; grind

def totalDur : List (Rat × Nat × S) → Nat
  | [] => 0
  | (_, d, _) :: t => d + totalDur t

def lastState : S → List (Rat × Nat × S) → S
  | s, [] => s
  | _, (_, _, s') :: t => lastState s' t

def shapedRetGen (γ : Rat) (Φ : S → Rat) : S → List (Rat × Nat × S) → Rat
  | _, [] => 0
  | s, (r, d, s') :: t => (r + γ ^ d * Φ s' - Φ s) + γ ^ d * shapedRetGen γ Φ s' t

/-- General telescoping: `Σ γ^{τ_t}(r_t + γ^{d_t}Φ(s_{t+1}) − Φ(s_t)) = G − Φ(s₀) + γ^T Φ(s_T)`. -/
theorem general_telescope (γ : Rat) (Φ : S → Rat) : ∀ (s : S) (steps : List (Rat × Nat × S)),
    shapedRetGen γ Φ s steps = ret γ steps - Φ s + γ ^ totalDur steps * Φ (lastState s steps) := by
  intro s steps
  induction steps generalizing s with
  | nil => simp [shapedRetGen, ret, totalDur, lastState]; grind
  | cons x t ih =>
      obtain ⟨r, d, s'⟩ := x
      simp only [shapedRetGen, ret, totalDur, lastState, ih s', rpow_add]
      generalize γ ^ d = g; generalize γ ^ totalDur t = h; generalize ret γ t = R
      generalize Φ (lastState s' t) = L
      grind

/-! ## Policy-order preservation -/

/-- A policy's episode distribution from `s₀`: weighted episodes. -/
def expect (f : List (Rat × Nat × S) → Rat) : List (Rat × List (Rat × Nat × S)) → Rat
  | [] => 0
  | (w, e) :: rest => w * f e + expect f rest

def totalWeight : List (Rat × List (Rat × Nat × S)) → Rat
  | [] => 0
  | (w, _) :: rest => w + totalWeight rest

theorem expect_shaped (γ : Rat) (Φ : S → Rat) (s₀ : S) :
    ∀ D : List (Rat × List (Rat × Nat × S)), (∀ we ∈ D, we.2 ≠ []) →
      expect (shapedRet γ Φ s₀) D = expect (ret γ) D - totalWeight D * Φ s₀ := by
  intro D hD
  induction D with
  | nil => simp only [expect, totalWeight]; grind
  | cons x rest ih =>
      obtain ⟨w, e⟩ := x
      simp only [expect, totalWeight]
      rw [potential_return_telescopes γ Φ s₀ e (hD _ List.mem_cons_self),
        ih (fun we h => hD we (List.mem_cons_of_mem _ h))]
      generalize ret γ e = R; generalize expect (ret γ) rest = E; generalize totalWeight rest = W
      grind

/-- **Potential shaping preserves the policy order** of the discounted episode objective, for
any two policies (episode distributions of total mass 1 over non-empty episodes from `s₀`). -/
theorem potential_shaping_preserves_policy_order (γ : Rat) (Φ : S → Rat) (s₀ : S)
    (D₁ D₂ : List (Rat × List (Rat × Nat × S)))
    (h₁ : ∀ we ∈ D₁, we.2 ≠ []) (h₂ : ∀ we ∈ D₂, we.2 ≠ [])
    (w₁ : totalWeight D₁ = 1) (w₂ : totalWeight D₂ = 1) :
    (expect (shapedRet γ Φ s₀) D₁ ≤ expect (shapedRet γ Φ s₀) D₂ ↔
      expect (ret γ) D₁ ≤ expect (ret γ) D₂) ∧
    (expect (shapedRet γ Φ s₀) D₁ = expect (shapedRet γ Φ s₀) D₂ ↔
      expect (ret γ) D₁ = expect (ret γ) D₂) := by
  rw [expect_shaped γ Φ s₀ D₁ h₁, expect_shaped γ Φ s₀ D₂ h₂, w₁, w₂]
  generalize expect (ret γ) D₁ = A; generalize expect (ret γ) D₂ = B
  constructor <;> constructor <;> intro h <;> grind

/-! ## Variable-length macros -/

/-- Primitive per-step discounted return. -/
def primRet (γ : Rat) : List Rat → Rat
  | [] => 0
  | r :: t => r + γ * primRet γ t

theorem primRet_append (γ : Rat) : ∀ (l m : List Rat),
    primRet γ (l ++ m) = primRet γ l + γ ^ l.length * primRet γ m := by
  intro l m
  induction l with
  | nil => simp [primRet]; grind
  | cons r t ih =>
      simp only [List.cons_append, primRet, ih, List.length_cons, Rat.pow_succ]
      generalize γ ^ t.length = g; generalize primRet γ t = P; generalize primRet γ m = M
      grind

/-- A macro-step: its primitive rewards and successor state. -/
def macroStep (γ : Rat) (m : List Rat × S) : Rat × Nat × S := (primRet γ m.1, m.1.length, m.2)

/-- **Macro discounting with `γ^duration` is exact.** -/
theorem macro_discount_correct (γ : Rat) : ∀ ms : List (List Rat × S),
    ret γ (ms.map (macroStep γ)) = primRet γ (ms.flatMap (·.1)) := by
  intro ms
  induction ms with
  | nil => rfl
  | cons m rest ih =>
      simp only [List.map_cons, ret, macroStep, List.flatMap_cons, primRet_append, ih]

/-! ## Bounded, frozen, verifier-controlled potentials -/

structure Potential (S : Type) where
  version : Nat
  Φ : S → Rat
  bound : Rat
  lower : ∀ s, -bound ≤ Φ s
  upper : ∀ s, Φ s ≤ bound

theorem shaped_reward_bounds (P : Potential S) (γ r : Rat) (d : Nat) (s s' : S)
    (hγ0 : 0 ≤ γ) (hγ1 : γ ≤ 1) :
    r - 2 * P.bound ≤ r + γ ^ d * P.Φ s' - P.Φ s ∧ r + γ ^ d * P.Φ s' - P.Φ s ≤ r + 2 * P.bound := by
  have hg0 : 0 ≤ γ ^ d := Rat.pow_nonneg hγ0
  have hg1 : γ ^ d ≤ 1 := by
    induction d with
    | zero => rw [Rat.pow_zero]; exact Rat.le_refl
    | succ n ih =>
        rw [Rat.pow_succ]
        have := Rat.mul_le_mul_of_nonneg_left hγ1 (Rat.pow_nonneg (n := n) hγ0)
        have h2 := ih (Rat.pow_nonneg hγ0); grind
  have l1 := P.lower s; have u1 := P.upper s; have l2 := P.lower s'; have u2 := P.upper s'
  have hb : 0 ≤ P.bound := by grind
  have a1 := Rat.mul_le_mul_of_nonneg_left u2 hg0
  have a2 := Rat.mul_le_mul_of_nonneg_left l2 hg0
  have a3 := Rat.mul_le_mul_of_nonneg_left hg1 hb
  generalize γ ^ d = g at *
  constructor <;> grind

/-- A shaped episode records the potential version; only the frozen version is admissible. -/
def frozenOK (P : Potential S) (versions : List Nat) : Bool := versions.all (· == P.version)

/-- The verifier-controlled potential used for proof episodes: `−min(goals, 10)/50`, computed
from the verifier-replayed goal count (not from the policy).  Bounded by `1/5`. -/
def goalPotential : Potential Nat where
  version := 1
  Φ g := -((min g 10 : Nat) : Rat) / 50
  bound := 1 / 5
  lower g := by
    have : ((min g 10 : Nat) : Rat) ≤ 10 := by
      have := Nat.min_le_right g 10
      exact_mod_cast this
    grind
  upper g := by
    have : (0 : Rat) ≤ ((min g 10 : Nat) : Rat) := by exact_mod_cast Nat.zero_le _
    grind

/-! ## Analysis of the current dense reward (exact hundredths, as in `environment.py`) -/

/-- Reward of a valid, unverified step from `before` to `after` open goals. -/
def denseValid (before after : Nat) : Int := -1 + 2 * ((before - after : Nat) : Int)

/-- **The dense reward is not potential-based**: split 1→3 goals then close 3→1 earns +0.02. -/
theorem dense_reward_cycle_positive : denseValid 1 3 + denseValid 3 1 = 2 := by decide

/-- For a cycle of `k` such loops the dense return grows linearly — a longer proof with the same
outcome is strictly preferred. -/
theorem dense_reward_prefers_longer (k : Nat) :
    100 + (k : Int) * (denseValid 1 3 + denseValid 3 1) > 100 ↔ 0 < k := by
  simp only [dense_reward_cycle_positive]; omega

/-- Any potential term sums to zero along a cycle returning to the same state (`γ = 1`). -/
theorem potential_cycle_zero (Φ : S → Rat) (s t : S) :
    (1 ^ 1 * Φ t - Φ s) + 1 ^ 1 * (1 ^ 1 * Φ s - Φ t) = 0 := by
  simp only [Rat.pow_succ, Rat.pow_zero]; grind

end PCSVerifiedLearning.Shaping
